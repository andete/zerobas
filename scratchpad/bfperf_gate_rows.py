#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-BFBYTE -- run JUST the `bfbyte_*` gate rows as a differential.

The knives need to score individual rows by name, and `make graphics-acceptance`
runs 350+ of them. This drives the SAME row definitions -- imported from
`basic_probe_graphics.LINE_CASES`, not copied -- so a row can never drift
between the gate and the knife that is supposed to redden it.

    python3 -u scratchpad/bfperf_gate_rows.py
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
sys.path.insert(0, os.path.join(REPO, "probes", "basic"))

import omsx_repl                                    # noqa: E402
from basic_probe_graphics import (                  # noqa: E402
    LINE_CASES, band_segs, prog, LINIT, REF, ZB)

ROWS = [c for c in LINE_CASES if c[0].startswith("bfbyte_")]


def main() -> int:
    print(f"=== D-BFBYTE gate rows as a differential ({len(ROWS)} rows) ===")
    print(f"    ref={REF}  zb={ZB}\n")
    bad = 0
    for label, ops, xr, yr, col in ROWS:
        segs = band_segs(xr, yr, color=col)
        specs = [("stored", prog([LINIT, ops]))]
        r = omsx_repl.run_cases(REF, specs, batch=False,
                                capture=("vram_segs", segs))[0]
        z = omsx_repl.run_cases(ZB, specs, batch=False,
                                capture=("vram_segs", segs))[0]
        ok = r is not None and r == z
        bad += not ok
        plane = "colour " if col else "pattern"
        print(f"  {'agree' if ok else 'DIFF '} {label:18} {plane}")
        if not ok:
            print(f"        ref={r}")
            print(f"        zb ={z}")
    print(f"\n=== rows where the machines DIFFER: {bad} ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
