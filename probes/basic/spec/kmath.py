#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""KMATH -- the measured cases behind docs/keywords/ABS.md, SGN.md, INT.md, FIX.md and SQR.md: the maths region's
first keyword probe (D-KWSPEC; docs/keywords/spec-plan.md §2 region 2, docs/spec-method.md §3a). The frame, the
record framing and the run file are the shared RAM-record harness's (probes/basic/spec/ramrec.py).

Clean room: typed BASIC in, RAM out. The program is TYPED on each machine; it evaluates every case and POKEs a record
of the outcome into RAM, which the harness reads after the program's own done flag. No reference ROM byte is read.

THE SETUP SEPARATES (spec-method §3a):
  * a numeric argument is READ from DATA into a variable of the case's own type -- N% (integer), N! (single) or N#
    (double) -- and that variable's own bytes are recorded BEFORE the call (ramrec.number decodes them exactly), so
    the rules work from the value the function was given, not from the DATA text;
  * THE RESULT'S TYPE IS SEEN (spec-plan §7 item 3). Every case is evaluated twice: once as `R=F(N)` -- R a double,
    its own 8 bytes recorded -- and once as `Q=USR(F(N))`, where USR is the probe's own 18-byte routine at $BF00
    (POKEd from DATA, above CLEAR's limit). By the MSX convention (docs/keywords/USR.md: measured on the VG-8020) the
    routine receives the argument -- here F's RESULT, unconverted -- in DAC ($F7F6) with its type in VALTYP ($F663);
    it copies VALTYP to $BF80 and DAC's 8 bytes to $BF81 and returns. So the record holds the result's type (2 / 4 /
    8) and its own bytes (an integer at DAC+2). $BF80 holds 255 before every case: a USR that was never reached
    (the function raised an error first) leaves it there. The routine and its copy area are the probe's own memory;
    the work-area cells are read by the routine, never PEEKed;
  * an APPARATUS row per argument, `ID`: `R=N` and `Q=USR(N)` with no function, whose captured type and bytes must be
    the argument's own (the loader refuses a run where they are not -- the USR readout is checked on every
    argument before any rule reads it);
  * every case starts with R = -12345 and E = 0, so an error, which assigns nothing, cannot read as a result;
  * the numbers sit where rival rules disagree: INT (floor) vs FIX (toward zero) vs rounding at +-.5, +-.9, +-2.5,
    +-1.9; an integer's -32768, which has no positive integer; the ends of each type's range; already-whole numbers
    with all 6 / 14 digits used; values of 1E-64 that INT must take to -1 and FIX to 0; perfect squares and not for
    SQR, and negative arguments (error 5).

THE RECORD (27 bytes per case, from $C001):
  0 E1          ERR after `R=F(N)` (0: none)
  1-8 ARG       the numeric argument's own bytes, read before the call (2 / 4 / 8 of them, the rest 0); FX: all 0
  9-16 R        R's 8 bytes after `R=F(N)` (a double)
  17 E2         ERR after `Q=USR(F(N))`
  18 VT         the result's type as USR saw it (2 / 4 / 8; 255: USR not reached)
  19-26 DAC     DAC's 8 bytes as USR saw them (the result: an integer at 21-22, a single at 19-22, a double 19-26)

THE GROUPS (case ids "KMA <group> ..."): one per argument type, so no group's records reach $F380 (asserted):
  MI    the functions over the integers MI_ARGS (N%)       -> "KMA MI <fn> <text>"
  MS    over the singles MS_ARGS (N!)                      -> "KMA MS <fn> <text>"
  MD    over the doubles MD_ARGS (N#)                      -> "KMA MD <fn> <text>"
  FX    fixed statements (types, missing / extra arguments, spaces, literals, nesting, non-canonical bytes;
        S$ = "12")                                         -> "KMA FX <i>"

    python3 probes/basic/spec/kmath.py [GROUP ...] [--out scratchpad/KMA_run1.out]
(run through tools/agent_wt.py: it boots the VG-8020 and zerobas's NODISK machine)."""
import os
import sys
from types import SimpleNamespace as NS

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, HERE)
import ramrec  # noqa: E402

REC = 27
RUN = "KMA_run1.out"
R_SENT = -12345
TYPES = {"I": ("%", 2), "S": ("!", 4), "D": ("#", 8)}
FNS = ["ID", "ABS", "SGN", "INT", "FIX", "SQR"]
USR_AT, CAP = 0xBF00, 0xBF80
# LD A,(VALTYP) / LD (CAP),A / LD HL,DAC / LD DE,CAP+1 / LD BC,8 / LDIR / RET
ROUTINE = [0x3A, 0x63, 0xF6, 0x32, CAP & 255, CAP >> 8, 0x21, 0xF6, 0xF7, 0x11, (CAP + 1) & 255, (CAP + 1) >> 8,
           0x01, 0x08, 0x00, 0xED, 0xB0, 0xC9]

MI_ARGS = ["0", "1", "-1", "2", "-2", "3", "4", "5", "-5", "9", "10", "16", "100", "255", "12345", "-12345", "32767",
           "-32767", "-32768"]
MS_ARGS = ["0", "-0", "1", "-1", ".5", "-.5", ".4", "-.4", ".6", "-.6", ".9", "-.9", ".1", "-.1", "1.5", "-1.5",
           "1.9", "-1.9", "2.5", "-2.5", "2", "3", "4", "5", "9", "10", "16", ".25", "2.25", "1.44", "99.9998",
           ".999999", "-.999999", "99999.5", "-99999.5", "99999.9", "-99999.9", "12345.6", "-12345.6", "32767",
           "32767.5", "-32767.5", "32768", "-32768", "-32768.5", "-32769", "65535.5", "123456", "-123456", "999999",
           "-999999", "1E6", "-1E6", "1E10", "-1E10", "1E-10", "-1E-10", "1E-6", "-1E-6", "1.23456E-5",
           "1E-63", "-1E-63", "1E-64", "-1E-64", "9.99999E62", "-9.99999E62"]
MD_ARGS = ["0", "-0", "1", "-1", ".5", "-.5", ".9", "-.9", "1.5", "-1.5", "2.5", "-2.5", "2", "3", "5", "10", ".25",
           "2.25", "99.99998", "32767.9", "-32768.1", "32768", "-32768", "-32769", "65536.5", "1234567.5",
           "-1234567.5", "12345678.9", "-12345678.9", "-9999999.5", ".99999999999999", "-.99999999999999",
           "1.9999999999999", "-1.9999999999999", "9999999999999.5", "-9999999999999.5", "1234567890123.4",
           "-1234567890123.4", "12345678901234", "-12345678901234", "1D14", "-1D14", "1D20", "-1D20", "1D-10",
           "-1D-10", "1D-14", "-1D-14", "1D-64", "-1D-64", "9.9999999999999D62", "-9.9999999999999D62"]
ARGS = {"MI": ("I", MI_ARGS), "MS": ("S", MS_ARGS), "MD": ("D", MD_ARGS)}
GAPS = {"MI": 2500.0, "MS": 6000.0, "MD": 6000.0, "FX": 2500.0}

# FX: (fn, statement, what it separates, the USR form or None). S$ = "12". The USR form evaluates the same
# expression inside USR( ) so the result's type is seen; it is None where the statement is not an expression.
PRE0 = "N!=1:V=VARPTR(N!):POKE V,0:"
PRE80 = "N!=1:V=VARPTR(N!):POKE V,128:"
FX = []
for _f in FNS[1:]:
    def _v(expr, why, pre=""):
        FX.append((_f, f"{pre}R={expr}", why, f"Q=USR({expr})"))
    def _n(stmt, why):
        FX.append((_f, stmt, why, None))
    _n(f'R={_f}("A")', "a string as the argument")
    _n(f"R={_f}(S$)", "a string variable as the argument")
    _n(f"R$={_f}(5)", "the result assigned to a string")
    _n(f"R={_f}(1/0)", "the argument's own error")
    _n(f"R={_f}()", "no argument")
    _n(f"R={_f}(5,1)", "an extra argument")
    _n(f"R={_f}(5", "no closing parenthesis")
    _n(f"R={_f}", "no parenthesis")
    _v(f"{_f}(2.5)", "a literal with a point")
    _v(f"{_f}(-2.5)", "a negative literal with a point")
    _v(f"{_f} (2.5)", "a space before the parenthesis")
    _v(f"{_f}( 2.5 )", "spaces around the argument")
    _v(f"{_f}(7%)", "an integer literal")
    _v(f"{_f}(2.5!)", "a single literal")
    _v(f"{_f}(2.5#)", "a double literal")
    _v(f"{_f}(7)", "a literal without a point")
    _v(f"{_f}(&H8000)", "a hex literal (the integer -32768)")
    _v(f"{_f}(-32768)", "minus the literal 32768")
    _v(f"{_f}(-0)", "minus zero")
    _v(f"{_f}(1/4)", "an expression")
    _v(f"{_f}({_f}(2.25))", "nested")
    _v(f"{_f}(N!)", "a single with exponent byte 0, digit bytes 10 00 00", PRE0)
    _v(f"{_f}(N!)", "a single with exponent byte 80, digit bytes 10 00 00", PRE80)
# LET, not this unit's subject: a single zero with digit bytes assigned to a double (the evidence of R's bytes in
# the ASSIGN rules; no page loads fn "LET")
FX += [("LET", f"{PRE0}R=N!", "a single with exponent byte 0, digit bytes 10 00 00, assigned", "Q=USR(N!)"),
       ("LET", "N!=.5:N!=FIX(N!):R=N!", "FIX(.5!) stored in a single, then assigned", "Q=USR(N!)"),
       ("LET", "R=0:R=SQR(0%)", "SQR(0%) after R=0", "Q=USR(SQR(0%))"),
       ("LET", "R=-12345:R=SQR(0!)", "SQR(0!) after R=-12345", "Q=USR(SQR(0!))")]
FX_S = "12"

RECORD = [
    "900 POKE A,E1:V=VARPTR(R):FOR K=0 TO 7:POKE A+9+K,PEEK(V+K):POKE A+19+K,PEEK(&HBF81+K):NEXT",
    "910 POKE A+17,E2:POKE A+18,PEEK(&HBF80):A=A+27:RETURN",
    ramrec.ERRLINE,
]


def head():
    return "10 CLEAR 2000,&HBF00:DEFDBL A-Z:DEFINT I-K:ON ERROR GOTO 800:POKE &HC000,0:A=&HC001"


def program(group):
    """the typed lines (numbered program + RUN) and the case list [(id, meta)] in record order"""
    routine = [str(x) for x in ROUTINE]
    if group == "FX":
        lines = [head(), "20 FOR K=0 TO 17:READ X:POKE &HBF00+K,X:NEXT:DEFUSR=&HBF00", f'25 S$="{FX_S}":GOTO 2000']
        cases = []
        for i, (fn, stmt, why, ustmt) in enumerate(FX):
            n = 2000 + 3 * i
            lines.append(f"{n} E=0:R={R_SENT}:POKE &HBF80,255:FOR K=1 TO 8:POKE A+K,0:NEXT:{stmt}")
            lines.append(f"{n + 1} E1=E:E=0:" + (ustmt if ustmt else "REM"))
            lines.append(f"{n + 2} E2=E:GOSUB 900")
            cases.append((f"KMA FX {i}", dict(fn=fn, stmt=stmt, why=why, ustmt=ustmt, ty=None, text=None)))
        lines += [f"{2000 + 3 * len(FX)} " + ramrec.TAIL] + RECORD + ramrec.data(1000, routine)
        _fits(group, cases)
        return lines + ["RUN"], cases
    ty, xs = ARGS[group]
    nb = TYPES[ty][1]
    var = "N" + TYPES[ty][0]
    nf = len(FNS)
    lines = [head(),
             "20 FOR K=0 TO 17:READ X:POKE &HBF00+K,X:NEXT:DEFUSR=&HBF00",
             f"30 READ I2:FOR J2=1 TO I2:READ {var}:V=VARPTR({var})",
             f"40 FOR J4=1 TO {nf}:FOR K=0 TO 7:X=0:IF K<{nb} THEN X=PEEK(V+K)",
             f"50 POKE A+1+K,X:NEXT K:E=0:R={R_SENT}:POKE &HBF80,255:GOSUB 200:E1=E:E=0:GOSUB 500:E2=E",
             f"60 GOSUB 900:V=VARPTR({var}):NEXT J4,J2",
             "70 " + ramrec.TAIL,
             "200 ON J4 GOTO " + ",".join(str(210 + k) for k in range(nf)),
             "500 ON J4 GOTO " + ",".join(str(510 + k) for k in range(nf))]
    for k, f in enumerate(FNS):
        expr = var if f == "ID" else f"{f}({var})"
        lines += [f"{210 + k} R={expr}:RETURN", f"{510 + k} Q=USR({expr}):RETURN"]
    lines += RECORD
    lines += ramrec.data(1000, routine + [str(len(xs))] + xs)
    cases = [(f"KMA {group} {f} {x}", dict(fn=f, ty=ty, text=x, stmt=None, why=None, ustmt=None))
             for x in xs for f in FNS]
    _fits(group, cases)
    return lines + ["RUN"], cases


def _fits(group, cases):
    assert 1 + REC * len(cases) + 1 <= 0xF380 - ramrec.BASE, f"{group}: the records run past $F380"


VT_N = {2: 2, 4: 4, 8: 8}


def decode(hexs, n):
    rs, why = ramrec.frame(hexs, n, REC)
    if rs is None:
        return None, why
    out = []
    for r in rs:
        vt = r[18]
        dac = r[19:27]
        res = None
        if vt == 2:
            res = dac[2:4]
        elif vt in (4, 8):
            res = dac[:vt]
        out.append(dict(e1=r[0], arg=r[1:9], rbytes=r[9:17], e2=r[17], vt=vt, res=res))
    return out, None


def argval(c):
    """the numeric argument's exact value, from its own recorded bytes"""
    return ramrec.number(c.arg[:TYPES[c.ty][1]])


ORDER = ["MI", "MS", "MD", "FX"]


def check_apparatus(cases, who):
    """the ID rows: USR saw the argument's own type and bytes, and R = N assigned its value; else the readout is
    not trusted (exits)"""
    bad = []
    for c in cases:
        if c.fn != "ID":
            continue
        nb = TYPES[c.ty][1]
        ok = c.e1 == 0 and c.e2 == 0 and c.vt == nb and c.res == c.arg[:nb]
        try:
            ok = ok and ramrec.number(c.rbytes) == argval(c)
        except ValueError:
            ok = False
        if not ok:
            bad.append(c.id)
    if bad:
        sys.exit(f"FAIL: the USR readout is not the argument's own on {who}: {', '.join(bad[:8])}")


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
