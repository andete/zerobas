#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""The SCREEN for the leaked-trap depth run -- what each machine actually says.

`scratchpad/trapsvc_depth.py` reads counters out of $D000, and on the leaking
case those counters stop being trustworthy: zerobas dies before writing them,
and the VG-8020 row came back with err=115 / done=76, neither of which is a
valid value. A counter block written by a program that did not finish is not a
reading. So this asks the screen instead, which is unambiguous.
"""
import os, sys
ROOT=os.path.abspath(".")
sys.path.insert(0, os.path.join(ROOT,"probes","lib"))
import omsx_repl
J=0xFC9E
prog=['1 ONERRORGOTO900','5 FORZ=0TO11:POKE&HD000+Z,0:NEXT',
 '10 ONINTERVAL=10GOSUB800','20 INTERVALON',
 f'30 H=PEEK(&H{J+1:X}):W=PEEK(&H{J:X})+256*H:IFH<>PEEK(&H{J+1:X})THEN30',
 f'32 H=PEEK(&H{J+1:X}):V=PEEK(&H{J:X})+256*H:IFH<>PEEK(&H{J+1:X})THEN32',
 '34 IFV-W<300THEN32','40 PRINT"[DONE";PEEK(&HD000);"]":END',
 '790 END','800 A=PEEK(&HD000):IFA<250THENPOKE&HD000,A+1','801 INTERVALON','802 GOTO30',
 '900 PRINT"[ERR";ERR;"AT";PEEK(&HD000);"]":END','RUN']
for side,mach,boot,step in (("vg8020","Philips_VG_8020",8.0,3.0),
                            ("zb",os.environ.get("ZEROBAS_BASIC_MACHINE","C-BIOS_MSX1_EU_REPACK_DISK"),8.0,3.0)):
    caps=omsx_repl.run_cases(mach,[("direct",prog)],batch=False,boot=boot,step=step,
                             cap_gap=10.0,timeout=400.0)
    scr=caps[0]
    print(f"=== {side}: captured={scr is not None}")
    if scr:
        C=omsx_repl.COLS
        rows=[scr[r*C:(r+1)*C].rstrip() for r in range(omsx_repl.ROWS)]
        for r in [x for x in rows if x][-8:]: print("   |", r)
