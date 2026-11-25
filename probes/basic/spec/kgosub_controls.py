#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""The CONTROLS of kgosub_model's rules (docs/spec-method.md §3a: a rule must be shown able to fail). Each control is
a rival rule the probe separates, run over the same reference cases; it must be FALSE on some of them.

    python3 probes/basic/spec/kgosub_controls.py      (exit 1 when a control finds no case against it)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kgosub_model as M  # noqa: E402


def alt(*a):
    return lambda c: M.ok(c, frozenset(a))


CONTROLS = {
    "GOTO": [("R-GOTO-GOTO", "`GO TO` is no keyword (a Syntax error) -- zerobas's", alt("no-goto-space")),
             ("R-GOTO-ERRORS", "a line past 65529 is a Syntax error", alt("big-line-syntax")),
             ("R-GOTO-ERRORS", "text after the line number is a Syntax error", alt("trailing-syntax"))],
    "RETURN": [("R-RETURN-FRAMES", "RETURN keeps the subroutine's FOR frames", alt("return-keeps-for")),
               ("R-RETURN-FRAMES", "NEXT in a subroutine reaches a FOR outside it", alt("next-crosses-gosub")),
               ("R-RETURN-BACK", "RETURN n ignores n and comes back after the GOSUB", alt("return-line-ignored"))],
}


def main():
    rc = 0
    for kw, ctl in CONTROLS.items():
        cs = M.load(kw)["ref"]
        rules = {r.id: r for r in M.rules(kw)}
        for rid, what, check in ctl:
            sel = [c for c in cs if rules[rid].select(c)]
            false = [c.id for c in sel if not check(c)]
            print(f"{rid:16s} {what[:62]:62s} FALSE on {len(false):3d} of {len(sel):<3d}"
                  f"{'  e.g. ' + false[0] if false else '  <-- NO CASE AGAINST IT'}")
            rc |= not false
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
