#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""The model and rule builders for IF's EXECUTABLE RULES (docs/spec-method.md §3a, docs/keywords/spec-plan.md
region 5). The cases come from probes/basic/spec/kif.py's committed run (scratchpad/KIF_run1.out). Each case's record
-- the first and last error, WN% and WP% (1 line n ran; 2 / 4 / 8 the parts the case marks) -- is PREDICTED from the
rules; a control (kif_controls.py) replaces one rule with a rival and must be FALSE on some case."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
import kif  # noqa: E402
from spec_rules import Rule  # noqa: E402

FIELDS = ["e", "f", "n", "p"]
OUTPUTS = {"FX": FIELDS}
OUTPUTS_DESC = "each case's first and last error, WN% (a counter) and WP% (the bits of the parts of the line that ran)"

T = {
    "a true IF runs THEN and the rest of the line": (0, 0, 0, 0b111),
    "a false IF skips THEN and the rest of the line": (0, 0, 0, 0b1),
    "-1 is true": (0, 0, 0, 0b11), "a fraction is true": (0, 0, 0, 0b11), "a tiny number is true": (0, 0, 0, 0b11),
    "a variable holding 0 is false": (0, 0, 0, 0b1),
    "THEN a line number": (0, 0, 0, 0b101), "THEN a line number, false": (0, 0, 0, 0b1),
    "IF ... GOTO": (0, 0, 0, 0b101), "IF ... GOTO, false (the rest of the line too)": (0, 0, 0, 0b1),
    "ELSE, true": (0, 0, 0, 0b11), "ELSE, false": (0, 0, 0, 0b101), "ELSE a line number": (0, 0, 0, 0b1001),
    "statements after ELSE's own": (0, 0, 0, 0b1101), "statements after ELSE, true": (0, 0, 0, 0b11),
    "ELSE after a nested IF (true, false)": (0, 0, 0, 0b101),
    "ELSE after a nested IF (false outside)": (0, 0, 0, 0b1),
    "two ELSEs: the second belongs to the outer IF": (0, 0, 0, 0b1001),
    "two ELSEs, both true": (0, 0, 0, 0b11),
    "a string comparison": (0, 0, 0, 0b11), "a string as the condition": (13, 13, 0, 0b1),
    "THEN followed by nothing": (0, 0, 0, 0b1), "no THEN": (2, 2, 0, 0b1), "no condition": (2, 2, 0, 0b1),
    "the condition's own error": (11, 11, 0, 0b101),
    "THEN a line that does not exist": (8, 8, 0, 0b1), "THEN a missing line, false": (0, 0, 0, 0b1),
    "THEN back to its own line": (0, 0, 3, 0b1),
    "NEXT after a true IF on the same line": (0, 0, 0, 0b1),
    "a false IF skips the NEXT behind it": (0, 0, 1, 0b1),
    "ELSE to a missing line, not taken": (0, 0, 0, 0b11), "THEN followed by a colon": (0, 0, 0, 0b11),
}


def expect(c, alt=frozenset()):
    w = c.why
    if "false-skips-then-only" in alt:          # rival: a false IF skips only THEN's statement
        r = {"a false IF skips THEN and the rest of the line": (0, 0, 0, 0b101),
             "IF ... GOTO, false (the rest of the line too)": (0, 0, 0, 0b11),
             "a false IF skips the NEXT behind it": (0, 0, 3, 0b1)}
        if w in r:
            return r[w]
    if "else-outer" in alt and w in ("ELSE after a nested IF (true, false)", "ELSE after a nested IF (false outside)"):
        return {"ELSE after a nested IF (true, false)": (0, 0, 0, 0b1),
                "ELSE after a nested IF (false outside)": (0, 0, 0, 0b101)}[w]
    if "fraction-false" in alt and w in ("a fraction is true", "a tiny number is true"):
        return 0, 0, 0, 0b1
    if "else-one-stmt" in alt and w == "statements after ELSE's own":
        return 0, 0, 0, 0b101
    if "then-empty-syntax" in alt and w == "THEN followed by nothing":
        return 2, 2, 0, 0b1
    return T[w]


def ok(c, alt=frozenset()):
    return (c.e, c.f, c.n, c.p) == expect(c, alt)


def load(kw):
    out = kif.load()
    return {who: [c for c in cs if c.kw == kw] for who, cs in out.items()}


def by(*whys):
    return lambda c: c.why in whys


def rules(kw):
    s1, s2, s3 = "1. Truth", "2. THEN, ELSE and the rest of the line", "3. Errors"
    return [
        Rule("R-IF-TRUTH", s1, "Any non-zero number is true -- -1, .5, 1E-30 -- and 0 (also a variable holding 0) "
             "false; a string comparison is a number like any other (\"A\"<\"B\" is true).",
             by("-1 is true", "a fraction is true", "a tiny number is true", "a variable holding 0 is false",
                "a string comparison"), ok),
        Rule("R-IF-LINE", s2, "A true IF runs THEN's statements AND the rest of the line; a false IF skips the WHOLE "
             "rest of the line -- every statement after it, a GOTO and a NEXT included (a loop on one line ends there).",
             by("a true IF runs THEN and the rest of the line", "a false IF skips THEN and the rest of the line",
                "IF ... GOTO, false (the rest of the line too)", "a false IF skips the NEXT behind it",
                "NEXT after a true IF on the same line"), ok),
        Rule("R-IF-JUMP", s2, "THEN n, and IF ... GOTO n, jump to line n when true (also back to the IF's own line); a "
             "missing line is only an error when the jump is taken (error 8).",
             by("THEN a line number", "THEN a line number, false", "IF ... GOTO", "THEN back to its own line",
                "THEN a line that does not exist", "THEN a missing line, false", "ELSE to a missing line, not taken"),
             ok),
        Rule("R-IF-ELSE", s2, "ELSE runs when the IF is false -- its statements and every statement after them on the "
             "line, or a jump to ELSE n -- and none of it when true. An ELSE belongs to the NEAREST unmatched IF: "
             "IF a THEN IF b THEN x ELSE y runs y only when a is true and b false, and a second ELSE belongs to the "
             "outer IF.",
             by("ELSE, true", "ELSE, false", "ELSE a line number", "statements after ELSE's own",
                "statements after ELSE, true", "ELSE after a nested IF (true, false)",
                "ELSE after a nested IF (false outside)", "two ELSEs: the second belongs to the outer IF",
                "two ELSEs, both true"), ok),
        Rule("R-IF-EMPTY", s2, "THEN followed by nothing, or by a colon, is no error.",
             by("THEN followed by nothing", "THEN followed by a colon"), ok),
        Rule("R-IF-ERRORS", s3, "A string as the condition is error 13 (Type mismatch); no THEN, or no condition, error "
             "2; the condition's own error is that error (1/0: 11), and RESUME NEXT then carries on after THEN's "
             "statement.",
             by("a string as the condition", "no THEN", "no condition", "the condition's own error"), ok),
    ]
