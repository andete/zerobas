#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""KTRANS -- the measured cases behind docs/keywords/EXP.md, LOG.md, SIN.md, COS.md, TAN.md and ATN.md: the maths
region's second keyword probe, the transcendentals (D-KWSPEC; docs/keywords/spec-plan.md §2 region 2, §6 "The maths
region's second unit"; docs/spec-method.md §3a). The frame, the record, the USR type readout and the apparatus row are
probes/basic/spec/kmath.py's, unchanged (its `ROUTINE`, `RECORD`, `head`, `decode`, `check_apparatus`); the run file
is the shared RAM-record harness's (probes/basic/spec/ramrec.py).

Clean room: typed BASIC in, RAM out. The program is TYPED on each machine; it evaluates every case and POKEs a record
of the outcome into RAM, which the harness reads after the program's own done flag. No reference ROM byte is read;
the USR routine is the probe's own code and reads only the published cells VALTYP and DAC; every variable read
through VARPTR is assigned first; the record area ends below $F380 (asserted per group).

THE SETUP SEPARATES (spec-method §3a), as kmath.py's (read its docstring): the argument READ into N% / N! / N# and
its own bytes recorded before the call; `R=F(N)` (R a double, its 8 bytes) and `Q=USR(F(N))` (the result's TYPE and
its own bytes, unconverted); an `ID` apparatus row per argument; R = -12345 and the type cell 255 before every case.
What is new here is the MATRIX: a transcendental's last digits are the reference's own approximation, so its rules
are bounds against the exact value (computed by the model at 60 digits), and the arguments are chosen
  * at the special points (EXP(0), LOG(1), SIN / TAN / ATN (0), COS(0)) and at +-x for the symmetry rules;
  * across the whole range: tiny (1E-64, 1E-10), around 1, large (1E10 ... 9.99999E62), in every type;
  * at EXP's edges: overflow from 145.0628 up, the band of large negative arguments (-149.67 .. -297.03) the
    reference reports as Overflow (docs/keywords/EXP.md), and the huge negative ones (-40000 ... -9.99999E62);
  * at LOG's domain edge (0, -0, the smallest positive numbers, negatives);
  * for SIN / COS / TAN at the reduction's landmarks: 14-digit multiples of pi/4, pi/2, pi, 2 pi; and from 1E10 to
    1E38, where the reference's reduction leaves fewer fraction digits of a turn (D-TANBIG: TAN(1E38) Overflow);
  * for ATN, 1, sqrt(3), 1/sqrt(3), and very large arguments.

THE GROUPS (case ids "KTR <group> <fn> <text>" / "KTR FX <i>"): every function over each group's arguments, one
argument type per group, sized so no group's records reach $F380 (asserted):
  TI    the integers TI_ARGS (N%)
  TS1   singles, the EXP / LOG landmarks      TS2   singles, the angle landmarks
  TD1   doubles, the EXP / LOG landmarks      TD2   doubles, the angle landmarks
  FX    fixed statements (types, missing / extra arguments, spaces, literals, nesting, non-canonical bytes;
        S$ = "12")

    python3 probes/basic/spec/ktrans.py [GROUP ...] [--out scratchpad/KTR_run1.out]
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
RUN = "KTR_run1.out"
R_SENT = kmath.R_SENT
TYPES = kmath.TYPES
FNS = ["ID", "EXP", "LOG", "SIN", "COS", "TAN", "ATN"]

TI_ARGS = ["0", "1", "-1", "2", "-2", "3", "-3", "4", "5", "-5", "7", "10", "-10", "20", "-20", "50", "-50", "100",
           "-100", "145", "146", "-147", "-148", "-149", "-150", "-200", "-297", "-298", "1000", "-1000", "12345",
           "32767", "-32768"]
TS1_ARGS = ["0", "-0", "1E-64", "-1E-64", "1E-20", "1E-10", "-1E-10", "1E-6", "-1E-6", ".001", "-.001", ".01", ".1",
            "-.1", ".2", ".25", ".5", "-.5", ".693147", ".7", ".75", ".9", ".999999", "1", "-1", "1.00001", "1.5",
            "-1.5", "2", "-2", "2.5", "-2.5", "2.71828", "3", "5", "10", "-10", "20", "-20", "50", "-50", "99",
            "100", "-100", "145.062", "145.063", "-147.3", "-147.4", "-149.66", "-149.67", "-297.03", "-297.04",
            "-1000", "1000", "12345.6", "99999.9"]
TS2_ARGS = [".785398", "-.785398", "1.0472", ".523599", "1.5708", "-1.5708", "1.57079", "3.14159", "-3.14159",
            "3.1416", "4.71239", "6.28318", "6.28319", "7", "10.5", "100.5", "1E5", "123456", "1E6", "-1E6", "1E10",
            "1E12", "1E13", "5E13", "7E13", "1E14", "1E20", "1E38", "-1E38", "9.99999E62", "-9.99999E62",
            "1.23456E-5", "3.33333", ".333333", "-.333333", "4", "8", "16", "64", ".0625", "1E30", "-1E30", "1E-30",
            "1E-63", "1.73205", ".57735", "-.57735", "-40000", "-65535", "-65536", "-99999",
            "-1E5", "-999999"]
TD1_ARGS = ["0", "-0", "1D-64", "-1D-64", "1D-14", "-1D-14", "1D-10", "1D-7", ".001", "-.001", ".1", "-.1", ".5",
            "-.5", ".69314718055995", "1.0000000000001", ".99999999999999", "1", "-1", "2", "-2", "2.302585092994",
            "2.718281828459", "2.7182818284590", "10", "-10", "1.2345678901234", "-1.2345678901234",
            "12.345678901234", "50", "-50", "100", "-100", "145.06286", "145.0628", "145.063", "-147.3", "-147.4",
            "-149.668", "-149.67", "-297.033", "-297.04", "-1000", "1000", "1D10", "1D20", "1D-20",
            "9.9999999999999D62", "-9.9999999999999D62", "32767.9", "123456789.01234"]
TD2_ARGS = [".78539816339745", "-.78539816339745", ".78539816339744", "1.0471975511966", ".5235987755983",
            "1.5707963267949", "-1.5707963267949", "1.5707963267948", "3.1415926535898", "-3.1415926535898",
            "3.1415926535897", "4.7123889803847", "6.2831853071796", "-6.2831853071796", "12.566370614359", "1000",
            "-1000", "1D10", "-1D10", "1D11", "1D12", "1D13", "7D13", "1D14", "1D38", "1.7320508075689",
            ".57735026918963", "-.57735026918963", "1D-5", "-1D-5", ".12345678901234", "-.12345678901234",
            "1234.5678901234", "31415.926535898", "100", "3.3333333333333", "1D30", "-1D30", "1D-30"]
ARGS = {"TI": ("I", TI_ARGS), "TS1": ("S", TS1_ARGS), "TS2": ("S", TS2_ARGS), "TD1": ("D", TD1_ARGS),
        "TD2": ("D", TD2_ARGS)}
GAPS = {"TI": 6000.0, "TS1": 6000.0, "TS2": 6000.0, "TD1": 6000.0, "TD2": 6000.0, "FX": 2500.0}
ORDER = ["TI", "TS1", "TS2", "TD1", "TD2", "FX"]

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
    _v(f"{_f}({_f}(.5))", "nested")
    _v(f"{_f}(N!)", "a single with exponent byte 0, digit bytes 10 00 00", PRE0)
    _v(f"{_f}(N!)", "a single with exponent byte 80, digit bytes 10 00 00", PRE80)
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
            cases.append((f"KTR FX {i}", dict(fn=fn, stmt=stmt, why=why, ustmt=ustmt, ty=None, text=None)))
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
    cases = [(f"KTR {group} {f} {x}", dict(fn=f, ty=ty, text=x, stmt=None, why=None, ustmt=None))
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
