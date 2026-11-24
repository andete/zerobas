#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""The shared model and rule builders for CINT / CSNG / CDBL's EXECUTABLE RULES (docs/spec-method.md §3a,
docs/keywords/spec-plan.md). The cases come from probes/basic/spec/kconv.py's committed run (scratchpad/KCV_run1.out);
each page's module takes its own keyword's cases from `load(fn)` and its rules from `rules(fn)`.

The models work from what the record holds -- the argument's own bytes (2 / 4 / 8) and its type -- and say the
result's type and bytes; R's 8 bytes are that result assigned to a double (kmath_model.as_double). The byte helpers,
the record checks and the rules every one-argument function shares (TYPE, OWNERR, SYNTAX) are kmath_model's."""
import os
import sys
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
import kconv  # noqa: E402
import kmath_model as K  # noqa: E402
from spec_rules import Rule  # noqa: E402

FIELDS = K.FIELDS
OUTPUTS = {g: FIELDS for g in kconv.ORDER}
OUTPUTS_DESC = K.OUTPUTS_DESC
MX = ("CI", "CS", "CD")
enc, value, as_double = K.enc, K.value, K.as_double


def load(fn):
    """this keyword's cases from every group, the reference's and zerobas's, after the READ check"""
    out = {"ref": [], "zb": []}
    for g in kconv.ORDER:
        cs = kconv.load(g)
        if g in MX:
            check_read(cs, g)
        for who in out:
            out[who] += [c for c in cs[who] if c.fn == fn]
    return out


def check_read(cs, g):
    """apparatus: every row's recorded argument is the DATA text's value in the row's type, on both machines (a
    text with more digits than the type holds is checked only to be the same on every row of that text). Exits
    otherwise."""
    bad, seen = [], {}
    for who in cs:
        for c in cs[who]:
            try:
                ok = c.arg == enc(K.text_value(c.text), c.ty) + bytes(8 - K.NB[c.ty])
            except AssertionError:
                ok = seen.setdefault(c.text, c.arg) == c.arg
            if not ok:
                bad.append(f"{who} {c.id}")
    if bad:
        sys.exit(f"FAIL: {g}: the argument READ is not the DATA text's value: {', '.join(bad[:8])}")


# --- the models: (ty, argument bytes) -> ("err", code) | ("num", vt, bytes) ---

def m_cint(ty, b, how="trunc"):
    """toward zero (`how`: "trunc" the page's rule; "round" half away from zero, "floor", "precheck" the range tested on the
    value before truncation -- controls); error 6
    (Overflow) when that is outside -32768..32767. An exponent byte of 0 or &H80 is 0."""
    if ty == "I":
        return "num", 2, b
    if b[0] & 0x7F == 0:
        return "num", 2, enc(0, "I")
    v = value(b)
    if how == "precheck" and not -32768 <= v <= 32767:
        return "err", 6
    if how == "round":
        t = int(abs(v) + Fraction(1, 2)) * (1 if v >= 0 else -1)
    elif how == "floor":
        t = v.numerator // v.denominator
    else:
        t = int(v)                                   # Python's int() of a Fraction truncates toward zero
    if not -32768 <= t <= 32767:
        return "err", 6
    return "num", 2, enc(t, "I")


def m_csng(ty, b, how="half-up", odd="keep"):
    """an integer exactly; a single as its own 4 bytes, whatever they are (`odd`: "keep" the page's rule, "zero" a
    canonical zero -- a control); a double's 14 digits shortened to 6, the magnitude rounded half up on the 7th
    (`how`: "trunc" / "even" -- controls), a carry moving into the exponent; error 6 when it carries past
    exponent byte &H7F (9.999995D62)."""
    if ty == "I":
        return "num", 4, enc(value(b), "S")
    if ty == "S":
        return "num", 4, (bytes(4) if odd == "zero" and b[0] & 0x7F == 0 else b)
    if b[0] & 0x7F == 0:
        return "num", 4, bytes(4) if odd == "zero" else b[:4]
    ds = K._digits(b)
    head, rest = int(ds[:6]), ds[6:]
    if how == "half-up":
        up = rest[0] >= "5"
    elif how == "even":
        up = rest > "5" + "0" * 7 or (rest == "5" + "0" * 7 and head % 2 == 1)
    else:
        up = False
    head += up
    e = b[0] & 0x7F
    if head == 1000000:
        head, e = 100000, e + 1
    if e > 0x7F:
        return "err", 6
    return "num", 4, K._pack((b[0] & 0x80) | e, f"{head:06d}")


def m_cdbl(ty, b, odd="keep"):
    """an integer exactly; a single as its own 4 bytes followed by four zero bytes -- its 6 decimal digits, nothing
    added -- an exponent-0 one too (`odd`: "zero" a canonical zero, a control); a double unchanged"""
    if ty == "I":
        return "num", 8, enc(value(b), "D")
    if ty == "S":
        return "num", 8, (bytes(8) if odd == "zero" and b[0] & 0x7F == 0 else b + bytes(4))
    return "num", 8, b


MODELS = {"CINT": m_cint, "CSNG": m_csng, "CDBL": m_cdbl}

# --- the fixed statements' arguments (the literal types are kmath's, MEASURED there: KMA FY's LIT rows) ---
THIRD_D = enc(Fraction(33333333333333, 10 ** 14), "D")        # 1/3 and 1!/3: a double (R-RND-LIT, KMA FY)
FX_ARG = {k: v for k, v in K.FX_ARG.items() if k not in ("an expression", "nested")}
FX_ARG.update({"an expression (a double)": ("D", THIRD_D), "nested": ("S", enc(Fraction(5, 2), "S"))})
EXTRA = {"32767.5 as a literal": ("S", enc(Fraction(65535, 2), "S")),
         "-32768.5 as a literal": ("S", enc(Fraction(-65537, 2), "S")),
         "1!/3, a double expression": ("D", THIRD_D),
         ".1 stored in a single, widened": ("S", enc(Fraction(1, 10), "S"))}
ORDER_WHYS = ("a string, no closing parenthesis", "a string and an extra argument")
# FY (goldfish pass 1): the inputs of its rows
D0 = bytes([0x00, 0x10]) + bytes(6)
D80 = bytes([0x80, 0x10]) + bytes(6)
FY_ARG = {"a double with exponent byte 0, digit bytes 10 00 ...": ("D", D0),
          "a double with exponent byte 80, digit bytes 10 00 ...": ("D", D80),
          "40000.5 (the page's example)": ("S", enc(Fraction(80001, 2), "S")),
          "the most negative double": ("D", enc(-Fraction(99999999999999, 10 ** 13) * 10 ** 62, "D")),
          "CSNG(1/3) alone": ("D", THIRD_D)}
FY_ORDER = {"the argument's own error, no closing parenthesis": 11,
            "the argument's own error, then an extra argument": 11,
            "Overflow, no closing parenthesis": 2}
LET_D = {"the double 1.2345649999999# stored in a single": "1.2345649999999",
         "the double 1.234565# stored in a single": "1.234565", "the double -1.234565# stored in a single": "-1.234565",
         "the double 9.9999949999999D62 stored in a single": "9.9999949999999E62",
         "the double 9.999995D62 stored in a single": "9.999995E62"}


def fy_want(c, model=None):
    """the predicted outcome of an FY row (whose kinds the rules below name)"""
    m = model or MODELS[c.fn]
    w = c.why
    if w in FY_ORDER:
        return "err", FY_ORDER[w]
    if w in FY_ARG:
        return m(*FY_ARG[w])
    if w == "the result stored in an integer":            # Z%=F(2.7): the result truncated into an integer
        k = MODELS[c.fn]("S", enc(Fraction(27, 10), "S"))
        return "num", 2, enc(int(value(k[2])), "I")
    if w == "the result stored in a single":               # Z!=F(1.234565#): the result made a single as CSNG
        k = MODELS[c.fn]("D", enc(Fraction(1234565, 10 ** 6), "D"))
        ty = {2: "I", 4: "S", 8: "D"}[k[1]]
        return m_csng(ty, k[2])
    if w == "CSNG(1/3) times a single":                   # the product of two singles is a DOUBLE (measured)
        return "num", 8, enc(Fraction(999999, 10 ** 6), "D")
    if w in LET_D:
        k = m_csng("D", enc(K.text_value(LET_D[w]), "D"))
        if k[0] == "err":                                 # Overflow; Z! keeps the previous row's value
            return "keep", m_csng("D", enc(K.text_value("9.9999949999999E62"), "D"))[2]
        return k
    if w == "a single holding 1/3, widened":
        return m_cdbl("S", enc(Fraction(333333, 10 ** 6), "S"))
    if w == "the type of 1!/3 (apparatus)":
        return "num", 8, THIRD_D
    raise KeyError(w)
FORM_WHYS = tuple(w for w in FX_ARG if "exponent byte" not in w)
ODD_WHYS = tuple(w for w in FX_ARG if "exponent byte" in w)


def fx_by(c, *whys):
    return c.src == "FX" and c.why in whys


def want(c, model=None):
    m = model or MODELS[c.fn]
    if c.src == "FY":
        return fy_want(c, model)
    if c.src in MX:
        return m(c.ty, K.argb(c))
    ty, b = FX_ARG.get(c.why) or EXTRA[c.why]
    if c.why == "nested":
        k = MODELS[c.fn](ty, b)
        ty, b = {2: "I", 4: "S", 8: "D"}[k[1]], k[2]
    return m(ty, b)


def outcome(c, w):
    if w[0] == "keep":           # an assignment that overflowed: ERR 6, then R=Z! / USR(Z!) read Z!'s old value
        return c.e1 == 6 and c.e2 == 0 and c.vt == 4 and c.res == w[1]
    if w[0] == "err" and c.src in ("FX", "FY") and c.ustmt is None:
        return K.no_usr(c, w[1])
    return K.error_is(c, w[1]) if w[0] == "err" else K.result_is(c, w[1], w[2])


def assigned(c):
    """R after the case, from the STATEMENT's own outcome (not the USR form's): its sentinel after an error -- except
    the overflowing `Z!=` row, whose next statement `R=Z!` still ran -- else the result widened to a double"""
    if c.src == "FY" and c.why in LET_D and want(c)[0] == "keep":
        return c.rbytes == K.as_double(4, want(c)[1])
    if c.e1 != 0:
        return c.rbytes == K.R_SENT
    return c.res is not None and c.rbytes == K.as_double(c.vt, c.res)


def fy(c, *whys):
    return c.src == "FY" and c.why in whys


def rules(fn):
    tag = fn
    s1, s2, s3 = "1. The value", "2. Forms and errors", "3. The result stored"
    R = []
    if fn == "CINT":
        R += [
            Rule("R-CINT-TRUNC", s1, "The result is an INTEGER: the argument with its fraction dropped, toward zero -- "
                 "CINT(2.5) is 2, CINT(-2.5) -2, CINT(.9) 0, CINT(-.9) 0, CINT(32767.9) 32767, CINT(-32768.9) "
                 "-32768: no rounding. An integer is returned as it is; a single or double whose exponent byte is 0 "
                 "or &H80 is 0.",
                 lambda c: c.src in MX and want(c)[0] == "num", lambda c: outcome(c, want(c))),
            Rule("R-CINT-RANGE", s1, "When the truncated value is outside -32768..32767 -- 32768, -32769, 65535, 1E10, "
                 "9.99999E62, 40000.5 -- it is error 6 (Overflow), from `R=CINT(x)` and from `USR(CINT(x))` alike, "
                 "before anything is assigned.",
                 lambda c: (c.src in MX and want(c)[0] == "err") or fy(c, "40000.5 (the page's example)"),
                 lambda c: outcome(c, want(c)))]
    if fn == "CSNG":
        R += [
            Rule("R-CSNG-ROUND", s1, "The result is a SINGLE. An integer gives its exact value; a single is returned "
                 "unchanged; a double's 14 digits are cut to 6 and the magnitude rounded half up on the 7th digit "
                 "(1.2345649999999 -> 1.23456, 1.234565 -> 1.23457, -1.234565 -> -1.23457, .49999999999999 -> .5), "
                 "a carry moving into the exponent (9.999995 -> 10, 999999.5 -> 1000000).",
                 lambda c: c.src in MX and want(c)[0] == "num", lambda c: outcome(c, want(c))),
            Rule("R-CSNG-OVER", s1, "A double that rounds past the largest exponent -- 9.999995D62, "
                 "9.9999999999999D62 and their negatives -- is error 6 (Overflow), from `R=CSNG(x)` and from "
                 "`USR(CSNG(x))` alike: USR is not reached (its type cell stays 255).",
                 lambda c: (c.src in MX and want(c)[0] == "err") or fy(c, "the most negative double"),
                 lambda c: outcome(c, want(c))),
            Rule("R-CSNG-LET", s1, "Storing a double in a single variable rounds it the same way: `Z!=1.2345649999999#` "
                 "is 1.23456, `Z!=1.234565#` 1.23457, `Z!=-1.234565#` -1.23457, `Z!=9.9999949999999D62` 9.99999E+62; "
                 "`Z!=9.999995D62` is error 6 and Z! keeps the value it had.",
                 lambda c: fy(c, *LET_D), lambda c: outcome(c, want(c))),
            Rule("R-CSNG-USE", s1, "CSNG(1/3) is the single .333333; in arithmetic it counts with its 6 digits: "
                 "CSNG(1/3)*3 and CSNG(1/3)*3! are .999999 -- a DOUBLE, even the product of two singles (the "
                 "operators' region states why).",
                 lambda c: fx_by(c, "the single 1/3 times 3") or fy(c, "CSNG(1/3) alone", "CSNG(1/3) times a single"),
                 lambda c: (K.result_is(c, 8, enc(Fraction(999999, 10 ** 6), "D")) if c.why != "CSNG(1/3) alone"
                            else outcome(c, want(c))))]
    if fn == "CDBL":
        R += [
            Rule("R-CDBL-WIDEN", s1, "The result is a DOUBLE: an integer's exact value; a single's 6 decimal digits "
                 "followed by 8 zeros (CDBL(.499999!) is .49999900000000, CDBL of a single holding .1 is "
                 ".10000000000000 -- nothing invented); a double unchanged.",
                 lambda c: c.src in MX or fx_by(c, "1!/3, a double expression", ".1 stored in a single, widened")
                 or fy(c, "a single holding 1/3, widened", "the type of 1!/3 (apparatus)"),
                 lambda c: outcome(c, want(c)))]
    R += [
        Rule(f"R-{tag}-TYPE", s2, "A string as the argument (a literal or a variable) is error 13 (Type mismatch), and "
             "so is assigning the result to a string variable.",
             lambda c: fx_by(c, *K.TYPE_WHYS), lambda c: K.no_usr(c, 13)),
        Rule(f"R-{tag}-OWNERR", s2, "An argument that fails to compute raises its own error (1/0: error 11).",
             lambda c: fx_by(c, "the argument's own error"), lambda c: K.no_usr(c, 11)),
        Rule(f"R-{tag}-SYNTAX", s2, "No argument, a second argument, no closing parenthesis, or the name without a "
             "parenthesis is error 2 (Syntax error).",
             lambda c: fx_by(c, *K.SYNTAX_WHYS), lambda c: K.no_usr(c, 2)),
        Rule(f"R-{tag}-ORDER", s2, f"The argument is evaluated first -- its own error wins: {fn}(1/0 and {fn}(1/0,2) are "
             f"error 11 --, then the `)` is required, before the type is checked or the conversion done: "
             f"{fn}(\"A\" and {fn}(\"A\",2) are error 2, not 13" + (", and CINT(32768 is 2, not 6." if fn == "CINT"
             else ", and CSNG(9.999995D62 is 2, not 6." if fn == "CSNG" else "."),
             lambda c: fx_by(c, *ORDER_WHYS) or fy(c, *FY_ORDER), lambda c: outcome(c, want(c))
             if c.src == "FY" else K.no_usr(c, 2)),
        Rule(f"R-{tag}-FORMS", s2, f"Spaces before the parenthesis and around the argument are allowed; a literal's own "
             f"type is the argument's (2.5 a single, 7 an integer, &H8000 the integer -32768, -32768 a single, -0 "
             f"the integer 0, 1/3 a double -- kmath's measured literal types); {fn}({fn}(2.5)) is {fn} of that "
             f"result" + (", and the literals 32767.5 and -32768.5 give 32767 and -32768." if fn == "CINT" else "."),
             lambda c: fx_by(c, *FORM_WHYS) or (fn == "CINT" and fx_by(c, *list(EXTRA)[:2])),
             lambda c: outcome(c, want(c))),
        Rule(f"R-{tag}-STORE", s3, f"Stored in a variable, {fn}'s result is converted for it as any number is: "
             f"`Z%={fn}(2.7)` holds 2, `Z!={fn}(1.234565#)` holds " + ("1" if fn == "CINT" else "1.23457") + ".",
             lambda c: fy(c, "the result stored in an integer", "the result stored in a single"),
             lambda c: outcome(c, want(c))),
        Rule(f"R-{tag}-ODD", s2, {
            "CINT": "A single or double whose exponent byte is 0 or &H80 with digit bytes 10 00 ... is 0.",
            "CSNG": "A single whose exponent byte is 0 or &H80 with digit bytes 10 00 00 is returned as it is -- "
                    "00 10 00 00 and 80 10 00 00, a single, not made a clean zero; such a double gives its first 4 "
                    "bytes.",
            "CDBL": "A single whose exponent byte is 0 or &H80 with digit bytes 10 00 00 is widened as any single: "
                    "00 10 00 00 00 00 00 00 and 80 10 00 00 00 00 00 00; such a double is returned as it is."}[fn],
             lambda c: fx_by(c, *ODD_WHYS) or fy(c, *list(FY_ARG)[:2]), lambda c: outcome(c, want(c))),
        Rule(f"R-{tag}-ASSIGN", s3, "`R=" + fn + "(x)` with R a double stores the result as a double: an integer by its "
             "value, a single's 4 bytes then four zero bytes (an exponent-0 one too), a double's 8; after an error "
             "R keeps its sentinel -12345. Read in every case.",
             lambda c: True, assigned),
    ]
    return R
