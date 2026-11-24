#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""The shared model and rule builders for LET / SWAP's EXECUTABLE RULES (docs/spec-method.md §3a,
docs/keywords/spec-plan.md). The cases come from probes/basic/spec/klet.py's committed run (scratchpad/KLT_run1.out).

Each case's record -- ERR and the variables it names -- is PREDICTED from the rules and the statement: a number
stored into an integer by CINT's rule, into a single by CSNG's (kconv_model's models, measured on their pages), into a
double exactly; SWAP exchanging two variables of exactly the same type. A variable the case did not create reads 0
(or "") -- reading it creates it."""
import os
import sys
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
import kconv_model as C  # noqa: E402
import kmath_model as K  # noqa: E402
import klet  # noqa: E402
from spec_rules import Rule  # noqa: E402

FIELDS = ["e", "v1", "v2"]
OUTPUTS = {"FX": FIELDS}
OUTPUTS_DESC = "each case's ERR and the bytes of the (up to two) variables it names, read after it"
enc = K.enc
TV = K.text_value


def num(ty, v):
    return {"I": "%", "S": "!", "D": "#"}[ty], enc(v, ty), None


def store(ty, v, how="half-up", to_int="trunc"):
    """a value stored into a variable of type ty: (e, variable) -- CINT's / CSNG's rules"""
    if ty == "I":
        k = C.m_cint("D", enc(v, "D") if v else bytes(8), how=to_int)
        return (k[1], None) if k[0] == "err" else (0, ("%", k[2], None))
    if ty == "S":
        k = C.m_csng("D", enc(v, "D") if v else bytes(8), how=how)
        return (k[1], None) if k[0] == "err" else (0, ("!", k[2], None))
    return 0, num("D", v)


def s(text):
    return "$", text.encode()[:7], len(text)


ZERO = {"%": num("I", 0), "!": num("S", 0), "#": num("D", 0), "$": s("")}
D = lambda v: num("D", Fraction(v))   # noqa: E731


def expect(c, alt=frozenset()):
    """(e, v1, v2) the rules give for case c; `alt` names a control's rival"""
    w = c.why
    hu = "trunc" if "sng-trunc" in alt else "half-up"
    ti = "round" if "int-round" in alt else "trunc"
    lit = {"a single into an integer": ("I", "1.7"), "a negative single into an integer": ("I", "-1.7"),
           "2.5 into an integer": ("I", "2.5"), "32767.9 into an integer": ("I", "32767.9"),
           "-32768.9 into an integer": ("I", "-32768.9"), "32768 into an integer": ("I", "32768"),
           "1234567 into a single": ("S", "1234567"), "a double just below a tie into a single": ("S", "1.2345649999999"),
           "a tie into a single": ("S", "1.234565"), "a negative tie into a single": ("S", "-1.234565"),
           "a single into a double": ("D", "1.5"), "an integer into a plain (double) name": ("D", "7")}
    if w in lit:
        ty, t = lit[w]
        e, v = store(ty, TV(t), hu, ti)
        return e, v if v else ZERO[{"I": "%", "S": "!", "D": "#"}[ty]], None
    if w == "a double expression into a double":
        return 0, ("#", C.THIRD_D, None), None
    if w == "LET written out":
        return 0, D(5), None
    if w == "two names with the same first two characters":
        return 0, D(6), D(6)
    if w == "DEFINT decides a plain name's type":
        return store("I", TV("2.7"), hu, ti)[0], store("I", TV("2.7"), hu, ti)[1], None
    if w == "a string":
        return 0, s("ABC"), None
    if w in ("a string into a number (A new)",):
        return 13, ZERO["#"], None
    if w in ("a number into a string (A$ new)", "a number into a string array element"):
        return 13, ZERO["$"], None
    if w == "the right side's own error (A kept)":
        return 11, D(3), None
    if w == "the right side's own error (B new)":
        return 11, ZERO["#"], None
    if c.kw == "LET":                                   # the target or the statement malformed
        return 2, None, None
    # ---- SWAP ----
    ex = {"two doubles": (0, D(2), D(1)), "two integers": (0, num("I", -2), num("I", 1)),
          "two singles": (0, num("S", Fraction(-5, 2)), num("S", Fraction(3, 2))), "two strings": (0, s("YZ"), s("X")),
          "a variable with itself": (0, D(1), None),
          "string array elements": (0, s("QR"), s("P")),
          "string array elements, the other order": (0, s("QR"), s("P")),
          "string array elements, no SWAP (apparatus)": (0, s("P"), s("QR")),
          "strings after a later allocation": (0, s("X" * 20), s("AB")),
          "an array never DIMmed": (0, D(0), D(1)), "an array element": (0, D(5), D(1))}
    if w in ex:
        return ex[w]
    types = {"integer and single": (num("I", 1), num("S", Fraction(5, 2))),
             "single and double": (num("S", 1), D(2)), "integer and a plain (double) name": (num("I", 1), D(2)),
             "a number and a string": (D(1), s("X")),
             "DEFINT makes C an integer, D a double": (num("I", 1), D(2))}
    if w in types:
        if "types-convert" in alt and w != "a number and a string":
            return 0, None, None                        # a rival: no error -- cannot be stated in bytes; fails
        return (13,) + types[w]
    if w == "the first variable new":                   # A created, takes B's value; B gets A's 0
        return 0, D(1), D(0)
    if w in ("the second variable new", "a third, the second new"):
        if "second-new-ok" in alt:
            return 0, D(0), D(1)
        return 5, D(1), D(0)                            # B never created by SWAP: it reads 0
    if w == "a type mismatch, both new":
        return 13, D(0), s("")
    if w == "a subscript out of range":
        return 9, D(1), None
    after = ("an expression as the second", "a third variable", "an expression as the second, minus",
             "an expression as the second, times")
    if w in after:                                      # the exchange happens, THEN the rest is a Syntax error
        return (2, D(1), D(2)) if "error-first" in alt else (2, D(2), D(1))
    if w == "a parenthesis":
        return 2, D(1), D(2)
    if w in ("SWAP alone",):
        return 2, None, None
    if w in ("one variable", "a number as the second", "a number as the first"):
        return 2, D(1), None
    raise KeyError(w)


def ok(c, alt=frozenset()):
    e, v1, v2 = expect(c, alt)
    return (c.e, c.v1, c.v2) == (e, v1, v2)


def load(kw):
    cs = klet.load()
    return {who: [c for c in cs[who] if c.kw == kw] for who in cs}


def by(*whys):
    return lambda c: c.why in whys


def rules(kw):
    R = []
    if kw == "LET":
        s1, s2 = "1. Storing a number", "2. Names, types and errors"
        R += [
            Rule("R-LET-INT", s1, "A number stored into an integer variable is truncated toward zero, as CINT does: "
                 "A%=1.7 is 1, A%=-1.7 -1, A%=2.5 2, A%=32767.9 32767, A%=-32768.9 -32768; A%=32768 is error 6 "
                 "(Overflow) and A% (new) holds 0.",
                 by("a single into an integer", "a negative single into an integer", "2.5 into an integer",
                    "32767.9 into an integer", "-32768.9 into an integer", "32768 into an integer"), ok),
            Rule("R-LET-SNG", s1, "Into a single it is ROUNDED to 6 digits, half up by size, as CSNG does: A!=1234567 "
                 "is 1234570, A!=1.2345649999999# 1.23456, A!=1.234565# 1.23457, A!=-1.234565# -1.23457.",
                 by("1234567 into a single", "a double just below a tie into a single", "a tie into a single",
                    "a negative tie into a single"), ok),
            Rule("R-LET-DBL", s1, "Into a double it is stored exactly: A#=1.5! is 1.5 (the single's digits, eight zeros "
                 "added), A#=1/3 .33333333333333, a plain name A=7% the double 7.",
                 by("a single into a double", "a double expression into a double",
                    "an integer into a plain (double) name", "LET written out"), ok),
            Rule("R-LET-NAMES", s2, "A name counts by its first two characters (ZQ9 and ZQ7 are one variable); a plain "
                 "name is a double unless a DEF says otherwise for its first letter (after DEFINT D, D=2.7 stores the "
                 "integer 2); a string variable takes a string.",
                 by("two names with the same first two characters", "DEFINT decides a plain name's type",
                    "a string"), ok),
            Rule("R-LET-TYPE", s2, "A string into a number variable, or a number into a string variable (or element), "
                 "is error 13 (Type mismatch); the variable, created by then, holds 0 or \"\".",
                 by("a string into a number (A new)", "a number into a string (A$ new)",
                    "a number into a string array element"), ok),
            Rule("R-LET-RHS", s2, "When the right side raises an error (1/0: 11), nothing is stored: a variable that "
                 "existed keeps its value; a new one holds 0.",
                 by("the right side's own error (A kept)", "the right side's own error (B new)"), ok),
            Rule("R-LET-SYNTAX", s2, "LET alone, LET A with no `=`, and a target that is not a variable (5, \"A\", "
                 "TIME) are error 2 (Syntax error).",
                 by("a number as the target", "a string as the target", "TIME as LET's target", "LET alone",
                    "no `=`"), ok),
        ]
    else:
        s1, s2 = "1. The exchange", "2. Errors"
        R += [
            Rule("R-SWAP-EXCH", s1, "SWAP exchanges two variables of exactly the same type -- integer, single, double, "
                 "string, array elements (an array never DIMmed is created as DIM would) -- and a variable with "
                 "itself is unchanged; strings keep their text after later string allocations.",
                 by("two doubles", "two integers", "two singles", "two strings", "a variable with itself",
                    "string array elements", "string array elements, the other order",
                    "string array elements, no SWAP (apparatus)", "strings after a later allocation",
                    "an array never DIMmed", "an array element"), ok),
            Rule("R-SWAP-TYPES", s2, "Two different types -- integer and single, single and double, integer and a plain "
                 "name, a number and a string, an integer and a double by DEFINT -- are error 13 (Type mismatch); "
                 "nothing moves.",
                 by("integer and single", "single and double", "integer and a plain (double) name",
                    "a number and a string", "DEFINT makes C an integer, D a double"), ok),
            Rule("R-SWAP-NEW", s2, "The first variable may be new: it is created and takes the second's value, the "
                 "second gets 0. A second variable that does not exist is error 5 (Illegal function call) -- also "
                 "with a third after it -- and the first keeps its value; the second is not created (it reads 0). "
                 "Both new and of different types: error 13 first.",
                 by("the first variable new", "the second variable new", "a third, the second new",
                    "a type mismatch, both new"), ok),
            Rule("R-SWAP-SUBSCR", s2, "An array element out of range is error 9 (Subscript out of range); nothing moves.",
                 by("a subscript out of range"), ok),
            Rule("R-SWAP-SHAPE", s2, "SWAP alone, one variable, a number in either place, or a parenthesised first "
                 "variable are error 2 (Syntax error); nothing moves.",
                 by("SWAP alone", "one variable", "a number as the second", "a number as the first",
                    "a parenthesis"), ok),
            Rule("R-SWAP-AFTER", s2, "Anything after the second variable -- `,C`, `+0`, `-0`, `*1` -- is error 2, but "
                 "only AFTER the exchange: A and B have been swapped.",
                 by("a third variable", "an expression as the second", "an expression as the second, minus",
                    "an expression as the second, times"), ok),
        ]
    return R
