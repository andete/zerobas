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
            ("R-FOR-STEP0", "STEP 0 ends at the limit (Microsoft's sign compare)", alt("step0-sign")),
            ("R-FOR-STEP0", "STEP 0 is a positive step -- zerobas's", alt("step0-past")),
            ("R-FOR-ONCE", "the limit re-read at every NEXT", alt("limit-live")),
            ("R-FOR-ONCE", "the step re-read at every NEXT", alt("step-live")),
            ("R-FOR-ONCE", "NEXT counts a private copy kept in the frame", alt("private-copy")),
            ("R-FOR-NEST", "a FOR on a variable with a frame replaces it (and the frames above)", alt("replace-frame")),
            ("R-FOR-FRACTION", "the sum is not rounded to the variable's type", alt("sum-unrounded")),
            ("R-FOR-INT", "an integer variable ROUNDS start and limit", alt("int-round")),
            ("R-FOR-INT", "an integer variable FLOORS (towards minus infinity)", alt("int-floor")),
            ("R-FOR-INT", "an integer variable keeps a fractional STEP, the sum cut -- zerobas's", alt("int-step-kept")),
            ("R-FOR-OVERFLOW", "32767 + 1 wraps to -32768", alt("int-wrap")),
            ("R-FOR-OVERFLOW", "the range is checked before the cut", alt("range-first")),
            ("R-FOR-ERRORS", "the variable is made only after `=`", alt("make-late")),
            ("R-FOR-ERRORS", "the start is stored only once the whole FOR has parsed", alt("store-late")),
            ("R-FOR-NOFRAME", "a FOR error ends the line", alt("failed-for-ends-line")),
            ("R-FOR-NOFRAME", "text after STEP's value is caught before the push", alt("comma-before-push"))],
    "NEXT": [("R-NEXT-MATCH", "a name does not skip spaces", alt("no-space-skip")),
             ("R-NEXT-LIST", "the whole list is checked before stepping", alt("list-first")),
             ("R-NEXT-ERRORS", "a failed NEXT drops the frames -- zerobas's", alt("next-fail-drops")),
             ("R-NEXT-CREATE", "a failing NEXT I does not create I -- zerobas's", alt("next-no-create"))],
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
