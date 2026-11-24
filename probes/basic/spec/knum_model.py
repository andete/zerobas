#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""The shared model and rule builders for STR$ / VAL / HEX$ / OCT$ / BIN$'s EXECUTABLE RULES (docs/spec-method.md
§3a, docs/keywords/spec-plan.md). The cases come from probes/basic/spec/knum.py's committed run
(scratchpad/KNM_run1.out); each page's module takes its own keyword's cases from `load(fn)` and its rules from
`rules(fn)`.

The models work from what the record holds: a numeric argument's own bytes (ramrec.number), a VAL source's own
bytes. Every string result is compared byte for byte, every numeric result as R's 8 bytes."""
import math
import os
import re
import sys
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
import knum  # noqa: E402
from spec_rules import Rule  # noqa: E402

FIELDS = ["e", "rl", "rb", "rsum", "rbytes", "sl", "ss"]
OUTPUTS = {g: FIELDS for g in knum.ORDER}
OUTPUTS_DESC = ("each case's error, the string result's length, first 24 bytes and byte sum, the numeric result's "
                "8 bytes, the source string's length and sum")
SENT_S = bytes([250])                                   # R$ before every case
SENT_N = bytes([0xC5, 0x12, 0x34, 0x50, 0, 0, 0, 0])    # R = -12345 (a double) before every case
S, T = knum.FX_S, knum.FX_T                             # the fixed statements' S$ and T$
WS = b" \t\n"                                           # what VAL skips inside a number (measured: KNM VL)

GROUPS_OF = {"STR$": ["SN"], "VAL": ["VL"], "HEX$": ["RX"], "OCT$": ["RX"], "BIN$": ["RX"]}


def load(fn):
    """this keyword's cases: its matrix group's and the fixed statements', the reference's and zerobas's in order"""
    out = {"ref": [], "zb": []}
    for g in GROUPS_OF[fn] + ["FX"]:
        cs = knum.load(g)
        for who in out:
            out[who] += [c for c in cs[who] if c.fn == fn]
    return out


# --- what a case recorded ---

def _rstr_is(c, b):
    return c.rl == len(b) and c.rb == (b[:24] + bytes(24))[:24] and c.rsum == sum(b) & 0xFFFF


def str_result(c, b):
    """no error, R$ is exactly the string b, R untouched"""
    return c.e == 0 and _rstr_is(c, b) and c.rbytes == SENT_N


def num_result(c, b8):
    """no error, R's 8 bytes are b8, R$ untouched"""
    return c.e == 0 and c.rbytes == b8 and _rstr_is(c, SENT_S)


def error_is(c, code):
    """the case raised `code` and assigned nothing: R$ and R still hold their sentinels"""
    return c.e == code and _rstr_is(c, SENT_S) and c.rbytes == SENT_N


def outcome(c, model):
    """model(c) -> ("err", code) | ("str", bytes) | ("num", 8 bytes)"""
    k, v = model(c)
    return error_is(c, v) if k == "err" else str_result(c, v) if k == "str" else num_result(c, v)


def kept(c):
    """S$ is left as it was"""
    return (c.sl, c.ss) == (len(c.s), sum(c.s) & 0xFFFF)


def encode(v):
    """a value as a double variable's 8 bytes (exactly representable in 14 digits)"""
    if v == 0:
        return bytes(8)
    neg = v < 0
    v = abs(Fraction(v))
    e = 0
    while v >= 1:
        v /= 10
        e += 1
    while v < Fraction(1, 10):
        v *= 10
        e -= 1
    m = v * 10 ** 14
    assert m.denominator == 1, "not 14 digits"
    return _pack(neg, 64 + e, str(m.numerator).rjust(14, "0"))


def _pack(neg, eb, digits14):
    return bytes([(0x80 if neg else 0) | eb]) + bytes(int(digits14[k:k + 2], 16) for k in range(0, 14, 2))


# --- STR$: PRINT's format ---

def _digits(c):
    """(negative, significant digits, E) of a single / double argument: the value is .d1d2... x 10^E; None for 0"""
    b = c.arg[:knum.TYPES[c.ty][1]]
    if b[0] & 0x7F == 0:
        return None
    ds = "".join(f"{x:02x}" for x in b[1:]).rstrip("0")
    return bool(b[0] & 0x80), ds, (b[0] & 0x7F) - 64


def fmt(c, lo=-1, hi=14, sep="E", trail=""):
    """STR$ of the case's argument; lo / hi bound the decimal point positions written in full (a control alters
    them, the exponent letter, or adds PRINT's trailing space)"""
    if c.ty == "I":
        v = knum.argval(c)
        return ((b"-" if v < 0 else b" ") + str(abs(v)).encode() + trail.encode())
    d = _digits(c)
    if d is None:
        return b" 0" + trail.encode()
    neg, ds, e = d
    if lo <= e <= hi:
        if e <= 0:
            body = "." + "0" * -e + ds
        elif len(ds) <= e:
            body = ds + "0" * (e - len(ds))
        else:
            body = ds[:e] + "." + ds[e:]
    else:
        x = e - 1
        body = ds[0] + ("." + ds[1:] if len(ds) > 1 else "") + sep + ("-" if x < 0 else "+") + f"{abs(x):02d}"
    return (b"-" if neg else b" ") + body.encode() + trail.encode()


def m_str(c):
    return "str", fmt(c)


def str_e(c):
    """the decimal point position E of a non-zero single / double argument (None otherwise)"""
    d = _digits(c) if c.ty in ("S", "D") else None
    return None if d is None else d[2]


# --- HEX$ / OCT$ / BIN$ ---

BASES = {"HEX$": 16, "OCT$": 8, "BIN$": 2}


def radix_arg(v, high="wrap"):
    """(error, the 16-bit pattern): error 6 when v truncated toward zero is below -32768, or v is 65536 or more;
    below 32768 the pattern is v truncated toward zero, from 32768 up it is v - 65536 truncated toward zero
    (`high`: "wrap" the page's rule; "trunc" / "round" deliberately altered rules, for the controls)"""
    if math.trunc(v) < -32768 or v >= 65536:
        return 6, None
    if v < 32768 or high == "trunc":
        t = math.trunc(v)
    elif high == "round":
        t = math.floor(v + Fraction(1, 2))
    else:
        t = math.trunc(v - 65536)
    return 0, t & 0xFFFF


def digits_in(u, base):
    s = ""
    while True:
        s = "0123456789ABCDEF"[u % base] + s
        u //= base
        if not u:
            return s.encode()


def m_radix(c, high="wrap"):
    e, u = radix_arg(knum.argval(c), high)
    return ("err", e) if e else ("str", digits_in(u, BASES[c.fn]))


# --- VAL ---

def m_val_bytes(s, ws=WS, amp_gap=True, wrap=True, keep_digits=True, nd=14, half="up"):
    """VAL(s) -> ("err", code) | ("num", 8 bytes). The keyword arguments are the page's rule; the controls alter
    them: `ws` the characters skipped, `amp_gap` whitespace allowed between & and its letter, `wrap` the exponent
    kept in 8 bits (else any exponent past the range overflows), `keep_digits` the digits kept behind an exponent of
    0, `nd` / `half` the rounding."""
    i, n = 0, len(s)
    while i < n and s[i] in ws:
        i += 1
    if i < n and s[i] == ord("&"):
        i += 1
        if amp_gap:
            while i < n and s[i] in ws:
                i += 1
        L = chr(s[i]).upper() if i < n else ""
        if L not in ("H", "O", "B"):
            return "err", 2
        base = {"H": 16, "O": 8, "B": 2}[L]
        v = 0
        for x in s[i + 1:]:
            d = int(chr(x), 16) if chr(x) in "0123456789abcdefABCDEF" else 99
            if d >= base:
                break
            v = v * base + d
            if v > 0xFFFF:
                return "err", 6
        return "num", encode(v - 65536 if v >= 32768 else v)
    neg = False
    if i < n and s[i] in b"+-":
        neg = s[i] == ord("-")
        i += 1
    t = bytes(x for x in s[i:] if x not in ws)
    j, m = 0, len(t)
    ds, e = [], 0

    def dig(k):
        return k < m and 48 <= t[k] <= 57
    while dig(j):
        d = t[j] - 48
        if ds or d:
            ds.append(d)
            e += 1
        j += 1
    if j < m and t[j] == ord("."):
        j += 1
        while dig(j):
            d = t[j] - 48
            if ds or d:
                ds.append(d)
            else:
                e -= 1
            j += 1
    suffix = None
    if j < m and t[j] in b"%!#":
        suffix = t[j]
    elif j < m and t[j] in b"EeDd":
        j += 1
        es = 1
        if j < m and t[j] in b"+-":
            es = -1 if t[j] == ord("-") else 1
            j += 1
        x = 0
        while dig(j):
            x = x * 10 + t[j] - 48
            j += 1
        e += es * x
        if j < m and t[j] in b"%!#":
            suffix = t[j]
    if not ds:
        return "num", bytes(8)
    if suffix == ord("%"):
        v = math.trunc(Fraction(int("".join(map(str, ds))), 10 ** len(ds)) * Fraction(10) ** e)
        v = -v if neg else v
        return ("err", 6) if v < -32768 or v > 32767 else ("num", encode(v))
    if suffix == ord("!"):
        nd = 6
    if len(ds) > nd:
        up = ds[nd] > 5 or (ds[nd] == 5 and (half == "up" or any(ds[nd + 1:]) or ds[nd - 1] % 2))
        if half == "trunc":
            up = False
        ds = ds[:nd]
        if up:
            k = nd - 1
            while k >= 0 and ds[k] == 9:
                ds[k] = 0
                k -= 1
            if k < 0:
                ds = [1] + ds[:-1]
                e += 1
            else:
                ds[k] += 1
    eb = 64 + e
    if wrap:
        eb %= 256
    if eb & 0x80 or eb < 0 or eb > 127:
        return "err", 6
    digits = "".join(map(str, ds)).ljust(14, "0")[:14]
    if eb == 0 and not keep_digits:
        return "num", bytes(8)
    return "num", _pack(neg, eb, digits)


def m_val(c, **kw):
    return m_val_bytes(c.s, **kw)


def vclass(s):
    """which VAL rule speaks about the source s (one each)"""
    k, b = m_val_bytes(s)
    if s.lstrip(WS).lstrip(b"+-")[:1] == b"&":
        return "PREFIX"
    if any(x in s for x in b"%!#"):
        return "SUFFIX"
    if (k == "err" and b == 6) or (k == "num" and b[0] & 0x7F == 0 and any(b[1:])) or \
            m_val_bytes(s, wrap=False) != (k, b):
        return "RANGE"
    if k == "num" and b == bytes(8):
        return "NONE"
    t = bytes(x for x in s if x not in WS)
    if re.fullmatch(rb"[+-]?(\d+\.?\d*|\.\d+)([EeDd][+-]?\d+)?", t):
        return "SPACE" if t != s else "NUMBER"
    return "STOP"


# --- the fixed statements: what each one gives (S$ = "12345", T$ = "6.5") ---

def _s(b):
    return "str", b


FX_WANT = {
    "R$=STR$(5)": _s(b" 5"), "R$=STR$(-5)": _s(b"-5"), "R$=STR$ (5)": _s(b" 5"), "R$=STR$( 5 )": _s(b" 5"),
    "R$=STR$(5 )": _s(b" 5"), "R$=STR$( 5)": _s(b" 5"), "R$=STR$(&HFF)": _s(b" 255"), "R$=STR$(&HFFFF)": _s(b"-1"),
    "R$=STR$(5%)": _s(b" 5"), "R$=STR$(1.5#)": _s(b" 1.5"), "R$=STR$(-0)": _s(b" 0"), "R$=STR$(1/4)": _s(b" .25"),
    'R$=STR$(5)+"X"': _s(b" 5X"),
    "R=VAL(S$)": ("num", encode(12345)), "R=VAL (S$)": ("num", encode(12345)),
    "R=VAL( S$ )": ("num", encode(12345)), "R=VAL(S$ )": ("num", encode(12345)),
    "R=VAL( S$)": ("num", encode(12345)), 'R=VAL("12")': ("num", encode(12)), 'R=VAL("12" )': ("num", encode(12)),
    'R=VAL("12")+1': ("num", encode(13)), "R=VAL(LEFT$(S$,2))": ("num", encode(12)),
    "R=VAL(MID$(S$,2,2))": ("num", encode(23)), "R=VAL(RIGHT$(S$,2))": ("num", encode(45)),
    "R=VAL(S$+T$)": ("num", encode(Fraction("123456.5"))), "R=VAL(T$+S$)": ("num", encode(Fraction("6.512345"))),
    'R=VAL("&HFF")': ("num", encode(255)), 'R=VAL("")': ("num", bytes(8)),
}
for _f, _d in (("HEX$", b"FF"), ("OCT$", b"377"), ("BIN$", b"11111111")):
    for _st in ("(255)", " (255)", "( 255 )", "(255 )", "(&HFF)", "(255%)"):
        FX_WANT[f"R$={_f}{_st}"] = _s(_d)


def fx_want(c):
    return FX_WANT[c.stmt]


def fx_by(c, *whys):
    return c.src == "FX" and c.why in whys


def _common(tag, sec, whys_type, whys_own, whys_syntax, whys_forms, type_text, own_text, syntax_text, forms_text,
            keep=True):
    out = [
        Rule(f"R-{tag}-TYPE", sec, type_text, lambda c: fx_by(c, *whys_type), lambda c: error_is(c, 13)),
        Rule(f"R-{tag}-OWNERR", sec, own_text, lambda c: fx_by(c, *whys_own), lambda c: error_is(c, 11)),
        Rule(f"R-{tag}-SYNTAX", sec, syntax_text, lambda c: fx_by(c, *whys_syntax), lambda c: error_is(c, 2)),
        Rule(f"R-{tag}-FORMS", sec, forms_text, lambda c: fx_by(c, *whys_forms), lambda c: outcome(c, fx_want)),
    ]
    if keep:
        out.append(Rule(f"R-{tag}-KEEP", sec,
                        "The string variable S$ is left as it was, in every case, error or not (read back after "
                        "every case).", lambda c: True, kept))
    return out


SYNTAX_WHYS = ("no argument", "an extra argument", "no closing parenthesis", "no parenthesis")
SYNTAX_TEXT = ("No argument, a second argument, no closing parenthesis, or the name without a parenthesis is "
               "error 2 (Syntax error).")
OWN_TEXT = "An argument that fails to compute raises its own error (1/0: error 11)."


def rules(fn):
    if fn == "STR$":
        sec = "1. STR$(n)"
        M = lambda c: c.src == "SN"  # noqa: E731
        return [
            Rule("R-STR-INT", sec,
                 "An integer (a % variable) is written as its decimal digits, with \"-\" in front of a negative "
                 "number and a space in front of any other; nothing after the last digit (0, 9, 10, 32767, -32768).",
                 lambda c: M(c) and c.ty == "I", lambda c: outcome(c, m_str)),
            Rule("R-STR-FIXED", sec,
                 "A single or double n = .d1d2...dk x 10^E (k its significant digits, trailing zeros dropped) with "
                 "E from -1 to 14 is written in full: a space or \"-\", then the digits with the decimal point in "
                 "place -- zeros added up to the point when the number is whole (1E13! is \" 10000000000000\", 14 "
                 "digits, though a single holds 6), no 0 before a leading point (\" .5\", \" .0123456\"), no "
                 "point after a whole number. Every stored digit is written: 6 at most for a single, 14 for a "
                 "double.", lambda c: M(c) and str_e(c) is not None and -1 <= str_e(c) <= 14,
                 lambda c: outcome(c, m_str)),
            Rule("R-STR-EXP", sec,
                 "Outside that range (n below .01 or 10^14 and up, in size) it is written d1.d2...dkE+xx or E-xx: "
                 "one digit before the point, the point only when more digits follow, then E -- for a double "
                 "too, never D -- a sign and two digits (\" 1E-03\", \" 1.23456E-03\", \" 1E+14\", "
                 "\" 9.9999999999999E+62\", \" 1E-64\").",
                 lambda c: M(c) and str_e(c) is not None and not -1 <= str_e(c) <= 14,
                 lambda c: outcome(c, m_str)),
            Rule("R-STR-ZERO", sec,
                 "Zero is \" 0\" in every type -- also a single whose exponent byte is 0 but whose digit bytes are "
                 "not (READ left 1E-65 that way on the reference: KNM SN S 1E-65).",
                 lambda c: M(c) and c.ty in ("S", "D") and str_e(c) is None, lambda c: outcome(c, m_str)),
        ] + _common("STR", sec, ("a string as the argument", "a string variable as the argument",
                                 "the result is a string"), ("the argument's own error",), SYNTAX_WHYS,
                    ("plain", "a negative number", "a space before the parenthesis", "spaces around the argument",
                     "a space before the closing parenthesis", "a space after the parenthesis", "a hex argument",
                     "a hex argument past 32767", "an integer literal", "a double literal", "minus zero",
                     "an expression", "the result in a concatenation"),
                    "A string as the argument is error 13 (Type mismatch), and so is assigning the result to a "
                    "numeric variable: the result is a string.", OWN_TEXT, SYNTAX_TEXT,
                    "Spaces before the parenthesis, after it and before the closing parenthesis are allowed; &HFF "
                    "is \" 255\" and &HFFFF \"-1\" (a hex literal is a signed integer); -0 is \" 0\"; 1/4 is "
                    "\" .25\"; the result is an ordinary string (STR$(5)+\"X\" is \" 5X\").")
    if fn == "VAL":
        sec = "1. VAL(a$)"

        def V(*cls):
            return lambda c: c.src == "VL" and vclass(c.s) in cls
        return [
            Rule("R-VAL-NUMBER", sec,
                 "A string that starts with a decimal number: an optional + or -, digits, an optional point and more "
                 "digits, an optional exponent (E, D, e or d, an optional sign, digits). The value keeps 14 "
                 "significant digits, rounded half up at the 15th (\"123456789012345\" is 1.2345678901235E+14, "
                 "\"999999999999995\" 1E+15, \"12345678901234.5\" 12345678901235); 7 to 14 digits are kept even "
                 "with an E exponent (\"1.23456789E3\" is 1234.56789). Leading zeros do not count.",
                 V("NUMBER"), lambda c: outcome(c, m_val)),
            Rule("R-VAL-SPACE", sec,
                 "Spaces, TAB (CHR$(9)) and LF (CHR$(10)) are skipped everywhere in a decimal number: before it, "
                 "between the sign and the digits, between digits, around the point, inside the exponent "
                 "(\"1 2\" and \"1\"+CHR$(9)+\"2\" are 12, \" - 12\" is -12, \"1E- 3\" .001; 254 spaces then 7 "
                 "is 7).", V("SPACE"), lambda c: outcome(c, m_val)),
            Rule("R-VAL-STOP", sec,
                 "The number ends at the first character that cannot continue it, and what was read so far is "
                 "the value: \"12ABC\" 12, \"1.2.3\" 1.2, \"1,000\" 1, \"2+3\" 2, \"1E3E3\" 1000, \"1.5E1.5\" 15, "
                 "\"1E\" and \"1E+\" 1, \"1\"+CHR$(0)+\"2\" 1, \"1\"+CHR$(255)+\"2\" 1.",
                 V("STOP"), lambda c: outcome(c, m_val)),
            Rule("R-VAL-NONE", sec,
                 "No number at the start is 0, not an error: \"\", spaces only, \"ABC\", \".\", \"-\", \"+\", "
                 "\"E3\", \".E3\", \"$12\", and a second sign (\"--1\", \"+-1\", \"-+1\"). Zero is stored as 8 "
                 "zero bytes, \"-0\" included. Control characters other than TAB and LF are not skipped: CR, CHR$(0), "
                 "CHR$(11), CHR$(12), CHR$(28), CHR$(31), CHR$(127) and CHR$(160) before the digits give 0.",
                 V("NONE"), lambda c: outcome(c, m_val)),
            Rule("R-VAL-SUFFIX", sec,
                 "A type mark after the digits or the exponent ends the number and sets its precision: ! rounds "
                 "to 6 digits (\"1234567!\" is 1234570), # changes nothing, % cuts the value to a whole number "
                 "(\"1.5%\" is 1) and is error 6 (Overflow) past 32767 (\"40000%\"). Nothing after the mark is "
                 "read (\"12%3\" is 12, \"1.5!E3\" 1.5).", V("SUFFIX"), lambda c: outcome(c, m_val)),
            Rule("R-VAL-RANGE", sec,
                 "The decimal exponent is kept in 8 bits, 64 + E for .d1d2... x 10^E: from 1 to 127 the number "
                 "is in range; when it reaches 128 to 255 the result is error 6 (Overflow) -- \"1E63\", \"1E99\", "
                 "64 to 129 digits, and also \"1E-66\" and a point followed by 70 zeros, which wrap below 0 to 255 "
                 "and down; at exactly 0 (\"1E-65\", \"5E-65\") the value is 0 but its digits stay in the "
                 "mantissa bytes (00 10 00 ... for \"1E-65\"); and past 255 it wraps back into range: 200 ones are "
                 "1.1111111111111E-57, 255 ones .011111111111111.", V("RANGE"), lambda c: outcome(c, m_val)),
            Rule("R-VAL-PREFIX", sec,
                 "&H, &O and &B (either case, and with spaces, TABs or LFs allowed between & and the letter, never "
                 "after it) read hexadecimal, octal or binary digits up to the first that does not belong; the "
                 "value is a 16-bit pattern taken as signed (\"&HFFFF\" is -1, \"&H8000\" -32768, \"&H0000FFFF\" "
                 "-1); a pattern past 16 bits is error 6 (Overflow); no digit is 0 (\"&HZZ\", \"&O9\", \"&H "
                 "10\"); & followed by any other letter, a digit or nothing is error 2 (Syntax error). A sign "
                 "before & is not a number (\"-&H10\" is 0).", V("PREFIX"), lambda c: outcome(c, m_val)),
            Rule("R-VAL-END", sec,
                 "VAL reads its own string only: in the cases where the byte that follows a$ in memory is a digit, "
                 "a point or a letter that could continue the number, the result is still a$'s own.",
                 lambda c: c.src == "VL" and c.s and c.arg[0] in b"0123456789.EeDdHh",
                 lambda c: outcome(c, m_val)),
        ] + _common("VAL", sec, ("a number as the argument", "the result is a number"),
                    ("the argument's own error",), SYNTAX_WHYS,
                    ("plain", "a space before the parenthesis", "spaces around the argument",
                     "a space before the closing parenthesis", "a space after the parenthesis",
                     "a literal (in the program text)", "a space before the closing parenthesis, a literal",
                     "the result in arithmetic", "a LEFT$ of a longer string", "a MID$ of a longer string",
                     "a RIGHT$ of a longer string", "a concatenation", "a concatenation, the other way",
                     "a hex literal string", "an empty literal"),
                    "A number as the argument is error 13 (Type mismatch), and so is assigning the result to a "
                    "string variable: the result is a number.", OWN_TEXT, SYNTAX_TEXT,
                    "Spaces before the parenthesis, after it and before the closing parenthesis are allowed; the "
                    "argument may be a literal in the program text, a LEFT$ / MID$ / RIGHT$ of a longer string "
                    "(VAL(LEFT$(\"12345\",2)) is 12: the rest of the longer string is not read) or a "
                    "concatenation (\"12345\"+\"6.5\" is 123456.5, \"6.5\"+\"12345\" 6.512345).") + [
            Rule("R-VAL-LITERAL", sec,
                 "Inside a literal string the rules are the same: VAL(\"1E99\") is error 6, VAL(\"&\") error 2.",
                 lambda c: fx_by(c, "an overflowing literal string", "a bare & in a literal string"),
                 lambda c: error_is(c, 6 if "1E99" in c.stmt else 2)),
        ]
    if fn in BASES:
        tag = fn[:3]
        sec = f"1. {fn}(n)"
        M = lambda c: c.src == "RX"  # noqa: E731
        base_word = {"HEX$": "hexadecimal, capitals", "OCT$": "octal", "BIN$": "binary"}[fn]
        ex = {"HEX$": ('"FFFF"', '"8001"', '"FFFF"'), "OCT$": ('"177777"', '"100001"', '"177777"'),
              "BIN$": ("sixteen 1s", '"1000000000000001"', "sixteen 1s")}[fn]
        return [
            Rule(f"R-{tag}-LOW", sec,
                 f"From -32768 to below 32768 the number is truncated toward zero and its 16-bit pattern (two's "
                 f"complement for a negative number) is written in {base_word}, without leading zeros, \"0\" for 0: "
                 f"-1 and -1.5 give {ex[0]}, -.9 and .9 give \"0\", 32767.9 the pattern of 32767. -32768.5 is "
                 f"-32768: the truncation comes before the range test.",
                 lambda c: M(c) and c.fn == fn and radix_arg(knum.argval(c))[0] == 0 and knum.argval(c) < 32768,
                 lambda c: outcome(c, m_radix)),
            Rule(f"R-{tag}-HIGH", sec,
                 f"From 32768 to below 65536 the pattern is that of n - 65536, truncated toward zero -- so a "
                 f"fraction there moves UP: 32768.5 gives {ex[1]}, 65534.5 gives {ex[2]}, and 65535.5 and "
                 f"65535.9 give \"0\" (65536 wrapped to 16 bits), not an error.",
                 lambda c: M(c) and c.fn == fn and radix_arg(knum.argval(c))[0] == 0 and knum.argval(c) >= 32768,
                 lambda c: outcome(c, m_radix)),
            Rule(f"R-{tag}-RANGE", sec,
                 "Error 6 (Overflow), nothing assigned, when the number truncated toward zero is below -32768 "
                 "(-32769, -65536, -1E10) or the number is 65536 or more (65536, 70000, 1E10) -- in every type.",
                 lambda c: M(c) and c.fn == fn and radix_arg(knum.argval(c))[0] != 0,
                 lambda c: outcome(c, m_radix)),
        ] + _common(tag, sec, ("a string as the argument", "a string variable as the argument",
                               "the result is a string"), ("the argument's own error",), SYNTAX_WHYS,
                    ("plain", "a space before the parenthesis", "spaces around the argument",
                     "a space before the closing parenthesis", "a hex argument", "an integer literal"),
                    "A string as the argument is error 13 (Type mismatch), and so is assigning the result to a "
                    "numeric variable: the result is a string.", OWN_TEXT, SYNTAX_TEXT,
                    "Spaces before the parenthesis, around the argument and before the closing parenthesis are "
                    "allowed; a hex or integer literal is a number like any other (255, &HFF and 255% give the "
                    "same).") + [
            Rule(f"R-{tag}-LITERAL", sec, f"A literal out of range is the same error 6: {fn}(70000).",
                 lambda c: fx_by(c, "an overflowing literal"), lambda c: error_is(c, 6)),
        ]
    raise KeyError(fn)
