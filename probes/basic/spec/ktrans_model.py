#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""The shared model and rule builders for EXP / LOG / SIN / COS / TAN / ATN's EXECUTABLE RULES (docs/spec-method.md
§3a, docs/keywords/spec-plan.md §6 "The maths region's second unit"). The cases come from
probes/basic/spec/ktrans.py's committed run (scratchpad/KTR_run1.out); each page's module takes its own keyword's
cases from `load(fn)` and its rules from `rules(fn)`.

A transcendental's last digits are the reference's own approximation, so most of its rules are BOUNDS: the result
is a double within B units of the 14th significant digit of a target computed here exactly (60+ digits, Python's
Decimal -- no reference byte involved). B is the MEASURED worst case on the VG-8020 rounded up (the measured worst
is in each rule's sentence); kt_controls.py shows each bound fails when tightened and each target fails when
replaced by a rival. What CAN be stated exactly is stated exactly: the result's type (always a double), the special
points' bytes, the errors and where they start, the symmetry of SIN / TAN / ATN / COS.

THE ANGLE REDUCTION (SIN / COS / TAN; measured from the outside, D-TANBIG 2026-11-04 and here): the reference turns
the angle into turns, p = x * C rounded to 14 significant digits (half up), C = 0.15915494309190 (1 / 2 pi to 14
digits), and works on the fraction of p (its sign kept): SIN(x) approximates sin(2 pi f), f = frac(p); COS(x)
approximates sin(2 pi g), g = frac(r14(1/4 - p)). A p below 1E-64 in size is 0. The bound is then against
sin(2 pi f) -- the true sine of the REDUCED angle -- not against sin(x), which the reference misses by up to 0.5
for x >= 1E12 (a control)."""
import os
import sys
from decimal import Decimal as D, localcontext
from functools import lru_cache
from fractions import Fraction as Fr

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
import ktrans  # noqa: E402
import kmath_model as KM  # noqa: E402
import ramrec  # noqa: E402
from spec_rules import Rule  # noqa: E402

FIELDS = KM.FIELDS
OUTPUTS = {g: FIELDS for g in ktrans.ORDER}
OUTPUTS_DESC = KM.OUTPUTS_DESC
R_SENT = KM.R_SENT
NB = KM.NB
ONE = bytes([0x41, 0x10, 0, 0, 0, 0, 0, 0])                      # the double 1
ZERO8 = bytes(8)
TWOPI_ZERO = bytes([0x00, 0x62, 0x83, 0x18, 0x53, 0x07, 0x17, 0x96])   # exponent 0, the digits of 2 pi

# --- the bounds, in units of the 14th significant digit of the target (measured worst on the VG-8020 in ( )) ---
B_EXP_SMALL = 3          # |x| <= 1                      (2.5: EXP(.9!), EXP(1))
B_EXP_POS = 500          # x > 1                         (472: EXP(145.0628#))
B_EXP_NEG = 40000        # x < -1, and the digits below 1E-64 (39525: EXP(-149.668#); 27178: EXP(-147.3))
B_LOG = 10               #                               (8.3: LOG(.5235987755983#))
B_TRIG = 2.5             # SIN / COS against the reduced angle (2.07: COS(.25!); SIN 1.86: SIN(1D11))
B_TAN = 6                # TAN against sin(2 pi f) / sin(2 pi g)   (5.2: TAN(4.71239!))
B_TAN_OWN = 3            # TAN against the same machine's SIN(x) / COS(x)  (2.79: TAN(12345%))
B_ATN = 3                # (2.69: ATN(1.0471975511966#))

# --- exact mathematics (Decimal, 90 digits; pi to 100) ---
PI = D("3.14159265358979323846264338327950288419716939937510582097494459230781640628620899862803482534211706798")
PIF = Fr(PI)


def _dec(f):
    return D(f.numerator) / D(f.denominator)


@lru_cache(maxsize=None)
def _sin_dec(x):
    """sin of a Decimal, 90 digits"""
    with localcontext() as c:
        c.prec = 200
        k = (x / (2 * PI)).to_integral_value()
        x = x - k * 2 * PI
        c.prec = 90
        t = s = x
        n = 1
        while True:
            t = -t * x * x / ((2 * n) * (2 * n + 1))
            n += 1
            if abs(t) < D(10) ** -88:
                break
            s += t
        return +s


@lru_cache(maxsize=None)
def sin_turns(f):
    """sin(2 pi f) for a rational f, exactly 0 at whole and half turns"""
    if (2 * f).denominator == 1:
        return Fr(0)
    return Fr(_sin_dec(_dec(2 * PIF * f)))


@lru_cache(maxsize=None)
def x_sin(x):
    return Fr(_sin_dec(_dec(Fr(x))))


@lru_cache(maxsize=None)
def x_cos(x):
    return sin_turns(Fr(1, 4)) if x == 0 else Fr(_sin_dec(_dec(Fr(x)) + PI / 2))


@lru_cache(maxsize=None)
def x_atan(x):
    x = Fr(x)
    if x == 0:
        return Fr(0)
    with localcontext() as c:
        c.prec = 90
        y = _dec(abs(x))
        inv = y > 1
        if inv:
            y = 1 / y
        k = 0
        while y > D("0.1"):
            y = y / (1 + (1 + y * y).sqrt())
            k += 1
        t = s = y
        n = 1
        while True:
            t = -t * y * y
            term = t / (2 * n + 1)
            n += 1
            if abs(term) < D(10) ** -88:
                break
            s += term
        r = s * (2 ** k)
        if inv:
            r = PI / 2 - r
        return Fr(r) if x > 0 else -Fr(r)


@lru_cache(maxsize=None)
def x_exp(x):
    with localcontext() as c:
        c.prec = 90
        return Fr(_dec(Fr(x)).exp())


@lru_cache(maxsize=None)
def x_ln(x):
    with localcontext() as c:
        c.prec = 90
        return Fr(_dec(Fr(x)).ln())


LN10 = x_ln(10)
EXP_OVER = 63 * LN10          # e^x >= 1E63 from here: Overflow
EXP_M64 = -64 * LN10          # e^x = 1E-64
EXP_M65 = -65 * LN10
EXP_M129 = -129 * LN10


# --- numbers ---

def value(b):
    return ramrec.number(b)


def dexp(v):
    """the decimal exponent e of v != 0: 0.1 <= |v| / 10^e < 1"""
    a = abs(Fr(v))
    e = 0
    while a >= 1:
        a /= 10
        e += 1
    while a < Fr(1, 10):
        a *= 10
        e -= 1
    return e


def r14(v):
    """v rounded to 14 significant digits, half up in size; below 1E-64 in size 0"""
    v = Fr(v)
    if v == 0:
        return v
    e = dexp(v)
    m = abs(v) * Fr(10) ** (14 - e)
    n = int(m)
    if m - n >= Fr(1, 2):
        n += 1
    out = Fr(n) * Fr(10) ** (e - 14)
    if out < Fr(1, 10 ** 64):
        return Fr(0)
    return out if v > 0 else -out


def frac(p):
    """the fraction of p, its sign kept (toward zero)"""
    return p - int(p)


C_TURN = r14(1 / (2 * PIF))          # 0.15915494309190


def turns_sin(x):
    """f: SIN's reduced angle in turns"""
    return frac(r14(Fr(x) * C_TURN))


def turns_cos(x):
    """g: COS's reduced angle in turns -- a quarter turn minus the angle's turns, rounded, its fraction"""
    return frac(r14(Fr(1, 4) - r14(Fr(x) * C_TURN)))


def units(v, target):
    """|v - target| in units of the 14th significant digit of target (target != 0)"""
    if target == 0:
        return Fr(0) if v == 0 else Fr(10) ** 99
    return abs(Fr(v) - target) / Fr(10) ** (dexp(target) - 14)


# --- the models: (ty, argument bytes) -> outcome ---
#   ("err", code) | ("bytes", 8 bytes) | ("near", target, bound) | ("zdig", target, bound)
#   "near": a double, exponent byte not 0, within bound units of target;
#   "zdig": a double whose exponent byte is 0 and whose 14 digits, read as 0.d1..d14 * 10^-64, are within bound
#           units of target (EXP below 1E-64)

def argval(ty, b):
    return value(b) if ty == "I" or b[0] & 0x7F else Fr(0)


@lru_cache(maxsize=None)
def m_exp(ty, b):
    x = argval(ty, b)
    if x == 0:
        return "bytes", ONE
    if x <= -99999:
        return "err", 6
    if x >= EXP_OVER:
        return "err", 6
    if x < EXP_M129:
        return "bytes", ZERO8
    if x < EXP_M65:
        return "err", 6
    t = x_exp(x)
    bound = B_EXP_SMALL if abs(x) <= 1 else (B_EXP_POS if x > 0 else B_EXP_NEG)
    if x < EXP_M64:
        return "zdig", t, bound
    return "near", t, bound


@lru_cache(maxsize=None)
def m_log(ty, b):
    x = argval(ty, b)
    if x <= 0 or (ty != "I" and b[0] & 0x80):
        return "err", 5
    if x == 1:
        return "bytes", ZERO8
    return "near", x_ln(x), B_LOG


@lru_cache(maxsize=None)
def m_sin(ty, b):
    t = sin_turns(turns_sin(argval(ty, b)))
    return ("bytes", TWOPI_ZERO) if t == 0 else ("near", t, B_TRIG)


@lru_cache(maxsize=None)
def m_cos(ty, b):
    x = argval(ty, b)
    if x == 0:
        return "bytes", ONE
    t = sin_turns(turns_cos(x))
    return ("bytes", TWOPI_ZERO) if t == 0 else ("near", t, B_TRIG)


@lru_cache(maxsize=None)
def m_tan(ty, b):
    x = argval(ty, b)
    c = sin_turns(turns_cos(x))
    if c == 0:
        return "err", 6
    s = sin_turns(turns_sin(x))
    if s == 0:
        return "bytes", TWOPI_ZERO
    return "near", s / c, B_TAN


@lru_cache(maxsize=None)
def m_atn(ty, b):
    if ty == "I" and value(b) == 0:
        return "bytes", ZERO8
    if ty != "I" and b[0] & 0x7F == 0:
        return "bytes", bytes([0]) + b[1:] + bytes(8 - len(b))
    return "near", x_atan(value(b)), B_ATN


MODELS = {"EXP": m_exp, "LOG": m_log, "SIN": m_sin, "COS": m_cos, "TAN": m_tan, "ATN": m_atn}
EXACT = {"EXP": x_exp, "LOG": x_ln, "SIN": x_sin, "COS": x_cos, "TAN": lambda x: x_sin(x) / x_cos(x),
         "ATN": x_atan}


# --- what a case recorded ---

def ok_double(c):
    return c.e1 == 0 and c.e2 == 0 and c.vt == 8 and c.res is not None


def outcome(c, want, bound=None):
    k = want[0]
    if k == "err":
        return KM.error_is(c, want[1])
    if not ok_double(c):
        return False
    if k == "bytes":
        return c.res == want[1]
    t, b = want[1], (want[2] if bound is None else bound)
    if k == "zdig":
        if c.res[0] != 0:
            return False
        return units(value(bytes([0x40]) + c.res[1:]) * Fr(10) ** -64, t) <= b
    return c.res[0] & 0x7F != 0 and units(value(c.res), t) <= b


def argb(c):
    return c.arg[:NB[c.ty]]


def xval(c):
    """the argument's value: a matrix case's own bytes, a fixed statement's literal (FX_ARG)"""
    if c.src == "FX":
        return argval(*FX_ARG[c.why])
    return argval(c.ty, argb(c))


# the fixed statements' arguments: the type and bytes each literal is (kmath's, measured through USR there)
FX_ARG = dict(KM.FX_ARG)
FX_ARG.pop("nested")
FORM_WHYS = tuple(w for w in FX_ARG if "exponent byte" not in w)
ODD_WHYS = KM.ODD_WHYS
NESTED_IN = ("S", KM.enc(Fr(1, 2), "S"))           # F(F(.5)): the inner call's argument


def want(c, model=None):
    m = model or MODELS[c.fn]
    if c.src != "FX":
        return m(c.ty, argb(c))
    ty, b = FX_ARG[c.why]
    return m(ty, b)


def fx_by(c, *whys):
    return c.src == "FX" and c.why in whys


def mx(c):
    return c.src != "FX"


def load(fn):
    """this keyword's cases from every group, the reference's and zerobas's. A matrix case also carries `neg` (the
    same group's case of -x, if measured, else None) and, for TAN, `sinrow` / `cosrow` (SIN(x) and COS(x) from the
    same group) -- the partners the pair rules read"""
    out = {"ref": [], "zb": []}
    half = {}
    for g in ktrans.ORDER:
        cs = ktrans.load(g)
        for who in out:
            by = {(c.fn, c.text): c for c in cs[who] if c.src != "FX"}
            if g == "TS1":
                half[who] = by[(fn, ".5")]
            for c in cs[who]:
                if c.fn != fn:
                    continue
                c.neg = c.sinrow = c.cosrow = c.inner = None
                if c.src != "FX":
                    t = c.text
                    c.neg = by.get((fn, t[1:] if t.startswith("-") else "-" + t))
                    c.sinrow, c.cosrow = by[("SIN", t)], by[("COS", t)]
                elif c.why == "nested":
                    c.inner = half[who]
                out[who].append(c)
    return out


def odd_pair(c):
    """F(-x) is F(x) with the sign bit flipped (a zero result: the same bytes), and the same error"""
    n = c.neg
    if c.vt == 255 or n.vt == 255:
        return c.vt == n.vt and c.e1 == n.e1
    if c.res[0] & 0x7F == 0:
        return c.res == n.res
    return c.res == bytes([n.res[0] ^ 0x80]) + n.res[1:]


def even_pair(c):
    n = c.neg
    return (c.vt, c.e1, c.res) == (n.vt, n.e1, n.res)


def tan_own(c, bound=B_TAN_OWN):
    """TAN(x) is within `bound` units of SIN(x) / COS(x) as the same machine computes them (both nonzero)"""
    s, k = value(c.sinrow.res), value(c.cosrow.res)
    return ok_double(c) and units(value(c.res), s / k) <= bound


def _has_pair(c):
    return mx(c) and c.neg is not None and c.text[0] != "-" and c.text not in ("0",)


def _common(fn, tag, sec):
    return [
        Rule(f"R-{tag}-TYPE", sec,
             "A string as the argument (a literal or a variable) is error 13 (Type mismatch), and so is assigning "
             "the result to a string variable: the result is a number.",
             lambda c: fx_by(c, *KM.TYPE_WHYS), lambda c: KM.no_usr(c, 13)),
        Rule(f"R-{tag}-OWNERR", sec, "An argument that fails to compute raises its own error (1/0: error 11).",
             lambda c: fx_by(c, "the argument's own error"), lambda c: KM.no_usr(c, 11)),
        Rule(f"R-{tag}-SYNTAX", sec,
             "No argument, a second argument, no closing parenthesis, or the name without a parenthesis is error 2 "
             "(Syntax error).", lambda c: fx_by(c, *KM.SYNTAX_WHYS), lambda c: KM.no_usr(c, 2)),
        Rule(f"R-{tag}-FORMS", sec,
             f"Spaces before the parenthesis and around the argument are allowed, and a literal's own type is the "
             f"argument's (2.5 a single, 7 an integer, &H8000 the integer -32768, -32768 a single, -0 the integer 0, "
             f"1/4 a double); each gives what the rules above say for that value.",
             lambda c: fx_by(c, *FORM_WHYS), lambda c: outcome(c, want(c))),
        Rule(f"R-{tag}-ASSIGN", sec,
             "`R=" + fn + "(x)` with R a double stores the result's 8 bytes as they are (a zero's digit bytes "
             "included), and an error stores nothing (R keeps its sentinel). Read in every case.", lambda c: True,
             lambda c: (c.rbytes == R_SENT) if c.vt == 255 else (c.res is not None and
                                                                 c.rbytes == KM.as_double(c.vt, c.res))),
    ]


def _sel(pred):
    """the matrix cases and the fixed statements' value forms whose model outcome satisfies pred"""
    return lambda c: (mx(c) or fx_by(c, *FX_ARG)) and pred(c, want(c))


def _ok(c):
    return outcome(c, want(c))


def rules(fn):
    sec = f"1. {fn}(x)"
    tag = fn
    if fn == "EXP":
        def cls(lo, hi):
            return _sel(lambda c, w: w[0] == "near" and lo(xval(c)) and hi(xval(c)))
        out = [
            Rule("R-EXP-ZERO", sec,
                 "EXP of zero is exactly the double 1 (41 10 00 00 00 00 00 00), whatever the zero's digit or sign "
                 "bytes (00 10 00 00 and 80 10 00 00 give 1 too).",
                 _sel(lambda c, w: w == ("bytes", ONE)), _ok),
            Rule("R-EXP-SMALL", sec,
                 f"For 0 < |x| <= 1 the result is a DOUBLE (whatever the argument's type) within {B_EXP_SMALL} units "
                 f"of the 14th significant digit of e^x (measured worst 2.5: EXP(1) is 2.7182818284588, e is "
                 f"2.71828182845904...).",
                 cls(lambda x: abs(x) <= 1, lambda x: True), _ok),
            Rule("R-EXP-POS", sec,
                 f"For 1 < x < 63 ln 10 (145.06286...) a double within {B_EXP_POS} units of e^x: the error grows "
                 f"with x (EXP(10) 6.7 units low, EXP(100) 74, EXP(145.0628#) 472).",
                 cls(lambda x: x > 1, lambda x: True), _ok),
            Rule("R-EXP-NEG", sec,
                 f"For x < -1, while e^x >= 1E-64, a double within {B_EXP_NEG} units of e^x -- an irregular error: "
                 f"EXP(-3) 5 units, EXP(-2) 5,930, EXP(-50) 331, EXP(-147.3) 27,178 (all high).",
                 cls(lambda x: x < -1, lambda x: True), _ok),
            Rule("R-EXP-OVER", sec,
                 "From e^x >= 1E63 on (x >= 145.063: 145.06286# still gives 9.99...E62) it is error 6 (Overflow).",
                 _sel(lambda c, w: w == ("err", 6) and xval(c) > 0), _ok),
            Rule("R-EXP-TINY", sec,
                 f"Where 1E-65 <= e^x < 1E-64 (x from about -147.36 to -149.668) the result is a double whose "
                 f"exponent byte is 0 -- it reads as zero -- and whose digit bytes are the digits of e^x (within "
                 f"{B_EXP_NEG} units; measured worst 39,525, EXP(-149.668#)): EXP(-147.4) is 00 96 60 36 12 55 89 73.",
                 _sel(lambda c, w: w[0] == "zdig"), _ok),
            Rule("R-EXP-BAND", sec,
                 "Where 1E-129 <= e^x < 1E-65 (x from -149.67 to -297.033) it is error 6 (Overflow), not 0.",
                 _sel(lambda c, w: w == ("err", 6) and -99999 < xval(c) < 0), _ok),
            Rule("R-EXP-FLUSH", sec,
                 "Below that, down to at least x = -65536 (e^x < 1E-129: -297.04, -298, -1000, -32768, -40000, "
                 "-65535, -65536) it is a clean double zero, 8 zero bytes.",
                 _sel(lambda c, w: w == ("bytes", ZERO8)), _ok),
            Rule("R-EXP-HUGE", sec,
                 "From x = -99999 down (measured -99999, -1E5, -999999, -1E6, -1E10, -1E30, -1E38, -9.99999E62 "
                 "and -9.9999999999999D62) it is error 6 (Overflow) again.",
                 _sel(lambda c, w: w == ("err", 6) and xval(c) <= -99999), _ok),
        ]
    elif fn == "LOG":
        out = [
            Rule("R-LOG-DOMAIN", sec,
                 "Zero or a negative argument is error 5 (Illegal function call), in every type and size (0, -0, "
                 "-1E-64, -9.99999E62) -- also a single whose exponent byte is 0 or &H80 (a zero, signed or not).",
                 _sel(lambda c, w: w == ("err", 5)), _ok),
            Rule("R-LOG-ONE", sec, "LOG(1) is exactly 0: 8 zero bytes, a double.",
                 _sel(lambda c, w: w == ("bytes", ZERO8)), _ok),
            Rule("R-LOG-NEAR", sec,
                 f"Any other positive argument gives a DOUBLE within {B_LOG} units of the 14th significant digit of "
                 f"ln x -- measured worst 8.3 (LOG(.5235987755983#)); LOG(2) 1.5 units low, LOG(1D-64) and "
                 f"LOG(9.99999E62) within 0.5.",
                 _sel(lambda c, w: w[0] == "near"), _ok),
        ]
    elif fn in ("SIN", "COS"):
        red = ("f = frac(p), p = x * 0.15915494309190 rounded to 14 significant digits" if fn == "SIN" else
               "g = frac(r14(1/4 - p)), p = x * 0.15915494309190 rounded to 14 significant digits")
        out = []
        if fn == "COS":
            out.append(Rule("R-COS-ONE", sec, "COS of zero is exactly the double 1 (41 10 00 00 00 00 00 00), "
                            "whatever the zero's digit or sign bytes.",
                            _sel(lambda c, w: w == ("bytes", ONE)), _ok))
        out += [
            Rule(f"R-{fn}-ZERO", sec,
                 f"The result is a DOUBLE. When the reduced angle is a whole or a half turn ({red}; a whole turn "
                 f"when p is 0 or whole) it is a zero whose digit bytes are 2 pi's: 00 62 83 18 53 07 17 96 -- "
                 + ("SIN(0), SIN(1E-64) (p below 1E-64 is 0), SIN(3.1415926535897#) (p is .5), and every x "
                    "from 1E13 up, where p has no fraction digit left." if fn == "SIN" else
                    "COS(x) from x = 7E13 up, where 1/4 - p rounds to a whole number."),
                 _sel(lambda c, w: w == ("bytes", TWOPI_ZERO)), _ok),
            Rule(f"R-{fn}-NEAR", sec,
                 f"Otherwise a double within {B_TRIG} units of the 14th significant digit of sin(2 pi "
                 f"{'f' if fn == 'SIN' else 'g'}) -- the sine of the REDUCED angle, not {fn.lower()}(x): "
                 + ("SIN(1000) is .82687954054849 (the reduced target .8268795405485..., sin(1000) is "
                    ".8268795405320...), SIN(3.1415926535898#) -1.2566370614359E-13 (f = -2E-14 turns from a half "
                    "turn), SIN(1E12) -.58778525229247 (f = .9). Measured worst 1.9 units." if fn == "SIN" else
                    "COS(1.5707963267949#) is -6.2831853071796E-14 (g = -1E-14), COS(4.71239!) 1.0196154567834E-06, "
                    "COS(1E13) .95105651629516 (1/4 - p rounds to -1591549430918.8, g = -.8). Measured worst 2.1 "
                    "units."),
                 _sel(lambda c, w: w[0] == "near"), _ok),
        ]
        if fn == "SIN":
            out.append(Rule("R-SIN-ODD", sec,
                            "SIN(-x) is SIN(x) with the sign bit flipped -- byte for byte, the zero's bytes the same "
                            "(every x measured with its negation).", _has_pair, odd_pair))
        else:
            out.append(Rule("R-COS-EVEN", sec,
                            "COS(-x) is COS(x), byte for byte (every x measured with its negation).",
                            _has_pair, even_pair))
    elif fn == "TAN":
        out = [
            Rule("R-TAN-POLE", sec,
                 "When COS's reduced angle is a whole or a half turn (COS(x) is the 2-pi-digit zero, COS's page) TAN "
                 "is error 6 (Overflow): every x from 7E13 up (1E14, 1E20, 1E38, 9.99999E62, the negatives too).",
                 _sel(lambda c, w: w == ("err", 6)), _ok),
            Rule("R-TAN-ZERO", sec,
                 "Otherwise, when SIN's is (SIN(x) the 2-pi-digit zero), TAN is that zero too: 00 62 83 18 53 07 17 "
                 "96 -- TAN(0), TAN(1E-64), TAN(3.1415926535897#), TAN(1E13), TAN(5E13).",
                 _sel(lambda c, w: w == ("bytes", TWOPI_ZERO)), _ok),
            Rule("R-TAN-NEAR", sec,
                 f"Otherwise a DOUBLE within {B_TAN} units of the 14th significant digit of sin(2 pi f) / "
                 f"sin(2 pi g) -- the reduced angles of SIN and COS (their pages): TAN(1.5707963267949#) is "
                 f"-15915494309189 (g is -1E-14 turns), TAN(1) 1.5574077246549. Measured worst 5.2 units.",
                 _sel(lambda c, w: w[0] == "near"), _ok),
            Rule("R-TAN-OWN", sec,
                 f"And within {B_TAN_OWN} units of SIN(x) / COS(x) as the same machine computes them (the case's "
                 f"SIN and COS rows): the quotient of the two, not always rounded correctly (measured worst 2.8, "
                 f"TAN(12345%)).", lambda c: mx(c) and want(c)[0] == "near", tan_own),
            Rule("R-TAN-ODD", sec,
                 "TAN(-x) is TAN(x) with the sign bit flipped (a zero the same bytes, an error the same error).",
                 _has_pair, odd_pair),
        ]
    elif fn == "ATN":
        out = [
            Rule("R-ATN-ZERO", sec,
                 "A zero argument gives a zero DOUBLE that keeps the argument's digit bytes, the sign dropped: "
                 "ATN(0) is 8 zero bytes, ATN of the single 00 10 00 00 or 80 10 00 00 is 00 10 00 00 00 00 00 00.",
                 _sel(lambda c, w: w[0] == "bytes"), _ok),
            Rule("R-ATN-NEAR", sec,
                 f"Any other argument gives a DOUBLE within {B_ATN} units of the 14th significant digit of atan x "
                 f"(between -pi/2 and pi/2): ATN(1) .78539816339745, ATN(1E-63) 1E-63, ATN(1E13) 1.5707963267948, "
                 f"ATN(1E38) 1.5707963267949. Measured worst 2.7 units (ATN(1.0471975511966#)).",
                 _sel(lambda c, w: w[0] == "near"), _ok),
            Rule("R-ATN-ODD", sec, "ATN(-x) is ATN(x) with the sign bit flipped (every x measured with its negation).",
                 _has_pair, odd_pair),
        ]
    else:
        raise KeyError(fn)
    out.append(Rule(f"R-{tag}-ODDBYTES", sec,
                    "On a non-canonical single (exponent byte 0 or &H80, digit bytes 10 00 00) it gives what the "
                    "rules above say for a zero argument.", lambda c: fx_by(c, *ODD_WHYS), _ok))
    out.append(Rule(f"R-{tag}-NESTED", sec,
                    f"{fn}({fn}(.5)) is {fn} of the double that {fn}(.5) returns (the KTR TS1 row): what the rules "
                    f"above say for that double" + (" -- error 5, LOG(.5) being negative" if fn == "LOG" else "")
                    + ".",
                    lambda c: fx_by(c, "nested"), nested_ok))
    return out + _common(fn, tag, f"2. {fn}(x): forms, errors and assignment")


def nested_ok(c):
    """F(F(.5)) is F of the double the same machine returns for F(.5!) (its KTR TS1 row): the model's outcome for
    that double's bytes"""
    i = c.inner
    if i.vt == 255:
        return False
    return outcome(c, MODELS[c.fn]("D", i.res))
