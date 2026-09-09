#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-DONOTHING3 closing demo — one real BASIC program, four machines.

Run with `--side <name>` so the BEFORE ROM can be measured on its own build.
"""
from __future__ import annotations
import os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl, probe_sides                                     # noqa: E402

PROG = ['10 ON ERROR GOTO 100',
        '20 SET',
        '30 PRINT"ZQ 0 QZ":END',
        '100 PRINT"ZQ";ERR;"QZ":END']
side = sys.argv[sys.argv.index("--side") + 1] if "--side" in sys.argv else "zb"
c = probe_sides.sides(side)[side]
raw = "".join(omsx_repl.run_cases(
    c["machine"], [("direct", list(c["reset"]) + PROG + ["RUN"])],
    batch=False, reset=(), boot=c["boot"], step=4.0, run_gap=10.0,
    cap_gap=4.0, timeout=420.0)[0] or "")
v = [g for g in re.findall(r'ZQ\s*([0-9]+)\s*QZ', raw) if '"' not in g]
print(f"{side:12s} `SET` (bare statement) -> ERR {v[-1] if v else '<none>'}")
