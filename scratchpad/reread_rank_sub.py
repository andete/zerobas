# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-REREAD on the SUB ROM (2026-11-03): its candidate ranking.

Joost, 2026-11-03, on retiring sub2: "let's first optimize a bit more" -- the
space sub2's page-0 tenants need (~2.7 KB short) has to come from the sub ROM
itself. reread_rank.py ranks the MAIN ROM; this is its twin for build/sub.sym:
label-to-label spans of the code labels defined in sub/ sources (and the
basic/*.inc bodies sub/ includes), per island -- page 0 ($0000-$3FFF, the
callable-from-main island) and page 1 ($4000-$7FFF, the BIOS-visible one) --
largest first, minus every routine NAMED in scratchpad/reread_reviewed.md.
A span runs to the next code label, so it can hold a data table: read it.
The ranking rots with every carve: re-run it, never quote it.

    python3 scratchpad/reread_rank_sub.py [--top 40] [--page 0|1]
"""
import argparse
import os
import re

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=40)
    ap.add_argument("--page", type=int, choices=(0, 1))
    a = ap.parse_args()
    sym = {}
    for ln in open(os.path.join(REPO, "build", "sub.sym")):
        m = re.match(r"(\S+)\s+EQU\s+0?([0-9A-Fa-f]+)H", ln)
        if m:
            sym[m.group(1)] = int(m.group(2), 16)
    # the files sub/sub.asm actually assembles, FOLLOWED RECURSIVELY (2026-11-03:
    # the first cut read only sub.asm's own include lines, so every label of a
    # body .inc pulled in by another sub file was missing and one "span" swallowed
    # a whole body -- sd10_skip read as 941 B, all of basic/detok.inc). pasmo
    # resolves a bare name against `-I sub` and the repo root.
    def resolve(name):
        for cand in (name, os.path.join("sub", name)):
            if os.path.exists(os.path.join(REPO, cand)):
                return cand
        return None
    files, todo = [], ["sub/sub.asm"]
    while todo:
        f = todo.pop()
        if f in files:
            continue
        files.append(f)
        text = open(os.path.join(REPO, f), errors="replace").read()
        for name in re.findall(r'^\s*include\s+"([^"]+)"', text, re.M):
            r = resolve(name)
            if r and r.endswith((".asm", ".inc")):
                todo.append(r)
    loc = {}
    for f in sorted(set(files)):
        for i, ln in enumerate(open(os.path.join(REPO, f), errors="replace"), 1):
            m = re.match(r"^([A-Za-z_]\w*):", ln)
            if m and m.group(1) in sym:
                loc.setdefault(m.group(1), f"{f}:{i}")
    if not loc:
        print("NO CODE LABELS MATCHED build/sub.sym -- refusing to rank")
        return 2
    done = open(os.path.join(REPO, "scratchpad", "reread_reviewed.md")).read()
    addrs = sorted((sym[n], n) for n in loc)
    ends = {0: sym.get("__MEAS_SUB_P0_END", 0x4000), 1: sym.get("__MEAS_SUB_P1_END", 0x8000)}
    rows = []
    for i, (ad, n) in enumerate(addrs):
        page = 0 if ad < 0x4000 else 1
        nxt = addrs[i + 1][0] if i + 1 < len(addrs) else ends[page]
        if (nxt < 0x4000) != (ad < 0x4000):
            nxt = ends[page]
        size = nxt - ad
        if size <= 0 or re.search(r"\b%s\b" % re.escape(n), done):
            continue
        if a.page is not None and page != a.page:
            continue
        rows.append((size, page, n, loc[n]))
    rows.sort(reverse=True)
    tot = {0: 0, 1: 0}
    for size, page, *_ in rows:
        tot[page] += size
    print(f"sub ROM code spans not yet reviewed: page 0 {tot[0]} B, page 1 {tot[1]} B "
          f"({len(rows)} routines)")
    print("  size  pg  routine                      where")
    for size, page, n, where in rows[:a.top]:
        print(f"{size:6d}  {page}   {n:28s} {where}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
