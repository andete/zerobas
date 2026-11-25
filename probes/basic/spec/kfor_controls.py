#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""The CONTROLS of kfor_model's rules (docs/spec-method.md §3a: a rule must be shown able to fail). Each control is a
rival rule the probe was built to separate, run over the same reference cases as the page's rule; it must be FALSE on
some of them, or the matrix cannot tell the two apart.

    python3 probes/basic/spec/kfor_controls.py      (exit 1 when a control finds no case against it)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kfor_model as M  # noqa: E402


def alt(*a):
    return lambda c: M.ok(c, frozenset(a))


CONTROLS = {
    "FOR": [("R-FOR-RUNS", "a start past the limit skips the body (0 runs)", alt("skip-past")),
            ("R-FOR-STEP0", "STEP 0 with the start past the limit runs once -- zerobas's", alt("step0-past-ends")),
            ("R-FOR-ONCE", "the limit re-read at every NEXT", alt("limit-live")),
            ("R-FOR-ONCE", "the step re-read at every NEXT", alt("step-live")),
            ("R-FOR-INT", "an integer variable ROUNDS start and limit", alt("int-round")),
            ("R-FOR-INT", "an integer variable keeps a fractional STEP", alt("int-step-kept")),
            ("R-FOR-NOFRAME", "a failed FOR keeps its frame -- zerobas's", alt("frame-kept"))],
    "NEXT": [("R-NEXT-CREATE", "a failing NEXT I does not create I -- zerobas's", alt("next-no-create"))],
}


def main():
    rc = 0
    for kw, ctl in CONTROLS.items():
        cs = M.load(kw)["ref"]
        rules = {r.id: r for r in M.rules(kw)}
        for rid, what, check in ctl:
            sel = [c for c in cs if rules[rid].select(c)]
            false = [c.id for c in sel if not check(c)]
            print(f"{rid:15s} {what[:64]:64s} FALSE on {len(false):3d} of {len(sel):<3d}"
                  f"{'  e.g. ' + false[0] if false else '  <-- NO CASE AGAINST IT'}")
            rc |= not false
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
