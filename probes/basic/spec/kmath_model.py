#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""The shared model and rule builders for ABS / SGN / INT / FIX / SQR's EXECUTABLE RULES (docs/spec-method.md §3a,
docs/keywords/spec-plan.md). The cases come from probes/basic/spec/kmath.py's committed run (scratchpad/KMA_run1.out);
each page's module takes its own keyword's cases from `load(fn)` and its rules from `rules(fn)`.

The models work from what the record holds: the argument's own bytes (2 / 4 / 8) and its type. A result is the
type USR saw (2 / 4 / 8) and its own bytes, compared byte for byte; R's 8 bytes are the same result assigned to a
double. SQR's last digit is the reference's own (docs/keywords/SQR.md: not reproducible from the printed digits), so
its rule is a bound, not bytes."""
import math
from decimal import Context, Decimal
import os
import sys
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
import kmath  # noqa: E402
import ramrec  # noqa: E402
from spec_rules import Rule  # noqa: E402

FIELDS = ["e1", "rbytes", "e2", "vt", "res"]
OUTPUTS = {g: FIELDS for g in kmath.ORDER}
OUTPUTS_DESC = ("each case's error from `R=F(x)` and from `Q=USR(F(x))`, R's 8 bytes, the result's type as USR saw "
                "it and the result's own bytes")
R_SENT = bytes([0xC5, 0x12, 0x34, 0x50, 0, 0, 0, 0])     # R = -12345 (a double) before every case
NB = {"I": 2, "S": 4, "D": 8}
VT = {"I": 2, "S": 4, "D": 8}
SQR_BOUND = 3                                           # units of the 14th digit (measured: -1.9 .. +2.5)


# the LET rows of kmath's FX group (fn "LET") each page loads: FIX's the two exponent-0 singles assigned, SQR's
# the two zero roots assigned after R=0 / R=-12345 (goldfish pass 1: they were measured but loaded by no page)
LET_ROWS = {"FIX": ("a single with exponent byte 0, digit bytes 10 00 00, assigned",
                    "FIX(.5!) stored in a single, then assigned"),
            "SQR": ("SQR(0%) after R=0", "SQR(0!) after R=-12345")}
MX = ("MI", "MS", "MD")


def load(fn):
    """this keyword's cases: the three matrix groups', the fixed statements' (FX, FY, FZ) and its LET rows, the
    reference's and zerobas's -- after the apparatus checks (check_read, check_lit)"""
    out = {"ref": [], "zb": []}
    for g in kmath.ORDER:
        cs = kmath.load(g)
        if g in MX:
            check_read(cs, g)
        if g == "FY":
            check_lit(cs)
        for who in out:
            out[who] += [c for c in cs[who] if c.fn == fn or (c.fn == "LET" and c.why in LET_ROWS.get(fn, ()))]
    return out


def text_value(t):
    """the value a DATA / literal text stands for, exactly ("1D14" a double's exponent)"""
    return Fraction(Decimal(t.replace("D", "E")))


def check_read(cs, g):
    """apparatus (goldfish pass 1): every row's recorded argument is the DATA text's value in the row's type, on
    both machines -- so the six rows of one text (ID, ABS, SGN, INT, FIX, SQR) saw the same argument, no function
    changed its argument variable, and the two machines READ the text alike. Exits otherwise."""
    bad = [f"{who} {c.id}" for who in cs for c in cs[who]
           if c.arg != enc(text_value(c.text), c.ty) + bytes(8 - NB[c.ty])]
    if bad:
        sys.exit(f"FAIL: {g}: the argument READ is not the DATA text's value: {', '.join(bad[:8])}")


def check_lit(cs):
    """apparatus (goldfish pass 1): FY's LIT rows (`R=<literal>`, `Q=USR(<literal>)`, no function) give each
    literal's type and bytes as LIT says, on both machines -- the literal types FX_ARG and LIT use are MEASURED.
    Exits otherwise."""
    bad = [f"{who} {c.id}" for who in cs for c in cs[who] if c.fn == "LIT" and not (
        c.e1 == 0 and c.e2 == 0 and c.vt == VT[LIT[c.lit][0]] and c.res == LIT[c.lit][1]
        and c.rbytes == as_double(c.vt, c.res))]
    if bad:
        sys.exit(f"FAIL: FY: a literal's measured type / bytes are not LIT's: {', '.join(bad[:8])}")


# --- numbers as bytes ---

def enc(v, ty):
    """the canonical bytes of the value v in type ty ("I", "S", "D"); v must fit exactly"""
    v = Fraction(v)
    if ty == "I":
        assert v.denominator == 1 and -32768 <= v <= 32767, v
        return (int(v) & 0xFFFF).to_bytes(2, "little")
    nd = 6 if ty == "S" else 14
    if v == 0:
        return bytes(NB[ty])
    neg = v < 0
    a = abs(v)
    e = 0
    while a >= 1:
        a /= 10
        e += 1
    while a < Fraction(1, 10):
        a *= 10
        e -= 1
    m = a * 10 ** nd
    assert m.denominator == 1, f"{v} is not {nd} digits"
    ds = str(m.numerator).rjust(nd, "0")
    return bytes([(0x80 if neg else 0) | (64 + e)]) + bytes(int(ds[k:k + 2], 16) for k in range(0, nd, 2))


def as_double(vt, b):
    """R's 8 bytes after `R = <a result of type vt with bytes b>`: an integer by its value; a single's own 4 bytes,
    then four zero bytes -- its exponent byte and digits kept as they are (an exponent byte of 0 with digits too)"""
    if vt == 2:
        return enc(ramrec.number(b), "D")
    return b + bytes(8 - len(b))


def value(b):
    return ramrec.number(b)


def _digits(b):
    return "".join(f"{x:02x}" for x in b[1:])


def _pack(b0, ds):
    return bytes([b0]) + bytes(int(ds[k:k + 2], 16) for k in range(0, len(ds), 2))


# --- the models: (ty, argument bytes) -> ("err", code) | ("num", vt, bytes) | ("near", exact root) ---

def m_abs(ty, b, int_edge="S"):
    """`int_edge`: the type of ABS(-32768%) (the page's rule "S"; a control alters it)"""
    if ty == "I":
        v = value(b)
        if v == -32768:
            return "num", VT[int_edge], enc(32768, int_edge)
        return "num", 2, enc(abs(v), "I")
    return "num", VT[ty], bytes([b[0] & 0x7F]) + b[1:]


def m_sgn(ty, b, zero="byte"):
    """`zero`: "byte" -- only an exponent byte of exactly 0 is a zero (the page's rule); "exp" -- any exponent 0,
    the sign bit ignored (a control)"""
    if ty == "I":
        v = value(b)
    elif b[0] == 0 or (zero == "exp" and b[0] & 0x7F == 0):
        v = 0
    else:
        v = -1 if b[0] & 0x80 else 1
    return "num", 2, enc((v > 0) - (v < 0), "I")


def m_fix(ty, b, small="digits"):
    """toward zero, in the argument's own type: the digits after the point become 0; below 1 in size the result is
    an exponent byte of 0, the sign dropped, the digit bytes kept as they were (`small`: "digits" the page's rule,
    "zero" a canonical zero -- a control)"""
    if ty == "I":
        return "num", 2, b
    p = (b[0] & 0x7F) - 64
    ds = _digits(b)
    if b[0] & 0x7F == 0 or p <= 0:
        return "num", VT[ty], bytes(len(b)) if small == "zero" else bytes([0]) + b[1:]
    if p >= len(ds):
        return "num", VT[ty], b
    return "num", VT[ty], _pack(b[0], ds[:p] + "0" * (len(ds) - p))


def _frac(b):
    """the argument has digits after its point (a negative exponent byte of 0 counts: all its digits are)"""
    p = (b[0] & 0x7F) - 64
    ds = _digits(b)
    if b[0] & 0x7F == 0 or p <= 0:
        return any(c != "0" for c in ds)
    return any(c != "0" for c in ds[p:])


def m_int(ty, b, neg_type="split"):
    """down (floor): FIX, except for a negative argument with digits after the point, which is FIX - 1 -- as the
    INTEGER -1 when FIX is 0 (the argument above -1), else as a DOUBLE (`neg_type`: "split" the page's rule; "same"
    the argument's own type, a control)"""
    if ty == "I" or not (b[0] & 0x80 and _frac(b)):
        return m_fix(ty, b)
    p = (b[0] & 0x7F) - 64
    t = value(m_fix(ty, b)[2]) if p > 0 else 0
    if neg_type == "same":
        return "num", VT[ty], enc(t - 1, ty)
    if p <= 0:
        return "num", 2, enc(-1, "I")
    return "num", 8, enc(t - 1, "D")


def _exact_root(v):
    """the square root of v if it has at most 14 significant digits, else None (v a decimal fraction)"""
    for k in range(0, 200, 2):
        w = v * Fraction(10) ** k
        if w.denominator == 1:
            r = math.isqrt(w.numerator)
            if r * r != w.numerator:
                return None
            root = Fraction(r) / Fraction(10) ** (k // 2)
            try:
                enc(root, "D")
            except AssertionError:
                return None
            return root
    return None


def m_sqr(ty, b):
    """error 5 for a negative argument (the sign bit set: also an exponent byte of &H80); a zero (exponent byte 0)
    is returned as a double, its digit bytes kept; an exact root of at most 14 digits is that root; any other is
    "near" (within SQR_BOUND units of the 14th digit of the exact root). Always a double."""
    if ty == "I":
        v = value(b)
        if v < 0:
            return "err", 5
        if v == 0:
            return "num", 8, bytes(8)
    else:
        if b[0] & 0x80:
            return "err", 5
        if b[0] == 0:
            return "num", 8, b + bytes(8 - len(b))
        v = value(b)
    r = _exact_root(v)
    if r is not None:
        return "num", 8, enc(r, "D")
    return "near", v


MODELS = {"ABS": m_abs, "SGN": m_sgn, "INT": m_int, "FIX": m_fix, "SQR": m_sqr}


def near(res, v, bound=SQR_BOUND):
    """res (8 bytes) is within `bound` units of the 14th significant digit of sqrt(v) -- the unit sized from the
    EXACT root's decade, not the result's (goldfish pass 1: a result that rounds up across a power of ten, as
    SQR(.99999999999999#) -> 1, was otherwise judged with a unit ten times too large)"""
    x = value(res)
    if x <= 0:
        return False
    # the exact root's decade: 10^(e-1) <= sqrt(v) < 10^e  <=>  10^(2e-2) <= v < 10^(2e)
    e = 0
    while Fraction(10) ** (2 * e) <= v:
        e += 1
    while Fraction(10) ** (2 * e - 2) > v:
        e -= 1
    ulp = Fraction(10) ** (e - 14)
    lo, hi = x - bound * ulp, x + bound * ulp
    return (lo <= 0 or lo * lo < v) and v < hi * hi


# --- what a case recorded ---

def no_usr(c, code):
    """a statement with no USR form (not an expression): `code` from it, R still holding its sentinel, USR never
    called (its type cell still 255)"""
    return c.e1 == code and c.rbytes == R_SENT and c.e2 == 0 and c.vt == 255 and c.res is None


def error_is(c, code):
    """both forms raised `code`, R still holds its sentinel and USR was never reached"""
    return c.e1 == code and c.e2 == code and c.rbytes == R_SENT and c.vt == 255 and c.res is None


def result_is(c, vt, b):
    """no error in either form, the result is of type vt with bytes b (R is the ASSIGN rule's)"""
    return c.e1 == 0 and c.e2 == 0 and c.vt == vt and c.res == b


def outcome(c, want, bound=SQR_BOUND):
    k = want[0]
    if k == "err":
        return error_is(c, want[1])
    if k == "num":
        return result_is(c, want[1], want[2])
    return (c.e1 == 0 and c.e2 == 0 and c.vt == 8 and c.res is not None and near(c.res, want[1], bound))


def argb(c):
    return c.arg[:NB[c.ty]]


def want(c, model=None):
    """the model's outcome for a matrix case, or for a fixed statement's value form"""
    m = model or MODELS[c.fn]
    if c.src in MX:
        return m(c.ty, argb(c))
    if c.src in ("FY", "FZ"):
        ty, b = LIT[c.lit]
        for _ in range(getattr(c, "depth", None) or 1):
            k = m(ty, b)
            if k[0] != "num":
                return k
            ty, b = {2: "I", 4: "S", 8: "D"}[k[1]], k[2]
        return k
    ty, b = FX_ARG[c.why]
    if c.why == "nested":
        k, vt, b = MODELS[c.fn](ty, b)
        ty = {2: "I", 4: "S", 8: "D"}[vt]
    return m(ty, b)


# --- the fixed statements' arguments: the type and bytes each literal is (measured through USR on the
#     matrix-free forms: 2.5 is a single, 7 an integer, -32768 a single, 1/4 a double) ---

FX_ARG = {
    "a literal with a point": ("S", enc(Fraction(5, 2), "S")),
    "a negative literal with a point": ("S", enc(Fraction(-5, 2), "S")),
    "a space before the parenthesis": ("S", enc(Fraction(5, 2), "S")),
    "spaces around the argument": ("S", enc(Fraction(5, 2), "S")),
    "an integer literal": ("I", enc(7, "I")),
    "a single literal": ("S", enc(Fraction(5, 2), "S")),
    "a double literal": ("D", enc(Fraction(5, 2), "D")),
    "a literal without a point": ("I", enc(7, "I")),
    "a hex literal (the integer -32768)": ("I", enc(-32768, "I")),
    "minus the literal 32768": ("S", enc(-32768, "S")),
    "minus zero": ("I", enc(0, "I")),
    "an expression": ("D", enc(Fraction(1, 4), "D")),
    "nested": ("S", enc(Fraction(9, 4), "S")),
    "a single with exponent byte 0, digit bytes 10 00 00": ("S", bytes([0x00, 0x10, 0, 0])),
    "a single with exponent byte 80, digit bytes 10 00 00": ("S", bytes([0x80, 0x10, 0, 0])),
}
TYPE_WHYS = ("a string as the argument", "a string variable as the argument", "the result assigned to a string")
SYNTAX_WHYS = ("no argument", "an extra argument", "no closing parenthesis", "no parenthesis")
FORM_WHYS = tuple(w for w in FX_ARG if "exponent byte" not in w)
ODD_WHYS = tuple(w for w in FX_ARG if "exponent byte" in w)


def fx_by(c, *whys):
    return c.src == "FX" and c.why in whys


def mx(c):
    return c.src in MX


def fy(c, *kinds):
    return c.src in ("FY", "FZ") and getattr(c, "kind", None) in kinds


# --- goldfish pass 1 (FY / FZ): the literals measured, the order of the checks, an exponent-0 zero used, the
#     result stored in T% / T! ---

LIT = {
    "2.5": ("S", enc(Fraction(5, 2), "S")), "-2.5": ("S", enc(Fraction(-5, 2), "S")), "7": ("I", enc(7, "I")),
    "7%": ("I", enc(7, "I")), "2.5!": ("S", enc(Fraction(5, 2), "S")), "2.5#": ("D", enc(Fraction(5, 2), "D")),
    "&H8000": ("I", enc(-32768, "I")), "-32768": ("S", enc(-32768, "S")), "-0": ("I", enc(0, "I")),
    "1/4": ("D", enc(Fraction(1, 4), "D")), "2.25": ("S", enc(Fraction(9, 4), "S")),
    "-1E38": ("S", enc(-10 ** 38, "S")), ".5!": ("S", enc(Fraction(1, 2), "S")),
    "-.5!": ("S", enc(Fraction(-1, 2), "S")), "1E10": ("S", enc(10 ** 10, "S")),
    "32767.9": ("S", enc(Fraction(327679, 10), "S")), "-32768.5": ("S", enc(Fraction(-65537, 2), "S")),
    "-1.5": ("S", enc(Fraction(-3, 2), "S")), "-.5": ("S", enc(Fraction(-1, 2), "S")), "1": ("I", enc(1, "I")),
    "2": ("I", enc(2, "I")), "3": ("I", enc(3, "I")), "0": ("I", enc(0, "I")),
    "N!": ("S", bytes([0x00, 0x10, 0, 0])),          # the POKEd single (PRE0), not a literal: not a LIT row
}
# the order of the checks: the argument is evaluated (its own error wins), THEN the `)` / `,` is required, THEN the
# argument's type is checked
ORDER_ERR = {"the argument's own error, no closing parenthesis": 11, "a string argument, no closing parenthesis": 2,
             "the argument's own error, then an extra argument": 11, "a string argument, then an extra argument": 2}
FY_SYNTAX_WHYS = ("PRINT and the name alone", "two arguments, as the pages write it")


def zero_use(why, z=Fraction(0)):
    """what `R=<expr>` gives for FY's "an exponent-0 zero used" rows, the zero being worth z (0: the rule; a
    control passes .5, the zero's digits read as a value). (vt, bytes)."""
    w = why.split(": ", 1)[1]
    if w == "+1":
        return 8, enc(z + 1, "D")                       # measured a DOUBLE on both machines (open: why)
    if w == "*3":
        # value 0: exponent byte 0; the reference's digit bytes are 30 00 ..., the other operand's (one case)
        return 8, (bytes([0, 0x30]) + bytes(6)) if z == 0 else enc(3 * z, "D")
    if w == "=0":
        return 2, enc(int(z == 0), "I")
    if w == ">0":
        return 2, enc(int(z > 0), "I")
    if w == "<0":
        return 2, enc(0, "I")                           # FIX(-.5!) / INT(.5!): the sign is dropped / positive
    if w == "SGN":
        return 2, enc((z > 0) - (z < 0), "I")
    if w == "LEN(STR$)":
        return 2, enc(2 if z == 0 else 3, "I")          # " 0" / " .5"
    if w == "STR$'s digit":
        return 2, enc(48 if z == 0 else 46, "I")        # "0" / "."
    raise KeyError(why)


T_SENT = {"%": enc(-7, "I"), "!": enc(-7, "S")}


def target(c, to_int=lambda v: int(v), zero_let=False):
    """what `T%=F(x)` / `T!=F(x)` leaves in T: ("err", code, T's sentinel) or ("num", vt, bytes). An integer
    target takes the value with its fraction DROPPED (`to_int`: the rule's truncation; a control passes rounding),
    Overflow (6) outside -32768..32767; a single target takes a single as its own 4 bytes (an exponent-0 one too;
    `zero_let`: zerobas's 4 zero bytes, a control), an integer by value, a double shortened to 6 digits."""
    k = MODELS[c.fn](*LIT[c.lit])
    if k[0] == "err":
        return "err", k[1], T_SENT[c.target]
    if k[0] == "near":
        ctx = Context(prec=40)
        v = Fraction(ctx.divide(Decimal(k[1].numerator), Decimal(k[1].denominator)).sqrt(ctx))
    else:
        v = value(k[2])
    if c.target == "%":
        r = to_int(v)
        if not -32768 <= r <= 32767:
            return "err", 6, T_SENT["%"]
        return "num", 2, enc(r, "I")
    if k[0] == "num" and k[1] == 4:
        return "num", 4, bytes(4) if zero_let and k[2][0] == 0 else k[2]
    if k[0] == "num" and k[1] == 2:
        return "num", 4, enc(v, "S")
    if v == 0:
        return "num", 4, bytes(4)
    s1 = Fraction(Context(prec=6).divide(Decimal(v.numerator), Decimal(v.denominator)))
    return "num", 4, enc(s1, "S")


def target_is(c, t):
    """the assignment raised t's error (or none), R was never touched, USR(T) ran and saw T's type and bytes"""
    code = t[1] if t[0] == "err" else 0
    vt, b = (2 if c.target == "%" else 4, t[2]) if t[0] == "err" else (t[1], t[2])
    return c.e1 == code and c.rbytes == R_SENT and c.e2 == 0 and c.vt == vt and c.res == b


def assigned(c):
    """R holds what the case's result is when assigned to a double, or its sentinel after an error"""
    return (c.rbytes == R_SENT) if c.vt == 255 else (c.res is not None and c.rbytes == as_double(c.vt, c.res))


ASSIGN_EG = {
    "ABS": "so ABS of the POKEd single 00 10 00 00 leaves R 00 10 00 00 00 00 00 00, KMA FX 21",
    "SGN": "SGN's result is an integer, stored by its value: SGN(-2.5) leaves R the double -1",
    "INT": "so INT(.5!)'s exponent-0 result keeps its digit bytes in R: 00 50 00 00 00 00 00 00",
    "FIX": "so FIX(.5!)'s exponent-0 result keeps its digit bytes in R: 00 50 00 00 00 00 00 00",
    "SQR": "SQR's result is always a double: R holds its 8 bytes",
}


def _common(fn, tag, sec):
    return [
        Rule(f"R-{tag}-TYPE", sec,
             f"A string as the argument (a literal or a variable) is error 13 (Type mismatch), and so is assigning "
             f"the result to a string variable: the result is a number.",
             lambda c: fx_by(c, *TYPE_WHYS), lambda c: no_usr(c, 13)),
        Rule(f"R-{tag}-OWNERR", sec, "An argument that fails to compute raises its own error (1/0: error 11).",
             lambda c: fx_by(c, "the argument's own error"), lambda c: no_usr(c, 11)),
        Rule(f"R-{tag}-SYNTAX", sec,
             "No argument, a second argument, no closing parenthesis, or the name without a parenthesis is error 2 "
             "(Syntax error); so are `PRINT " + fn + "` and `" + fn + "(1,2)`, the forms this page quotes.",
             lambda c: fx_by(c, *SYNTAX_WHYS) or (fy(c, "syntax")), lambda c: no_usr(c, 2)),
        Rule(f"R-{tag}-ORDER", sec,
             f"The argument is evaluated before the call's shape is checked, and its type after: {fn}(1/0 (no "
             f"`)`) and {fn}(1/0,2) raise the argument's own error 11, but {fn}(\"A\" (no `)`) and {fn}(\"A\",2) are "
             f"error 2 (Syntax error), not 13 -- the `)` is required before the string is refused.",
             lambda c: fy(c, "prec"), lambda c: no_usr(c, ORDER_ERR[c.why])),
        Rule(f"R-{tag}-NEST", sec,
             f"{fn} nested 16 and 32 deep ({fn}({fn}(...(" + ("1" if fn == "SQR" else "-2.5") + ")...))) gives "
             f"what the rules above give applied that many times, with no error.",
             lambda c: fy(c, "nest"), lambda c: outcome(c, want(c)) and assigned(c)),
        Rule(f"R-{tag}-FORMS", sec,
             f"Spaces before the parenthesis and around the argument are allowed, and a literal's own type is the "
             f"argument's: 2.5 and -2.5 are singles, 7 an integer, 7% / 2.5! / 2.5# what they say, &H8000 the "
             f"integer -32768, -32768 a single (a minus on the single 32768), -0 the integer 0, 1/4 a double; "
             f"{fn} of {fn}(2.25) is {fn} of that result. Each gives what the rules above say for that type and "
             f"value; so does {fn}(-1E38), a single. These types are MEASURED: each literal alone, `R=<literal>` / "
             f"`Q=USR(<literal>)`, gives that type and value on both machines (KMA FY 70-92; the loader refuses a "
             f"run where it does not).", lambda c: fx_by(c, *FORM_WHYS) or fy(c, "value"),
             lambda c: outcome(c, want(c))),
        Rule(f"R-{tag}-ASSIGN", sec,
             "`R=" + fn + "(x)` with R a double stores the result's value -- an integer by its value, a single's "
             "own 4 bytes then four zero bytes, its exponent byte and digit bytes as they are (" + ASSIGN_EG[fn] +
             ") -- and an error stores nothing (R keeps its sentinel). Read in every case that assigns R.",
             lambda c: c.fn == fn and not fy(c, "target"), assigned),
        Rule(f"R-{tag}-TARGET", sec,
             f"Stored in an INTEGER variable, {fn}'s result loses its fraction -- truncated, not rounded (SQR(3) "
             f"stores 1) -- and a value outside -32768..32767 is error 6 (Overflow), the variable unchanged; stored "
             f"in a SINGLE, a single keeps its own 4 bytes (an exponent-0 one its digit bytes too), an integer "
             f"becomes its value, a double is cut to 6 digits (SQR(2): 1.41421). Read back through USR(T%) / "
             f"USR(T!).", lambda c: fy(c, "target"), lambda c: target_is(c, target(c))),
    ]


def rules(fn):
    sec = f"1. {fn}(x)"
    tag = fn
    M = MODELS[fn]

    def typed(*tys):
        return lambda c: mx(c) and c.ty in tys

    def ok(c):
        return outcome(c, want(c))
    if fn == "ABS":
        out = [
            Rule("R-ABS-INT", sec,
                 "An integer gives an integer, its value without the sign (ABS(-5%) is 5%, ABS(32767%) 32767%) -- "
                 "except -32768, whose 32768 is no integer: ABS(-32768%) is the SINGLE 32768 (45 32 76 80).",
                 typed("I"), ok),
            Rule("R-ABS-REAL", sec,
                 "A single gives a single and a double a double: the argument's own bytes with the sign bit "
                 "cleared, nothing else changed (every digit kept, 1E-64 and 9.99999E62 included; -0 READ is "
                 "already 0).", typed("S", "D"), ok),
            Rule("R-ABS-ODD", sec,
                 "Only the sign bit changes even on a non-canonical single: exponent byte 0 or &H80 with digit "
                 "bytes 10 00 00 both give 00 10 00 00.", lambda c: fx_by(c, *ODD_WHYS), ok),
        ]
    elif fn == "SGN":
        out = [
            Rule("R-SGN-ALL", sec,
                 "The result is always an INTEGER: -1 for a negative argument, 0 for zero, 1 for a positive one, in "
                 "every argument type and size (1E-64 is 1, -9.99999E62 -1, -32768% -1).",
                 lambda c: mx(c), ok),
            Rule("R-SGN-ODD", sec,
                 "Only an exponent byte of exactly 0 is a zero: 00 10 00 00 gives 0, but 80 10 00 00 (the sign bit "
                 "set, exponent 0) gives -1.", lambda c: fx_by(c, *ODD_WHYS), ok),
        ]
    elif fn == "FIX":
        out = [
            Rule("R-FIX-INT", sec, "An integer is returned unchanged, as an integer (-32768% included).",
                 typed("I"), ok),
            Rule("R-FIX-WHOLE", sec,
                 "A single or a double of 1 or more in size keeps its type, its sign and its exponent byte; the "
                 "digits after the decimal point become 0 -- toward zero on both sides (FIX(-2.5) is -2, "
                 "FIX(-32768.5!) -32768, FIX(-9999999999999.5#) -9999999999999); a whole number is unchanged.",
                 lambda c: mx(c) and c.ty in "SD" and (c.arg[0] & 0x7F) > 64, ok),
            Rule("R-FIX-SMALL", sec,
                 "Below 1 in size (zero included) the result is a zero of the argument's type whose exponent byte "
                 "is 0 -- the sign dropped -- and whose digit bytes are the argument's, unchanged: FIX(-.5!) is "
                 "00 50 00 00, FIX(1D-64) 00 10 00 00 00 00 00 00. It is 0 to arithmetic, comparison, SGN and STR$ "
                 "(R-FIX-ZEROUSE).", lambda c: mx(c) and c.ty in "SD" and (c.arg[0] & 0x7F) <= 64, ok),
            Rule("R-FIX-ODD", sec,
                 "The same on a non-canonical single: exponent byte 0 or &H80 with digit bytes 10 00 00 both give "
                 "00 10 00 00.", lambda c: fx_by(c, *ODD_WHYS), ok),
        ]
    elif fn == "INT":
        out = [
            Rule("R-INT-INT", sec, "An integer is returned unchanged, as an integer (-32768% included).",
                 typed("I"), ok),
            Rule("R-INT-DOWN", sec,
                 "A single or a double that is zero, positive, or negative and whole gives what FIX gives "
                 "(FIX's page, its first three rules): its own type, the digits after the point 0 -- so "
                 "INT(.5!) is 00 50 00 00, a zero with its digit bytes.",
                 lambda c: mx(c) and c.ty in "SD" and not (c.arg[0] & 0x80 and _frac(argb(c))), ok),
            Rule("R-INT-NEGFRAC", sec,
                 "A negative single or double with digits after the point gives the next whole number DOWN, and "
                 "NOT in the argument's type: between -1 and 0 (-.5, -1E-64) it is the INTEGER -1 (FF FF); from -1 "
                 "down it is a DOUBLE -- INT(-1.5!) is the double -2, INT(-32768.5!) the double -32769, "
                 "INT(-9999999999999.5#) -10000000000000.",
                 lambda c: mx(c) and c.ty in "SD" and c.arg[0] & 0x80 and _frac(argb(c)), ok),
            Rule("R-INT-ODD", sec,
                 "On a non-canonical single: 00 10 00 00 gives 00 10 00 00; 80 10 00 00 (negative, exponent 0) is "
                 "a negative number above -1 and gives the integer -1.", lambda c: fx_by(c, *ODD_WHYS), ok),
        ]
    elif fn == "SQR":
        out = [
            Rule("R-SQR-NEG", sec,
                 "A negative argument is error 5 (Illegal function call), in every type and size (-1%, -32768%, "
                 "-1E-64, -9.9999999999999D62) -- and so is 80 10 00 00 (a single with the sign bit set and "
                 "exponent 0).",
                 lambda c: (mx(c) or fx_by(c, *FX_ARG)) and want(c)[0] == "err", ok),
            Rule("R-SQR-ZERO", sec,
                 "Zero gives a DOUBLE zero; a single zero whose digit bytes are not 0 (exponent byte 0, digits 10 00 "
                 "00) gives a double with those digit bytes kept (00 10 00 00 00 00 00 00).",
                 lambda c: (mx(c) or fx_by(c, *FX_ARG)) and want(c)[0] == "num" and want(c)[2][0] == 0, ok),
            Rule("R-SQR-EXACT", sec,
                 "The result is always a DOUBLE, whatever the argument's type (SQR(4%) is the double 2). When the "
                 "exact root has at most 14 significant digits it is that root, exactly: SQR(2.25) 1.5, "
                 "SQR(1.44!) 1.2, SQR(1E-10) 1E-05, SQR(1D20) 1E+10, SQR(1D-64) 1E-32.",
                 lambda c: (mx(c) or fx_by(c, *FX_ARG)) and want(c)[0] == "num" and want(c)[2][0] != 0, ok),
            Rule("R-SQR-NEAR", sec,
                 f"Otherwise the result is a double within {SQR_BOUND} units of the 14th significant digit of the "
                 "exact root (the unit sized from the exact root's decade) -- NOT always the correctly rounded "
                 "root: SQR(2) is 1.4142135623730 (the exact root is 1.41421356237309505...), SQR(.4!) 2.4 units "
                 "high. The measured errors run from -1.9 units (SQR(1234567890123.4#)) to +2.5 (SQR(.999999!) and "
                 "SQR(999999!)); their rule is the reference's own algorithm, which the printed digits do not "
                 "reveal. A bound, not the reference's digits: any root within it passes, zerobas's correctly "
                 "rounded one included (the Differences and Open below).",
                 lambda c: (mx(c) or fx_by(c, *FX_ARG)) and want(c)[0] == "near", ok),
        ]
    else:
        raise KeyError(fn)
    if fn in ("FIX", "INT"):
        out.append(Rule(f"R-{fn}-ZEROUSE", sec,
                        f"The exponent-0 zero {fn}(.5!) returns (00 50 00 00) is 0 to arithmetic, comparison, SGN and "
                        f"STR$: {fn}(.5!)+1 is 1 (a double), {fn}(.5!)=0 is true, >0 and <0 false"
                        + (" (FIX(-.5!)<0 too: the sign is dropped)" if fn == "FIX" else "") +
                        f", SGN gives 0, STR$ gives \" 0\". {fn}(.5!)*3 is a double whose exponent byte is 0 (the "
                        f"value 0) and whose digit bytes are 30 00 00 00 00 00 00 -- the other operand's (one case).",
                        lambda c: fy(c, "zero"),
                        lambda c: c.e1 == 0 and c.e2 == 0 and (c.vt, c.res) == zero_use(c.why) and assigned(c)))
    if fn == "FIX":
        out.append(Rule("R-FIX-LET", sec,
                        "The assignment, not FIX, decides what a variable keeps: the POKEd single 00 10 00 00 "
                        "assigned to R (`R=N!`) leaves R 00 10 00 00 00 00 00 00, and `N!=FIX(N!)` with N! = .5 "
                        "keeps 00 50 00 00 in the single N! and then in R.",
                        lambda c: c.fn == "LET",
                        lambda c: c.e1 == 0 and c.e2 == 0 and c.vt == 4 and c.res == (
                            bytes([0, 0x10, 0, 0]) if "digit bytes 10" in c.why else bytes([0, 0x50, 0, 0]))
                        and assigned(c)))
    if fn == "SQR":
        out.append(Rule("R-SQR-LET", sec,
                        "A zero root assigned to R is 8 zero bytes whatever R held before: `R=0:R=SQR(0%)` and "
                        "`R=-12345:R=SQR(0!)` both leave R 00 00 00 00 00 00 00 00.",
                        lambda c: c.fn == "LET",
                        lambda c: c.e1 == 0 and c.e2 == 0 and c.vt == 8 and c.res == bytes(8)
                        and c.rbytes == bytes(8)))
    return out + _common(fn, tag, sec)
