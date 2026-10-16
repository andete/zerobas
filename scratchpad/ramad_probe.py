#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-RAMAD (2026-10-16, Buzz Off's reset): the slot cells a program reads to find
its RAM. Buzz Off's code ends up running $8010 with page 2 on slot 0 on zerobas
(an inter-slot call through the RAM helpers, slot 0 where its RAM is slot 3).
At the prompt, PEEK on both machines (work-area RAM only, no ROM byte):
  RAMAD0..3 $F341-$F344, EXPTBL $FCC1-$FCC4, SLTTBL $FCC5-$FCC8, the primary
  slot register through INP(&HA8), and the RAM slot BASIC itself runs in.
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "probes", "lib"))
import omsx_repl

PROG = ["NEW",
        '10 S$="":FOR I=&HF341 TO &HF344:S$=S$+" "+HEX$(PEEK(I)):NEXT:PRINT"[RAMAD";S$;"]"',
        '20 S$="":FOR I=&HFCC1 TO &HFCC4:S$=S$+" "+HEX$(PEEK(I)):NEXT:PRINT"[EXPTBL";S$;"]"',
        '30 S$="":FOR I=&HFCC5 TO &HFCC8:S$=S$+" "+HEX$(PEEK(I)):NEXT:PRINT"[SLTTBL";S$;"]"',
        '40 PRINT"[A8 ";HEX$(INP(&HA8));"]"',
        "RUN"]


def main():
    for m in ("Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK", "C-BIOS_MSX1_EU_REPACK"):
        scr = omsx_repl.run_cases(m, [("direct", PROG)], batch=False,
                                  reset=("", "SCREEN 0:WIDTH 40"), step=3.0, run_gap=10.0)[0]
        r = [scr[i:i + 40].strip() for i in range(0, len(scr), 40)] if scr else ["<NO OUTPUT>"]
        print(f"{m:30} {' | '.join(x for x in r if x.startswith('['))}", flush=True)


if __name__ == "__main__":
    main()
