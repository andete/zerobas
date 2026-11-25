#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""The CONTROLS of kdim_model's rules (docs/spec-method.md §3a: a rule must be shown able to fail). Each control flips
ONE law of the shared small BASIC (kstop_model's `alt` switches) and runs over the reference's cases; it must be FALSE
on some of them.

    python3 probes/basic/spec/kdim_controls.py      (exit 1 when a control finds no case against it)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kdim_model as M  # noqa: E402


def alt(*a):
    return lambda c: M.ok(c, frozenset(a))


CONTROLS = {
    "DIM": [("R-DIM-BOUNDS", "an undeclared array has bound 9", alt("auto-bound-9")),
            ("R-DIM-BOUNDS", "a negative subscript is error 9", alt("neg-subscript-9")),
            ("R-DIM-SIZE", "there is no 65535-byte limit, only free memory", alt("dim-memory-first")),
            ("R-DIM-NAMES", "the name as written (suffix and all) is the identity", alt("array-suffix-names")),
            ("R-DIM-FORMS", "a DIM that fails makes none of its arrays", alt("dim-all-or-nothing"))],
    "ERASE": [("R-ERASE-REMOVE", "an ERASE that fails erases none of its names", alt("erase-all-or-nothing")),
              ("R-ERASE-ERRORS", "ERASE ignores the type suffix", alt("erase-any-type"))],
    "CLEAR": [("R-CLEAR-RESET", "CLEAR keeps ON ERROR", alt("clear-keeps-onerror")),
              ("R-CLEAR-RESET", "CLEAR keeps READ's position", alt("clear-keeps-data-ptr")),
              ("R-CLEAR-SIZE", "a bare CLEAR goes back to 200 bytes", alt("bare-clear-resets-size")),
              ("R-CLEAR-ERRORS", "a refused CLEAR has already cleared the variables", alt("refused-clear-partial")),
              ("R-CLEAR-ERRORS", "a comma and no top is error 2", alt("clear-comma-syntax")),
              ("R-CLEAR-ERRORS", "Overflow only past 65535", alt("clear-bound-65535")),
              ("R-CLEAR-ERRORS", "the top is not checked against the size", alt("clear-top-unchecked"))],
}


def main():
    rc = 0
    for kw, ctl in CONTROLS.items():
        cs = M.load(kw)["ref"]
        rules = {r.id: r for r in M.rules(kw)}
        for rid, what, check in ctl:
            sel = [c for c in cs if rules[rid].select(c)]
            false = [c.id for c in sel if not check(c)]
            print(f"{rid:18s} {what[:62]:62s} FALSE on {len(false):3d} of {len(sel):<3d}"
                  f"{'  e.g. ' + false[0] if false else '  <-- NO CASE AGAINST IT'}")
            rc |= not false
        bare = sorted(set(rules) - {rid for rid, _, _ in ctl})    # every rule pinned by a control of its own
        for rid in bare:
            print(f"{rid:18s} 🔴 NO CONTROL OF ITS OWN")
        rc |= bool(bare)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
