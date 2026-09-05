#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-REVERTSWEEP — a filed ✅ for work the SOURCE says was undone.

Found twice by hand in one afternoon:

  * the non-tiling `LEN=r` entry carried *"✅ AND THE VALIDATOR IS NOW WIDENED
    (D-RECLEN2)"* while `basic/files.asm`'s `opr_lowbyte` said *"D-RECLEN2 TRIED
    TO DROP THIS AND HAD TO PUT IT BACK"* — false since the day it was written;
  * `basic_probe_sprite_trap.py`'s header claimed it was *"deliberately NOT yet
    wired to a `make` target"* while naming the target that runs it.

🎯 THE SHAPE IS ONE-SIDED AND THAT IS WHY NOTHING CATCHES IT. A slice lands, is
written up ✅, and is LATER undone by a different slice that records the reversal
**where the code is** — in a source comment nobody re-reads against the filing.
`todo-citation-check` verifies that a citation points at the right BLOCK; nothing
asks whether the block is still TRUE.

## What this does

1. find revert/undo language in the ROM sources (`PUT IT BACK`, `REVERTED`,
   `TRIED TO … AND HAD TO`, `never shipped`, …);
2. read the `D-XXX` slice names in that comment's neighbourhood;
3. report every one of those names that TODO.md marks ✅/🟢 anywhere.

⚠️ A SHORTLIST, NEVER A VERDICT — and the reasons are specific. A slice can be
partly reverted and rightly still carry a ✅ for the half that stands
(`basic/graphics.asm`'s fold is REVERTED at four sites and explicitly *"NOT
reverted"* broadly). A comment can also record a reversal that the entry itself
already describes. Every hit is read.
"""
from __future__ import annotations

import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TREES = ("basic", "sub", "disk", "tape")
# 🔴 TWO ALTERNATIVES CAME OUT AFTER THE FIRST RUN, EACH FOR ITS OWN REASON.
#   `had to put`  matched basic/sysvars.inc's *"D-LINEMAX had to put it
#                 somewhere, and it cost 1792 B of TXTMAX"* -- a PLACEMENT COST,
#                 not a reversal. Too generic to keep.
#   the DRAFT exclusion below kills sub/punum.asm's *"The first attempt at this
#                 (D-PUDOT, reverted) juggled it through push/pop"* -- a
#                 discarded DRAFT inside a slice that then shipped a better
#                 design. Its ✅ is correct; what was reverted is not its subject.
# 🎯 THE DISCRIMINATOR IS WHETHER THE REVERTED THING IS THE SLICE'S SUBJECT
# or a draft it replaced, and that is what these two exclusions approximate.
REVERT = re.compile(
    r"put it back|revert|backed out|tried to (drop|remove|widen)|"
    r"never shipped|was undone|does not ship", re.I)
DRAFT = re.compile(r"attempt|first cut|first try|draft|earlier version", re.I)
SLICE = re.compile(r"\bD-[A-Z0-9]{3,}\b")
DONE = re.compile(r"(✅|🟢)[^\n]{0,160}")
NEAR = 6                       # comment lines either side to read slice names from

# 🔴 READ AND ALLOWED, WITH THE REASON. A slice can ship HALF of itself and be
# filed accurately for that half, and this sweep cannot tell that from a filing
# that claims the whole. The exceptions live here so the tool can go clean --
# meaning "nothing NEW" -- rather than being tuned until it is silent, which
# would be fitting the answer. They may shrink; a stale one is a defect.
ALLOW = {
    "D-RECLEN2":
        "TODO.md:6875 files it exactly right -- `D-RECLEN2 2026-08-30 -- THE "
        "FACE SHIPPED, THE DOMAIN DID NOT`. The face (ERR 5, not Syntax error) "
        "IS shipped; the domain widening is what went back, and opr_lowbyte's "
        "note is about that half. The entry that DID claim the whole thing "
        "(`AND THE VALIDATOR IS NOW WIDENED`) was struck 2026-09-05 by "
        "D-RECLENROT -- which is the case this tool was written for, and it "
        "found it.",
}


def main() -> int:
    todo = open(os.path.join(ROOT, "TODO.md"), encoding="utf-8").read()
    # 🔴 A ✅ INSIDE `~~...~~` HAS ALREADY BEEN RETRACTED, and counting it as
    # live would make this sweep report its own fixed case for ever. Both are
    # collected, and the hit says which -- so the calibration stays VISIBLE (the
    # case that motivated the tool still shows, labelled) instead of vanishing.
    done_slices, struck_slices = set(), set()
    for m in DONE.finditer(todo):
        seg = m.group(0)
        lo = todo.rfind("~~", 0, m.start())
        hi = todo.find("~~", m.start())
        inside = lo != -1 and hi != -1 and todo.count("~~", 0, m.start()) % 2 == 1
        (struck_slices if inside else done_slices).update(SLICE.findall(seg))
    struck_slices -= done_slices

    hits, scanned = [], 0
    for t in TREES:
        for p in sorted(glob.glob(os.path.join(ROOT, t, "**", "*.asm"),
                                  recursive=True)
                        + glob.glob(os.path.join(ROOT, t, "**", "*.inc"),
                                    recursive=True)):
            scanned += 1
            lines = open(p, encoding="utf-8", errors="replace").read().splitlines()
            for i, ln in enumerate(lines):
                if not REVERT.search(ln):
                    continue
                window = "\n".join(lines[max(0, i - NEAR):i + NEAR + 1])
                # 🔴 THE DRAFT TEST READS THE WINDOW, NOT THE LINE, AND THE FIRST
                # CUT READ THE LINE. sub/punum.asm wraps mid-sentence: "The first
                # attempt at this (D-PUDOT," ends one line and "reverted) juggled
                # it through push/pop" begins the next, so a line-scoped
                # exclusion saw `reverted` with no `attempt` beside it and kept a
                # false positive the very comment disqualifies.
                if DRAFT.search(window):
                    continue
                for name in set(SLICE.findall(window)):
                    if name in ALLOW:
                        continue
                    if name in done_slices or name in struck_slices:
                        hits.append((os.path.relpath(p, ROOT), i + 1, name,
                                     ln.strip()[:88],
                                     "LIVE" if name in done_slices
                                     else "STRUCK - already corrected"))
    print(f"{scanned} source file(s) swept; TODO.md marks "
          f"{len(done_slices)} slice name(s) ✅/🟢")
    if not done_slices:
        print("🔴 INSTRUMENT FAULT: no ✅ slice names parsed out of TODO.md "
              "at all — the cross-check has nothing to compare against and a "
              "clean result would mean nothing.")
        return 2
    if not hits:
        print(f"clean — no source revert note names a slice TODO.md still "
              f"marks done, beyond the {len(ALLOW)} read and allowed:")
        for k, why in sorted(ALLOW.items()):
            print(f"    [{k}] {why}")
        return 0
    live = [h for h in sorted(set(hits)) if h[4] == "LIVE"]
    print(f"\n{len(hits)} source revert note(s) naming a slice TODO.md marks "
          f"✅ — READ EACH, this is a shortlist:")
    for rel, ln, name, text, state in sorted(set(hits)):
        print(f"  [{state:26s}] {rel}:{ln}  [{name}]  {text}")
    if not live:
        print("\nclean — every hit is a ✅ that has ALREADY been struck through, "
              "which is the calibration: the case that motivated this tool still "
              "shows up, labelled, instead of vanishing once fixed.")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
