#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""The rule builders for NEW / LIST / DELETE / RENUM's EXECUTABLE RULES (docs/spec-method.md §3a,
docs/keywords/spec-plan.md region 7). The cases come from probes/basic/spec/klist.py's committed run
(scratchpad/KNL_run1.out): each case's normalised SCREEN. The model is kstop_model.py's small BASIC, the one interpreter
for every screen-reading keyword probe (range() / spell() / renum() hold the laws the rules state; its output wraps at
the line width, 37, as a listed line does)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import klist  # noqa: E402
import kstop_model as K  # noqa: E402
from kstop_model import Rule  # noqa: E402

FIELDS = K.FIELDS
OUTPUTS = {"FX": FIELDS}
OUTPUTS_DESC = K.OUTPUTS_DESC
run = K.run
ok = K.ok


def load(kw):
    out = klist.load()
    return {who: [c for c in cs if c.kw == kw] for who, cs in out.items()}


def by(*whys):
    return lambda c: c.why in whys


def rules(kw):
    if kw == "NEW":
        return [
            Rule("R-NEW-ERASE", "1. Erasing", "NEW erases the program and the variables and switches ON ERROR off; the "
                 "string-space size stays. Inside a running program it erases the program and stops, with no error.",
                 by("NEW erases the program", "NEW clears the variables", "NEW keeps the string space",
                    "NEW inside a program stops it", "NEW switches ON ERROR off"), ok),
            Rule("R-NEW-ERRORS", "2. Errors", "Anything after NEW is error 2, and then nothing is erased.",
                 by("something after NEW erases nothing"), ok),
        ]
    if kw == "LIST":
        return [
            Rule("R-LIST-RANGE", "1. Which lines", "LIST n lists line n only; n-m every stored line from n to m (neither "
                 "end has to exist); n- to the end, -m from the start; a reversed range, a missing line or an empty "
                 "program list nothing, with no error. `.` is the last line LIST printed.",
                 by("LIST n", "a range whose ends do not exist", "a range open at the top", "a range open at the bottom",
                    "a reversed range", "a line that is not there", "LIST . after a LIST", "LIST with no program"), ok),
            Rule("R-LIST-STOP", "1. Which lines", "LIST ends its line, and a running program (with no error); it is "
                 "not a program edit: the variables and the CONT point survive it.",
                 by("LIST ends the line", "LIST keeps the variables and CONT", "LIST inside a program stops it"), ok),
            Rule("R-LIST-SPELL", "2. The text", "A constant with a fraction or an exponent is listed in the machine's "
                 "own spelling, not as typed: 0.5 as .5, 1.5D3 as 1500#, 0.123456789 as .123456789# (more than six "
                 "digits is double).", by("numbers listed in the machine's spelling"), ok),
            Rule("R-LIST-ERRORS", "3. Errors", "A comma is not a separator: LIST 10,30 is error 2.", by("a comma"), ok),
        ]
    if kw == "DELETE":
        return [
            Rule("R-DELETE-RANGE", "1. Which lines", "DELETE n deletes line n; n-m every stored line from n to m -- the "
                 "LOW end need not exist; -m from the start.",
                 by("DELETE n", "a low end that does not exist", "a range open at the bottom"), ok),
            Rule("R-DELETE-CHECK", "2. Errors", "The HIGH end must be a stored line, the range must not be reversed, "
                 "and there must be a range: else error 5 (Illegal function call) -- checked before anything is deleted, "
                 "so nothing is. A comma is error 2.",
                 by("a high end that does not exist", "a range open at the top", "DELETE alone", "a reversed range",
                    "a comma"), ok),
            Rule("R-DELETE-EDIT", "3. An edit", "A DELETE that succeeds is a program edit: the variables go and CONT is "
                 "`Can't CONTINUE`; it ends its line.",
                 by("DELETE is an edit: no CONT", "DELETE is an edit: the variables go", "DELETE ends the line"), ok),
        ]
    return [
        Rule("R-RENUM-NUMBERS", "1. The new numbers", "RENUM makes the lines 10, 20, ...; RENUM n starts at n; RENUM "
             "n,old renumbers only from the old line `old` on; an absent new start is 10, also in the comma forms "
             "(RENUM ,,5: 10, 15).",
             by("RENUM", "RENUM n", "RENUM n,old", "RENUM ,,inc starts at 10"), ok),
        Rule("R-RENUM-REFS", "2. References", "Every line reference is rewritten -- GOTO, GOSUB, RESTORE, every number of "
             "an ON ... GOTO list -- but not a number inside a string or a REM. A reference to a missing line is "
             "reported (`Undefined line 77 in 5`: the target, then its line's OLD number), left as it is, and the "
             "renumbering goes on: no error.",
             by("a reference to a missing line", "references rewritten, text left alone"), ok),
        Rule("R-RENUM-CHECK", "3. Errors", "An increment of 0, or new numbers that would not stay above the lines left "
             "alone, is error 5, and nothing changes.", by("an increment of 0", "lines that would overlap"), ok),
        Rule("R-RENUM-KEEPS", "3. Errors", "RENUM is not an edit of the variables: they and the CONT point survive "
             "it (CONT goes on in the renumbered line).", by("RENUM keeps the variables and CONT"), ok),
    ]
