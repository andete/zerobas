#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""The model and rule builders for FOR / NEXT's EXECUTABLE RULES (docs/spec-method.md §3a, docs/keywords/spec-plan.md
region 5). The cases come from probes/basic/spec/kfor.py's committed run (scratchpad/KFR_run1.out). Each case's record
-- the first error, the last error, the body's runs (WN%) and the loop variable -- is PREDICTED from the rules below and
the case; a control (kfor_controls.py) replaces one rule with a rival and must be FALSE on some case.

The loop, as the rules state it: FOR stores the start in the variable (an integer variable TRUNCATES start and limit
-- and STEP, so .5 is 0), evaluates the limit and STEP ONCE, and pushes a frame; the body runs (at least once); NEXT
adds STEP and loops while the variable has not passed the limit in STEP's direction -- STEP 0 loops for ever. A FOR
that fails pushes NO frame, so the NEXT that RESUME NEXT then reaches is NEXT without FOR (1)."""
import os
import sys
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
import kfor  # noqa: E402
import kmath_model as K  # noqa: E402
from spec_rules import Rule  # noqa: E402

FIELDS = ["e", "f", "n", "v"]
OUTPUTS = {"FX": FIELDS}
OUTPUTS_DESC = ("each case's first and last error, the body's runs (WN%, 21 = the probe's guard ended a loop that "
                "did not stop) and the loop variable's bytes after it")
GUARD = 21


def D(v):
    return "#", K.enc(Fraction(v), "D")


def S(v):
    return "!", K.enc(Fraction(v), "S")


def I(v):                               # noqa: E743
    return "%", K.enc(Fraction(v), "I")


ZERO = D(0)


def expect(c, alt=frozenset()):
    """(e, f, n, v) the rules give for case c; `alt` names a control's rival"""
    w = c.why
    t = {
        "three runs": (0, 0, 3, D(4)),
        "start = limit": (0, 0, 1, D(2)),
        "a negative step": (0, 0, 3, ZERO),
        "a fractional step (double)": (0, 0, 11, D(Fraction(11, 10))),
        "a fractional step (single)": (0, 0, 11, S(Fraction(11, 10))),
        "a fractional step (double literal)": (0, 0, 11, D(Fraction(11, 10))),
        "an integer variable": (0, 0, 3, I(4)),
        "the variable changed in the body": (0, 0, 1, D(6)),
        "nested, NEXT J,I": (0, 0, 6, D(4)),
        "nested, two bare NEXTs": (0, 0, 6, D(3)),
        "the same variable twice": (0, 0, 3, D(4)),
        "no NEXT": (0, 0, 0, D(1)),
    }
    if w in t:
        return t[w]
    if w == "start past the limit":             # the body runs ONCE, then NEXT's test ends it
        return (0, 0, 0, D(3)) if "skip-past" in alt else (0, 0, 1, D(4))
    if w == "a negative step, start below":
        return (0, 0, 0, D(1)) if "skip-past" in alt else (0, 0, 1, ZERO)
    if w == "STEP 0":
        return 0, 0, GUARD, D(1)
    if w == "STEP 0, start past the limit":
        return (0, 0, 1, D(3)) if "step0-past-ends" in alt else (0, 0, GUARD, D(3))
    if w == "an integer variable up to 32767":  # NEXT's 32767 + 1 overflows; the variable keeps 32767
        return 6, 6, 3, I(32767)
    if w == "an integer variable down to -32768":
        return 6, 6, 3, I(-32768)
    if w == "an integer variable, STEP .5":     # STEP truncated to 0 for an integer variable: no end
        return (0, 0, 5, I(3)) if "int-step-kept" in alt else (0, 0, GUARD, I(1))
    if w == "an integer variable, a fractional limit":
        return (0, 0, 4, I(5)) if "int-round" in alt else (0, 0, 3, I(4))
    if w == "an integer variable, a fractional start":
        return (0, 0, 2, I(4)) if "int-round" in alt else (0, 0, 3, I(4))
    if w == "an integer variable, a limit past 32767":   # Overflow AT the FOR: no frame, so NEXT is error 1
        return 6, 1, 1, I(1)
    if w == "the limit changed in the body":
        return (0, 0, 1, D(2)) if "limit-live" in alt else (0, 0, 3, D(4))
    if w == "the step changed in the body":
        return (0, 0, 3, D(7)) if "step-live" in alt else (0, 0, 5, D(6))
    if w == "NEXT I inside FOR J":              # NEXT I drops J's frame: I's loop runs, J's body once per I
        return 0, 0, 2, D(3)
    # ---- errors: a failed FOR pushes no frame, so the NEXT after RESUME NEXT is error 1 (the LAST error) ----
    nofr = "frame-kept" not in alt
    if w == "a string variable":
        return 13, 1, 1, None
    if w == "a string limit":
        return (13, 1, 1, D(1)) if nofr else (13, 13, 1, D(2))
    if w == "a string step":
        return (13, 1, 1, D(1)) if nofr else (13, 13, GUARD, D(1))
    if w == "STEP with nothing":
        return (24, 1, 1, D(1)) if nofr else (24, 24, GUARD, D(1))
    if w == "the start's own error":
        return 11, 1, 1, ZERO
    if w == "the limit's own error":
        return 11, 1, 1, D(1)
    if w == "no TO":
        return 2, 2, 0, D(1)
    if w == "nothing after TO":
        return 24, 24, 0, D(1)
    if w == "no `=`":
        return 2, 2, 0, ZERO
    if w == "a number as the variable":
        return 2, 2, 0, None
    if w == "an array element as the variable":
        return 2, 1, 1, None
    # ---- NEXT ----
    if w == "NEXT without FOR":
        return 1, 1, 0, None
    if w == "NEXT I without FOR":               # the failing NEXT I creates I (it reads 0)
        return (1, 1, 0, "none") if "next-no-create" in alt else (1, 1, 0, ZERO)
    if w == "NEXT J inside FOR I":
        return 1, 1, 1, D(1)
    if w == "a trailing comma":                 # the loop runs out, then the missing name: NEXT without FOR
        return 1, 1, 2, D(3)
    if w == "a number after NEXT":
        return 2, 2, 1, D(1)
    if w == "two names without a comma":
        return 1, 1, 1, D(1)
    if w == "a third name past the frames":
        return 1, 1, 4, D(3)
    raise KeyError(w)


def ok(c, alt=frozenset()):
    return (c.e, c.f, c.n, c.v) == expect(c, alt)


def load(kw):
    out = kfor.load()
    return {who: [c for c in cs if c.kw == kw] for who, cs in out.items()}


def by(*whys):
    return lambda c: c.why in whys


def rules(kw):
    if kw == "FOR":
        s1, s2, s3 = "1. The loop", "2. An integer loop variable", "3. Errors"
        return [
            Rule("R-FOR-RUNS", s1, "FOR stores the start in the variable and the body runs AT LEAST ONCE; NEXT adds STEP "
                 "(default 1) and runs the body again while the variable has not passed the limit in STEP's direction. "
                 "FOR I=1 TO 3 runs 3 times and leaves I 4; FOR I=1 TO 1 once (I 2); FOR I=3 TO 1 once (I 4); "
                 "FOR I=3 TO 1 STEP -1 3 times (I 0); FOR I=1 TO 3 STEP -1 once (I 0).",
                 by("three runs", "start = limit", "start past the limit", "a negative step",
                    "a negative step, start below"), ok),
            Rule("R-FOR-FRACTION", s1, "A fractional STEP adds in the variable's own type: FOR I=0 TO 1 STEP .1 runs 11 "
                 "times and ends at 1.1, for a double, a single or a double literal step alike.",
                 by("a fractional step (double)", "a fractional step (single)", "a fractional step (double literal)"),
                 ok),
            Rule("R-FOR-STEP0", s1, "STEP 0 never ends -- also when the start is already past the limit (FOR I=3 TO 1 "
                 "STEP 0); the probe's guard stops both.",
                 by("STEP 0", "STEP 0, start past the limit"), ok),
            Rule("R-FOR-ONCE", s1, "The limit and STEP are evaluated once, at FOR: changing L or S in the body changes "
                 "nothing (FOR I=1 TO L with L=1 in the body still runs 3 times; STEP S with S=2 still steps 1, 5 runs). "
                 "Changing the VARIABLE does count: I=5 in the body ends the loop after one run with I 6.",
                 by("the limit changed in the body", "the step changed in the body",
                    "the variable changed in the body"), ok),
            Rule("R-FOR-NEST", s1, "Loops nest: FOR I / FOR J closed by NEXT J,I or by two bare NEXTs run 6 bodies; a "
                 "second FOR on the same variable replaces the first's frame (3 runs, not 6); a FOR without NEXT is no "
                 "error (the body runs 0 times after it: the line ends).",
                 by("nested, NEXT J,I", "nested, two bare NEXTs", "the same variable twice", "no NEXT"), ok),
            Rule("R-FOR-INT", s2, "An integer variable TRUNCATES the start, the limit and the step: FOR I%=1.6 TO 3 and "
                 "FOR I%=1 TO 3.7 both run 3 times (I% 4); STEP .5 is 0 and never ends. FOR I%=1 TO 3 leaves I% 4.",
                 by("an integer variable", "an integer variable, a fractional start",
                    "an integer variable, a fractional limit", "an integer variable, STEP .5"), ok),
            Rule("R-FOR-OVERFLOW", s2, "Stepping an integer variable past 32767 or below -32768 is error 6 (Overflow) "
                 "at NEXT, the variable keeping its last value (3 runs: I% 32767, or -32768); a LIMIT an integer "
                 "variable cannot hold is error 6 at the FOR itself (FOR I%=1 TO 40000), and no frame is pushed.",
                 by("an integer variable up to 32767", "an integer variable down to -32768",
                    "an integer variable, a limit past 32767"), ok),
            Rule("R-FOR-ERRORS", s3, "A string variable, limit or STEP is error 13 (Type mismatch); no TO, no `=`, a "
                 "number or an array element as the variable error 2 (Syntax error); nothing after TO or after STEP "
                 "error 24 (Missing operand); an error in the start or the limit is that error (1/0: 11). A shape error ends the "
                 "line there (no body runs); the others leave the line running on (R-FOR-NOFRAME).",
                 by("a string variable", "a string limit", "a string step", "no TO", "nothing after TO", "no `=`",
                    "a number as the variable", "an array element as the variable", "STEP with nothing",
                    "the start's own error", "the limit's own error"),
                 ok),
            Rule("R-FOR-NOFRAME", s3, "A FOR that fails pushes NO frame: after RESUME NEXT the body runs once and its "
                 "NEXT is error 1 (NEXT without FOR), the variable as the failed FOR left it.",
                 by("a string variable", "a string limit", "a string step", "STEP with nothing",
                    "the start's own error", "the limit's own error", "an array element as the variable",
                    "an integer variable, a limit past 32767"), ok),
        ]
    s1, s2 = "1. Closing loops", "2. Errors"
    return [
        Rule("R-NEXT-CLOSE", s1, "NEXT I inside FOR J closes I's loop and drops J's frame: 2 bodies, I 3.",
             by("NEXT I inside FOR J"), ok),
        Rule("R-NEXT-ERRORS", s2, "NEXT without a FOR and NEXT J inside FOR I are error 1 (NEXT "
             "without FOR); a name after the loops ran out -- a trailing comma, a third name (NEXT J,I,K) -- is error 1 "
             "once those loops have finished; two names without a comma error 1 at once; a number after NEXT error 2. The "
             "loop variable is as the loops left it (NEXT J inside FOR I: I 1, its frame unused).",
             by("NEXT without FOR", "NEXT J inside FOR I", "a trailing comma",
                "a third name past the frames", "two names without a comma", "a number after NEXT"),
             ok),
        Rule("R-NEXT-CREATE", s2, "NEXT I without a FOR is error 1 too, and it creates the variable I (it reads 0; "
             "VARPTR finds it).",
             by("NEXT I without FOR"), ok),
    ]
