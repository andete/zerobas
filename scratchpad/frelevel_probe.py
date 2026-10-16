#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-FREPLUS14 (2026-10-16): what does FRE(0) lose per level of expression nesting,
inside a GOSUB and inside a FOR, on each machine? The reference counts FRE(0) down
to the live SP; zerobas to a fixed top. Every reading is taken AFTER the variables
it is stored in exist (FRE.md's rule), and printed as a difference from A.
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "probes", "lib"))
import omsx_repl

PROG = [
    "NEW",
    "10 A=0:B=0:C=0:D=0:E=0:F=0:G=0:H=0:I=0:J=0",
    "20 A=FRE(0):B=(FRE(0)):C=((FRE(0))):D=(((FRE(0)))):E=1+FRE(0):F=1*(1+(1+FRE(0)))",
    "30 GOSUB 100:FOR I=1 TO 1:H=FRE(0):NEXT",
    '40 PRINT"[N";A-B;A-C;A-D;A-E+1;A-F+2;"]":PRINT"[S";A;A-G;A-H;"]":END',
    "100 G=FRE(0):RETURN",
    "RUN",
]
for m in ("C-BIOS_MSX1_EU_REPACK_NODISK", "Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_DISK",
          "National_CF-3300"):
    scr = omsx_repl.run_cases(m, [("direct", PROG)], batch=False,
                              reset=("", "SCREEN 0:WIDTH 40"), step=3.0, run_gap=12.0)[0]
    r = [scr[i:i + 40].strip() for i in range(0, len(scr), 40)] if scr else ["<NO OUTPUT>"]
    keep = [x for x in r if x.startswith("[") or "rror" in x]
    print(f"{m:30} {' | '.join(keep) or '<nothing matched>'}", flush=True)
