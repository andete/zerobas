#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-CLEARWRAP, measure first (2026-11-01): CLEAR's fit check sums PRGEND + the
requested string space + 680 in 16 bits with no carry test (a D-REREAD batch 8
reviewer). Does a string space near 32767 get ACCEPTED here where the references
say Out of memory? One boot per case and machine; typed BASIC in, the screen out.
Prints ERR (0 = accepted) and, when accepted, FRE("") afterwards.
"""
import os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl, probe_sides  # noqa: E402

SIDES = probe_sides.sides("vg8020", "cf3300", "zb")
CASES = ["30000", "32000", "32100", "32500", "32767", "200,&HF000"]


def main():
    for n in CASES:
        row = {}
        for side, c in SIDES.items():
            p = ["10 ON ERROR GOTO 900", f"20 CLEAR {n}",
                 '30 PRINT"ZQ";0;",";FRE("");"QZ":END',
                 '900 PRINT"ZQ";ERR;",";-1;"QZ":END']
            raw = "".join(omsx_repl.run_cases(
                c["machine"], [("direct", list(c["reset"]) + p + ["RUN"])],
                batch=False, reset=(), boot=c["boot"], step=4.0, run_gap=10.0,
                cap_gap=4.0, timeout=420.0)[0] or "")
            v = re.findall(r'ZQ\s*(-?[0-9]+)\s*,\s*(-?[0-9]+)\s*QZ', raw)
            row[side] = v[-1] if v else None
        print(f"  CLEAR {n:12s} " + "  ".join(f"{s}={row[s]}" for s in SIDES), flush=True)


if __name__ == "__main__":
    main()
