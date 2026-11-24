#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""The shared model and rule builders for AND / OR / XOR / EQV / IMP / NOT / MOD's EXECUTABLE RULES (docs/spec-method.md
§3a, docs/keywords/spec-plan.md). The cases come from probes/basic/spec/kops.py's committed run (scratchpad/KOP_run1.out);
each page's module takes its own operator's cases from `load(op)` and its rules from `rules(op)`.

The model: each operand is made an INTEGER first by CINT's rule (toward zero; Overflow, error 6, outside
-32768..32767 -- kconv_model.m_cint, measured on CINT's page); the operation is then on the two 16-bit integers; the
result is an integer. The fixed statements are evaluated by a small precedence parser stating the order the pages
give: `^`; unary minus; `*` `/`; `\\`; MOD; `+` `-`; comparisons; NOT; AND; OR; XOR; EQV; IMP; left to right."""
import os
import re
import sys
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
import kconv_model as C  # noqa: E402
import kmath_model as K  # noqa: E402
import kops  # noqa: E402
from spec_rules import Rule  # noqa: E402

FIELDS = ["e1", "rbytes", "e2", "vt", "res"]
OUTPUTS = {g: FIELDS for g in kops.ORDER}
OUTPUTS_DESC = ("each case's error from `R=<expr>` and from `Q=USR(<expr>)`, R's 8 bytes, the result's type as USR saw "
                "it and the result's own bytes")
MX = ("OI", "OS", "OD")
enc, R_SENT = K.enc, K.R_SENT


class Err(Exception):
    def __init__(self, code):
        self.code = code


def load(op):
    out = {"ref": [], "zb": []}
    for g in kops.ORDER:
        cs = kops.load(g)
        if g in MX:
            check_read(cs, g)
        for who in out:
            out[who] += [c for c in cs[who] if (c.op == op if g in MX else op in c.op.split("/"))]
    return out


def check_read(cs, g):
    """apparatus: every row's X and Y are their DATA texts' values in the group's type (texts with more digits than
    the type holds: the same on every row of that text). Exits otherwise."""
    bad, seen = [], {}
    for who in cs:
        for c in cs[who]:
            for t, b in ((c.x, c.arg1), (c.y, c.arg2)):
                try:
                    ok = b == enc(K.text_value(t), c.ty) + bytes(8 - K.NB[c.ty])
                except AssertionError:
                    ok = seen.setdefault(t, b) == b
                if not ok:
                    bad.append(f"{who} {c.id}")
    if bad:
        sys.exit(f"FAIL: {g}: an operand READ is not its DATA text's value: {', '.join(bad[:8])}")


def to_int(v, how="trunc"):
    """an operand made an integer (`how`: "trunc" CINT's rule; "round" / "floor" / "unsigned" -- controls)"""
    if how == "unsigned" and 32768 <= v < 65536:
        v -= 65536
    if how == "round":
        t = int(abs(v) + Fraction(1, 2)) * (1 if v >= 0 else -1)
    elif how == "floor":
        t = v.numerator // v.denominator
    else:
        t = int(v)
    if not -32768 <= t <= 32767:
        raise Err(6)
    return t


def s16(v):
    v &= 0xFFFF
    return v - 65536 if v & 0x8000 else v


def binop(op, a, b, how="trunc", mod_sign="dividend"):
    if op == "NOT":
        return s16(~to_int(a, how))
    x, y = to_int(a, how), to_int(b, how)
    if op == "AND":
        return s16(x & y)
    if op == "OR":
        return s16(x | y)
    if op == "XOR":
        return s16(x ^ y)
    if op == "EQV":
        return s16(~(x ^ y))
    if op == "IMP":
        return s16(~x | y)
    if op == "MOD":
        if y == 0:
            raise Err(11)
        r = abs(x) % abs(y)
        if mod_sign == "dividend":
            return -r if x < 0 else r
        return x % y                                   # Python's: the divisor's sign (a control)
    raise KeyError(op)


def outcome(fn):
    """("num", 2, bytes) | ("err", code) of a callable computing the integer result"""
    try:
        return "num", 2, enc(fn(), "I")
    except Err as e:
        return "err", e.code


# ---- the fixed statements: a small precedence parser ------------------------------------------------------------
LEVELS = [("IMP",), ("EQV",), ("XOR",), ("OR",), ("AND",)]       # loosest first; NOT, comparisons, + -, MOD ... below
TOK = re.compile(r'\s*(&H[0-9A-F]+|(?:\d+\.?\d*|\.\d+)(?:[ED][-+]?\d+)?[!#%]?|"[^"]*"|AND|OR|XOR|EQV|IMP|NOT|MOD|'
                 r'[-+*/\\^=<>()])')


def literal(t):
    """a literal's value and type, as kmath's LIT rows measured them: a hex literal an integer (two's complement); a
    number with a point or beyond 32767 a single; else an integer; ! # % as written"""
    if t.startswith("&H"):
        return Fraction(s16(int(t[2:], 16))), "I"
    if t[-1] in "!#%":
        return Fraction(K.text_value(t[:-1])), {"!": "S", "#": "D", "%": "I"}[t[-1]]
    v = Fraction(K.text_value(t))
    if "D" in t:
        return v, "D"
    return v, ("I" if "." not in t and "E" not in t and -32768 <= v <= 32767 else "S")


class Parser:
    def __init__(self, text, how="trunc"):
        self.toks, pos = [], 0
        text = text.strip()
        while pos < len(text):
            m = TOK.match(text, pos)
            if not m:
                raise ValueError(text[pos:])
            self.toks.append(m.group(1))
            pos = m.end()
        self.i, self.how = 0, how

    def peek(self):
        return self.toks[self.i] if self.i < len(self.toks) else None

    def take(self):
        t = self.peek()
        self.i += 1
        return t

    def parse(self):
        v = self.level(0)
        if self.peek() is not None:
            raise Err(2)
        return v

    def level(self, n):
        if n == len(LEVELS):
            return self.not_()
        v = self.level(n + 1)
        while self.peek() in LEVELS[n]:
            op = self.take()
            if not getattr(self, "late", False):
                to_int(v, self.how)      # the LEFT operand is made an integer before the right is read
            w = self.level(n + 1)
            v = Fraction(binop(op, v, w, self.how))
        return v

    def not_(self):
        if self.peek() == "NOT":
            self.take()
            return Fraction(binop("NOT", self.not_(), None, self.how))
        return self.cmp()

    def cmp(self):
        v = self.add()
        while self.peek() in ("=", "<", ">"):
            op = self.take()
            w = self.add()
            v = Fraction(-1 if {"=": v == w, "<": v < w, ">": v > w}[op] else 0)
        return v

    def add(self):
        v = self.mod()
        while self.peek() in ("+", "-"):
            op = self.take()
            w = self.mod()
            v = v + w if op == "+" else v - w
        return v

    def mod(self):
        v = self.idiv()
        while self.peek() == "MOD":
            self.take()
            if not getattr(self, "late", False):
                to_int(v, self.how)      # the LEFT operand is made an integer before the right is read
            v = Fraction(binop("MOD", v, self.idiv(), self.how))
        return v

    def idiv(self):
        v = self.mul()
        while self.peek() == "\\":
            self.take()
            w = self.mul()
            x, y = to_int(v), to_int(w)
            if y == 0:
                raise Err(11)
            v = Fraction(abs(x) // abs(y) * (-1 if (x < 0) != (y < 0) else 1))
        return v

    def mul(self):
        v = self.unary()
        while self.peek() in ("*", "/"):
            op = self.take()
            w = self.unary()
            v = v * w if op == "*" else v / w
        return v

    def unary(self):
        t = self.peek()
        if t == "-":
            self.take()
            return -self.unary()
        if t == "NOT":                        # NOT after a unary minus or a binary operator: it takes in a comparison
            return self.not_()
        return self.power()

    def power(self):
        v = self.atom()
        while self.peek() == "^":
            self.take()
            v = v ** int(self.unary())
        return v

    def atom(self):
        t = self.take()
        if t is None or t in ("AND", "OR", "XOR", "EQV", "IMP", "MOD", "*", "/", "\\", "=", "<", ">", ")"):
            raise Err(24 if t is None else 2)
        if t.startswith('"'):
            raise Err(13)
        if t == "(":
            v = self.level(0)
            if self.take() != ")":
                raise Err(2)
            return v
        return literal(t)[0]


def fx_want(c, how="trunc"):
    try:
        v = Parser(c.expr, how).parse()
    except Err as e:
        return ("err", e.code)
    return "num", 2, enc(v, "I")


def want(c, how="trunc", mod_sign="dividend"):
    if c.src in MX:
        a = K.value(c.arg1[:K.NB[c.ty]])
        b = K.value(c.arg2[:K.NB[c.ty]])
        return outcome(lambda: binop(c.op, a, b, how, mod_sign))
    return fx_want(c, how)


def case_ok(c, w):
    if w[0] == "err":
        if c.is_expr:
            return K.error_is(c, w[1])
        return K.no_usr(c, w[1])
    return K.result_is(c, w[1], w[2])


def assigned(c):
    return c.rbytes == (R_SENT if c.vt == 255 else K.as_double(c.vt, c.res))


DESC = {"AND": "a bit is set where it is set in both", "OR": "where it is set in either",
        "XOR": "where it is set in exactly one", "EQV": "where the two agree (NOT (x XOR y))",
        "IMP": "where x's is clear or y's is set ((NOT x) OR y)", "NOT": "NOT x is -x-1: every bit inverted",
        "MOD": "x MOD y is the remainder of x \\ y, with x's sign (-5 MOD 3 is -2, 5 MOD -3 is 2); y = 0 -- after "
               "truncation: .5, .9 -- is error 11 (Division by zero)"}


RANGE_WHYS = ("a right operand below the range", "a double right operand above the range", "a huge right operand",
              "Overflow against Division by zero", "Overflow against Division by zero (a fraction)",
              "Overflow against Division by zero (doubles)", "two bad operands: a range and a string")


def fixed(c):
    return c.src in ("FX", "FY")


def rules(op):
    s1, s2, s3 = "1. The value", "2. Precedence and forms", "3. The result stored"
    R = [
        Rule(f"R-{op}-VALUE", s1, f"Each operand is made an integer by CINT's rule first -- the fraction dropped toward "
             f"zero (2.7 -> 2, -2.7 -> -2, 32767.9 -> 32767, -32768.9 -> -32768) -- and then {DESC[op]}; on 16 bits, "
             "two's complement. The result is an INTEGER in every case.",
             lambda c: c.src in MX and want(c)[0] == "num", lambda c: case_ok(c, want(c))),
        Rule(f"R-{op}-RANGE", s1, "An operand whose truncated value is outside -32768..32767 -- 32768, -32769, 65535, "
             "1E10, 1D20 -- is error 6 (Overflow), whichever side it is on" + (" (NOT has one)" if op == "NOT" else "")
             + (", before any Division by zero" if op == "MOD" else "") + ".",
             lambda c: (c.src in MX and want(c) == ("err", 6)) or (c.src == "FY" and c.why in RANGE_WHYS),
             lambda c: case_ok(c, want(c))),
    ]
    if op == "MOD":
        R.append(Rule("R-MOD-ZERO", s1, "A divisor that truncates to 0 -- 0, .5, -.5, .9, .99999999999999 -- is error 11 "
                      "(Division by zero).", lambda c: c.src in MX and want(c) == ("err", 11),
                      lambda c: case_ok(c, want(c))))
    R += [
        Rule(f"R-{op}-PREC", s2, "In an expression the operators bind in this order, tightest first: `^`; unary minus; "
             "`*` `/`; `\\`; MOD; `+` `-`; the comparisons; NOT; AND; OR; XOR; EQV; IMP -- each group left to right "
             "(XOR and EQV cannot be told apart: every grouping of the two agrees). So NOT 1+2 is NOT 3 (-4), NOT 1<2 "
             "is 0, 7 MOD 4+2 is 5, -7 MOD 4 is -3, 7\\2 MOD 2 is 1; a minus may stand before NOT (-NOT 0 is 1). A "
             "literal's own type counts (&HFFFF the integer -1; 65535 a single: error 6).",
             lambda c: fixed(c) and c.is_expr and c.why not in RANGE_WHYS, lambda c: case_ok(c, want(c))),
        Rule(f"R-{op}-ERRORS", s2, ("A string operand (`NOT \"A\"`) is error 13 (Type mismatch); `NOT` alone is error 24 "
                                     "(Missing operand)." if op == "NOT" else
             "A string on either side is error 13 (Type mismatch) -- unless the left operand is out of range: it is "
             "made an integer as soon as the operator is met, so `70000 AND \"A\"` is error 6; nothing after the "
             "operator is error 24 (Missing operand); an operator or `)` where an operand belongs is error 2."),
             lambda c: fixed(c) and not c.is_expr and c.why not in RANGE_WHYS, lambda c: case_ok(c, want(c))),
        Rule(f"R-{op}-ASSIGN", s3, "`R=x " + op + " y` with R a double stores the integer result by its value; after "
             "an error R keeps its sentinel -12345. Read in every case.", lambda c: True, assigned),
    ]
    return R
