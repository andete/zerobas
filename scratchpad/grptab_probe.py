#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-GRPTAB, measure first (2026-11-05): TAB( and SPC( in a PRINT # to GRP:.

Round-5 shape (scratchpad/opengrp5_probe.py): SCREEN 2, OPEN "GRP:", the text
cursor's column CSRX ($F3DD, published) poked to 11 so "counts from CSRX" and
"counts from column 0" read differently; the graphic cursor GRPACX/Y read back
with PEEK (work-area RAM). Typed BASIC in, the screen out. Both machines.

    python3 -u scratchpad/grptab_probe.py [CASE...]
"""
import os, re, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                   # noqa: E402

REF = "Philips_VG_8020"
CUR = '510 X0=PEEK(&HFCB7)+256*PEEK(&HFCB8):Y0=PEEK(&HFCB9)+256*PEEK(&HFCBA):RETURN'
ERR = '90 SCREEN 0:PRINT"<E";ERR;ERL;">":END'
OPEN = ['10 ON ERROR GOTO 90', '20 SCREEN 2', '30 OPEN"GRP:"FOR OUTPUT AS #1']


def out(expr):
    return f'70 SCREEN 0:PRINT"<";{expr};">":END'


CASES = {
    "tab5":   OPEN + ['40 POKE &HF3DD,11:PSET(0,8),4:PRINT #1,"A";TAB(5);"B";:GOSUB 510', out("X0;Y0"), ERR, CUR],
    "tab20":  OPEN + ['40 POKE &HF3DD,11:PSET(0,8),4:PRINT #1,"A";TAB(20);"B";:GOSUB 510', out("X0;Y0"), ERR, CUR],
    "tab0":   OPEN + ['40 PSET(0,8),4:PRINT #1,TAB(5);"B";:GOSUB 510', out("X0;Y0"), ERR, CUR],
    "tabbk":  OPEN + ['40 POKE &HF3DD,11:PSET(0,8),4:PRINT #1,"ABCDEFG";TAB(3);"X";:GOSUB 510', out("X0;Y0"), ERR, CUR],
    "tabx":   OPEN + ['40 POKE &HF3DD,11:PSET(40,8),4:PRINT #1,"A";TAB(5);"B";:GOSUB 510', out("X0;Y0"), ERR, CUR],
    "spc3":   OPEN + ['40 POKE &HF3DD,11:PSET(0,8),4:PRINT #1,"A";SPC(3);"B";:GOSUB 510', out("X0;Y0"), ERR, CUR],
    "tabnl":  OPEN + ['40 POKE &HF3DD,11:PSET(0,8),4:PRINT #1,"A":PRINT #1,TAB(5);"B";:GOSUB 510', out("X0;Y0"), ERR, CUR],
}
RX = re.compile(r"<[^<>]*>")
MACHINES = ["Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK"]


def main():
    only = sys.argv[1:]
    for m in MACHINES:
        for name, lines in CASES.items():
            if only and name not in only:
                continue
            raw = omsx_repl.run_cases(m, [("direct", ["NEW"] + lines + ["RUN"])],
                                      batch=False, reset=("", "SCREEN 0"), run_gap=30.0)[0] or ""
            flat = raw.replace("\n", "")
            run = flat[flat.rfind("RUN") + 3:] if "RUN" in flat else flat
            hits = RX.findall(run)
            print(f"{m[:12]:12s} {name:7s} {re.sub(' +', ' ', hits[-1]) if hits else 'NONE: ' + run[-80:]}",
                  flush=True)
    print(__import__("probe_refcache").summary())
    return 0


if __name__ == "__main__":
    sys.exit(main())
