#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""The CONTROLS of ktrans_model's rules (docs/spec-method.md §3a: a rule must be shown able to fail). Each control is
a rival rule -- a tighter bound, another target, zerobas's own behaviour -- run over the same reference cases as the
page's rule; it must be FALSE on some of them, or the matrix cannot tell the two apart.

    python3 probes/basic/spec/ktrans_controls.py      (exit 1 when a control finds no case against it)
"""
import os
import sys
from fractions import Fraction as Fr

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ktrans_model as M  # noqa: E402


def mx(c):
    return c.src != "FX"


def kind(k):
    """the cases whose model outcome is of kind k"""
    return lambda c: (mx(c) or M.fx_by(c, *M.FX_ARG)) and M.want(c)[0] == k


def near_in(lo, hi):
    return lambda c: kind("near")(c) and lo <= M.xval(c) <= hi


def bound(b):
    """the page's target with bound b in place of the page's"""
    return lambda c: M.outcome(c, M.want(c), bound=b)


def target(f, b):
    """a double within b units of f(x) -- another target"""
    return lambda c: M.outcome(c, ("near", f(M.xval(c)), b))


def turns_exact_c(x):
    """the reduction with 1/2 pi to 60 digits in place of 0.15915494309190"""
    return M.frac(M.r14(Fr(x) / (2 * M.PIF)))


def cos_frac_first(x):
    """COS's turns as 1/4 minus the fraction of p (the fraction taken first)"""
    return M.frac(M.r14(Fr(1, 4) - M.turns_sin(x)))


def cos_plus(x):
    """COS's turns as p + 1/4 rounded (a quarter turn added, not p subtracted from it)"""
    return M.frac(M.r14(M.r14(Fr(x) * M.C_TURN) + Fr(1, 4)))


def sin_of(turns):
    return lambda x: M.sin_turns(turns(x))


def is_bytes(b):
    return lambda c: M.ok_double(c) and c.res == b


def is_err(code):
    return lambda c: M.KM.error_is(c, code)


def single_for_single(c):
    return M.ok_double(c) or c.vt == 4


CONTROLS = [
    # (keyword, rule it shadows, what it alters, select, check)
    ("EXP", "R-EXP-SMALL", "correctly rounded (within 0.5 units)", near_in(-1, 1), bound(0.5)),
    ("EXP", "R-EXP-SMALL", "within 2 units", near_in(-1, 1), bound(2)),
    ("EXP", "R-EXP-POS", f"within {M.B_EXP_SMALL} units (SMALL's bound) above 1 too", near_in(1, 200),
     bound(M.B_EXP_SMALL)),
    ("EXP", "R-EXP-POS", "within 400 units", near_in(1, 200), bound(400)),
    ("EXP", "R-EXP-NEG", f"within {M.B_EXP_POS} units (POS's bound) below -1 too", near_in(-200, -1),
     bound(M.B_EXP_POS)),
    ("EXP", "R-EXP-TINY", "a clean zero (8 zero bytes) below 1E-64", kind("zdig"), is_bytes(M.ZERO8)),
    ("EXP", "R-EXP-BAND", "0 in the band, as above and below it -- zerobas's rule",
     lambda c: mx(c) and M.want(c) == ("err", 6) and -99999 < M.xval(c) < 0, is_bytes(M.ZERO8)),
    ("EXP", "R-EXP-HUGE", "0 for the huge negatives -- zerobas's rule",
     lambda c: mx(c) and M.want(c) == ("err", 6) and M.xval(c) <= -99999, is_bytes(M.ZERO8)),
    ("EXP", "R-EXP-OVER", "Overflow from 145.0628 (not 145.063) on", lambda c: mx(c) and M.xval(c) >= Fr("145.0628"),
     is_err(6)),
    ("LOG", "R-LOG-NEAR", "within 5 units (this page before 2026-11-24)", kind("near"), bound(5)),
    ("LOG", "R-LOG-NEAR", "correctly rounded", kind("near"), bound(0.5)),
    ("SIN", "R-SIN-NEAR", "within 2.5 units of the TRUE sin(x)", kind("near"), target(M.x_sin, 2.5)),
    ("SIN", "R-SIN-NEAR", "the reduction with 1/2 pi exact (not 14 digits)", kind("near"),
     target(sin_of(turns_exact_c), 2.5)),
    ("SIN", "R-SIN-NEAR", "within 1 unit of the reduced target", kind("near"), bound(1)),
    ("SIN", "R-SIN-ZERO", "the zero 8 zero bytes", kind("bytes"), is_bytes(M.ZERO8)),
    ("COS", "R-COS-NEAR", "within 2.5 units of the TRUE cos(x)", kind("near"), target(M.x_cos, 2.5)),
    ("COS", "R-COS-NEAR", "1/4 minus the FRACTION of p", lambda c: mx(c) and M.want(c)[0] != "err",
     lambda c: M.outcome(c, ("near", sin_of(cos_frac_first)(M.xval(c)), 2.5)) if
     sin_of(cos_frac_first)(M.xval(c)) else c.res == M.TWOPI_ZERO),
    ("COS", "R-COS-NEAR", "p + 1/4 in place of 1/4 - p", kind("near"), target(sin_of(cos_plus), 2.5)),
    ("COS", "R-COS-NEAR", "within 2 units of the reduced target", kind("near"), bound(2)),
    ("TAN", "R-TAN-NEAR", "within 3 units of the reduced quotient", kind("near"), bound(3)),
    ("TAN", "R-TAN-OWN", "the own SIN / COS correctly rounded -- zerobas's rule", lambda c: mx(c) and kind("near")(c),
     lambda c: M.tan_own(c, bound=0.5)),
    ("TAN", "R-TAN-NEAR", "within 6 units of the TRUE tan(x)", kind("near"), target(M.EXACT["TAN"], 6)),
    ("TAN", "R-TAN-ZERO", "the zero 8 zero bytes -- zerobas's", kind("bytes"), is_bytes(M.ZERO8)),
    ("ATN", "R-ATN-NEAR", "within 2 units (zerobas's design target, Joost 2026-07-13)", kind("near"), bound(2)),
    ("ATN", "R-ATN-NEAR", "correctly rounded", kind("near"), bound(0.5)),
    ("ATN", "R-ATN-ODDBYTES", "80 10 00 00 gives a negative zero C0 00 ... -- zerobas's",
     lambda c: M.fx_by(c, *M.ODD_WHYS), is_bytes(bytes([0xC0]) + bytes(7))),
    ("EXP", "R-EXP-SMALL", "a single argument gives a single result", lambda c: mx(c) and c.ty == "S",
     lambda c: c.vt == 4 or c.vt == 255),
]


def main():
    bad = 0
    cache = {}
    for fn, rule, what, sel, check in CONTROLS:
        if fn not in cache:
            cache[fn] = M.load(fn)["ref"]
        cs = [c for c in cache[fn] if sel(c)]
        false = [c.id for c in cs if not check(c)]
        print(f"{fn:4} {rule:15} {what:66} FALSE on {len(false):4} of {len(cs)}"
              + (f"  e.g. {false[0]}" if false else "  <- NO CASE SEPARATES IT"))
        bad += not false
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
