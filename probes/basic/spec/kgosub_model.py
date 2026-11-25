#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""The model and rule builders for GOTO / GOSUB / RETURN's EXECUTABLE RULES (docs/spec-method.md §3a,
docs/keywords/spec-plan.md region 5). The cases come from probes/basic/spec/kgosub.py's committed run
(scratchpad/KGS_run1.out). Each case's record -- the first and last error, WN% and WP% (the bits of the lines it
reached: 1 line n's own start, 2 the rest of line n after a GOSUB, 4 / 8 / 16 the case's target lines) -- is PREDICTED
from the rules; a control (kgosub_controls.py) replaces one rule with a rival and must be FALSE on some case."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
import kgosub  # noqa: E402
from spec_rules import Rule  # noqa: E402

FIELDS = ["e", "f", "n", "p"]
OUTPUTS = {"FX": FIELDS}
OUTPUTS_DESC = ("each case's first and last error, WN% (a counter; 21 = the probe's guard ended a loop that did not "
                "stop) and WP% (the bits of the lines the case reached)")
GUARD = 21

T = {
    "a forward GOTO skips the rest of the line": (0, 0, 0, 0b0101),
    "GOTO skips the lines between": (0, 0, 0, 0b1000),
    "a GOTO loop (the guard ends it)": (0, 0, GUARD, 0b0100),
    "a line that does not exist": (8, 8, 0, 0),
    "a line number past 65529": (8, 8, 0, 0),
    "no line number": (2, 2, 0, 0),
    "a variable as the line": (2, 2, 0, 0),
    "GO TO with a space": (0, 0, 0, 0b0100),
    "something after the line number": (8, 8, 0, 0),
    "GOSUB / RETURN comes back after the GOSUB": (0, 0, 0, 0b0110),
    "nested GOSUBs": (0, 0, 0, 0b11110),
    "recursion five deep, each level falling through to RETURN": (0, 0, 5, 0),
    "a subroutine without RETURN (runs on into the record)": (0, 0, 0, 0b0100),
    "unbounded recursion (the guard ends it)": (0, 0, GUARD, 0),
    "RETURN without GOSUB": (3, 3, 0, 0),
    "RETURN with a line number": (0, 0, 0, 0b1100),
    "RETURN to a line that does not exist": (8, 8, 0, 0b0100),
    "statements after RETURN": (0, 0, 0, 0b0110),
    "a second RETURN once the GOSUB came back": (3, 3, 0, 0b0010),
    "GOSUB inside FOR": (0, 0, 2, 0),
    "RETURN from inside a FOR in the subroutine, then NEXT": (1, 1, 1, 0b0010),
    "a whole FOR inside the subroutine": (0, 0, 3, 0b0010),
    "NEXT inside the subroutine for a FOR outside it": (1, 1, 1, 0),
    "a GOTO inside a subroutine, RETURN from elsewhere": (0, 0, 0, 0b1110),
    "GO SUB with a space": (2, 2, 0, 0b0010),
    "GO TO with two spaces": (2, 2, 0, 0),
    "GO TO after THEN": (0, 0, 0, 0b0100),
    "GO alone": (2, 2, 0, 0),
}


def expect(c, alt=frozenset()):
    """(e, f, n, p) the rules give for case c; `alt` names a control's rival"""
    w = c.why
    if w in ("GO TO with a space", "GO TO after THEN") and "no-goto-space" in alt:
        return 2, 2, 0, (0 if w == "GO TO after THEN" else 0)
    if w == "RETURN from inside a FOR in the subroutine, then NEXT" and "return-keeps-for" in alt:
        return 0, 0, 3, 0b0010
    if w == "NEXT inside the subroutine for a FOR outside it" and "next-crosses-gosub" in alt:
        return 0, 0, 2, 0
    if w == "a line number past 65529" and "big-line-syntax" in alt:
        return 2, 2, 0, 0
    if w == "RETURN with a line number" and "return-line-ignored" in alt:
        return 0, 0, 0, 0b0110
    if w == "something after the line number" and "trailing-syntax" in alt:
        return 2, 2, 0, 0
    return T[w]


def ok(c, alt=frozenset()):
    return (c.e, c.f, c.n, c.p) == expect(c, alt)


def load(kw):
    out = kgosub.load()
    return {who: [c for c in cs if c.kw == kw] for who, cs in out.items()}


def by(*whys):
    return lambda c: c.why in whys


def rules(kw):
    if kw == "GOTO":
        s1, s2 = "1. The jump", "2. Errors"
        return [
            Rule("R-GOTO-JUMP", s1, "GOTO n continues at line n: the rest of its own line and every line in between "
                 "are skipped; a GOTO back to its own line loops; a GOTO inside a subroutine leaves the GOSUB pending, "
                 "so a RETURN on the line it reaches comes back after the GOSUB.",
                 by("a forward GOTO skips the rest of the line", "GOTO skips the lines between",
                    "a GOTO loop (the guard ends it)", "a GOTO inside a subroutine, RETURN from elsewhere"), ok),
            Rule("R-GOTO-GOTO", s1, "`GO TO` written with exactly ONE space is GOTO -- also after THEN; two spaces, or "
                 "`GO` alone, are error 2 (Syntax error).",
                 by("GO TO with a space", "GO TO after THEN", "GO TO with two spaces", "GO alone"), ok),
            Rule("R-GOTO-ERRORS", s2, "A line that does not exist is error 8 (Undefined line number) -- also a number "
                 "past 65529 and a number followed by more text (`GOTO n 7`, read as one number); no number, or a "
                 "variable, is error 2.",
                 by("a line that does not exist", "a line number past 65529", "something after the line number",
                    "no line number", "a variable as the line"), ok),
        ]
    if kw == "GOSUB":
        s1, s2 = "1. The call", "2. Errors"
        return [
            Rule("R-GOSUB-CALL", s1, "GOSUB n runs line n on; RETURN continues after the GOSUB, on its own line. "
                 "GOSUBs nest and recurse (five deep, each level falling through to the RETURN); recursion without "
                 "a RETURN runs on (the guard stopped it at 21 levels, no error). A subroutine without RETURN simply "
                 "runs on.",
                 by("GOSUB / RETURN comes back after the GOSUB", "nested GOSUBs",
                    "recursion five deep, each level falling through to RETURN",
                    "a subroutine without RETURN (runs on into the record)", "unbounded recursion (the guard ends it)"),
                 ok),
            Rule("R-GOSUB-ERRORS", s2, "A line that does not exist is error 8; no line number error 2; `GO SUB` with a "
                 "space is error 2 (only GO TO has a spelled-out form).",
                 by("a line that does not exist", "no line number", "GO SUB with a space"), ok),
        ]
    s1, s2 = "1. Coming back", "2. Errors"
    return [
        Rule("R-RETURN-BACK", s1, "RETURN continues after its GOSUB; the rest of RETURN's own line is not run. RETURN n "
             "continues at line n instead, dropping the GOSUB. A GOSUB inside a FOR returns into the loop, which "
             "goes on (2 runs); a whole FOR inside the subroutine runs before RETURN (3 runs).",
             by("RETURN with a line number", "statements after RETURN", "GOSUB inside FOR",
                "a whole FOR inside the subroutine"), ok),
        Rule("R-RETURN-FRAMES", s1, "RETURN drops every FOR frame opened since its GOSUB: a NEXT after it is error 1 "
             "(NEXT without FOR); and a NEXT inside a subroutine does not reach a FOR opened before the GOSUB "
             "(error 1).",
             by("RETURN from inside a FOR in the subroutine, then NEXT",
                "NEXT inside the subroutine for a FOR outside it"), ok),
        Rule("R-RETURN-ERRORS", s2, "RETURN with no GOSUB pending is error 3 (RETURN without GOSUB) -- also a second "
             "RETURN once the GOSUB came back; RETURN n to a line that does not exist is error 8.",
             by("RETURN without GOSUB", "a second RETURN once the GOSUB came back",
                "RETURN to a line that does not exist"), ok),
    ]
