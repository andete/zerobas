#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-ROMSIZE step 2, measure first (Joost 2026-10-14: "measure first how the
VG-8020 stores and reclaims strings"): HOW DOES THE STRING COLLECTOR'S TIME GROW?

zerobas's strheap_gc (sub/strheap.asm) finds every descriptor that points into the
string space, SORTS them by address and moves each string once -- 959 B of the sub
ROM, 282 of them the sort (the 2026-10-20 size measurement). The question that
decides whether a smaller collector is allowed: is the VG-8020's compaction the
same shape, or the classic Microsoft one (rescan for the highest live string, move
it, repeat -- O(n^2) and tiny)? If the reference is quadratic, a quadratic
collector is ON PAR and the sort is bytes spent beating it.

Black box only: TIME ticks (50 Hz) around one FRE(""), which compacts before it
answers (docs/concepts/strings-and-string-space.md). N live 8-byte strings, each
with an 8-byte piece of GARBAGE allocated just before it, so every live string has
to move; the `k.*` rows keep the same N live strings with NO garbage between them,
so nothing moves and only the walk is timed.
    python3 -u scratchpad/gctime_probe.py [vg8020,zb]
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "probes", "basic"))
import basic_probe_deffn as D

CASES, ORDER = {}, []
def add(lab, setup, expr):
    CASES[lab] = (setup, expr); ORDER.append(lab)

NS = (25, 50, 100, 200, 400)
for n in NS:
    # g.N: garbage between the live strings -- every live string moves
    add(f"g.{n:03d}", [f"CLEAR 7200:DIM A$({n})",
                       f"FOR I=1 TO {n}:B$=STRING$(8,66):A$(I)=STRING$(8,65):NEXT:B$=\"\"",
                       'T=TIME:X=FRE(""):T=TIME-T'], 'T')
for n in NS:
    # k.N: the same live strings, no garbage -- the walk without the moves
    add(f"k.{n:03d}", [f"CLEAR 7200:DIM A$({n})",
                       f"FOR I=1 TO {n}:A$(I)=STRING$(8,65):NEXT",
                       'T=TIME:X=FRE(""):T=TIME-T'], 'T')
# control: FRE("") must have reclaimed the garbage -- the answer, both machines
add("c.free", ["CLEAR 7200:DIM A$(100)",
               "FOR I=1 TO 100:B$=STRING$(8,66):A$(I)=STRING$(8,65):NEXT:B$=\"\""],
    'FRE("")')

D.CASES.update(CASES)
sides = (sys.argv[1] if len(sys.argv) > 1 else "vg8020,zb").split(",")
res = {s: D.run_side(s, ORDER) for s in sides}
w = max(len(l) for l in ORDER)
print(f"\n{'row':<{w}}  " + "  ".join(f"{s:>16}" for s in sides) + "   zb/ref")
for l in ORDER:
    vals = [res[s].get(l) for s in sides]
    ratio = ""
    try:
        a, b = float(vals[0]), float(vals[1])
        ratio = f"{b / a:.2f}" if a else "-"
    except (TypeError, ValueError, IndexError):
        pass
    print(f"{l:<{w}}  " + "  ".join(f"{str(v):>16}" for v in vals) + f"   {ratio}")
print("done")
