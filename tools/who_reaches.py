#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""who_reaches — who can reach routine X, resolving fall-through and shared tails.

🔴 WHY THIS EXISTS (filed 2026-08-02 by D-MSGMIGRATE §9). That slice's
blast-radius sweep grepped for `jp|call|jr .*print_msg` and missed a FOURTH
reacher: `dl_store`'s line-number-out-of-range arm arrives by `jr dl_ovf_report`,
a SHARED TAIL, and never names `print_msg` anywhere in its own body. The BUILD
caught it -- the label vanished with a collapsed branch -- not the sweep. It
passes a resident string, so it reaches nothing sub-hosted today; it would have,
silently, had that string ever migrated.

🎯 AN INDIRECT REACHER CANNOT BE ENUMERATED BY NAMING THE CALLEE, so this walks
the CALL GRAPH instead -- `check_dead_code.Spans` already resolves fall-through
and shared-tail edges for the dead-code sweep, and this asks it the reverse
question.

WHAT THE HOP DISTANCE MEANS, and it is the whole readout:

  hop 1  the routines that jump/call the target directly. A grep for the
         callee's name finds these, because naming it is how they reach it.
  hop 2+ the routines that reach a hop-1 routine. **These are SILENT**: they
         reach the target without its name appearing in their body, so no grep
         for the callee can list them.

⚠️ THIS IS A QUERY TOOL, NOT A GATE, and deliberately so: "no silent reachers"
is not a property this tree has or should have -- `print_msg` alone has 66 of
them, every one legitimate. The finding a sweep needs is the LIST, not a verdict.

    python3 tools/who_reaches.py print_msg
    python3 tools/who_reaches.py <label> --build sub --hops 3
"""
from __future__ import annotations

import argparse
import collections
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import check_dead_code as dc                                       # noqa: E402

TOPS = {"main": "basic/main.asm", "sub": "sub/sub.asm"}


def graph(build: str):
    m = dc.Spans(TOPS[build], build)
    rev = collections.defaultdict(set)
    for a, bs in m.edges.items():
        for b in bs:
            rev[b].add(a)
    return m, rev


def span_text(m):
    """label -> its own source text, for the "does this body NAME the target"
    question. Rebuilt from `seq` (the per-file label order) rather than stored,
    because Spans keeps order and edges but not the text."""
    out = {}
    for f in m.files:
        try:
            lines = open(f, errors="ignore").read().split("\n")
        except OSError:
            continue
        labs = {l for l in m.seq.get(f, []) if not l.startswith(dc.PROLOGUE)}
        pos = {}
        for i, ln in enumerate(lines):
            s = ln.split(":")[0].strip()
            if s in labs and s not in pos:
                pos[s] = i
        order = sorted(pos, key=lambda x: pos[x])
        for i, lab in enumerate(order):
            end = pos[order[i + 1]] if i + 1 < len(order) else len(lines)
            out[lab] = "\n".join(lines[pos[lab]:end])
    return out


def by_hop(rev, target, hops):
    """{hop: {labels}} -- each label at its SHORTEST distance back from target."""
    seen, frontier, out = {target}, {target}, {}
    for h in range(1, hops + 1):
        nxt = set()
        for n in frontier:
            nxt |= rev.get(n, set())
        # ⚠️ `@prologue:` nodes are the dead-code graph's OWN artefact (one per
        # file, carrying source-adjacency edges), not routines anybody can name
        # or migrate. Reporting them as "silent reachers" would pad the answer
        # with things that are not callers at all.
        nxt = {n for n in nxt if not n.startswith(dc.PROLOGUE)}
        nxt -= seen
        if not nxt:
            break
        out[h] = nxt
        seen |= nxt
        frontier = nxt
    return out


def report(target, build, hops):
    m, rev = graph(build)
    if target not in m.nodes:
        print(f"who_reaches: `{target}` is not a label in the {build} build")
        return 2
    text = span_text(m)
    layers = by_hop(rev, target, hops)
    print(f"who_reaches `{target}` [{build}] -- fall-through and shared-tail "
          f"edges resolved\n")
    total_silent = 0
    for h in sorted(layers):
        labs = sorted(layers[h])
        silent = [n for n in labs if target not in text.get(n, "")]
        total_silent += len(silent) if h > 1 else 0
        tag = ("a grep for the callee finds these" if h == 1
               else "🔴 SILENT to a grep for the callee")
        print(f"  hop {h}: {len(labs)} routine(s), {len(silent)} name it "
              f"NOWHERE in their body -- {tag}")
        for n in labs:
            mark = "     " if target in text.get(n, "") else "  🔴 "
            print(f"{mark}{n}")
    print(f"\n{total_silent} routine(s) beyond hop 1 reach `{target}` without "
          f"its name appearing in them. A blast-radius sweep that greps for the "
          f"callee cannot see any of them.")
    return 0


def selftest() -> int:
    """The D-MSGMIGRATE case itself: `dl_store` must come back as a SILENT
    reacher of `print_msg`. Without that this tool would only be re-deriving what
    a grep already finds."""
    fails = 0
    m, rev = graph("main")
    text = span_text(m)
    layers = by_hop(rev, "print_msg", 3)
    h1 = layers.get(1, set())
    beyond = set().union(*[layers[h] for h in layers if h > 1]) if len(layers) > 1 else set()
    if "dl_ovf_report" not in h1:
        print("  selftest: dl_ovf_report is not a hop-1 reacher of print_msg")
        fails += 1
    if "dl_store" not in beyond:
        print("  selftest: dl_store -- D-MSGMIGRATE's OWN missed reacher -- is "
              "not reported beyond hop 1")
        fails += 1
    elif "print_msg" in text.get("dl_store", ""):
        print("  selftest: dl_store names print_msg, so it is not the silent "
              "case this tool exists for")
        fails += 1
    # ...and the control: hop-1 routines DO name it, which is why a grep finds
    # them and why "silent" means something
    named = [n for n in h1 if "print_msg" in text.get(n, "")]
    if len(named) != len(h1):
        print(f"  selftest: {len(h1) - len(named)} hop-1 routine(s) do not name "
              f"the target -- the hop-1/grep equivalence this report asserts "
              f"does not hold")
        fails += 1
    print("  selftest: PASS" if not fails else f"  selftest: {fails} FAILURE(S)")
    return fails


def main(argv):
    if "--selftest" in argv:
        return 2 if selftest() else 0
    ap = argparse.ArgumentParser()
    ap.add_argument("label")
    ap.add_argument("--build", default="main", choices=sorted(TOPS))
    ap.add_argument("--hops", type=int, default=2)
    a = ap.parse_args(argv)
    return report(a.label, a.build, a.hops)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
