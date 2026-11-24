#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""The CONTROLS of klet_model's rules (docs/spec-method.md §3a: a rule must be shown able to fail). Each control is a
deliberately altered model -- a rival rule the probe was built to separate -- run over the same reference cases as
the page's rule; it must be FALSE on some of them, or the matrix cannot tell the two rules apart.

    python3 probes/basic/spec/klet_controls.py      (exit 1 when a control finds no case against it)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import klet_model as M  # noqa: E402


def alt(*a):
    return lambda c: M.ok(c, frozenset(a))


def names_three(c):
    """names count by three characters: ZQ7 is a new variable (ZQ7+1 = 1)"""
    if c.why == "two names with the same first two characters":
        return (c.e, c.v1, c.v2) == (0, M.D(5), M.D(1))
    return M.ok(c)


def rhs_zero(c):
    """a right-side error stores 0 into the target (A=3:A=1/0 leaves 0)"""
    if c.why == "the right side's own error (A kept)":
        return (c.e, c.v1, c.v2) == (11, M.D(0), None)
    return M.ok(c)


def dbl_short(c):
    """a double target keeps only 6 digits (stored through a single)"""
    if c.why == "a double expression into a double":
        return (c.e, c.v1) == (0, M.num("S", M.Fraction(333333, 10 ** 6))[:1] + (M.C.THIRD_D[:4] + bytes(4), None))
    return M.ok(c)


def swap_new_copies(c):
    """the missing second variable created holding the first's value -- zerobas's"""
    if c.why in ("the second variable new", "a third, the second new"):
        return (c.e, c.v1, c.v2) == (5, M.D(1), M.D(1))
    return M.ok(c)


CONTROLS = {
    "LET": [("R-LET-INT", "rounded half away from zero (not truncated)", alt("int-round")),
            ("R-LET-SNG", "the 7th digit dropped (not rounded)", alt("sng-trunc")),
            ("R-LET-DBL", "a double target kept to 6 digits", dbl_short),
            ("R-LET-NAMES", "names count by three characters", names_three),
            ("R-LET-RHS", "a right-side error stores 0", rhs_zero)],
    "SWAP": [("R-SWAP-TYPES", "numeric types converted and exchanged (no error)", alt("types-convert")),
             ("R-SWAP-NEW", "a missing second variable created and exchanged", alt("second-new-ok")),
             ("R-SWAP-NEW", "the missing second created holding the first's value -- zerobas's", swap_new_copies),
             ("R-SWAP-AFTER", "the Syntax error before any exchange", alt("error-first"))],
}


def main():
    rc = 0
    for kw, ctl in CONTROLS.items():
        cs = M.load(kw)["ref"]
        rules = {r.id: r for r in M.rules(kw)}
        for rid, what, check in ctl:
            sel = [c for c in cs if rules[rid].select(c)]
            false = [c.id for c in sel if not check(c)]
            print(f"{rid:13s} {what[:66]:66s} FALSE on {len(false):3d} of {len(sel):<3d}"
                  f"{'  e.g. ' + false[0] if false else '  <-- NO CASE AGAINST IT'}")
            rc |= not false
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
