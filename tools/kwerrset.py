#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-KWT6 — the T6 DENOMINATOR: which errors the REFERENCE raises, per keyword form.

🏗️ JOOST'S RULING (2026-09-27): a keyword proves T6 ("handles the exhaustive
error set") when, FOR EACH DOCUMENTED SYNTAX FORM, it has one row per DISTINCT
error the reference raises for that form -- wrong type, out of range, missing
argument, illegal direct, ... -- each matching the reference's error CODE and
LINE. Finite per keyword, enumerable by probing the reference.

This file is that denominator. `tools/tier_table.py` ticks T6 for a keyword only
when:
  * the keyword is knife-proven CONNECTED (the rule every rung above T1 keeps);
  * EVERY form `tools/kwforms.py` authors for it has an entry here -- a form
    whose error set was never measured leaves the keyword UNRATED, not satisfied;
  * the entries hold at least one code in total (a zero denominator proves
    nothing -- the `kwcover` lesson);
  * every (form, code) pair here has a SUPPORTED kwsweep row declaring
    `PROVES-T6:<code>` with that `FORM:` tag. Those rows run in `stored` mode,
    so the reference's ` in <line>` is part of what is compared.

🔴 AN ENTRY IS A MEASUREMENT, NOT AN OPINION. Each one is written from a probe run
against the reference (never from our own handler -- the `kwforms` circularity
rule: a keyword implemented too simply would get a smaller denominator) and
carries its provenance: the probe, its output file and the date.

⚠️ ABSENCE IS NOT AN EMPTY SET. A keyword missing here has no measured error set
yet and cannot reach T6.
"""
from __future__ import annotations

# keyword -> form -> the error codes the reference raised for that form, and
# where that was measured (PROVENANCE); only a probe run writes an entry.
# 📏 BATCH 1, MEASURED 2026-09-27 (D-KWT6 S2): ten one-form functions already at
# level 3. The battery per argument: wrong type, missing, one extra, and the range
# edges named in the probe. zerobas matched the reference on all 48 cases.
ERRSETS: dict[str, dict[str, frozenset[int]]] = {
    "ABS": {"magnitude": frozenset({2, 13})},
    "SGN": {"sign": frozenset({2, 13})},
    "INT": {"floor": frozenset({2, 13})},
    "SQR": {"square-root": frozenset({2, 5, 13})},
    "LOG": {"logarithm": frozenset({2, 5, 13})},
    "EXP": {"exponential": frozenset({2, 6, 13})},
    "ASC": {"code-of": frozenset({2, 5, 13})},
    "CHR$": {"code-to-char": frozenset({2, 5, 6, 13})},
    "LEN": {"length": frozenset({2, 13})},
    "PEEK": {"address-read": frozenset({2, 6, 13})},
    # 📏 BATCH 2, MEASURED 2026-09-27 (t6enum_probe.py --batch=2 -> t6enum_b2.out):
    # multi-argument functions and statements, every argument faulted in turn.
    "LEFT$": {"prefix": frozenset({2, 5, 6, 13})},
    "RIGHT$": {"suffix": frozenset({2, 5, 6, 13})},
    "STRING$": {"repeat": frozenset({2, 5, 13})},
    "HEX$": {"to-hex": frozenset({2, 6, 13})},
    "OCT$": {"to-octal": frozenset({2, 6, 13})},
    "BIN$": {"to-binary": frozenset({2, 6, 13})},
    "SPACE$": {"pad": frozenset({2, 5, 13})},
    "STR$": {"number-to-string": frozenset({2, 13})},
    "CINT": {"to-integer": frozenset({2, 6, 13})},
    "FIX": {"truncate": frozenset({2, 13})},
    "CSNG": {"to-single": frozenset({2, 13})},
    "CDBL": {"to-double": frozenset({2, 13})},
    "SIN": {"sine": frozenset({2, 13})},
    "COS": {"cosine": frozenset({2, 13})},
    "TAN": {"tangent": frozenset({2, 6, 13})},
    "ATN": {"arctangent": frozenset({2, 13})},
    "VPEEK": {"address-read": frozenset({2, 5, 6, 13})},
    "POKE": {"address-value": frozenset({2, 5, 6, 13, 24})},
    "VPOKE": {"address-value": frozenset({2, 5, 6, 13, 24})},
    "SOUND": {"register-value": frozenset({2, 5, 13, 24})},
    # 📏 BATCH 3, MEASURED 2026-09-27 on the CF-3300 (the Disk BASIC oracle;
    # t6enum_probe.py --batch=3 -> t6enum_b3.out).
    "MKI$": {"int-to-string": frozenset({2, 6, 13})},
    "CVI": {"string-to-int": frozenset({2, 5, 13})},
    "MKS$": {"single-to-string": frozenset({2, 13})},
    "CVS": {"string-to-single": frozenset({2, 5, 13})},
    "MKD$": {"double-to-string": frozenset({2, 13})},
    "CVD": {"string-to-double": frozenset({2, 5, 13})},
    "DSKF": {"free-space": frozenset({2, 5, 13, 62})},
    # 📏 BATCH 4, MEASURED 2026-09-27 (t6enum_probe.py --batch=4 -> t6enum_b4.out):
    # statements and multi-form keywords, one-line scenarios per form.
    "INSTR": {"search": frozenset({2, 13}), "search-from": frozenset({2, 5, 6, 13})},
    "MID$": {"substring-3arg": frozenset({2, 5, 6, 13}), "substring-to-end": frozenset({2, 5, 13}), "assign": frozenset({2, 5, 13})},
    "NEXT": {"bare": frozenset({1}), "named": frozenset({1, 2}), "comma-list": frozenset({1})},
    "RETURN": {"bare": frozenset({3}), "line": frozenset({2, 3, 8})},
    "RESTORE": {"bare": frozenset({8}), "line": frozenset({8})},
    "GOTO": {"jump": frozenset({2, 8})},
    "READ": {"read-data": frozenset({2, 4, 6})},
    "SWAP": {"exchange": frozenset({2, 13})},
    "ERASE": {"free-array": frozenset({2, 5})},
    "DIM": {"one-dimensional": frozenset({2, 5, 6, 9, 10, 13}), "multi-dimensional": frozenset({5, 9, 10, 13})},
    # 📏 BATCH 5, MEASURED 2026-09-27 (t6enum_probe.py --batch=5 -> t6enum_b5.out).
    # ⚠️ INKEY$'s only code (13) is `A=INKEY$` -- the ASSIGNMENT's type mismatch,
    # since `INKEY$(1)` reads OK on the reference: weak evidence for INKEY$ itself.
    "AND": {"bitwise-and": frozenset({6, 13, 24})},
    "OR": {"bitwise-or": frozenset({6, 13, 24})},
    "XOR": {"bitwise-xor": frozenset({6, 13, 24})},
    "EQV": {"equivalence": frozenset({6, 13, 24})},
    "IMP": {"implication": frozenset({6, 13, 24})},
    "NOT": {"bitwise-not": frozenset({6, 13, 24})},
    "MOD": {"modulo": frozenset({6, 11, 13, 24})},
    "BEEP": {"no-argument": frozenset({2})},
    "CLS": {"no-argument": frozenset({2})},
    "TRON": {"toggle": frozenset({2})},
    "TROFF": {"toggle": frozenset({2})},
    "END": {"terminate": frozenset({2})},
    "CSRLIN": {"row-read": frozenset({2})},
    "ERL": {"error-line": frozenset({2})},
    "ERR": {"error-code": frozenset({2})},
    "ERROR": {"raise": frozenset({2, 5, 6, 13, 24})},
    "GOSUB": {"call": frozenset({2, 8})},
    "INKEY$": {"poll-key": frozenset({13})},
    "INP": {"port-read": frozenset({2, 13})},
    "LET": {"assign": frozenset({2, 13})},
    "OUT": {"port-value": frozenset({2, 5, 13, 24})},
    "POINT": {"pixel-read": frozenset({2, 13})},
    "POS": {"column-read": frozenset({2})},
    "LPOS": {"column-read": frozenset({2})},
    "RND": {"reseeded-draw": frozenset({2, 13})},
    # 📏 BATCH 6, MEASURED 2026-09-27 (t6enum_probe.py --batch=6 -> t6enum_b6.out):
    # multi-form statements; RESUME not measurable by this probe (untrappable).
    "FOR": {"ascending": frozenset({2, 13, 24}), "step": frozenset({2, 13, 24}), "negative-step": frozenset({13, 24})},
    "IF": {"then": frozenset({2, 8, 13}), "else": frozenset({8, 13}), "goto": frozenset({2, 8, 13})},
    "CLEAR": {"bare": frozenset({2}), "string-space": frozenset({5, 6, 7, 13}), "himem": frozenset({5, 13, 24})},
    "COLOR": {"foreground": frozenset({5, 13}), "background": frozenset({5, 13}), "border": frozenset({2, 5, 13})},
    "SCREEN": {"mode": frozenset({5, 13}), "sprite-size": frozenset({5, 13}), "key-click": frozenset({2, 5, 13})},
    "LOCATE": {"column": frozenset({5, 13}), "row": frozenset({5, 13}), "omitted-column": frozenset({13}), "cursor-switch": frozenset({13})},
    "TIME": {"read": frozenset({13}), "write": frozenset({6, 13, 24})},
    "DEFINT": {"single-letter": frozenset({2}), "letter-range": frozenset({2})},
    "DEFSNG": {"single-letter": frozenset({2}), "letter-range": frozenset({2})},
    "DEFDBL": {"single-letter": frozenset({2}), "letter-range": frozenset({2})},
    "DEFSTR": {"single-letter": frozenset({2}), "letter-range": frozenset({2})},
    # --- batch 7: graphics statements, device functions, ON/KEY/FN, PLAY, SET.
    # 🔴 CIRCLE AND PAINT ARE NOT HERE, ON PURPOSE: `CIRCLE(99,99),-5` and both
    # `PAINT(1,1),1,16` / `PAINT(1,1),1,1,1` gave the REFERENCE no reading, so
    # those forms' sets are not known to be complete -- an entry is a
    # measurement, and a partly-read form is not one.
    "PSET": {"colour-explicit": frozenset({2, 5, 13}), "colour-default": frozenset({2, 24}), "step-relative": frozenset({2, 5, 13}), "mode-screen3": frozenset({5, 6, 13})},
    "PRESET": {"colour-default": frozenset({2, 5, 13}), "colour-explicit": frozenset({5, 13}), "step-relative": frozenset({2, 13}), "mode-screen3": frozenset({5, 13})},
    "LINE": {"segment": frozenset({2, 5, 13}), "box": frozenset({2, 5}), "filled-box": frozenset({2, 5}), "step-relative": frozenset({2, 13}), "omitted-start": frozenset({2, 13}), "colour-default": frozenset({2, 13, 24})},
    "DRAW": {"movement": frozenset({5, 13}), "move-absolute": frozenset({5}), "move-relative": frozenset({5}), "blank-prefix": frozenset({5}), "no-update-prefix": frozenset({5}), "colour": frozenset({5}), "scale": frozenset({5}), "angle": frozenset({5}), "substring-exec": frozenset({5, 13}), "variable-substitution": frozenset({5, 13})},
    "BASE": {"read": frozenset({2, 5, 13}), "write": frozenset({5, 6, 13, 24})},
    "VDP": {"read": frozenset({2, 5, 13}), "write": frozenset({5, 13, 24})},
    "SPRITE": {"pattern-write": frozenset({5}), "enable": frozenset({2}), "disable": frozenset({2})},
    "ON GOTO": {"index-goto": frozenset({2, 5, 8, 13})},
    "ON GOSUB": {"index-gosub": frozenset({2, 5, 8, 13})},
    "KEY": {"assign": frozenset({2, 5, 13}), "list": frozenset({2}), "display-on": frozenset({2}), "display-off": frozenset({2})},
    "STICK": {"cursor-keys": frozenset({2, 5, 13}), "joystick-port": frozenset({2, 5})},
    "STRIG": {"space-bar": frozenset({2, 5, 13}), "joystick-trigger": frozenset({2, 5})},
    "PDL": {"read": frozenset({2, 5, 13})},
    "PAD": {"touch-status": frozenset({2, 5, 13}), "coordinate": frozenset({2, 5}), "switch": frozenset({2, 5})},
    "DEF USR": {"default": frozenset({2, 6, 13}), "numbered": frozenset({2, 6, 13})},
    "DEF FN": {"numeric": frozenset({2}), "string-valued": frozenset({2})},
    "FN": {"numeric": frozenset({2, 13, 18}), "string-valued": frozenset({13, 18})},
    "STOP": {"break": frozenset({2})},
    "PLAY": {"notes": frozenset({5, 13}), "note-number": frozenset({5}), "rest": frozenset({5}), "octave": frozenset({5}), "default-length": frozenset({5}), "tempo": frozenset({5}), "volume": frozenset({5}), "envelope": frozenset({5}), "multi-voice": frozenset({2, 13}), "substring-exec": frozenset({5, 13})},
    "SET": {"refuse": frozenset({5})},
}

_B1 = {"ABS", "SGN", "INT", "SQR", "LOG", "EXP", "ASC", "CHR$", "LEN", "PEEK"}
_B3 = {"MKI$", "CVI", "MKS$", "CVS", "MKD$", "CVD", "DSKF"}
_B4 = {"INSTR", "MID$", "NEXT", "RETURN", "RESTORE", "GOTO", "READ", "SWAP", "ERASE", "DIM"}
_B6 = {"FOR", "IF", "CLEAR", "COLOR", "SCREEN", "LOCATE", "TIME", "DEFINT", "DEFSNG",
       "DEFDBL", "DEFSTR"}
_B7 = {"PSET", "PRESET", "LINE", "DRAW", "BASE", "VDP", "SPRITE", "ON GOTO", "ON GOSUB",
       "KEY", "STICK", "STRIG", "PDL", "PAD", "DEF USR", "DEF FN", "FN", "STOP", "PLAY",
       "SET"}
_B5 = {"AND", "OR", "XOR", "EQV", "IMP", "NOT", "MOD", "BEEP", "CLS", "TRON", "TROFF",
       "END", "CSRLIN", "ERL", "ERR", "ERROR", "GOSUB", "INKEY$", "INP", "LET", "OUT",
       "POINT", "POS", "LPOS", "RND"}
PROVENANCE: dict[str, str] = {
    k: ("scratchpad/t6enum_probe.py -> scratchpad/t6enum_run.out (EXP: t6enum_exp.out), VG-8020"
        if k in _B1 else
        "scratchpad/t6enum_probe.py --batch=3 -> scratchpad/t6enum_b3.out, CF-3300"
        if k in _B3 else
        "scratchpad/t6enum_probe.py --batch=4 -> scratchpad/t6enum_b4.out, VG-8020"
        if k in _B4 else
        "scratchpad/t6enum_probe.py --batch=5 -> scratchpad/t6enum_b5.out, VG-8020"
        if k in _B5 else
        "scratchpad/t6enum_probe.py --batch=6 -> scratchpad/t6enum_b6.out, VG-8020"
        if k in _B6 else
        "scratchpad/t6enum_probe.py --batch=7 -> scratchpad/t6enum_b7.out, VG-8020"
        if k in _B7 else
        "scratchpad/t6enum_probe.py --batch=2 -> scratchpad/t6enum_b2.out, VG-8020")
       + ", 2026-09-27"
    for k in ERRSETS}


def errset_for(kw: str):
    """{form: frozenset(codes)} for a keyword, or None when never measured."""
    return ERRSETS.get(kw)
