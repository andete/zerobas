#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""The CONTROLS of kdata_model's rules (docs/spec-method.md §3a: a rule must be shown able to fail). Each control flips
ONE law of the shared small BASIC (kstop_model's `alt` switches) and runs over the reference's cases; it must be FALSE
on some of them.

    python3 probes/basic/spec/kdata_controls.py      (exit 1 when a control finds no case against it)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kdata_model as M  # noqa: E402


def alt(*a):
    return lambda c: M.ok(c, frozenset(a))


CONTROLS = {
    "DATA": [("R-DATA-CUT", "unquoted trailing spaces are trimmed", alt("data-trim-trailing")),
             ("R-DATA-CUT", "the quotes are part of the item", alt("data-quotes-kept")),
             ("R-DATA-CUT", "an empty item is an error", alt("data-empty-error")),
             ("R-DATA-TYPE", "the Syntax error names the READ's line", alt("data-error-read-line"))],
    "READ": [("R-READ-NEXT", "a READ at the prompt starts again at the first item", alt("direct-read-restarts")),
             ("R-READ-NEXT", "CLEAR keeps READ's position", alt("clear-keeps-data-ptr")),
             ("R-READ-NEXT", "an edit keeps READ's position", alt("edit-keeps-data-ptr")),
             ("R-READ-ERRORS", "an integer target takes any number", alt("read-int-no-overflow")),
             ("R-READ-ERRORS", "an array element is not checked against its DIM", alt("subscript-unchecked"))],
    "RESTORE": [("R-RESTORE-POINT", "RESTORE n is plain RESTORE", alt("restore-n-ignored")),
                ("R-RESTORE-ERRORS", "a variable after RESTORE is error 2", alt("restore-var-syntax"))],
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
