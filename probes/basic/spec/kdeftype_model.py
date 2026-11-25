#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""The model and rule builders for DEFINT / DEFSNG / DEFDBL / DEFSTR's EXECUTABLE RULES (docs/spec-method.md §3a,
docs/keywords/spec-plan.md region 6). The cases come from probes/basic/spec/kdeftype.py's committed run
(scratchpad/KDT_run1.out).

THE MODEL IS AN INTERPRETER, NOT A TABLE (the flow region's goldfish pass, 2026-11-25: a per-case table of records
checks no sentence). It runs each case's own statements -- the DEF list parse, the type of a name, an assignment's
conversion -- and predicts the record from that; a rival rule (`alt`, kdeftype_controls.py) changes ONE law of the
interpreter and must be false on some case."""
import os
import re
import sys
from fractions import Fraction as Fr

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
import kdeftype  # noqa: E402
from spec_rules import Rule  # noqa: E402

FIELDS = ["e", "f", "t", "v"]
OUTPUTS = {"FX": FIELDS}
OUTPUTS_DESC = ("each case's first and last error, the type byte before each named variable (PEEK(VARPTR(v)-3); "
                "$EE: VARPTR refused the name) and the number the case left in WV#")
CODE = {"%": 2, "$": 3, "!": 4, "#": 8}
NOVAR = 0xEE
KWS = {"DEFINT": "%", "DEFSNG": "!", "DEFDBL": "#", "DEFSTR": "$"}


class Err(Exception):
    def __init__(self, n):
        self.n = n


def _round(x, digits):
    """x to `digits` significant decimal digits, half away from zero (BCD); 0 stays 0"""
    if x == 0:
        return Fr(0)
    s, a = (-1 if x < 0 else 1), abs(x)
    e = 0
    while a >= 1:
        a /= 10
        e += 1
    while a < Fr(1, 10):
        a *= 10
        e -= 1
    m = a * 10 ** digits
    q = int(m) + (1 if m - int(m) >= Fr(1, 2) else 0)
    return s * Fr(q, 10 ** digits) * Fr(10) ** e


class Machine:
    def __init__(self, alt, data):
        self.alt = alt
        self.data = list(data)
        self.clear()

    def clear(self):
        self.deftbl = {chr(c): ("!" if "default-single" in self.alt else "#") for c in range(65, 91)}
        self.vars = {}
        self.arrays = {}

    # -- names and types --------------------------------------------------------------------------------------------
    def typ(self, name):
        """the type of a name as written: its suffix, else the DEF table's entry for its first letter AT THIS USE"""
        if name[-1] in CODE:
            return name[-1]
        if "create-time" in self.alt:
            made = [t for (b, t) in self.vars if b == name[:2]]
            if made:
                return made[0]
        return self.deftbl[name[0]]

    def key(self, name):
        base = name.rstrip("%$!#")[:2]
        if "defstr-separate" in self.alt and name[-1] not in CODE and self.typ(name) == "$":
            base += "_"                  # the rival: an unsuffixed DEFSTR name is not the `$` variable
        return base, self.typ(name)

    def store(self, t, val):
        """an assignment's conversion to the target's type"""
        kind, x = val
        if t == "$":
            if kind != "s":
                raise Err(13)
            return val
        if kind == "s":
            raise Err(13)
        if t == "%":
            q = (int(x) if "int-floor" not in self.alt else (x.numerator // x.denominator))
            if "int-round" in self.alt:
                q = int(x + Fr(1, 2)) if x >= 0 else -int(-x + Fr(1, 2))
            if not -32768 <= q <= 32767:
                raise Err(6)
            return ("n", Fr(q))
        y = _round(x, 6 if t == "!" else 14) if "sng-truncate" not in self.alt or t != "!" else \
            Fr(int(x * 10 ** 5 * 10) if x else 0, 10 ** 6)
        if abs(y) >= Fr(10) ** 63:
            raise Err(6)
        return ("n", y)

    # -- expressions ------------------------------------------------------------------------------------------------
    def expr(self, s):
        toks = re.findall(r'"[^"]*"|\d*\.?\d+(?:E[+-]?\d+)?|[A-Z][A-Z0-9]*[$%!#]?|[-+*/()]', s)
        self.tk, self.i = toks, 0
        v = self.sum()
        assert self.i == len(toks), (s, toks)
        return v

    def sum(self):
        v = self.prod()
        while self.i < len(self.tk) and self.tk[self.i] in "+-":
            op = self.tk[self.i]
            self.i += 1
            w = self.prod()
            v = ("n", v[1] + w[1] if op == "+" else v[1] - w[1])
        return v

    def prod(self):
        v = self.atom()
        while self.i < len(self.tk) and self.tk[self.i] in "*/":
            op = self.tk[self.i]
            self.i += 1
            w = self.atom()
            v = ("n", _round(v[1] * w[1] if op == "*" else v[1] / w[1], 14))
        return v

    def atom(self):
        t = self.tk[self.i]
        self.i += 1
        if t == "-":
            return ("n", -self.atom()[1])
        if t.startswith('"'):
            return ("s", t[1:-1])
        if t[0].isdigit() or t[0] == ".":
            return ("n", Fr(t))
        if t in ("LEN", "ASC", "STR$"):
            self.i += 1
            a = self.sum()
            self.i += 1
            if t == "LEN":
                return ("n", Fr(len(a[1])))
            if t == "ASC":
                return ("n", Fr(ord(a[1][0])))
            return ("s", (" " if a[1] >= 0 else "") + str(a[1]))
        if self.i < len(self.tk) and self.tk[self.i] == "(":
            self.i += 1
            k = int(self.sum()[1])
            self.i += 1
            arr = self.array(t)
            return arr[k]
        k = self.key(t)
        if k in self.vars:
            return self.vars[k]
        return ("s", "") if k[1] == "$" else ("n", Fr(0))    # reading does not create

    def array(self, name):
        k = self.key(name)
        if k not in self.arrays:
            self.arrays[k] = [("s", "") if k[1] == "$" else ("n", Fr(0))] * 11
        return self.arrays[k]

    # -- statements -------------------------------------------------------------------------------------------------
    def deflist(self, t, rest):
        """the DEF list: LETTER [- LETTER] {, ...}; each item is APPLIED AS SOON AS IT IS READ, then its
        terminator is checked (`,` goes on; `:` / the end stops; anything else is error 2)"""
        s, i = rest, 0

        def sp(i):
            while i < len(s) and s[i] == " ":
                i += 1
            return i
        while True:
            i = sp(i)
            if i >= len(s) or not s[i].isalpha():
                raise Err(2)
            a = b = s[i]
            i = sp(i + 1)
            if i < len(s) and s[i] == "-":
                i = sp(i + 1)
                if i >= len(s) or not s[i].isalpha():
                    raise Err(2)
                b = s[i]
                i = sp(i + 1)
                if b < a and "reversed-swaps" not in self.alt:
                    raise Err(2)
                a, b = min(a, b), max(a, b)
            if "all-or-nothing" in self.alt:
                pend = getattr(self, "_pend", [])
                pend += [chr(c) for c in range(ord(a), ord(b) + 1)]
                self._pend = pend
            else:
                for c in range(ord(a), ord(b) + 1):
                    self.deftbl[chr(c)] = t
            if i >= len(s):
                if "all-or-nothing" in self.alt:
                    for c in self._pend:
                        self.deftbl[c] = t
                return
            if s[i] != ",":
                raise Err(2)
            i += 1

    def stmt(self, s):
        s = s.strip()
        m = re.match(r"(DEFINT|DEFSNG|DEFDBL|DEFSTR)(.*)$", s)
        if m:
            self._pend = []
            return self.deflist(KWS[m.group(1)], m.group(2))
        if s.startswith("CLEAR"):
            if "clear-keeps-def" in self.alt:
                self.vars, self.arrays = {}, {}
            else:
                self.clear()
            return
        if s.startswith("RESTORE"):
            return
        if s.startswith("DIM "):
            self.array(s[4:].split("(")[0])
            return
        if s.startswith("READ "):
            return self.assign(s[5:], ("n", Fr(self.data.pop(0))))
        m = re.match(r"FOR (\w+)=(.+) TO (.+)$", s)
        if m:
            self.forvar, self.forend = m.group(1), self.expr(m.group(3))
            return self.assign(m.group(1), self.expr(m.group(2)))
        if s == "NEXT":
            k = self.key(self.forvar)
            return self.assign(self.forvar, ("n", self.forend[1] + 1)) if k in self.vars else None
        lhs, rhs = s.split("=", 1)
        return self.assign(lhs, None, rhs)

    def assign(self, lhs, val, rhs=None):
        """LET: the target is created FIRST (its type's zero), then the value is evaluated and converted"""
        lhs = lhs.strip()
        m = re.match(r"(\w+[$%!#]?)\((\d+)\)$", lhs)
        if m:
            arr = self.array(m.group(1))
            t = self.typ(m.group(1))
            arr[int(m.group(2))] = self.store(t, val if rhs is None else self.expr(rhs))
            return
        k = self.key(lhs)
        if "create-after" not in self.alt and k not in self.vars:
            self.vars[k] = ("s", "") if k[1] == "$" else ("n", Fr(0))
        v = self.store(k[1], val if rhs is None else self.expr(rhs))
        self.vars[k] = v


def _split(s):
    out, cur, q = [], "", False
    for ch in s:
        if ch == '"':
            q = not q
        if ch == ":" and not q:
            out.append(cur)
            cur = ""
        else:
            cur += ch
    return out + [cur]


def _upper(s):
    return re.sub(r'"[^"]*"|[^"]+', lambda m: m.group(0) if m.group(0).startswith('"') else m.group(0).upper(), s)


def run(c, alt=frozenset()):
    """(e, f, [the named variables' type codes, NOVAR when absent], v) the interpreter gives for case c"""
    data = [x.split("DATA ")[1] for x in c.subs.values() if "DATA " in x]
    mc = Machine(alt, data)
    errs = []
    for st in _split(_upper(c.stmt)):
        try:
            mc.stmt(st)
        except Err as e:
            errs.append(e.n)
    wv = mc.vars.get(("WV", "#"), ("n", Fr(0)))[1]
    ts = []
    for name in c.names:
        k = mc.key(name)
        ts.append(CODE[k[1]] if k in mc.vars else NOVAR)
    ts += [0] * (3 - len(ts))
    return (errs[0] if errs else 0), (errs[-1] if errs else 0), ts, wv


def behaves(c, alt=frozenset()):
    """errors, the value, and WHETHER each named variable exists (not its type byte -- that is R-xxx-ENTRY's)"""
    e, f, ts, v = run(c, alt)
    exists = [None if x == 0 else x != NOVAR for x in ts]
    got = [None if x == 0 else x != NOVAR for x in c.t]
    return (c.e, c.f, c.v) == (e, f, v) and got == exists


def entry(c, alt=frozenset()):
    """the byte before an existing variable's name is its type code"""
    _, _, ts, _ = run(c, alt)
    return list(c.t) == ts


def load(kw):
    out = kdeftype.load()
    return {who: [c for c in cs if c.kw == kw] for who, cs in out.items()}


NAME_WHYS = {"a suffix wins over DEF", "the type is looked up at each use: the double A is not the int A",
             "two A's side by side: back to the double one", "A and A$ are the same variable",
             "DEFSNG A-Z; a double read through another suffix"}


def has_def(c):
    return "DEF" in c.stmt.upper()


def rules(kw, cases=None):
    """the page's rules; with `cases`, a rule that selects none of them is left out (a rule about nothing)"""
    rs = _rules(kw)
    return rs if cases is None else [r for r in rs if any(r.select(c) for c in cases)]


def _rules(kw):
    k = kw[3:]                        # INT SNG DBL STR
    s1, s2, s3 = "1. The letters", "2. Storing a value", "3. The variable table"
    syn = lambda c: c.e == 2          # noqa: E731
    ok = lambda c: not syn(c)         # noqa: E731
    out = [
        Rule(f"R-{k}-LIST", s1, f"`{kw}` takes a list of items separated by `,`: a letter, or a range `X-Y` (spaces "
             "allowed around the dash and before the comma). Every letter of the list now gives an unsuffixed name "
             "that type; the last `DEF` for a letter wins, and `CLEAR` puts every letter back to double. Each item "
             "is applied as soon as it is read: a bad item later in the list, or text glued to it (`DEFINT AB`, "
             "`DEFINT A-CD`), is error 2 (Syntax error) but the items before it -- and the glued item itself -- "
             "stand. Anything else -- no item, a digit, a range without its end letter or written backwards, a "
             "suffix, a trailing comma -- is error 2 too.",
             lambda c: has_def(c), behaves),
        Rule(f"R-{k}-NAME", s1, "Only an unsuffixed name follows the table, through its FIRST letter, and the table is "
             "read at every USE of a name, not when the variable was made: after `A=7:DEFINT A`, `A` names a new "
             "integer variable (0) beside the double one, which `DEFDBL A` names again. A suffix always wins.",
             lambda c: ok(c) and has_def(c) and c.why in NAME_WHYS,
             behaves),
    ]
    store = {
        "INT": ("An integer variable keeps the whole part, cut TOWARDS ZERO (1.7 -> 1, -1.7 -> -1, 2.5 -> 2); "
                "outside -32768..32767 is error 6 (Overflow). FOR, READ and array elements store the same way."),
        "SNG": "A single variable keeps six digits, the seventh rounded half up (1.23456789 -> 1.23457).",
        "DBL": "Without any DEF every unsuffixed name is double: fourteen digits.",
        "STR": ("An unsuffixed name of a DEFSTR letter IS the `$` variable (`A` and `A$` are one); storing a "
                "number in it is error 13 (Type mismatch)."),
    }[k]
    out.append(Rule(f"R-{k}-STORE", s2, store + " An assignment makes its variable BEFORE the value is checked, so "
                    "after an error the variable exists, holding its type's zero; reading a name never makes it.",
                    lambda c: ok(c) and not c.why in NAME_WHYS,
                    behaves))
    out.append(Rule(f"R-{k}-ENTRY", s3, "The byte just before a variable's two name bytes, `PEEK(VARPTR(v)-3)`, is "
                    "its type: 2 integer, 3 string, 4 single, 8 double (the published MSX variable entry: type, two "
                    "name bytes, value).",
                    lambda c: any(x not in (0, NOVAR) for x in c.t), entry))
    return out
