#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""How big is the "an unnamed outcome reads as no outcome" hole, in numbers?

The filed item asks a standing question: *what might the machine legitimately DO
that this readout has no name for -- and when you add one name, what is the next
one?* It records the empirical answer once (naming `UNTRAPPED <msg>` fixed a row,
and within the hour `Division by zero` was missing from the new alternation).
This measures the whole tree instead of one anecdote.

DENOMINATOR: the ROM's OWN message table, `sub/errmsg.asm` -- every
`db "...",0  ; ERR n`. Not a hand-list, so it cannot drift from what the machine
can actually print.

SUBJECT: every tracked probe with a `<NO OUTPUT>` bucket, split by HOW it
classifies. A probe that names no canonical message is not blind -- it reads an
ERR code, a `[...]` span or VRAM, and only falls back to the sentinel when
nothing printed. Only MESSAGE-TEXT classifiers are the subject.

🔴 COMMENTS ARE STRIPPED, AND ONE SPELLING IS NOT THE LIST. A first cut looked
for quoted literals and scored `circmiss_sib2.py` at 1/30 -- the file the item
NAMES as carrying the widened list, which spells it as a REGEX ALTERNATION. A
detector that knows one spelling measures the spelling, not the list.
"""
from __future__ import annotations

import io
import re
import statistics
import subprocess
import sys
import tokenize

CANON_SRC = "sub/errmsg.asm"


def canon() -> set[str]:
    t = open(CANON_SRC).read()
    return {m.group(1) for m in re.finditer(r'db\s+"([^"]+)",0\s*;\s*ERR', t)}


def code_only(path: str) -> str:
    """Source minus `#` comments, so a message named in PROSE is not counted as
    one the readout can recognise."""
    try:
        return "\n".join(tok.string for tok in
                         tokenize.generate_tokens(io.StringIO(open(path).read()).readline)
                         if tok.type != tokenize.COMMENT)
    except Exception:
        return open(path).read()


def main() -> int:
    C = canon()
    if len(C) < 20:
        print(f"INSTRUMENT FAULT: only {len(C)} message(s) parsed out of "
              f"{CANON_SRC}; the denominator is not the ROM's table.")
        return 2
    files = [f for f in subprocess.run(["git", "ls-files"], capture_output=True,
                                       text=True).stdout.split()
             if f.endswith(".py") and (f.startswith("probes/") or f.startswith("scratchpad/"))]
    text_cls, other, bare = [], [], []
    for f in files:
        raw = open(f).read()
        if "<NO OUTPUT>" not in raw:
            continue
        # 🔴 TWO SPELLINGS SATISFY THIS, AND THE FIRST CUT SAW ONLY ONE.
        # The question is "when the readout cannot name what the screen said,
        # does it carry the text?" -- and a probe can answer that either by
        # making `<NO OUTPUT>` itself an f-string, or by returning a SEPARATE
        # sentinel for the unnameable case and keeping `<NO OUTPUT>` bare for a
        # genuinely empty screen. The second is strictly MORE informative (it
        # distinguishes "nothing was printed" from "something was printed that I
        # cannot spell"), and D-CARRYTEXT gave ten probes exactly that shape --
        # which this sweep then reported as unchanged, because it was matching
        # the SPELLING rather than the property. Measured 2026-09-02: the ten
        # edits moved the count by zero until this line was widened, while a
        # planted empty alphabet proved the new path fires on all of them.
        # [[readout-blind-to-its-own-subject]]
        if not re.search(r"<(?:NO OUTPUT|UNREADABLE)[^\"']*\{", raw):
            bare.append(f)
        t = code_only(f)
        known = {m for m in C if m in t}
        (text_cls if known else other).append((len(known), f, sorted(C - known)))
    text_cls.sort()
    ns = [n for n, _, _ in text_cls]
    print(f"canon: {len(C)} messages, from {CANON_SRC}")
    print(f"probes with a <NO OUTPUT> bucket: {len(text_cls) + len(other)}")
    print(f"  classify by MESSAGE TEXT (the subject): {len(text_cls)}")
    print(f"  classify by code / span / VRAM:         {len(other)}")
    print(f"\ncoverage of the canon: min {min(ns)}  median "
          f"{int(statistics.median(ns))}  max {max(ns)}")
    print(f"COMPLETE readouts: {sum(1 for n in ns if n == len(C))} of {len(ns)}")
    print(f"\nsentinels that do NOT carry the text they could not name: "
          f"{len(bare)} of {len(text_cls) + len(other)}")
    for n, f, _ in text_cls:
        print(f"  {n:2d}/{len(C)}  {f}")
    print(f"\nthe WIDEST list in the tree still cannot name {len(text_cls[-1][2])} "
          f"of them, e.g. {text_cls[-1][2][:4]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
