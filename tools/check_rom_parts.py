#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Every file a ROM INCLUDES must be a prerequisite of that ROM.

🔴 WRITTEN BECAUSE IT HAPPENED (2026-09-03, D-PUDOT). `sub/punum.asm` was added
as a new sub-ROM tenant and never put in `SUB_PARTS`, so `make sub` answered
"nothing to be done" after a FULL REWRITE of that tenant and `build/sub.rom`
silently kept the old body. The Makefile already carried a memory link for this
exact shape -- `[[makefile-subparts-stale-tenant]]`, from a previous occurrence
-- and there was still no check. A lesson with no gate is a lesson that gets
re-learned.

WHAT IT COMPARES. The TRANSITIVE include closure of each ROM's top source
against the prerequisites the Makefile actually gives that ROM's rule -- the
`*_PARTS` variable plus anything named directly on the target line. A file in
the closure but not in the prerequisites is a REBUILD THAT WILL NOT HAPPEN.

⚠️ IT ALSO REPORTS THE REVERSE, and does not fail on it. A prerequisite that is
no longer included is harmless (an extra rebuild), but it is usually a rename
nobody finished, so it is worth seeing.

🔴 REFUSES A DEGENERATE PARSE rather than printing a clean bill of health: zero
includes found, or zero prerequisites parsed, exits 2. An instrument that
answers from an input it misread is the failure this tree keeps filing.
"""
from __future__ import annotations

import os
import re
import sys

ROMS = [
    # label,           top source,      Makefile target line prefix
    ("sub.rom",  "sub/sub.asm",   "$(SUB_ROM):"),
    ("disk.rom", "disk/disk.asm", "$(DISK_ROM):"),
]
INC = re.compile(r'^\s*include\s+"([^"]+)"', re.M)


def makefile_text() -> str:
    """The Makefile with line continuations JOINED.

    🔴 WITHOUT THIS THE GATE LIES CONFIDENTLY. `SUB_PARTS` spans a dozen
    backslash-continued lines; parsing line-at-a-time saw only the first, so the
    first run reported 63 files "missing" that are listed right there. An
    instrument that reads its input wrong produces a plausible table, which is
    exactly the failure this file's own docstring is about."""
    return open("Makefile").read().replace("\\\n", " ")


def var_value(mk: str, name: str) -> list[str]:
    m = re.search(rf'^{re.escape(name)}\s*:?=\s*(.*(?:\\\n.*)*)$', mk, re.M)
    if not m:
        return []
    return m.group(1).replace("\\\n", " ").split()


def prereqs(mk: str, target: str) -> list[str]:
    m = re.search(rf'^{re.escape(target)}(.*)$', mk, re.M)
    if not m:
        return []
    out = []
    for tok in m.group(1).split():
        if tok == "|":
            break
        v = re.fullmatch(r'\$\((\w+)\)', tok)
        out.extend(var_value(mk, v.group(1)) if v else [tok])
    return out


def closure(top: str) -> set[str]:
    """Every file transitively included from `top`, as repo-relative paths."""
    seen, todo = set(), [top]
    root = os.path.dirname(top)
    while todo:
        f = todo.pop()
        if f in seen or not os.path.isfile(f):
            continue
        seen.add(f)
        for name in INC.findall(open(f, errors="replace").read()):
            for cand in (name, os.path.join(root, name)):
                if os.path.isfile(cand):
                    todo.append(os.path.normpath(cand))
                    break
    return seen - {top}


def main() -> int:
    mk = makefile_text()
    bad = 0
    for label, top, target in ROMS:
        inc = closure(top)
        pre = {os.path.normpath(p) for p in prereqs(mk, target)}
        if not inc:
            print(f"REFUSED: parsed ZERO includes from {top} -- the `include \"…\"` "
                  "form must have changed; nothing was checked")
            return 2
        if not pre:
            print(f"REFUSED: parsed ZERO prerequisites for {target} -- nothing "
                  "was checked")
            return 2
        missing = sorted(inc - pre - {top})
        extra = sorted(p for p in pre - inc - {os.path.normpath(top)}
                       if p.endswith((".asm", ".inc")) and os.path.isfile(p))
        if missing:
            bad += len(missing)
            print(f"FAIL: {label} INCLUDES {len(missing)} file(s) that are NOT "
                  f"prerequisites of {target} -- an edit to any of them will NOT "
                  "trigger a rebuild, and the ROM will go quietly stale:")
            for p in missing:
                print(f"        {p}")
        else:
            print(f"OK: {label} -- all {len(inc)} included file(s) are "
                  f"prerequisites ({len(pre)} listed)")
        for p in extra:
            print(f"  [note] {p} is a prerequisite of {target} but is not "
                  "included any more (harmless; usually an unfinished rename)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
