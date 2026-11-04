#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-DEFFNARY, measure first (2026-11-04): what `DEF FNA(C(1))=...` does at the DEF.

Our own program, one case per boot, under ON ERROR:
    10 ON ERROR GOTO 90
    20 <the case>
    30 PRINT "OK":END
    90 PRINT "E";ERR;ERL:END
Typed BASIC in, the screen out.

    python3 -u scratchpad/deffnary_probe.py [MACHINE...]
"""
import os, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

CASES = {"a0": "DEF FNA(C(1))=1",
         "a11": "DEF FNA(C(11))=1",
         "adz": "DEF FNA(C(1/0))=1",
         "avar": "X=20:DEF FNA(C(X))=1",
         "adim": "DEF FNA(C(1))=1:DIM C(5)",
         "astr": "DEF FNA(C$(1))=1:DIM C$(3)",
         "a2d": "DEF FNA(D(1,2))=1:DIM D(3)",
         "acall": "DEF FNA(C(1))=1:PRINT FNA(2)",
         "ctrl": "DEF FNA(X)=X+1:PRINT FNA(2)"}
MACHINES = ["Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK"]


def main():
    for m in sys.argv[1:] or MACHINES:
        for name, d in CASES.items():
            lines = ["10 ON ERROR GOTO 90", f"20 {d}", '30 PRINT "OK":END',
                     '90 PRINT "E";ERR;ERL:END', "RUN"]
            scr = omsx_repl.run_cases(m, [("direct", lines)], batch=False, boot=14.0,
                                      reset=("SCREEN 0:WIDTH 40", "NEW"), step=4.0,
                                      run_gap=6.0)[0]
            rows = [scr[i:i + 40].rstrip() for i in range(0, len(scr or ""), 40)]
            if "RUN" in rows:
                rows = rows[rows.index("RUN") + 1:]
            out = " | ".join(r for r in rows if r.strip() and r.strip() != "Ok") or "<NO OUTPUT>"
            print(f"{m:30s} {name:6s} {d:30s} [{out}]", flush=True)
    print(__import__("probe_refcache").summary())


if __name__ == "__main__":
    main()
