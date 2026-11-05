#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-TRAPNEVERON, measure first (2026-11-05): does `INTERVAL STOP` on an interval
that was NEVER turned on latch an event?

Found while building trapstmt-acceptance: with `ON INTERVAL=50 GOSUB 100:INTERVAL
STOP` (no INTERVAL ON before it) and 120 frames waited, the VG-8020's handler had
not run by the end of the next line; zerobas's ran at once. H=-1 = never ran.
Rows: `stop` (never ON, then STOP), `on` (ON, then STOP: the latching control),
`off` (ON, OFF, STOP). Our own programs, typed in, the screen read.

    python3 -u scratchpad/trapneveron_probe.py [MACHINE...]
"""
import os, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

ARM = {"stop": "INTERVAL STOP", "on": "INTERVAL ON:INTERVAL STOP",
       "off": "INTERVAL ON:INTERVAL OFF:INTERVAL STOP"}
MACHINES = ["Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK"]

for m in sys.argv[1:] or MACHINES:
    for name, arm in ARM.items():
        lines = [f"10 ON INTERVAL=50 GOSUB 100:{arm}:T=TIME:H=-1",
                 "20 IF TIME-T<120 THEN 20",
                 "30 A=0:INTERVAL ON:A=1:A=2:B=A",
                 '40 PRINT "<";H;B;">":END',
                 "100 H=A:INTERVAL OFF:RETURN", "RUN"]
        scr = omsx_repl.run_cases(m, [("direct", lines)], batch=False, boot=14.0,
                                  reset=("SCREEN 0:WIDTH 40", "NEW"), step=4.0,
                                  run_gap=6.0)[0]
        rows = [scr[i:i + 40].rstrip() for i in range(0, len(scr or ""), 40)]
        if "RUN" in rows:
            k = len(rows) - 1 - rows[::-1].index("RUN")
            rows = rows[k + 1:]
        out = " | ".join(r for r in rows if r.strip() and r.strip() not in ("Ok", "ZB")
                         and "color" not in r) or "<NO OUTPUT>"
        print(f"{m:30s} {name:5s} [{out}]", flush=True)
print(__import__("probe_refcache").summary())
