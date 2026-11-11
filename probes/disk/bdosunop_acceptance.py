#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""bdosunop-acceptance (D-BDOSUNOP): FCLOSE ($10) and SEQREAD ($14) through $F37D on FCBs
that were never opened, on the National CF-3300 and on ours.

A BASIC program (AUTOEXEC.BAS, root entry 0) calls $F37D through a USR stub for each row,
on a disk that also holds SECOND.DAT (root entry 1):
  * CLOSE / SEQREAD of a fresh FCB naming NOSUCH.XYZ, then SECOND.DAT -- never opened;
  * OPEN AUTOEXEC.BAS, SEQREAD, CLOSE, CLOSE again, SEQREAD (the control);
  * OPEN NOSUCH.XYZ (fails), CLOSE, SEQREAD.
The CF-3300 closes only an FCB whose root index (+25; 0 when fresh) holds an entry with
the FCB's NAME -- else $FF and nothing written -- and a SEQREAD of a size-0 FCB is end of
file. Ours wrote entry +25 whatever its name: closing a never-opened SECOND.DAT zeroed
AUTOEXEC.BAS's first cluster and size (scratchpad/bdosunop_run3.out).
PASS = every row's A, every FCB's 37 bytes afterwards and root entries 0..1 of the disk
afterwards are the SAME on both machines. Values are printed, not only their agreement.
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
MACHINES = {"cf": "National_CF-3300", "zb": "C-BIOS_MSX1_EU_REPACK_DISK"}
FCBS = {"NO": (0xC020, "NOSUCH  XYZ"), "EX": (0xC0A0, "SECOND  DAT"),
        "OP": (0xC0D0, "AUTOEXECBAS"), "NF": (0xC100, "NOSUCH  XYZ")}
F = {k: v[0] for k, v in FCBS.items()}
ROWS = [(0x1A, 0xD400, "SETDTA $D400"), (0x0D, 0, "DSKRST"),
        (0x10, F["NO"], "CLOSE nosuch, fresh"), (0x14, F["NO"], "SEQRD nosuch, fresh"),
        (0x10, F["EX"], "CLOSE exists, fresh"), (0x14, F["EX"], "SEQRD exists, fresh"),
        (0x0F, F["OP"], "OPEN exists"), (0x14, F["OP"], "SEQRD exists, open"),
        (0x10, F["OP"], "CLOSE exists, open"), (0x10, F["OP"], "CLOSE again"),
        (0x14, F["OP"], "SEQRD after CLOSE"),
        (0x0F, F["NF"], "OPEN nosuch"), (0x10, F["NF"], "CLOSE after fail"),
        (0x14, F["NF"], "SEQRD after fail")]
SCORED = {0x0F, 0x10, 0x14}                   # SETDTA / DSKRST's A is no contract
DUMP = 0xCA00
# USR stub at $C000: C = ($C0F0), DE = ($C0F2), HL = ($C0F4); CALL $F37D; store HL, DE,
# BC at $C0FA / $C0FC / $C0FE and AF at $C0F6
MC = [0x3A, 0xF0, 0xC0, 0x4F, 0xED, 0x5B, 0xF2, 0xC0, 0x2A, 0xF4, 0xC0, 0xCD, 0x7D,
      0xF3, 0x22, 0xFA, 0xC0, 0xED, 0x53, 0xFC, 0xC0, 0xED, 0x43, 0xFE, 0xC0, 0xF5,
      0xE1, 0x22, 0xF6, 0xC0, 0xC9]


def program() -> bytes:
    def fcb(addr, name):
        return (f'FOR I=0 TO 36:POKE &H{addr:X}+I,0:NEXT:N$="{name}":'
                f'FOR I=1 TO 11:POKE &H{addr:X}+I,ASC(MID$(N$,I,1)):NEXT')
    lines = ["10 CLEAR 200,&HBFFF",
             f"20 FOR I=0 TO {len(MC) - 1}:READ A:POKE &HC000+I,A:NEXT"]
    lines += [f"{30 + k} " + fcb(a, n) for k, (a, n) in enumerate(FCBS.values())]
    lines += ["40 DEFUSR=&HC000",
              f"50 FOR R=0 TO {len(ROWS) - 1}:READ F,D",
              "60 POKE &HC0F0,F:POKE &HC0F2,D-INT(D/256)*256:POKE &HC0F3,INT(D/256):"
              "POKE &HC0F4,0:POKE &HC0F5,0",
              "70 X=USR(0):FOR J=0 TO 9:POKE &HC800+R*10+J,PEEK(&HC0F6+J):NEXT:POKE &HC7FF,R",
              "80 NEXT",
              "85 " + ":".join(f"FOR I=0 TO 36:POKE &H{DUMP + 37 * k:X}+I,PEEK(&H{a:X}+I):NEXT"
                               for k, (a, _) in enumerate(FCBS.values())),
              "86 POKE &HC7FE,165",
              "90 DATA " + ",".join(str(b) for b in MC)]
    for i in range(0, len(ROWS), 7):
        lines.append(f"{100 + i} DATA " + ",".join(f"{f},{d}" for f, d, _ in ROWS[i:i + 7]))
    return ("\r\n".join(lines) + "\r\n").encode("ascii") + b"\x1a"


def image() -> bytes:
    path = probe_tmp.tmp("bdosunop_empty.dsk")
    subprocess.run(["python3", os.path.join(REPO, "tools", "make_test_dsk.py"), "--empty", path],
                   check=True, capture_output=True)
    img = bytearray(open(path, "rb").read())
    fat12_add(img, "AUTOEXEC", "BAS", program())       # root entry 0
    fat12_add(img, "SECOND", "DAT", b"HELLO, SECOND FILE\r\n" * 8)   # root entry 1
    return bytes(img)


def run(machine, img):
    td = tempfile.mkdtemp(prefix="bdosunop_", dir=probe_tmp.tmp(""))
    try:
        dsk = os.path.join(td, "v.dsk")
        open(dsk, "wb").write(img)
        out = os.path.join(td, "m.txt")
        tcl = ("set throttle off\nafter time 150 {\n"
               f"  set f [open {{{out}}} w]\n"
               "  binary scan [debug read_block memory 0xC7FE 2] H* flag\n"
               f"  binary scan [debug read_block memory 0xC800 {10 * len(ROWS)}] H* v\n"
               f"  binary scan [debug read_block memory {DUMP} {37 * len(FCBS)}] H* d\n"
               '  puts $f "$flag $v $d"\n  close $f\n  exit\n}\n')
        open(os.path.join(td, "s.tcl"), "w").write(tcl)
        subprocess.run(omsx_preflight.guarded([OMSX, "-machine", machine, "-diska", dsk,
                       "-command", "set renderer none; set sound_driver null",
                       "-script", os.path.join(td, "s.tcl")]),
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=300)
        root = open(dsk, "rb").read()[7 * 512:7 * 512 + 64]
        if not os.path.exists(out):
            return None
        flag, v, d = open(out).read().split()
        return bytes.fromhex(flag), bytes.fromhex(v), bytes.fromhex(d), root
    finally:
        shutil.rmtree(td, ignore_errors=True)


def main() -> int:
    img = image()
    res = {k: run(m, img) for k, m in MACHINES.items()}
    for k, r in res.items():
        if r is None or r[0] != bytes([0xA5, len(ROWS) - 1]):
            print(f"  FAIL  {MACHINES[k]}: the program never finished -- NOTHING WAS MEASURED "
                  f"(flag {r[0].hex() if r else None})")
            print("===== bdosunop-acceptance: FAIL =====")
            return 1
    ok = True
    for i, (f, _d, what) in enumerate(ROWS):
        a = {k: res[k][1][10 * i + 1] for k in res}
        same = a["cf"] == a["zb"] or f not in SCORED
        ok &= same
        print(f"  {'    ' if f not in SCORED else 'PASS' if same else 'FAIL'}  {f:02X} {what:22s} "
              f"A: CF-3300 {a['cf']:02X}  ours {a['zb']:02X}")
    for n, name in enumerate(FCBS):
        c, z = (res[k][2][37 * n:37 * n + 37] for k in ("cf", "zb"))
        ok &= c == z
        print(f"  {'PASS' if c == z else 'FAIL'}  FCB {name} afterwards: +12.. CF-3300 "
              f"{c[12:].hex()}" + ("" if c == z else f"\n                                 ours    {z[12:].hex()}"))
    for e in (0, 1):
        c, z = (res[k][3][32 * e:32 * e + 32] for k in ("cf", "zb"))
        ok &= c == z
        print(f"  {'PASS' if c == z else 'FAIL'}  root entry {e} afterwards: CF-3300 {c.hex()}"
              + ("" if c == z else f"\n                                   ours    {z.hex()}"))
    print(f"===== bdosunop-acceptance: {'PASS' if ok else 'FAIL'} =====")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
