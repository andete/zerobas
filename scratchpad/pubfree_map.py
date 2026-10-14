#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-WSZERO: which PUBLISHED work-area cells ($F380-$FFFF) are idle on zerobas.

A static map, the first cut for choosing equate-only homes (a runtime write
census confirms a pick before it ships). For every published name in C-BIOS's
systemvars.asm (the published list, a source file -- no ROM byte is read):
  * its extent: up to the next published name (capped at 512 B);
  * ZB: the zerobas symbols (build/*.sym, every image) whose value falls inside;
  * CB: whether any C-BIOS source other than systemvars.asm names it.
A published variable with no ZB symbol and no CB reference is a CANDIDATE home.
Runs of adjacent candidates print as one block, largest first.

    python3 scratchpad/pubfree_map.py [--all]
"""
import glob, os, re, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CB = os.path.expanduser("~/projects/cbios/src")

pub = []
for line in open(os.path.join(CB, "systemvars.asm")):
    m = re.match(r"^([A-Z][A-Z0-9_]*):?\s+equ\s+\$([0-9A-Fa-f]{4})\b", line)
    if m:
        a = int(m.group(2), 16)
        if 0xF380 <= a <= 0xFFFF:
            pub.append((a, m.group(1)))
pub.sort()
if not pub:
    sys.exit("REFUSE: no published names parsed")

zb = {}
for f in glob.glob(os.path.join(REPO, "build", "*.sym")):
    for line in open(f):
        m = re.match(r"^(\S+)\s+EQU\s+0?([0-9A-F]+)H", line)
        if m:
            v = int(m.group(2), 16)
            if 0xF380 <= v <= 0xFFFF:
                zb.setdefault(v, set()).add(m.group(1))
if len(zb) < 50:
    sys.exit(f"REFUSE: only {len(zb)} zerobas symbols in the published range -- stale or missing build?")

cbsrc = ""
for f in glob.glob(os.path.join(CB, "*.asm")):
    if not f.endswith("systemvars.asm"):
        cbsrc += open(f, errors="replace").read()
cbwords = set(re.findall(r"[A-Z][A-Z0-9_]*", cbsrc))

rows = []
for i, (a, n) in enumerate(pub):
    nxt = pub[i + 1][0] if i + 1 < len(pub) else 0x10000
    size = max(1, min(nxt - a, 512))
    zs = sorted(s for v in range(a, a + size) for s in zb.get(v, ()))
    cb = n in cbwords
    rows.append((a, size, n, zs, cb))

if "--all" in sys.argv:
    for a, size, n, zs, cb in rows:
        print(f"${a:04X} {size:4d} {n:10s} CB={'Y' if cb else '-'} ZB={','.join(zs[:6])}{'...' if len(zs) > 6 else ''}")
    sys.exit(0)

blocks, cur = [], None
for a, size, n, zs, cb in rows:
    free = not zs and not cb
    if free and cur and cur[0] + cur[1] == a:
        cur[1] += size
        cur[2].append(n)
    elif free:
        cur = [a, size, [n]]
        blocks.append(cur)
    else:
        cur = None
print(f"{len(pub)} published names in $F380-$FFFF; {len(zb)} zerobas addresses there; "
      f"{sum(1 for r in rows if not r[3] and not r[4])} names idle on both")
for a, size, names in sorted(blocks, key=lambda b: -b[1]):
    if size >= 4:
        print(f"  {size:4d} B  ${a:04X}-${a + size - 1:04X}  {' '.join(names)}")
