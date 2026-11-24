#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""KOPS -- the measured cases behind docs/keywords/AND.md, OR.md, XOR.md, EQV.md, IMP.md, NOT.md and MOD.md: the
operators region's first keyword probe (D-KWSPEC; docs/keywords/spec-plan.md §2 region 4; docs/spec-method.md §3a).
The USR type readout is kmath.py's (its `ROUTINE`); the run file is the shared RAM-record harness's
(probes/basic/spec/ramrec.py).

Clean room: typed BASIC in, RAM out. The program is TYPED on each machine; it evaluates every case and POKEs a record
of the outcome into RAM, which the harness reads after the program's own done flag. No reference ROM byte is read;
every variable read through VARPTR is assigned first; the record area ends below $F380 (asserted per group).

THE SETUP SEPARATES (spec-method §3a):
  * both operands are READ into variables of the group's type -- X% / Y%, X! / Y!, X# / Y# -- and their own bytes are
    recorded before the operation, so the rules work from the values given;
  * every case is evaluated twice: `R=X op Y` (R a double, its 8 bytes) and `Q=USR(X op Y)`, the probe's own routine
    copying VALTYP and DAC -- the result's TYPE and its own bytes; `NOT X` the same, Y unused;
  * before every case R = -12345 and the USR type cell 255: an error, which assigns nothing, cannot read as a result;
  * the operands sit where rival rules disagree: truncation vs rounding vs floor of a fraction (+-2.5, +-2.7, +-.5),
    the integer range's ends and just past them (32767.9, -32768.9, 32768, -32769, 65535 -- an unsigned reading
    would accept it), signs for MOD (5 / -5 by 3 / -3), MOD by 0 and by a fraction below 1 (truncated to 0).

THE RECORD (35 bytes per case, from $C001):
  0 E1          ERR after `R=X op Y`
  1-8 ARG1      X's own bytes (2 / 4 / 8, the rest 0); FX: 0
  9-16 ARG2     Y's own bytes
  17-24 R       R's 8 bytes after `R=X op Y`
  25 E2         ERR after `Q=USR(X op Y)`
  26 VT         the type USR saw (2 / 4 / 8; 255: USR not reached)
  27-34 DAC     DAC's 8 bytes as USR saw them

THE GROUPS (case ids "KOP <group> <op> <x> <y>" / "KOP FX <i>"):
  OI    integer operands (X%, Y%)       OS    singles (X!, Y!)       OD    doubles (X#, Y#)
  FX    fixed statements: precedence (every ordered pair of the logical operators, NOT against a comparison),
        mixed types, strings, missing operands, literals

    python3 probes/basic/spec/kops.py [GROUP ...] [--out scratchpad/KOP_run1.out]"""
import os
import sys
from types import SimpleNamespace as NS

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, HERE)
import kmath  # noqa: E402
import ramrec  # noqa: E402

REC = 35
RUN = "KOP_run1.out"
R_SENT = kmath.R_SENT
TYPES = kmath.TYPES
OPS = ["ID", "AND", "OR", "XOR", "EQV", "IMP", "MOD", "NOT"]

OI_PAIRS = [("0", "0"), ("1", "0"), ("0", "1"), ("-1", "0"), ("12", "10"), ("5", "3"), ("-1", "-1"), ("-1", "255"),
            ("255", "-256"), ("32767", "1"), ("-32768", "-1"), ("-32768", "32767"), ("-5", "3"), ("5", "-3"),
            ("-5", "-3"), ("7", "0"), ("0", "7"), ("32767", "32767"), ("-32768", "2"), ("1234", "-4321")]
OS_PAIRS = [("2.5", "1"), ("-2.5", "1"), ("2.7", "3"), ("-2.7", "3"), (".5", ".5"), ("-.5", "-.5"), ("3.5", "7"),
            ("32767.9", "1"), ("-32768.9", "1"), ("32768", "1"), ("1", "32768"), ("-32769", "1"), ("65535", "1"),
            ("1E10", "1"), ("1E-64", "1"), ("5.9", "2.9"), ("-5.9", "2.9"), ("7", ".9"), ("7", "-.5"),
            ("12345.6", "255")]
OD_PAIRS = [("2.5", "1"), ("-2.5", "1"), ("2.7", "3"), ("-2.7", "3"), ("32767.99999999", "1"),
            ("-32768.99999999", "1"), ("32768", "1"), ("-32769", "1"), ("65535", "1"), ("5.9", "2.9"),
            ("-5.9", "2.9"), ("7", ".99999999999999"), ("1D20", "1"), (".49999999999999", "-.5")]
ARGS = {"OI": ("I", OI_PAIRS), "OS": ("S", OS_PAIRS), "OD": ("D", OD_PAIRS)}
GAPS = {"OI": 6000.0, "OS": 6000.0, "OD": 6000.0, "FX": 2500.0, "FY": 2500.0}
ORDER = ["OI", "OS", "OD", "FX", "FY"]

# FX: (op, expression or statement, what it separates, is it an expression (R= / USR forms))
LOGIC = ["NOT", "AND", "OR", "XOR", "EQV", "IMP"]
FX = []
# precedence: for each ordered pair of two-operand operators, a three-operand chain whose two groupings differ
for _i, _a in enumerate(LOGIC[1:]):
    for _b in LOGIC[1:]:
        if _a != _b:
            FX.append((f"{_a}/{_b}", f"5 {_a} 3 {_b} 6", f"5 {_a} 3 {_b} 6: precedence", True))
            FX.append((f"{_a}/{_b}", f"0 {_a} 1 {_b} 0", f"0 {_a} 1 {_b} 0: precedence", True))
for _b in LOGIC[1:]:
    FX.append((f"NOT/{_b}", f"NOT 5 {_b} 3", f"NOT 5 {_b} 3: NOT against {_b}", True))
    FX.append((f"{_b}/self", f"5 {_b} 3 {_b} 6", f"5 {_b} 3 {_b} 6: grouping", True))
FX += [("NOT/cmp", "NOT 1=2", "NOT against a comparison", True),
       ("NOT/cmp", "NOT 1<2", "NOT against a comparison", True),
       ("NOT/arith", "NOT 1+2", "NOT against +", True),
       ("NOT/arith", "-NOT 0", "minus NOT", True),
       ("AND/cmp", "1<2 AND 3<4", "comparisons bind tighter", True),
       ("AND/arith", "1+2 AND 3", "+ binds tighter", True),
       ("MOD/arith", "7 MOD 4*2", "* against MOD", True),
       ("MOD/arith", "7 MOD 4+2", "+ against MOD", True),
       ("MOD/arith", "-7 MOD 4", "unary minus against MOD", True),
       ("MOD/div", "7\\2 MOD 2", "\\ against MOD", True),
       ("AND", '1 AND "A"', "a string on the right", False),
       ("AND", '"A" AND 1', "a string on the left", False),
       ("AND", "1 AND", "nothing after the operator", False),
       ("NOT", "NOT", "NOT alone", False),
       ("NOT", 'NOT "A"', "NOT of a string", False),
       ("MOD", "7 MOD 0", "MOD by 0", True),
       ("MOD", "7 MOD .5", "MOD by .5 (truncated to 0)", True),
       ("MOD", "7.9 MOD 2", "a literal fraction", True),
       ("AND", "&HFFFF AND &H8000", "hex literals (integers)", True),
       ("OR", "65535 OR 0", "65535, a single", True),
       ("XOR", "2.5! XOR 7%", "mixed types", True),
       ("EQV", "1# EQV 1%", "mixed types", True)]
for _o in ("OR", "XOR", "EQV", "IMP", "MOD"):           # each operator's own error rows (appended: FX ids above keep)
    FX += [(_o, f'1 {_o} "A"', "a string on the right", False),
           (_o, f'"A" {_o} 1', "a string on the left", False),
           (_o, f"1 {_o}", "nothing after the operator", False)]

# FY (goldfish pass 1, 2026-11-24, scratchpad/REVIEW-m2-gOPS1.md): rows that SEPARATE what FX could not -- the
# arithmetic / comparison levels against each logical operator, OR against IMP once more, MOD's own grouping and its
# place against / and ^, overflow against Division by zero, which error wins with two bad operands, out-of-range
# RIGHT operands, NOT after a minus with a comparison and after a binary operator, a deep NOT chain, and operator
# structure errors. (op, expression, what it separates, is it an expression)
FY = [("AND/cmp", "1<2 AND 1", "a comparison against AND", True),
      ("AND/arith", "1+2 AND 0", "+ against AND", True),
      ("OR/cmp", "1=2 OR 3", "a comparison against OR", True),
      ("XOR/arith", "1+2 XOR 3", "+ against XOR", True),
      ("EQV/arith", "1 EQV 2+3", "+ against EQV", True),
      ("IMP/cmp", "1=1 IMP 1=0", "comparisons against IMP", True),
      ("OR/IMP", "6 OR 1 IMP 0", "OR against IMP, again", True),
      ("MOD/self", "100 MOD 7 MOD 3", "MOD's own grouping", True),
      ("MOD/div", "7 MOD 4/2", "/ against MOD", True),
      ("MOD/pow", "2^3 MOD 3", "^ against MOD", True),
      ("MOD/neg", "-32768 MOD 5", "unary minus against MOD at the range's edge", True),
      ("MOD", "32768 MOD 0", "Overflow against Division by zero", True),
      ("MOD", "1E10 MOD .5", "Overflow against Division by zero (a fraction)", True),
      ("MOD", "-32769# MOD .9#", "Overflow against Division by zero (doubles)", True),
      ("AND", '70000 AND "A"', "two bad operands: a range and a string", False),
      ("AND", '"A" AND 70000', "two bad operands, the string first", False),
      ("MOD", '"A" MOD 0', "a string against Division by zero", False),
      ("NOT/cmp", "-NOT 0=1", "a minus, NOT and a comparison", True),
      ("NOT/arith", "2*NOT 0", "NOT after *", True),
      ("NOT/cmp", "2+NOT 0=0", "NOT after +, then a comparison", True),
      ("NOT", "NOT NOT NOT NOT NOT NOT NOT NOT NOT NOT NOT NOT NOT NOT NOT NOT NOT NOT NOT NOT 7",
       "twenty NOTs", True),
      ("AND", "5 AND * 3", "an operator where an operand belongs", False),
      ("AND", "1 AND )", "a closing parenthesis as the operand", False)]
for _o in ("AND", "OR", "XOR", "EQV", "IMP", "MOD"):
    FY += [(_o, f"1 {_o} -32769", "a right operand below the range", True),
           (_o, f"1# {_o} 32768#", "a double right operand above the range", True),
           (_o, f"1 {_o} 1D20", "a huge right operand", True)]

RECORD = [
    "900 POKE A,E1:V=VARPTR(R):FOR K=0 TO 7:POKE A+17+K,PEEK(V+K):POKE A+27+K,PEEK(&HBF81+K):NEXT",
    "910 POKE A+25,E2:POKE A+26,PEEK(&HBF80):A=A+35:RETURN",
    ramrec.ERRLINE,
]


def program(group):
    """the typed lines (numbered program + RUN) and the case list [(id, meta)] in record order"""
    routine = [str(v) for v in kmath.ROUTINE]
    head = [kmath.head(), "20 FOR K=0 TO 17:READ X:POKE &HBF00+K,X:NEXT:DEFUSR=&HBF00"]
    if group in ("FX", "FY"):
        lines = head + ["25 GOTO 2000",
                        f"880 E=0:R={R_SENT}:POKE &HBF80,255:FOR K=1 TO 16:POKE A+K,0:NEXT:RETURN"]
        cases = []
        for i, (op, expr, why, is_expr) in enumerate(FX if group == "FX" else FY):
            n = 2000 + 2 * i
            lines.append(f"{n} GOSUB 880:R={expr}")
            lines.append(f"{n + 1} E1=E:E=0:" + (f"Q=USR({expr}):E2=E" if is_expr else "E2=0") + ":GOSUB 900")
            cases.append((f"KOP {group} {i}", dict(op=op, expr=expr, why=why, is_expr=is_expr, ty=None, x=None, y=None)))
        lines += [f"{2000 + 2 * len(FX)} " + ramrec.TAIL] + RECORD + ramrec.data(1000, routine)
        _fits(group, cases)
        return lines + ["RUN"], cases
    ty, pairs = ARGS[group]
    sfx, nb = TYPES[ty]
    x, y = "X" + sfx, "Y" + sfx
    nf = len(OPS)
    lines = head + [
        f"30 READ I2:FOR J2=1 TO I2:READ {x},{y}",
        f"40 FOR J4=1 TO {nf}:V=VARPTR({x}):W=VARPTR({y}):FOR K=0 TO 7:X1=0:X2=0:IF K<{nb} THEN X1=PEEK(V+K):X2=PEEK(W+K)",
        f"50 POKE A+1+K,X1:POKE A+9+K,X2:NEXT K:E=0:R={R_SENT}:POKE &HBF80,255:GOSUB 200:E1=E:E=0:GOSUB 500:E2=E",
        f"60 GOSUB 900:NEXT J4,J2",
        "70 " + ramrec.TAIL,
        "200 ON J4 GOTO " + ",".join(str(210 + k) for k in range(nf)),
        "500 ON J4 GOTO " + ",".join(str(510 + k) for k in range(nf))]
    for k, op in enumerate(OPS):
        expr = x if op == "ID" else (f"NOT {x}" if op == "NOT" else f"{x} {op} {y}")
        lines += [f"{210 + k} R={expr}:RETURN", f"{510 + k} Q=USR({expr}):RETURN"]
    lines += RECORD
    vals = [str(len(pairs))]
    for a, b in pairs:
        vals += [a, b]
    lines += ramrec.data(1000, routine + vals)
    cases = [(f"KOP {group} {op} {a} {b}", dict(op=op, ty=ty, x=a, y=b, expr=None, why=None, is_expr=True))
             for a, b in pairs for op in OPS]
    _fits(group, cases)
    return lines + ["RUN"], cases


def _fits(group, cases):
    assert 1 + REC * len(cases) + 1 <= 0xF380 - ramrec.BASE, f"{group}: the records run past $F380"


def decode(hexs, n):
    rs, why = ramrec.frame(hexs, n, REC)
    if rs is None:
        return None, why
    out = []
    for r in rs:
        vt = r[26]
        dac = r[27:35]
        res = None
        if vt == 2:
            res = dac[2:4]
        elif vt in (4, 8):
            res = dac[:vt]
        out.append(dict(e1=r[0], arg1=r[1:9], arg2=r[9:17], rbytes=r[17:25], e2=r[25], vt=vt, res=res))
    return out, None


def load(group, run=RUN):
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
