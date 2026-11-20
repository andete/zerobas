#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-TRGFLGISR: TRGFLG ($F3E8) as each machine's interrupt leaves it -- idle, and with the
space bar held (matrix row 8, bit 0). Black box: a BASIC PEEK of the published cell after a
delay loop, so several key scans have run. No ROM byte is read.
    python3 -u scratchpad/trgflg_probe.py > scratchpad/TRGFLG_run3.out"""
import os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl, probe_sides  # noqa: E402

PROG = ["10 FOR I=1 TO " + ("3000" if "space" in sys.argv[1:] else "400") + ":NEXT", "20 PRINT \"T=\";PEEK(&HF3E8)", "RUN"]
CASES = [(n, h) for n, h in [("idle", None), ("space", (8, 0x01))] if n in (sys.argv[1:] or ["idle", "space"])]
for side in ("vg8020", "cf3300", "zb"):
    m = probe_sides.MACHINES[side]
    for name, hold in CASES:
        kw = dict(holds=[hold], hold_lead=0.1, hold_secs=8.0) if hold else {}
        scr = omsx_repl.run_batch(m["machine"], [("direct", PROG)], boot=m["boot"],
                                  reset=m["reset"], **kw)[0] or ""
        v = re.findall(r"T=\s*(\d+)", scr)
        print(f"{side:7} {name:6} TRGFLG = " + (f"${int(v[-1]):02X} ({v[-1]})" if v else "<none>"))
