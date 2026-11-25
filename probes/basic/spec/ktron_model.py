#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""The rule builders for TRON / TROFF / REM's EXECUTABLE RULES (docs/spec-method.md §3a, docs/keywords/spec-plan.md
region 6). The cases come from probes/basic/spec/ktron.py's committed run (scratchpad/KTN_run1.out): each case's
normalised SCREEN. The model is kstop_model.py's small BASIC, the one interpreter for every screen-reading keyword
probe: it prints `[n]` -- no new line of its own -- each time a program line is entered from its top (never for a
statement typed at the prompt), and reads a REM, or an apostrophe, as the rest of the line."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ktron  # noqa: E402
import kstop_model as K  # noqa: E402
from kstop_model import Rule  # noqa: E402

FIELDS = K.FIELDS
OUTPUTS = {"FX": FIELDS, "FY": FIELDS}
OUTPUTS_DESC = K.OUTPUTS_DESC
run = K.run
ok = K.ok


def load(kw):
    out = ktron.load()
    return {who: [c for c in cs if c.kw == kw] for who, cs in out.items()}


def by(*whys):
    return lambda c: c.why in whys


def rules(kw):
    if kw == "TRON":
        return [
            Rule("R-TRON-TRACE", "1. The trace", "With the trace on, each program line prints `[n]` -- its number, no "
                 "padding, NO new line of its own -- when it is entered from its top: by falling in, as a GOTO or GOSUB "
                 "target, each time a NEXT sends a loop back to it. Once per line, not per statement; going on in the "
                 "middle of a line prints nothing -- after a GOSUB's RETURN, a loop inside one line (`[10]AA`), CONT after "
                 "a STOP. A line is traced whenever it is entered at its first statement: by its own GOTO (`[10][10]`), "
                 "a RETURN that lands on a line start, an ON n GOTO or IF ... THEN n target, a typed GOTO, an error "
                 "handler's line; a REM line and an END line are traced too. An error message starts its own line.",
                 by("each line traced", "one trace per line", "a GOSUB target traced, its return not",
                    "a loop over two lines", "an END line is traced", "the trace has no new line of its own",
                    "a five-digit line", "a GOTO target traced", "a line that jumps to itself", "a loop inside one line",
                    "RETURN to the start of a line", "the trace through an error handler",
                    "CONT after STOP with the trace on", "a typed GOTO", "an ON n GOTO target",
                    "an IF ... THEN n target", "a REM line is traced", "an error message after the trace"), ok),
            Rule("R-TRON-ONOFF", "2. On and off", "TRON starts the trace at the NEXT line entered (the line holding it is "
                 "not traced); a statement typed at the prompt is never traced; the trace stays on through RUN, and NEW "
                 "switches it off. Anything after TRON is error 2.",
                 by("the TRON line itself is not traced", "a typed statement is not traced",
                    "the trace stays on through RUN", "NEW switches the trace off", "something after TRON"), ok),
        ]
    if kw == "TROFF":
        return [
            Rule("R-TROFF-OFF", "1. Switching off", "TROFF stops the trace after its own line -- that line was traced "
                 "before it ran -- and it stays off for the next RUN; typed, it stops it for the next RUN; with the trace "
                 "already off it does nothing. "
                 "Anything after TROFF is error 2.",
                 by("the TROFF line is still traced", "TROFF when the trace is off", "something after TROFF",
                    "a typed TROFF", "TROFF in a program, then RUN again"), ok),
        ]
    return [
        Rule("R-REM-LINE", "1. The rest of the line", "REM makes the rest of its line a comment, colons included -- and "
             "an ELSE, so `IF 0 THEN REM ELSE B=1` leaves B alone. The apostrophe is REM, and needs no colon before it "
             "(`PRINT \"C\" 'X`); REM itself does: `PRINT \"A\" REM X` prints A, then error 2. A REM line is an ordinary "
             "GOTO target; a typed REM does nothing. REM is a statement, not text: inside DATA it is data (`DATA X REM Y` "
             "reads `X REM Y`), inside a string an apostrophe is a character; after THEN an apostrophe is a comment, "
             "and after GOTO's line number a REM is never read. `PRINT \"A\",\"B\"` is no error (a comma moves to "
             "the next zone).",
             by("REM ends the line", "the apostrophe without a colon", "REM swallows an ELSE", "a colon inside a REM",
                "a GOTO to a REM line", "REM after a statement without a colon", "a typed REM",
                "the apostrophe after a colon", "REM inside DATA", "an apostrophe inside a string",
                "an apostrophe after THEN", "REM after a GOTO's line number", "REM swallows an ELSE (a sentinel 5)",
                "PRINT with a comma is no error"), ok),
    ]
