#!/usr/bin/env python3
"""D-LSETTM closing demo — one real MSX BASIC program, four machines.

Run AFTER the battery, never beside it.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "probes", "basic"))
import basic_probe_deffn as D

D.SIDES.update({
    "cf3000": dict(machine="National_CF-3000", boot=8.0,
                   reset=("", "SCREEN 0", "NEW")),
})

PROG = [
    'A$="12345"',
    'LSET A$="AB"',           # the padding store: disk pads, cassette refuses
    'RSET B$=5',              # the RHS decline, "something and not a string"
]
D.CASES.update({
    'demo.pad':  (['A$="12345"', 'LSET A$="AB"'], 'A$+"|";LEN(A$)'),
    'demo.type': (['A$="12345"', 'LSET A$=5'],    '"no error"'),
    'demo.miss': (['A$="12345"', 'LSET A$='],     '"no error"'),
})
ORDER = ['demo.pad', 'demo.type', 'demo.miss']
sides = (sys.argv[1] if len(sys.argv) > 1 else "vg8020,cf3000,cf3300,zb").split(",")
res = {s: D.run_side(s, ORDER) for s in sides}
w = max(len(l) for l in ORDER)
print(f"\n{'row':<{w}}  " + "  ".join(f"{s:>18}" for s in sides))
print("-" * (w + 2 + 20 * len(sides)))
for l in ORDER:
    print(f"{l:<{w}}  " + "  ".join(f"{res[s][l]:>18}" for s in sides))
