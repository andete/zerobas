#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Standing page-1-escape gate for sub-ROM page-1 tenants (subrom-mathpack arc).

A page-1 tenant (e.g. fp_sqrt) runs with main-ROM PAGE 1 switched OUT. Every
routine in the TRANSITIVE call closure of the resident-ABI surface the tenant
calls MUST therefore live in the page-0 low region (< $4000). If any transitive
callee sits at >= $4000 (page 1), the tenant calls into sub-ROM $FF padding at
runtime -> rst $38 / wild jump / hang. This bit us twice (cmp16_bits @ $4A02,
div10 @ $5233) because the manual leaf-audit only checked DIRECT, in-file
callees. This gate walks the FULL transitive closure across all basic/*.asm and
fails on any page-1 escape.

Seed = the symbols imported in sub/basic-resident-abi.inc (exactly the page-0
entry points the tenant calls). Extends automatically as slice-2 transcendental
tenants add callees to that .inc.

    python3 tools/check_tenant_closure.py build/basic-reloc.sym sub/basic-resident-abi.inc
"""
from __future__ import annotations
import re
import sys
import glob

PAGE1 = 0x4000

_SYM = re.compile(r'^(\S+)\s+EQU\s+([0-9A-Fa-f]+)H', re.IGNORECASE)
_LBL = re.compile(r'^([A-Za-z_]\w*):')
# call/jp/jr/djnz <optional cc,> <label>   (label = symbolic target, not a number)
_XFER = re.compile(
    r'\b(?:call|jp|jr|djnz)\s+(?:(?:nz|z|nc|c|p|m|pe|po)\s*,\s*)?([A-Za-z_]\w*)')
_INC_SYM = re.compile(r'^\s*([A-Za-z_]\w*)\s+equ\b', re.IGNORECASE)


def load_syms(path):
    syms = {}
    for line in open(path):
        m = _SYM.match(line)
        if m:
            syms[m.group(1)] = int(m.group(2), 16)
    return syms


# An unconditional control-flow terminator ends a routine's linear span (code
# past it is NOT reached by fallthrough). ret/reti/retn WITHOUT a condition,
# jp/jr with an unconditional target, and jp (hl/ix/iy).
_COND = ('nz', 'z', 'nc', 'c', 'p', 'm', 'pe', 'po')


def _is_terminator(code: str) -> bool:
    s = code.strip().lower()
    if not s:
        return False
    parts = s.split(None, 1)
    op = parts[0]
    rest = parts[1].strip() if len(parts) > 1 else ""
    if op in ('reti', 'retn'):
        return True
    if op == 'ret':
        return rest == ""                     # `ret` uncond; `ret nz` falls through
    if op in ('jp', 'jr'):
        if rest.startswith('(') or op == 'jp' and rest in ('(hl)', '(ix)', '(iy)'):
            return True
        first = rest.split(',', 1)[0].strip()
        return first not in _COND             # `jp X` uncond; `jp nz,X` falls through
    return False


def build_callgraph():
    """label -> set(transfer targets) using each routine's LINEAR SPAN: from its
    label through any fallthrough into later labels, up to and including the first
    unconditional terminator. This captures call/jp targets that sit past a
    fallthrough into an internal label (how div10 was missed by naive
    nearest-label attribution). Over-attribution across fallthrough is safe (a
    page-1-escape gate must never MISS an edge)."""
    graph = {}
    for f in sorted(glob.glob("basic/*.asm")):
        lines = [ln.split(';', 1)[0] for ln in open(f)]
        labels = []  # (line_index, name)
        for i, code in enumerate(lines):
            m = _LBL.match(code)
            if m:
                labels.append((i, m.group(1)))
                graph.setdefault(m.group(1), set())
        for i, name in labels:
            j = i
            while j < len(lines):
                code = lines[j]
                for x in _XFER.finditer(code):
                    graph[name].add(x.group(1))
                if j > i and _is_terminator(code):
                    break
                j += 1
    return graph


def seeds_from_inc(inc_path):
    return [m.group(1) for line in open(inc_path)
            if (m := _INC_SYM.match(line))]


def main() -> int:
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    syms = load_syms(sys.argv[1])
    graph = build_callgraph()
    seeds = seeds_from_inc(sys.argv[2])
    if not seeds:
        print(f"FAIL: no seed symbols in {sys.argv[2]}", file=sys.stderr)
        return 1

    seen = set()
    stack = list(seeds)
    while stack:
        n = stack.pop()
        if n in seen:
            continue
        seen.add(n)
        stack.extend(c for c in graph.get(n, ()) if c not in seen)

    escapes = sorted((n, syms[n]) for n in seen
                     if n in syms and syms[n] >= PAGE1)
    if escapes:
        print("FAIL: page-1 escapes in the tenant's resident closure — these "
              "routines are switched OUT while the page-1 tenant runs, so "
              "calling them hangs/crashes. Relocate each to the page-0 low "
              "region (see cmp16_bits/div10 in basic/float-arith.asm):",
              file=sys.stderr)
        for n, a in escapes:
            print(f"  {n} = {a:04X}", file=sys.stderr)
        return 1
    print(f"OK: {len(seen)} routines in the resident closure of {len(seeds)} "
          f"ABI seeds, all page-0 (< ${PAGE1:04X}). No page-1 escapes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
