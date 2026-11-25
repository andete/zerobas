#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""The rule builders for ERROR / ERR / ERL / RESUME's EXECUTABLE RULES (docs/spec-method.md §3a,
docs/keywords/spec-plan.md region 6). The cases come from probes/basic/spec/kerr.py's committed run
(scratchpad/KER_run1.out): each case's normalised SCREEN.

The model is kstop_model.py's small BASIC -- ONE interpreter for every screen-reading keyword probe -- which types the
case and predicts the whole screen. Its error laws, which these rules state: ERROR n raises n (a code with no message
prints `Unprintable error`; outside 1..255: 5; past 65535: 6; a fraction is cut); every error sets ERR and ERL (65535
for an error typed at the prompt); an armed handler catches it -- an error typed at the prompt too -- except RESUME's
own error and an error inside the active handler; RESUME / RESUME 0 run the failing statement again, RESUME NEXT the
next one, RESUME n line n, each setting ERR back to 0; a handler that runs off the end is `No RESUME` in the last line
that ran; ON ERROR GOTO 0 -- or anything after GOTO that is not a number -- disarms, and inside the active handler
re-raises the error that entered it, untrapped, with its own line."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kerr  # noqa: E402
import kstop_model as K  # noqa: E402
from kstop_model import Rule  # noqa: E402

FIELDS = K.FIELDS
OUTPUTS = {"FX": FIELDS}
OUTPUTS_DESC = K.OUTPUTS_DESC
run = K.run
ok = K.ok


def load(kw):
    out = kerr.load()
    return {who: [c for c in cs if c.kw == kw] for who, cs in out.items()}


def by(*whys):
    return lambda c: c.why in whys


def rules(kw):
    if kw == "ERROR":
        return [
            Rule("R-ERROR-RAISE", "1. Raising", "ERROR n raises error n as BASIC would: its message, `in` the line in a "
                 "program, alone when typed; a code with no message of its own prints `Unprintable error`; a handler "
                 "sees ERR = n -- also for an ERROR typed at the prompt (ERL 65535).",
                 by("ERROR n in a program", "ERROR n typed", "a code with no message", "a handler sees ERROR's code",
                    "a typed ERROR reaches the handler"), ok),
            Rule("R-ERROR-CODE", "2. The code", "The code is cut to an integer (1.7 is 1); 0 and 256 are error 5 "
                 "(Illegal function call), past 65535 error 6 (Overflow), a string 13, nothing 24 (Missing operand), "
                 "anything after it (`ERROR 1,1`) 2.",
                 by("ERROR 0", "ERROR 256", "a fractional code", "a string code", "no code", "a code past 65535",
                    "a comma after the code"), ok),
        ]
    if kw == "ERR":
        return [
            Rule("R-ERR-VALUE", "1. The code", "ERR is the code of the last error -- in its handler, and at the prompt "
                 "after an untrapped one -- 0 before any error, and 0 again after a RESUME (ERL keeps its line).",
                 by("ERR and ERL in a handler", "ERR and ERL after an untrapped error", "ERR and ERL before any error",
                    "RESUME NEXT: ERR 0, ERL kept"), ok),
            Rule("R-ERR-SYNTAX", "2. Errors", "Anything after ERR (`A=ERR 1`) is error 2.", by("something after ERR"), ok),
        ]
    if kw == "ERL":
        return [
            Rule("R-ERL-LINE", "1. The line", "An error typed at the prompt has no line: ERL is 65535 -- also after a "
                 "program's error was followed by a typed one.",
                 by("an error typed at the prompt", "a typed error after a program's"), ok),
        ]
    return [
        Rule("R-RESUME-FORMS", "1. Where it goes on", "RESUME and RESUME 0 run the failing statement again (the handler "
             "having fixed the cause); RESUME NEXT runs the statement after it -- on the same line after a `:`, else the "
             "next line; a `:` inside a string does not count; RESUME n goes to line n, and a missing n is error 8 in "
             "the handler's line, untrapped. RESUME with no error is error 22 (RESUME without error).",
             by("RESUME runs the statement again", "RESUME 0 is RESUME", "RESUME NEXT, same line",
                "RESUME NEXT, the next line", "RESUME NEXT and a colon in a string", "RESUME n",
                "RESUME to a missing line", "RESUME with no error"), ok),
        Rule("R-RESUME-HANDLER", "2. The handler", "A handler is entered by any error while it is armed and none is "
             "active -- one typed at the prompt too (RESUME NEXT then goes on along the typed line), and after an "
             "earlier handler ended with END; NOT RESUME's own error, and not an error inside the active handler (that "
             "one stops the program). After RESUME the handler catches the next error again. A handler that runs off "
             "the end of the program stops with `No RESUME` in the last line that ran (ERR 21, ERL that line); RUN "
             "inside it clears it.",
             by("a handler running off the end", "ERR and ERL after No RESUME", "an error inside the handler",
                "the handler catches each error again after RESUME", "a typed error with a handler armed",
                "RUN inside the handler, then a typed RESUME", "a typed error after a handler ended with END",
                "a typed RESUME with a handler armed"), ok),
        Rule("R-RESUME-ONERROR", "3. ON ERROR GOTO", "ON ERROR GOTO n arms line n -- a missing n is error 8 at once; "
             "ON ERROR GOTO 0 disarms, and so does a non-number after GOTO (`ON ERROR GOTO A` is GOTO 0). Inside the "
             "active handler, GOTO 0 re-raises the error that entered it, untrapped, with its own line; GOTO n there "
             "arms n and goes on.",
             by("ON ERROR GOTO 0 inside the handler", "ON ERROR GOTO a missing line",
                "ON ERROR GOTO 0 outside a handler disarms", "ON ERROR GOTO inside the handler re-arms",
                "ON ERROR GOTO and a variable"), ok),
    ]
