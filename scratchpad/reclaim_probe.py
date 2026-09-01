#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-RECLAIM — the reclaimed 8 KB is really usable, not just really reported.

`FRE(0)` rising from 14767 to 22959 proves an arithmetic change. It does NOT
prove the memory works: a ceiling can be raised over a region that faults, is
overwritten by something unmapped, or is shadowed. So these rows ALLOCATE across
the old ceiling and read the data back.

🎯 THE SEPARATING SIZE IS THE POINT. `DIM A%(9000)` is 18000 B of elements: it
does not fit the OLD 14767 B (ERR 7 there) and does fit the new 22959 B. The
CF-3300 has 23348 B, so it is an AGREEMENT row on the fixed build and an
"Out of memory" on the old one -- the row is the reclaim
[[a-witness-row-can-be-the-divergence]].

🟢 CONTROLS both sides of the boundary: `d.small` must work everywhere (the
apparatus can allocate at all), `d.huge` must fail everywhere (the ceiling still
EXISTS -- a reclaim that removed the bound entirely would pass this and be a bug).
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "probes", "basic"))
import basic_probe_deffn as D                                    # noqa: E402

CASES, ORDER = {}, []
def add(lab, setup, expr):
    CASES[lab] = (setup, expr); ORDER.append(lab)

add('c.fre',    [],                                   'FRE(0)')
# 🟢 the apparatus can allocate and read back at all
add('d.small',  ['DIM A%(1000)', 'A%(1000)=7'],       'A%(1000)')
# inside the OLD ceiling: worked before, must still work
add('d.mid',    ['DIM B%(6000)', 'B%(6000)=11'],      'B%(6000)')
# 🔴 THE RECLAIM ROW: 18000 B of elements -- over the old 14767, under the new
add('d.big',    ['DIM C%(9000)', 'C%(9000)=13'],      'C%(9000)')
# ...and the far end of it, still written and read back
add('d.big0',   ['DIM D%(9000)', 'D%(0)=17'],         'D%(0)')
# 🟢 the ceiling still EXISTS: 30000 B fits nothing here
add('d.huge',   ['DIM E%(15000)'],                    'E%(0)')

D.CASES.update(CASES)
sides = (sys.argv[1] if len(sys.argv) > 1 else "cf3300,zb").split(",")
res = {s: D.run_side(s, ORDER) for s in sides}
w = max(len(l) for l in ORDER)
print(f"{'row':<{w}}  {'setup':<22}  " + "  ".join(f"{s:>14}" for s in sides))
diff = []
for l in ORDER:
    st = CASES[l][0][0] if CASES[l][0] else "(none)"
    cells = [str(res[s].get(l)) for s in sides]
    same = len(set(cells)) == 1
    if not same and l != 'c.fre':
        diff.append(l)
    print(f"{l:<{w}}  {st:<22}  " + "  ".join(f"{c:>14}" for c in cells)
          + ("" if same else "   DIFF"))
print(f"\nDIFF (excluding c.fre, which is a per-machine property): "
      f"{len(diff)}/{len(ORDER)-1}" + ("  " + " ".join(diff) if diff else ""))
raise SystemExit(1 if diff else 0)
