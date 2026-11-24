#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""The CONTROLS of ktrans_model's rules (docs/spec-method.md §3a: a rule must be shown able to fail). Each control is
a rival rule -- a tighter bound, another target, zerobas's own behaviour -- run over the same reference cases as the
page's rule; it must be FALSE on some of them, or the matrix cannot tell the two apart.

    python3 probes/basic/spec/ktrans_controls.py [--zb]     (exit 1 when a control finds no case against it)
--zb also prints zerobas's own worst error against each page's target (an observation the pages quote, not a rule).
"""
import os
import sys
from fractions import Fraction as Fr

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ktrans_model as M  # noqa: E402


def mx(c):
    return M.mx(c)


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


def r14_even(v):
    """14 digits, ties to the even digit"""
    v = Fr(v)
    if v == 0:
        return v
    e = M.dexp(v)
    m = abs(v) * Fr(10) ** (14 - e)
    n = int(m)
    if m - n > Fr(1, 2) or (m - n == Fr(1, 2) and n % 2):
        n += 1
    out = Fr(n) * Fr(10) ** (e - 14)
    return Fr(0) if out < Fr(1, 10 ** 64) else (out if v > 0 else -out)


def r14_trunc(v):
    """14 digits, truncated"""
    v = Fr(v)
    if v == 0:
        return v
    e = M.dexp(v)
    out = Fr(int(abs(v) * Fr(10) ** (14 - e))) * Fr(10) ** (e - 14)
    return Fr(0) if out < Fr(1, 10 ** 64) else (out if v > 0 else -out)


def sin_even(x):
    """SIN's turns with p rounded half-even"""
    return M.frac(r14_even(Fr(x) * M.C_TURN))


def cos_with(rnd):
    """COS's turns with 1/4 - p rounded by rnd (the page: half down)"""
    return lambda x: M.frac(rnd(Fr(1, 4) - M.r14(Fr(x) * M.C_TURN)))


def trig_rival(fn, turns_s, turns_c):
    """a whole SIN / COS / TAN model with other reduced angles: (kind, target)"""
    def m(c):
        x = M.xval(c)
        s, k = M.sin_turns(turns_s(x)), M.sin_turns(turns_c(x))
        if fn == "SIN":
            return ("bytes", M.TWOPI_ZERO) if s == 0 else ("near", s, M.B_TRIG)
        if fn == "COS":
            if x == 0:
                return "bytes", M.ONE
            return ("bytes", M.TWOPI_ZERO) if k == 0 else ("near", k, M.B_TRIG)
        if k == 0:
            return "err", 6
        return ("bytes", M.TWOPI_ZERO) if s == 0 else ("near", s / k, M.B_TAN)
    return lambda c: M.outcome(c, m(c))


def pow10_r14(x):
    """10^r14(x * log10 e): EXP through a 14-digit reduction to a power of ten"""
    from decimal import Decimal as D, localcontext
    with localcontext() as ctx:
        ctx.prec = 90
        return Fr(D(10) ** M._dec(M.r14(Fr(x) * M.r14(1 / M.LN10))))


def cos_plus(x):
    """COS's turns as p + 1/4 rounded (a quarter turn added, not p subtracted from it)"""
    return M.frac(M.r14(M.r14(Fr(x) * M.C_TURN) + Fr(1, 4)))


def sin_of(turns):
    return lambda x: M.sin_turns(turns(x))


def is_bytes(b):
    return lambda c: M.ok_double(c) and c.res == b


def is_zero(c):
    return M.ok_double(c) and c.res[0] & 0x7F == 0


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
    ("EXP", "R-EXP-NEG", "within 39,000 units", near_in(-200, -1), bound(39000)),
    ("EXP", "R-EXP-NEG", "within 5 units of 10^r14(x * log10 e) -- a 14-digit reduction (review 2.4)",
     lambda c: kind("near")(c) and M.xval(c) < -1, target(pow10_r14, 5)),
    ("EXP", "R-EXP-TINY", "the digits within 39,000 units", kind("zdig"), bound(39000)),
    ("EXP", "R-EXP-TINY", "a clean zero (8 zero bytes) below 1E-64", kind("zdig"), is_bytes(M.ZERO8)),
    ("EXP", "R-EXP-BAND", "a zero (exponent byte 0, any digit bytes) in the band -- zerobas's rule",
     lambda c: mx(c) and M.want(c) == ("err", 6) and M.EXP_M129 <= M.xval(c) < 0, is_zero),
    ("EXP", "R-EXP-HUGE", "a zero (exponent byte 0, any digit bytes) for the huge negatives -- zerobas's rule",
     lambda c: mx(c) and M.want(c) == ("err", 6) and M.xval(c) <= M.EXP_HUGE, is_zero),
    ("EXP", "R-EXP-HUGE", "Overflow only from -99999 (this page before the goldfish pass)",
     lambda c: mx(c) and -99999 < M.xval(c) <= M.EXP_HUGE, is_bytes(M.ZERO8)),
    ("EXP", "R-EXP-FLUSH", "Overflow already below -65536 (review 2.5)",
     lambda c: mx(c) and M.xval(c) < -65536 and M.want(c) == ("bytes", M.ZERO8), is_err(6)),
    ("EXP", "R-EXP-OVER", "Overflow from 145.0628 (not 145.063) on", lambda c: mx(c) and M.xval(c) >= Fr("145.0628"),
     is_err(6)),
    ("LOG", "R-LOG-NEAR", "within 5 units (this page before 2026-11-24)", kind("near"), bound(5)),
    ("LOG", "R-LOG-NEAR", "within 8 units", kind("near"), bound(8)),
    ("LOG", "R-LOG-NEAR", "correctly rounded", kind("near"), bound(0.5)),
    ("SIN", "R-SIN-NEAR", "within 2.5 units of the TRUE sin(x)", kind("near"), target(M.x_sin, 2.5)),
    ("SIN", "R-SIN-NEAR", "the reduction with 1/2 pi exact (not 14 digits)", kind("near"),
     target(sin_of(turns_exact_c), 2.5)),
    ("SIN", "R-SIN-NEAR", "within 1 unit of the reduced target", kind("near"), bound(1)),
    ("SIN", "R-SIN-NEAR", "within 1.5 units of the reduced target", kind("near"), bound(1.5)),
    ("SIN", "R-SIN-NEAR", "p = x * C rounded half-even, not half up", mx, trig_rival("SIN", sin_even, M.turns_cos)),
    ("SIN", "R-SIN-ZERO", "the zero 8 zero bytes", kind("bytes"), is_bytes(M.ZERO8)),
    ("SIN", "R-SIN-ZERO", "the 2-pi zero for every x from 1E13 up (this page's sentence before the goldfish pass)",
     lambda c: mx(c) and M.xval(c) >= 10 ** 13, is_bytes(M.TWOPI_ZERO)),
    ("SIN", "R-SIN-ZERO", "the zero below x = 1E-63 (an x threshold, not p's)",
     lambda c: mx(c) and 0 < M.xval(c) < Fr(1, 10 ** 63), is_bytes(M.TWOPI_ZERO)),
    ("COS", "R-COS-NEAR", "within 2.5 units of the TRUE cos(x)", kind("near"), target(M.x_cos, 2.5)),
    ("COS", "R-COS-NEAR", "1/4 minus the FRACTION of p", lambda c: mx(c) and M.want(c)[0] != "err",
     lambda c: M.outcome(c, ("near", sin_of(cos_frac_first)(M.xval(c)), 2.5)) if
     sin_of(cos_frac_first)(M.xval(c)) else c.res == M.TWOPI_ZERO),
    ("COS", "R-COS-NEAR", "p + 1/4 in place of 1/4 - p", kind("near"), target(sin_of(cos_plus), 2.5)),
    ("COS", "R-COS-NEAR", "within 1.5 units of the reduced target", kind("near"), bound(1.5)),
    ("COS", "R-COS-NEAR", "1/4 - p rounded half up (the first run's model)", mx,
     trig_rival("COS", M.turns_sin, cos_with(M.r14))),
    ("COS", "R-COS-NEAR", "1/4 - p rounded half-even", mx, trig_rival("COS", M.turns_sin, cos_with(r14_even))),
    ("COS", "R-COS-NEAR", "1/4 - p truncated", mx, trig_rival("COS", M.turns_sin, cos_with(r14_trunc))),
    ("COS", "R-COS-ZERO", "the 2-pi zero only from 7E13 up (this page before the goldfish pass)",
     lambda c: mx(c) and 0 < M.xval(c) < 7 * 10 ** 13, lambda c: c.res != M.TWOPI_ZERO),
    ("TAN", "R-TAN-NEAR", "within 3 units of the reduced quotient", kind("near"), bound(3)),
    ("TAN", "R-TAN-NEAR", "within 5 units of the reduced quotient", kind("near"), bound(5)),
    ("TAN", "R-TAN-OWN", "within 2.5 units of the own SIN / COS", lambda c: mx(c) and kind("near")(c),
     lambda c: M.tan_own(c, bound=2.5)),
    ("TAN", "R-TAN-POLE", "Overflow only from 7E13 up (this page before the goldfish pass)",
     lambda c: mx(c) and 0 < abs(M.xval(c)) < 7 * 10 ** 13, lambda c: c.e1 != 6),
    ("TAN", "R-TAN-POLE", "1/4 - p rounded half up (the first run's model)", mx,
     trig_rival("TAN", M.turns_sin, cos_with(M.r14))),
    ("TAN", "R-TAN-OWN", "the own SIN / COS correctly rounded -- zerobas's rule", lambda c: mx(c) and kind("near")(c),
     lambda c: M.tan_own(c, bound=0.5)),
    ("TAN", "R-TAN-NEAR", "within 6 units of the TRUE tan(x)", kind("near"), target(M.EXACT["TAN"], 6)),
    ("TAN", "R-TAN-ZERO", "the zero 8 zero bytes -- zerobas's", kind("bytes"), is_bytes(M.ZERO8)),
    ("ATN", "R-ATN-NEAR", "within 2 units (zerobas's design target, Joost 2026-07-13)", kind("near"), bound(2)),
    ("ATN", "R-ATN-NEAR", "correctly rounded", kind("near"), bound(0.5)),
    ("ATN", "R-ATN-NEAR", "within 2.5 units", kind("near"), bound(2.5)),
    ("ATN", "R-ATN-ODDBYTES", "a signed zero (80 ...) gives a negative zero C0 00 ... -- zerobas's",
     lambda c: M.fx_by(c, *M.ODD_WHYS) and "byte 80" in c.why, is_bytes(bytes([0xC0]) + bytes(7))),
    ("ATN", "R-ATN-ZERO", "an exponent-0 single keeps its digit bytes, the sign dropped (the first run's rule)",
     lambda c: M.fx_by(c, *M.ODD_WHYS) and "byte 80" in c.why,
     lambda c: c.res == bytes([0]) + M.FX_ARG[c.why][1][1:] + bytes(4)),
    ("ATN", "R-ATN-ZERO", "any exponent-0 single gives the constant 00 10 00 00 ... (review 2.6)",
     lambda c: M.fx_by(c, *M.ODD_WHYS), is_bytes(M.ATN_NEGZERO)),
    ("EXP", "R-EXP-SMALL", "a single argument gives a single result", lambda c: mx(c) and c.ty == "S",
     lambda c: c.vt == 4 or c.vt == 255),
] + [(fn, f"R-{fn}-USE", what, lambda c, key=key: M.fy_by(c) and key in c.why, check)
     for fn in ("SIN", "COS", "TAN", "EXP", "ATN")
     for what, key, check in (
         ("times 1E10 gives a clean zero (8 zero bytes) -- zerobas's", "times 1E10", is_bytes(M.ZERO8)),
         ("negation sets the sign bit", "minus", lambda c: M.ok_double(c) and c.res[0] & 0x80 != 0),
         ("a single takes the zero as 4 zero bytes -- zerobas's", "to a single",
          lambda c: c.vt == 4 and c.res == bytes(4)))]


def zb_readout():
    """zerobas's own accuracy, an OBSERVATION the pages quote (not a rule): per function and range, the worst units of
    zerobas's results against the page's target, over the cases where zerobas satisfies the page's rule"""
    print("\nzerobas's worst against each page's target, where it satisfies the page's rule (an observation):")
    for fn in ("EXP", "LOG", "SIN", "COS", "TAN", "ATN"):
        worst = {}
        for c in M.load(fn)["zb"]:
            if not (mx(c) or M.fx_by(c, *M.FX_ARG)):
                continue
            w = M.want(c)
            if w[0] != "near" or not M.outcome(c, w):
                continue
            x = M.xval(c)
            rng = ("|x| <= 1" if abs(x) <= 1 else "x > 1" if x > 0 else "x < -1") if fn == "EXP" else "all"
            u = M.units(M.value(c.res), w[1])
            if u > worst.get(rng, (-1, ""))[0]:
                worst[rng] = (u, c.id)
        for rng, (u, cid) in worst.items():
            print(f"  {fn:4} {rng:9} {float(u):5.2f} units  ({cid})")


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
    if "--zb" in sys.argv:
        zb_readout()
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
