#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""The CONTROLS of kslice_model's rules (LEFT$ / RIGHT$ / MID$; docs/spec-method.md §3a: a rule must be shown able to
fail). Each control is a rival rule the probe was built to separate, run over the REFERENCE cases the page's rule
selects; it must be FALSE on some of them, or the cases cannot tell the two rules apart.

    python3 probes/basic/spec/kslice_controls.py      (exit 1 when a control finds no case against it)

Written for the goldfish pass (2026-11-24); the first three are the pilot's (spec-plan §6), which ran by hand then.
"""
import math
import os
import sys
from types import SimpleNamespace as NS

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kslice_model as M  # noqa: E402


def rnd(v):
    """rounding half away from zero, the rival of truncation"""
    return int(math.floor(abs(v) + 0.5)) * (1 if v >= 0 else -1)


def arg_round(v, lo=0):
    t = rnd(v)
    if t < -32768 or t > 32767:
        return 6, None
    return (5, None) if t < lo or t > 255 else (0, t)


def arg_test_first(v, lo=0):
    """the overflow test on the value BEFORE truncation (-32768.5 would be 6)"""
    if v < -32768 or v > 32767:
        return 6, None
    t = math.trunc(v)
    return (5, None) if t < lo or t > 255 else (0, t)


def arg_6_high_only(v, lo=0):
    """error 6 only above 32767; anything negative is 5 (the count's lower overflow assumed away)"""
    t = math.trunc(v)
    if t > 32767:
        return 6, None
    return (5, None) if t < lo or t > 255 else (0, t)


def patched(model, argf, posf=None):
    def f(c):
        old = M.arg, M.pos
        M.arg = argf
        M.pos = posf or (lambda v: argf(v, 1))
        try:
            return model(c)
        finally:
            M.arg, M.pos = old
    return f


def rule(rules, rid):
    return next(r for r in rules if r.id == rid)


def outer_reads_source(c):
    """nested: the outer call reads the ORIGINAL source, not the inner result"""
    e = c.expr
    if "LEFT$(RIGHT$" in e or "LEFT$(LEFT$" in e:
        return M.result_is(c, M.S5[:2] if "LEFT$(RIGHT$" in e else M.S5[:4])
    if "RIGHT$(LEFT$" in e or "RIGHT$(RIGHT$" in e:
        return M.result_is(c, M.S5[-2:] if "RIGHT$(LEFT$" in e else M.S5[-4:])
    if "MID$(MID$" in e:
        return M.result_is(c, M.S5[1:3])
    return M.want(c)


LEFT = M.lr_rules("LEFT$", "LEFT", "")
RIGHT = M.lr_rules("RIGHT$", "RIGHT", "")
MID = M.mid_rules("")
lr_left = lambda c: M.lr(c, "LEFT$")  # noqa: E731

# (what the rival says, keyword, the page's rule whose cases it runs over, the rival's check)
CONTROLS = [
    ("LEFT$'s count rounded, not truncated", "LEFT$", "R-LEFT-SLICE",
     lambda c: M.outcome(c, patched(lr_left, arg_round))),
    ("MID$'s position 0 allowed (taken as 1)", "MID$", "R-MID-POS",
     lambda c: M.outcome(c, lambda c: M.mid(NS(**{**vars(c), "p": 1.0}) if math.trunc(c.p) == 0 else c))
     if M.M(c) else M.error_is(c, 6)),
    ("LEFT$'s data judged by RIGHT$'s rule", "LEFT$", "R-LEFT-SLICE",
     lambda c: M.outcome(c, lambda c: M.lr(c, "RIGHT$"))),
    ("the overflow test before truncation (-32768.5 is 6)", "LEFT$", "R-LEFT-ERR5",
     lambda c: M.outcome(c, patched(lr_left, arg_test_first))),
    ("MID$'s position overflow tested before truncation", "MID$", "R-MID-POS",
     lambda c: M.outcome(c, patched(M.mid, M.arg, lambda v: arg_test_first(v, 1))) if M.M(c) else M.error_is(c, 6)),
    ("MID$'s count overflows only above 32767 (below -32768 is 5)", "MID$", "R-MID-COUNT",
     lambda c: M.outcome(c, patched(M.mid, arg_6_high_only, M.pos))),
    ("MID$'s count overflow tested before truncation", "MID$", "R-MID-COUNT",
     lambda c: M.outcome(c, patched(M.mid, arg_test_first, M.pos))),
    ("nested: the outer LEFT$ reads the original source", "LEFT$", "R-LEFT-EXPR", outer_reads_source),
    ("nested: the outer RIGHT$ reads the original source", "RIGHT$", "R-RIGHT-EXPR", outer_reads_source),
    ("nested: the outer MID$ reads the original source", "MID$", "R-MID-EXPR", outer_reads_source),
    ("all arguments evaluated before the string's type is checked (LEFT$(5,1/0) is 11)", "LEFT$", "R-LEFT-TYPE",
     lambda c: M.error_is(c, 11 if "1/0" in c.expr else 13)),
    ("all arguments evaluated before the string's type is checked (MID$(5,1/0) is 11)", "MID$", "R-MID-TYPE",
     lambda c: M.error_is(c, 11 if "1/0" in c.expr else 13)),
    ("the call is parsed before the count's range (LEFT$(S$,256,1) is 2)", "LEFT$", "R-LEFT-EARLY",
     lambda c: M.error_is(c, 2)),
    ("the call is parsed before the range (MID$(S$,0,1,1) is 2)", "MID$", "R-MID-EARLY", lambda c: M.error_is(c, 2)),
    ("an empty count is 24 (Missing operand)", "RIGHT$", "R-RIGHT-SYNTAX",
     lambda c: M.error_is(c, 24 if c.src == "FY" else 2)),
    ("an empty argument is 24 (Missing operand)", "MID$", "R-MID-SYNTAX",
     lambda c: M.error_is(c, 24 if c.src == "FY" else 2)),
    ("the count evaluated and type-checked before the position's range (MID$(S$,-32769,\"A\") is 13)", "MID$",
     "R-MID-ORDER",
     lambda c: M.error_is(c, 13 if '"A"' in c.expr else 11 if "1/0" in c.expr else 6 if "70000" in c.expr else 5)),
    ("S$=LEFT$(S$,2) leaves S$ as it was", "LEFT$", "R-LEFT-ALIAS", lambda c: M.want(c) and M.source_kept(c)),
    ("S$=MID$(S$,...) leaves S$ as it was", "MID$", "R-MID-ALIAS", lambda c: M.want(c) and M.source_kept(c)),
    ("S$=LEFT$(S$,2) slices the NEW value (S$ cleared first: \"\")", "LEFT$", "R-LEFT-ALIAS",
     lambda c: M.result_is(c, b"")),
    ("the comparison ignores the result (always true)", "LEFT$", "R-LEFT-USE",
     lambda c: M.result_is(c, b"B") if "=CHR$" in c.expr else M.want(c)),
]


def main():
    cases = {fn: M.load(fn)["ref"] for fn in ("LEFT$", "RIGHT$", "MID$")}
    rules = {"LEFT$": LEFT, "RIGHT$": RIGHT, "MID$": MID}
    bad = 0
    for what, fn, rid, rival in CONTROLS:
        r = rule(rules[fn], rid)
        sel = [c for c in cases[fn] if r.select(c)]
        assert all(r.expect(c) for c in sel), rid
        false = [c.id for c in sel if not rival(c)]
        print(f"{rid:15s} {len(false):4d} of {len(sel):4d} FALSE  -- {what}"
              + (f"  (e.g. {false[0]})" if false else "  ** NO CASE SEPARATES IT **"))
        bad += not false
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
