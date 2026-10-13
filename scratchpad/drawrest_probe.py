#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-DRAWSUBVAR, the measurement its entry names first: what does the VG-8020
do with the REST of `=A+1;` and `XA$+D$;`? drawsub_probe.out read both as
`[OK]` there, which says nothing about what was drawn.

Each case draws from a fresh SCREEN 2 and reads pixels with POINT (a BASIC
function, the same on both machines), printed after SCREEN 0:

  plus   A=5:   DRAW"BM50,50R=A+1;"   POINT(55,50) POINT(56,50)
                (R5 ends at x=55; R6 also sets x=56)
  xplus  A$="R2":D$="D2":  DRAW"BM50,60XA$+D$;"   POINT(52,60) POINT(52,62)
                (A$ alone leaves (52,62) clear; A$+D$ sets it)
  abs    A=5:   DRAW"BM50,70R=ABS(A);"   POINT(50,70) POINT(51,70) POINT(55,70)
                (the array element AB(5) = 0 -> R0 sets only x=50; ABS -> R5)

Prediction (2026-10-13): the VG-8020 reads the variable and skips to the `;`
-- plus R5, xplus A$ only, abs R0; zerobas evaluates -- R6, A$+D$, R5.
"""
import os, sys
os.environ.setdefault("ZEROBAS_REFCACHE", "0")
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                   # noqa: E402

MACHINES = ("Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK")
CASES = [
    ("plus", 'A=5', 'DRAW"BM50,50R=A+1;"', "POINT(55,50);POINT(56,50)"),
    ("xplus", 'A$="R2":D$="D2"', 'DRAW"BM50,60XA$+D$;"', "POINT(52,60);POINT(52,62)"),
    ("abs", 'A=5', 'DRAW"BM50,70R=ABS(A);"', "POINT(50,70);POINT(51,70);POINT(55,70)"),
]


def main():
    for m in MACHINES:
        print(f"=== {m}", flush=True)
        for name, setup, draw, pts in CASES:
            prog = ["NEW", "10 ON ERROR GOTO 100", f"20 {setup}",
                    f"30 SCREEN 2:COLOR 15,4:{draw}", f"40 P$=STR$({pts.replace(';', ')+STR$(')})",
                    '50 SCREEN 0:PRINT"["P$"]":END', '100 SCREEN 0:PRINT"[E"ERR"]":END', "RUN"]
            raw = omsx_repl.run_cases(m, [("direct", prog)], batch=False,
                                      reset=("", "SCREEN 0"), run_gap=8.0)[0]
            span = omsx_repl.result_span(raw) if raw else None
            print(f"   {name:6s} {draw:24s} {pts:40s} -> {('[' + span + ']') if span else 'NO READING'}",
                  flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
