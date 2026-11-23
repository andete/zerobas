#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""The shared model and rule builders for LEFT$ / RIGHT$ / MID$ (the function)'s EXECUTABLE RULES
(docs/spec-method.md §3a, docs/keywords/spec-plan.md). The cases come from probes/basic/spec/kslice.py's committed run
(scratchpad/KSL_run1.out); each page's module takes its own keyword's cases from `load(fn)`."""
import math
import os
import sys
from types import SimpleNamespace as NS

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
import kslice  # noqa: E402
from spec_rules import Rule  # noqa: E402

FIELDS = ["e", "rl", "fb", "lb", "s", "w", "sl", "ss"]
OUTPUTS = {"LR": FIELDS, "MID": FIELDS, "FX": FIELDS}
OUTPUTS_DESC = "each case's error, the result's length, first and last byte and two checksums, the source's length and sum"
SENTINEL = bytes([250])          # R$ before every case: an error leaves it


def load(fn):
    """this keyword's cases: the matrix group's and the fixed expressions', the reference's and zerobas's in the same
    order"""
    out = {"ref": [], "zb": []}
    for g in ("MID",) if fn == "MID$" else ("LR",):
        cs = kslice.load(g)
        for who in out:
            out[who] += [c for c in cs[who] if c.fn == fn]
    cs = kslice.load("FX")
    for who in out:
        out[who] += [c for c in cs[who] if c.fn == fn]
    return out


def source(c):
    """the source string's bytes: CHR$(1) .. CHR$(L) (the matrix); CHR$(1..5) for a fixed expression"""
    return bytes(range(1, (c.l if c.src != "FX" else 5) + 1))


def digest(b):
    """(RL, FB, LB, S, W) as the probe records them for the string b"""
    if not b:
        return 0, 0, 0, 0, 0
    return len(b), b[0], b[-1], sum(b) & 0xFFFF, sum((k + 1) * x for k, x in enumerate(b)) & 0xFFFF


def result_is(c, b):
    """the case recorded no error and the string b as the result"""
    return c.e == 0 and (c.rl, c.fb, c.lb, c.s, c.w) == digest(b)


def error_is(c, code):
    """the case raised `code` and the result was never assigned (R$ still holds the sentinel)"""
    return c.e == code and (c.rl, c.fb, c.lb, c.s, c.w) == digest(SENTINEL)


def source_kept(c):
    return (c.sl, c.ss) == (len(source(c)), sum(source(c)) & 0xFFFF)


def arg(v):
    """an argument's outcome: (error, value) -- the value truncated toward zero, then 6 outside the 16-bit signed
    range, else 5 outside 0..255"""
    t = math.trunc(v)
    if t < -32768 or t > 32767:
        return 6, None
    if t < 0 or t > 255:
        return 5, None
    return 0, t


def pos(v):
    """MID$'s position: as `arg`, but 1..255"""
    t = math.trunc(v)
    if t < -32768 or t > 32767:
        return 6, None
    if t < 1 or t > 255:
        return 5, None
    return 0, t


def mid(c):
    """(error, result) of MID$(S$,P[,M]) for a matrix case"""
    e, p = pos(c.p)
    if e:
        return e, None
    m = None
    if c.m is not None:
        e, m = arg(c.m)
        if e:
            return e, None
    s = source(c)
    return 0, s[p - 1:] if m is None else s[p - 1:p - 1 + m]


def lr(c, fn):
    """(error, result) of LEFT$ / RIGHT$ (fn: the RULE's keyword, never the case's own label)"""
    e, n = arg(c.n)
    if e:
        return e, None
    s = source(c)
    return 0, (s[:n] if fn == "LEFT$" else s[len(s) - min(n, len(s)):])


def outcome(c, model):
    e, b = model(c)
    return error_is(c, e) if e else result_is(c, b)


def M(c):
    return c.src != "FX"


def fx(*idx):
    want = {f"KS FX {i}" for i in idx}
    return lambda c: c.id in want


def fx_by(c, *whys):
    return c.src == "FX" and c.why in whys


def lr_rules(fn, tag, section):
    """LEFT$ / RIGHT$: the same rules, mirrored"""
    first = "first" if fn == "LEFT$" else "last"
    model = lambda c: lr(c, fn)  # noqa: E731
    plain = {"LEFT$": "LEFT$(S$,2)", "RIGHT$": "RIGHT$(S$,2)"}[fn]
    want = {"LEFT$": bytes([1, 2]), "RIGHT$": bytes([4, 5])}[fn]
    return [
        Rule(f"R-{tag}-SLICE", section,
             f"The count is truncated toward zero; from 0 to 255 the result is the {first} min(count, LEN(a$)) "
             f"characters of a$, in order: 0 gives \"\", a count past the end the whole string. (.9 gives \"\" and "
             f"1.5 one character: truncation, not rounding.)",
             lambda c: M(c) and arg(c.n)[0] == 0, lambda c: outcome(c, model)),
        Rule(f"R-{tag}-ERR5", section,
             "A truncated count from -32768 to -1, or from 256 to 32767, is error 5 (Illegal function call), and "
             "nothing is assigned. -32768.5 and 32767.9 are 5: the count is truncated BEFORE the range test.",
             lambda c: M(c) and arg(c.n)[0] == 5, lambda c: outcome(c, model)),
        Rule(f"R-{tag}-ERR6", section,
             "A truncated count below -32768 or above 32767 is error 6 (Overflow), and nothing is assigned.",
             lambda c: M(c) and arg(c.n)[0] == 6, lambda c: outcome(c, model)),
        Rule(f"R-{tag}-SRC", section, "The source string is left as it was, in every case, error or not.",
             lambda c: True, source_kept),
        Rule(f"R-{tag}-TYPE", section,
             "A number as the string, or a string as the count, is error 13 (Type mismatch); the types are checked "
             "before the count's range or overflow (a number as the string with count -1 or 70000 is still 13).",
             lambda c: fx_by(c, "a number as the string", "a string as the count",
                             "the type before the count's range", "the type before the count's overflow"),
             lambda c: error_is(c, 13)),
        Rule(f"R-{tag}-OWNERR", section,
             "An argument that fails to compute raises its own error (1/0 as either argument: error 11).",
             lambda c: fx_by(c, "the count's own error", "the string argument's own error"),
             lambda c: error_is(c, 11)),
        Rule(f"R-{tag}-SYNTAX", section,
             "A missing count, no argument at all, or a third argument is error 2 (Syntax error).",
             lambda c: fx_by(c, "no count", "no argument", "an extra argument"), lambda c: error_is(c, 2)),
        Rule(f"R-{tag}-FORMS", section,
             "A space before the parenthesis and spaces around the arguments are allowed"
             + (", and so are an integer (`2%`) or hex (`&H2`) count" if fn == "LEFT$" else "")
             + f": each gives what {plain} gives.",
             lambda c: fx_by(c, "a space before the parenthesis", "spaces around the arguments", "an integer count",
                             "a hex count"), lambda c: result_is(c, want)),
        Rule(f"R-{tag}-EXPR", section,
             f"The string may be any string expression: a concatenation (S$+S$, 7) and the function nested in itself "
             f"(4, then 2) give the {first} characters of the expression's value.",
             lambda c: fx_by(c, "an expression as the string", "nested"),
             lambda c: result_is(c, (bytes(range(1, 6)) * 2)[:7] if fn == "LEFT$" and "+" in c.expr else
                                 (bytes(range(1, 6)) * 2)[-7:] if "+" in c.expr else want)),
    ]


def mid_rules(section):
    return [
        Rule("R-MID-SLICE", section,
             "The position P and the count M are truncated toward zero. With P from 1 to 255 and M from 0 to 255 the "
             "result is the M characters of a$ from position P (counting from 1), or the rest of a$ when fewer are "
             "left; a position past the end gives \"\".",
             lambda c: M(c) and c.m is not None and mid(c)[0] == 0, lambda c: outcome(c, mid)),
        Rule("R-MID-REST", section,
             "Without a count, MID$(a$,P) is everything from position P to the end (\"\" past the end).",
             lambda c: M(c) and c.m is None and mid(c)[0] == 0, lambda c: outcome(c, mid)),
        Rule("R-MID-POS", section,
             "The position is checked first, completely: truncated, below -32768 or above 32767 is error 6, otherwise "
             "outside 1 to 255 is error 5, whatever the count is (MID$(S$,0,32768) is 5, MID$(S$,70000,-1) is 6). "
             "Position 0 is an error; position 255 is not, at any length.",
             lambda c: M(c) and pos(c.p)[0] != 0, lambda c: outcome(c, mid)),
        Rule("R-MID-COUNT", section,
             "With a valid position, the count is checked as LEFT$'s: truncated, error 6 outside -32768 to 32767, "
             "else error 5 outside 0 to 255. Nothing is assigned on an error.",
             lambda c: M(c) and pos(c.p)[0] == 0 and c.m is not None and arg(c.m)[0] != 0,
             lambda c: outcome(c, mid)),
        Rule("R-MID-SRC", section, "The source string is left as it was, in every case, error or not.",
             lambda c: True, source_kept),
        Rule("R-MID-TYPE", section,
             "A number as the string, or a string as the position or the count, is error 13 -- the string's type is "
             "checked before the position's range (MID$(5,0) is 13).",
             lambda c: fx_by(c, "a number as the string", "a string as the position", "a string as the count",
                             "the type before the position's range"), lambda c: error_is(c, 13)),
        Rule("R-MID-ORDER", section,
             "The position is checked before the count is even evaluated: a bad position wins over a count of the "
             "wrong type and over a count that fails to compute (MID$(S$,0,\"A\") and MID$(S$,0,1/0) are 5, "
             "MID$(S$,70000,\"A\") and MID$(S$,-32769,1) are 6).",
             lambda c: fx_by(c, "the position's range before the count's type",
                             "the position's overflow before the count's type",
                             "the position's range before the count's own error", "a position below -32768"),
             lambda c: error_is(c, 6 if ("70000" in c.expr or "32769" in c.expr) else 5)),
        Rule("R-MID-OWNERR", section,
             "A position or count that fails to compute raises its own error (1/0: error 11).",
             lambda c: fx_by(c, "the position's own error", "the count's own error"), lambda c: error_is(c, 11)),
        Rule("R-MID-SYNTAX", section,
             "No position, no argument at all, or a fourth argument is error 2 (Syntax error).",
             lambda c: fx_by(c, "no position", "no argument", "an extra argument"), lambda c: error_is(c, 2)),
        Rule("R-MID-FORMS", section,
             "Spaces before the parenthesis and around the arguments are allowed (MID$ (S$,2,2) is characters 2-3), "
             "and the string may be an expression (MID$(S$+S$,4,4) is characters 4-7 of the ten).",
             lambda c: fx_by(c, "a space before the parenthesis", "spaces around the arguments",
                             "an expression as the string"),
             lambda c: result_is(c, (bytes(range(1, 6)) * 2)[3:7] if "+" in c.expr else bytes([2, 3]))),
    ]
