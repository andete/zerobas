#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""The shared model and rule builders for MKI$ / MKS$ / MKD$ / CVI / CVS / CVD's EXECUTABLE RULES (docs/spec-method.md
§3a, docs/keywords/spec-plan.md). The cases come from probes/basic/spec/kmkcv.py's committed run
(scratchpad/KMC_run1.out); each page's module takes its own keyword's cases from `load(fn)` and its rules from
`rules(fn)`.

Two references: the National CF-3300 with Disk BASIC (groups DMK / DCV / DFX, against zerobas's DISK build) -- the
pages' reference, where these functions work -- and the Philips VG-8020 without it (MK / CV / FX, against zerobas
NODISK), where they do not. Each case's whole record is PREDICTED from the rules and the case's inputs (the number
READ, the bytes of the source string, the statement): MK*$ is CINT / CSNG / CDBL (kconv_model's models, measured on
their own pages) followed by the result's own bytes; CV* takes the first 2 / 4 / 8 bytes of the string as they are."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
import kconv_model as C  # noqa: E402
import kmath_model as K  # noqa: E402
import kmkcv  # noqa: E402
from spec_rules import Rule  # noqa: E402

FIELDS = ["e1", "rbytes", "sl", "sb", "e2", "vt", "res"]
OUTPUTS = {g: FIELDS for g in kmkcv.ORDER}
OUTPUTS_DESC = ("each case's error from the statement and from its USR form, R's 8 bytes, S$'s length and first 8 "
                "bytes, the result's type as USR saw it and the result's own bytes")
R_SENT = K.R_SENT
DISK = ("DMK", "DCV", "DFX")
CONV = {"MKI$": C.m_cint, "MKS$": C.m_csng, "MKD$": C.m_cdbl}
NB = {"CVI": 2, "CVS": 4, "CVD": 8}
enc = K.enc


def load(fn):
    out = {"ref": [], "zb": []}
    for g in kmkcv.ORDER:
        cs = kmkcv.load(g)
        if g in ("MK", "DMK"):
            check_read(cs, g)
        for who in out:
            out[who] += [c for c in cs[who] if c.fn == fn]
    return out


def check_read(cs, g):
    """apparatus: every MK row's recorded number is its DATA text's value in its type, on both machines"""
    bad = []
    for who in cs:
        for c in cs[who]:
            try:
                ok = c.arg == enc(K.text_value(c.text), c.ty) + bytes(8 - K.NB[c.ty])
            except AssertionError:
                ok = True
            if not ok:
                bad.append(f"{who} {c.id}")
    if bad:
        sys.exit(f"FAIL: {g}: the number READ is not the DATA text's value: {', '.join(bad[:8])}")


def disk(c):
    return c.src in DISK


# ---- the fixed statements' inputs ---------------------------------------------------------------------------------
MK_FORM = {"a space before the parenthesis": ("I", enc(5, "I")), "a literal without a point": ("I", enc(7, "I")),
           "a literal with a point": ("S", K.LIT["2.5"][1]), "an expression (a double)": ("D", C.THIRD_D),
           "a hex literal": ("I", enc(-32768, "I")), "40000 (beyond an integer)": ("S", enc(40000, "S"))}
TYPE_WHYS = {"a string as the argument", "the result assigned to a number", "a number as the argument",
             "the result assigned to a string"}
SYNTAX_WHYS = {"no argument", "an extra argument", "no closing parenthesis", "no parenthesis"}
CV_SRC = {"an expression of 8 bytes": b"ABCDEFGH", "a string from MID$": b"CDEFGH"}
ROUND = {"CVI": ("I", enc(-12345, "I")), "CVS": ("S", enc(K.text_value("-1.23456"), "S")),
         "CVD": ("D", enc(K.text_value("1.2345678901234"), "D"))}


def rec(e1=0, s=b"", e2=0, vt=255, res=None):
    return dict(e1=e1, sl=len(s), sb=s[:8], e2=e2, vt=vt, res=res)


def mk_value(fn, ty, b):
    """MK*$'s outcome on Disk BASIC: the conversion, then its own bytes as the string"""
    k = CONV[fn](ty, b)
    if k[0] == "err":
        return rec(e1=k[1])
    return rec(s=k[2])


def cv_value(fn, src, s_after=b""):
    """CV*'s outcome on Disk BASIC: error 5 when the string is shorter than the type, else its first bytes as they
    are, in that type (`R=` and `USR(...)` alike)"""
    n = NB[fn]
    if len(src) < n:
        return rec(e1=5, s=s_after, e2=5)
    return rec(s=s_after, vt=n, res=src[:n])


def expect(c):
    """the case's predicted record (without R: R-*-ASSIGN's)"""
    on_disk = disk(c)
    if c.src in ("MK", "DMK"):
        return mk_value(c.fn, c.ty, K.argb(c)) if on_disk else rec(e1=5)
    if c.src in ("CV", "DCV"):
        if on_disk:
            return cv_value(c.fn, c.bytes, c.bytes)
        return rec(e1=5, s=c.bytes, e2=5)
    w = c.why
    if w in SYNTAX_WHYS:
        return rec(e1=2)
    if w == "the argument's own error":
        return rec(e1=11)
    if w in TYPE_WHYS:
        return rec(e1=13 if on_disk else 5)
    if c.fn in CONV:                                    # MK*$ value forms
        return mk_value(c.fn, *MK_FORM[w]) if on_disk else rec(e1=5)
    s_after = b"ABCDEFGH" if w == "a string from MID$" else b""
    if not on_disk:
        return rec(e1=5, s=s_after, e2=5)
    if w == "a round trip":
        ty, b = ROUND[c.fn]
        return rec(vt=NB[c.fn], res=CONV["MK" + c.fn[2] + "$"](ty, b)[2])
    return cv_value(c.fn, CV_SRC[w], s_after)


def outcome_ok(c):
    w = expect(c)
    return (c.e1, c.sl, c.sb, c.e2, c.vt, c.res) == (w["e1"], w["sl"], w["sb"], w["e2"], w["vt"], w["res"])


def assigned(c):
    """R after the case: a CV* result assigned to the double R (an integer by its value, a single's 4 bytes and four
    zero bytes, a double's 8 -- K.as_double), else its sentinel -12345"""
    if c.fn in NB and c.vt != 255 and c.res is not None and "R=" in (c.stmt or "R=") and c.e1 == 0:
        return c.rbytes == K.as_double(c.vt, c.res)
    return c.rbytes == R_SENT


def fx(c, *whys):
    return c.src in ("FX", "DFX") and c.why in whys


def rules(fn):
    s1, s2, s3, s4 = ("1. With Disk BASIC (the CF-3300)", "2. Forms and errors", "3. Without Disk BASIC (the "
                                                                                        "VG-8020)", "4. The result stored")
    mk = fn in CONV
    conv = {"MKI$": "CINT", "MKS$": "CSNG", "MKD$": "CDBL"}.get(fn)
    n = NB.get(fn)
    tag = fn.rstrip("$")                    # a rule id has no `$`: R-MKI-BYTES
    R = []
    if mk:
        R.append(Rule(f"R-{tag}-BYTES", s1, f"{fn}(x) is a string of { {'MKI$': 2, 'MKS$': 4, 'MKD$': 8}[fn]} "
                      f"bytes: x converted as {conv}(x) does ([{conv}]({conv}.md): "
                      + {"MKI$": "toward zero, 2.5 -> 2, -2.5 -> -2", "MKS$": "a double rounded half up on its 7th "
                         "digit", "MKD$": "a single's 6 digits and 8 zeros"}[fn]
                      + "), then that number's own bytes, as VARPTR shows them (an integer low byte first). Where "
                      f"{conv} raises Overflow, so does {fn}"
                      + {"MKI$": " (32768, 1E10, 1D20): error 6, S$ left as it was.", "MKS$": " (9.999995D62): error "
                         "6.", "MKD$": " -- never: every number has a double."}[fn],
                      lambda c: c.src == "DMK", outcome_ok))
    else:
        R.append(Rule(f"R-{tag}-BYTES", s1, f"{fn}(s) is the first {n} bytes of s, as they are -- "
                      + {"CVI": "an integer, low byte first", "CVS": "a single", "CVD": "a double"}[fn]
                      + f", whatever they hold (a zero exponent byte with digits, a non-BCD nibble: unchanged); "
                      f"bytes beyond the {n}th are ignored; a string shorter than {n} bytes is error 5 (Illegal "
                      f"function call), from `R={fn}(s)` and `USR({fn}(s))` alike.",
                      lambda c: c.src == "DCV", outcome_ok))
        R.append(Rule(f"R-{tag}-EXPR", s1, f"The argument may be any string expression: {fn}(\"A\"+...+\"H\") is the "
                      f"bytes 41 42 ...; {fn}(MID$(S$,3)) starts at S$'s third byte; and {fn}(MK{fn[2]}$(x)) gives x "
                      "back, byte for byte.",
                      lambda c: c.src == "DFX" and c.why in ("an expression of 8 bytes", "a string from MID$",
                                                             "a round trip"), outcome_ok))
    if mk:
        R.append(Rule(f"R-{tag}-FORMS", s2, f"A space before the parenthesis is allowed, and a literal's own type is "
                      f"the argument's (7 and &H8000 integers, 2.5 and 40000 singles, 1/3 a double -- kmath's measured "
                      f"literal types); each gives what R-{tag}-BYTES says for it.",
                      lambda c: c.src == "DFX" and c.why in MK_FORM, outcome_ok))
        R.append(Rule(f"R-{tag}-OWNERR", s2, "An argument that fails to compute raises its own error (1/0: error 11) "
                      "-- with or without Disk BASIC: the argument is evaluated first.",
                      lambda c: fx(c, "the argument's own error"), outcome_ok))
    R.append(Rule(f"R-{tag}-TYPE", s2, ("A string as the argument, or the result assigned to a number variable, "
                                       if mk else "A number as the argument, or the result assigned to a string "
                                       "variable, ") + "is error 13 (Type mismatch).",
                  lambda c: c.src == "DFX" and c.why in TYPE_WHYS, outcome_ok))
    R.append(Rule(f"R-{tag}-SYNTAX", s2, "No argument, a second argument, no closing parenthesis, or the name without "
                  "a parenthesis is error 2 (Syntax error) -- with or without Disk BASIC.",
                  lambda c: fx(c, *SYNTAX_WHYS), outcome_ok))
    R.append(Rule(f"R-{tag}-NODISK", s3, f"Without Disk BASIC every call of {fn} whose argument computes is error 5 "
                  "(Illegal function call) -- whatever the argument, " + ("a string included (5, not 13), "
                                                                         if mk else "a number included (5, not 13), ")
                  + "and the result assigned to the wrong type too; nothing is assigned and USR is not reached.",
                  lambda c: c.src in ("MK", "CV", "FX") and not (c.src == "FX" and c.why in SYNTAX_WHYS
                                                                 | {"the argument's own error"}), outcome_ok))
    R.append(Rule(f"R-{tag}-ASSIGN", s4, ("`S$=" + fn + "(x)` assigns only S$: R keeps its sentinel -12345 in every case."
                                         if mk else "`R=" + fn + "(s)` with R a double stores the result as a double: an "
                  "integer by its value, a single's 4 bytes then four zero bytes -- an exponent-0 one too (CVS of "
                  "00 10 00 00 leaves R 00 10 00 00 00 00 00 00) --, a double's 8; after an error R keeps its sentinel "
                  "-12345. Read in every case."), lambda c: True, assigned))
    return R
