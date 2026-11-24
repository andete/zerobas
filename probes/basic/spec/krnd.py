#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""KRND -- the measured cases behind docs/keywords/RND.md: the maths region's last keyword (D-KWSPEC;
docs/keywords/spec-plan.md §2 region 2, docs/spec-method.md §3a). RND is a SEQUENCE, not a function of its argument,
so this probe is a sequence harness: every record is one STEP of a sequence, and it holds the generator's state
AFTER the step as well as the step's result. The frame, the record framing and the run file are the shared RAM-record
harness's (probes/basic/spec/ramrec.py); the USR readout of the result's type is kmath.py's (spec-plan §7 item 3).

Clean room: typed BASIC in, RAM out. The program is TYPED on each machine; it POKEs a record per step into RAM,
which the harness reads after the program's own done flag. No reference ROM byte is read. The only work-area cells
PEEKed are the 8 bytes at $F857..$F85E: RNDX, which C-BIOS's source (an admissible source for published work-area
ADDRESSES, docs/allowed-sources.md) names "last calculated random double". They are DATA, read and never followed.
(The probe itself shows they are the generator's state: they change on every positive RND, stay on RND(0), and are
set by a negative argument whatever came before -- the rules R-RND-NEXT / -REPEAT / -SEED.)

THE SETUP SEPARATES (spec-method §3a):
  * the state is read after EVERY step, so each step's rule predicts from the state the previous record read
    ("local"), and a second rule predicts the whole group from the start-up constant and the arguments alone
    ("chain", reading no measured state) -- neither replays the reference's own output;
  * every case starts with R = -12345 and the USR type cell at 255, so an error, which assigns nothing, cannot read
    as a result; a step either assigns `R=RND(N)` (R's 8 bytes) or evaluates `Q=USR(RND(N))`, where USR is kmath's
    18-byte routine at $BF00 that copies VALTYP and DAC (the result unconverted) into the probe's memory; ID rows
    (`Q=USR(N)`, no RND) check that readout on each argument type, and the loader refuses a run where they fail;
  * an argument is READ into a variable of the case's own type (N% / N! / N#) whose own bytes are recorded before the
    call, so the rules work from the value given;
  * the arguments sit where rival rules disagree: every type, both ends of each range, the same digits at different
    exponents (-1, -.001, -1E9), the same value with 6 and 14 digits (-.333333! / -.33333333333333#), and reseeds
    chosen (by inverting the recurrence) so that the NEXT state is 0, 1, 10, 12345, 10^13 - 1, 10^13 or 99...9 --
    a result with leading zero digits, or none at all.

THE RECORD (34 bytes per step, from $C001):
  0 E           ERR after the step (0: none)
  1-8 ARG       the argument's own bytes, read before the call (2 / 4 / 8 of them, the rest 0); FX / BOOT: all 0
  9-16 R        R's 8 bytes after the step (a double; -12345 unless the step assigned it)
  17 VT         the result's type as USR saw it (2 / 4 / 8; 255: no USR in this step)
  18-25 DAC     DAC's 8 bytes as USR saw them
  26-33 RNDX    $F857..$F85E after the step

THE GROUPS (case ids "KRN <group> <i>"):
  BOOT  DIRECT MODE from power-on, before any program line: RNDX at power-on, RND(0), RND(1), CLS, a program line
        entered, CLEAR, NEW, RUN of a one-line program
  RUNR  a typed program, the state stepped from direct mode (RND(1) twice, RND(-7)), then RUN: the state at RUN's
        first line, then after CLEAR
  GOTO  the same program and the same direct steps, started with GOTO 5 instead of RUN
  GOTO2 as GOTO, with a program line (99 REM) entered after the direct steps
  SQ1   after CLEAR: positive and zero arguments of every type, R and USR steps, other maths between
  SQ2   reseeds: 46 negative arguments, each followed by RND(1), USR(RND(1)) and RND(0)
  SQ3   a long run: RND(-1), then 200 x RND(1) with RND(0) every 25
  FX    fixed statements: errors (none may move the state), forms, literals, nesting, evaluation order,
        non-canonical arguments (exponent byte 0 with digit bytes)

    python3 probes/basic/spec/krnd.py [GROUP ...] [--out scratchpad/KRN_run1.out]
(run through tools/agent_wt.py: it boots the VG-8020 and zerobas's NODISK machine, once per group)."""
import os
import sys
from types import SimpleNamespace as NS

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, HERE)
import ramrec  # noqa: E402
import kmath  # noqa: E402

REC = 34
RUN = "KRN_run1.out"
R_SENT = -12345
RNDX = 0xF857
TY = {1: ("I", "%", 2), 2: ("S", "!", 4), 3: ("D", "#", 8)}
OPS = {1: "R", 2: "U", 3: "OTHER", 4: "PEEK", 5: "ID"}

# ---- the program groups' shared lines ---------------------------------------------------------------------------
HEAD = ["10 CLEAR 2000,&HBF00:DEFDBL A-Z:DEFINT I-K:ON ERROR GOTO 800:POKE &HC000,0:A=&HC001",
        "20 FOR K=0 TO 17:READ X:POKE &HBF00+K,X:NEXT:DEFUSR=&HBF00",
        '25 S$="12"']
RECORD = [
    ramrec.ERRLINE,
    f"880 E=0:R={R_SENT}:POKE &HBF80,255:FOR K=1 TO 8:POKE A+K,0:NEXT:RETURN",
    "900 POKE A,E:V=VARPTR(R):FOR K=0 TO 7:POKE A+9+K,PEEK(V+K):POKE A+18+K,PEEK(&HBF81+K)"
    ":POKE A+26+K,PEEK(&HF857+K):NEXT",
    "910 POKE A+17,PEEK(&HBF80):A=A+34:RETURN",
]
SEQ_BODY = [
    "30 READ I2:FOR J2=1 TO I2:READ J4,J5:GOSUB 880:ON J5 GOSUB 300,310,320",
    "40 ON J4 GOSUB 400,410,420,430,440",
    "50 GOSUB 900:NEXT J2",
    "60 " + ramrec.TAIL,
    "300 READ N%:V=VARPTR(N%):FOR K=0 TO 1:POKE A+1+K,PEEK(V+K):NEXT:RETURN",
    "310 READ N!:V=VARPTR(N!):FOR K=0 TO 3:POKE A+1+K,PEEK(V+K):NEXT:RETURN",
    "320 READ N#:V=VARPTR(N#):FOR K=0 TO 7:POKE A+1+K,PEEK(V+K):NEXT:RETURN",
    "400 ON J5 GOTO 401,402,403",
    "401 R=RND(N%):RETURN",
    "402 R=RND(N!):RETURN",
    "403 R=RND(N#):RETURN",
    "410 ON J5 GOTO 411,412,413",
    "411 Q=USR(RND(N%)):RETURN",
    "412 Q=USR(RND(N!)):RETURN",
    "413 Q=USR(RND(N#)):RETURN",
    "420 X=SIN(1)*EXP(1)/SQR(2)+LOG(3)+ATN(1)+INT(-2.5)+ABS(-1):Y$=STR$(X)+HEX$(7):RETURN",
    "430 RETURN",
    "440 ON J5 GOTO 441,442,443",
    "441 Q=USR(N%):RETURN",
    "442 Q=USR(N!):RETURN",
    "443 Q=USR(N#):RETURN",
]

# ---- the sequences --------------------------------------------------------------------------------------------
# a step: (op, type, DATA text); op 1 R=RND(N), 2 Q=USR(RND(N)), 3 other maths (no RND), 4 no statement, 5 Q=USR(N)
POS = [(1, "1"), (1, "7"), (1, "32767"), (2, "1"), (2, ".3"), (2, "1E-64"), (2, "9.99999E62"), (3, "1"), (3, ".5"),
       (3, "1D-64"), (3, "9.9999999999999D62"), (3, "12345.678901234")]
ZERO = [(1, "0"), (2, "0"), (2, "-0"), (3, "0"), (3, "-0")]
SQ1 = [(4, 3, "0"), (5, 1, "7"), (5, 2, ".3"), (5, 3, ".12345678901234"), (4, 3, "0")]
SQ1 += [(1, 3, "1"), (1, 3, "0"), (2, 3, "1"), (2, 3, "0")]
SQ1 += [(1, t, x) for t, x in POS] + [(2, t, x) for t, x in POS]
SQ1 += [(1, t, x) for t, x in ZERO] + [(2, t, x) for t, x in ZERO]
SQ1 += [(3, 3, "0"), (1, 3, "1"), (3, 3, "0"), (3, 3, "0"), (1, 3, "0")]
SQ1 += [(1, 3, "1")] * 12 + [(1, 1, "1")] * 4 + [(1, 2, "1")] * 4

# reseeds; the last group are the PRE-IMAGES of chosen states (pre(T) = (T - C) / A mod 10^14), so the step after the
# reseed lands on T exactly: T = 0, 1, 10, 12345, 10^13 - 1, 10^13, 99999999999999, 12300000000000, 50000000000000
SEEDS = [(1, "-1"), (1, "-2"), (1, "-5"), (1, "-10"), (1, "-100"), (1, "-12345"), (1, "-32767"), (1, "-32768"),
         (2, "-1"), (2, "-.001"), (2, "-1E9"), (2, "-.333333"), (2, "-.5"), (2, "-5"), (2, "-1E-64"),
         (2, "-9.99999E62"), (2, "-123456"), (2, "-.000001"), (2, "-7"),
         (3, "-1"), (3, "-1D-64"), (3, "-1D62"), (3, "-9.9999999999999D62"), (3, "-.33333333333333"),
         (3, "-.12345678901234"), (3, "-12345678901234"), (3, "-.5"), (3, "-.99999999999999"), (3, "-7"),
         (3, "-1.0000000000001"),
         (3, "-.30494897914141"), (3, "-.3497607753522"), (3, "-.75306694124931"), (3, "-.50657320134396"),
         (3, "-.16013718293062"), (3, "-.20494897914141"), (3, "-.26013718293062"), (3, "-.27948753692280"),
         (3, "-.80494897914141"), (3, "-.91387465484261"),
         (2, "-.304949"), (1, "-3"), (2, "-3"), (3, "-3"), (2, "-.3"), (3, "-.3")]
SQ2 = [(4, 3, "0")]
for i, (t, x) in enumerate(SEEDS):
    SQ2 += [(1 + i % 2, t, x), (1, 3, "1"), (2, 3, "1"), (1, 3, "0")]
SQ3 = [(4, 3, "0"), (1, 3, "-1")]
for i in range(200):
    SQ3.append((1, 3, "1"))
    if i % 25 == 24:
        SQ3.append((1, 3, "0"))
SEQS = {"SQ1": SQ1, "SQ2": SQ2, "SQ3": SQ3}

# ---- FX: fixed statements, one per case, the state flowing through them in order --------------------------------
# (stmt, why, kind, steps); kind: "peek" (no call), "lit" (USR of a literal, no RND: its own type and bytes, the next
# row's seed), "err" (an error, no step), "val" (RND steps: R or USR), "order" (two calls in one expression)
# For "val" rows, `steps` is the RND calls in the order the rule claims they run: a list of ("pos" | "zero" |
# ("seed", digits) | ("seedres", k)) -- "seedres": a reseed from the digits of the k-th earlier step's own result in
# this statement (RND(-RND(1))).
PRE0 = "N!=1:V=VARPTR(N!):POKE V,0:"
PRE80 = "N!=1:V=VARPTR(N!):POKE V,128:"
PRE0D = "N#=.12345678901234#:V=VARPTR(N#):POKE V,0:"
PRE80D = "N#=.12345678901234#:V=VARPTR(N#):POKE V,128:"
FX = [
    ("R=-12345", "the state after CLEAR", "peek", None),
    ('R=RND("A")', "a string literal as the argument", "err", 13),
    ("R=RND(S$)", "a string variable as the argument", "err", 13),
    ("R$=RND(1)", "the result assigned to a string", "err", 13),
    ("R=RND()", "no argument", "err", 2),
    ("R=RND(1,2)", "an extra argument", "err", 2),
    ("R=RND(-1,2)", "a reseed with an extra argument", "err", 2),
    ("R=RND(1", "no closing parenthesis", "err", 2),
    ("R=RND(-1.5", "a reseed, no closing parenthesis", "err", 2),
    ("R=RND", "no parenthesis", "err", 2),
    ("R=RND(1/0)", "the argument's own error", "err", 11),
    ("R=RND(-1/0)", "a negative argument's own error", "err", 11),
    ('R=RND(1/0', "the argument's own error, no closing parenthesis", "err", 11),
    ('R=RND("A"', "a string argument, no closing parenthesis", "err", 2),
    ('R=RND("A",2)', "a string argument, then an extra argument", "err", 2),
    ("RANDOMIZE 1", "RANDOMIZE (not MSX1 BASIC)", "err", 2),
    ("R=RND(1)", "a literal 1", "val", ["pos"]),
    ("R=RND (1)", "a space before the parenthesis", "val", ["pos"]),
    ("R=RND( 1 )", "spaces around the argument", "val", ["pos"]),
    ("R=RND(0)", "a literal 0", "val", ["zero"]),
    ("R=RND(-0)", "minus zero", "val", ["zero"]),
    ("Q=USR(-1)", "the literal -1: its own type and bytes (apparatus)", "lit", None),
    ("R=RND(-1)", "a literal -1 (a reseed)", "val", ["seed"]),
    ("Q=USR(-.001)", "the literal -.001: its own type and bytes (apparatus)", "lit", None),
    ("R=RND(-.001)", "-.001: the digits of -1, another exponent", "val", ["seed"]),
    ("Q=USR(-1E9)", "the literal -1E9: its own type and bytes (apparatus)", "lit", None),
    ("R=RND(-1E9)", "-1E9", "val", ["seed"]),
    ("Q=USR(-1/3)", "the literal -1/3: its own type and bytes (apparatus)", "lit", None),
    ("R=RND(-1/3)", "-1/3: a double expression", "val", ["seed"]),
    ("Q=USR(-1!/3)", "the literal -1!/3: its own type and bytes (apparatus)", "lit", None),
    ("R=RND(-1!/3)", "-1!/3: a single expression", "val", ["seed"]),
    ("Q=USR(&HFFFF)", "the literal &HFFFF: its own type and bytes (apparatus)", "lit", None),
    ("R=RND(&HFFFF)", "&HFFFF: the integer -1", "val", ["seed"]),
    ("Q=USR(&H8000)", "the literal &H8000: its own type and bytes (apparatus)", "lit", None),
    ("R=RND(&H8000)", "&H8000: the integer -32768", "val", ["seed"]),
    ("Q=USR(-32768)", "the literal -32768: its own type and bytes (apparatus)", "lit", None),
    ("R=RND(-32768)", "minus the literal 32768 (a single)", "val", ["seed"]),
    ("R=RND(.5)", "a literal .5", "val", ["pos"]),
    ("R=RND(1E-64)", "the smallest positive single", "val", ["pos"]),
    ("R=RND(RND(1))", "nested: a positive inner result", "val", ["pos", "pos"]),
    ("R=RND(RND(0))", "nested: RND(0) as the argument", "val", ["zero", "pos"]),
    ("R=RND(-RND(1))", "a reseed from the digits of RND(1)", "val", ["pos", ("seedres", 0)]),
    ("R=RND(-RND(0))", "a reseed from the digits of RND(0)", "val", ["zero", ("seedres", 0)]),
    ("R=RND(1)-RND(0)", "left to right: RND(1), then RND(0) repeats it", "order", ["pos", "zero"]),
    ("R=RND(0)-RND(1)", "left to right: RND(0), then RND(1)", "order", ["zero", "pos"]),
    ("Q=USR(RND(1))", "the type of RND(1)", "val", ["pos"]),
    ("Q=USR(RND(0))", "the type of RND(0)", "val", ["zero"]),
    ("Q=USR(RND(-1))", "the type of RND(-1)", "val", ["seed"]),
    ("Q=USR(RND(1%))", "the type, an integer argument", "val", ["pos"]),
    ("Q=USR(RND(1!))", "the type, a single argument", "val", ["pos"]),
    (PRE0 + "R=RND(N!)", "a single, exponent byte 0, digit bytes 10 00 00", "val", None),
    (PRE80 + "R=RND(N!)", "a single, exponent byte 80, digit bytes 10 00 00", "val", None),
    (PRE0D + "R=RND(N#)", "a double, exponent byte 0, digit bytes 12 34 ... 34", "val", None),
    (PRE80D + "R=RND(N#)", "a double, exponent byte 80, digit bytes 12 34 ... 34", "val", None),
    ("R=RND(-.30494897914141#)", "the reseed whose next state is 0", "val", ["seed"]),
    ("R=RND(1)", "the step from state 0", "val", ["pos"]),
    ("R=RND(-.30494897914141#)", "state 0 again", "val", ["seed"]),
    ("R=RND(0)", "RND(0) in state 0", "val", ["zero"]),
    ("Q=USR(RND(0))", "the type and bytes of RND(0) in state 0", "val", ["zero"]),
    ("R=RND(-RND(0))", "a reseed from RND(0) in state 0 (an exact zero: RND(0)'s rule)", "val", None),
    ("R=-12345", "the state at the end", "peek", None),
]
GAPS = {"BOOT": 2500.0, "RUNR": 2500.0, "GOTO": 2500.0, "GOTO2": 2500.0, "SQ1": 3000.0, "SQ2": 4000.0, "SQ3": 5000.0, "FX": 2500.0}
ORDER = ["BOOT", "RUNR", "GOTO", "GOTO2", "SQ1", "SQ2", "SQ3", "FX"]


def _drec(i, stmt):
    """a DIRECT-mode line that runs `stmt` and records step i (R# and RNDX)"""
    return (f"{stmt}:B=&HC001+{REC * i}:POKE B,0:V=VARPTR(R#):FOR K=0 TO 7:POKE B+9+K,PEEK(V+K)"
            f":POKE B+26+K,PEEK(&HF857+K):NEXT:POKE B+17,255")


# BOOT: (typed line, None) for an unrecorded line; (stmt, why) for a recorded step
BOOT = [("R#=-12345", "power-on"),
        ("R#=RND(0)", "RND(0) at power-on"),
        ("R#=RND(1)", "the first RND(1) after power-on"),
        ("R#=RND(1)", "the second"),
        ("CLS:R#=-12345", "after CLS"),
        ("R#=RND(1)", "RND(1) after CLS"),
        ("10 REM", None),
        ("R#=-12345", "after a program line is entered"),
        ("R#=RND(1)", "RND(1) after it"),
        ("CLEAR:R#=-12345", "after CLEAR"),
        ("R#=RND(1)", "RND(1) after CLEAR"),
        ("R#=RND(-1)", "RND(-1)"),
        ("NEW", None),
        ("R#=-12345", "after NEW"),
        ("R#=RND(1)", "RND(1) after NEW"),
        ("R#=RND(-5)", "RND(-5)"),
        ("20 REM", None),
        ("RUN", None),
        ("R#=-12345", "after RUN (of a one-line REM program)"),
        ("R#=RND(1)", "RND(1) after it"),
        ("R#=RND(1)", "and again")]

RUNPROG = [
    "5 DEFDBL A-Z:DEFINT I-K:E=0:R=-12345:A=&HC001:GOSUB 900",
    "6 R=RND(1):GOSUB 900",
    "7 R=RND(0):GOSUB 900",
    f"10 CLEAR 2000,&HBF00:DEFDBL A-Z:DEFINT I-K:A=&HC001+{3 * REC}:E=0:R=-12345:GOSUB 900",
    "20 R=RND(1):GOSUB 900",
    "30 " + ramrec.TAIL,
    "900 V=VARPTR(R):FOR K=0 TO 8:POKE A+K,0:NEXT:FOR K=0 TO 7:POKE A+9+K,PEEK(V+K):POKE A+18+K,0"
    ":POKE A+26+K,PEEK(&HF857+K):NEXT:POKE A+17,255:A=A+34:RETURN",
]
RUN_PERTURB = "X=RND(1):X=RND(1):X=RND(-7):POKE &HC000,0"
RUN_STEPS = [("R=-12345", "at the program's first line", "peek", None),
             ("R=RND(1)", "RND(1)", "val", ["pos"]),
             ("R=RND(0)", "RND(0)", "val", ["zero"]),
             ("CLEAR 2000,&HBF00:R=-12345", "after CLEAR", "peek", None),
             ("R=RND(1)", "RND(1) after CLEAR", "val", ["pos"])]


def program(group):
    """the typed lines and the case list [(id, meta)] in record order"""
    routine = [str(x) for x in kmath.ROUTINE]
    if group == "BOOT":
        lines, cases = [], []
        for stmt, why in BOOT:
            if why is None:
                lines.append(stmt)
                continue
            i = len(cases)
            lines.append(_drec(i, stmt))
            cases.append((f"KRN BOOT {i}", dict(op="FX", stmt=stmt, why=why, ty=None, text=None)))
        lines.append(f"POKE &HC001+{REC * len(cases)},&HC3:POKE &HC000,&H5A")
        _fits(group, cases)
        return lines, cases
    if group in ("RUNR", "GOTO", "GOTO2"):
        lines = RUNPROG + [RUN_PERTURB] + (["99 REM"] if group == "GOTO2" else []) + \
            ["RUN" if group == "RUNR" else "GOTO 5"]
        cases = [(f"KRN {group} {i}", dict(op="FX", stmt=s, why=w, ty=None, text=None))
                 for i, (s, w, _k, _st) in enumerate(RUN_STEPS)]
        _fits(group, cases)
        return lines, cases
    if group == "FX":
        lines = list(HEAD) + ["26 GOTO 2000"]
        cases = []
        for i, (stmt, why, kind, steps) in enumerate(FX):
            n = 2000 + 2 * i
            lines += [f"{n} GOSUB 880:{stmt}", f"{n + 1} GOSUB 900"]
            assert len(lines[-2]) <= 240
            cases.append((f"KRN FX {i}", dict(op="FX", stmt=stmt, why=why, ty=None, text=None, kind=kind,
                                              steps=steps)))
        lines += [f"{2000 + 2 * len(FX)} " + ramrec.TAIL] + RECORD + ramrec.data(1000, routine)
        _fits(group, cases)
        return lines + ["RUN"], cases
    steps = SEQS[group]
    vals = [str(len(steps))]
    for op, t, x in steps:
        vals += [str(op), str(t), x]
    lines = list(HEAD) + SEQ_BODY + RECORD + ramrec.data(1000, routine + vals)
    cases = [(f"KRN {group} {i}", dict(op=OPS[op], ty=TY[t][0], text=x, stmt=None, why=None))
             for i, (op, t, x) in enumerate(steps)]
    _fits(group, cases)
    return lines + ["RUN"], cases


def _fits(group, cases):
    assert 0xC000 + 1 + REC * len(cases) + 1 <= 0xF380, f"{group}: the records run past $F380"


def decode(hexs, n, group=None):
    """BOOT's direct lines write only E, R, VT (255) and RNDX: its ARG and DAC bytes are whatever RAM held and are
    not part of the record (ARG reads as zeros)"""
    rs, why = ramrec.frame(hexs, n, REC)
    if rs is None:
        return None, why
    out = []
    for r in rs:
        vt = r[17]
        dac = r[18:26]
        res = None
        if vt == 2:
            res = dac[2:4]
        elif vt in (4, 8):
            res = dac[:vt]
        arg = bytes(8) if group == "BOOT" else r[1:9]
        out.append(dict(e=r[0], arg=arg, rbytes=r[9:17], vt=vt, res=res, rndx=r[26:34]))
    return out, None


def check_apparatus(cases, who):
    """the ID rows: USR saw the argument's own type and bytes; else the readout is not trusted (exits)"""
    bad = []
    for c in cases:
        if c.op != "ID":
            continue
        nb = {"I": 2, "S": 4, "D": 8}[c.ty]
        if not (c.e == 0 and c.vt == nb and c.res == c.arg[:nb]):
            bad.append(c.id)
    if bad:
        sys.exit(f"FAIL: the USR readout is not the argument's own on {who}: {', '.join(bad[:8])}")


def load(group, run=RUN):
    """the cases of one group from the committed run file: {"ref": [...], "zb": [...]}"""
    sec = ramrec.read_section(os.path.join(ROOT, "scratchpad", run), group)
    _, cases = program(group)
    out = {}
    for who, h in sec.items():
        recs, why = decode(h, len(cases), group)
        if recs is None:
            sys.exit(f"FAIL: {run} {group} {who}: {why}")
        out[who] = [NS(src=group, id=cid, **meta, **r) for (cid, meta), r in zip(cases, recs)]
        check_apparatus(out[who], who)
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
            recs, why = decode(cap[who], len(cases), g)
            if recs is None:
                bad.append(f"{who}: {why}")
        text = open(path).read() if os.path.exists(path) else ""
        open(path, "w").write(ramrec.write_section(text, g, cap, len(cases), bad))
        print(f"{g}: {len(cases)} cases; {'; '.join(bad) or 'both complete'}", flush=True)
        if not bad:
            ref, zb = (decode(cap[w], len(cases), g)[0] for w in ("ref", "zb"))
            diff = [cases[i][0] for i in range(len(cases)) if ref[i] != zb[i]]
            print(f"  {len(diff)} cases differ" + (": " + ", ".join(diff[:12]) if diff else ""), flush=True)
    print(f"wrote {os.path.relpath(path, ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
