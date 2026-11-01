#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-REREAD-EDGES, the ranking tool: what could a routine and its CALL SITES
share? (Joost 2026-11-01: "widen the re-read to take a function and also its
edges"; the campaign order he set the same day: EDGES first, feeding
D-SUB2RETIRE.)

Reads the BUILT main ROM through z80flow's loader (build/zerobas-main-eu.rom +
build/basic-reloc.sym, context 0 only -- the sub ROMs are a later pass). For
every code label it decodes forward to a terminator or the next label and
records each CALL with the instructions before and after it in that run. Per
call target:

  PRELUDE  -- the instructions just BEFORE the call that k of its n sites share
              (the best k for prelude lengths 1..4). Folding them into a new
              entry label placed in front of the callee costs 0 bytes and saves
              (k - 1) x their size: every other caller and every jp into the
              callee are untouched.
  POSTLUDE -- the instructions just AFTER the call that k sites share. Folding
              them needs the callee to run them on EVERY exit, so these rows are
              CANDIDATES that need the callee's exits read first.

Bytes are the encoded lengths of the identical instructions (the decoder's
`length`). A `jr` / `jp` / `call` matches only with the SAME absolute target.

⚠️ A row is a CANDIDATE, never an edit:
  * z80flow is BLIND TO STACK DEPTH -- moving a `push` across a call boundary
    is exactly what batch 10's dimedge fall-through broke;
  * ABI edges are excluded by hand, not here yet: sub-ROM tenants' callees, the
    published BASIC entries, the low-region forced set, the pinned addresses;
  * a flag-setting prelude (`cp`, `or a`) is only foldable if nothing between it
    and the call reads... it is IN FRONT of the call, so the call sees it either way.

    python3 scratchpad/edges_rank.py [--top 40] [--min-sites 2]
"""
import argparse
import collections
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "tools", "z80flow"))
from z80flow.decode import decode               # noqa: E402
from z80flow.program_zerobas import build       # noqa: E402

MAX_RUN = 256


def runs(p):
    """label addr -> list of decoded instructions up to a terminator / next label."""
    # every context (main, sub p0/p1, sub2 p0/p1, disk); context 0's code ranges are
    # known, the others' labels are taken as code (a data label decodes to calls
    # that match nothing, which ranks nothing)
    labs = sorted(a for a in p.labels if (a >> 16) or p.in_code(a))
    out = {}
    for i, a in enumerate(labs):
        nxt = labs[i + 1] if i + 1 < len(labs) else a + MAX_RUN
        seq, pc = [], a
        while pc < nxt and pc - a < MAX_RUN:
            ins = decode(p.read, pc)
            if ins.invalid:
                break
            seq.append(ins)
            pc += ins.length
            if not ins.falls_through:
                break
        out[a] = seq
    return out


def key(ins):
    return ins.mnem


def best_shared(seqs, longest=4, reverse_text=False):
    """-> (k, L, bytes, text): the most bytes saved by one sequence of L instrs
    that k of the given instruction lists share (pre: their LAST L; the caller
    reverses for post)."""
    best = (0, 0, 0, "")
    for L in range(1, longest + 1):
        groups = collections.defaultdict(list)
        for s in seqs:
            if len(s) >= L:
                groups[tuple(key(x) for x in s[-L:])].append(s)
        for k_seq, members in groups.items():
            k = len(members)
            if k < 2:
                continue
            nbytes = sum(x.length for x in members[0][-L:])
            saved = (k - 1) * nbytes
            if saved > best[2]:
                shown = reversed(k_seq) if reverse_text else k_seq
                best = (k, L, saved, " / ".join(shown))
    return best


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=40)
    ap.add_argument("--min-sites", type=int, default=2)
    a = ap.parse_args()
    p = build(REPO)
    r = runs(p)
    pre = collections.defaultdict(list)    # target -> [instrs before the call]
    post = collections.defaultdict(list)   # target -> [instrs after the call]
    jumped = collections.Counter()
    for lab, seq in r.items():
        ctx = lab & ~0xFFFF
        for i, ins in enumerate(seq):
            if ins.target is None:
                continue
            # the decoder's target is a 16-bit address: put it in the CALL SITE's
            # context (a sub-ROM call to $0200 is not C-BIOS's $0200). `rst` is
            # left out: $FF fill decodes as `rst $38`, and RSTs are fixed vectors.
            t = ctx | (ins.target & 0xFFFF)
            if ins.kind == "call":
                pre[t].append(seq[:i])
                post[t].append(list(reversed(seq[i + 1:])))
            elif ins.kind in ("jp", "jr"):
                jumped[t] += 1
    if not pre:
        print("NO CALL SITES DECODED -- refusing to rank (an empty table is not 'nothing to save')")
        return 2
    rows = []
    for t, seqs in pre.items():
        if len(seqs) < a.min_sites:
            continue
        k, L, saved, text = best_shared(seqs)
        if saved:
            rows.append(("PRE ", saved, k, len(seqs), L, p.name_of(t), text, jumped[t], t >> 16))
        k, L, saved, text = best_shared(post[t], reverse_text=True)
        if saved:
            rows.append(("POST", saved, k, len(seqs), L, p.name_of(t), text, jumped[t], t >> 16))
    rows.sort(key=lambda x: -x[1])
    total_pre = sum(x[1] for x in rows if x[0] == "PRE ")
    total_post = sum(x[1] for x in rows if x[0] == "POST")
    print(f"labels walked: {len(r)}; call targets with >= {a.min_sites} sites: "
          f"{sum(1 for s in pre.values() if len(s) >= a.min_sites)}")
    print(f"candidate bytes (overlapping, an UPPER bound): prelude {total_pre}, postlude {total_post}")
    print("per ROM context (prelude + postlude, upper bound):")
    for cid, cname in sorted(p.contexts.items()):
        b = sum(x[1] for x in rows if x[8] == cid)
        print(f"  {cname:7s} {b:5d} B")
    print("\nkind  saved  k/n   L  ctx     target                     jp-in  shared instructions")
    for kind, saved, k, n, L, name, text, j, cid in rows[:a.top]:
        print(f"{kind} {saved:5d}  {k:2d}/{n:<3d} {L}  {p.contexts.get(cid, cid):7s} {name:26s} {j:4d}   {text[:80]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
