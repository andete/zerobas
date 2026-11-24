#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""The CONTROLS of kstr_model's rules (docs/spec-method.md §3a: a rule must be shown able to fail). Each control is a
deliberately altered model -- a rival rule the probe was built to separate -- run over the same reference cases as
the page's rule; it must be FALSE on some of them, or the matrix cannot tell the two rules apart.

    python3 probes/basic/spec/kstr_controls.py      (exit 1 when a control finds no case against it)
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kstr_model as M  # noqa: E402


def rnd(v):
    """rounding half away from zero, the rival of truncation"""
    return int(math.floor(abs(v) + 0.5)) * (1 if v >= 0 else -1)


def byte_round(v):
    t = rnd(v)
    if t < -32768 or t > 32767:
        return 6, None
    return (5, None) if t < 0 or t > 255 else (0, t)


def byte_int(v):
    t = math.floor(v)
    if t < -32768 or t > 32767:
        return 6, None
    return (5, None) if t < 0 or t > 255 else (0, t)


def with_arg(model, argf):
    """run `model` with M.byte_arg replaced by argf"""
    def f(c):
        old = M.byte_arg
        M.byte_arg = argf
        try:
            return model(c)
        finally:
            M.byte_arg = old
    return f


def string_code_first(c):
    """STRING$ with the code checked before the count"""
    if c.src == "STRN":
        e, _ = M.byte_arg(c.c)
        if e:
            return "err", e
    return M.m_string(c)


def string_empty_ok(c):
    """an empty fill allowed when the count is 0"""
    if c.src == "STRS" and not c.s and M.byte_arg(c.n) == (0, 0):
        return "str", b""
    return M.m_string(c)


def instr_from0(c):
    """INSTR searching from the start's own index (one past), the off-by-one rival"""
    k, v = M.m_instr(c)
    if k != "num" or c.n is None or not c.t:
        return k, v
    i = c.s.find(c.t, M.start_arg(c.n)[1])
    return "num", 0 if i < 0 else i + 1


def instr_start0(c):
    """INSTR with start 0 allowed (taken as 1)"""
    if c.n is not None and 0 <= c.n < 1:
        return M.m_instr(type("C", (), dict(vars(c), n=1))())
    return M.m_instr(c)


CONTROLS = [
    # (keyword, rule it shadows, what it alters, select, altered model)
    ("LEN", "R-LEN-VALUE", "a length that stops at CHR$(0)", M.M,
     lambda c: ("num", c.s.index(0) if 0 in c.s else len(c.s))),
    ("ASC", "R-ASC-VALUE", "the LAST character's code", lambda c: M.M(c) and c.s, lambda c: ("num", c.s[-1])),
    ("CHR$", "R-CHR-VALUE/ERR5/ERR6", "rounding in place of truncation", lambda c: c.src == "NUM",
     with_arg(M.m_chr, byte_round)),
    ("CHR$", "R-CHR-VALUE/ERR5/ERR6", "INT in place of truncation", lambda c: c.src == "NUM",
     with_arg(M.m_chr, byte_int)),
    ("SPACE$", "R-SPACE-VALUE/ERR5/ERR6", "rounding in place of truncation", lambda c: c.src == "NUM",
     with_arg(M.m_space, byte_round)),
    ("STRING$", "R-STRING-COUNT", "the code checked before the count", lambda c: c.src == "STRN",
     string_code_first),
    ("STRING$", "R-STRING-EMPTY", "an empty fill allowed with count 0", lambda c: c.src == "STRS",
     string_empty_ok),
    ("INSTR", "R-INSTR-EMPTY", "an empty b$ found at min(start, LEN(a$)+1) -- zerobas's rule",
     lambda c: M.M(c) and not c.t, lambda c: M.m_instr(c, "lenplus1")),
    ("INSTR", "R-INSTR-FIND", "the search starting one past the start", lambda c: M.M(c) and c.t, instr_from0),
    ("INSTR", "R-INSTR-START", "start 0 allowed (as 1)", lambda c: M.M(c), instr_start0),
]


def main():
    bad = 0
    cache = {}
    for fn, rule, what, sel, model in CONTROLS:
        if fn not in cache:
            cache[fn] = M.load(fn)["ref"]
        cs = [c for c in cache[fn] if sel(c)]
        false = [c.id for c in cs if not M.outcome(c, model)]
        print(f"{fn:8} {rule:24} {what:62} FALSE on {len(false):4} of {len(cs)}"
              + (f"  e.g. {false[0]}" if false else "  <- NO CASE SEPARATES IT"))
        bad += not false
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
