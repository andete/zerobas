#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""The CONTROLS of klist_model's rules (docs/spec-method.md §3a: a rule must be shown able to fail). Each control flips
ONE law of the shared small BASIC (kstop_model's `alt` switches) and runs over the reference's cases; it must be FALSE
on some of them.

    python3 probes/basic/spec/klist_controls.py      (exit 1 when a control finds no case against it)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import klist_model as M  # noqa: E402


def alt(*a):
    return lambda c: M.ok(c, frozenset(a))


CONTROLS = {
    "NEW": [("R-NEW-ERASE", "NEW inside a program goes on", alt("new-continues")),
            ("R-NEW-ERASE", "NEW takes the string space back to 200", alt("new-resets-size")),
            ("R-NEW-ERRORS", "NEW with an argument erases, then errors", alt("new-arg-erases"))],
    "LIST": [("R-LIST-RANGE", "LIST n lists from n to the end", alt("list-n-from")),
             ("R-LIST-RANGE", "a reversed range is error 5", alt("list-reversed-error")),
             ("R-LIST-STOP", "the rest of LIST's line runs", alt("list-continues-line")),
             ("R-LIST-STOP", "LIST is a program edit", alt("list-is-edit")),
             ("R-LIST-SPELL", "constants are listed as typed", alt("list-as-typed")),
             ("R-LIST-ERRORS", "a comma separates the range's ends", alt("list-comma-separator"))],
    "DELETE": [("R-DELETE-RANGE", "the low end must exist too", alt("delete-low-must-exist")),
               ("R-DELETE-CHECK", "the high end need not exist", alt("delete-high-free")),
               ("R-DELETE-EDIT", "DELETE keeps the variables and CONT", alt("delete-keeps-vars"))],
    "RENUM": [("R-RENUM-NUMBERS", "an absent new start in the comma forms is 0", alt("renum-comma-start-0")),
              ("R-RENUM-REFS", "a reference to a missing line is error 8", alt("renum-missing-error")),
              ("R-RENUM-REFS", "numbers inside strings are rewritten too", alt("renum-touches-text")),
              ("R-RENUM-CHECK", "overlapping new numbers are allowed", alt("renum-overlap-ok")),
              ("R-RENUM-KEEPS", "RENUM is a program edit", alt("renum-is-edit"))],
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
