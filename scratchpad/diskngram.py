#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Repeated byte runs in build/disk.rom (our own ROM), label boundaries ignored.

For every maximal sequence of MIN bytes or more that occurs at two or more
places (zero fill and the FDC window excluded), print its length, each site
as symbol+offset, and the count -- the D-DISKCARVE third-cut scan, re-runnable.
A repeat is a CANDIDATE: read each site (fall-through, jr reach, a pinned
address inside) before sharing it.

    python3 scratchpad/diskngram.py [MIN]      (default 12)
"""
import bisect, collections, os, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MIN = int(sys.argv[1]) if len(sys.argv) > 1 else 12
rom = open(os.path.join(REPO, "build", "disk.rom"), "rb").read()
sym = []
for line in open(os.path.join(REPO, "build", "disk.sym")):
    p = line.split()
    if len(p) >= 2:
        try:
            sym.append((int(p[-1].rstrip("H").lstrip("$"), 16), p[0].rstrip(":")))
        except ValueError:
            pass
sym = sorted(x for x in sym if 0x4000 <= x[0] < 0x8000 and not x[1].startswith("__"))
addrs = [a for a, _ in sym]


def name(a):
    i = bisect.bisect_right(addrs, a) - 1
    return f"{sym[i][1]}+{a - sym[i][0]}" if i >= 0 else hex(a)


def usable(off):
    a = 0x4000 + off
    return not (0x7F80 <= a <= 0x7FBF)


seen = collections.defaultdict(list)
for i in range(len(rom) - MIN):
    w = rom[i:i + MIN]
    if w.count(0) > MIN // 2 or not usable(i):
        continue
    seen[w].append(i)
# grow each repeated seed to its maximal common length, keep the longest per site set
best = {}
for w, sites in seen.items():
    if len(sites) < 2:
        continue
    n = MIN
    while all(s + n < len(rom) for s in sites) and len({rom[s + n] for s in sites}) == 1:
        n += 1
    key = tuple(sites)
    # drop seeds that are the tail of an earlier one (s-1 also matches)
    if all(s > 0 for s in sites) and len({rom[s - 1] for s in sites}) == 1:
        continue
    best[key] = max(best.get(key, 0), n)
rows = sorted(((n, sites) for sites, n in best.items()), key=lambda r: (-(r[0] * (len(r[1]) - 1)), r[0]))
for n, sites in rows[:40]:
    print(f"{n:3} B x{len(sites)}  saves ~{n * (len(sites) - 1) - 3 * len(sites)} B  "
          + "   ".join(f"${0x4000 + s:04X} {name(0x4000 + s)}" for s in sites))
