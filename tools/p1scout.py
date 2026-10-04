#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""PAGE-1-tenancy scout: mirror of carve_scout's page-0 legality question.

A page-1 tenant runs with MAIN PAGE 1 switched OUT and main page 0 (BIOS + the
low region $2765-$3FFF: eval's float bottom, the whole float pack) MAPPED.
So the only fatal escapes are calls to MAIN routines >= $4000 outside the moved
set.  Reports the FRONTIER -- the direct dependencies you must dissolve -- not
the whole transitive tail, which is unreadable and misleading.

  tools/p1scout.py SYM --files a.asm,b.asm [--entries e1,e2] [--extra lbl,lbl]
"""
import sys, os, glob, re, argparse
from collections import deque
sys.path.insert(0, "tools")
from check_tenant_closure import build_callgraph, load_syms

PAGE1 = 0x4000
_LBL = re.compile(r'^([A-Za-z_]\w*):')


def labels_in(files):
    out = set()
    for f in files:
        for ln in open(f):
            m = _LBL.match(ln.split(';', 1)[0])
            if m:
                out.add(m.group(1))
    return out


def sizes_by_symbol(syms):
    ordered = sorted((v, k) for k, v in syms.items())
    return {name: (ordered[i + 1][0] - addr if i + 1 < len(ordered) else 0)
            for i, (addr, name) in enumerate(ordered)}


ap = argparse.ArgumentParser()
ap.add_argument("sym")
ap.add_argument("--files", default="")
ap.add_argument("--entries", default="")
ap.add_argument("--extra", default="", help="extra labels to treat as moved")
a = ap.parse_args()

syms = load_syms(a.sym)
graph = build_callgraph(sorted(glob.glob("basic/*.asm")))
span = sizes_by_symbol(syms)

files = [f for f in a.files.split(",") if f]
moved = labels_in(files) if files else set()
moved |= {x for x in a.extra.split(",") if x}
entries = [e for e in a.entries.split(",") if e]

# grow the moved set: if --entries given, the moved set is the closure of the
# entries RESTRICTED to labels defined in the given files (+extras)
if entries:
    keep, work = set(), list(entries)
    while work:
        n = work.pop()
        if n in keep or n not in moved:
            continue
        keep.add(n)
        work.extend(graph.get(n, ()))
    moved = keep

in_p1 = {n for n in moved if n in syms and PAGE1 <= syms[n] < 0x8000}
frontier = {}
for m in in_p1:
    for t in graph.get(m, ()):
        if t in syms and PAGE1 <= syms[t] < 0x8000 and t not in moved:
            frontier.setdefault(t, set()).add(m)

print(f"=== page-1-tenancy frontier: {a.files} {'entries=' + a.entries if entries else ''}")
print(f"    MOVED: {len(in_p1)} page-1 labels = **{sum(span.get(n,0) for n in in_p1)} B**")
print(f"    DIRECT main-page-1 deps to dissolve: {len(frontier)}")
for t in sorted(frontier, key=lambda x: -span.get(x, 0)):
    cs = sorted(frontier[t])
    print(f"      {span.get(t,0):5} B  {t:24} <- {', '.join(cs[:4])}"
          + (f" (+{len(cs)-4})" if len(cs) > 4 else ""))
