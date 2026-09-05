#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-CITEHEAD — an AUDIT for citations that name the wrong block. Not a gate.

🔴 THE CLASS. `tools/check_todo_citations.py` verifies that a citation's LINE
and ID agree; it cannot ask whether the cited block is the one the prose is
ABOUT. Seven citations have now been found naming an unrelated item, **every one
of them GREEN** by that rule -- the id really was the id of the block at that
line.

🎯 AND FIVE OF THE SEVEN WERE FOUND BY ACCIDENT. The id is derived from the
headline, so closing an item re-keys every inbound citation; the wrong one then
goes red for the wrong reason and a human reads it. That is not a method. The
two found on 2026-09-06 were found by THIS, which is.

## Why this is an audit and not a gate

D-CITESUBJ measured the obvious semantic rule -- flag a citation sharing no
distinctive token with the cited block -- over the live corpus: **30 of 46**
against the headline, **21 of 46** against the whole block, with no true
positive left to find. Shipping that as an advisory is shipping noise.

This is the same idea narrowed to where the prose actually declares a subject:
**the markdown HEADING above the citation**. In a survey document each `### N.
<claim>` section IS one item, and the heading is written to name it.

    measured 2026-09-06 over 41 markdown citations
      13  no heading within 8 lines        -- not in scope
      10  heading too thin                 -- grouping ("Also open, lower value")
                                              or structural ("S1 - Make the ...")
       8  heading SHARES a token           -- consistent
      10  FLAGGED, of which 2 were REAL

20% precision. Too noisy for a gate, and 🟢 productive as a one-off audit: those
two -- gapsweep sections 3 and 5 -- had been wrong since 2026-08-21 and are
instances SIX and SEVEN. The eight false positives are a document's own title or
section-0 heading, which names the DOC and not the cited item; that is a shape,
not a mistake, and tuning it away on two data points would be fitting.

⚠️ SO: RUN IT, READ EVERY FLAG, EXPECT MOST TO BE FINE. It is collected by no
battery on purpose -- `make gates` gains nothing from a check that is right one
time in five.
"""
from __future__ import annotations

import collections
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import check_todo_citations as C                                  # noqa: E402

TOK = re.compile(r"`([^`\n]{2,40})`|\"([^\"\n]{2,40})\"|\b([A-Za-z][A-Za-z0-9_$]{3,})\b")
# ⚠️ THE STOPLIST CARRIES THE GROUPING WORDS TOO ("open", "lower", "value",
# "row", "smaller"), because a heading like "Also open, lower value" is a BUCKET
# and not a claim -- it cannot agree or disagree with anything.
STOP = set("the and for with that this from into only when what which have been were "
           "todo done does not but its are was has had can will would than then there "
           "their they them all any one two also more most much such over under about "
           "after before both each other same some still very just make call site open "
           "lower value smaller each row rows".split())
HEAD = re.compile(r"^\s{0,3}#{1,6}\s+(.*\S)\s*$")
MIN_HEADING_TOKENS = 4


def toks(text: str) -> set[str]:
    out = set()
    for m in TOK.finditer(text or ""):
        v = (m.group(1) or m.group(2) or m.group(3)).lower()
        for w in re.split(r"[^a-z0-9_$.]+", v):
            if len(w) >= 4 and w not in STOP:
                out.add(w)
    return out


def heading_above(lines, n, window=8):
    for i in range(n - 1, max(-1, n - 1 - window), -1):
        m = HEAD.match(lines[i])
        if m:
            return m.group(1)
    return None


def audit():
    C._CACHE.clear()
    found = C.scan(C.tracked())
    stats, flags = collections.Counter(), []
    for rel, n, spelled, line, bid, verdict, _ in found:
        if verdict not in ("OK", "PAIR") or not rel.endswith(".md"):
            continue
        tgt = C.resolve(rel, spelled)
        blk = C.block_at(tgt, line) if tgt else None
        if blk is None:
            continue
        lines = open(os.path.join(ROOT, rel), encoding="utf-8",
                     errors="replace").read().splitlines()
        head = heading_above(lines, n)
        if head is None:
            stats["no heading in scope"] += 1
            continue
        a, b = toks(head), toks(blk["headline"])
        if len(a) < MIN_HEADING_TOKENS:
            stats["heading too thin (grouping/structural)"] += 1
            continue
        if not b:
            stats["cited headline carries no token"] += 1
            continue
        if a & b:
            stats["shares a token"] += 1
        else:
            stats["FLAGGED"] += 1
            flags.append((rel, n, head, tgt, line, blk["id"], blk["headline"]))
    return stats, flags


def main():
    stats, flags = audit()
    print(f"D-CITEHEAD audit: {sum(stats.values())} markdown citation(s)")
    for k, v in stats.most_common():
        print(f"  {v:3d}  {k}")
    if not flags:
        print("\n  no flags -- every claim-shaped heading shares a token with the "
              "block it cites")
        return 0
    print(f"\n🔎 {len(flags)} FLAG(S) — READ EACH ONE. Historically about "
          f"1 in 5 is a real mis-aimed citation; the rest are a document's own "
          f"title or section-0 heading, which names the DOC, not the item.")
    for rel, n, head, tgt, line, bid, bh in flags:
        print(f"\n  {rel}:{n} -> {tgt}:{line} ({bid})")
        print(f"    heading: {head[:76]}")
        print(f"    block  : {re.sub(r'[*`~]', '', bh)[:76]}")
    # 🔴 rc 0 ON PURPOSE. This is an audit; a non-zero rc invites someone to
    # collect it into `make gates`, where a 20%-precision rule would train people
    # to ignore a red.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
