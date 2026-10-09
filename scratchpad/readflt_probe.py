#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-READFLT: does READ into a numeric variable take a non-integer DATA item?
(The READ/DATA engine, basic/readdata-body.inc, parses items with
data_parse_int -- "no float work" per sub/readdata.asm's header.)

Clean-room: typed BASIC in, the text screen out. VG-8020 vs zerobas NODISK.
"""
import os, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                    # noqa: E402

CASES = {
    "frac":  ["10 ON ERROR GOTO 90", "20 DATA 1.5", "30 READ A:PRINT A"],
    "big":   ["10 ON ERROR GOTO 90", "20 DATA 40000", "30 READ A:PRINT A"],
    "exp":   ["10 ON ERROR GOTO 90", "20 DATA 2E3", "30 READ A:PRINT A"],
    "neg":   ["10 ON ERROR GOTO 90", "20 DATA -.25", "30 READ A:PRINT A"],
    "dbl":   ["10 ON ERROR GOTO 90", "20 DATA 1.23456789012", "30 READ A#:PRINT A#"],
    "int":   ["10 ON ERROR GOTO 90", "20 DATA 42", "30 READ A:PRINT A"],
    # D-READFLT round 2 (2026-10-09): the rules a fix must keep
    "intovf": ["10 ON ERROR GOTO 90", "20 DATA 99999", "30 READ A%:PRINT A%"],
    "e99":   ["10 ON ERROR GOTO 90", "20 DATA 1E99", "30 READ A:PRINT A"],
    "junk":  ["10 ON ERROR GOTO 90", "20 DATA 12X", "30 READ A:PRINT A"],
    "quote": ["10 ON ERROR GOTO 90", '20 DATA "5"', "30 READ A:PRINT A"],
    "empty": ["10 ON ERROR GOTO 90", "20 DATA ,7", "30 READ A,B:PRINT A;B"],
    "spaces": ["10 ON ERROR GOTO 90", "20 DATA   1.5  ,2", "30 READ A,B:PRINT A;B"],
    "hex":   ["10 ON ERROR GOTO 90", "20 DATA &H10,&B101", "30 READ A,B:PRINT A;B"],
    "sign":  ["10 ON ERROR GOTO 90", "20 DATA -,.", "30 READ A,B:PRINT A;B"],
    "again": ["10 ON ERROR GOTO 90", "20 DATA HELLO,7", "30 READ A:PRINT A", "40 READ B:PRINT B",
              "50 END", '90 PRINT "ERR";ERR;"IN";ERL:RESUME NEXT'],
    "dbltyp": ["10 ON ERROR GOTO 90", "20 DATA 1.23456789012", "30 READ A!:PRINT A!"],
}
TAIL = ["40 END", '90 PRINT "ERR";ERR;"IN";ERL:END', "RUN"]


def out(scr):
    if scr is None:
        return "<NO CAPTURE>"
    rows = [scr[i:i + 40].rstrip() for i in range(0, len(scr), 40)][:-1]
    if "RUN" in rows:
        rows = rows[rows.index("RUN") + 1:]
    return " | ".join(r for r in rows if r and r not in ("Ok", "ZB"))


def main():
    bad = 0
    only = sys.argv[1:]
    for name, lines in CASES.items():
        if only and name not in only:
            continue
        got = {}
        tail = ["RUN"] if any(x.startswith("90 ") for x in lines) else TAIL
        for side, m in (("VG-8020", "Philips_VG_8020"), ("zerobas", "C-BIOS_MSX1_EU_REPACK_NODISK")):
            scr = omsx_repl.run_cases(m, [("direct", ["NEW"] + lines + tail)], batch=False,
                                      reset=("", "SCREEN 0:WIDTH 40"), step=3.0)[0]
            got[side] = out(scr)
        same = got["VG-8020"] == got["zerobas"]
        bad += not same
        print(f"{'==' if same else '✗ '} {name:5s} VG-8020 [{got['VG-8020']}]  zerobas [{got['zerobas']}]", flush=True)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
