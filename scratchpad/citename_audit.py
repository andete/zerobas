#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-CITENAME -- the LONE mis-aimed citation, caught by NAMING rather than by
disagreement.

## The residual this attacks

`check_todo_citations.subject_conflicts()` catches the SIBLING shape: two docs
whose identical sentence resolve to two different blocks. At most one can be
right, and no guess about meaning is needed. It found three of the first four
instances and reads 0 false positives.

It cannot see a LONE wrong citation -- one doc, one sentence, one wrong block,
nothing to disagree with. That residual is written into the parent item, and
`scratchpad/citehead_audit.py` is the measured attempt at it: flag a citation
whose markdown heading shares no distinctive token with the block it names.
**20% precision** -- productive as a one-off sweep, refused as a gate.

## The sharper signal both real instances actually carried

Read instances SIX and SEVEN again and the finding is not "these headings
disagree with the block". It is stronger and it is positive:

    section 3  "SCREEN 3 draws on both references; zerobas raises ERR 5"
               -> is the headline of T-6AC87B, VERBATIM
    section 5  "A stored `DATA` literal charges the string pool 25 B"
               -> is the headline of T-B22650, VERBATIM

The heading is not merely inconsistent with the cited block. It **names a
different block, exactly**. That is an identification, not a similarity, and it
needs no threshold: a survey section headed with some item's own headline is
about THAT item, and a citation under it pointing elsewhere is wrong.

Absence of a match says nothing at all -- most headings are prose the author
wrote fresh -- so this is precise where `citehead_audit` is broad, and blind
where `citehead_audit` at least guesses. They are complements.

## Matching

Normalise to a token sequence (markdown, emoji and punctuation stripped, case
folded) and require the heading to be the whole headline or a PREFIX of it --
headlines wrap across lines and a heading routinely carries the first line only.
`MIN_TOKENS` keeps a short structural heading ("S1 -- Make the build") from
prefix-matching half the corpus.

## Measured 2026-09-06 over the live corpus

    41 markdown citations
      21  heading names no block          -- prose the author wrote fresh
      13  no heading within 8 lines
       5  heading too short to identify
       2  heading names a block SOME citation under it cites   <- the controls
       0  FLAGGED

Both positive controls are gapsweep sections 3 and 4, whose headings ARE the
headlines of `T-6AC87B` and `T-E0B04B` and which cite exactly those. Verified by
falsification, three arms, each restoring byte-identically:

  * plant a LONE mis-aim (section 4 repointed at `T-B22650`):
    `check_todo_citations.py` stays **rc 0** -- the id really is the id of the
    block at that line -- and this reads **rc 1**. That is the residual class,
    reproduced.
  * plant a see-also (the correct citation PLUS one to another block): the group
    absorbs it, 2 -> 3 members, **no flag**. Scored per CITATION this is a false
    positive with no defence; per HEADING it is not.
  * `--selftest`, 8 arms, over the two normalisations and the group rule.

## Why this is an audit and not collected into `make gates`

Not for `citehead_audit`'s reason. That one is 20% precise; this one reads 0
false positives and the only known false-positive SHAPE is designed out. The
reason is the **denominator**: 2 of 41 citations are in scope, so as a gate it
would be 39/41 vacuous, and a green that covers two rows is the shape this
project keeps catching itself trusting. It fires honestly when it fires; there
is just very little for it to fire on until more survey documents exist.
"""
from __future__ import annotations

import collections
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import check_todo_citations as C                                  # noqa: E402

HEAD = re.compile(r"^\s{0,3}#{1,6}\s+(.*\S)\s*$")
# 🔴 THE SECTION NUMBER IS PART OF THE HEADING AND NOT PART OF THE NAME. A survey
# heading reads `### 4. A line store is bounded by ...`; leaving the `4.` in the
# token stream puts it at position 0, where it defeats a PREFIX match against the
# headline outright. This cost the audit both positive controls a second time,
# after the trailing-period fix -- the same zero, a different cause.
ENUM = re.compile(r"^\s*(?:[A-Za-z]?\d+(?:\s*[\u2013\u2014-]\s*\d+)?)"
                  r"\s*[.)\u2013\u2014-]?\s+")
MIN_TOKENS = 5
CORPUS = ("TODO.md", "docs/TODO-done.md")


def norm(text: str) -> tuple[str, ...]:
    t = re.sub(r"[*`~_]", " ", text or "")
    t = re.sub(r"\[\[[^\]]*\]\]", " ", t)
    t = re.sub(r"[^\w$. ]+", " ", t, flags=re.UNICODE)
    # 🔴 STRIP TRAILING PUNCTUATION PER TOKEN, NOT GLOBALLY. `.` is kept inside a
    # token so `basic/files.asm` and `§4.1` survive, and the first cut kept it at
    # the END too -- which made `himem.` != `himem` and silently cost this audit
    # BOTH of its known-good positive controls. The readout said "0 flags" and
    # also "0 headings name the block they cite"; the second zero is what showed
    # it was measuring nothing [[readout-blind-to-its-own-subject]].
    return tuple(w for w in (x.strip(".") for x in t.lower().split()) if w)


def headline_index():
    """normalised headline -> [(rel, id, headline)]; plus every prefix of it."""
    idx = collections.defaultdict(list)
    for rel in CORPUS:
        if not os.path.exists(os.path.join(ROOT, rel)):
            continue
        for b in C.blocks_of(rel):
            key = norm(b["headline"])
            if len(key) < MIN_TOKENS:
                continue
            idx[key].append((rel, b["id"], b["headline"]))
    return idx


def heading_above(lines, n, window=8):
    """(heading text, its line index) -- the index is the GROUP KEY, see audit()."""
    for i in range(n - 1, max(-1, n - 1 - window), -1):
        m = HEAD.match(lines[i])
        if m:
            return ENUM.sub("", m.group(1)), i
    return None, None


def audit():
    C._CACHE.clear()
    idx = headline_index()
    # prefix map: a heading may carry only the headline's first line
    prefixes = collections.defaultdict(list)
    for key, hits in idx.items():
        for k in range(MIN_TOKENS, len(key) + 1):
            prefixes[key[:k]].extend(hits)

    stats = collections.Counter()
    # 🎯 THE UNIT IS THE HEADING, NOT THE CITATION. A section headed with item
    # X's own headline is about X, but it may legitimately carry a "see also"
    # citation to a RELATED item -- and scored per citation that see-also is a
    # false positive with no defence. Scored per heading it is not: the group is
    # clean as soon as ANY citation under the heading names X, and the flag
    # means "this section names X and nothing under it points at X".
    groups: dict[tuple, list] = collections.defaultdict(list)
    for rel, n, spelled, line, bid, verdict, _ in C.scan(C.tracked()):
        if verdict not in ("OK", "PAIR") or not rel.endswith(".md"):
            continue
        tgt = C.resolve(rel, spelled)
        blk = C.block_at(tgt, line) if tgt else None
        if blk is None:
            continue
        lines = open(os.path.join(ROOT, rel), encoding="utf-8",
                     errors="replace").read().splitlines()
        head, hidx = heading_above(lines, n)
        if head is None:
            stats["no heading in scope"] += 1
            continue
        key = norm(head)
        if len(key) < MIN_TOKENS:
            stats["heading too short to identify"] += 1
            continue
        if not prefixes.get(key):
            stats["heading names no block (silent, by design)"] += 1
            continue
        groups[(rel, hidx, head, key)].append((n, tgt, line, blk))

    flags = []
    for (rel, _hidx, head, key), members in sorted(groups.items()):
        hits = prefixes[key]
        ids = {h[1] for h in hits}
        if any(b["id"] in ids for _n, _t, _l, b in members):
            stats["heading names a block some citation under it cites"] += len(members)
        else:
            stats["FLAGGED (heading group)"] += 1
            flags.append((rel, head, members, hits))
    return stats, flags


def selftest() -> int:
    """🔬 THE THREE PLACES THIS AUDIT MEASURED NOTHING BEFORE IT MEASURED
    ANYTHING. Both were the same symptom -- "0 flags" -- with two different
    causes, and both were caught only because the readout ALSO prints how many
    headings match POSITIVELY. A rule that never fires either way is not clean,
    it is blind [[readout-blind-to-its-own-subject]]."""
    bad = []

    def eq(got, want, what):
        if got != want:
            bad.append(f"{what}: got {got!r}, want {want!r}")

    # (1) trailing punctuation is not part of a token
    eq(norm("not by HIMEM."), ("not", "by", "himem"), "trailing period")
    eq(norm("`basic/files.asm` §4.1"), ("basic", "files.asm", "4.1"),
       "interior dot survives")
    # (2) a section enumerator is not part of the name
    eq(ENUM.sub("", "4. A line store"), "A line store", "enumerator")
    eq(ENUM.sub("", "6\u20138. Smaller"), "Smaller", "en-dash range")
    eq(ENUM.sub("", "S1 - Make the build"), "Make the build", "letter+digit")
    eq(ENUM.sub("", "25 B is charged"), "B is charged", "bare number")
    # (3) the group rule: clean iff SOME member cites the identified block
    prefixes = {("a", "line", "store", "is", "bounded"): [("TODO.md", "T-X", "h")]}
    key = ("a", "line", "store", "is", "bounded")
    hits = prefixes[key]
    ids = {h[1] for h in hits}
    eq(any(b in ids for b in ["T-Y"]), False, "lone mis-aim flags")
    eq(any(b in ids for b in ["T-X", "T-Y"]), True, "see-also is absorbed")
    eq(any(b in ids for b in ["T-Y", "T-X"]), True, "order does not matter")
    # falsification: a heading shorter than MIN_TOKENS must identify nothing
    eq(len(norm("2. `DEF FN` / `FN`")) >= MIN_TOKENS, False, "thin heading")

    for b in bad:
        print(f"  SELFTEST FAIL {b}")
    print(f"selftest: {8 - len(bad)}/8 arms green")
    return len(bad)


def main():
    if "--selftest" in sys.argv:
        return selftest()
    stats, flags = audit()
    print(f"D-CITENAME audit: {sum(stats.values())} markdown citation(s)")
    for k, v in stats.most_common():
        print(f"  {v:3d}  {k}")
    if not flags:
        print("\n  no flags -- no citation sits under a heading that is another "
              "block's headline")
        return 0
    print(f"\n🔴 {len(flags)} FLAGGED HEADING(S). Each is an IDENTIFICATION, "
          f"not a similarity: the heading IS some block's headline, and NOTHING "
          f"cited under it points at that block.")
    for rel, head, members, hits in flags:
        print(f"\n  {rel}: heading {head[:66]!r}")
        for h_rel, h_id, h_head in hits[:3]:
            print(f"    names      : {h_rel} ({h_id}) "
                  f"{re.sub(r'[*`~]', '', h_head)[:52]}")
        for n, tgt, line, b in members:
            print(f"    :{n} cites  : {tgt}:{line} ({b['id']}) "
                  f"{re.sub(r'[*`~]', '', b['headline'])[:46]}")
    return len(flags)


if __name__ == "__main__":
    raise SystemExit(1 if main() else 0)
