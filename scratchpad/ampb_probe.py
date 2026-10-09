#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-AMPB: does a `&B` binary literal in program text / direct mode give its
value? zerobas stores `&B` as text and does not evaluate it (basic/PROVENANCE.md
descope); the numbers concept page (2026-10-09) asked what the VG-8020 does.

Clean-room: typed BASIC in, the text screen out. VG-8020 vs zerobas NODISK.
"""
import os, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                    # noqa: E402

CASES = {
    "prog": ["NEW", '10 PRINT "[";&B101;"]"', "20 A=&B11111111:PRINT A", "30 PRINT &B1+1", "RUN"],
    "direct": ['PRINT "[";&B101;"]"'],
    "big": ["NEW", '10 PRINT &B1111111111111111', "RUN"],
}


def rows(scr, start):
    if scr is None:
        return "<NO CAPTURE>"
    r = [scr[i:i + 40].rstrip() for i in range(0, len(scr), 40)][:-1]
    if start in r:
        r = r[r.index(start) + 1:]
    return " | ".join(x for x in r if x and x not in ("Ok", "ZB"))


def main():
    bad = 0
    for name, lines in CASES.items():
        got = {}
        for side, m in (("VG-8020", "Philips_VG_8020"), ("zerobas", "C-BIOS_MSX1_EU_REPACK_NODISK")):
            scr = omsx_repl.run_cases(m, [("direct", lines)], batch=False,
                                      reset=("", "SCREEN 0:WIDTH 40"), step=3.0)[0]
            got[side] = rows(scr, lines[-1])
        same = got["VG-8020"] == got["zerobas"]
        bad += not same
        print(f"{'==' if same else '✗ '} {name:6s} VG-8020 [{got['VG-8020']}]  zerobas [{got['zerobas']}]", flush=True)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
