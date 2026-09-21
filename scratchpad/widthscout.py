#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-WIDTHSCOUT -- what does the CODE say a pinned cell's width is?

🔴 WHY. `tools/ram-width-allow.txt` pins every cell whose extent
`tools/ram_map.py` cannot read out of its own comment. It is a ratchet that may
only shrink, and the way to shrink it is to give a cell a machine-readable width
-- but `docs/ram-map.md`'s own header records the failure mode that matters
here: **a width can be PRESENT AND WRONG**, and no gate catches that. `; 32 B …
(word)` read as 2 and `; (4 B each)` read as 4 for a 32-byte array, both on
2026-09-21.

🎯 SO A WIDTH MUST BE DERIVED, NEVER GUESSED, AND THIS READS IT OFF THE
INSTRUCTIONS THAT TOUCH THE CELL. A Z80 access names its own width:
`ld (N),hl` is two bytes, `ld a,(N)` is one, `ld (N+3),a` proves the cell is at
least four. The tool collects every access spelled with the NAME (or one of its
aliases), classifies each by width, and reports the SET.

⚠️ IT REFUSES MORE THAN IT ANSWERS, ON PURPOSE. Three outcomes:
  * **UNAMBIGUOUS** -- every access agrees on one width and no offset reaches
    past it. Only these are safe to write into a declaration.
  * **AMBIGUOUS** -- accesses disagree (a word cell whose low byte is also
    poked, an array reached at several offsets). These are the INTERESTING ones:
    they are exactly where a guessed width would have been wrong, and each needs
    a human reading, not a rule.
  * **UNSEEN** -- no access spelled with the name at all. The cell is reached
    only through a pointer or an offset from a neighbour, so the code cannot
    speak for it [[a-coverage-row-whose-geometry-cannot-reach-the-case]].

⚠️ AND "UNSEEN" IS NOT "ONE BYTE". The whole point of the pin file is that an
address says where a cell STARTS and never how long it is.

🔴 NEVER WRITE A WIDTH INTO A GENERATED FILE, AND THIS TOOL SAYS WHICH THEY ARE
BECAUSE THE FIRST SWEEP DID EXACTLY THAT. `disk/basic-resident-abi.inc` is
produced by `tools/gen_resident_abi.py`, which COPIES (and truncates) main's
comment for each imported cell. Three widths written there survived long enough
to make their pins look stale, the pins were deleted, and the next build
regenerated the file and wiped the widths -- leaving three cells with no width
and no pin, which `make ram-map-check` then caught. The fix for an imported
cell is main's OWN declaration; and note the truncation, which can cut a width
off a comment that really does declare one.

    python3 scratchpad/widthscout.py [--selftest] [--why undeclared]
"""
from __future__ import annotations

import os
import re
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
# \u26a0\ufe0f MODULE LEVEL, NOT INSIDE selftest(). `make temp-root-check` reads a
# FUNCTION-local import as "reaches no chokepoint" -- a static scanner cannot
# see a runtime one [[a-static-gate-cannot-see-a-computed-path]], which cost a
# build on 2026-09-21. The side effect (setting tempfile.tempdir) is the point.
import probe_tmp  # noqa: E402,F401
import ram_map  # noqa: E402

ALLOW = os.path.join(ROOT, "tools", "ram-width-allow.txt")

# A 16-bit register pair in a `ld` to/from an absolute address moves TWO bytes;
# `a` moves one. `sp` is two. These are the only absolute-addressing loads the
# Z80 has, which is what makes the classification total rather than heuristic.
W2 = ("hl", "de", "bc", "sp", "ix", "iy")


def access_re(name: str) -> re.Pattern:
    """Every `(NAME)` or `(NAME + k)` operand, with the register beside it."""
    n = re.escape(name)
    return re.compile(
        r"(?:ld\s+\(\s*" + n + r"\s*(?:\+\s*(\d+))?\s*\)\s*,\s*([a-z]{1,2})"
        r"|ld\s+([a-z]{1,2})\s*,\s*\(\s*" + n + r"\s*(?:\+\s*(\d+))?\s*\))",
        re.I)


def strip_comment(line: str) -> str:
    return line.split(";", 1)[0]


def scan(names, files):
    """-> (widths seen, max offset+1 seen, sample lines). Comments excluded:
    a comment naming `ld (X),hl` is prose, and prose is not a measurement."""
    pats = [(n, access_re(n)) for n in names]
    widths, reach, samples = set(), 0, []
    for path in files:
        try:
            src = open(os.path.join(ROOT, path)).read().splitlines()
        except OSError:
            continue
        for line in src:
            code = strip_comment(line)
            if not code.strip():
                continue
            for n, pat in pats:
                for m in pat.finditer(code):
                    off = m.group(1) or m.group(4) or "0"
                    reg = (m.group(2) or m.group(3) or "").lower()
                    w = 2 if reg in W2 else 1
                    widths.add(w)
                    reach = max(reach, int(off) + w)
                    if len(samples) < 3:
                        samples.append(code.strip())
    return widths, reach, samples


def verdict(widths, reach):
    if not widths:
        return "UNSEEN", None
    if len(widths) == 1 and reach == next(iter(widths)):
        return "UNAMBIGUOUS", reach
    return "AMBIGUOUS", reach


def selftest():
    """Planted sources with a KNOWN answer, plus the negative controls. A scan
    that matched nothing would print "0 ambiguous" just as loudly as a clean
    corpus, so every arm below has a counterpart that must NOT fire."""
    fails = 0

    def arm(label, want_v, want_r, names, text):
        nonlocal fails
        d = tempfile.mkdtemp()
        p = os.path.join(d, "x.asm")
        open(p, "w").write(text)
        rel = os.path.relpath(p, ROOT)
        w, r, _ = scan(names, [rel])
        v, got = verdict(w, r)
        if v != want_v or (want_r is not None and got != want_r):
            print(f"  selftest: {label}: got {v}/{got}, want {want_v}/{want_r}")
            fails += 1

    arm("a word cell", "UNAMBIGUOUS", 2, ["FOO"],
        "        ld (FOO),hl\n        ld hl,(FOO)\n")
    arm("a byte cell", "UNAMBIGUOUS", 1, ["BAR"],
        "        ld a,(BAR)\n        ld (BAR),a\n")
    # 🔴 THE ARM THIS TOOL EXISTS FOR: two widths on one cell must NOT be
    # reported as either of them.
    arm("a word cell whose low byte is poked", "AMBIGUOUS", 2, ["BAZ"],
        "        ld (BAZ),hl\n        ld a,(BAZ)\n")
    arm("an offset past the access width", "AMBIGUOUS", 4, ["QUX"],
        "        ld (QUX),hl\n        ld (QUX + 2),hl\n")
    # NEGATIVE: a name that appears only in a COMMENT is not an access...
    arm("a comment-only mention", "UNSEEN", None, ["ZOT"],
        "        nop        ; ld (ZOT),hl -- prose, not code\n")
    # ...and a DIFFERENT name that merely contains ours must not match.
    arm("a longer name containing ours", "UNSEEN", None, ["PRE"],
        "        ld (PREFIX),hl\n")
    # ...nor a bare `ld hl,NAME` (that is the ADDRESS, not a read of the cell)
    arm("an address load is not an access", "UNSEEN", None, ["ADR"],
        "        ld hl,ADR\n")
    print("  selftest: PASS" if not fails else f"  selftest: {fails} FAILURE(S)")
    return fails


def main(argv):
    if "--selftest" in argv:
        return 2 if selftest() else 0
    want = None
    if "--why" in argv:
        want = argv[argv.index("--why") + 1]

    allow = ram_map.load_allow(ALLOW)
    # \U0001f534 THE FLOOR IS STRUCTURAL, NOT A TALLY, AND THE FIRST CUT GOT THAT
    # WRONG. It refused below 100 "because the file had 137 on 2026-09-21" --
    # and the very sweep this tool exists for took it to 83, so the instrument
    # refused its own success. The pin file SHRINKS BY DESIGN; a refusal keyed
    # to a count is a figure that rots [[a-ranked-candidate-rots-like-a-wall]].
    # What it can honestly refuse is a file it could not PARSE at all.
    if not allow:
        print("INSTRUMENT FAULT: parsed 0 pin(s) from "
              f"{os.path.relpath(ALLOW, ROOT)} -- the parse broke, and a clean "
              f"run here would mean nothing.")
        return 2
    files = {c: ram_map.files_for(c) for c in ("basic", "disk")}
    gen = set()
    for comp in files:
        for p in files[comp]:
            if any(p.endswith(g) for g in ram_map.IMPORTED_FILES):
                gen.add(p)
    buckets = {"UNAMBIGUOUS": [], "AMBIGUOUS": [], "UNSEEN": []}
    for comp, names, why in allow:
        if want and why != want:
            continue
        widths, seen, samples = scan(names.split("/"), files[comp])
        v, reach = verdict(widths, seen)
        buckets[v].append((comp, names, why, reach, samples))

    total = sum(len(b) for b in buckets.values())
    print(f"width-scout: {total} pin(s) examined"
          + (f" (--why {want})" if want else "") + "\n")
    for v in ("UNAMBIGUOUS", "AMBIGUOUS", "UNSEEN"):
        rows = buckets[v]
        print(f"== {v} ({len(rows)}) ==")
        for comp, names, why, reach, samples in rows:
            w = f"{reach} B" if reach else "-"
            print(f"  {comp:6} {names:28} {why:11} {w}")
            if v == "AMBIGUOUS":
                for s in samples:
                    print(f"           | {s}")
        print()
    print("🔴 ONLY THE UNAMBIGUOUS SET IS SAFE TO WRITE INTO A DECLARATION. An")
    print("   AMBIGUOUS cell is where a guessed width would have been WRONG, and")
    print("   UNSEEN is not 'one byte' -- it is 'the code cannot speak for it'.")
    if gen:
        print()
        print("🔴 AND NOT INTO THESE -- THEY ARE GENERATED, AND A WIDTH WRITTEN")
        print("   HERE IS WIPED BY THE NEXT BUILD (measured 2026-09-21: three")
        print("   pins were deleted on widths that then vanished):")
        for p in sorted(gen):
            print(f"     {p}   <- fix the width in MAIN's own declaration instead")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
