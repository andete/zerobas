#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""KSTR -- the measured cases behind docs/keywords/LEN.md, ASC.md, CHR$.md, SPACE$.md, STRING$.md and INSTR.md: the
strings region's second keyword probe (D-KWSPEC; docs/keywords/spec-plan.md, docs/spec-method.md §3a). The frame,
the record framing and the run file are the shared RAM-record harness's (probes/basic/spec/ramrec.py).

Clean room: typed BASIC in, RAM out. The program is TYPED on each machine; it evaluates every case and POKEs a record
of the outcome into RAM, which the harness reads after the program's own done flag. No reference ROM byte is read.

THE SETUP SEPARATES (spec-method §3a):
  * every case writes BOTH result variables' sentinels first -- R$ = CHR$(250), R = -12345 -- so an error (which
    assigns nothing) cannot read as a result, and a function that writes the wrong target is seen;
  * a numeric result is read as R's own 8 bytes (VARPTR; a double, DEFDBL), decoded exactly (ramrec.number): a
    result of 3.5, or a rounded one, cannot hide in an integer;
  * a string result is read as its length, first and last byte and two checksums (ramrec.STR_DIGEST), never through
    a string function; the sources S$ and T$ are read back the same way after every case (they are kept);
  * the sources are built in string space, byte by byte (CHR$ -- the CHR$ page's own keyword: a wrong CHR$ would
    show in every case's source digest, which a rule checks), never pointing into the program text;
  * numbers at the values where rival rules disagree: truncation vs rounding (.9, 1.5, 255.9), truncation vs INT
    (-.9), the overflow test before vs after truncation (-32768.5, 32767.9), both ends of each range;
  * INSTR's haystacks repeat their bytes ("ABCABC", "AAAAA", 254 x "A" + "B"), so "the first match", "a later match"
    and "the match at or after the start" give different positions; the long ones cross 128 and reach 255.

THE RECORD (22 bytes per case, from $C001):
  0 E      ERR after the case (0: none)
  1 RL, 2 FB, 3 LB, 4-5 RS, 6-7 RW    R$ (the string result): length, first / last byte, sum, sum of k * byte k
  8-15 R   R's 8 bytes (the numeric result)
  16 SL, 17-18 SS                     S$ after the case: length, sum
  19 TL, 20-21 TS                     T$ after the case: length, sum

THE GROUPS (case ids "KST <group> ..."):
  SRC   LEN(S$), ASC(S$): S$ of length 0, 1, 2, 3, 127, 128, 129, 254, 255, first byte 0 / 1 / 65 / 128 / 255, then
        CHR$(p) at position p
  NUM   CHR$(N), SPACE$(N): N in NUMS
  STRN  STRING$(N,C): N in NUMS, C in CODES
  STRS  STRING$(N,S$): N in NUMS, S$ in five fill strings ("" included)
  INS1..INS4  INSTR([N,]S$,T$): haystacks x needles x starts (one start "absent": the two-argument form)
  OS    SPACE$(N), STRING$(N,65) after CLEAR 200: where string space runs out
  FX    fixed statements (types, missing / extra arguments, spaces, nesting, the order of the checks; S$ = "ABCDE",
        T$ = "CD", both in string space)

    python3 probes/basic/spec/kstr.py [GROUP ...] [--out scratchpad/KST_run1.out]
(run through tools/agent_wt.py: it boots the VG-8020 and zerobas's NODISK machine)."""
import os
import sys
from fractions import Fraction
from decimal import Decimal
from types import SimpleNamespace as NS

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, HERE)
import ramrec  # noqa: E402

REC = 22
RUN = "KST_run1.out"
ABSENT = "-99999"
R_SENT = -12345

NUMS = ["-1E10", "-70000", "-32769", "-32768.5", "-32768", "-32767", "-1", "-.9", "-.1", "0", ".1", ".9", "1",
        "1.5", "2", "3", "4", "5", "6", "254", "255", "255.9", "256", "32767", "32767.9", "32768", "70000", "1E10"]
CODES = ["-1E10", "-32769", "-32768.5", "-32768", "-1", "-.9", "0", ".9", "1", "65", "65.9", "255", "255.9", "256",
         "32767.9", "32768", "70000"]
STARTS = [None, "-32769", "-1", "0", ".9", "1", "1.9", "2", "3", "4", "5", "6", "7", "129", "130", "131", "254",
          "255", "255.9", "256", "32768"]


def pos_bytes(first, n):
    """first, then CHR$(p) at position p (2..n)"""
    return bytes([first]) + bytes(range(2, n + 1)) if n else b""


A = ord("A")
HAY = {"E": b"", "ABCABC": b"ABCABC", "A5": b"AAAAA", "A254B": b"A" * 254 + b"B", "A128BC": b"A" * 128 + b"BC"}
NEEDLES = {"E": b"", "A": b"A", "B": b"B", "C": b"C", "AB": b"AB", "BC": b"BC", "CA": b"CA", "ABC": b"ABC",
           "AA": b"AA", "AAB": b"AAB", "Z": b"Z", "ABCABC": b"ABCABC", "ABCABCA": b"ABCABCA"}
NEEDLES_LONG = ["E", "A", "B", "AB", "BC", "AAB", "Z", "ABC"]
FILLS = {"E": b"", "Z0": b"\x00", "P789": bytes([7, 8, 9]), "P255": bytes([255, 1, 2]), "L255": pos_bytes(1, 255)}

INSTR_FN = ("INSTR", [f"IF N={ABSENT}! THEN {{2}}", "R=INSTR(N,S$,T$):RETURN", "R=INSTR(S$,T$):RETURN"])


def _groups():
    g = {}
    srcs = [("L0 B-", b"")] + [(f"L{n} B{b}", pos_bytes(b, n)) for n in (1, 2, 3, 127, 128, 129, 254, 255)
                               for b in (0, 1, 65, 128, 255)]
    g["SRC"] = dict(clear=2000, pairs=[(nm, s, "", b"") for nm, s in srcs], ns=["0"], cs=["0"],
                    fns=[("LEN", ["R=LEN(S$):RETURN"]), ("ASC", ["R=ASC(S$):RETURN"])])
    g["NUM"] = dict(clear=2000, pairs=[("", b"", "", b"")], ns=NUMS, cs=["0"],
                    fns=[("CHR$", ["R$=CHR$(N):RETURN"]), ("SPACE$", ["R$=SPACE$(N):RETURN"])])
    g["STRN"] = dict(clear=2000, pairs=[("", b"", "", b"")], ns=NUMS, cs=CODES,
                     fns=[("STRING$", ["R$=STRING$(N,C):RETURN"])])
    g["STRS"] = dict(clear=2000, pairs=[(nm, s, "", b"") for nm, s in FILLS.items()], ns=NUMS, cs=["0"],
                     fns=[("STRING$", ["R$=STRING$(N,S$):RETURN"])])
    st = [ABSENT if s is None else s for s in STARTS]
    g["INS1"] = dict(clear=2000, pairs=[("ABCABC", HAY["ABCABC"], t, NEEDLES[t]) for t in NEEDLES], ns=st, cs=["0"],
                     fns=[INSTR_FN])
    g["INS2"] = dict(clear=2000, pairs=[("E", HAY["E"], t, NEEDLES[t]) for t in NEEDLES], ns=st, cs=["0"],
                     fns=[INSTR_FN])
    g["INS3"] = dict(clear=2000, pairs=[("A5", HAY["A5"], t, NEEDLES[t]) for t in NEEDLES], ns=st, cs=["0"],
                     fns=[INSTR_FN])
    g["INS4"] = dict(clear=2000, pairs=[(h, HAY[h], t, NEEDLES[t]) for h in ("A254B", "A128BC")
                                        for t in NEEDLES_LONG], ns=st, cs=["0"], fns=[INSTR_FN])
    g["OS"] = dict(clear=200, pairs=[("", b"", "", b"")],
                   ns=["150", "190", "195", "196", "197", "198", "199", "200", "201", "255"], cs=["0"],
                   fns=[("SPACE$", ["R$=SPACE$(N):RETURN"]), ("STRING$", ["R$=STRING$(N,65):RETURN"])])
    return g


GROUPS = _groups()
GAPS = {"SRC": 3000.0, "NUM": 600.0, "STRN": 4000.0, "STRS": 3000.0, "INS1": 3000.0, "INS2": 3000.0,
        "INS3": 3000.0, "INS4": 6000.0, "OS": 600.0, "FX": 300.0}

FX = [
    # (the keyword, the statement, what it separates); S$ = "ABCDE", T$ = "CD"
    ("LEN", "R=LEN(S$)", "plain"),
    ("LEN", "R=LEN(5)", "a number as the argument"),
    ("LEN", "R=LEN(1/0)", "the argument's own error"),
    ("LEN", "R=LEN()", "no argument"),
    ("LEN", "R=LEN(S$,1)", "an extra argument"),
    ("LEN", "R=LEN(S$", "no closing parenthesis"),
    ("LEN", "R=LEN (S$)", "a space before the parenthesis"),
    ("LEN", "R=LEN( S$ )", "spaces around the argument"),
    ("LEN", "R=LEN(S$+T$)", "an expression"),
    ("LEN", 'R=LEN("")', "an empty literal"),
    ("LEN", 'R=LEN("ABC")', "a literal (in the program text)"),
    ("LEN", "R$=LEN(S$)", "the result is a number"),
    ("ASC", "R=ASC(S$)", "plain"),
    ("ASC", "R=ASC(5)", "a number as the argument"),
    ("ASC", "R=ASC(1/0)", "the argument's own error"),
    ("ASC", "R=ASC()", "no argument"),
    ("ASC", "R=ASC(S$,1)", "an extra argument"),
    ("ASC", "R=ASC(S$", "no closing parenthesis"),
    ("ASC", "R=ASC (S$)", "a space before the parenthesis"),
    ("ASC", "R=ASC( S$ )", "spaces around the argument"),
    ("ASC", "R=ASC(T$+S$)", "an expression"),
    ("ASC", 'R=ASC("")', "an empty literal"),
    ("ASC", 'R=ASC("abc")', "a literal (in the program text)"),
    ("ASC", 'R=ASC(""+"")', "an empty expression"),
    ("ASC", "R$=ASC(S$)", "the result is a number"),
    ("CHR$", "R$=CHR$(65)", "plain"),
    ("CHR$", 'R$=CHR$("A")', "a string as the argument"),
    ("CHR$", "R$=CHR$(1/0)", "the argument's own error"),
    ("CHR$", "R$=CHR$()", "no argument"),
    ("CHR$", "R$=CHR$(65,1)", "an extra argument"),
    ("CHR$", "R$=CHR$(65", "no closing parenthesis"),
    ("CHR$", "R$=CHR$ (65)", "a space before the parenthesis"),
    ("CHR$", "R$=CHR$( 65 )", "spaces around the argument"),
    ("CHR$", "R$=CHR$(65%)", "an integer argument"),
    ("CHR$", "R$=CHR$(&H41)", "a hex argument"),
    ("CHR$", "R$=CHR$(65.9!)", "a single argument"),
    ("CHR$", "R=CHR$(65)", "the result is a string"),
    ("SPACE$", "R$=SPACE$(3)", "plain"),
    ("SPACE$", 'R$=SPACE$("A")', "a string as the argument"),
    ("SPACE$", "R$=SPACE$(1/0)", "the argument's own error"),
    ("SPACE$", "R$=SPACE$()", "no argument"),
    ("SPACE$", "R$=SPACE$(1,1)", "an extra argument"),
    ("SPACE$", "R$=SPACE$(3", "no closing parenthesis"),
    ("SPACE$", "R$=SPACE$ (3)", "a space before the parenthesis"),
    ("SPACE$", "R$=SPACE$( 3 )", "spaces around the argument"),
    ("SPACE$", "R$=SPACE$(3%)", "an integer argument"),
    ("SPACE$", "R$=SPACE$(&H3)", "a hex argument"),
    ("SPACE$", "R=SPACE$(3)", "the result is a string"),
    ("STRING$", "R$=STRING$(3,65)", "plain, a code"),
    ("STRING$", "R$=STRING$(3,S$)", "plain, a string"),
    ("STRING$", 'R$=STRING$("A","A")', "a string as the count"),
    ("STRING$", 'R$=STRING$("A",65)', "a string as the count, a code"),
    ("STRING$", 'R$=STRING$("A",256)', "the count's type before the code's range"),
    ("STRING$", "R$=STRING$(2)", "no fill"),
    ("STRING$", "R$=STRING$()", "no argument"),
    ("STRING$", 'R$=STRING$(2,"A","A")', "an extra argument"),
    ("STRING$", "R$=STRING$(2,65,1)", "an extra argument, a code"),
    ("STRING$", 'R$=STRING$(2,""', "no closing parenthesis after an empty fill"),
    ("STRING$", 'R$=STRING$(-1,"A"', "no closing parenthesis after a bad count"),
    ("STRING$", "R$=STRING$ (2,65)", "a space before the parenthesis"),
    ("STRING$", "R$=STRING$( 2 , 65 )", "spaces around the arguments"),
    ("STRING$", "R$=STRING$(2, S$)", "a space before the string fill"),
    ("STRING$", "R$=STRING$(1/0,65)", "the count's own error"),
    ("STRING$", "R$=STRING$(2,1/0)", "the code's own error"),
    ("STRING$", "R$=STRING$(-1,1/0)", "the count's range before the fill's own error"),
    ("STRING$", 'R$=STRING$(-1,5+"A")', "the count's range before the fill's type"),
    ("STRING$", "R$=STRING$(2%,&H41)", "an integer count, a hex code"),
    ("STRING$", "R$=STRING$(2,T$+S$)", "an expression as the fill"),
    ("STRING$", "R=STRING$(2,65)", "the result is a string"),
    ("INSTR", "R=INSTR(S$,T$)", "plain"),
    ("INSTR", "R=INSTR(2,S$,T$)", "plain, a start"),
    ("INSTR", "R=INSTR(S$,5)", "a number as the string to find"),
    ("INSTR", "R=INSTR(1,5,T$)", "a number as the string to search"),
    ("INSTR", "R=INSTR(1,S$,5)", "a number as the string to find, a start"),
    ("INSTR", 'R=INSTR("A",S$,T$)', "a string as the start"),
    ("INSTR", "R=INSTR(S$)", "one string"),
    ("INSTR", "R=INSTR(1,S$)", "a start and one string"),
    ("INSTR", "R=INSTR(1)", "a start only"),
    ("INSTR", "R=INSTR()", "no argument"),
    ("INSTR", 'R=INSTR(S$,T$,"C")', "an extra argument"),
    ("INSTR", 'R=INSTR(1,S$,T$,"C")', "an extra argument, a start"),
    ("INSTR", "R=INSTR(S$,T$", "no closing parenthesis"),
    ("INSTR", "R=INSTR (S$,T$)", "a space before the parenthesis"),
    ("INSTR", "R=INSTR( S$ , T$ )", "spaces around the arguments"),
    ("INSTR", "R=INSTR( 2 , S$ , T$ )", "spaces around the arguments, a start"),
    ("INSTR", "R=INSTR(1/0,S$,T$)", "the start's own error"),
    ("INSTR", "R=INSTR(S$,1/0)", "the second argument's own error"),
    ("INSTR", "R=INSTR(1,S$,1/0)", "the third argument's own error"),
    ("INSTR", "R=INSTR(0,S$,5)", "the start's range before the type of the string to find"),
    ("INSTR", "R=INSTR(0,5,T$)", "the start's range before the type of the string to search"),
    ("INSTR", "R=INSTR(70000,S$,5)", "the start's overflow before the type"),
    ("INSTR", "R=INSTR(0,S$,1/0)", "the start's range before the third argument's own error"),
    ("INSTR", "R=INSTR(0,S$)", "the start's range before a missing argument"),
    ("INSTR", "R=INSTR(2%,S$,T$)", "an integer start"),
    ("INSTR", "R=INSTR(&H2,S$,T$)", "a hex start"),
    ("INSTR", 'R=INSTR("ABCDE","CD")', "literals (in the program text)"),
    ("INSTR", "R=INSTR(7,S$+S$,T$)", "an expression as the string to search"),
    ("INSTR", "R$=INSTR(S$,T$)", "the result is a number"),
    # which space INSTR( S$ , T$ ) trips on (zerobas: error 2, the reference: 3) -- one space at a time
    ("INSTR", "R=INSTR( S$,T$)", "a space after the parenthesis"),
    ("INSTR", "R=INSTR(S$ ,T$)", "a space before the comma"),
    ("INSTR", "R=INSTR(S$, T$)", "a space after the comma"),
    ("INSTR", "R=INSTR(S$,T$ )", "a space before the closing parenthesis"),
    ("INSTR", "R=INSTR( 2,S$,T$)", "a space after the parenthesis, a start"),
    ("INSTR", "R=INSTR(2 ,S$,T$)", "a space after the start"),
    ("INSTR", "R=INSTR(2, S$,T$)", "a space before the string to search, a start"),
    ("INSTR", "R=INSTR(2,S$ ,T$)", "a space before the second comma, a start"),
    ("INSTR", "R=INSTR(2,S$, T$)", "a space after the second comma, a start"),
    ("INSTR", 'R=INSTR( "ABCDE","CD")', "a space after the parenthesis, a literal"),
    ("INSTR", 'R=INSTR("ABCDE" ,"CD")', "a space before the comma, a literal"),
    ("LEN", "R=LEN( S$)", "a space after the parenthesis"),
    ("ASC", "R=ASC( S$)", "a space after the parenthesis"),
    ("STRING$", "R$=STRING$( 2,S$)", "a space after the parenthesis, a string fill"),
    ("STRING$", "R$=STRING$(2 ,S$)", "a space before the comma, a string fill"),
    ("INSTR", 'R=INSTR("ABCDE","CD" )', "a space before the closing parenthesis, a literal"),
    ("STRING$", "R$=STRING$(2,S$ )", "a space before the closing parenthesis, a string fill"),
]
FX_S, FX_T = b"ABCDE", b"CD"

RECORD = [
    "900 V=VARPTR(R$):GOSUB 950:POKE A,E:POKE A+1,RL:POKE A+2,FB:POKE A+3,LB",
    "910 POKE A+4,S-INT(S/256)*256:POKE A+5,INT(S/256):POKE A+6,W-INT(W/256)*256:POKE A+7,INT(W/256)",
    "920 V=VARPTR(R):FOR K=0 TO 7:POKE A+8+K,PEEK(V+K):NEXT",
    "930 V=VARPTR(S$):GOSUB 950:POKE A+16,RL:POKE A+17,S-INT(S/256)*256:POKE A+18,INT(S/256)",
    "940 V=VARPTR(T$):GOSUB 950:POKE A+19,RL:POKE A+20,S-INT(S/256)*256:POKE A+21,INT(S/256):A=A+22:RETURN",
] + ramrec.STR_DIGEST + [ramrec.ERRLINE]
# a string from DATA: IR runs of (count IC, byte IB); IB < 0 is "the position" (1-based). Built in string space.
BUILD = [
    "300 READ IR:Q$=\"\":IP=0:IF IR>0 THEN FOR I=1 TO IR:READ IC,IB:FOR J=1 TO IC:IP=IP+1:"
    "Q$=Q$+CHR$(IB-(IB<0)*(IP-IB)):NEXT J,I",
    "310 RETURN",
]


def runs(b):
    """b as (count, byte) runs; a stretch where byte == position is one run of byte -1"""
    out = []
    i = 0
    while i < len(b):
        j = i
        if b[i] == i + 1:
            while j < len(b) and b[j] == j + 1:
                j += 1
            out.append((j - i, -1))
        else:
            while j < len(b) and b[j] == b[i] and b[j] != j + 1:
                j += 1
            out.append((j - i, b[i]))
        i = j
    return out


def _rebuild(rs):
    b = []
    for n, x in rs:
        for _ in range(n):
            b.append(len(b) + 1 if x < 0 else x)
    return bytes(b)


def spec_values(b):
    rs = runs(b)
    assert _rebuild(rs) == b
    return [str(len(rs))] + [str(v) for r in rs for v in r]


def num(text):
    return None if text is None or text == ABSENT else Fraction(Decimal(text))


def program(group):
    """the typed lines (numbered program + RUN) and the case list [(id, meta)] in record order"""
    if group == "FX":
        # each statement on a line of its own, the record on the next: RESUME NEXT after any error in the statement
        # (an unclosed parenthesis included) lands on the record, never inside the statement's own text
        lines = [ramrec.head(2000), "20 GOSUB 300:S$=Q$:GOSUB 300:T$=Q$:GOTO 2000"]
        cases = []
        for i, (fn, stmt, why) in enumerate(FX):
            lines.append(f"{2000 + 2 * i} E=0:R$=CHR$(250):R={R_SENT}:{stmt}")
            lines.append(f"{2001 + 2 * i} GOSUB 900")
            cases.append((f"KST FX {i}", dict(fn=fn, stmt=stmt, why=why, s=FX_S, t=FX_T)))
        lines += [f"{2000 + 2 * len(FX)} " + ramrec.TAIL] + BUILD + RECORD
        lines += ramrec.data(1000, spec_values(FX_S) + spec_values(FX_T))
        return lines + ["RUN"], cases
    G = GROUPS[group]
    nf = len(G["fns"])
    lines = [ramrec.head(G["clear"]),
             "20 READ I2:DIM NA(I2):FOR I=1 TO I2:READ NA(I):NEXT",
             "30 READ I3:DIM CA(I3):FOR I=1 TO I3:READ CA(I):NEXT",
             "40 READ I1:FOR J1=1 TO I1:GOSUB 300:S$=Q$:GOSUB 300:T$=Q$",
             f"50 FOR J2=1 TO I2:FOR J3=1 TO I3:FOR J4=1 TO {nf}:N=NA(J2):C=CA(J3):E=0:R$=CHR$(250):R={R_SENT}",
             "60 GOSUB 200:GOSUB 900:NEXT J4,J3,J2,J1",
             "70 " + ramrec.TAIL,
             "200 ON J4 GOSUB " + ",".join(str(210 + 10 * k) for k in range(nf)) + ":RETURN"]
    for k, (_fn, bodies) in enumerate(G["fns"]):
        base = 210 + 10 * k
        for i, body in enumerate(bodies):
            lines.append(f"{base + i} " + body.replace("{2}", str(base + 2)))
    lines += BUILD + RECORD
    vals = [str(len(G["ns"]))] + G["ns"] + [str(len(G["cs"]))] + G["cs"] + [str(len(G["pairs"]))]
    for _sn, s, _tn, t in G["pairs"]:
        vals += spec_values(s) + spec_values(t)
    lines += ramrec.data(1000, vals)
    cases = []
    for sn, s, tn, t in G["pairs"]:
        for nt in G["ns"]:
            for ct in G["cs"]:
                for fn, _b in G["fns"]:
                    if group == "SRC":
                        cid = f"KST SRC {fn} {sn}"
                    elif group in ("NUM", "OS"):
                        cid = f"KST {group} {fn} N{nt}"
                    elif group == "STRN":
                        cid = f"KST STRN N{nt} C{ct}"
                    elif group == "STRS":
                        cid = f"KST STRS N{nt} F{sn}"
                    else:
                        cid = f"KST {group} H{sn} T{tn} P{'-' if nt == ABSENT else nt}"
                    cases.append((cid, dict(fn=fn, s=s, t=t, sname=sn, tname=tn, n=num(nt),
                                            ntext=None if nt == ABSENT else nt, c=num(ct), ctext=ct)))
    return lines + ["RUN"], cases


def decode(hexs, n):
    rs, why = ramrec.frame(hexs, n, REC)
    if rs is None:
        return None, why
    out = []
    for r in rs:
        try:
            rv = ramrec.number(r[8:16])
        except ValueError:
            rv = None
        out.append(dict(e=r[0], rl=r[1], fb=r[2], lb=r[3], rs=r[4] | r[5] << 8, rw=r[6] | r[7] << 8, r=rv,
                        sl=r[16], ss=r[17] | r[18] << 8, tl=r[19], ts=r[20] | r[21] << 8))
    return out, None


ORDER = ["SRC", "NUM", "STRN", "STRS", "INS1", "INS2", "INS3", "INS4", "OS", "FX"]


def load(group, run=RUN):
    """the cases of one group from the committed run file: {"ref": [...], "zb": [...]}"""
    sec = ramrec.read_section(os.path.join(ROOT, "scratchpad", run), group)
    _, cases = program(group)
    out = {}
    for who, h in sec.items():
        recs, why = decode(h, len(cases))
        if recs is None:
            sys.exit(f"FAIL: {run} {group} {who}: {why}")
        out[who] = [NS(src=group, id=cid, **meta, **r) for (cid, meta), r in zip(cases, recs)]
    return out


def main(argv):
    groups = [g for g in ORDER if g in argv] or ORDER
    path = os.path.join(ROOT, "scratchpad", RUN)
    if "--out" in argv:
        path = os.path.join(ROOT, argv[argv.index("--out") + 1])
    if "--lines" in argv:
        for g in groups:
            print("\n".join(program(g)[0]))
        return 0
    for g in groups:
        lines, cases = program(g)
        cap = ramrec.measure(lines, len(cases), REC, GAPS[g])
        bad = []
        for who in ("ref", "zb"):
            recs, why = decode(cap[who], len(cases))
            if recs is None:
                bad.append(f"{who}: {why}")
        text = open(path).read() if os.path.exists(path) else ""
        open(path, "w").write(ramrec.write_section(text, g, cap, len(cases), bad))
        print(f"{g}: {len(cases)} cases; {'; '.join(bad) or 'both complete'}", flush=True)
        if not bad:
            ref, zb = (decode(cap[w], len(cases))[0] for w in ("ref", "zb"))
            diff = [cases[i][0] for i in range(len(cases)) if ref[i] != zb[i]]
            print(f"  {len(diff)} cases differ" + (": " + ", ".join(diff[:12]) if diff else ""), flush=True)
    print(f"wrote {os.path.relpath(path, ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
