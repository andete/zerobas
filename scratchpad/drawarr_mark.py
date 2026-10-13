#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Does zerobas's DRAW HANG on an array-element substitution (`R=B(1);`)?

drawsub_probe.out read NO READING on zerobas for every array-shaped
substitution, and a 30 s run_gap still showed the machine in SCREEN 2. A blank
capture has been a timing artefact before (TODO: D-PAINTHANG, withdrawn), so
this times the DRAW between two program-written marks (docs/spec-probe-mark.md,
emulated time) with a 120 s budget.

Prediction (2026-10-13): VG-8020 -- both marks, well under a second, for every
case; zerobas -- both marks for `R=A;`, mark 201 and never 202 for `R=B(1);`.
"""
import os, sys
os.environ.setdefault("ZEROBAS_REFCACHE", "0")
_R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [os.path.join(_R, "probes", "lib"), os.path.join(_R, "probes", "basic")]
import omsx_repl                                   # noqa: E402

MACHINES = ("Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK")
CASES = [("var", "R=A;"), ("arr", "R=B(1);"), ("xarr", "XC$(1);")]


def main():
    print(f"{'case':6} {'sub':10} {'machine':30} marks (emulated s)")
    for name, sub in CASES:
        for m in MACHINES:
            body = ["A=5:DIM B(2):B(1)=3:DIM C$(2):C$(1)=\"U2\"", "SCREEN2",
                    "POKE&HC000,201", f'DRAW"BM50,50{sub}"', "POKE&HC000,202", "SCREEN0"]
            so = {}
            omsx_repl.run_case(m, "stored", body, sentinel=(0xC000, 202),
                               sentinel_capture=True, cap_gap=120.0, timeout=600.0,
                               settle_out=so)
            mk = so.get("marks", {}).get(0, [])
            t1 = [t for t, v in mk if v == 201]
            t2 = [t for t, v in mk if v == 202]
            verdict = ("NO MARK AT ALL (instrument?)" if not t1 else
                       f"201 at {t1[0]:.3f}, 202 NEVER (120 s)" if not t2 else
                       f"DRAW took {t2[0] - t1[0]:.3f}")
            print(f"{name:6} {sub:10} {m:30} {verdict}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
