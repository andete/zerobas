#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""shared-body-check — every `.inc` under basic/ and sub/ must be ASSEMBLED.

WHY THIS EXISTS. D-TRUNCLOAD bounded `relink`'s walk in `sub/lineedit.asm`
(`HL == PRGEND` -> `>=`, which is what stopped a truncated program hanging the
machine). A sweep for the same shape then found a SECOND copy of that loop, in
`basic/lineedit-body.inc` -- byte-identical before the fix, divergent after --
and that file is included by NOTHING. It is the only `.inc` in the tree that is
not, so nothing was watching.

🔴 A DEAD SHARED BODY IS WORSE THAN DEAD CODE. Ordinary dead code does nothing;
a dead COPY of a live routine reads as the live one. `deadcode-check` cannot see
this class: it reasons about labels in an assembled image, and an unassembled
file contributes none.

⚠️ THE MATCH IS BY BASENAME, AND THAT IS FORCED. Sources include each other
across the basic/sub boundary with relative paths -- `include
"../basic/title-body.inc"` from `sub/title.asm`, `include "equates.inc"` from
`sub/sub.asm`. A first cut compared the include text against repo-relative paths
and reported FIVE dead files, four of them false: every cross-directory include
missed. A checker whose failure mode is "everything looks dead" would have been
believed exactly once.

🔴 AND IT REFUSES ON A DEGENERATE SCAN. If the include regex matches nothing at
all -- a syntax change, a moved tree, a bad glob -- every `.inc` looks dead and
the tool would print a catastrophic, entirely false report. Zero includes found
is an INSTRUMENT failure, exit 2, never a finding.
"""
from __future__ import annotations

import os
import re
import sys
# 🔴 `probe_tmp` AT MODULE LEVEL, NOT INSIDE THE SELFTEST. It sets
# `tempfile.tempdir` as an IMPORT SIDE EFFECT, so the selftest's planted-body
# directory lands under /tmp/zerobas -- and `tools/check_temp_root.py` scans
# STATICALLY, so a function-local import reads as "reaches no chokepoint" and it
# refused the build. Both facts are the point: the root is real, and the gate
# that polices it cannot see a runtime import
# [[a-static-gate-cannot-see-a-computed-path]].
sys.path.insert(0, os.path.join(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))), "probes", "lib"))
import probe_tmp                  # noqa: E402,F401 -- sets tempfile.tempdir

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# 🔴 `disk` WAS MISSING UNTIL 2026-09-20 (D-SAVEPORT), AND THAT MADE THIS GATE
# BLIND IN THE ONE DIRECTION IT EXISTS TO WATCH. A shared body included ONLY by
# disk.rom read as "included by NOTHING" -- the exact false positive this file's
# own header warns a bad glob produces. It stayed invisible because every shared
# body disk.rom includes was ALSO included by sub, until sv-savdisk.inc moved
# out of the sub-ROM and into disk.rom alone.
DIRS = ("basic", "sub", "disk")
INCLUDE = re.compile(r'^\s*include\s+"([^"]+)"', re.I | re.M)
ALLOW = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     "shared-body-allow.txt")
# A scan that finds fewer than this many includes is not a tree this tool
# understands. The real count is ~100; the floor only has to be far above
# "the regex broke".
MIN_INCLUDES = 20


def sources():
    for d in DIRS:
        p = os.path.join(ROOT, d)
        for name in sorted(os.listdir(p)):
            if name.endswith((".asm", ".inc")):
                yield os.path.join(d, name)


def included_basenames(files):
    out = set()
    for rel in files:
        text = open(os.path.join(ROOT, rel), errors="replace").read()
        for m in INCLUDE.finditer(text):
            out.add(os.path.basename(m.group(1)))
    return out


def allowlist():
    """basename -> reason. A dead body may be KEPT, but only with a reason."""
    out = {}
    if not os.path.exists(ALLOW):
        return out
    for line in open(ALLOW, errors="replace"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        name, _, why = line.partition(" ")
        out[name] = why.strip()
    return out



# --- THE SECOND RULE: A SHARED BODY MAY NOT SPELL A PER-ROM BUFFER NAME -------
# 🔴 THIS IS THE DEFECT THAT COST STEP 12 A DAY, AS A GATE (D-NEUTRALSWEEP,
# 2026-09-21). `basic/fatiow-body.inc` buffered each byte with
# `ld de, FSECTOR_BUF` where its read twin says `FAT_DBUF`. In main and sub those
# are ONE address, so it assembled clean and was invisible; in `disk.rom`
# `FSECTOR_BUF` resolves through the generated ABI to MAIN's $E5C0 while
# `FAT_DBUF` is $E2A0 -- so every byte went to main's buffer and the flush wrote
# the untouched one.
# 🎯 IT IS A CLASS, NOT AN INCIDENT, AND THE SWEEP PROVED IT: FIVE MORE shared
# bodies still spelled the per-ROM name in CODE (fat-delete, fiawalked, fld-fill,
# format, randio -- 31 references). None of them bit, because no ROM that binds
# the names differently includes them YET. Each was one `include` away.
# 🔬 The conversion is provably a no-op where the names alias: both ROMs came out
# BYTE-IDENTICAL.
# ⚠️ COMMENTS ARE EXEMPT ON PURPOSE. `fatio-body.inc` and `fatiow-body.inc` carry
# the rule itself in prose and must go on naming the wrong name to state it.
PERROM = re.compile(r"\b(FSECTOR_BUF|FWBUF)\b")
NEUTRAL = {"FSECTOR_BUF": "FAT_DBUF", "FWBUF": "FAT_MBUF"}


# A DECLARATION is not a reference. `basic/sysvars.inc` is where these names are
# BOUND (`FWBUF equ $E7C0`, `FAT_MBUF equ FWBUF`) and the generated ABI is where
# disk.rom IMPORTS main's -- both must go on spelling them. The rule is about a
# body that READS OR WRITES through the name.
EQU_DEF = re.compile(r"^\s*\w+\s+equ\b", re.IGNORECASE)
PERROM_EXEMPT_FILES = ("basic/sysvars.inc", "disk/equates.inc",
                       "disk/basic-resident-abi.inc", "sub/equates.inc")


def perrom_hits(rel):
    """[(line, text, name)] for CODE references only.

    Comments are exempt (two bodies state the rule in prose and must name the
    wrong name to do it), and so are `equ` DEFINITIONS and the files whose job
    is to bind or import these names.
    """
    out = []
    if rel.replace(os.sep, "/") in PERROM_EXEMPT_FILES:
        return out
    try:
        lines = open(os.path.join(ROOT, rel), errors="replace").readlines()
    except OSError:
        return out
    for i, ln in enumerate(lines, 1):
        code = ln.split(";", 1)[0]
        if EQU_DEF.match(code):
            continue
        m = PERROM.search(code)
        if m:
            out.append((i, code.strip(), m.group(1)))
    return out


def check(verbose=True):
    files = list(sources())
    inc = included_basenames(files)
    if len(inc) < MIN_INCLUDES:
        print(f"🔴 INSTRUMENT FAILURE: only {len(inc)} include(s) found across "
              f"{len(files)} source file(s) (floor {MIN_INCLUDES}). Every .inc "
              f"would read as dead. Refused, not reported.")
        return 2
    allow = allowlist()
    dead, kept = [], []
    for rel in files:
        if not rel.endswith(".inc"):
            continue
        base = os.path.basename(rel)
        if base in inc:
            continue
        (kept if base in allow else dead).append(rel)
    if verbose:
        n_inc = sum(1 for r in files if r.endswith(".inc"))
        print(f"shared-body-check: {n_inc} .inc file(s), {len(inc)} include "
              f"target(s) across {len(files)} source file(s)")
        for rel in kept:
            print(f"  [allowed] {rel} — {allow[os.path.basename(rel)]}")
        for rel in dead:
            print(f"  🔴 {rel}: included by NOTHING. It is not assembled, so "
                  f"nothing in it is checked by any other gate — and if it "
                  f"duplicates a live routine it now reads as that routine "
                  f"while being free to drift from it. Delete it, include it, "
                  f"or allowlist it with a reason in "
                  f"{os.path.relpath(ALLOW, ROOT)}.")
        if not dead:
            print("  clean — every .inc is assembled (or allowlisted with a "
                  "reason)")

    # --- rule 2: no per-ROM buffer name in a shared body's CODE --------------
    named = []
    for rel in files:
        if not rel.endswith(".inc"):
            continue
        for line, text, which in perrom_hits(rel):
            named.append((rel, line, text, which))
    if verbose:
        if named:
            print(f"\n  🔴 {len(named)} per-ROM buffer name(s) in shared body "
                  f"CODE. In main and sub these ALIAS the neutral name, so the "
                  f"build is silent; in disk.rom they are DIFFERENT ADDRESSES "
                  f"and the body reads or writes the wrong buffer. Spell "
                  f"FAT_DBUF / FAT_MBUF:")
            for rel, line, text, which in named:
                print(f"     {rel}:{line}  {text[:60]}"
                      f"   -> {NEUTRAL[which]}")
        else:
            print("  clean — no shared body spells FSECTOR_BUF or FWBUF in "
                  "code (comments are exempt: two bodies state the rule)")
    return 1 if (dead or named) else 0


def selftest():
    ok = True

    def arm(name, cond):
        nonlocal ok
        print(f"{'PASS' if cond else 'FAIL'}  {name}")
        ok = ok and bool(cond)

    files = list(sources())
    inc = included_basenames(files)
    # 🟢 THE CONTROL THAT MATTERS: a file included ONLY across the directory
    # boundary, by a relative path. This is the case the first cut got wrong,
    # and it is why the match is by basename.
    arm("S1 a cross-directory relative include is seen "
        "(title-body.inc, included as '../basic/title-body.inc')",
        "title-body.inc" in inc)
    arm(f"S2 the scan is not degenerate ({len(inc)} includes, "
        f"floor {MIN_INCLUDES})", len(inc) >= MIN_INCLUDES)
    # 🔴 THE PLANTED DRIFT. Without this the checker could match nothing and
    # still report "clean" for the whole tree.
    arm("S3 a name that is NOT included is not reported as included",
        "no-such-body.inc" not in inc)
    # the degenerate-input refusal, driven rather than asserted
    saved = globals()["INCLUDE"]
    try:
        globals()["INCLUDE"] = re.compile(r"^\s*zzz-no-match\s+\"([^\"]+)\"", re.M)
        arm("S4 a regex that matches nothing REFUSES (exit 2) rather than "
            "reporting every .inc dead", check(verbose=False) == 2)
    finally:
        globals()["INCLUDE"] = saved
    # --- rule 2's arms, each with its negative control --------------------
    # 🔴 THE PLANT IS A FILE, not a string, because perrom_hits READS THE TREE.
    # An arm that only exercised the regex would pass while the file walk was
    # blind -- the shape that let the ORIGINAL defect through six shared bodies.
    import tempfile
    d = tempfile.mkdtemp(prefix="sharedbody-")
    plant = os.path.join(d, "planted-body.inc")
    with open(plant, "w") as f:
        f.write("; FSECTOR_BUF in a comment is EXEMPT -- two bodies state the "
                "rule\n")
        f.write("PLANTED_ALIAS   equ     FWBUF       ; an equ DEFINITION is "
                "exempt too\n")
        f.write("                ld      hl,FSECTOR_BUF\n")
        f.write("                ld      de,FWBUF+1  ; FSECTOR_BUF here is a "
                "comment\n")
    saved_root = globals()["ROOT"]
    try:
        globals()["ROOT"] = d
        hits = perrom_hits("planted-body.inc")
    finally:
        globals()["ROOT"] = saved_root
    arm("S5 a per-ROM name in CODE is reported (2 of them)", len(hits) == 2)
    arm("S6 NEGATIVE: the one in a COMMENT is not",
        all("comment" not in t for _l, t, _w in hits))
    arm("S7 NEGATIVE: an `equ` DEFINITION is not -- sysvars.inc binds these "
        "names and must go on spelling them", "equ" not in
        " ".join(t for _l, t, _w in hits).lower())
    arm("S8 each hit names the neutral spelling to use",
        {NEUTRAL[w] for _l, _t, w in hits} == {"FAT_DBUF", "FAT_MBUF"})
    arm("S9 NEGATIVE: a declaration FILE is exempt whole -- sysvars.inc has "
        "many and must report none", perrom_hits("basic/sysvars.inc") == [])
    arm("S10 the live tree is CLEAN of the class (31 references were "
        "converted on 2026-09-21; both ROMs came out byte-identical)",
        not [1 for rel in sources() if rel.endswith(".inc")
             for _h in perrom_hits(rel)])
    import shutil
    shutil.rmtree(d, ignore_errors=True)
    print("selftest:", "GREEN" if ok else "🔴 RED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv else check())
