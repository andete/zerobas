#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-PASMO053 gate -- no `equ` whose value pasmo 0.5.3 cannot know yet is USED
above its own line.

pasmo 0.5.3 (what Debian / Ubuntu ship) assembles in two passes. An `equ` is
evaluated where it stands; in pass 1 a name it refers to that is defined LATER
is still unknown, so the equ gets 0. In pass 2 the equ line is re-evaluated --
but every use ABOVE it has already been assembled with the pass-1 value. 0.5.5
gets this right, so nothing fails: 0.5.3 just builds a ROM with $0000 operands.
On 2026-10-11 that was 13 jump / pointer operands in main, every one a use of a
label ALIAS (`X equ lbl`) above its equ line (basic/aliases-early.inc).

This walks each build's include-expanded source in assembly order, simulates
pass 1 (which names are known at each line), marks every equ whose expression
names something not yet known -- transitively -- as LATE, and reports every
use of a LATE name above its equ line. Plain forward references to LABELS are
fine on both versions and are not reported.

Exit 0 clean; 1 findings; 2 the walk itself failed (an include not found, or
the self-test went blind).
"""
from __future__ import annotations

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILDS = (("basic/main.asm", ()), ("sub/sub.asm", ("sub",)), ("disk/disk.asm", ("disk",)))
INCLUDE = re.compile(r'^\s+include\s+"([^"]+)"', re.I)
LABEL = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*):")
EQU = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s+equ\s+(.+)$", re.I)
IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
STRING = re.compile(r'"[^"]*"|\'[^\']*\'')
# number literals, removed BEFORE identifiers are collected: `$F348` is not a
# name F348 (the first cut read it as one and flagged 30 constants)
NUMBER = re.compile(r"\$[0-9A-Fa-f]+|0[xX][0-9A-Fa-f]+|%[01]+|\b[0-9][0-9A-Fa-f]*[hHbBoOqQ]?\b")


def names(expr: str) -> set:
    return set(IDENT.findall(NUMBER.sub(" ", expr)))


def code_part(line: str) -> str:
    """The line without its comment and without string / char literals."""
    out, q = [], None
    for ch in line:
        if q:
            if ch == q:
                q = None
            continue
        if ch in "\"'":
            q = ch
            continue
        if ch == ";":
            break
        out.append(ch)
    return "".join(out)


def expand(path: str, incdirs, seen=None, depth=0):
    """[(file, lineno, text)] in assembly order, includes inlined."""
    if depth > 30:
        raise RuntimeError(f"include depth > 30 at {path}")
    out = []
    for n, raw in enumerate(open(os.path.join(ROOT, path), errors="replace"), 1):
        m = INCLUDE.match(raw)
        if m:
            inc = m.group(1)
            base = os.path.dirname(path)
            for cand in [inc] + [os.path.normpath(os.path.join(d, inc)) for d in incdirs] \
                    + [os.path.normpath(os.path.join(base, inc))]:
                if os.path.exists(os.path.join(ROOT, cand)):
                    out += expand(cand, incdirs, seen, depth + 1)
                    break
            else:
                raise RuntimeError(f"{path}:{n}: include {inc!r} not found")
            continue
        out.append((path, n, raw.rstrip("\n")))
    return out


def findings(lines):
    known, late, defline = set(), set(), {}
    # pass 1: what is known where, and which equs are LATE
    for i, (_f, _n, raw) in enumerate(lines):
        code = code_part(raw)
        m = EQU.match(code.strip()) if not code[:1].isspace() else None
        if m:
            name, expr = m.group(1), m.group(2)
            refs = names(expr)
            if any((r not in known) or (r in late) for r in refs):
                late.add(name)
            known.add(name)
            defline.setdefault(name, i)
            continue
        m = LABEL.match(code)
        if m:
            known.add(m.group(1))
    if not late:
        return []
    out = []
    for i, (f, n, raw) in enumerate(lines):
        code = code_part(raw)
        lab = LABEL.match(code)
        body = code[lab.end():] if lab else code
        if EQU.match(code.strip()) and not code[:1].isspace():
            body = EQU.match(code.strip()).group(2)
        for t in names(body) & late:
            if i < defline[t]:
                df, dn, _ = lines[defline[t]]
                out.append(f"{f}:{n}: uses {t} above its equ ({df}:{dn}) -- pasmo 0.5.3 "
                           f"assembles it as 0 (its value is not known in pass 1)")
    return out


def selftest() -> int:
    cases = {
        "bites": ("        jp X\nX equ lbl\nlbl:\n        ret\n", 1),
        "alias after its target": ("lbl:\n        ret\nX equ lbl\n        jp X\n", 0),
        "used below its line": ("X equ lbl\nlbl:\n        jp X\n", 0),
        # a chain is TWO findings: Y used above Y's line, AND Y's own equ uses X
        # above X's line -- Y takes X's pass-1 zero, so Y is wrong everywhere
        "chain": ("        jp Y\nY equ X\nX equ lbl\nlbl:\n        ret\n", 2),
        "constant": ("        ld hl,K\nK equ $F348\n", 0),
    }
    bad = 0
    for name, (src, want) in cases.items():
        # in memory: findings() takes the expanded lines, no file is needed
        lines = [("t.asm", n, l) for n, l in enumerate(src.split("\n"), 1)]
        got = len(findings(lines))
        ok = got == want
        bad += not ok
        print(f"{'PASS' if ok else 'FAIL'}  selftest {name}: {got} finding(s) (want {want})")
    return 2 if bad else 0


def main() -> int:
    if "--selftest" in sys.argv:
        return selftest()
    total = []
    for src, inc in BUILDS:
        try:
            lines = expand(src, inc)
        except RuntimeError as e:
            print(f"WALK FAILED: {e}")
            return 2
        f = findings(lines)
        print(f"{src}: {len(lines)} lines walked, {len(f)} finding(s)")
        total += f
    for x in total:
        print("  " + x)
    print(f"\n{'CLEAN' if not total else 'FAIL'}: an equ pasmo 0.5.3 cannot resolve in "
          f"pass 1, used above its own line ({len(total)})")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
