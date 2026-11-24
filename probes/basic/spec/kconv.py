#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""KCONV -- the measured cases behind docs/keywords/CINT.md, CSNG.md and CDBL.md: the conversion region's first
keyword probe (D-KWSPEC; docs/keywords/spec-plan.md §2 region 3; docs/spec-method.md §3a). The frame, the record,
the USR type readout and the apparatus row are probes/basic/spec/kmath.py's, unchanged (its `ROUTINE`, `RECORD`,
`head`, `decode`, `check_apparatus`), and the program builder is ktrans.py's; the run file is the shared RAM-record
harness's (probes/basic/spec/ramrec.py).

Clean room: typed BASIC in, RAM out. The program is TYPED on each machine; it evaluates every case and POKEs a record
of the outcome into RAM, which the harness reads after the program's own done flag. No reference ROM byte is read;
the USR routine is the probe's own code and reads only the published cells VALTYP and DAC; every variable read
through VARPTR is assigned first; the record area ends below $F380 (asserted per group).

THE SETUP SEPARATES (spec-method §3a), as kmath.py's (read its docstring): the argument READ into N% / N! / N# and
its own bytes recorded before the call; `R=F(N)` (R a double, its 8 bytes) and `Q=USR(F(N))` (the result's TYPE and
its own bytes, unconverted); an `ID` apparatus row per argument; R = -12345 and the type cell 255 before every case.
The MATRIX sits where rival conversion rules disagree:
  * CINT: truncation vs rounding (half up, half away from zero, half to even) vs floor -- at +-.5, +-1.5, +-2.5,
    +-.4, +-.6, +-.9, +-.49999999999999 -- and the integer range's ends: 32767, 32767.4 / .5 / .9, 32768, -32768,
    -32768.4 / .5 / .9, -32769, in every type;
  * CSNG: a double's 7th digit and beyond (...4999999, ...5, ...5000001, ...9999995 with a carry into the next
    decade and into the exponent, at the top of the range 9.9999995D62), negative mirrors, tiny numbers (1D-64);
  * CDBL: a single's 6 digits widened (the 8 new digits zero, or the single's decimal value?), integers.

THE GROUPS (case ids "KCV <group> <fn> <text>" / "KCV FX <i>"): every function over each group's arguments:
  CI    the integers (N%)        CS    singles (N!)        CD    doubles (N#)
  FX    fixed statements (types, missing / extra arguments, spaces, literals, nesting, non-canonical bytes;
        S$ = "12")

    python3 probes/basic/spec/kconv.py [GROUP ...] [--out scratchpad/KCV_run1.out]
(run through tools/agent_wt.py: it boots the VG-8020 and zerobas's NODISK machine)."""
import os
import sys
from types import SimpleNamespace as NS

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, HERE)
import kmath  # noqa: E402
import ramrec  # noqa: E402

REC = kmath.REC
RUN = "KCV_run1.out"
R_SENT = kmath.R_SENT
TYPES = kmath.TYPES
FNS = ["ID", "CINT", "CSNG", "CDBL"]

CI_ARGS = ["0", "1", "-1", "2", "-2", "7", "-7", "255", "12345", "-12345", "32767", "-32767", "-32768"]
CS_ARGS = ["0", "-0", "1", "-1", ".5", "-.5", "1.5", "-1.5", "2.5", "-2.5", "3.5", "-3.5", ".4", "-.4", ".6", "-.6",
           ".9", "-.9", ".499999", "-.499999", "1.49999", "2.50001", "-2.50001", "99.5", "-99.5", "12345.6",
           "-12345.6", "32766.5", "32767", "32767.4", "32767.5", "32767.9", "32768", "-32768", "-32768.4",
           "-32768.5", "-32768.9", "-32769", "65535", "123456", "1E10", "-1E10", "1E-10", "1E-64", "-1E-64",
           "9.99999E62", "-9.99999E62", "1.23456", "3.33333"]
CD_ARGS = ["0", "-0", "1", "-1", ".5", "-.5", "1.5", "-1.5", "2.5", "-2.5", ".49999999999999", "-.49999999999999",
           ".50000000000001", "32766.5", "32767.49999999", "32767.5", "32767.99999999", "-32768.49999999",
           "-32768.5", "-32768.99999999", "1.2345649999999", "1.234565", "1.2345650000001", "-1.234565",
           "-1.2345650000001", "1.2345655", "1.2345665", "9.9999949999999", "9.999995", "-9.999995", "99999.95",
           "999999.5", "9999995", "1.23456789012345", ".33333333333333", ".66666666666667", "123456789.12345",
           "1D-64", "-1D-64", "9.99999D62", "9.9999949999999D62", "9.999995D62", "-9.999995D62",
           "9.9999999999999D62"]
ARGS = {"CI": ("I", CI_ARGS), "CS": ("S", CS_ARGS), "CD": ("D", CD_ARGS)}
GAPS = {"CI": 3000.0, "CS": 6000.0, "CD": 6000.0, "FX": 2500.0}
ORDER = ["CI", "CS", "CD", "FX"]

# FX: (fn, statement, what it separates, the USR form or None) -- kmath's list for these functions. S$ = "12".
PRE0, PRE80 = kmath.PRE0, kmath.PRE80
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
    _n(f'R={_f}("A"', "a string, no closing parenthesis")
    _n(f'R={_f}("A",2)', "a string and an extra argument")
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
    _v(f"{_f}(1/3)", "an expression (a double)")
    _v(f"{_f}({_f}(2.5))", "nested")
    _v(f"{_f}(N!)", "a single with exponent byte 0, digit bytes 10 00 00", PRE0)
    _v(f"{_f}(N!)", "a single with exponent byte 80, digit bytes 10 00 00", PRE80)
FX += [("CINT", "R=CINT(32767.5)", "32767.5 as a literal", "Q=USR(CINT(32767.5))"),
       ("CINT", "R=CINT(-32768.5)", "-32768.5 as a literal", "Q=USR(CINT(-32768.5))"),
       ("CSNG", "R=CSNG(1/3)*3", "the single 1/3 times 3", "Q=USR(CSNG(1/3)*3)"),
       ("CDBL", "R=CDBL(1!/3)", "a single expression widened", "Q=USR(CDBL(1!/3))"),
       ("CDBL", "Z!=.1:R=CDBL(Z!)", ".1 stored in a single, widened", "Q=USR(CDBL(Z!))")]
FX_S = "12"


def program(group):
    """the typed lines (numbered program + RUN) and the case list [(id, meta)] in record order"""
    routine = [str(x) for x in kmath.ROUTINE]
    if group == "FX":
        # kmath's FX frame in two lines a case and a shared prefix (880), so 138 cases fit below CLEAR's limit:
        # the statement stays LAST on its line (RESUME NEXT after a syntax error goes to the next line)
        lines = [kmath.head(), "20 FOR K=0 TO 17:READ X:POKE &HBF00+K,X:NEXT:DEFUSR=&HBF00",
                 f'25 S$="{FX_S}":GOTO 2000',
                 f"880 E=0:R={R_SENT}:POKE &HBF80,255:FOR K=1 TO 8:POKE A+K,0:NEXT:RETURN"]
        cases = []
        for i, (fn, stmt, why, ustmt) in enumerate(FX):
            n = 2000 + 2 * i
            lines.append(f"{n} GOSUB 880:{stmt}")
            lines.append(f"{n + 1} E1=E:E=0:" + (f"{ustmt}:E2=E" if ustmt else "E2=0") + ":GOSUB 900")
            cases.append((f"KCV FX {i}", dict(fn=fn, stmt=stmt, why=why, ustmt=ustmt, ty=None, text=None)))
        lines += [f"{2000 + 2 * len(FX)} " + ramrec.TAIL] + kmath.RECORD + ramrec.data(1000, routine)
        _fits(group, cases)
        return lines + ["RUN"], cases
    ty, xs = ARGS[group]
    nb = TYPES[ty][1]
    var = "N" + TYPES[ty][0]
    nf = len(FNS)
    lines = [kmath.head(),
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
    lines += kmath.RECORD
    lines += ramrec.data(1000, routine + [str(len(xs))] + xs)
    cases = [(f"KCV {group} {f} {x}", dict(fn=f, ty=ty, text=x, stmt=None, why=None, ustmt=None))
             for x in xs for f in FNS]
    _fits(group, cases)
    return lines + ["RUN"], cases


def _fits(group, cases):
    assert 1 + REC * len(cases) + 1 <= 0xF380 - ramrec.BASE, f"{group}: the records run past $F380"


def load(group, run=RUN):
    """the cases of one group from the committed run file: {"ref": [...], "zb": [...]}"""
    sec = ramrec.read_section(os.path.join(ROOT, "scratchpad", run), group)
    _, cases = program(group)
    out = {}
    for who, h in sec.items():
        recs, why = kmath.decode(h, len(cases))
        if recs is None:
            sys.exit(f"FAIL: {run} {group} {who}: {why}")
        out[who] = [NS(src=group, id=cid, **meta, **r) for (cid, meta), r in zip(cases, recs)]
        kmath.check_apparatus(out[who], who)
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
            recs, why = kmath.decode(cap[who], len(cases))
            if recs is None:
                bad.append(f"{who}: {why}")
        text = open(path).read() if os.path.exists(path) else ""
        open(path, "w").write(ramrec.write_section(text, g, cap, len(cases), bad))
        print(f"{g}: {len(cases)} cases; {'; '.join(bad) or 'both complete'}", flush=True)
        if not bad:
            ref, zb = (kmath.decode(cap[w], len(cases))[0] for w in ("ref", "zb"))
            diff = [cases[i][0] for i in range(len(cases)) if ref[i] != zb[i]]
            print(f"  {len(diff)} cases differ" + (": " + ", ".join(diff[:12]) if diff else ""), flush=True)
    print(f"wrote {os.path.relpath(path, ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
