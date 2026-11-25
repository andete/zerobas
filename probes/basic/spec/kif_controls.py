#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""The CONTROLS of kif_model's rules (docs/spec-method.md §3a: a rule must be shown able to fail). Each control is
a rival rule the probe separates, run over the same reference cases; it must be FALSE on some of them.

    python3 probes/basic/spec/kgosub_controls.py      (exit 1 when a control finds no case against it)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kif_model as M  # noqa: E402


def alt(*a):
    return lambda c: M.ok(c, frozenset(a))


CONTROLS = {
    "IF": [("R-IF-LINE", "a false IF skips only THEN's statement", alt("false-skips-then-only")),
           ("R-IF-ELSE", "an ELSE belongs to the OUTER IF", alt("else-outer")),
           ("R-IF-ELSE", "ELSE runs only its own statement", alt("else-one-stmt")),
           ("R-IF-TRUTH", "a fraction or a tiny number is false (truncated to 0)", alt("fraction-false")),
           ("R-IF-EMPTY", "THEN followed by nothing is a Syntax error", alt("then-empty-syntax"))],
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
