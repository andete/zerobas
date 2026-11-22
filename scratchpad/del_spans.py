#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""D-CBIOS032: delete dead label spans from basic/ sources, by name.

A span is the label's line through the line before the next label in the same file (tools/check_dead_code.py's
model). Trailing comment / blank lines are KEPT (they introduce the next, live label). A span that contains an
IF / ELSE / ENDIF line is REFUSED (reported), never cut half-way: those are done by hand.

    python3 scratchpad/del_spans.py LABEL ...        # prints what it cut, per file
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LABEL = re.compile(r"^([A-Za-z_]\w*):")
COND = re.compile(r"^\s*(IF|ELSE|ENDIF)\b", re.I)


def files():
    for d in ("basic",):
        for f in sorted(os.listdir(os.path.join(ROOT, d))):
            if f.endswith((".asm", ".inc")):
                yield os.path.join(d, f)


def main(names):
    want = set(names)
    done, refused = [], []
    for rel in files():
        p = os.path.join(ROOT, rel)
        lines = open(p).read().split("\n")
        labs = [(i, LABEL.match(l).group(1)) for i, l in enumerate(lines) if LABEL.match(l)]
        cut = set()
        for k, (i, n) in enumerate(labs):
            if n not in want:
                continue
            j = labs[k + 1][0] if k + 1 < len(labs) else len(lines)
            end = j
            while end > i + 1 and (not lines[end - 1].strip() or lines[end - 1].lstrip().startswith(";")):
                end -= 1
            body = lines[i:end]
            if any(COND.match(l) for l in body):
                refused.append(f"{rel}:{i + 1} {n}")
                continue
            cut.update(range(i, end))
            done.append(f"{rel}:{i + 1} {n} ({end - i} lines)")
            want.discard(n)
        if cut:
            open(p, "w").write("\n".join(l for i, l in enumerate(lines) if i not in cut))
    for d in done:
        print("CUT    ", d)
    for r in refused:
        print("REFUSED", r, "(an IF / ENDIF inside: by hand)")
    for n in sorted(want - {r.split()[-1] for r in refused}):
        print("NOTFOUND", n)


if __name__ == "__main__":
    main(sys.argv[1:])
