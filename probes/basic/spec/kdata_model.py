#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""The rule builders for DATA / READ / RESTORE's EXECUTABLE RULES (docs/spec-method.md §3a, docs/keywords/spec-plan.md
region 7). The cases come from probes/basic/spec/kdata.py's committed run (scratchpad/KDA_run1.out): each case's
normalised SCREEN. The model is kstop_model.py's small BASIC, the one interpreter for every screen-reading keyword
probe (its data_items() cuts DATA the way the rules state; READ / RESTORE keep one pointer into that list)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kdata  # noqa: E402
import kstop_model as K  # noqa: E402
from kstop_model import Rule  # noqa: E402

FIELDS = K.FIELDS
OUTPUTS = {"FX": FIELDS}
OUTPUTS_DESC = K.OUTPUTS_DESC
run = K.run
ok = K.ok


def load(kw):
    out = kdata.load()
    return {who: [c for c in cs if c.kw == kw] for who, cs in out.items()}


def by(*whys):
    return lambda c: c.why in whys


def rules(kw):
    if kw == "DATA":
        return [
            Rule("R-DATA-CUT", "1. The items", "DATA's items are cut at commas, in program order, wherever the DATA "
                 "stands (after an END on its line too). Unquoted text keeps what was typed -- spaces inside and "
                 "TRAILING spaces kept, leading spaces skipped. Quotes protect commas and colons (the statement after "
                 "the closing quote runs); an unterminated quote runs to the end of the line; quoted spaces are kept at "
                 "both ends; the quotes are not part of the item. An empty item reads as 0, or as an empty string; "
                 "digits read into a string stay text.",
                 by("two numbers", "trailing spaces kept", "spaces inside kept", "leading spaces skipped",
                    "quotes protect a comma", "quotes protect a colon", "an unterminated quote",
                    "quoted spaces kept at both ends", "an empty item into a number", "an empty item into a string",
                    "digits into a string stay text", "DATA after END on its line"), ok),
            Rule("R-DATA-TYPE", "2. Errors", "Text read into a number is error 2 (Syntax error) -- reported in the DATA "
                 "line, not the READ's.", by("text into a number"), ok),
        ]
    if kw == "READ":
        return [
            Rule("R-READ-NEXT", "1. The next item", "Each variable takes the next item, across DATA lines; a READ typed "
                 "at the prompt goes on where the program stopped. RUN, CLEAR and a program edit take the position "
                 "back to the first item.",
                 by("across DATA lines", "a direct READ goes on after the program", "RUN goes back to the first item",
                    "CLEAR goes back to the first item", "an edit goes back to the first item"), ok),
            Rule("R-READ-ERRORS", "2. Errors", "No item left is error 4 (Out of DATA), also in the middle of a READ; "
                 "an array element out of its DIM is error 9; a number an integer cannot hold is error 6.",
                 by("no DATA at all", "out of DATA in the middle of a READ", "a bad subscript",
                    "a number too large for an integer"), ok),
        ]
    return [
        Rule("R-RESTORE-POINT", "1. Where READ goes on", "RESTORE takes the next READ back to the first item -- the "
             "rest of its line runs; RESTORE n to the first item of line n, or of the next DATA after it when line n "
             "has none.",
             by("RESTORE and the rest of the line", "RESTORE n", "RESTORE to a line without DATA",
                "RESTORE n to the line just read"), ok),
        Rule("R-RESTORE-ERRORS", "2. Errors", "A line that does not exist is error 8 (Undefined line number) -- and so is "
             "anything else after RESTORE: a variable, a comma.",
             by("RESTORE to a missing line", "RESTORE and a variable", "RESTORE and a comma"), ok),
    ]
