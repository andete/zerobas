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
OUTPUTS = {"FX": FIELDS}
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
                 "middle of a line (after a GOSUB's RETURN) prints nothing. An END line is traced.",
                 by("each line traced", "one trace per line", "a GOSUB target traced, its return not",
                    "a loop over two lines", "an END line is traced", "the trace has no new line of its own",
                    "a five-digit line", "a GOTO target traced"), ok),
            Rule("R-TRON-ONOFF", "2. On and off", "TRON starts the trace at the NEXT line entered (the line holding it is "
                 "not traced); a statement typed at the prompt is never traced; the trace stays on through RUN, and NEW "
                 "switches it off. Anything after TRON is error 2.",
                 by("the TRON line itself is not traced", "a typed statement is not traced",
                    "the trace stays on through RUN", "NEW switches the trace off", "something after TRON"), ok),
        ]
    if kw == "TROFF":
        return [
            Rule("R-TROFF-OFF", "1. Switching off", "TROFF stops the trace after its own line -- that line was traced "
                 "before it ran; typed, it stops it for the next RUN; with the trace already off it does nothing. "
                 "Anything after TROFF is error 2.",
                 by("the TROFF line is still traced", "TROFF when the trace is off", "something after TROFF",
                    "a typed TROFF"), ok),
        ]
    return [
        Rule("R-REM-LINE", "1. The rest of the line", "REM makes the rest of its line a comment, colons included -- and "
             "an ELSE, so `IF 0 THEN REM ELSE B=1` leaves B alone. The apostrophe is REM, and needs no colon before it "
             "(`PRINT \"C\" 'X`); REM itself does: `PRINT \"A\" REM X` prints A, then error 2. A REM line is an ordinary "
             "GOTO target; a typed REM does nothing.",
             by("REM ends the line", "the apostrophe without a colon", "REM swallows an ELSE", "a colon inside a REM",
                "a GOTO to a REM line", "REM after a statement without a colon", "a typed REM",
                "the apostrophe after a colon"), ok),
    ]
