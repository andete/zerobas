#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""The D-DUPSPAN2 alias roster, taken from the SOURCE rather than from the spec.

The item owes "one row per aliased site", and the first thing a per-site row set
needs is a per-site DENOMINATOR that is not a sentence. The spec says "28 aliases
in 16 files"; this counts the markers the slice actually left in the tree.

🔴 AN ALIAS IS SPELLED TWO WAYS and a scanner that knows one undercounts.
`ee_synerr_pop:` is a LABEL; `poke_err equ ex_let_err` is an EQU. A first cut
looked only for `^name:` and resolved 22 of 27 markers -- the five it "could not
find" were all EQUs, which are the clearest aliases in the tree.
"""
from __future__ import annotations

import collections
import re
import subprocess
import sys

MARK = re.compile(r"D-DUPSPAN2: an ALIAS, not a second copy -- byte-identical to (\w+)")
NAME = re.compile(r"^(\w+)\s*:|^(\w+)\s+equ\s+", re.I)


def main() -> int:
    files = [f for f in subprocess.run(["git", "ls-files", "basic", "sub"],
                                       capture_output=True, text=True).stdout.split()
             if f.endswith((".asm", ".inc"))]
    pairs, unresolved = [], []
    for f in files:
        L = open(f).read().splitlines()
        for i, line in enumerate(L):
            m = MARK.search(line)
            if not m:
                continue
            lbl = None
            for j in list(range(i + 1, min(i + 14, len(L)))) + \
                     list(range(i - 1, max(i - 14, -1), -1)):
                nm = NAME.match(L[j])
                if nm:
                    lbl = nm.group(1) or nm.group(2)
                    break
            (pairs if lbl else unresolved).append((lbl or "?", m.group(1), f, i + 1))
    print(f"D-DUPSPAN2 alias markers in source : {len(pairs) + len(unresolved)}")
    print(f"  resolved to an alias name        : {len(pairs)}")
    print(f"  files                            : {len({p[2] for p in pairs})}")
    print(f"  distinct canonicals              : "
          f"{len({p[1] for p in pairs})}")
    if unresolved:
        print(f"  🔴 UNRESOLVED: {unresolved}")
        return 2
    for a, c, f, ln in sorted(pairs):
        print(f"    {a:22s} -> {c:22s} {f}:{ln}")
    print(f"\n⚠️ the spec (docs/spec-basic-dupspan2.md §3) says '28 aliases in "
          f"16 files'. Source says {len(pairs)} in "
          f"{len({p[2] for p in pairs})}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
