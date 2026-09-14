#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-KWTIER1 — how many FORMS a keyword must be shown to handle, per keyword.

🎚️ JOOST'S RULE (2026-09-14): a keyword reaches TIER 1 when it is knife-proven
CONNECTED, has rows covering N distinct FORMS, and carries no open TIER item --
"N should depend on the complexity of each individual keyword".

🔴 N IS AUTHORED HERE AND NOT DERIVED FROM OUR OWN HANDLER, AND THAT IS THE WHOLE
POINT. The tempting mechanical route -- count the optional-argument branches in
`basic/*.asm` -- is CIRCULAR: a keyword we implemented too simply would get a
lower bar and pass more easily, so the test would be graded against the thing
under test. The bar comes from the REFERENCE's syntax. Where the tree has no
grammar table (247 spec docs, all organised by slice, none per keyword), the form
list is written out by hand WITH ITS REASON and is reviewable as data.

🎯 A FORM IS A DISTINCT BEHAVIOUR THE VERB MUST GET RIGHT, not a distinct input.
`PSET(1,1),15` and `PSET(2,2),7` are ONE form sampled twice -- which is exactly
what the sweep held before this file existed, and why the tier table counts
DISTINCT `FORM:` tags rather than rows.

⚠️ ABSENCE FROM THIS TABLE IS NOT N=0. A keyword with no entry has no authored
bar yet, and `tier_table` must treat it as UNRATED rather than as satisfied --
the `kwcover` lesson: an instrument that reports a plausible answer from a missing
input is worse than one that refuses.
"""
from __future__ import annotations

# 🎚️ COMPOSITE STATEMENTS (Joost, 2026-09-14: "one could consider the ON + second
# keyword one composite keyword requiring its own tests"). `ON KEY GOSUB` and
# `ON n GOTO` share nothing but a token; `LINE INPUT` and `LINE (x,y)-(x,y)` are
# entirely different statements. Tiering the FIRST keyword of a statement would let
# a graphics row vouch for console input, and it is what let `ON` reach TIER 1 on
# three rows that spoke for three of its EIGHT composites.
# 🔴 MOST SPECIFIC FIRST, AND THE ORDER IS LOAD-BEARING: `ON ERROR GOTO` must win
# over `ON GOTO`, and `ON GOTO` must never match an `ON ERROR GOTO` body. Each
# pattern is the set of keywords that must ALL appear; longer sets are tried first.
# ⚠️ GROUNDED IN WHAT THIS TREE SHIPS, not in the MSX manual: every one below has a
# handler here (the ON-traps are ex_on_key / ex_on_interval / ex_on_strig /
# eos_common, basic/interp.asm:284).
COMPOSITES: tuple[tuple[frozenset[str], str], ...] = tuple(
    (frozenset(ws.split()), name) for ws, name in (
        ("ON ERROR GOTO",   "ON ERROR GOTO"),
        ("ON KEY GOSUB",    "ON KEY GOSUB"),
        ("ON STOP GOSUB",   "ON STOP GOSUB"),
        ("ON SPRITE GOSUB", "ON SPRITE GOSUB"),
        ("ON STRIG GOSUB",  "ON STRIG GOSUB"),
        ("ON INTERVAL GOSUB", "ON INTERVAL GOSUB"),
        ("ON GOSUB",        "ON GOSUB"),
        ("ON GOTO",         "ON GOTO"),
        ("LINE INPUT",      "LINE INPUT"),
        ("DEF FN",          "DEF FN"),
        ("DEF USR",         "DEF USR"),
        ("PUT SPRITE",      "PUT SPRITE"),
        ("PRINT USING",     "PRINT USING"),
    ))
COMPOSITES = tuple(sorted(COMPOSITES, key=lambda e: -len(e[0])))


def composite_name(words) -> str | None:
    """The composite statement `words` names, or None.

    `words` is the set of KEYWORDS a crunch body contains. The most specific
    pattern wins, so `{ON, ERROR, GOTO}` is `ON ERROR GOTO` and never `ON GOTO`."""
    ws = set(words)
    for need, name in COMPOSITES:
        if need <= ws:
            return name
    return None


# keyword -> (forms, why this is the set)
FORMS: dict[str, tuple[tuple[str, ...], str]] = {
    "PSET": (
        ("colour-explicit", "colour-default", "step-relative", "mode-screen3"),
        "MSX1 syntax is `PSET [STEP](x,y)[,colour]`, so the switches are STEP and "
        "the optional colour; the bitmap mode is the fourth because SCREEN 3 is "
        "MULTICOLOUR with its own VRAM layout, and the plot and the read-back both "
        "take a different address calculation there. The MSX2-only logical "
        "OPERATOR argument is deliberately NOT counted -- this is an MSX1 tree.",
    ),
    "PRESET": (
        ("colour-default", "colour-explicit", "step-relative", "mode-screen3"),
        "`PRESET [STEP](x,y)[,colour]` -- the same shape as PSET, so the same four. "
        "The default form ERASES (it draws in the background) while the explicit "
        "form draws in the colour given, which is why both are forms and not one "
        "form sampled twice.",
    ),
    "COLOR": (
        ("foreground", "background", "border"),
        "`COLOR [fg][,bg][,border]` -- three POSITIONS, and the form that matters "
        "is the OMISSION: a parser that shifted `COLOR ,5` left would write the "
        "background value into the foreground. Each lands in a declared cell "
        "(FORCLR $F3E9, BAKCLR $F3EA, BDRCLR $F3EB), so all three are readable. "
        "This is deliberately a DIFFERENT SHAPE from PSET/PRESET -- positional "
        "omission rather than an optional trailing argument and a mode.",
    ),
    "CLEAR": (
        ("bare", "string-space", "himem"),
        "MSX1 syntax is `CLEAR [<string space>[,<himem>]]`, so the whole surface is "
        "three: the bare form (which resets variables), the string-space argument, "
        "and the HIMEM ceiling. There is no fourth -- unlike PSET this verb has no "
        "mode or coordinate dimension, which is why N is 3 here and 4 there.",
    ),
}


def forms_for(kw: str) -> tuple[str, ...] | None:
    """The authored form list for `kw`, or None when no bar has been authored."""
    e = FORMS.get(kw)
    return e[0] if e else None


def n_for(kw: str) -> int | None:
    """N for `kw`, or None when UNRATED (no entry). None is not zero."""
    f = forms_for(kw)
    return len(f) if f else None
