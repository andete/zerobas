#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-FREPLUS14 (2026-10-17): a Python prototype of the re-scan that docs/spec-basic-
frelive.md plans for zerobas's FRE(0) -- validated against the VG-8020's measured
depths (scratchpad/freshape_run3.out) BEFORE any Z80 is written.

It runs a shunting-yard over an expression's text up to the first `FRE(`, keeps what
is still pending there, and sums the reference's costs for it:
  open `(` 6 . unary - / NOT 6 . function call 10 . array subscript 18
  arithmetic op 8 + width(left) . relational 10 + width(left) . integer op 8
  string concatenation 2
Widths: integer 2, single 4, double 8 (string 3). Untyped variables are double.
"""
import re, sys

W = {"int": 2, "sng": 4, "dbl": 8, "str": 3}
PREC = {"^": 13, "*": 11, "/": 11, "\\": 10, "MOD": 9, "+": 8, "-": 8,
        "=": 7, "<": 7, ">": 7, "<>": 7, "<=": 7, ">=": 7,
        "AND": 5, "OR": 4, "XOR": 3, "EQV": 2, "IMP": 1}
UNARY_PREC = {"NEG": 12, "NOT": 6}
INTOPS = {"\\", "MOD", "AND", "OR", "XOR", "EQV", "IMP"}
RELOPS = {"=", "<", ">", "<>", "<=", ">="}
FUNC_INT = {"LEN", "ASC", "PEEK", "INP", "POS", "LPOS", "VPEEK", "INSTR", "SGN", "CINT",
            "STICK", "STRIG", "PDL", "PAD", "EOF", "LOC", "LOF", "VARPTR", "CSRLIN"}
FUNC_SAME = {"ABS", "INT", "FIX"}                  # the argument's own type
TOKEN = re.compile(r'\s*(?:(?P<str>"[^"]*")|(?P<num>\d+\.\d*|\d+)(?P<nsuf>[%!#]?)'
                   r'|(?P<kw>MOD|AND|OR|XOR|EQV|IMP|NOT)\b|(?P<name>[A-Z][A-Z0-9]*\$?[%!#]?)'
                   r'|(?P<op><>|<=|>=|[-+*/^\\=<>(),]))')


def tokens(text):
    pos, out = 0, []
    while pos < len(text):
        m = TOKEN.match(text, pos)
        if not m or m.end() == pos:
            raise ValueError(f"cannot tokenise at {text[pos:]!r}")
        pos = m.end()
        if m["str"]:
            out.append(("val", "str"))
        elif m["num"]:
            suf = m["nsuf"]
            if suf:
                out.append(("val", {"%": "int", "!": "sng", "#": "dbl"}[suf]))
            elif "." in m["num"] or int(m["num"]) > 32767:
                out.append(("val", "dbl"))
            else:
                out.append(("val", "int"))
        elif m["kw"]:
            out.append(("op", m["kw"]))
        elif m["name"]:
            out.append(("name", m["name"]))
        else:
            out.append(("op", m["op"]))
    return out


def vtype(name):
    if name.endswith("$"):
        return "str"
    return {"%": "int", "!": "sng", "#": "dbl"}.get(name[-1], "dbl")


def result(op, lt, rt):
    if op in RELOPS or op in INTOPS:
        return "int"
    if op == "+" and lt == "str":
        return "str"
    if op in ("/", "^"):
        return "dbl"
    return max(lt, rt, key=lambda t: W[t])


def cost(entry):
    kind = entry[0]
    if kind == "paren":
        return 6
    if kind == "unary":
        return 6
    if kind == "func":
        return 10
    if kind == "array":
        return 18
    op, left = entry[1], entry[2]
    if op in INTOPS:
        return 8
    if op in RELOPS:
        return 10 + W[left]
    if op == "+" and left == "str":
        return 2
    return 8 + W[left]


def depth(text):
    """The reference's depth at the first FRE( in `text` (an expression)."""
    toks = tokens(text)
    stack, vals, expect = [], [], True
    i = 0

    def reduce_top():
        e = stack.pop()
        if e[0] == "unary":
            v = vals.pop()
            vals.append("int" if e[1] == "NOT" else v)
        else:
            rt = vals.pop()
            vals.append(result(e[1], e[2], rt))

    def prec(e):
        return UNARY_PREC[e[1]] if e[0] == "unary" else PREC[e[1]]

    while i < len(toks):
        kind, v = toks[i]
        nxt = toks[i + 1] if i + 1 < len(toks) else None
        if expect:
            if kind == "name" and v == "FRE" and nxt == ("op", "("):
                return sum(cost(e) for e in stack)
            if kind == "op" and v in ("-", "NOT"):
                stack.append(("unary", "NEG" if v == "-" else "NOT"))
            elif kind == "op" and v == "(":
                stack.append(("paren",))
            elif kind == "name" and nxt == ("op", "("):
                is_fn = v in FUNC_INT or v in FUNC_SAME or v.endswith("$") and len(v) > 2 \
                    or v in {"VAL", "SQR", "SIN", "COS", "TAN", "ATN", "EXP", "LOG", "RND",
                             "CSNG", "CDBL", "FRE", "USR"}
                stack.append(("func", v) if is_fn else ("array", vtype(v)))
                i += 1                                   # the '(' belongs to it
            elif kind == "name":
                vals.append(vtype(v)); expect = False
            elif kind == "val":
                vals.append(v); expect = False
            else:
                raise ValueError(f"unexpected {v!r}")
        else:
            if kind == "op" and v in (")", ","):
                while stack and stack[-1][0] in ("op", "unary"):
                    reduce_top()
                if v == ")":
                    e = stack.pop()
                    inner = vals.pop()
                    if e[0] == "func":
                        vals.append("int" if e[1] in FUNC_INT else inner if e[1] in FUNC_SAME
                                    else "str" if e[1].endswith("$") else
                                    "sng" if e[1] == "CSNG" else "dbl")
                    elif e[0] == "array":
                        vals.append(e[1])
                    else:
                        vals.append(inner)
                else:
                    vals.pop(); expect = True
            elif kind == "op" and v in PREC:
                while stack and stack[-1][0] in ("op", "unary") and prec(stack[-1]) >= PREC[v]:
                    reduce_top()
                stack.append(("op", v, vals.pop())); expect = True
            else:
                raise ValueError(f"unexpected {v!r} after an operand")
        i += 1
    raise ValueError("no FRE( in the expression")


# the measured VG-8020 depths (freshape_run3.out), expression -> depth
MEASURED = {
    "(FRE(0))": 6, "((FRE(0)))": 12, "(((FRE(0))))": 18, "0+FRE(0)": 10, "FRE(0)+0": 0,
    "1*FRE(0)": 10, "FRE(0)*1": 0, "0+1*FRE(0)": 20, "0+0+FRE(0)": 10,
    "0+(0+(0+FRE(0)))": 42, "-(-FRE(0))": 18, "1-(1-FRE(0))": 26, "0 OR FRE(0)": 8,
    "(0=0)*0+FRE(0)": 10, "ABS(FRE(0))": 10, "INT(ABS(FRE(0)))": 20,
    "VAL(STR$(FRE(0)))": 20, "2*FRE(0)/2": 10,
    "I%+FRE(0)-I%": 10, "S!+FRE(0)-S!": 12, "D#+FRE(0)-D#": 16, "E#*FRE(0)": 16,
    "A-K<FRE(0)": 18, "(A-K<FRE(0))=(0=0)": 24, "-1 AND (A-K<FRE(0))": 32,
    "0 XOR (A-K<FRE(0))": 32, "(A-K<FRE(0)) MOD 2": 24, "(A-K<FRE(0))\\1": 24,
    "(A-K<FRE(0))^1": 24, "NOT(A-K<FRE(0))": 30,
    "8 MOD ((A-K<FRE(0))-2)": 38, "8\\((A-K<FRE(0))-2)": 38, "2^(A-K<FRE(0))": 34,
    "1/((A-K<FRE(0))-2)": 40, "0 EQV (A-K<FRE(0))": 32, "-1 IMP (A-K<FRE(0))": 32,
    "0=(A-K<FRE(0))": 36, "0<>(A-K<FRE(0))": 36, "-1>=(A-K<FRE(0))": 36,
    "0<=(A-K<FRE(0))": 36, "0>(A-K<FRE(0))": 36, "R((A-K<FRE(0))+1)": 42,
    "A%-K%<FRE(0)": 12, "VAL(\"\"+STR$(FRE(0)))": 22,
}


def main():
    bad = 0
    for expr, want in MEASURED.items():
        got = depth(expr)
        ok = got == want
        bad += not ok
        print(f"{'ok  ' if ok else 'MISS'} {expr:28} model {got:3} measured {want:3}")
    print(f"\n{len(MEASURED) - bad}/{len(MEASURED)} rows match the model")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
