#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-WSZERO compaction planner: pack what is left of zerobas's window state
against the top, so TXTMAX_NODISK can rise by the total of the holes.

Reads tools/ram_map.py's resolved maps of BOTH components (source only, as
ws_shift does) over [TXTMAX_NODISK, $F380). A cell occupies [a, a + width); a
cell with no trusted width is taken to run to the next name (conservative). The
occupied ISLANDS are printed bottom to top with the hole under each, then a
plan: every island slides up to sit directly under the next one's NEW start
(top island against RESERVED_TOP), so internal layout -- unions, contiguity
asserts, offsets into a buffer -- is preserved. The plan is ws_shift.py
`--move` arguments; ws_shift is what verifies and applies.

    python3 scratchpad/wszero_compact.py [--reserve LO-HI ...]
"""
import os, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "tools"))
os.chdir(REPO)
import ram_map                                      # noqa: E402

TOP = 0xF380
PACK_TOP = int(next((a.split("=")[1] for a in sys.argv[1:] if a.startswith("--top=")), "F195"), 16)
SKIP = {"FN_STK_FLOOR"}   # dead constant (D-FNPOOL removed its last use)
maps = {c: ram_map.Map(c, 0xE000, TOP, use_sym=False) for c in ("basic", "disk")}
lo = maps["basic"].vals["TXTMAX_NODISK"]
occ = {}                       # address -> names
for c, m in maps.items():
    addrs = [a for a in m.addrs if a >= lo and not m.imported(a)]
    for i, a in enumerate(m.addrs):
        if a < lo or m.imported(a) or set(m.byaddr[a]) <= SKIP:
            continue
        w = m.width.get(a)
        if w is None:
            nxt = next((b for b in m.addrs if b > a), TOP)
            w = nxt - a
        for x in range(a, min(a + w, TOP)):
            occ.setdefault(x, set())
        occ[a].update(f"{c}:{n}" for n in m.byaddr[a])
# reserved spans (C-BIOS's own cells below $F380 on the repack, ...)
for arg in sys.argv[1:]:
    if "-" in arg and not arg.startswith("--"):
        r0, r1 = (int(x, 16) for x in arg.split("-"))
        for x in range(r0, r1 + 1):
            occ.setdefault(x, set()).add("RESERVED")
islands, x = [], lo
while x < TOP:
    if x in occ:
        s = x
        while x < TOP and x in occ:
            x += 1
        islands.append([s, x])
    else:
        x += 1
total = sum(b - a for a, b in islands)
print(f"window [${lo:04X}, ${TOP:04X}) = {TOP - lo} B: {len(islands)} islands, "
      f"{total} B occupied, {TOP - lo - total} B holes")
prev = lo
for a, b in islands:
    names = sorted({n.split(':', 1)[1] for x in range(a, b) for n in occ.get(x, ())})
    print(f"  hole {a - prev:4d} | ${a:04X}-${b - 1:04X} {b - a:4d} B  {' '.join(names[:8])}"
          f"{' ...' if len(names) > 8 else ''}")
    prev = b
print(f"  hole {TOP - prev:4d} (tail)")
# page-constrained blocks: every name code uses in a page idiom (ws_shift's own
# list, with its declared width -- an overlay's demoted claim still counts), plus
# the DEF FN frame, whose same-page rule is a build assert on FN_BASE / FN_BLK.
import ws_shift                                     # noqa: E402
pblocks = []
for c, m in maps.items():
    for n in ws_shift.page_idiom_names():
        v = m.vals.get(n)
        if v is None or not lo <= v < TOP or m.not_a_cell(n):
            continue
        w = m.width.get(v) or (m.overrun.get(v) or (None,))[0]
        if w:
            pblocks.append((v, w, n))
bm = maps["basic"]
pblocks.append((bm.vals["FN_BASE"], bm.vals["FN_PAREA_CEIL"] - bm.vals["FN_BASE"], "FN frame"))   # <= FN_BLK
print("page-constrained blocks: " + ", ".join(f"{n} ${v:04X}+{w}" for v, w, n in sorted(set(pblocks))))


def crosses(a, w):
    return (a >> 8) != ((a + w - 1) >> 8)


# the plan: top-down, each island directly under the next one's new start,
# lowered as far as needed to keep its page-constrained blocks inside one page
moves, ceil = [], PACK_TOP
for a, b in reversed([i for i in islands if i[1] <= PACK_TOP]):
    new_b = ceil
    d = new_b - b
    inside = [(v, w) for v, w, _ in pblocks if a <= v < b]
    while any(crosses(v + d, w) for v, w in inside):
        d -= 1
    if d:
        moves.append((a, b, d))
    ceil = a + d
print(f"\nplan: new ceiling ${ceil:04X} (+{ceil - lo} B); {len(moves)} moves")
for a, b, d in moves:
    print(f"  --move {a:04X} {b:04X} {d:X}   (${a:04X}-${b - 1:04X} up {d} B{'  page-aligned' if d % 256 == 0 else ''})")
