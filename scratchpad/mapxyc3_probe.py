#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-BIOSRUNG (3), PNTINI / SCANR / SCANL's SCREEN 3 rows could not be read: MAPXYC(50,55)
left CLOC at $6DF (paintbios_run5.out). So MAPXYC alone, SCREEN 3 (and SCREEN 2 for scale):
our code calls it for (0,0), (8,0), (0,32) and (50,55) and stores CLOC / CMASK after each.
Black-box: registers and work-area RAM.

    python3 -u scratchpad/mapxyc3_probe.py
"""
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "basic"))
import basic_probe_biosregs as B   # noqa: E402

PTS = ((0, 0), (8, 0), (0, 32), (50, 55))


def code():
    c, dst = [], 0xD100
    for x, y in PTS:
        c += [0x01, x & 255, x >> 8, 0x11, y & 255, y >> 8, 0xCD, 0x11, 0x01,   # MAPXYC
              0x2A, 0x2A, 0xF9, 0x22, dst & 255, dst >> 8,                      # CLOC
              0x3A, 0x2C, 0xF9, 0x32, (dst + 2) & 255, (dst + 2) >> 8]         # CMASK
        dst += 3
    return c + [0xC9]


def prog(scr):
    c = code()
    return ["NEW",
            f"10 CLEAR 200,&HCFFF:SCREEN {scr}",
            f"20 FOR I=0 TO {len(c) - 1}:READ X:POKE &HD000+I,X:NEXT",
            "30 DEFUSR=&HD000:Q=USR(0)",
            '40 SCREEN 0:S$="":FOR I=0 TO 3:S$=S$+" "+HEX$(PEEK(&HD100+3*I)+256*PEEK(&HD101+3*I))+"/"+HEX$(PEEK(&HD102+3*I)):NEXT',
            '50 PRINT"[C";S$;"]"',
            "60 DATA " + ",".join(str(b) for b in c[:42]),   # two lines: one is past the
            "70 DATA " + ",".join(str(b) for b in c[42:]),   # 254-char line buffer
            "RUN"]


ROWS = {"scr2": prog(2), "scr3": prog(3)}


def main():
    for name, p in ROWS.items():
        got = {side: B.read(m, p) for side, m in B.MACHINES}
        print(f"ROW {name} VG=[{got['VG']}] ZB=[{got['ZB']}]", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
