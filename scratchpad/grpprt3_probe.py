#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-BIOSRUNG (3), GRPPRT ($008D) in SCREEN 3 -- filed when MAPXYC's SCREEN 3 arm went in
(it follows MAPXYC's CLOC). 'A' printed at GRPACX / GRPACY by a direct call in SCREEN 3;
then GRPACX / GRPACY and a weighted checksum + the nonzero count of pattern bytes
$0000-$02FF (SCREEN 3 block rows 0..23; $05FF timed out), read before SCREEN 0. Black-box: registers,
work-area RAM, VRAM.

    python3 -u scratchpad/grpprt3_probe.py [ROW ...]
"""
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scratchpad"))
sys.path.insert(0, os.path.join(REPO, "probes", "basic"))
import biossweep_probe as S        # noqa: E402  (B with read2)

B = S.B
SHOW = ('S=0:N=0:FOR I=0 TO &H2FF:V=VPEEK(I):S=S+V*(I MOD 97+1):N=N-(V<>0):NEXT:'
        'X=PEEK(&HFCB7)+256*PEEK(&HFCB8):Y=PEEK(&HFCB9)+256*PEEK(&HFCBA):'
        'SCREEN 0:PRINT "[C";S;N;X;Y;"]"')


def row(x, y, ch=0x41, extra=""):
    return B.prog(0x008D, ch, before=f"SCREEN 3:POKE &HFCB7,{x & 255}:POKE &HFCB8,{x >> 8}:"
                                    f"POKE &HFCB9,{y & 255}:POKE &HFCBA,{y >> 8}{extra}",
                  after=SHOW)


def dump(*ranges):
    # one [C line of hex per range (lo, hi inclusive), read before SCREEN 0
    rd = "".join(f'D{i}$="":FOR I=&H{lo:X} TO &H{hi:X}:D{i}$=D{i}$+RIGHT$("0"+HEX$(VPEEK(I)),2):NEXT:'
                 for i, (lo, hi) in enumerate(ranges))
    pr = ":".join(f'PRINT "[C";D{i}$;"]"' for i in range(len(ranges)))
    return rd + "SCREEN 0:" + pr


ROWS = {
    "g3_0_0":    row(0, 0),
    "g3_10_13":  row(10, 13),
    "g3_100_80": row(100, 80),
    "g3_cr":     row(100, 80, 13),    # a control code: CR
    # ROUND 2: the glyph's bytes. 'A' at (0,0): blocks 0..7 x 0..7 = bytes $00-$1F;
    # at (10,13): blocks from (2,3) -- bytes $08-$27 and $108-$127
    "v3_0_0":    B.prog(0x008D, 0x41, before="SCREEN 3:POKE &HFCB7,0:POKE &HFCB8,0:"
                        "POKE &HFCB9,0:POKE &HFCBA,0", after=dump((0x00, 0x0F), (0x10, 0x1F))),
    "v3_10_13":  B.prog(0x008D, 0x41, before="SCREEN 3:POKE &HFCB7,10:POKE &HFCB8,0:"
                        "POKE &HFCB9,13:POKE &HFCBA,0",
                        after=dump((0x08, 0x17), (0x108, 0x117))),
    # ROUND 4: the text modes -- SCREEN 1 (the cursor cells, the name table untouched?)
    "g1_10_13":  B.prog(0x008D, 0x41, before="SCREEN 1:POKE &HFCB7,10:POKE &HFCB8,0:"
                        "POKE &HFCB9,13:POKE &HFCBA,0",
                        after=SHOW.replace("SCREEN 0:", "SCREEN 0:")),
    "g1_cr":     B.prog(0x008D, 13, before="SCREEN 1:POKE &HFCB7,10:POKE &HFCB8,0:"
                        "POKE &HFCB9,13:POKE &HFCBA,0", after=SHOW),
    # ROUND 3: unset font pixels over a non-background block -- bytes $00-$1F VPOKEd $99
    "v3_over":   B.prog(0x008D, 0x41, before="SCREEN 3:POKE &HFCB7,0:POKE &HFCB8,0:"
                        "POKE &HFCB9,0:POKE &HFCBA,0:FOR I=0 TO 31:VPOKE I,&H99:NEXT",
                        after=dump((0x00, 0x0F), (0x10, 0x1F))),
}


def main():
    for name in sys.argv[1:] or list(ROWS):
        got = {side: B.read(m, ROWS[name]) for side, m in B.MACHINES}
        v = "NO-REFERENCE" if not got["VG"] else ("SAME" if got["VG"] == got["ZB"] else "DIVERGES")
        print(f"ROW {name:10} VG=[{got['VG']}] ZB=[{got['ZB']}] {v}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
