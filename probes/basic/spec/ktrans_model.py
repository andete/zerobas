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
approximates sin(2 pi g), g = frac(rd14(1/4 - p)). A p below 1E-64 in size is 0. The bound is then against
sin(2 pi f) -- the true sine of the REDUCED angle -- not against sin(x), which the reference misses by up to 0.5
for x >= 1E12 (a control).

The two roundings differ (goldfish pass 1, 2026-11-24, KTR TS3): p = x * C is rounded half UP in size (SIN(9.5):
p = 1.51197195937305 exactly, ...731 fits within 1.9 units, ...730 is 626 units off); 1/4 - p is rounded half DOWN
in size -- a tie goes toward zero (rd14). Ties in 1/4 - p are every case where p has 13 integer digits (x from about
6.3E12 to 6.3E13): COS(1.2E13) is the half-turn zero (1/4 - p = -1909859317102.55 -> .5; half-even and half-up both
give .6), COS(1.1E13) .58778525229247 (-1750704374010.65 -> .6; half-up gives .7). Truncation fits the ties too but
not the other cases (a control)."""
import os
import re
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
OUTPUTS["FY"] = FIELDS + ["arg"]           # FY: ARG holds STR$'s length and first 7 bytes (0 where no STR$ ran)
OUTPUTS_DESC = KM.OUTPUTS_DESC
R_SENT = KM.R_SENT
NB = KM.NB
ONE = bytes([0x41, 0x10, 0, 0, 0, 0, 0, 0])                      # the double 1
ZERO8 = bytes(8)
TWOPI_ZERO = bytes([0x00, 0x62, 0x83, 0x18, 0x53, 0x07, 0x17, 0x96])   # exponent 0, the digits of 2 pi
ATN_NEGZERO = bytes([0x00, 0x10, 0, 0, 0, 0, 0, 0])                     # ATN of a zero whose sign bit is set

# --- the bounds, in units of the 14th significant digit of the target (measured worst on the VG-8020 in ( )) ---
B_EXP_SMALL = 3          # |x| <= 1                      (2.5: EXP(.9!), EXP(1))
B_EXP_POS = 500          # x > 1                         (472: EXP(145.0628#))
B_EXP_NEG = 40000        # x < -1, and the digits below 1E-64 (39533: EXP(-147.36544595#); 39525: EXP(-149.668#))
B_LOG = 9                #                               (8.3: LOG(.5235987755983#))
B_TRIG = 2               # SIN / COS against the reduced angle (COS 1.95: COS(.2!); SIN 1.86: SIN(1D11))
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
EXP_HUGE = Fr(-75460)         # Overflow from here down: measured 0 at -75453, Overflow at -75460 (KTR TS3); the edge
                              # between is not measured


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


def rd14(v):
    """v rounded to 14 significant digits, half DOWN in size (a tie goes toward zero); below 1E-64 in size 0 --
    COS's rounding of 1/4 - p"""
    v = Fr(v)
    if v == 0:
        return v
    e = dexp(v)
    m = abs(v) * Fr(10) ** (14 - e)
    n = int(m)
    if m - n > Fr(1, 2):
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
    """g: COS's reduced angle in turns -- a quarter turn minus the angle's turns, rounded half down, its fraction"""
    return frac(rd14(Fr(1, 4) - r14(Fr(x) * C_TURN)))


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
    if x <= EXP_HUGE:
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
        if b[0] & 0x80:
            return "bytes", ATN_NEGZERO
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
    if c.src in FIXED:
        return argval(*FX_ARG[c.why])
    return argval(c.ty, argb(c))


# the fixed statements' arguments: the type and bytes each literal is (kmath's, measured through USR there)
FX_ARG = dict(KM.FX_ARG)
FX_ARG.pop("nested")
FX_ARG["a single with exponent byte 0, digit bytes 12 34 56"] = ("S", bytes([0x00, 0x12, 0x34, 0x56]))   # KTR FY
FX_ARG["a single with exponent byte 80, digit bytes 12 34 56"] = ("S", bytes([0x80, 0x12, 0x34, 0x56]))
FORM_WHYS = tuple(w for w in FX_ARG if "exponent byte" not in w)
ODD_WHYS = tuple(w for w in FX_ARG if "exponent byte" in w)
FIXED = ("FX", "FY")
NESTED_IN = ("S", KM.enc(Fr(1, 2), "S"))           # F(F(.5)): the inner call's argument


def want(c, model=None):
    m = model or MODELS[c.fn]
    if c.src not in FIXED:
        return m(c.ty, argb(c))
    ty, b = FX_ARG[c.why]
    return m(ty, b)


def fx_by(c, *whys):
    return c.src in FIXED and c.why in whys


def mx(c):
    return c.src not in FIXED


def load(fn):
    """this keyword's cases from every group, the reference's and zerobas's. A matrix case also carries `neg` (the
    same group's case of -x, if measured, else None) and, for TAN, `sinrow` / `cosrow` (SIN(x) and COS(x) from the
    same group) -- the partners the pair rules read"""
    out = {"ref": [], "zb": []}
    half = {}
    rows = {"ref": {}, "zb": {}}          # (group, fn, text or why) -> case, every group so far: FY's partners
    for g in ktrans.ORDER:
        cs = ktrans.load(g)
        for who in out:
            by = {(c.fn, c.text): c for c in cs[who] if c.src not in FIXED}
            rows[who].update({(g, c.fn, c.text if c.src not in FIXED else c.why): c for c in cs[who]})
            if g == "TS1":
                half[who] = by[(fn, ".5")]
            for c in cs[who]:
                if c.fn != fn:
                    continue
                c.neg = c.sinrow = c.cosrow = c.inner = None
                if c.src not in FIXED:
                    t = c.text
                    c.neg = by.get((fn, t[1:] if t.startswith("-") else "-" + t))
                    c.sinrow, c.cosrow = by[("SIN", t)], by[("COS", t)]
                elif c.why == "nested":
                    c.inner = half[who]
                elif c.src == "FY" and c.why not in FX_ARG:
                    c.inner = rows[who][FY_INNER[re.search(r"[A-Z]{3}\([^)]*\)", c.why).group(0)]]
                out[who].append(c)
    return out


# FY: the call each statement uses, and the same machine's own row of that call (its matrix row, or FX's)
FY_INNER = {"SIN(0)": ("TI", "SIN", "0"), "COS(7E13)": ("TS2", "COS", "7E13"), "TAN(1E13)": ("TS2", "TAN", "1E13"),
            "EXP(-147.4)": ("TS1", "EXP", "-147.4"),
            "ATN(N!)": ("FX", "ATN", "a single with exponent byte 80, digit bytes 10 00 00"),
            "TAN(1.3E13)": ("TS3", "TAN", "1.3E13")}
STR_ZERO = bytes([2, 0x20, 0x30, 0, 0, 0, 0, 0])      # STR$'s " 0": length 2, then its bytes


def round6(b):
    """a double's 8 bytes as a single's 4: the 14 digits rounded half up to 6, the exponent byte kept (+1 on a
    carry)"""
    d = int(b[1:].hex())
    n, r = divmod(d, 10 ** 8)
    e = b[0]
    if r >= 5 * 10 ** 7:
        n += 1
    if n == 10 ** 6:
        n, e = 10 ** 5, e + 1
    return bytes([e]) + bytes.fromhex(f"{n:06d}")


def fy_use(c):
    """a FY statement that USES a result (not the 12 34 56 arguments): what it records, from the same machine's own
    row of the call (c.inner) -- STR$ " 0"; = 0 true, < 0 false; + 1 exactly 1; * 1E10 and negation the same bytes;
    a single the digits rounded to 6; an integer 0"""
    z = c.inner.res
    if z is None or c.e1 or c.e2:
        return False
    w = c.why
    if "PRINT's number format" in w:
        return c.vt == 255 and c.res is None and c.rbytes == R_SENT and c.arg == STR_ZERO
    if c.arg != ZERO8:
        return False
    if "compared with 0" in w:
        return c.vt == 255 and c.res is None and c.rbytes == ONE
    if "below 0" in w:
        return c.vt == 255 and c.res is None and c.rbytes == ZERO8
    if "plus 1" in w:
        return c.vt == 8 and c.res == ONE and c.rbytes == ONE
    if "times 1E10" in w or w.startswith("minus"):
        return c.vt == 8 and c.res == z and c.rbytes == z
    if "assigned to a single" in w:
        return c.vt == 4 and c.res == round6(z) and c.rbytes == c.res + bytes(4)
    if "assigned to an integer" in w:
        return c.vt == 2 and c.res == bytes(2) and c.rbytes == ZERO8
    raise KeyError(w)


def fy_by(c):
    return c.src == "FY" and c.why not in FX_ARG


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
                 f"EXP(-3) 5 units, EXP(-2) 5,930, EXP(-50) 331, EXP(-147.3) 27,178, EXP(-147.36544595#) 39,533 "
                 f"(all high). It is not a 14-digit reduction's artefact: 10^r14(x * log10 e) misses EXP(-2) by "
                 f"5,930 units too (a control).",
                 cls(lambda x: x < -1, lambda x: True), _ok),
            Rule("R-EXP-OVER", sec,
                 "From e^x >= 1E63 on it is error 6 (Overflow): the edge is 63 ln 10 = 145.0628608586..., and "
                 "145.06286085# still gives 9.9999999137221E+62, 145.06286086# Overflow.",
                 _sel(lambda c, w: w == ("err", 6) and xval(c) > 0), _ok),
            Rule("R-EXP-TINY", sec,
                 f"Where 1E-65 <= e^x < 1E-64 (x from -64 ln 10 = -147.3654459516...: -147.36544595# still gives "
                 f"1.0000000055722E-64, -147.36544596# the first such zero; down to -149.668) the result is a double "
                 f"whose exponent byte is 0 -- it reads as zero -- and whose digit bytes are the digits of e^x (within "
                 f"{B_EXP_NEG} units; measured worst 39,525, EXP(-149.668#)): EXP(-147.4) is 00 96 60 36 12 55 89 73.",
                 _sel(lambda c, w: w[0] == "zdig"), _ok),
            Rule("R-EXP-BAND", sec,
                 "Where 1E-129 <= e^x < 1E-65 (x from -149.67 to -297.033) it is error 6 (Overflow), not 0.",
                 _sel(lambda c, w: w == ("err", 6) and EXP_M129 <= xval(c) < 0), _ok),
            Rule("R-EXP-FLUSH", sec,
                 "Below that, down to at least x = -75453 (e^x < 1E-129: -297.04, -298, -1000, -32768, -40000, "
                 "-65536, -70000, -75000, -75453) it is a clean double zero, 8 zero bytes.",
                 _sel(lambda c, w: w == ("bytes", ZERO8)), _ok),
            Rule("R-EXP-HUGE", sec,
                 "From x = -75460 down it is error 6 (Overflow) again (measured -75460, -75500, -76000, -80000, "
                 "-90000, -99999, -1E5, -1E6, -1E10, -1E30, -1E38, -9.99999E62, -9.9999999999999D62 ...); between "
                 "-75453 and -75460 it is not measured.",
                 _sel(lambda c, w: w == ("err", 6) and xval(c) <= EXP_HUGE), _ok),
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
                 f"ln x -- measured worst 8.3 (LOG(.5235987755983#)), the next 7.3 (LOG(2.718281828459#)); LOG(2) "
                 f"1.5 units low, LOG(1D-64) and "
                 f"LOG(9.99999E62) within 0.5.",
                 _sel(lambda c, w: w[0] == "near"), _ok),
        ]
    elif fn in ("SIN", "COS"):
        red = ("f = frac(p), p = x * 0.15915494309190 rounded half up to 14 significant digits, a p below 1E-64 "
               "in size 0" if fn == "SIN" else
               "g = frac(rd14(1/4 - p)), p = x * 0.15915494309190 rounded half up to 14 significant digits, and "
               "1/4 - p rounded to 14 digits half DOWN in size -- a tie goes toward zero")
        out = []
        if fn == "COS":
            out.append(Rule("R-COS-ONE", sec, "COS of zero is exactly the double 1 (41 10 00 00 00 00 00 00), "
                            "whatever the zero's digit or sign bytes.",
                            _sel(lambda c, w: w == ("bytes", ONE)), _ok))
        out += [
            Rule(f"R-{fn}-ZERO", sec,
                 f"The result is a DOUBLE. When the reduced angle is a whole or a half turn ({red}; a whole turn "
                 f"when p is 0 or whole) it is a zero whose digit bytes are 2 pi's: 00 62 83 18 53 07 17 96 -- "
                 + ("SIN(0), SIN(6.28318E-64) (p is 9.99999E-65: 0; SIN(6.28319E-64) is not), "
                    "SIN(3.1415926535897#) (p is .5); where p has 13 integer digits (x from about 6.3E12) its one "
                    "fraction digit decides: 0 or 5 gives this zero (SIN(1E13), SIN(1.5E13), SIN(3E13)), any other "
                    "does not (SIN(1.1E13) is -.58778525229247, f = .9); from 6.3E13 up p has no fraction digit "
                    "and every x gives it." if fn == "SIN" else
                    "where p has 13 integer digits (x from about 6.3E12) every 1/4 - p is a tie, and a fraction "
                    "digit 3 or 8 in p rounds it to a whole or half turn: COS(7E12), COS(1.2E13) (1/4 - p = "
                    "-1909859317102.55 -> .5), COS(1.7E13); from 6.3E13 up every x gives it (COS(7E13))."),
                 _sel(lambda c, w: w == ("bytes", TWOPI_ZERO)), _ok),
            Rule(f"R-{fn}-NEAR", sec,
                 f"Otherwise a double within {B_TRIG} units of the 14th significant digit of sin(2 pi "
                 f"{'f' if fn == 'SIN' else 'g'}) -- the sine of the REDUCED angle, not {fn.lower()}(x): "
                 + ("SIN(1000) is .82687954054849 (the reduced target .8268795405485..., sin(1000) is "
                    ".8268795405320...), SIN(3.1415926535898#) -1.2566370614359E-13 (f = -2E-14 turns from a half "
                    "turn), SIN(1E12) -.58778525229247 (f = .9). Measured worst 1.86 units (SIN(1D11))."
                    if fn == "SIN" else
                    "COS(1.5707963267949#) is -6.2831853071796E-14 (g = -1E-14), COS(4.71239!) 1.0196154567834E-06, "
                    "COS(1.1E13) .58778525229247 (1/4 - p = -1750704374010.65 rounds to .6, g = -.6). Measured "
                    "worst 1.95 units (COS(.2!))."),
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
                 "is error 6 (Overflow): every x from 6.3E13 up (7E13, 1E14, 1E38, 9.99999E62, the negatives too), "
                 "and below it where p has 13 integer digits and the fraction digit 3 or 8 (TAN(7E12), "
                 "TAN(1.2E13), TAN(1.7E13); TAN(1.3E13) is 1.6180339887499).",
                 _sel(lambda c, w: w == ("err", 6)), _ok),
            Rule("R-TAN-ZERO", sec,
                 "Otherwise, when SIN's is (SIN(x) the 2-pi-digit zero), TAN is that zero too: 00 62 83 18 53 07 17 "
                 "96 -- TAN(0), TAN(6.28318E-64), TAN(3.1415926535897#), TAN(1E13), TAN(1.5E13), TAN(3E13).",
                 _sel(lambda c, w: w == ("bytes", TWOPI_ZERO)), _ok),
            Rule("R-TAN-NEAR", sec,
                 f"Otherwise a DOUBLE within {B_TAN} units of the 14th significant digit of sin(2 pi f) / "
                 f"sin(2 pi g) -- the reduced angles of SIN and COS (their pages): TAN(1.5707963267949#) is "
                 f"-15915494309189 (g is -1E-14 turns), TAN(1) 1.5574077246549. Measured worst 5.2 units "
                 f"(TAN(4.71239!)).",
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
                 "A zero argument gives a zero DOUBLE: ATN(0) is 8 zero bytes; a single whose exponent byte is 0 "
                 "keeps its digit bytes (00 10 00 00 gives 00 10 00 00 00 00 00 00, 00 12 34 56 gives 00 12 34 56 "
                 "00 00 00 00); with the sign bit set too (exponent byte &H80) it is 00 10 00 00 00 00 00 00 "
                 "whatever the digits (80 10 00 00 and 80 12 34 56 alike).",
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
                    "On a non-canonical single (exponent byte 0 or &H80, digit bytes 10 00 00 or 12 34 56) it gives "
                    "what the rules above say for a zero argument.", lambda c: fx_by(c, *ODD_WHYS),
                    lambda c: _ok(c) and (c.src != "FY" or c.arg == ZERO8)))
    if fn in USE_WHAT:
        out.append(Rule(f"R-{tag}-USE", sec,
                        f"{USE_WHAT[fn]} is an ordinary zero to the rest of BASIC (KTR FY, each the same machine's "
                        f"own zero): PRINT's number format (STR$) gives \" 0\", it equals 0 and is not below 0, plus 1 "
                        f"is exactly the double 1, and an integer variable takes it as 0; but times 1E10 and negated "
                        f"it comes back with the SAME bytes (exponent byte 0, no sign bit), and a single variable "
                        f"keeps exponent byte 0 and the digits rounded half up to 6 ({USE_EX[fn]})."
                        + (" TAN(1.3E13) in a single is 1.61803 (41 16 18 03), the double rounded the same way."
                           if fn == "TAN" else ""),
                        fy_by, fy_use))
    out.append(Rule(f"R-{tag}-NESTED", sec,
                    f"{fn}({fn}(.5)) is {fn} of the double that {fn}(.5) returns (the KTR TS1 row): what the rules "
                    f"above say for that double" + (" -- error 5, LOG(.5) being negative" if fn == "LOG" else "")
                    + ".",
                    lambda c: fx_by(c, "nested"), nested_ok))
    out = out + _common(fn, tag, f"2. {fn}(x): forms, errors and assignment")
    for r in out:
        if r.id.endswith("-ASSIGN"):
            r.select = lambda c: not fy_by(c)
    return out


USE_WHAT = {"SIN": "The 2-pi-digit zero (SIN(0))", "COS": "The 2-pi-digit zero (COS(7E13))",
            "TAN": "The 2-pi-digit zero (TAN(1E13))",
            "EXP": "The exponent-0 result below 1E-64 (EXP(-147.4): 00 96 60 36 12 55 89 73)",
            "ATN": "The zero ATN gives for a signed zero single (80 10 00 00: 00 10 00 00 00 00 00 00)"}
USE_EX = {"SIN": "00 62 83 19", "COS": "00 62 83 19", "TAN": "00 62 83 19", "EXP": "00 96 60 36",
          "ATN": "00 10 00 00"}


def nested_ok(c):
    """F(F(.5)) is F of the double the same machine returns for F(.5!) (its KTR TS1 row): the model's outcome for
    that double's bytes"""
    i = c.inner
    if i.vt == 255:
        return False
    return outcome(c, MODELS[c.fn]("D", i.res))
