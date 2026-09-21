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

# 🔴 AN ADDRESS LOAD MEANS THERE ARE ACCESSES THIS SCAN CANNOT SEE, AND THE
# FIRST CUT TREATED IT AS SILENCE. `ld hl,NAME` does not read the cell -- a
# selftest arm pins that, and it is right about what the instruction DOES. But
# it is the wrong answer to the question this tool actually asks. Measured
# 2026-09-21: `GFX_SOCT` reads UNAMBIGUOUS 1 B, because the only access spelled
# with its name is `ld a,(GFX_SOCT) / and 7` -- the octant bits. Its full record
# is compared by `ld hl,GFX_SOCT / ld de,GFX_EOCT / ld b,4`, a FOUR-byte pointer
# walk the name-keyed scan is blind to, and the declared `(2)` is correct.
# So a pointer to the cell DEMOTES the verdict: it is precisely the case where
# a derived width is least trustworthy, not most.
PTR = ("hl", "de", "bc", "ix", "iy")


def access_re(name: str) -> re.Pattern:
    """Every `(NAME)` or `(NAME + k)` operand, with the register beside it."""
    n = re.escape(name)
    return re.compile(
        r"(?:ld\s+\(\s*" + n + r"\s*(?:\+\s*(\d+))?\s*\)\s*,\s*([a-z]{1,2})"
        r"|ld\s+([a-z]{1,2})\s*,\s*\(\s*" + n + r"\s*(?:\+\s*(\d+))?\s*\))",
        re.I)


def pointer_re(name: str) -> re.Pattern:
    """`ld rr,NAME` -- the ADDRESS of the cell into a pointer register."""
    return re.compile(r"ld\s+(" + "|".join(PTR) + r")\s*,\s*"
                      + re.escape(name) + r"\s*(?:$|[;,+])", re.I | re.M)


def strip_comment(line: str) -> str:
    return line.split(";", 1)[0]


# 🔴 A COMPONENT'S ACCESSES DO NOT ALL LIVE IN ITS OWN FILE GLOB, AND THIS COST
# THE FIRST CUT A FALSE FINDING. `ram_map.files_for()` answers "where are this
# component's DECLARATIONS", which is the right question for the map and the
# wrong one here: `disk`'s `FAT_SECPERFAT` ($E55B) is written `ld (FAT_SECPERFAT),
# de` in `basic/fat-prim-body.inc` -- a SHARED body `disk.rom` assembles and the
# `disk/*` glob does not contain. The scan saw only `disk/fat.asm`'s byte read
# and reported the declared `(word)` as a disagreement.
# 🎯 THE FIX IS DERIVED, NOT A LIST: a component assembles its own files PLUS
# everything they `include`, transitively. That is the same relation
# `tools/check_shared_bodies.py` uses to decide what "shared" even means.
INCLUDE = re.compile(r'^\s*include\s+"([^"]+)"', re.I | re.M)


def assembled_files(paths):
    """`paths` plus every file they include, transitively. An include path
    containing "/" is repo-root relative -- the same rule check_tenant_closure
    learned the hard way, where "../basic/..." resolved ABOVE the repo and a
    body was silently dropped."""
    seen, queue = list(paths), list(paths)
    while queue:
        p = queue.pop()
        try:
            src = open(os.path.join(ROOT, p)).read()
        except OSError:
            continue
        for inc in INCLUDE.findall(src):
            rel = inc if "/" in inc else os.path.join(os.path.dirname(p), inc)
            if rel not in seen and os.path.exists(os.path.join(ROOT, rel)):
                seen.append(rel)
                queue.append(rel)
    return seen


def scan(names, files):
    """-> (widths seen, max offset+1 seen, sample lines, pointered). Comments
    excluded: a comment naming `ld (X),hl` is prose, not a measurement."""
    pats = [(n, access_re(n), pointer_re(n)) for n in names]
    widths, reach, samples, pointered = set(), 0, [], []
    for path in files:
        try:
            src = open(os.path.join(ROOT, path)).read().splitlines()
        except OSError:
            continue
        for line in src:
            code = strip_comment(line)
            if not code.strip():
                continue
            for n, pat, pptr in pats:
                if pptr.search(code) and len(pointered) < 3:
                    pointered.append(code.strip())
                for m in pat.finditer(code):
                    off = m.group(1) or m.group(4) or "0"
                    reg = (m.group(2) or m.group(3) or "").lower()
                    w = 2 if reg in W2 else 1
                    widths.add(w)
                    reach = max(reach, int(off) + w)
                    if len(samples) < 3:
                        samples.append(code.strip())
    return widths, reach, samples, pointered


def verdict(widths, reach, pointered=()):
    if pointered:
        return "POINTED", (reach or None)
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
        w, r, _, ptr = scan(names, [rel])
        v, got = verdict(w, r, ptr)
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
    # 🔴 ...and a bare `ld hl,NAME` IS STILL NOT A READ OF THE CELL -- but it is
    # PROOF THAT READS EXIST WHICH THIS SCAN CANNOT SEE, so the verdict is
    # POINTED, never UNSEEN and never UNAMBIGUOUS. Measured on GFX_SOCT.
    arm("an address load is not an access, but it IS a warning",
        "POINTED", None, ["ADR"], "        ld hl,ADR\n")
    arm("a pointer OUTRANKS an otherwise clean byte access",
        "POINTED", 1, ["PTD"],
        "        ld a,(PTD)\n        ld hl,PTD\n        ld b,4\n")
    # NEGATIVE: a cell with no pointer anywhere keeps its clean verdict, or the
    # new rule would swallow every answer the tool used to give.
    arm("NEGATIVE: no pointer -> the verdict is unchanged", "UNAMBIGUOUS", 2,
        ["CLN"], "        ld (CLN),hl\n        ld hl,(CLN)\n")
    # ...and an indirect load through the SAME register must not read as a
    # pointer-take: `ld hl,(CLN)` is a word READ, which the arm above pins.
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
    # \U0001f534 ACCESSES, NOT DECLARATIONS -- see assembled_files() above.
    files = {c: assembled_files(ram_map.files_for(c)) for c in ("basic", "disk")}
    gen = set()
    for comp in files:
        for p in files[comp]:
            if any(p.endswith(g) for g in ram_map.IMPORTED_FILES):
                gen.add(p)
    buckets = {"UNAMBIGUOUS": [], "AMBIGUOUS": [], "POINTED": [], "UNSEEN": []}
    for comp, names, why in allow:
        if want and why != want:
            continue
        widths, seen, samples, ptr = scan(names.split("/"), files[comp])
        v, reach = verdict(widths, seen, ptr)
        buckets[v].append((comp, names, why, reach, samples or ptr))

    total = sum(len(b) for b in buckets.values())
    print(f"width-scout: {total} pin(s) examined"
          + (f" (--why {want})" if want else "") + "\n")
    for v in ("UNAMBIGUOUS", "AMBIGUOUS", "POINTED", "UNSEEN"):
        rows = buckets[v]
        print(f"== {v} ({len(rows)}) ==")
        for comp, names, why, reach, samples in rows:
            w = f"{reach} B" if reach else "-"
            print(f"  {comp:6} {names:28} {why:11} {w}")
            if v in ("AMBIGUOUS", "POINTED"):
                for s in samples:
                    print(f"           | {s}")
        print()
    print("🔴 ONLY THE UNAMBIGUOUS SET IS SAFE TO WRITE INTO A DECLARATION. An")
    print("   AMBIGUOUS cell is where a guessed width would have been WRONG;")
    print("   UNSEEN is not 'one byte' -- it is 'the code cannot speak for it';")
    print("   and POINTED means a pointer is taken to the cell, so accesses")
    print("   exist that a NAME-keyed scan cannot see at all (GFX_SOCT: 1 B by")
    print("   this reading, 4 B by the pointer walk, and `(2)` is correct).")
    if gen:
        print()
        print("🔴 AND NOT INTO THESE -- THEY ARE GENERATED, AND A WIDTH WRITTEN")
        print("   HERE IS WIPED BY THE NEXT BUILD (measured 2026-09-21: three")
        print("   pins were deleted on widths that then vanished):")
        for p in sorted(gen):
            print(f"     {p}   <- fix the width in MAIN's own declaration instead")
    abi_width_audit()
    return 0


def abi_width_audit():
    """Published ABI cells whose width lives BELOW their `equ` line.

    🔴 WHY THIS EXISTS. `tools/gen_resident_abi.py` copies each published cell's
    comment so the width travels to disk.rom and sub.rom -- but `_scrape_origin`
    reads the `equ` LINE ONLY. A width spelled one line down (the `SH_SRC` shape,
    which this tree uses constantly) is therefore DROPPED, and the imported cell
    arrives width-less. Measured 2026-09-21: that is the entire reason
    `disk DISKOP_STATUS`, `disk FN_RESUME` and `disk STRSCR` were pinned.

    ⚠️ IT IS ADVISORY, NOT A GATE, AND THE REASON IS `TXTBASE`. A hit means the
    joined block declares a width the line does not -- which is EITHER a real
    width being lost OR a FALSE reading of the joined block. `TXTBASE`'s joined
    comment yields **2304**, off `TXTMAX`'s preamble ("Lowered 2304 B below the
    $C000 BLOAD ceiling"); TXTBASE has no such extent. Refusing on this signal
    would demand a fix where the right action is nothing
    [[a-claim-about-empty-space-read-as-a-cells-extent]].

    🎯 THE FIX FOR A REAL ONE IS THE SOURCE, NOT THE GENERATOR: move the width
    onto the declaration LINE, and the line-only scrape becomes right by
    construction. Teaching the generator to join would carry the hazardous block
    across too, TXTBASE's 2304 with it.
    """
    pub = set()
    for f in ("disk/basic-resident-abi.inc", "sub/basic-resident-abi.inc"):
        try:
            src = open(os.path.join(ROOT, f)).read()
        except OSError:
            continue
        pub |= set(re.findall(r"^([A-Za-z_][A-Za-z0-9_]*)\s+equ\s", src, re.M))
    m = ram_map.Map("basic", 0xE000, ram_map.DOC_HI)
    line, _ = ram_map.parse(m.files, joint=False)
    lost = []
    for n in sorted(pub):
        base = n[5:] if n.startswith("main_") else n
        a = m.vals.get(base)
        if a is None or base not in m.expr:
            continue
        wl, _r = ram_map.declared_width(a, line.get(base, (None,) * 4)[3])
        wj, rj = ram_map.declared_width(a, m.expr[base][3])
        if wl is None and wj is not None:
            lost.append((n, base, a, wj, rj))
    print()
    print(f"🔎 ABI WIDTH AUDIT -- {len(lost)} published cell(s) declare a width "
          f"only BELOW the `equ` line, so the generator's line-only scrape drops it:")
    if not lost:
        print("     none -- every published cell's width is on its own line.")
        return
    for n, base, a, wj, rj in lost:
        print(f"     {n:16} ${a:04X}  joined says {wj} ({rj}), line says nothing")
    print("   ⚠️ A hit is EITHER a real width being lost OR a false read of the")
    print("      joined block (TXTBASE yields 2304 off TXTMAX's preamble, and has")
    print("      no such extent). Read it; the fix for a real one is to move the")
    print("      width onto the declaration LINE, never to join in the generator.")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
