#!/usr/bin/env python3
"""🔴 The FIRST batch of TIER 3 rows found a divergence: `READ ZV` with no DATA
answers `Out of DATA` on the reference and `Syntax error` on zerobas. Before
filing it, separate the three things it could be — the DIRECT-mode form, the bare
variable, or READ's out-of-data path itself — because a row that reads a real
defect and a row that reads its own shape look identical from one cell.
"""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl, probe_sides

CASES = [
    ("direct, no DATA",      ['READ ZV']),
    ("direct, DATA present", ['10 DATA 7', 'READ ZV', 'PRINT"[";ZV;"]"']),
    ("stored, no DATA",      ['10 READ ZV', '20 PRINT"[";ZV;"]"', 'RUN']),
    ("stored, DATA runs out",['10 DATA 7', '20 READ ZV,ZW', 'RUN']),
    ("stored, DATA enough",  ['10 DATA 7', '20 READ ZV', '30 PRINT"[";ZV;"]"', 'RUN']),
]
for side in ("vg8020", "zb"):
    cfg = probe_sides.sides(side)[side]
    print("=== %s" % side)
    for label, lines in CASES:
        caps = omsx_repl.run_cases(cfg["machine"], [("c", list(cfg["reset"]) + ['NEW'] + lines)],
                                   batch=False, reset=(), boot=cfg["boot"], step=1.0,
                                   cap_gap=6.0, timeout=600.0)
        cap = caps[0]
        rows = [cap[r*40:(r+1)*40].rstrip() for r in range(24)] if cap else []
        rows = [r.strip() for r in rows if r.strip()]
        print("   %-22s %s" % (label, " | ".join(rows[-3:])))
        sys.stdout.flush()
