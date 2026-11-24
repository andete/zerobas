#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""The shared model and rule builders for LEN / ASC / CHR$ / SPACE$ / STRING$ / INSTR's EXECUTABLE RULES
(docs/spec-method.md §3a, docs/keywords/spec-plan.md). The cases come from probes/basic/spec/kstr.py's committed run
(scratchpad/KST_run1.out); each page's module takes its own keyword's cases from `load(fn)` and its rules from
`rules(fn)`."""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
import kstr  # noqa: E402
import ramrec  # noqa: E402
from spec_rules import Rule  # noqa: E402

FIELDS = ["e", "rl", "fb", "lb", "rs", "rw", "r", "sl", "ss", "tl", "ts"]
OUTPUTS = {g: FIELDS for g in kstr.ORDER}
OUTPUTS_DESC = ("each case's error, the string result's length, first and last byte and two checksums, the numeric "
                "result's 8 bytes, the two source strings' lengths and sums")
SENT_S = bytes([250])            # R$ before every case
SENT_N = kstr.R_SENT             # R before every case
S, T = kstr.FX_S, kstr.FX_T      # the fixed expressions' S$ and T$

GROUPS_OF = {"LEN": ["SRC"], "ASC": ["SRC"], "CHR$": ["NUM"], "SPACE$": ["NUM", "OS"], "STRING$": ["STRN", "STRS", "OS"],
             "INSTR": ["INS1", "INS2", "INS3", "INS4"]}


def load(fn):
    """this keyword's cases: its matrix groups' and the fixed statements', the reference's and zerobas's in order"""
    out = {"ref": [], "zb": []}
    for g in GROUPS_OF[fn] + ["FX"]:
        cs = kstr.load(g)
        for who in out:
            out[who] += [c for c in cs[who] if c.fn == fn]
    return out


# --- what a case recorded ---

def _rstr(c):
    return c.rl, c.fb, c.lb, c.rs, c.rw


def str_result(c, b):
    """no error, R$ is the string b, R untouched"""
    return c.e == 0 and _rstr(c) == ramrec.digest(b) and c.r == SENT_N


def num_result(c, v):
    """no error, R is the number v, R$ untouched"""
    return c.e == 0 and c.r == v and _rstr(c) == ramrec.digest(SENT_S)


def error_is(c, code):
    """the case raised `code` and assigned nothing: R$ and R still hold their sentinels"""
    return c.e == code and _rstr(c) == ramrec.digest(SENT_S) and c.r == SENT_N


def outcome(c, model):
    """model(c) -> ("err", code) | ("str", bytes) | ("num", value)"""
    k, v = model(c)
    return error_is(c, v) if k == "err" else str_result(c, v) if k == "str" else num_result(c, v)


def kept(c):
    """S$ and T$ are left as they were"""
    return (c.sl, c.ss, c.tl, c.ts) == (len(c.s), sum(c.s) & 0xFFFF, len(c.t), sum(c.t) & 0xFFFF)


# --- the models ---

def byte_arg(v):
    """a 0..255 argument: (error, value) -- truncated toward zero, then 6 outside -32768..32767, else 5 outside 0..255"""
    t = math.trunc(v)
    if t < -32768 or t > 32767:
        return 6, None
    if t < 0 or t > 255:
        return 5, None
    return 0, t


def start_arg(v):
    """INSTR's start: as byte_arg, but 1..255"""
    e, t = byte_arg(v)
    if e == 0 and t == 0:
        return 5, None
    return e, t


def m_len(c):
    return "num", len(c.s)


def m_asc(c):
    return ("err", 5) if not c.s else ("num", c.s[0])


def m_chr(c):
    e, n = byte_arg(c.n)
    return ("err", e) if e else ("str", bytes([n]))


def m_space(c):
    e, n = byte_arg(c.n)
    return ("err", e) if e else ("str", b" " * n)


def m_string(c):
    """STRING$(N, C) / STRING$(N, S$): the count first, then the fill (a code, or a string's first byte)"""
    e, n = byte_arg(c.n)
    if e:
        return "err", e
    if c.src == "STRS":
        if not c.s:
            return "err", 5
        return "str", bytes([c.s[0]]) * n
    e, k = byte_arg(c.c)
    return ("err", e) if e else ("str", bytes([k]) * n)


def m_instr(c, empty_rule="ref"):
    """INSTR([N,]S$,T$): the start first; an empty T$ is found AT the start when the start is within S$, else 0;
    otherwise the first position >= the start where T$ occurs, 0 when none"""
    p = 1
    if c.n is not None:
        e, p = start_arg(c.n)
        if e:
            return "err", e
    h, t = c.s, c.t
    if not t:
        if empty_rule == "lenplus1":                 # a deliberately altered rule (a control, never the page's)
            return "num", min(p, len(h) + 1)
        return "num", p if p <= len(h) else 0
    i = h.find(t, p - 1)
    return "num", 0 if i < 0 else i + 1


# --- the fixed statements: what each one gives (S$ = "ABCDE", T$ = "CD") ---

FX_WANT = {
    "R=LEN(S$)": ("num", 5), "R=LEN (S$)": ("num", 5), "R=LEN( S$ )": ("num", 5), "R=LEN( S$)": ("num", 5),
    "R=LEN(S$+T$)": ("num", len(S + T)), 'R=LEN("")': ("num", 0), 'R=LEN("ABC")': ("num", 3),
    "R=ASC(S$)": ("num", S[0]), "R=ASC (S$)": ("num", S[0]), "R=ASC( S$ )": ("num", S[0]),
    "R=ASC( S$)": ("num", S[0]), "R=ASC(T$+S$)": ("num", T[0]), 'R=ASC("abc")': ("num", ord("a")),
    'R=ASC("")': ("err", 5), 'R=ASC(""+"")': ("err", 5),
    "R$=CHR$(65)": ("str", b"A"), "R$=CHR$ (65)": ("str", b"A"), "R$=CHR$( 65 )": ("str", b"A"),
    "R$=CHR$(65%)": ("str", b"A"), "R$=CHR$(&H41)": ("str", b"A"), "R$=CHR$(65.9!)": ("str", b"A"),
    "R$=SPACE$(3)": ("str", b"   "), "R$=SPACE$ (3)": ("str", b"   "), "R$=SPACE$( 3 )": ("str", b"   "),
    "R$=SPACE$(3%)": ("str", b"   "), "R$=SPACE$(&H3)": ("str", b"   "),
    "R$=STRING$(3,65)": ("str", b"AAA"), "R$=STRING$(3,S$)": ("str", S[:1] * 3),
    "R$=STRING$ (2,65)": ("str", b"AA"), "R$=STRING$( 2 , 65 )": ("str", b"AA"), "R$=STRING$(2, S$)": ("str", b"AA"),
    "R$=STRING$( 2,S$)": ("str", b"AA"), "R$=STRING$(2 ,S$)": ("str", b"AA"), "R$=STRING$(2,S$ )": ("str", b"AA"),
    "R$=STRING$(2%,&H41)": ("str", b"AA"), "R$=STRING$(2,T$+S$)": ("str", T[:1] * 2),
    "R=INSTR(S$,T$)": ("num", S.find(T) + 1), "R=INSTR(2,S$,T$)": ("num", S.find(T, 1) + 1),
    "R=INSTR (S$,T$)": ("num", 3), "R=INSTR( S$ , T$ )": ("num", 3), "R=INSTR( 2 , S$ , T$ )": ("num", 3),
    "R=INSTR( S$,T$)": ("num", 3), "R=INSTR(S$ ,T$)": ("num", 3), "R=INSTR(S$, T$)": ("num", 3),
    "R=INSTR(S$,T$ )": ("num", 3), "R=INSTR( 2,S$,T$)": ("num", 3), "R=INSTR(2 ,S$,T$)": ("num", 3),
    "R=INSTR(2, S$,T$)": ("num", 3), "R=INSTR(2,S$ ,T$)": ("num", 3), "R=INSTR(2,S$, T$)": ("num", 3),
    'R=INSTR( "ABCDE","CD")': ("num", 3), 'R=INSTR("ABCDE" ,"CD")': ("num", 3),
    'R=INSTR("ABCDE","CD" )': ("num", 3), "R=INSTR(2%,S$,T$)": ("num", 3), "R=INSTR(&H2,S$,T$)": ("num", 3),
    'R=INSTR("ABCDE","CD")': ("num", 3), "R=INSTR(7,S$+S$,T$)": ("num", (S + S).find(T, 6) + 1),
}


def fx_want(c):
    return FX_WANT[c.stmt]


def M(c):
    return c.src != "FX"


def fx_by(c, *whys):
    return c.src == "FX" and c.why in whys


def fx_has(c, *parts):
    return c.src == "FX" and any(p in c.why for p in parts)


def _common(tag, section, kind, whys_type, whys_own, whys_syntax, forms_text, whys_forms, own_text, syntax_text,
            type_text):
    """the rules every page has: the type, an argument's own error, the syntax, the forms, the sources kept"""
    return [
        Rule(f"R-{tag}-TYPE", section, type_text, lambda c: fx_by(c, *whys_type), lambda c: error_is(c, 13)),
        Rule(f"R-{tag}-OWNERR", section, own_text, lambda c: fx_by(c, *whys_own), lambda c: error_is(c, 11)),
        Rule(f"R-{tag}-SYNTAX", section, syntax_text, lambda c: fx_by(c, *whys_syntax), lambda c: error_is(c, 2)),
        Rule(f"R-{tag}-FORMS", section, forms_text, lambda c: fx_by(c, *whys_forms),
             lambda c: outcome(c, fx_want)),
        Rule(f"R-{tag}-KEEP", section,
             "The source strings are left as they were, in every case, error or not (S$ and T$ read back after "
             "every case).", lambda c: True, kept),
    ]


SPACES = ("a space before the parenthesis", "spaces around the argument", "a space after the parenthesis")


def rules(fn):
    if fn == "LEN":
        sec = "1. LEN(a$)"
        return [
            Rule("R-LEN-VALUE", sec,
                 "LEN(a$) is the number of characters in a$, 0 to 255, as a number; every byte counts, CHR$(0) and "
                 "CHR$(255) included (lengths 0, 1, 2, 3, 127, 128, 129, 254 and 255, first byte 0, 1, 65, 128, "
                 "255).", M, lambda c: outcome(c, m_len)),
        ] + _common("LEN", sec, "num",
                    ("a number as the argument", "the result is a number"),
                    ("the argument's own error",),
                    ("no argument", "an extra argument", "no closing parenthesis"),
                    "Spaces before the parenthesis and around the argument are allowed, and the argument may be any "
                    "string expression: a concatenation (S$+T$ is 7), an empty literal (0), a literal in the "
                    "program text (\"ABC\" is 3).",
                    SPACES + ("plain", "an expression", "an empty literal", "a literal (in the program text)"),
                    "An argument that fails to compute raises its own error (1/0: error 11).",
                    "No argument, a second argument, or no closing parenthesis is error 2 (Syntax error).",
                    "A number as the argument is error 13 (Type mismatch), and so is assigning the result to a "
                    "string variable: the result is a number.")
    if fn == "ASC":
        sec = "1. ASC(a$)"
        return [
            Rule("R-ASC-VALUE", sec,
                 "ASC(a$) is the code of a$'s first character, 0 to 255, as a number; the rest of the string is not "
                 "looked at (first bytes 0, 1, 65, 128, 255 at lengths 1 to 255).",
                 lambda c: M(c) and len(c.s) > 0, lambda c: outcome(c, m_asc)),
            Rule("R-ASC-EMPTY", sec,
                 "An empty string has no first character: ASC(\"\") is error 5 (Illegal function call) -- an empty "
                 "variable, an empty literal and an empty expression alike -- and nothing is assigned.",
                 lambda c: (M(c) and not c.s) or fx_by(c, "an empty literal", "an empty expression"),
                 lambda c: error_is(c, 5)),
        ] + _common("ASC", sec, "num",
                    ("a number as the argument", "the result is a number"),
                    ("the argument's own error",),
                    ("no argument", "an extra argument", "no closing parenthesis"),
                    "Spaces before the parenthesis and around the argument are allowed, and the argument may be any "
                    "string expression: ASC(T$+S$) is the code of T$'s first character, ASC(\"abc\") (a literal in "
                    "the program text) 97.",
                    SPACES + ("plain", "an expression", "a literal (in the program text)"),
                    "An argument that fails to compute raises its own error (1/0: error 11).",
                    "No argument, a second argument, or no closing parenthesis is error 2 (Syntax error).",
                    "A number as the argument is error 13 (Type mismatch), and so is assigning the result to a "
                    "string variable: the result is a number.")
    if fn in ("CHR$", "SPACE$"):
        tag, model = ("CHR", m_chr) if fn == "CHR$" else ("SPACE", m_space)
        sec = f"1. {fn}(n)"
        what = "the one character whose code is n" if fn == "CHR$" else "n spaces (\"\" for 0)"
        out = [
            Rule(f"R-{tag}-VALUE", sec,
                 f"The argument is truncated toward zero; from 0 to 255 the result is {what}. (-.9 and .9 give "
                 f"{'CHR$(0)' if fn == 'CHR$' else chr(34) * 2}, 255.9 gives {'CHR$(255)' if fn == 'CHR$' else '255 spaces'}: "
                 f"truncation, not rounding, and not INT.)",
                 lambda c: c.src == "NUM" and byte_arg(c.n)[0] == 0, lambda c: outcome(c, model)),
            Rule(f"R-{tag}-ERR5", sec,
                 "A truncated argument from -32768 to -1, or from 256 to 32767, is error 5 (Illegal function call), "
                 "and nothing is assigned. -32768.5 and 32767.9 are 5: the argument is truncated BEFORE the range "
                 "test.", lambda c: c.src == "NUM" and byte_arg(c.n)[0] == 5, lambda c: outcome(c, model)),
            Rule(f"R-{tag}-ERR6", sec,
                 "A truncated argument below -32768 or above 32767 is error 6 (Overflow), and nothing is assigned.",
                 lambda c: c.src == "NUM" and byte_arg(c.n)[0] == 6, lambda c: outcome(c, model)),
        ]
        if fn == "SPACE$":
            out.append(_room("SPACE", sec))
        return out + _common(tag, sec, "str",
                             ("a string as the argument", "the result is a string"),
                             ("the argument's own error",),
                             ("no argument", "an extra argument", "no closing parenthesis"),
                             f"Spaces before the parenthesis and around the argument are allowed, and so are an "
                             f"integer, a hex and a single argument: each gives what {fn}("
                             f"{'65' if fn == 'CHR$' else '3'}) gives"
                             + (" (65.9! is truncated to 65)." if fn == "CHR$" else "."),
                             SPACES + ("plain", "an integer argument", "a hex argument", "a single argument"),
                             "An argument that fails to compute raises its own error (1/0: error 11).",
                             "No argument, a second argument, or no closing parenthesis is error 2 (Syntax error).",
                             "A string as the argument is error 13 (Type mismatch), and so is assigning the result "
                             "to a numeric variable: the result is a string.")
    if fn == "STRING$":
        sec = "1. STRING$(n, code) and STRING$(n, a$)"
        return [
            Rule("R-STRING-CODE", sec,
                 "STRING$(n,code): both numbers are truncated toward zero; with both from 0 to 255 the result is n "
                 "copies of the character with that code (\"\" for 0).",
                 lambda c: c.src == "STRN" and m_string(c)[0] == "str", lambda c: outcome(c, m_string)),
            Rule("R-STRING-FILL", sec,
                 "STRING$(n,a$): with n from 0 to 255 and a$ not empty, the result is n copies of a$'s first "
                 "character; the rest of a$ is not used.",
                 lambda c: c.src == "STRS" and m_string(c)[0] == "str", lambda c: outcome(c, m_string)),
            Rule("R-STRING-COUNT", sec,
                 "The count is checked first, as LEFT$'s: truncated, error 6 outside -32768 to 32767, else error 5 "
                 "outside 0 to 255, whatever the second argument is (STRING$(-1,70000) is 5, STRING$(70000,-1) is "
                 "6). Nothing is assigned on an error.",
                 lambda c: c.src in ("STRN", "STRS") and byte_arg(c.n)[0] != 0, lambda c: outcome(c, m_string)),
            Rule("R-STRING-CODERANGE", sec,
                 "With a valid count, the code is checked the same way: error 6 outside -32768 to 32767, else 5 "
                 "outside 0 to 255 -- also when the count is 0, which needs no character.",
                 lambda c: c.src == "STRN" and byte_arg(c.n)[0] == 0 and byte_arg(c.c)[0] != 0,
                 lambda c: outcome(c, m_string)),
            Rule("R-STRING-EMPTY", sec,
                 "With a valid count, an empty fill string is error 5 (Illegal function call) -- also when the "
                 "count is 0.",
                 lambda c: c.src == "STRS" and byte_arg(c.n)[0] == 0 and not c.s, lambda c: outcome(c, m_string)),
            Rule("R-STRING-ORDER", sec,
                 "The count is checked before the second argument is even evaluated, and before the closing "
                 "parenthesis is looked for: STRING$(-1,1/0), STRING$(-1,5+\"A\") and STRING$(-1,\"A\" (unclosed) "
                 "are all error 5.",
                 lambda c: fx_by(c, "the count's range before the fill's own error",
                                 "the count's range before the fill's type", "no closing parenthesis after a bad count"),
                 lambda c: error_is(c, 5)),
            _room("STRING", sec),
        ] + _common("STRING", sec, "str",
                    ("a string as the count", "a string as the count, a code", "the count's type before the code's range",
                     "the result is a string"),
                    ("the count's own error", "the code's own error"),
                    ("no fill", "no argument", "an extra argument", "an extra argument, a code",
                     "no closing parenthesis after an empty fill"),
                    "Spaces before the parenthesis, around the arguments, and before or after a string fill are "
                    "allowed; an integer count and a hex code are numbers like any other; the fill may be a string "
                    "expression (T$+S$: T$'s first character).",
                    ("plain, a code", "plain, a string", "a space before the parenthesis", "spaces around the arguments",
                     "a space before the string fill", "an integer count, a hex code", "an expression as the fill",
                     "a space after the parenthesis, a string fill", "a space before the comma, a string fill",
                     "a space before the closing parenthesis, a string fill"),
                    "An argument that fails to compute raises its own error (1/0 as the count or the code: error 11).",
                    "No fill, no argument, a third argument, or no closing parenthesis (after an empty fill) is error 2 "
                    "(Syntax error): the parenthesis is checked before the empty fill.",
                    "A string as the count is error 13 (Type mismatch), checked before the code's range "
                    "(STRING$(\"A\",256) is 13); assigning the result to a numeric variable is 13 too.")
    if fn == "INSTR":
        sec = "1. INSTR([n,] a$, b$)"
        return [
            Rule("R-INSTR-FIND", sec,
                 "With b$ not empty: the result is the first position, counting from 1, at or after the start (1 "
                 "without one) where b$ occurs in a$, and 0 when it does not -- b$ longer than the rest of a$, a "
                 "start past the end, an empty a$. A start of 1.9 is 1: truncated. Haystacks of 130 and 255 "
                 "characters are searched to the end.",
                 lambda c: M(c) and c.t and start_arg(c.n if c.n is not None else 1)[0] == 0,
                 lambda c: outcome(c, m_instr)),
            Rule("R-INSTR-EMPTY", sec,
                 "With b$ empty: the result is the start (1 without one) when the start is within a$ (start <= "
                 "LEN(a$)), and 0 otherwise -- so INSTR(\"\",\"\") is 0, and INSTR(7,\"ABCABC\",\"\") is 0, not 7.",
                 lambda c: M(c) and not c.t and start_arg(c.n if c.n is not None else 1)[0] == 0,
                 lambda c: outcome(c, m_instr)),
            Rule("R-INSTR-START", sec,
                 "The start is truncated toward zero; below -32768 or above 32767 it is error 6, otherwise outside 1 "
                 "to 255 error 5, whatever the strings are (an empty b$ included). Start 0 is an error; start 255 "
                 "is not, at any length.",
                 lambda c: M(c) and c.n is not None and start_arg(c.n)[0] != 0, lambda c: outcome(c, m_instr)),
            Rule("R-INSTR-ORDER", sec,
                 "The start is checked before anything after it: a bad start wins over a number as either string, "
                 "over a third argument that fails to compute, and over a missing argument (INSTR(0,S$,5), "
                 "INSTR(0,5,T$), INSTR(0,S$,1/0) and INSTR(0,S$) are 5; INSTR(70000,S$,5) is 6).",
                 lambda c: fx_has(c, "the start's range before", "the start's overflow before"),
                 lambda c: error_is(c, 6 if "70000" in c.stmt else 5)),
        ] + _common("INSTR", sec, "num",
                    ("a number as the string to find", "a number as the string to search",
                     "a number as the string to find, a start", "the result is a number"),
                    ("the start's own error", "the second argument's own error", "the third argument's own error"),
                    ("a string as the start", "one string", "a start and one string", "a start only", "no argument",
                     "an extra argument", "an extra argument, a start", "no closing parenthesis"),
                    "Spaces are allowed before the parenthesis, after it, before and after every comma, and before "
                    "the closing parenthesis; an integer or hex start is a number like any other; the strings may "
                    "be literals in the program text or expressions (INSTR(7,S$+S$,T$) is 8).",
                    tuple(w for _f, _s, w in kstr.FX if _f == "INSTR" and ("space" in w or w in (
                        "plain", "plain, a start", "an integer start", "a hex start", "literals (in the program text)",
                        "an expression as the string to search"))),
                    "An argument that fails to compute raises its own error (1/0 as any argument: error 11).",
                    "One string, a start and one string, a start alone, no argument, a fourth (or, without a start, "
                    "a third) argument, or no closing parenthesis is error 2 (Syntax error). A string as the first of "
                    "three arguments is 2 as well: a string first means the two-string form, and the third argument "
                    "is one too many.",
                    "A number as either string is error 13 (Type mismatch), with or without a start; assigning the "
                    "result to a string variable is 13 too: the result is a number.")
    raise KeyError(fn)


def _room(tag, sec):
    return Rule(f"R-{tag}-ROOM", sec,
                "A result needs string space for all its characters: after CLEAR 200, with R$'s one-character "
                "previous value the only other string, a result of 199 characters fits and one of 200 or more is "
                "error 14 (Out of string space), nothing assigned.",
                lambda c: c.src == "OS",
                lambda c: (error_is(c, 14) if c.n >= 200 else
                           str_result(c, (b" " if c.fn == "SPACE$" else b"A") * int(c.n))))
