#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""The CONTROLS of krnd_model's rules (docs/spec-method.md §3a: a rule must be shown able to fail). Each control is a
deliberately altered generator -- a rival rule the probe was built to separate, or one constant changed in its last
digit -- run over the same reference cases as the page's rule; it must be FALSE on some of them, or the matrix
cannot tell the two rules apart.

    python3 probes/basic/spec/krnd_controls.py      (exit 1 when a control finds no case against it)
"""
import os
import sys
from fractions import Fraction

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import krnd_model as M  # noqa: E402
import ramrec  # noqa: E402


def gen(**kw):
    g = dict(M.GEN)
    g.update(kw)
    return g


def by_group(cases):
    out = {}
    for c in cases:
        out.setdefault(c.src, []).append(c)
    return out


def chain_under(cases, g=M.GEN, alt=frozenset()):
    exp = {}
    for cs in by_group(cases).values():
        exp.update(M.chain(cs, g, alt))
    return exp


def local_is(g=M.GEN, alt=frozenset()):
    return lambda c: M.same(c, M.local(c, g, alt))


def seed_local(mfun):
    """the plain reseed steps predicted with a rival m (from the argument's type and bytes)"""
    def check(c):
        ty, b = (c.ty, c.arg[:M.NB[c.ty]]) if c.op in ("R", "U") else _fx_arg(c)
        S = M.call(c.prev, "seed", mfun(ty, b))
        r = M.result(S)
        if c.op == "U" or (c.stmt or "").startswith("Q=USR("):
            return c.res == r and M.state_of(c.rndx) == S
        return c.rbytes == r and M.state_of(c.rndx) == S
    return check


def _fx_arg(c):
    if c.stmt in ("R=RND(-1/3)", "R=RND(-1!/3)"):
        return "D", M.THIRD
    ty, t = M.FX_ARG.get(c.stmt) or ("I", c.stmt[len("R#=RND("):-1])
    return ty, M.enc(t, ty)


def m_value(ty, b):
    """the argument's VALUE times 10^13 (the exponent counts)"""
    v = abs(ramrec.number(b))
    return int(v * 10 ** 13) % M.M14


def m_right(ty, b):
    """an integer's digits right-aligned (m = |n|)"""
    if ty == "I":
        return abs(ramrec.number(b))
    return M.classify(ty, b)[1]


def m_double(ty, b):
    """a single widened by its VALUE to 14 digits of 1/3-style: the single's value re-read as a double's digits
    of the same value -- here: a single's 6 digits repeated (rival to '6 then 8 zeros')"""
    if ty == "S":
        d = b[1:].hex()
        return int((d * 3)[:14])
    return M.classify(ty, b)[1]


def odd_sign_ignored(c):
    """an exponent-0 number is a zero even with the sign bit set"""
    S = c.prev
    return M.state_of(c.rndx) == S


REF = None


def ref():
    global REF
    if REF is None:
        REF = M.load()["ref"]
    return REF


def sel(rule_id):
    r = next(r for r in M.get_rules() if r.id == rule_id)
    return r.select


def chain_control(g=M.GEN, alt=frozenset()):
    exp = chain_under(ref(), g, alt)
    return lambda c: M.same(c, exp[c.id])


CONTROLS = [
    # (rule it shadows, what it alters, select, check)
    ("R-RND-NEXT", "A's last digit 9 -> 8 (21132486540518)", sel("R-RND-NEXT"),
     local_is(gen(A=21132486540518))),
    ("R-RND-NEXT", "C's last digit 1 -> 3 (14389820420823)", sel("R-RND-NEXT"),
     local_is(gen(C=14389820420823))),
    ("R-RND-NEXT", "a positive argument reseeds from its digits (the value matters)", sel("R-RND-NEXT"),
     local_is(alt={"pos-reseeds"})),
    ("R-RND-REPEAT", "RND(0) steps like a positive argument", sel("R-RND-REPEAT"), local_is(alt={"zero-steps"})),
    ("R-RND-SEED", "m is the argument's VALUE times 10^13 (the exponent counts)", sel("R-RND-SEED"),
     seed_local(m_value)),
    ("R-RND-SEED", "an integer's digits right-aligned (m = |n|)", sel("R-RND-SEED"), seed_local(m_right)),
    ("R-RND-SEED", "a single's 6 digits repeated, not followed by zeros", sel("R-RND-SEED"), seed_local(m_double)),
    ("R-RND-SIGN", "an exponent-0 number is a zero even with the sign bit set", sel("R-RND-SIGN"), odd_sign_ignored),
    ("R-RND-ORDER", "right to left", sel("R-RND-ORDER"), local_is(alt={"right-to-left"})),
    ("R-RND-CHAIN", "S0's last digit 8 -> 9 (40649651372359)", sel("R-RND-CHAIN"),
     chain_control(gen(S0=40649651372359))),
    ("R-RND-VALUE", "the result not normalised (exponent &H40, leading zeros kept)", sel("R-RND-VALUE"),
     lambda c: c.rbytes == M.out(M.state_of(c.rndx), {"unnormalised"})),
    ("R-RND-VALUE", "a zero result keeps digit bytes under exponent 0 -- zerobas's", sel("R-RND-VALUE"),
     lambda c: c.rbytes == M.out(M.state_of(c.rndx), {"zero-keeps-digits"})),
    ("R-RND-CELL", "RNDX holds the normalised result (byte 0 the exponent)", sel("R-RND-CHAIN"),
     chain_control(alt={"rndx-result"})),
    ("R-RND-TYPE", "the result in the argument's own type", sel("R-RND-TYPE"),
     lambda c: c.op != "U" or c.vt == M.NB[c.ty]),
    ("R-RND-START", "entering a program line keeps the state -- zerobas's", sel("R-RND-START"),
     chain_control(alt={"line-keeps"})),
    ("R-RND-START", "RUN keeps the state", sel("R-RND-START"), chain_control(alt={"no-run-reset"})),
    ("R-RND-START", "CLEAR keeps the state", sel("R-RND-START"), chain_control(alt={"no-clear-reset"})),
    ("R-RND-START", "NEW keeps the state", sel("R-RND-START"), chain_control(alt={"no-new-reset"})),
    ("R-RND-STRTARGET", "the string target refused before RND runs (the state stays)", sel("R-RND-STRTARGET"),
     local_is(alt={"type-first"})),
    ("R-RND-CHECKS", "the argument's type checked before the `)` (13) -- zerobas's rule", sel("R-RND-CHECKS"),
     local_is(alt={"zb-order"})),
]


def main():
    bad = 0
    for rule, what, s, check in CONTROLS:
        cs = [c for c in ref() if s(c)]
        false = [c.id for c in cs if not check(c)]
        print(f"{rule:16} {what:78} FALSE on {len(false):4} of {len(cs)}"
              + (f"  e.g. {false[0]}" if false else "  <- NO CASE SEPARATES IT"))
        bad += not false
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
