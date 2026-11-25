#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""The CONTROLS of kdeftype_model's rules (docs/spec-method.md §3a: a rule must be shown able to fail). Each control
changes ONE law of the interpreter (kdeftype_model.Machine's `alt` switches) -- never a hand-written record -- and is
run over the same reference cases; it must be FALSE on some of them.

    python3 probes/basic/spec/kdeftype_controls.py      (exit 1 when a control finds no case against it)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kdeftype_model as M  # noqa: E402


def alt(*a):
    return lambda c: M.behaves(c, frozenset(a))


def entry_alt(*a):
    return lambda c: M.entry(c, frozenset(a))


CONTROLS = {
    "DEFINT": [("R-INT-LIST", "a list stands only if ALL of it is good", alt("all-or-nothing")),
               ("R-INT-LIST", "a reversed range is swapped, not an error", alt("reversed-swaps")),
               ("R-INT-LIST", "CLEAR keeps the DEF table", alt("clear-keeps-def")),
               ("R-INT-NAME", "a variable keeps the type it was made with", alt("create-time")),
               ("R-INT-NAME", "a suffixed name is a variable apart from the unsuffixed one", alt("suffix-separate")),
               ("R-INT-STORE", "an integer rounds (half away from zero)", alt("int-round")),
               ("R-INT-STORE", "an integer floors (towards minus infinity)", alt("int-floor")),
               ("R-INT-STORE", "the variable is made only after its value is checked", alt("create-after")),
               ("R-INT-ENTRY", "the type byte FOLLOWS the name -- zerobas's order", entry_alt("entry-after-name"))],
    "DEFSNG": [("R-SNG-LIST", "a list stands only if ALL of it is good", alt("all-or-nothing")),
               ("R-SNG-NAME", "a suffixed name is a variable apart from the unsuffixed one", alt("suffix-separate")),
               ("R-SNG-STORE", "a single is CUT to six digits", alt("sng-truncate")),
               ("R-SNG-ENTRY", "the type byte FOLLOWS the name -- zerobas's order", entry_alt("entry-after-name"))],
    "DEFDBL": [("R-DBL-LIST", "a list stands only if ALL of it is good", alt("all-or-nothing")),
               ("R-DBL-NAME", "a suffixed name is a variable apart from the unsuffixed one", alt("suffix-separate")),
               ("R-DBL-STORE", "with no DEF an unsuffixed name is single", alt("default-single")),
               ("R-DBL-ENTRY", "the type byte FOLLOWS the name -- zerobas's order", entry_alt("entry-after-name"))],
    "DEFSTR": [("R-STR-LIST", "a list stands only if ALL of it is good", alt("all-or-nothing")),
               ("R-STR-NAME", "an unsuffixed DEFSTR name is a variable apart from the $ one", alt("defstr-separate")),
               ("R-STR-STORE", "the variable is made only after its value is checked", alt("create-after")),
               ("R-STR-ENTRY", "the type byte FOLLOWS the name -- zerobas's order", entry_alt("entry-after-name"))],
}


def main():
    rc = 0
    for kw, ctl in CONTROLS.items():
        cs = M.load(kw)["ref"]
        rules = {r.id: r for r in M.rules(kw, cs)}
        for rid, what, check in ctl:
            if rid not in rules:
                print(f"{rid:16s} NOT A RULE ON {kw}'s page")
                rc = 1
                continue
            sel = [c for c in cs if rules[rid].select(c)]
            false = [c.id for c in sel if not check(c)]
            print(f"{rid:16s} {what[:62]:62s} FALSE on {len(false):3d} of {len(sel):<3d}"
                  f"{'  e.g. ' + false[0] if false else '  <-- NO CASE AGAINST IT'}")
            rc |= not false
        # every rule must be pinned by a control of its OWN: the check is the whole interpreter, so a rule's ✓ says
        # only that the model agrees -- what pins its SENTENCE is a rival of that sentence's law failing on its cases
        bare = sorted(set(rules) - {rid for rid, _, _ in ctl})
        for rid in bare:
            print(f"{rid:16s} 🔴 NO CONTROL OF ITS OWN")
        rc |= bool(bare)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
