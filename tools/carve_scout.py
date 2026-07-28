#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Carve scout — size a candidate page-1 cluster AND test whether it can legally
become a page-0 sub-ROM tenant. Run this BEFORE writing any eviction code
(subrom-tenant-playbook: "measure + classify BEFORE implementing").

TWO INDEPENDENT QUESTIONS, and conflating them is how a carve gets mis-sized:

  1. HOW MANY BYTES DOES IT BUY?  Attribute by SOURCE FILE, not by call-graph
     closure. A transitive closure is useless for sizing here: the cassette
     program-load path legitimately calls `dispatch_line`, which reaches the
     whole interpreter, so its "closure" is ~the entire ROM. What actually
     leaves page 1 is *the routines defined in the files you move*.

  2. IS IT LEGAL?  A page-0 tenant runs with slot-0 page 0 switched OUT: the
     BIOS (< $2812) and the main low region ($2812-$3FFF) are NOT THERE. Main
     page 1 stays mapped, so calling into it is fine -- BUT THE WALK MUST
     CONTINUE THROUGH IT. If a main page-1 callee itself calls the low region,
     the tenant crashes just the same, because the slot config persists across
     that call. This is the check that decides viability, and it is transitive.

`--why LABEL` prints the shortest path from the cluster to a given escape, which
is how you tell a fatal dependency from one you can re-express sub-side.

Usage:

    # size: what leaves page 1 if these files move
    python3 tools/carve_scout.py build/basic-reloc.sym --files basic/cload.asm

    # legality: can these entry points run as a page-0 tenant?
    python3 tools/carve_scout.py build/basic-reloc.sym --entries do_cload,do_tape_prog

    python3 tools/carve_scout.py build/basic-reloc.sym --entries do_cload --why subrom_call

Escapes named by `--plumbing` are reported separately as re-expressible: they are
the tenant ABI itself (`subrom_call`, `subrom_absent_error`, `vars_reset`), which
a tenant does not need because it IS the sub-ROM. Everything else is a BLOCKER.
NOTE the distinction that matters: plumbing reached DIRECTLY from cluster code is
re-expressible; plumbing reached THROUGH a main page-1 routine you are NOT moving
is NOT -- you cannot rewrite `tokenise`'s call to `subrom_call` from the sub side.
The report separates these.
"""
from __future__ import annotations
import argparse
import glob
import os
import re
import sys
from collections import deque

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_tenant_closure import build_callgraph, load_syms  # noqa: E402

PAGE1 = 0x4000
LOWREGION = 0x2812
DEFAULT_PLUMBING = ("subrom_call", "subrom_absent_error", "vars_reset")
_LBL = re.compile(r'^([A-Za-z_]\w*):')


def labels_in(files):
    """Labels DEFINED in these source files -> the set that physically moves."""
    out = set()
    for f in files:
        for ln in open(f):
            m = _LBL.match(ln.split(';', 1)[0])
            if m:
                out.add(m.group(1))
    return out


def sizes_by_symbol(syms):
    """label -> byte span (distance to the next symbol in address order). Same
    accounting `make basic-reloc` reports the wall in."""
    ordered = sorted((v, k) for k, v in syms.items())
    return {name: (ordered[i + 1][0] - addr if i + 1 < len(ordered) else 0)
            for i, (addr, name) in enumerate(ordered)}


def reachable(graph, seeds):
    out, work = set(), list(seeds)
    while work:
        n = work.pop()
        if n in out:
            continue
        out.add(n)
        work.extend(graph.get(n, ()))
    return out


def shortest_path(graph, seeds, dst):
    q = deque([[s] for s in seeds])
    seen = set(seeds)
    while q:
        p = q.popleft()
        for n in graph.get(p[-1], ()):
            if n == dst:
                return p + [n]
            if n not in seen:
                seen.add(n)
                q.append(p + [n])
    return None


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("sym", help="build/basic-reloc.sym")
    ap.add_argument("--files", help="comma-separated source files to size (question 1)")
    ap.add_argument("--entries", help="comma-separated entry labels to vet (question 2)")
    ap.add_argument("--why", help="print the shortest path from the cluster to this label")
    ap.add_argument("--sources", default="basic/*.asm", help="main call-graph glob")
    ap.add_argument("--plumbing", default=",".join(DEFAULT_PLUMBING))
    ap.add_argument("--members", action="store_true", help="list moved labels, largest first")
    ap.add_argument("--census", action="store_true",
                    help="with --files: split the file into SHARED service routines "
                         "(called from outside it, so they must stay resident) and the "
                         "PRIVATE verb (the actually-movable part)")
    args = ap.parse_args()

    syms = load_syms(args.sym)
    graph = build_callgraph(sorted(glob.glob(args.sources)))
    span = sizes_by_symbol(syms)
    plumbing = {s for s in args.plumbing.split(",") if s}

    moved = set()
    if args.files:
        files = args.files.split(",")
        moved = labels_in(files)
        in_p1 = {n for n in moved if n in syms and PAGE1 <= syms[n] < 0x8000}
        total = sum(span.get(n, 0) for n in in_p1)
        print(f"=== size: {', '.join(files)}")
        print(f"    {len(moved)} labels defined, {len(in_p1)} in page 1")
        print(f"    **{total} B leaves page 1** if the file moves")
        if args.members:
            for n in sorted(in_p1, key=lambda x: -span.get(x, 0))[:25]:
                print(f"      {span.get(n,0):5} B  {n} @ ${syms[n]:04X}")
        if args.census:
            # A file usually hosts BOTH a verb and shared service routines. Only the
            # verb moves: anything called from OUTSIDE the file must stay resident for
            # those callers. Sizing without this split is how the same carve measured
            # 470 B and 381 B -- see docs/spec-traps-t3-key.md §7.6.
            callers = {}
            for src, tgts in graph.items():
                if src in moved:
                    continue
                for t in tgts:
                    if t in in_p1:
                        callers.setdefault(t, set()).add(src)
            shared = sorted(callers, key=lambda n: -len(callers[n]))
            priv = in_p1 - set(shared)
            print(f"\n    SHARED (called from outside -- must stay resident): "
                  f"{sum(span.get(n,0) for n in shared)} B")
            for n in shared:
                cs = sorted(callers[n])
                print(f"      {span.get(n,0):5} B  {n:22} {len(cs):3} ext callers"
                      f"  e.g. {', '.join(cs[:3])}")
            print(f"    PRIVATE (the movable verb): "
                  f"**{sum(span.get(n,0) for n in priv)} B** in {len(priv)} labels")
            print("      note: an entry point with exactly one external caller is the "
                  "verb's own\n            entry -- that caller becomes the tenant stub, "
                  "so it moves WITH the verb.")
        print()

    if not args.entries:
        return 0

    entries = args.entries.split(",")
    closure = reachable(graph, entries)
    # ⚠️ BOTH regions are absent while a page-0 tenant runs, so BOTH are escapes.
    # This used to compute `bios` separately, PRINT it, and then leave it out of
    # the verdict -- so a routine with BIOS callees and no low-region ones was
    # graded "page-0-tenant CLEAN". `do_bload` (7 BIOS callees) and
    # try_init_slot (2) both passed that way, and promoting either on that
    # verdict would have shipped a tenant that jumps into a BIOS that is not
    # mapped. check_tenant_closure.py -- the invariant the BUILD enforces --
    # always checked both ("No low-region/BIOS escape"); the scout that decides
    # what to attempt was the looser of the two, which is the wrong way round.
    escapes = sorted(n for n in closure if n in syms and syms[n] < PAGE1)
    bios = sorted(n for n in closure if n in syms and syms[n] < LOWREGION)

    # Direct = reachable without leaving the code being moved. Those calls can be
    # rewritten sub-side -- a low-region call by re-expressing it, a BIOS call by
    # going through CALSLT the way sub/format.asm already does (at a cost, so a
    # direct BIOS escape is a PRICE, not a free pass). Indirect = only reachable
    # THROUGH main page-1 code that stays resident -- unrewritable, hence fatal.
    inner = reachable({k: v for k, v in graph.items() if k in moved or k in entries},
                      entries) if moved else set(entries)
    direct = [n for n in escapes if any(n in graph.get(m, ()) for m in inner)]
    indirect = [n for n in escapes if n not in direct]

    print(f"=== page-0-tenant legality: {', '.join(entries)}")
    print(f"    closure {len(closure)} labels; "
          f"{len(escapes)} absent-region callees ({len(bios)} of them BIOS)")
    print(f"    directly called by the moved code : {len(direct)}"
          f" ({sum(1 for n in direct if n in plumbing)} plumbing, re-expressible)")
    for n in sorted(direct):
        tag = "plumbing" if n in plumbing else ("CALSLT" if n in bios else "BLOCKER")
        print(f"        {tag:9} {n} @ ${syms[n]:04X}")
    print(f"    reached THROUGH resident main page-1 : {len(indirect)}  <- FATAL if > 0")
    for n in sorted(indirect)[:12]:
        p = shortest_path(graph, entries, n)
        print(f"        {n} @ ${syms[n]:04X}   via {' -> '.join(p[:5])}"
              + (" ..." if p and len(p) > 5 else ""))
    if len(indirect) > 12:
        print(f"        ... and {len(indirect)-12} more")

    verdict = "NOT page-0-evictable" if indirect else "page-0-tenant CLEAN"
    print(f"    VERDICT: {verdict}")

    if args.why:
        p = shortest_path(graph, entries, args.why)
        print(f"\n    why {args.why}: {' -> '.join(p) if p else 'unreachable'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
