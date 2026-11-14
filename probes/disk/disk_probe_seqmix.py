#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-SEQMIX (gate: seqmix-acceptance): a SEQWRITE file, and another file read between its
writes, through BASIC's $F37D BDOS.

THE BUG (2026-11-14): the sequential writer kept its partial sector in the ONE shared
buffer between calls and closed from GLOBAL state. With B.DAT open for reading, FMAKE
A.DAT, SEQWRITE A rec0 $11, a read of B, SEQWRITE A rec1 $22, FCLOSE A / B:
  - read = RDBLK: A read back $AA / $22 (B's sector over A's buffered record);
  - read = SEQREAD: A came back EMPTY and B.DAT's entry carried A's size and cluster.
The CF-3300 (scratchpad/seqmix_probe.py -> seqmix_run1.out .. run3.out, 2026-11-14) reads
A as $11 / $22 with 2 records at cluster 5, and B untouched: 4 records at cluster 4, $AA.
Those values are pinned below; this gate runs zerobas only, both read shapes.

Black box: a BASIC program (AUTOEXEC.BAS on a copy of disk/empty720.dsk) calls $F37D
through a 31-byte USR stub and stores each call's registers, its FCB and DTA[0] in RAM;
the emulator's debugger reads that RAM back. No ROM byte is read.

Exit 0 every row as the CF-3300; 1 a difference; 2 no reading (the program did not finish).
"""
import os
import shutil
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_preflight  # noqa: E402

MACHINE = os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")
OPENMSX = shutil.which("openmsx") or "/opt/homebrew/bin/openmsx"
FCBA, FCBB, DTA = 0xC020, 0xC060, 0xD400
NONE = 256
REC = 50
# The USR stub: A = ($C0F0) -> C, DE = ($C0F2), HL = ($C0F4), CALL $F37D, then HL / DE /
# BC / AF stored at $C0FA.. / $C0F6 (the caller of scratchpad/bdosset_probe.py).
MC = [0x3A, 0xF0, 0xC0, 0x4F, 0xED, 0x5B, 0xF2, 0xC0, 0x2A, 0xF4, 0xC0, 0xCD, 0x7D,
      0xF3, 0x22, 0xFA, 0xC0, 0xED, 0x53, 0xFC, 0xC0, 0xED, 0x43, 0xFE, 0xC0, 0xF5,
      0xE1, 0x22, 0xF6, 0xC0, 0xC9]


def rows(read):
    """(function, HL, DTA fill or NONE, name the FCB first, RS or -1, RR or -1, FCB 0=A 1=B, what)"""
    rd = ((0x14, 0, 0xEE, 0, -1, -1, 1, "SEQREAD B") if read == "seqread"
          else (0x27, 1, 0xEE, 0, 128, 0, 1, "RDBLK B RR0"))
    r = [
        (0x1A, 0, NONE, 0, -1, -1, 0, "SETDTA"),
        (0x16, 0, NONE, 1, -1, -1, 1, "FMAKE B"),
        (0x15, 0, 0xAA, 0, -1, -1, 1, "SEQWRITE B 0"),
        (0x15, 0, 0xAA, 0, -1, -1, 1, "SEQWRITE B 1"),
        (0x15, 0, 0xAA, 0, -1, -1, 1, "SEQWRITE B 2"),
        (0x15, 0, 0xAA, 0, -1, -1, 1, "SEQWRITE B 3"),
        (0x10, 0, NONE, 0, -1, -1, 1, "FCLOSE B"),
        (0x0F, 0, NONE, 1, -1, -1, 1, "FOPEN B"),
        (0x16, 0, NONE, 1, -1, -1, 0, "FMAKE A"),
        (0x15, 0, 0x11, 0, -1, -1, 0, "SEQWRITE A 0"),
        rd,
        (0x15, 0, 0x22, 0, -1, -1, 0, "SEQWRITE A 1"),
        (0x10, 0, NONE, 0, -1, -1, 0, "FCLOSE A"),
        (0x10, 0, NONE, 0, -1, -1, 1, "FCLOSE B"),
        (0x0F, 0, NONE, 1, -1, -1, 0, "FOPEN A"),
        (0x21, 0, 0xEE, 0, 128, 0, 0, "RDRND A RR0"),
        (0x21, 0, 0xEE, 0, 128, 1, 0, "RDRND A RR1"),
        (0x10, 0, NONE, 0, -1, -1, 0, "FCLOSE A"),
        (0x0F, 0, NONE, 1, -1, -1, 1, "FOPEN B"),
        (0x21, 0, 0xEE, 0, 128, 0, 1, "RDRND B RR0"),
    ]
    if read == "close":
        # D-SEQMIX2: the SOURCE closed before the writer's last record (a copy that ends
        # with an EOF mark): B's second FCLOSE moves to right after the read.
        last = max(i for i, x in enumerate(r) if x[7] == "FCLOSE B")
        r = r[:last] + r[last + 1:]
        i = next(i for i, x in enumerate(r) if x[7] == "RDBLK B RR0") + 1
        r = r[:i] + [(0x10, 0, NONE, 0, -1, -1, 1, "FCLOSE B")] + r[i:]
    return r


# The CF-3300's readings (seqmix_run3.out / seqmix_fix_*.out / seqmix_close3.out, all three
# shapes alike): the LAST row of that label -> (A register, FCB +16..19 size, FCB +26..27 first
# cluster, DTA[0]); None = not checked.
EXPECT = {
    "FOPEN A": (0x00, 0x100, 5, None),       # 2 records, cluster 5
    "RDRND A RR0": (0x00, None, None, 0x11),
    "RDRND A RR1": (0x00, None, None, 0x22),
    "FOPEN B": (0x00, 0x200, 4, None),       # its entry untouched: 4 records, cluster 4
    "RDRND B RR0": (0x00, None, None, 0xAA),
}


# D-SEQMIX3: TWO files read alternately by SEQREAD (a merge / compare). The iterator was
# one, and SEQREAD A after FOPEN B read B's records (the CF-3300: A's, scratchpad/
# seqmix_inter1.out). Its own rows and expectations.
INTER = [
    (0x1A, 0, NONE, 0, -1, -1, 0, "SETDTA"),
    (0x16, 0, NONE, 1, -1, -1, 0, "FMAKE A"),
    (0x15, 0, 0x11, 0, -1, -1, 0, "SEQWRITE A 0"),
    (0x15, 0, 0x22, 0, -1, -1, 0, "SEQWRITE A 1"),
    (0x10, 0, NONE, 0, -1, -1, 0, "FCLOSE A"),
    (0x16, 0, NONE, 1, -1, -1, 1, "FMAKE B"),
    (0x15, 0, 0xAA, 0, -1, -1, 1, "SEQWRITE B 0"),
    (0x15, 0, 0xBB, 0, -1, -1, 1, "SEQWRITE B 1"),
    (0x10, 0, NONE, 0, -1, -1, 1, "FCLOSE B"),
    (0x0F, 0, NONE, 1, -1, -1, 0, "FOPEN A"),
    (0x0F, 0, NONE, 1, -1, -1, 1, "FOPEN B"),
    (0x14, 0, 0xEE, 0, -1, -1, 0, "SEQREAD A 0"),
    (0x14, 0, 0xEE, 0, -1, -1, 1, "SEQREAD B 0"),
    (0x14, 0, 0xEE, 0, -1, -1, 0, "SEQREAD A 1"),
    (0x14, 0, 0xEE, 0, -1, -1, 1, "SEQREAD B 1"),
    (0x14, 0, 0xEE, 0, -1, -1, 0, "SEQREAD A 2"),
    (0x10, 0, NONE, 0, -1, -1, 0, "FCLOSE A"),
    (0x10, 0, NONE, 0, -1, -1, 1, "FCLOSE B"),
]
EXPECT_INTER = {
    "SEQREAD A 0": (0x00, None, 4, 0x11),    # A's first cluster stays A's (4)
    "SEQREAD B 0": (0x00, None, 5, 0xAA),
    "SEQREAD A 1": (0x00, None, 4, 0x22),
    "SEQREAD B 1": (0x00, None, 5, 0xBB),
    "SEQREAD A 2": (0x01, None, 4, None),    # end of file
}


def program(rws):
    def name(fcb, n):
        return (f'FOR I=0 TO 36:POKE &H{fcb:X}+I,0:NEXT:N$="{n}":'
                f'FOR I=1 TO 11:POKE &H{fcb:X}+I,ASC(MID$(N$,I,1)):NEXT')
    lines = ["10 CLEAR 200,&HBFFF",
             f"20 FOR I=0 TO {len(MC) - 1}:READ A:POKE &HC000+I,A:NEXT",
             "30 DEFUSR=&HC000",
             f"40 FOR R=0 TO {len(rws) - 1}:READ F,H,V,Z,S,Q,C:D={FCBA}+C*{FCBB - FCBA}",
             f"50 IF Z AND C=0 THEN {name(FCBA, 'A       DAT')}",
             f"55 IF Z AND C=1 THEN {name(FCBB, 'B       DAT')}",
             f"60 IF V<256 THEN FOR I=0 TO 255:POKE &H{DTA:X}+I,V:NEXT",
             "70 IF S>=0 THEN POKE D+14,S:POKE D+15,0",
             "80 IF Q>=0 THEN POKE D+33,Q:POKE D+34,0:POKE D+35,0",
             f"90 IF F=26 THEN D={DTA}",
             "100 POKE &HC0F0,F:POKE &HC0F2,D-INT(D/256)*256:POKE &HC0F3,INT(D/256):"
             "POKE &HC0F4,H-INT(H/256)*256:POKE &HC0F5,INT(H/256)",
             f"110 X=USR(0):B=&HC800+R*{REC}:FOR J=0 TO 9:POKE B+J,PEEK(&HC0F6+J):NEXT",
             f"120 E={FCBA}+C*{FCBB - FCBA}:FOR J=0 TO 36:POKE B+10+J,PEEK(E+J):NEXT:"
             f"POKE B+47,PEEK(&H{DTA:X}):POKE &HC7FF,R",
             "130 NEXT:POKE &HC7FE,165",
             "140 DATA " + ",".join(str(b) for b in MC)]
    for i in range(0, len(rws), 4):
        lines.append(f"{200 + i} DATA " + ",".join(
            f"{f},{h},{v},{z},{s},{q},{c}" for f, h, v, z, s, q, c, _ in rws[i:i + 4]))
    return ("\r\n".join(lines) + "\r\n").encode("ascii") + b"\x1a"


def image(prog):
    """disk/empty720.dsk (720 KB, media $F9: FATs at sectors 1 and 4, root at 7, data at
    14, 2 sectors a cluster) with AUTOEXEC.BAS = prog in clusters 2.."""
    b = bytearray(open(os.path.join(REPO, "disk", "empty720.dsk"), "rb").read())
    assert len(b) == 737280 and b[21] == 0xF9 and b[512] == 0xF9, "empty720.dsk is not 720 KB $F9"
    nclus = -(-len(prog) // 1024)
    for fat in (1, 4):
        o = fat * 512
        for k in range(nclus):
            c = 2 + k
            v = c + 1 if k < nclus - 1 else 0xFFF
            p = o + c * 3 // 2
            if c & 1:
                b[p] = (b[p] & 0x0F) | ((v << 4) & 0xF0)
                b[p + 1] = (v >> 4) & 0xFF
            else:
                b[p] = v & 0xFF
                b[p + 1] = (b[p + 1] & 0xF0) | (v >> 8)
    e = bytearray(32)
    e[0:11] = b"AUTOEXECBAS"
    e[11] = 0x20
    e[24:26] = (0x0821).to_bytes(2, "little")
    e[26:28] = (2).to_bytes(2, "little")
    e[28:32] = len(prog).to_bytes(4, "little")
    root = 7 * 512
    b[root:root + 32] = e
    data = 14 * 512
    b[data:data + nclus * 1024] = prog.ljust(nclus * 1024, b"\0")
    return bytes(b)


def run(img, n):
    td = tempfile.mkdtemp(prefix="seqmix_")
    try:
        dsk = os.path.join(td, "v.dsk")
        open(dsk, "wb").write(img)
        out = os.path.join(td, "m.txt")
        tcl = ("set throttle off\n"
               "after time 300 {\n"
               f"  set f [open {{{out}}} w]\n"
               "  binary scan [debug read_block memory 0xC7FE 2] H* flag\n"
               f"  binary scan [debug read_block memory 0xC800 {REC * n}] H* v\n"
               '  puts $f "$flag $v"\n  close $f\n  exit\n}\n')
        open(os.path.join(td, "s.tcl"), "w").write(tcl)
        subprocess.run(omsx_preflight.guarded([OPENMSX, "-machine", MACHINE, "-diska", dsk,
                       "-command", "set renderer none; set sound_driver null",
                       "-script", os.path.join(td, "s.tcl")]),
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=600)
        if not os.path.exists(out):
            return None, None
        flag, v = open(out).read().split()
        return bytes.fromhex(flag), bytes.fromhex(v)
    finally:
        shutil.rmtree(td, ignore_errors=True)


def main():
    bad = blind = 0
    total = 0
    for read in ("rdblk", "seqread", "close", "interleave"):
        rws = INTER if read == "interleave" else rows(read)
        exp = EXPECT_INTER if read == "interleave" else EXPECT
        flag, v = run(image(program(rws)), len(rws))
        if not flag or flag[0] != 0xA5 or flag[1] != len(rws) - 1:
            print(f"ROW {read} NO READING (done-flag {flag.hex() if flag else None})")
            blind += 1
            continue
        for label, (a_want, size_want, clus_want, dta_want) in exp.items():
            total += 1
            i = max(k for k, x in enumerate(rws) if x[7] == label)
            r = v[REC * i:REC * i + REC]
            fcb = r[10:47]
            got = (r[1], int.from_bytes(fcb[16:20], "little"),
                   int.from_bytes(fcb[26:28], "little"), r[47])
            want = (a_want, size_want, clus_want, dta_want)
            ok = all(w is None or w == g for w, g in zip(want, got))
            bad += not ok
            print(f"ROW {read}:{rws[i][7]:12} A={got[0]:02X} size={got[1]:#06x} clus={got[2]} "
                  f"DTA0={got[3]:02X}  {'SAME' if ok else 'DIVERGES'}  (CF-3300 {want})")
    if blind:
        print(f"\nNO READING on {blind} shape(s)")
        return 2
    print(f"\n{'PASS' if not bad else 'FAIL'}: SEQWRITE with another file read between "
          f"({total - bad}/{total} as the CF-3300)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
