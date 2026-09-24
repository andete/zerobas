#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Carve scout, route C: main PAGE-1 code that could move into a sub PAGE-1
tenant (which may reach main's low region, the BIOS and RAM -- never main
page 1; tools/check_tenant_closure.py). For each page-1 label, its closure under
references INTO page 1; the closure moves whole, and every closure member that
something OUTSIDE references keeps a ~7 B stub in main (`ld ix,<slot>` + `jp
subrom_call`). Net = closure bytes - 7 * outside entries.
A RANKING, not a price: CALSLT clobbers IX and cannot carry a flag back, and
data/ISR/trap-context code has constraints this cannot see. Read the top rows.
"""
import os, re, sys, collections
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STUB = 7

def syms():
    d = {}
    for l in open(os.path.join(ROOT, "build", "basic-reloc.sym")):
        p = l.split()
        if len(p) >= 3 and p[1].upper() == "EQU":
            d[p[0]] = int(p[2].rstrip("Hh"), 16)
    return d

def main_lines():
    seen, out = set(), []
    def walk(rel):
        p = os.path.join(ROOT, rel)
        if rel in seen or not os.path.exists(p):
            return
        seen.add(rel)
        for n, raw in enumerate(open(p, errors="replace"), 1):
            code = raw.split(";")[0].rstrip()
            m = re.match(r'\s*include\s+"([^"]+)"', code)
            if m:
                walk(m.group(1)); continue
            out.append((rel, n, code))
    walk("basic/main.asm")
    return out

def main():
    S = syms()
    p1 = {k: v for k, v in S.items() if 0x4000 <= v < 0x8000}
    lines = main_lines()
    labels_in_order, blocks, cur = [], collections.defaultdict(list), None
    for rel, n, code in lines:
        m = re.match(r"^([A-Za-z_][\w]*):?(\s|$)", code)
        if m and not re.match(r"^[A-Za-z_]\w*\s*:?\s+equ\b", code, re.I) and m.group(1) in p1:
            cur = m.group(1); labels_in_order.append(cur)
            code = code[m.end(1):].lstrip(":")
        if cur and code.strip():
            blocks[cur].append(code.strip())
    addrs = sorted(set(p1.values()))
    nxt = {a: (addrs[i + 1] if i + 1 < len(addrs) else 0x8000) for i, a in enumerate(addrs)}
    size = {k: nxt[p1[k]] - p1[k] for k in labels_in_order}
    TERM = re.compile(r"^(jp|jr)\s+[^,(]+$|^ret$|^jp\s*\((hl|ix|iy)\)$", re.I)
    edges = collections.defaultdict(set)
    for i, k in enumerate(labels_in_order):
        for ins in blocks[k]:
            for tok in re.findall(r"[A-Za-z_]\w*", ins):
                if tok in p1 and tok != k:
                    edges[k].add(tok)
        body = [x for x in blocks[k] if not re.match(r"^(db|dw|ds|defs|defb|defw)\b", x, re.I)]
        if not (body and TERM.match(body[-1])) and i + 1 < len(labels_in_order):
            edges[k].add(labels_in_order[i + 1])
    rev = collections.defaultdict(set)
    for a, bs in edges.items():
        for b in bs:
            rev[b].add(a)
    # external references from NON-page-1 code (low region, data) count as entries too
    rows, seenc = [], set()
    for s in labels_in_order:
        C, st = set(), [s]
        while st:
            x = st.pop()
            if x in C: continue
            C.add(x); st += edges.get(x, ())
            if len(C) > 400: break
        if len(C) > 400: continue
        key = frozenset(C)
        if key in seenc: continue
        seenc.add(key)
        entries = {c for c in C if any(r not in C for r in rev.get(c, ()))}
        byt = sum(size.get(c, 0) for c in C)
        rows.append((byt - STUB * max(1, len(entries)), byt, len(C), len(entries), s))
    rows.sort(reverse=True)
    print(f"page-1 labels: {len(labels_in_order)}  closures scored: {len(rows)}")
    print(f"{'net':>5} {'bytes':>5} {'lbls':>4} {'entr':>4}  seed")
    only = sys.argv[1] if len(sys.argv) > 1 else None
    rows = [r for r in rows if not only or re.match(only, r[4])]
    for r in rows[:30]:
        print(f"{r[0]:5} {r[1]:5} {r[2]:4} {r[3]:4}  {r[4]}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
