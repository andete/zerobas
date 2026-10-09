#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-RESNEXTSTMT: RESUME NEXT after an error in the FIRST statement of a
multi-statement line -- does it resume at the next STATEMENT (the reference)
or skip the rest of the line? Found by the numbers concept page's example
(2026-10-09): `90 PRINT 1E62*9:END` trapped, RESUME NEXT skipped the END here.

Each case: 10 ON ERROR GOTO 100 / 20 <stmt>:PRINT "A" / 30 PRINT "B":END /
100 PRINT "E";ERR:RESUME NEXT. The reference should print E<code> A B.

Clean-room: typed BASIC in, the text screen out. VG-8020 vs zerobas NODISK.
"""
import os, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                    # noqa: E402

CASES = {
    "mulovf": "PRINT 1E62*9",
    "asgovf": "X=1E62*9",
    "divzero": "PRINT 1/0",
    "error6": "ERROR 6",
    "sqrneg": "PRINT SQR(-1)",
    "strovf": "PRINT CINT(40000)",
    "undef": "GOTO 999",
}


def rows(scr):
    if scr is None:
        return "<NO CAPTURE>"
    r = [scr[i:i + 40].rstrip() for i in range(0, len(scr), 40)][:-1]
    if "RUN" in r:
        r = r[r.index("RUN") + 1:]
    return " | ".join(x for x in r if x and x not in ("Ok", "ZB"))


def main():
    bad = 0
    for name, stmt in CASES.items():
        lines = ["NEW", "10 ON ERROR GOTO 100", f'20 {stmt}:PRINT "A"', '30 PRINT "B":END',
                 '100 PRINT "E";ERR:RESUME NEXT', "RUN"]
        got = {}
        for side, m in (("VG-8020", "Philips_VG_8020"), ("zerobas", "C-BIOS_MSX1_EU_REPACK_NODISK")):
            scr = omsx_repl.run_cases(m, [("direct", lines)], batch=False,
                                      reset=("", "SCREEN 0:WIDTH 40"), step=3.0)[0]
            got[side] = rows(scr)
        same = got["VG-8020"] == got["zerobas"]
        bad += not same
        print(f"{'==' if same else '✗ '} {name:7s} VG-8020 [{got['VG-8020']}]  zerobas [{got['zerobas']}]", flush=True)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
