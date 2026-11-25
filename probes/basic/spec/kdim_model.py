#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""The rule builders for DIM / ERASE / CLEAR's EXECUTABLE RULES (docs/spec-method.md §3a, docs/keywords/spec-plan.md
region 7). The cases come from probes/basic/spec/kdim.py's committed run (scratchpad/KDM_run1.out): each case's
normalised SCREEN. The model is kstop_model.py's small BASIC, the one interpreter for every screen-reading keyword
probe (its dim() / element() hold the array laws the rules state; CLEAR n[,top] checks every argument before it
changes anything)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kdim  # noqa: E402
import kstop_model as K  # noqa: E402
from kstop_model import Rule  # noqa: E402

FIELDS = K.FIELDS
OUTPUTS = {"FX": FIELDS, "FY": FIELDS}
OUTPUTS_DESC = K.OUTPUTS_DESC
run = K.run
ok = K.ok


def load(kw):
    out = kdim.load()
    return {who: [c for c in cs if c.kw == kw] for who, cs in out.items()}


def by(*whys):
    return lambda c: c.why in whys


def rules(kw):
    if kw == "DIM":
        return [
            Rule("R-DIM-BOUNDS", "1. Bounds", "Subscripts run from 0 to the bound (DIM A(3): four elements); an array "
                 "used without DIM is made with bound 10 in every dimension; past a bound is error 9 (Subscript out of "
                 "range) -- so is the wrong number of subscripts; a NEGATIVE subscript is error 5. A bound is cut to an "
                 "integer (DIM A(2.7) makes bound 2); after ERASE the default is 10 again. Arrays have any number of "
                 "dimensions; an integer element stores the whole part, cut towards zero.",
                 by("subscripts from 0 to the bound", "past the bound", "an undeclared array has bound 10",
                    "past an undeclared array's bound", "two dimensions", "an integer array and a double one",
                    "bound 10 in every dimension", "past bound 10 in the second dimension",
                    "after ERASE the default bound is 10 again", "an integer element cuts towards zero",
                    "a negative subscript", "the wrong number of subscripts", "a fractional bound is cut"), ok),
            Rule("R-DIM-SIZE", "2. Errors", "A negative bound is error 5; a bound too large for an integer (70000) error "
                 "6 (32768 already); a string bound 13. The elements -- 2 bytes an integer, 4 a single, 8 a double, 3 a "
                 "string -- must fit 65535 BYTES, else error 9 however small the bounds (DIM Q%(200,200); 65536 bytes "
                 "of any type); within that but past the memory left -- which the string space and every array "
                 "already made share -- error 7.",
                 by("a negative bound", "a bound past 65535", "more than 65535 bytes of doubles",
                    "more than 65535 bytes from small bounds", "more than free memory", "a string bound",
                    "two arrays that do not fit together", "65534 bytes of integers", "65536 bytes of integers",
                    "65532 bytes of singles", "65536 bytes of singles", "65535 bytes of strings",
                    "65538 bytes of strings", "a bound of 32768"), ok),
            Rule("R-DIM-NAMES", "1. Bounds", "An array's identity is its first two characters and its TYPE: AB1 and "
                 "AB2 are one array; with no DEF, A and A# are one (ERASE A removes A#; A#(3) is A(3)). A name "
                 "without bounds makes nothing (DIM A, then DIM A(2), is no error).",
                 by("two significant characters", "A# and A are one array with no DEF", "A#(3) is A(3) with no DEF",
                    "DIM A makes nothing"), ok),
            Rule("R-DIM-FORMS", "2. Errors", "DIM of an existing array is error 10 (Redimensioned array); a number for a "
                 "name, DIM alone or a trailing comma error 2; a name without bounds is no error and makes nothing. "
                 "Several arrays are made one by one: a failing one leaves those before it.",
                 by("DIM twice", "a number for a name", "DIM alone", "a trailing comma",
                    "the arrays before a failing one stay", "a name without bounds"), ok),
        ]
    if kw == "ERASE":
        return [
            Rule("R-ERASE-REMOVE", "1. Removing", "ERASE removes arrays one by one -- a later failing name leaves the "
                 "earlier ones erased; the name is free again (used, it is a new array of bound 10; DIM works again).",
                 by("ERASE, then the name used again", "the names before a failing one are erased",
                    "DIM again after ERASE"), ok),
            Rule("R-ERASE-ERRORS", "2. Errors", "An array that does not exist -- never made, already erased, or of "
                 "ANOTHER type (the suffix is part of the name) -- is error 5; ERASE alone or an element is error 2.",
                 by("ERASE an array that does not exist", "ERASE twice", "ERASE another type's array", "ERASE alone",
                    "ERASE an element"), ok),
        ]
    return [
        Rule("R-CLEAR-RESET", "1. What it clears", "CLEAR clears the variables and the GOSUB / FOR stack (a RETURN after it is "
             "error 3), switches ON ERROR off, takes READ back to the first item, and the program goes on after it.",
             by("CLEAR clears the variables", "CLEAR switches ON ERROR off", "CLEAR takes READ back to the first item",
                "the program goes on after CLEAR", "CLEAR inside a GOSUB"), ok),
        Rule("R-CLEAR-SIZE", "2. The string space", "The string space is 200 bytes at start-up; CLEAR n makes it exactly n "
             "(FRE of an empty string reads n), also with a new top (CLEAR n,top: the size is n); a bare CLEAR keeps "
             "the last size.",
             by("CLEAR n sets the string space", "the string space at start-up", "a bare CLEAR keeps the size",
                "moving the top keeps the size"), ok),
        Rule("R-CLEAR-ERRORS", "3. Errors", "Every argument is checked before anything changes, so a refused CLEAR leaves "
             "the variables and the handler as they were -- in this order: a negative size is 5, past 32767 6, a top below "
             "&H8000 5, more than the memory (or than the top leaves) 7, a string 13; then a third argument is 2; a "
             "comma and no top is 24 (Missing operand), a comma and no size 2.",
             by("a negative size", "a size past 65535", "more string space than memory", "a string size",
                "a top below &H8000", "a comma and no top", "a comma and no size", "a refused CLEAR changes nothing",
                "CLEAR 32768", "CLEAR 40000", "CLEAR 65535", "a top that leaves no room",
                "a negative size, then too many arguments", "a size past 65535, then too many arguments",
                "the string space and an array share memory"),
             ok),
    ]
