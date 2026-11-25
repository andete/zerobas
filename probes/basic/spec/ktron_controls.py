#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""The CONTROLS of ktron_model's rules (docs/spec-method.md §3a: a rule must be shown able to fail). Each control flips
ONE law of the shared small BASIC (kstop_model's `alt` switches) and runs over the reference's cases; it must be FALSE
on some of them.

    python3 probes/basic/spec/ktron_controls.py      (exit 1 when a control finds no case against it)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ktron_model as M  # noqa: E402


def alt(*a):
    return lambda c: M.ok(c, frozenset(a))


CONTROLS = {
    "TRON": [("R-TRON-TRACE", "a line is traced once per statement", alt("trace-per-statement")),
             ("R-TRON-TRACE", "going on after a RETURN traces the line again", alt("trace-on-return")),
             ("R-TRON-TRACE", "the trace starts a new line", alt("trace-newline")),
             ("R-TRON-ONOFF", "the line holding TRON is traced too", alt("tron-line-traced")),
             ("R-TRON-ONOFF", "a typed statement is traced", alt("trace-typed")),
             ("R-TRON-ONOFF", "NEW leaves the trace on", alt("new-keeps-trace"))],
    "TROFF": [("R-TROFF-OFF", "the TROFF line is not traced", alt("troff-line-untraced"))],
    "REM": [("R-REM-LINE", "a colon ends a REM", alt("rem-keeps-colon")),
            ("R-REM-LINE", "an ELSE after REM still counts", alt("else-past-rem")),
            ("R-REM-LINE", "the apostrophe needs a colon before it", alt("apostrophe-needs-colon")),
            ("R-REM-LINE", "REM after a statement needs no colon", alt("rem-after-stmt-ok")),
            ("R-REM-LINE", "a REM inside DATA ends the item", alt("data-stops-at-rem")),
            ("R-REM-LINE", "an apostrophe inside a string starts a comment", alt("apostrophe-in-string"))],
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
