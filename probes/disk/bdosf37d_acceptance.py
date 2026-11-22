#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""bdosf37d-acceptance (D-DISKCONTRACT gap 4, 2026-11-17): the BDOS through $F37D -- the
entry a ROM program uses with no MSX-DOS loaded -- for the functions no gate compared that
way, on the National CF-3300 and on the shipped machine.

$F37D has its own dispatch in our disk ROM (`bdos_tab`, disk/kernel.asm), separate from
the $0005 BDOS that the bdosx / dosl .COM exercisers test; bdosunop-acceptance compared
SETDTA / DSKRST / FOPEN / FCLOSE / SEQREAD through it, nothing else. bdosunop's harness:
a BASIC program (AUTOEXEC.BAS, root entry 0) calls $F37D through a USR stub per row, on a
disk that also holds SECOND.DAT and THIRD.DAT.

Scored: every row's A; the published register outputs where there are some (VERSION HL /
B, LOGIN HL, ALLOC A / BC / DE / HL, GDATE A / DE / HL, GTIME DE / HL); every FCB's 37
bytes afterwards; the DTA (128 B) afterwards; root entries 0..3 of the disk afterwards.
Every register is PRINTED, scored or not.
"""
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))
import omsx_preflight  # noqa: E402
import probe_tmp  # noqa: E402
from disk_probe_bdos import fat12_add  # noqa: E402

OMSX = shutil.which("openmsx") or "/opt/homebrew/bin/openmsx"
MACHINES = {"cf": "National_CF-3300",
            "zb": os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")}
# name -> (address, the 8.3 name, a rename target at +17 or None, RR (+33..35))
FCBS = {"S": (0xC020, "SECOND  DAT", None, 1),          # OPEN / FSIZE / SETRND / RDRND
        "W": (0xC050, "????????DAT", None, 0),          # SFIRST / SNEXT pattern
        "R": (0xC080, "THIRD   DAT", "RENAMED DAT", 0), # FREN
        "D": (0xC0B0, "RENAMED DAT", None, 0),          # FDEL (the renamed one)
        "N": (0xC0E0, "NEWFILE TMP", None, 2)}          # FMAKE / WRRND / WRZER / FCLOSE
F = {k: v[0] for k, v in FCBS.items()}
DTA = 0xD400
# (function, DE, label, the scored registers beyond A)
ROWS = [(0x1A, DTA, "SETDTA", ()), (0x0C, 0, "VERSION", ("HL", "B")),
        (0x18, 0, "LOGIN", ("HL",)), (0x19, 0, "CURDRV", ()),
        (0x0E, 0, "SELDSK 0", ()), (0x2A, 0, "GDATE", ("DE", "HL")),
        (0x2C, 0, "GTIME", ("DE", "HL")), (0x1B, 0, "ALLOC 0", ("B", "C", "DE", "HL")),
        (0x11, F["W"], "SFIRST *.DAT", ()), (0x12, F["W"], "SNEXT", ()),
        (0x12, F["W"], "SNEXT (none left)", ()),
        (0x0F, F["S"], "FOPEN SECOND", ()), (0x23, F["S"], "FSIZE SECOND", ()),
        (0x24, F["S"], "SETRND", ()), (0x21, F["S"], "RDRND rec 1", ()),
        (0x10, F["S"], "FCLOSE SECOND", ()),
        (0x17, F["R"], "FREN THIRD->RENAMED", ()), (0x13, F["D"], "FDEL RENAMED", ()),
        (0x16, F["N"], "FMAKE NEWFILE", ()), (0x22, F["N"], "WRRND rec 2", ()),
        (0x28, F["N"], "WRZER rec 2", ()), (0x10, F["N"], "FCLOSE NEWFILE", ()),
        (0x0B, 0, "CONST", ()), (0x06, 0x00FF, "DIRIO in", ()), (0x02, 0x51, "CONOUT 'Q'", ())]
UNSCORED_A = {0x1A, 0x02}           # SETDTA / CONOUT: A is no contract
DUMP = 0xCA00
STRIDE = 10
# USR stub at $C000: C = ($C3F0), DE = ($C3F2), HL = ($C3F4); CALL $F37D; store AF at
# $C3F6, HL / DE / BC at $C3FA / $C3FC / $C3FE
MC = [0x3A, 0xF0, 0xC3, 0x4F, 0xED, 0x5B, 0xF2, 0xC3, 0x2A, 0xF4, 0xC3, 0xCD, 0x7D,
      0xF3, 0x22, 0xFA, 0xC3, 0xED, 0x53, 0xFC, 0xC3, 0xED, 0x43, 0xFE, 0xC3, 0xF5,
      0xE1, 0x22, 0xF6, 0xC3, 0xC9]


def program() -> bytes:
    def fcb(addr, name, new, rr):
        s = (f'FOR I=0 TO 36:POKE &H{addr:X}+I,0:NEXT:N$="{name}":'
             f'FOR I=1 TO 11:POKE &H{addr:X}+I,ASC(MID$(N$,I,1)):NEXT')
        if new:
            s += f':N$="{new}":FOR I=1 TO 11:POKE &H{addr + 16:X}+I,ASC(MID$(N$,I,1)):NEXT'
        if rr:
            s += f":POKE &H{addr + 33:X},{rr}"
        return s
    lines = ["10 CLEAR 200,&HBFFF",
             f"20 FOR I=0 TO {len(MC) - 1}:READ A:POKE &HC000+I,A:NEXT"]
    lines += [f"{30 + k} " + fcb(*v) for k, v in enumerate(FCBS.values())]
    lines += ["40 DEFUSR=&HC000",
              f"50 FOR R=0 TO {len(ROWS) - 1}:READ F,D",
              "60 POKE &HC3F0,F:POKE &HC3F2,D-INT(D/256)*256:POKE &HC3F3,INT(D/256):"
              "POKE &HC3F4,0:POKE &HC3F5,0",
              f"70 X=USR(0):FOR J=0 TO 9:POKE &HC800+R*{STRIDE}+J,PEEK(&HC3F6+J):NEXT:POKE &HC7FF,R"
              f":POKE &HC800+R*{STRIDE}+2,PEEK(&H{F['S'] + 36:X})"    # FCB S's RR top byte and
              f":POKE &HC800+R*{STRIDE}+3,PEEK(&H{F['S'] + 15:X})",   # RS high byte, each row
              "80 NEXT",
              "85 " + ":".join(f"FOR I=0 TO 36:POKE &H{DUMP + 37 * k:X}+I,PEEK(&H{a:X}+I):NEXT"
                               for k, (a, *_r) in enumerate(FCBS.values())),
              f"86 FOR I=0 TO 127:POKE &H{DUMP + 37 * len(FCBS):X}+I,PEEK(&H{DTA:X}+I):NEXT",
              "87 POKE &HC7FE,165",
              "90 DATA " + ",".join(str(b) for b in MC)]
    for i in range(0, len(ROWS), 6):
        lines.append(f"{100 + i} DATA " + ",".join(f"{f},{d}" for f, d, _l, _s in ROWS[i:i + 6]))
    return ("\r\n".join(lines) + "\r\n").encode("ascii") + b"\x1a"


GEOMETRY = os.environ.get("ZB_GEOMETRY", "720")   # D-DISKCONTRACT gap 13: "360" = 1DD, media $F8


def to_360(img: bytearray) -> bytearray:
    """The 720 KB empty image re-made as a 360 KB single-sided one (media $F8): 720
    sectors, 1 head, 2 sectors per FAT -- FATs at 1..4, the root at 5..11, data from 12."""
    boot = bytearray(img[:512])
    boot[19:21] = (720).to_bytes(2, "little")      # total sectors
    boot[21] = 0xF8                                 # media
    boot[22:24] = (2).to_bytes(2, "little")         # sectors per FAT
    boot[26:28] = (1).to_bytes(2, "little")         # heads
    out = bytearray(720 * 512)
    out[:512] = boot
    for f in (1, 3):                                # both FAT copies
        out[f * 512:f * 512 + 3] = b"\xF8\xFF\xFF"
    return out


def geometry(img: bytes) -> dict:
    spf = int.from_bytes(img[22:24], "little")
    root = 1 + 2 * spf
    rsec = int.from_bytes(img[17:19], "little") * 32 // 512
    return {"spf": spf, "root": root, "rsec": rsec, "data": root + rsec, "spc": img[13]}


def image() -> bytes:
    path = probe_tmp.tmp("bdosf37d_empty.dsk")
    subprocess.run(["python3", os.path.join(REPO, "tools", "make_test_dsk.py"), "--empty", path],
                   check=True, capture_output=True)
    img = bytearray(open(path, "rb").read())
    if GEOMETRY == "360":
        img = to_360(img)
    fat12_add(img, "AUTOEXEC", "BAS", program())                     # root entry 0
    fat12_add(img, "SECOND", "DAT", bytes(range(256)) * 2)           # root entry 1
    fat12_add(img, "THIRD", "DAT", b"THIRD FILE\r\n" * 10)           # root entry 2
    return bytes(img)


def run(machine, img):
    td = tempfile.mkdtemp(prefix="bdosf37d_", dir=probe_tmp.tmp(""))
    try:
        dsk = os.path.join(td, "v.dsk")
        open(dsk, "wb").write(img)
        out = os.path.join(td, "m.txt")
        n_dump = 37 * len(FCBS) + 128
        tcl = ("set throttle off\nafter time 200 {\n"
               f"  set f [open {{{out}}} w]\n"
               "  binary scan [debug read_block memory 0xC7FE 2] H* flag\n"
               f"  binary scan [debug read_block memory 0xC800 {STRIDE * len(ROWS)}] H* v\n"
               f"  binary scan [debug read_block memory {DUMP} {n_dump}] H* d\n"
               '  puts $f "$flag $v $d"\n  close $f\n  exit\n}\n')
        open(os.path.join(td, "s.tcl"), "w").write(tcl)
        subprocess.run(omsx_preflight.guarded([OMSX, "-machine", machine, "-diska", dsk,
                       "-command", "set renderer none; set sound_driver null",
                       "-script", os.path.join(td, "s.tcl")]),
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=400)
        root = open(dsk, "rb").read()                  # the WHOLE image afterwards
        if not os.path.exists(out):
            return None
        flag, v, d = open(out).read().split()
        return bytes.fromhex(flag), bytes.fromhex(v), bytes.fromhex(d), root
    finally:
        shutil.rmtree(td, ignore_errors=True)


def regs(rec):
    """AF / HL / DE / BC as the stub stored them: F, A, (2 unused), L, H, E, D, C, B."""
    return {"F": rec[0], "A": rec[1], "HL": rec[4] | rec[5] << 8, "DE": rec[6] | rec[7] << 8,
            "B": rec[9], "C": rec[8], "S36": rec[2], "S15": rec[3]}


def main() -> int:
    img = image()
    res = {k: run(m, img) for k, m in MACHINES.items()}
    for k, r in res.items():
        if r is None or r[0] != bytes([0xA5, len(ROWS) - 1]):
            print(f"  FAIL  {MACHINES[k]}: the program never finished -- NOTHING WAS MEASURED "
                  f"(flag {r[0].hex() if r else None})")
            print("===== bdosf37d-acceptance: FAIL =====")
            return 1
    ok = True
    for i, (f, _d, what, scored) in enumerate(ROWS):
        r = {k: regs(res[k][1][STRIDE * i:STRIDE * i + STRIDE]) for k in res}
        keys = (() if f in UNSCORED_A else ("A",)) + tuple(scored)
        same = all(r["cf"][x] == r["zb"][x] for x in keys)
        ok &= same
        def fmt(x):
            return (f"A{x['A']:02X} F{x['F']:02X} BC{x['B']:02X}{x['C']:02X} "
                    f"DE{x['DE']:04X} HL{x['HL']:04X}")
        print(f"  {'PASS' if same else 'FAIL'}  {f:02X} {what:22s} scored {'/'.join(keys) or '-':10s} "
              f"CF {fmt(r['cf'])}  ours {fmt(r['zb'])}  S+36 {r['cf']['S36']:02X}/{r['zb']['S36']:02X}"
              f" S+15 {r['cf']['S15']:02X}/{r['zb']['S15']:02X}")
    for n, name in enumerate(FCBS):
        c, z = (res[k][2][37 * n:37 * n + 37] for k in ("cf", "zb"))
        ok &= c == z
        print(f"  {'PASS' if c == z else 'FAIL'}  FCB {name} afterwards: CF {c.hex()}"
              + ("" if c == z else f"\n                          ours {z.hex()}"))
    c, z = (res[k][2][37 * len(FCBS):] for k in ("cf", "zb"))
    ok &= c == z
    print(f"  {'PASS' if c == z else 'FAIL'}  DTA afterwards: CF {c[:48].hex()}..."
          + ("" if c == z else f"\n                    ours {z[:48].hex()}..."))
    # D-DISKCONTRACT gap 9 (2026-11-17): the WHOLE disk image afterwards -- both FAT copies,
    # the root directory, the data area -- not only the entries the rows name. A byte
    # different there is a disk another system would read differently.
    img = {k: res[k][3] for k in ("cf", "zb")}
    g = geometry(img["cf"])
    regions = (("boot", 0, 512), ("FAT 1", 512, g["spf"] * 512),
               ("FAT 2", (1 + g["spf"]) * 512, g["spf"] * 512),
               ("root", g["root"] * 512, g["rsec"] * 512),
               ("data", g["data"] * 512, len(img["cf"]) - g["data"] * 512))
    # EXCUSED, filed D-SLACK (TIER 6): NEWFILE.TMP's records nobody wrote. FDEL freed cluster 5
    # (sector 20), FMAKE + WRRND rec 2 took it; the CF-3300 writes its STALE sector buffer
    # (SECOND.DAT's bytes) around the record, ours reads-modifies-writes the old sector
    # (THIRD.DAT's text): bytes 0..255 and 384..511 of sector 20 (scratchpad/IM_run1.out).
    rootb = img["cf"][g["root"] * 512:(g["root"] + g["rsec"]) * 512]
    nf = next((rootb[i:i + 32] for i in range(0, len(rootb), 32) if rootb[i:i + 11] == b"NEWFILE TMP"),
              None)
    sec = g["data"] + (int.from_bytes(nf[26:28], "little") - 2) * g["spc"] if nf else -1
    slack = set(range(sec * 512, sec * 512 + 256)) | set(range(sec * 512 + 384, (sec + 1) * 512))
    for name, off, n in regions:
        c, z = img["cf"][off:off + n], img["zb"][off:off + n]
        d = [off + i for i in range(min(len(c), len(z)))
             if c[i] != z[i] and off + i not in slack]
        same = not d and len(c) == len(z)
        ok &= same
        print(f"  {'PASS' if same else 'FAIL'}  image {name:5s} (${off:05X}+{n}): "
              + ("same" if same else f"{len(d)} byte(s) differ from ${d[0]:05X}: CF "
                 f"{img['cf'][d[0]:d[0] + 16].hex()} ours {img['zb'][d[0]:d[0] + 16].hex()}"))
    for e in range(4):
        c, z = (res[k][3][g["root"] * 512 + 32 * e:g["root"] * 512 + 32 * e + 32] for k in ("cf", "zb"))
        ok &= c == z
        print(f"  {'PASS' if c == z else 'FAIL'}  root entry {e} afterwards: CF {c.hex()}"
              + ("" if c == z else f"\n                              ours {z.hex()}"))
    print(f"===== bdosf37d-acceptance ({GEOMETRY} KB): {'PASS' if ok else 'FAIL'} =====")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
