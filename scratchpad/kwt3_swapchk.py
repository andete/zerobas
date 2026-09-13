#!/usr/bin/env python3
"""🔴 A TIER 3 row found `SWAP <num>,<str$>` answering `Illegal function call`
where the reference says `Type mismatch`. Before filing it, separate the three
things it could be: SWAP's TYPE check, the operands being UNDEFINED, or the ORDER
of the two arguments. A row that reads a real defect and a row that reads its own
shape look identical from one cell.
"""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl, probe_sides

CASES = [
    ("undefined num,str", ['SWAP ZQ9,ZQ8$']),
    ("undefined str,num", ['SWAP ZQ8$,ZQ9']),
    ("DEFINED num,str",   ['ZQ9=1:ZQ8$="A"', 'SWAP ZQ9,ZQ8$']),
    ("both numeric (ok)", ['ZQ9=1:ZQ7=2', 'SWAP ZQ9,ZQ7', 'PRINT"[";ZQ9;ZQ7;"]"']),
    ("both string (ok)",  ['ZQ8$="A":ZQ6$="B"', 'SWAP ZQ8$,ZQ6$', 'PRINT"[";ZQ8$;ZQ6$;"]"']),
    ("int vs single",     ['ZQ5%=1:ZQ4!=2', 'SWAP ZQ5%,ZQ4!']),
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
        rows = [r for r in rows if not r.startswith("color")]
        print("   %-20s %s" % (label, " | ".join(rows[-2:])))
        sys.stdout.flush()
