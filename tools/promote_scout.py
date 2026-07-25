#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Promotion scout — which low-region routines may move UP into main page 1.

The mirror image of carve_scout.py. A carve moves page-1 code OUT to the sub-ROM;
a PROMOTION moves main low-region code ($2812-$3FFF) UP into main page 1
($4000-$7FFF), inside the same assembly. It is the only way a page-1 carve can
fund a LOW-REGION need: free page 1 first, then promote low-region content into
the space (docs/spec-traps-t3-key.md §7.4).

Promotion is nearly free -- same ROM, same slot, ordinary in-slot calls, and the
interpreter is 100% label-based (docs/cbios-repack-ws2-audit.md) -- but it is not
unconditional. Two callers CANNOT see main page 1, so anything they reach is
PINNED to the low region:

  * PAGE-1 SUB-ROM TENANTS. A page-1 tenant runs with main page 1 switched OUT,
    so every main routine it calls back into must stay < $4000. Seeds: the
    resident ABI, sub/basic-resident-abi.inc -- the same seeds
    check_tenant_closure.py's default mode gates on. Promote one of these and
    that gate fails; this tool is what tells you BEFORE you move it.

  * THE $0038 ISR PATH. The interrupt handler can land while a page-1 tenant owns
    page 1, so any main code the ISR reaches must also stay < $4000. htimi_guard
    (basic/subromcall.asm) exists exactly to make this bounded: it SKIPS the frame
    when a tenant is active, so page-1 code downstream of the guard (event_poll
    and friends) is unreachable in that window and is NOT pinned. What IS pinned
    is the guard itself and anything reached BEFORE the skip decision -- plus, for
    a handler that may not skip a frame (the KEY trap's diversion hook, which
    would leak a keystroke), that handler's whole closure.

Everything else in the low region is promotable, and promotion is monotonically
SAFE for page-0 tenants: they see main page 1 but not the low region, so moving a
routine up can only remove a violation, never create one.

Usage:

    # the inventory: promotable low-region routines, per file, largest first
    python3 tools/promote_scout.py build/basic-reloc.sym

    # is a specific cluster promotable, and what does it cost page 1?
    python3 tools/promote_scout.py build/basic-reloc.sym --labels do_dim,ary_find

    # why is this one pinned?
    python3 tools/promote_scout.py build/basic-reloc.sym --why fp_add
"""
from __future__ import annotations
import argparse
import glob
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_tenant_closure import build_callgraph, load_syms  # noqa: E402
from carve_scout import reachable, shortest_path, sizes_by_symbol  # noqa: E402

PAGE1 = 0x4000
LOWREGION = 0x2812
# The ISR-side pins. htimi_guard is the frame-skip decision itself; a trap hook
# that must NOT skip a frame (zkey_isr -- a missed frame leaks an undiverted
# keystroke, docs/spec-traps-t3-key.md §5) is pinned with its whole closure.
DEFAULT_ISR_SEEDS = ("htimi_guard", "zkey_isr", "zkey_hook")
_LBL = re.compile(r'^([A-Za-z_]\w*):')


def labels_by_file(files):
    """label -> defining source file, for attribution in the report."""
    out = {}
    for f in files:
        if not os.path.exists(f):
            continue
        for ln in open(f):
            m = _LBL.match(ln.split(';', 1)[0])
            if m:
                out.setdefault(m.group(1), f)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('sym', help='build/basic-reloc.sym')
    ap.add_argument('--abi', default='sub/basic-resident-abi.inc',
                    help='page-1-tenant resident ABI (the pinning seeds)')
    ap.add_argument('--sources', default='basic/*.asm',
                    help='main call-graph glob')
    ap.add_argument('--isr-seeds', default=','.join(DEFAULT_ISR_SEEDS),
                    help='comma-separated extra pinning seeds on the ISR path')
    ap.add_argument('--labels', help='comma-separated candidate cluster to vet')
    ap.add_argument('--why', help='explain why this label is pinned')
    args = ap.parse_args()

    syms = load_syms(args.sym)
    files = sorted(glob.glob(args.sources))
    graph = build_callgraph(files)
    sizes = sizes_by_symbol(syms)
    owner = labels_by_file(files)

    abi_seeds = sorted(load_syms(args.abi))
    isr_seeds = [s for s in args.isr_seeds.split(',') if s and s in graph]
    pinned = reachable(graph, abi_seeds) | reachable(graph, isr_seeds)

    def is_low(lbl):
        a = syms.get(lbl)
        return a is not None and LOWREGION <= a < PAGE1

    if args.why:
        lbl = args.why
        if lbl not in pinned:
            print(f"{lbl}: NOT pinned — promotable "
                  f"({'low region' if is_low(lbl) else 'not in the low region'})")
            return 0
        for name, seeds in (("page-1 tenant ABI", abi_seeds), ("ISR path", isr_seeds)):
            p = shortest_path(graph, seeds, lbl)
            if p or lbl in seeds:
                print(f"{lbl}: PINNED via the {name}: "
                      f"{' -> '.join(p) if p else lbl + ' (a seed)'}")
                return 0
        print(f"{lbl}: PINNED (seed itself)")
        return 0

    if args.labels:
        cluster = [l.strip() for l in args.labels.split(',') if l.strip()]
        cost = blocked = 0
        for lbl in cluster:
            if lbl not in syms:
                print(f"  ??  {lbl:28s} not in the sym file")
                continue
            if not is_low(lbl):
                print(f"  --  {lbl:28s} not in the low region (${syms[lbl]:04X})")
                continue
            n = sizes.get(lbl, 0)
            cost += n
            if lbl in pinned:
                blocked += 1
                print(f"  XX  {lbl:28s} {n:4d} B  PINNED — run --why {lbl}")
            else:
                print(f"  ok  {lbl:28s} {n:4d} B")
        print(f"\n  moves {cost} B out of the low region and INTO page 1 "
              f"(page 1 pays the same {cost} B)")
        print("  VERDICT: " + ("BLOCKED — %d pinned member(s)" % blocked if blocked
                               else "PROMOTABLE"))
        return 1 if blocked else 0

    low = {l for l in syms if is_low(l) and l in owner}
    per_file = {}
    for lbl in low:
        f = owner[lbl]
        free, pin = per_file.setdefault(f, ([], []))
        (pin if lbl in pinned else free).append((sizes.get(lbl, 0), lbl))

    print(f"low region ${LOWREGION:04X}-${PAGE1 - 1:04X}: "
          f"{len(low)} attributed routines; pinning seeds = "
          f"{len(abi_seeds)} resident-ABI + {len(isr_seeds)} ISR "
          f"({', '.join(isr_seeds) or 'none found'})\n")
    tot_free = tot_pin = 0
    for f in sorted(per_file, key=lambda f: -sum(n for n, _ in per_file[f][0])):
        free, pin = per_file[f]
        fb, pb = sum(n for n, _ in free), sum(n for n, _ in pin)
        tot_free += fb
        tot_pin += pb
        print(f"{fb:6d} B promotable / {pb:6d} B pinned   {f}")
        for n, lbl in sorted(free, reverse=True)[:6]:
            print(f"          {n:4d} B  {lbl}")
    print(f"\n{tot_free} B promotable, {tot_pin} B pinned "
          f"({tot_free + tot_pin} B attributed)")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
