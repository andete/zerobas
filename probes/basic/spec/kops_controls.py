#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""The CONTROLS of kops_model's rules (docs/spec-method.md §3a: a rule must be shown able to fail). Each control is a
deliberately altered model -- a rival rule the probe was built to separate -- run over the same reference cases as
the page's rule; it must be FALSE on some of them, or the matrix cannot tell the two rules apart.

    python3 probes/basic/spec/kops_controls.py      (exit 1 when a control finds no case against it)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kops_model as M  # noqa: E402


def with_levels(levels):
    """the PREC rule under another order of the two-operand logical operators"""
    def check(c):
        saved = M.LEVELS[:]
        M.LEVELS[:] = levels
        try:
            return M.case_ok(c, M.want(c))
        finally:
            M.LEVELS[:] = saved
    return check


def not_tight(c):
    """NOT binding as tightly as a unary minus (NOT 1+2 = (NOT 1)+2, NOT 1=2 = (NOT 1)=2)"""
    saved = M.Parser.not_, M.Parser.unary

    def not_(self):
        return self.cmp()

    def unary(self):
        if self.peek() == "NOT":
            self.take()
            return M.Fraction(M.binop("NOT", unary(self), None))
        return saved[1](self)
    M.Parser.not_, M.Parser.unary = not_, unary
    try:
        return M.case_ok(c, M.want(c))
    finally:
        M.Parser.not_, M.Parser.unary = saved


def minus_not_syntax(c):
    """NOT after an operator (a minus, *, +) is a Syntax error -- zerobas's"""
    if c.src in ("FX", "FY") and c.expr.replace(" ", "")[:1] in "-2" and "NOT" in c.expr and not c.expr.startswith("NOT"):
        return M.case_ok(c, ("err", 2))
    return M.case_ok(c, M.want(c))


def mod_plus(c):
    """MOD looser than + (7 MOD 4+2 = 7 MOD 6)"""
    saved = M.Parser.add, M.Parser.mod

    def add(self):
        v = saved[1](self) if False else self.idiv()
        while self.peek() in ("+", "-"):
            op = self.take()
            w = self.idiv()
            v = v + w if op == "+" else v - w
        return v

    def mod(self):
        v = add(self)
        while self.peek() == "MOD":
            self.take()
            v = M.Fraction(M.binop("MOD", v, add(self)))
        return v

    def cmp(self):
        v = mod(self)
        while self.peek() in ("=", "<", ">"):
            op = self.take()
            w = mod(self)
            v = M.Fraction(-1 if {"=": v == w, "<": v < w, ">": v > w}[op] else 0)
        return v
    sc = M.Parser.cmp
    M.Parser.cmp = cmp
    try:
        return M.case_ok(c, M.want(c))
    finally:
        M.Parser.cmp = sc


def per(op):
    return [
        (f"R-{op}-VALUE", "operands rounded half away from zero (not truncated)",
         lambda c: M.case_ok(c, M.want(c, how="round"))),
        (f"R-{op}-VALUE", "operands floored (as INT)", lambda c: M.case_ok(c, M.want(c, how="floor"))),
        (f"R-{op}-RANGE", "operands read as unsigned 16-bit (32768 .. 65535 accepted)",
         lambda c: M.case_ok(c, M.want(c, how="unsigned"))),
    ]


CONTROLS = {op: per(op) for op in ("AND", "OR", "XOR", "EQV", "IMP", "NOT", "MOD")}
CONTROLS["MOD"].append(("R-MOD-VALUE", "the remainder with the divisor's sign", lambda c: M.case_ok(c, M.want(c, mod_sign="divisor"))))
CONTROLS["MOD"].append(("R-MOD-PREC", "MOD looser than + and -", mod_plus))
CONTROLS["AND"].append(("R-AND-PREC", "AND and OR at one level, left to right",
                        with_levels([("IMP",), ("EQV",), ("XOR",), ("AND", "OR")])))
CONTROLS["OR"].append(("R-OR-PREC", "OR looser than XOR", with_levels([("IMP",), ("EQV",), ("OR",), ("XOR",), ("AND",)])))
CONTROLS["IMP"].append(("R-IMP-PREC", "IMP tighter than EQV", with_levels([("EQV",), ("IMP",), ("XOR",), ("OR",), ("AND",)])))
CONTROLS["EQV"].append(("R-EQV-PREC", "EQV tighter than OR", with_levels([("IMP",), ("XOR",), ("OR",), ("EQV",), ("AND",)])))
CONTROLS["XOR"].append(("R-XOR-PREC", "XOR tighter than AND", with_levels([("IMP",), ("EQV",), ("OR",), ("AND",), ("XOR",)])))
CONTROLS["NOT"].append(("R-NOT-PREC", "NOT tighter than comparisons and arithmetic", not_tight))
CONTROLS["NOT"].append(("R-NOT-PREC", "NOT after an operator a Syntax error -- zerobas's", minus_not_syntax))


def late_left(c):
    """the left operand made an integer only after the right one is read (a string on the right wins)"""
    saved = getattr(M.Parser, "late", False)
    M.Parser.late = True
    try:
        return M.case_ok(c, M.want(c))
    finally:
        M.Parser.late = saved


CONTROLS["AND"].append(("R-AND-RANGE", "the right operand read before the left is converted", late_left))


def main():
    rc = 0
    for op, ctl in CONTROLS.items():
        cs = M.load(op)["ref"]
        rules = {r.id: r for r in M.rules(op)}
        for rid, what, check in ctl:
            sel = [c for c in cs if rules[rid].select(c)]
            false = [c.id for c in sel if not check(c)]
            print(f"{rid:13s} {what[:66]:66s} FALSE on {len(false):4d} of {len(sel):<4d}"
                  f"{'  e.g. ' + false[0] if false else '  <-- NO CASE AGAINST IT'}")
            rc |= not false
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
