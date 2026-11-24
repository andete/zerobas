#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""The CONTROLS of kmath_model's rules (docs/spec-method.md §3a: a rule must be shown able to fail). Each control is a
deliberately altered model -- a rival rule the probe was built to separate -- run over the same reference cases as
the page's rule; it must be FALSE on some of them, or the matrix cannot tell the two rules apart.

    python3 probes/basic/spec/kmath_controls.py      (exit 1 when a control finds no case against it)
"""
import os
import sys
from decimal import Decimal, getcontext, ROUND_DOWN, ROUND_HALF_UP
from fractions import Fraction

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kmath_model as M  # noqa: E402

getcontext().prec = 80


def mx(c):
    return M.mx(c)          # the matrix groups MI / MS / MD (not FX, FY, FZ)


def odd(c):
    return M.fx_by(c, *M.ODD_WHYS)


def neg_frac(c):
    return mx(c) and c.ty in "SD" and c.arg[0] & 0x80 and M._frac(M.argb(c))


def is_(model):
    """the case's outcome is what `model(ty, bytes)` says (matrix and fixed value forms alike)"""
    return lambda c: M.outcome(c, M.want(c, model))


def sqr_digits(mode):
    """SQR as a 14-digit root of the exact value, rounded by `mode` (ROUND_HALF_UP: correctly rounded -- zerobas's
    rule; ROUND_DOWN: truncated)"""
    def m(ty, b):
        k = M.m_sqr(ty, b)
        if k[0] != "near":
            return k
        v = k[1]
        x = (Decimal(v.numerator) / Decimal(v.denominator)).sqrt()
        q = Decimal(f"1E{x.adjusted() + 1 - 14}")
        r = x.quantize(q, rounding=mode)
        return "num", 8, M.enc(Fraction(r), "D")
    return m


def fix_round(ty, b):
    """rounding half away from zero in place of truncation"""
    if ty == "I":
        return M.m_fix(ty, b)
    v = M.value(b)
    r = int((Decimal(v.numerator) / Decimal(v.denominator)).quantize(Decimal(1), rounding=ROUND_HALF_UP))
    return "num", M.VT[ty], M.enc(r, ty) if r else bytes(len(b))


def fix_floor(ty, b):
    """INT's floor in FIX's place (and its types)"""
    return M.m_int(ty, b)


def int_floor_double(ty, b):
    """a negative non-whole argument always gives a DOUBLE (no integer -1 between -1 and 0)"""
    if ty != "I" and b[0] & 0x80 and M._frac(b):
        p = (b[0] & 0x7F) - 64
        t = M.value(M.m_fix(ty, b)[2]) if p > 0 else 0
        return "num", 8, M.enc(t - 1, "D")
    return M.m_int(ty, b)


def int_fits_integer(ty, b):
    """a negative non-whole argument gives an INTEGER whenever the result fits -32768..32767"""
    k = M.m_int(ty, b)
    if ty != "I" and b[0] & 0x80 and M._frac(b):
        v = M.value(k[2])
        if -32768 <= v <= 32767:
            return "num", 2, M.enc(v, "I")
    return k


def sgn_typed(ty, b):
    """SGN in the argument's own type"""
    v = M.value(M.m_sgn(ty, b)[2])
    return "num", M.VT[ty], M.enc(v, ty)


def abs_canonical(ty, b):
    """the sign bit cleared and an exponent-0 number made a canonical zero"""
    k = M.m_abs(ty, b)
    if ty != "I" and k[2][0] == 0:
        return "num", k[1], bytes(len(k[2]))
    return k


def sqr_negzero(ty, b):
    """the sign bit of an exponent-0 single ignored: 80 10 00 00 is a zero, not negative"""
    if ty != "I" and b[0] & 0x7F == 0:
        return M.m_sqr(ty, bytes([0]) + b[1:])
    return M.m_sqr(ty, b)


def order_err(rival):
    """R-*-ORDER's rivals: "type" -- the argument's type checked before the `)` / `,` (zerobas's rule: 13);
    "shape" -- the call's shape checked before the argument is evaluated (2 throughout)"""
    def check(c):
        code = M.ORDER_ERR[c.why]
        if rival == "type" and '"A"' in c.stmt:
            code = 13
        if rival == "shape":
            code = 2
        return M.no_usr(c, code)
    return check


def zero_as_digits(c):
    """an exponent-0 zero read as its digits: FIX(.5!) / INT(.5!) worth .5"""
    return c.e1 == 0 and c.e2 == 0 and (c.vt, c.res) == M.zero_use(c.why, Fraction(1, 2))


def target_rival(**kw):
    return lambda c: M.target_is(c, M.target(c, **kw))


def round_half_away(v):
    return int((Decimal(v.numerator) / Decimal(v.denominator)).quantize(Decimal(1), rounding=ROUND_HALF_UP))


def let_digits_kept(c):
    """D-SQRZERO's zerobas: a zero root assigned to R leaves R's earlier digit bytes under exponent 0"""
    before = bytes(8) if "R=0" in c.stmt else M.R_SENT
    return c.e1 == 0 and c.rbytes == bytes([0]) + before[1:]


def assign_zeroed(c):
    """zerobas's LET: a single whose exponent byte is 0 is stored in R as 8 zero bytes"""
    if c.vt == 255:
        return c.rbytes == M.R_SENT
    want = M.as_double(c.vt, c.res)
    if c.vt == 4 and c.res[0] == 0:
        want = bytes(8)
    return c.rbytes == want


CONTROLS = [
    # (keyword, rule it shadows, what it alters, select, check)
    ("ABS", "R-ABS-INT", "ABS(-32768%) the DOUBLE 32768 -- zerobas's rule", lambda c: mx(c) and c.ty == "I",
     is_(lambda ty, b: M.m_abs(ty, b, int_edge="D"))),
    ("ABS", "R-ABS-INT", "ABS(-32768%) error 6 (no integer 32768)", lambda c: mx(c) and c.ty == "I",
     is_(lambda ty, b: ("err", 6) if ty == "I" and M.value(b) == -32768 else M.m_abs(ty, b))),
    ("ABS", "R-ABS-ODD", "an exponent-0 result made a canonical zero", odd, is_(abs_canonical)),
    ("SGN", "R-SGN-ALL", "the result in the argument's own type", mx, is_(sgn_typed)),
    ("SGN", "R-SGN-ODD", "any exponent 0 a zero, the sign bit ignored", odd,
     is_(lambda ty, b: M.m_sgn(ty, b, zero="exp"))),
    ("FIX", "R-FIX-SMALL", "below 1 a canonical zero (8 / 4 zero bytes)", mx,
     is_(lambda ty, b: M.m_fix(ty, b, small="zero"))),
    ("FIX", "R-FIX-WHOLE/SMALL", "rounding half away from zero (CINT-style)", mx, is_(fix_round)),
    ("FIX", "R-FIX-WHOLE/SMALL", "INT's floor in FIX's place", mx, is_(fix_floor)),
    ("INT", "R-INT-NEGFRAC", "the argument's own type -- zerobas's rule", mx,
     is_(lambda ty, b: M.m_int(ty, b, neg_type="same"))),
    ("INT", "R-INT-NEGFRAC", "toward zero (FIX) in INT's place", mx, is_(M.m_fix)),
    ("INT", "R-INT-NEGFRAC", "always a double, no integer -1 above -1", neg_frac, is_(int_floor_double)),
    ("INT", "R-INT-NEGFRAC", "an integer whenever the result fits -32768..32767", neg_frac, is_(int_fits_integer)),
    ("SQR", "R-SQR-NEAR", "the correctly rounded root -- zerobas's rule", mx, is_(sqr_digits(ROUND_HALF_UP))),
    ("SQR", "R-SQR-NEAR", "the root truncated at 14 digits", mx, is_(sqr_digits(ROUND_DOWN))),
    ("SQR", "R-SQR-NEAR", "within 1 unit of the 14th digit (not 3)", lambda c: (mx(c) or c.why in M.FX_ARG) and M.want(c)[0] == "near",
     lambda c: M.outcome(c, M.want(c), bound=1)),
    ("SQR", "R-SQR-EXACT", "a single argument gives a single result (the cases with no error)",
     lambda c: mx(c) and c.ty == "S" and M.want(c)[0] != "err", lambda c: c.e1 == 0 and c.vt == 4),
    ("SQR", "R-SQR-NEG", "80 10 00 00 a zero (the sign bit of an exponent-0 number ignored)", odd, is_(sqr_negzero)),
    ("FIX", "R-FIX-ASSIGN", "a single exponent-0 zero stored in R as 8 zero bytes -- zerobas's LET",
     lambda c: c.fn == "FIX" and (M.mx(c) or c.src == "FX"), assign_zeroed),
    # goldfish pass 1 (FY / FZ)
    ("ABS", "R-ABS-ORDER", "the argument's type checked before the `)` (13) -- zerobas's rule",
     lambda c: M.fy(c, "prec"), order_err("type")),
    ("ABS", "R-ABS-ORDER", "the call's shape checked before the argument is evaluated (2)",
     lambda c: M.fy(c, "prec"), order_err("shape")),
    ("ABS", "R-ABS-NEST", "32 deep is error 50 (zerobas before D-SPMERGE)", lambda c: M.fy(c, "nest"),
     lambda c: (c.e1 == 50) == (c.depth == 32)),
    ("FIX", "R-FIX-ZEROUSE", "FIX(.5!) read as its digits, .5", lambda c: M.fy(c, "zero"), zero_as_digits),
    ("INT", "R-INT-ZEROUSE", "INT(.5!) read as its digits, .5", lambda c: M.fy(c, "zero"), zero_as_digits),
    ("FIX", "R-FIX-LET", "a single exponent-0 zero stored as zero bytes -- zerobas's LET", lambda c: c.fn == "LET",
     lambda c: c.res == bytes(4) and c.rbytes == bytes(8)),
    ("SQR", "R-SQR-LET", "R's earlier digit bytes kept under exponent 0 -- zerobas's SQR(0%)",
     lambda c: c.fn == "LET", let_digits_kept),
    ("SQR", "R-SQR-TARGET", "an integer target rounds (CINT-style) instead of truncating",
     lambda c: M.fy(c, "target"), target_rival(to_int=round_half_away)),
    ("INT", "R-INT-TARGET", "a single exponent-0 zero stored in T! as zero bytes -- zerobas's LET",
     lambda c: M.fy(c, "target"), target_rival(zero_let=True)),
]
CONTROLS += [(fn, f"R-{fn}-ORDER", "the argument's type checked before the `)` (13) -- zerobas's rule",
              lambda c: M.fy(c, "prec"), order_err("type")) for fn in ("SGN", "INT", "FIX", "SQR")]
CONTROLS += [(fn, f"R-{fn}-TARGET", "a single exponent-0 zero stored in T! as zero bytes -- zerobas's LET",
              lambda c: M.fy(c, "target"), target_rival(zero_let=True)) for fn in ("ABS", "FIX")]


def main():
    bad = 0
    cache = {}
    for fn, rule, what, sel, check in CONTROLS:
        if fn not in cache:
            cache[fn] = M.load(fn)["ref"]
        cs = [c for c in cache[fn] if sel(c)]
        false = [c.id for c in cs if not check(c)]
        print(f"{fn:4} {rule:18} {what:72} FALSE on {len(false):4} of {len(cs)}"
              + (f"  e.g. {false[0]}" if false else "  <- NO CASE SEPARATES IT"))
        bad += not false
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
