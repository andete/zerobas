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
    return 1 if dead else 0


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
    print("selftest:", "GREEN" if ok else "🔴 RED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv else check())
