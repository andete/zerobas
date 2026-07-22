#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Eviction scout: which resident page-1 code is a CLEAN carve, and how big?

The G6 space work turned up the structural rule worth automating
(docs/spec-basic-graphics-g6.md §8): the two sub-ROM tenancies have
COMPLEMENTARY reach.

  * a PAGE-1 tenant  sees BIOS + the page-0 low region (float pack, subrom glue)
                     but NOT page-1 residents;
  * a PAGE-0 tenant  sees page-1 residents (CALSLT switches only page 0)
                     but NEITHER the BIOS NOR the page-0 low region.

The reach must be judged TRANSITIVELY, which is the trap: `eval` is page-1
resident, so a page-0 tenant may call it -- but eval itself calls the float pack
at $34xx, which IS page 0 and is the sub-ROM while the tenant runs. So any
candidate whose closure reaches eval is NOT page-0-carvable. Judging by direct
callees alone says the opposite, which is exactly the kind of plausible-but-wrong
answer this arc keeps getting burned by.

So, per candidate entry point R:

  CARVE   = the page-1 labels reachable from R (that is what would move).
  page-1 tenancy is clean iff the carve's outward edges land only on page-0/BIOS
          -- i.e. nothing in the carve calls a page-1 label left behind.
  page-0 tenancy is clean iff the carve's whole closure never touches page 0
          (no BIOS, no low region) -- transitively.
  ENTRIES = labels INSIDE the carve that code OUTSIDE it calls. A clean carve has
          exactly one (R itself); more means the carve needs more than one stub,
          or is not really a unit.

Static and source-based: it reads the asm, resolves labels through the reloc
symbol file, and sizes blocks from real symbol addresses. It cannot see computed
jumps or dispatch tables, so a shortlisted candidate still gets a human read --
but it turns "eyeball every routine" into "read the three the tool shortlists".

    python3 scratchpad/g6_carve_scout.py [min_carve_bytes]
"""
from __future__ import annotations
import glob
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
SYM = os.path.join(REPO, "build", "basic-reloc.sym")

LABEL = re.compile(r"^([A-Za-z_][A-Za-z_0-9]*):")
CALLT = re.compile(r"^\s+(?:call|jp|jr)\s+(?:[a-z]{1,2}\s*,\s*)?([A-Za-z_][A-Za-z_0-9]*)\s*(?:;.*)?$")

PAGE1 = range(0x4000, 0x8000)

# Edges that are RETURNS, not calls, once a routine becomes a tenant: a statement
# body ends by tail-jumping into the interpreter (exec_stmt) or into an error
# raiser, and a tenant does neither -- it returns a status to its resident stub,
# which performs the tail. Following these edges makes the whole call graph reach
# everything (the interpreter reaches the BIOS), which is why an unfiltered
# analysis reports "STRADDLE" for essentially every statement.
CUT = {"exec_stmt", "exec", "raise_error", "stmt_error", "err_mem",
       "gfx_err5", "gfx_absent", "gfx_typeerr", "load_error", "verify_error",
       "subrom_absent_error"}


def load_syms() -> dict[str, int]:
    syms = {}
    for ln in open(SYM):
        m = re.match(r"(\S+)\s+EQU\s+([0-9A-F]+)H", ln.strip())
        if m:
            syms[m.group(1)] = int(m.group(2), 16)
    return syms


def call_graph() -> dict[str, set[str]]:
    g: dict[str, set[str]] = {}
    for f in sorted(glob.glob(os.path.join(REPO, "basic", "*.asm"))):
        cur = None
        for ln in open(f):
            m = LABEL.match(ln)
            if m:
                cur = m.group(1)
                g.setdefault(cur, set())
                continue
            if cur:
                m = CALLT.match(ln.rstrip("\n"))
                if m:
                    g[cur].add(m.group(1))
    return g


def main() -> int:
    min_carve = int(sys.argv[1]) if len(sys.argv) > 1 else 80
    syms = load_syms()
    g = call_graph()
    addrs = sorted(set(v for v in syms.values() if 0x2000 <= v < 0x8200))

    def size_of(name: str) -> int:
        a = syms.get(name)
        if a is None or a not in PAGE1:
            return 0
        nxt = next((x for x in addrs if x > a), None)
        return (nxt - a) if nxt else 0

    def is_p1(name: str) -> bool:
        return syms.get(name, -1) in PAGE1

    rows = []
    carve_of = {}
    for entry in g:
        if not is_p1(entry):
            continue
        # the carve = page-1 labels transitively reachable from the entry
        carve, stack = set(), [entry]
        touches_page0 = set()
        while stack:
            n = stack.pop()
            if n in carve:
                continue
            if is_p1(n):
                carve.add(n)
                stack.extend(t for t in g.get(n, ()) if t not in CUT)
            elif n in syms:
                touches_page0.add(n)          # BIOS or page-0 low region
        size = sum(size_of(n) for n in carve)
        if size < min_carve:
            continue
        # entries: labels inside the carve called from outside it
        entries = {t for src, tgts in g.items() if src not in carve
                   for t in tgts if t in carve}
        rows.append((size, entry, len(carve), touches_page0, entries))
        carve_of[entry] = set(carve)

    import os as _os
    _want = _os.environ.get("SCOUT_ONLY")
    if _want:
        _w = set(_want.split(","))
        rows = [r for r in rows if r[1] in _w]
    rows.sort(key=lambda r: r[0])
    print("=== PAGE-0 TENANCY VIEW: only the ROUTINE ITSELF moves ===")
    print("(a page-0 tenant may keep calling its page-1 callees in place, so the")
    print(" saving is the routine's OWN size; the closure only has to stay off page 0)")
    print(f"{'own':>5}  {'routine':26s}  closure")
    print("-" * 78)
    p0 = [(size_of(e), e, pg0) for (sz, e, nb, pg0, en) in rows]
    for own, e, pg0 in sorted(p0, key=lambda r: -r[0])[:20]:
        print(f"{own:5d}  {e:26s}  {'PAGE-0 CLEAN' if not pg0 else 'reaches ' + ', '.join(sorted(pg0))[:40]}")
    print()
    print(f"{'carve':>6}  {'entry point':26s} {'blks':>4}  verdict")
    print("-" * 92)
    shown = 0
    for size, entry, nblk, page0, entries in rows:
        outside = entries - {entry}
        if page0:
            v0 = f"page-0 NO (reaches {', '.join(sorted(page0))[:34]})"
        else:
            v0 = "page-0 tenant CLEAN"
        # page-1 tenancy: the carve is self-contained by construction (we took the
        # closure), so what matters is how many stubs the leftover callers need
        v1 = f"{len(outside)} extra entr{'y' if len(outside)==1 else 'ies'}" if outside else "single entry"
        print(f"{size:6d}  {entry:26s} {nblk:4d}  {v0}; {v1}")
        if _os.environ.get("SCOUT_MEMBERS"):
            print("          members:", ", ".join(sorted(carve_of[entry])))
            print("          outside entries:", ", ".join(sorted(outside)) or "-")
        shown += 1
        if shown >= 200:
            break
    print("\nA carve is usable when: page-0 CLEAN (or its closure is BIOS/low-only,")
    print("which makes it a page-1 tenant instead) AND it has a single entry.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
