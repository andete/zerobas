#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""The model and rule builders for END / STOP / CONT / RUN's EXECUTABLE RULES (docs/spec-method.md §3a,
docs/keywords/spec-plan.md region 5). The cases come from probes/basic/spec/kstop.py's committed run
(scratchpad/KSP_run1.out): each case's normalised screen. A case's RESPONSE is that screen without the prompts and
without the echo of what was typed (each typed line cut at the screen's line width, 37); the model predicts the response
from the rules, and a control (kstop_controls.py) replaces one rule with a rival that must be FALSE on some case."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
import kstop  # noqa: E402
from spec_rules import Rule  # noqa: E402

FIELDS = ["scr"]
OUTPUTS = {"FX": FIELDS}
OUTPUTS_DESC = "each case's normalised screen (prompts as <prompt>, the echo of the typed lines read as typed)"

B = "Break in 10"
T = {
    "END stops the program mid-line": ["[A]"],
    "CONT after END": ["[A]", "[B]"],
    "END in direct mode": [],
    "END inside a GOSUB": [],
    "STOP stops with Break in": ["[A]", B],
    "CONT after STOP goes on after it": ["[A]", B, "[B]"],
    "STOP inside a GOSUB, then CONT returns normally": ["[A]", "Break in 30", "[B]", "[C]"],
    "STOP inside a FOR, CONT twice": ["[ 1 ]", B, "[ 2 ]", B, "[ 3 ]", B],
    "STOP in direct mode": ["Break"],
    "a variable changed while stopped": [B, "[ 7 ]"],
    "CONT before anything ran": ["Can't CONTINUE"],
    "CONT after an error": ["[A]", "Division by zero in 10", "Division by zero in 10"],
    "CONT after a line was added": ["[A]", B, "Can't CONTINUE"],
    "CONT after a direct statement": ["[A]", B, "2", "[B]"],
    "RUN n starts at line n": ["[B]"],
    "RUN to a line that does not exist": ["Undefined line number"],
    "RUN clears the variables": ["[ 0 ]", "[ 0 ]"],
    "RUN inside a program": ["[A]", "[B]"],
    "RUN with no program": [],
}
RIVAL = {
    "cont-after-end-cant": {"CONT after END": ["[A]", "Can't CONTINUE"]},
    "cont-after-error-cant": {"CONT after an error": ["[A]", "Division by zero in 10", "Can't CONTINUE"]},
    "direct-blocks-cont": {"CONT after a direct statement": ["[A]", B, "2", "Can't CONTINUE"]},
    "edit-keeps-cont": {"CONT after a line was added": ["[A]", B, "[B]"]},
    "run-keeps-vars": {"RUN clears the variables": ["[ 0 ]", "[ 5 ]"]},
    "stop-direct-silent": {"STOP in direct mode": []},
    "cont-from-stmt-start": {"CONT after STOP goes on after it": ["[A]", B, "[A]", B]},
}


def response(c):
    echo = set()
    for t in c.lines + ["NEW", "CLS"]:
        echo.update(t[i:i + 37].strip() for i in range(0, len(t), 37))   # a typed line wraps at LINLEN 37
    return [l for l in (c.scr or []) if l != "<prompt>" and l not in echo]


def expect(c, alt=frozenset()):
    for a in alt:
        if c.why in RIVAL.get(a, {}):
            return RIVAL[a][c.why]
    return T[c.why]


def ok(c, alt=frozenset()):
    return response(c) == expect(c, alt)


def load(kw):
    out = kstop.load()
    return {who: [c for c in cs if c.kw == kw] for who, cs in out.items()}


def by(*whys):
    return lambda c: c.why in whys


def rules(kw):
    if kw == "END":
        return [Rule("R-END-STOP", "1. Stopping", "END stops the program where it stands -- the rest of its line, and a "
                     "GOSUB still pending, are dropped -- with no message; in direct mode it does nothing. CONT after "
                     "END goes on with the statement after it.",
                     by("END stops the program mid-line", "CONT after END", "END in direct mode", "END inside a GOSUB"),
                     ok)]
    if kw == "STOP":
        return [
            Rule("R-STOP-BREAK", "1. Stopping", "STOP stops the program with `Break in n` (n its line); in direct mode "
                 "it prints `Break` alone.",
                 by("STOP stops with Break in", "STOP in direct mode"), ok),
            Rule("R-STOP-CONT", "2. Going on", "CONT goes on with the statement AFTER the STOP: inside a GOSUB the "
                 "RETURN still works, inside a FOR the loop goes on (each STOP stopping again), and a variable changed "
                 "while stopped is seen.",
                 by("CONT after STOP goes on after it", "STOP inside a GOSUB, then CONT returns normally",
                    "STOP inside a FOR, CONT twice", "a variable changed while stopped"), ok),
        ]
    if kw == "CONT":
        return [Rule("R-CONT-WHEN", "1. When CONT can go on", "CONT before anything ran, or after a program line was "
                     "added or changed, prints `Can't CONTINUE`; a direct statement in between does not stop it; after "
                     "an ERROR, CONT runs the failing statement again and raises the same error.",
                     by("CONT before anything ran", "CONT after a line was added", "CONT after a direct statement",
                        "CONT after an error"), ok)]
    return [
        Rule("R-RUN-START", "1. Starting", "RUN starts at the first line, RUN n at line n; a missing n is `Undefined line "
             "number`; RUN inside a program starts it again there; RUN with no program does nothing.",
             by("RUN n starts at line n", "RUN to a line that does not exist", "RUN inside a program",
                "RUN with no program"), ok),
        Rule("R-RUN-CLEAR", "1. Starting", "RUN clears the variables first: a value left by the last run reads 0.",
             by("RUN clears the variables"), ok),
    ]
