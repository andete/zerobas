#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""KMKCV -- the measured cases behind docs/keywords/MKI$.md, MKS$.md, MKD$.md, CVI.md, CVS.md and CVD.md: the
conversion region's second keyword probe, between numbers and their bytes in a string (D-KWSPEC;
docs/keywords/spec-plan.md §2 region 3; docs/spec-method.md §3a). The USR type readout is kmath.py's (its `ROUTINE`);
the run file is the shared RAM-record harness's (probes/basic/spec/ramrec.py).

Clean room: typed BASIC in, RAM out. The program is TYPED on each machine; it evaluates every case and POKEs a record
of the outcome into RAM, which the harness reads after the program's own done flag. No reference ROM byte is read;
every variable read through VARPTR is assigned first; the record area ends below $F380 (asserted per group).

THE SETUP SEPARATES (spec-method §3a):
  * MK*$: the number is READ into N% / N! / N# and its own bytes recorded before the call; the result S$'s length
    and first 8 bytes are recorded (VARPTR of S$: its descriptor, then the bytes) -- so the rules work from the bytes
    given and the bytes returned. Each of MKI$ / MKS$ / MKD$ takes every type, to see what each does with a number
    that is not its own type (converted? by which rule? or an error?);
  * CV*: the source string is BUILT from DATA bytes with CHR$ (lengths 0 to 9; canonical numbers, non-canonical
    exponent bytes, non-BCD digit nibbles), its length and first 8 bytes recorded; then `R=CVx(S$)` -- R a double, its
    8 bytes -- and `Q=USR(CVx(S$))`, whose routine copies VALTYP and DAC (the result's TYPE and its own bytes);
  * before every case S$ = "", R = -12345 and the USR type cell 255, so an error, which assigns nothing, cannot read
    as a result.

THE RECORD (37 bytes per case, from $C001):
  0 E1          ERR after the case's statement
  1-8 ARG       MK: the number's own bytes (2 / 4 / 8, the rest 0); CV: the source string's first 8 bytes; FX: 0
  9 ALEN        CV: the source string's length; else 0
  10-17 R       R's 8 bytes after the case (a double; -12345 unless the case assigned it)
  18 SL         LEN(S$) after the case
  19-26 SB      S$'s first 8 bytes (0 beyond its length)
  27 E2         ERR after the USR form (CV, FX value forms); 0 where there is none
  28 VT         the type USR saw (2 / 4 / 8; 255: USR not reached)
  29-36 DAC     DAC's 8 bytes as USR saw them

THE GROUPS (case ids "KMC <group> <i>"), MK / CV / FX on the VG-8020 and zerobas NODISK (no Disk BASIC: every call is
error 5 there), and DMK / DCV / DFX the same programs on the National CF-3300 and zerobas's DISK build (each booted
with a copy of disk/test720.dsk), the pages' reference:
  MK    every number in MK_NUMS (each its own type) through MKI$, MKS$ and MKD$
  CV    every byte string in CV_STRS through CVI, CVS and CVD
  FX    fixed statements: errors, forms, round trips (S$ = "12" where a string argument is named)

    python3 probes/basic/spec/kmkcv.py [GROUP ...] [--out scratchpad/KMC_run1.out]
(it boots the VG-8020 and zerobas's NODISK machine, once per group)."""
import os
import sys
from types import SimpleNamespace as NS

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, HERE)
import kmath  # noqa: E402
import ramrec  # noqa: E402

REC = 37
RUN = "KMC_run1.out"
R_SENT = kmath.R_SENT
TYPES = {"I": ("%", 2, 1), "S": ("!", 4, 2), "D": ("#", 8, 3)}
MKS = ["MKI$", "MKS$", "MKD$"]
CVS_ = ["CVI", "CVS", "CVD"]

MK_NUMS = [("I", "0"), ("I", "1"), ("I", "-1"), ("I", "255"), ("I", "256"), ("I", "12345"), ("I", "32767"),
           ("I", "-32768"),
           ("S", "0"), ("S", "1"), ("S", "-1"), ("S", ".5"), ("S", "2.5"), ("S", "-2.5"), ("S", "1.5"), ("S", "-1.5"),
           ("S", "32767.9"), ("S", "-32768.9"), ("S", "32768"), ("S", "1E10"), ("S", "1.23456"), ("S", "1E-64"),
           ("D", "0"), ("D", "1"), ("D", "-1"), ("D", "2.5"), ("D", "-2.5"), ("D", "1.2345678901234"),
           ("D", "-1.2345678901234"), ("D", "1.2345650000001"), ("D", "32767.5"), ("D", "-32768.5"), ("D", "1D20"),
           ("D", "9.999995D62"), ("D", "1.2345678D-10")]
# (bytes, what it separates)
CV_STRS = [([], "the empty string"), ([0x01], "one byte"), ([0x01, 0x02], "two bytes"),
           ([0x01, 0x02, 0x03], "three bytes"), ([0x34, 0x12], "the integer &H1234"),
           ([0xFF, 0xFF], "the integer -1"), ([0x00, 0x80], "the integer -32768"),
           ([0x41, 0x10, 0x00, 0x00], "the single 1"), ([0xC1, 0x12, 0x34, 0x56], "the single -1.23456"),
           ([0x00, 0x10, 0x00, 0x00], "a single, exponent byte 0, digits 10 00 00"),
           ([0x80, 0x10, 0x00, 0x00], "a single, exponent byte &H80, digits 10 00 00"),
           ([0x41, 0x1A, 0x00, 0x00], "a single with a non-BCD digit nibble"),
           ([0x41, 0x10, 0x00, 0x00, 0x77], "five bytes, a single first"),
           ([0x41, 0x12, 0x34, 0x56, 0x78, 0x90, 0x12, 0x34], "the double 1.2345678901234"),
           ([0x7F, 0x99, 0x99, 0x99, 0x99, 0x99, 0x99, 0x99], "the largest double"),
           ([0x41, 0x12, 0x34, 0x56, 0x78, 0x90, 0x12, 0x34, 0x55], "nine bytes, a double first"),
           ([0x41, 0x12, 0x34, 0x56, 0x78, 0x90, 0x12], "seven bytes")]
GAPS = {"MK": 4000.0, "CV": 4000.0, "FX": 2500.0, "DMK": 4000.0, "DCV": 4000.0, "DFX": 2500.0, "FY": 2500.0,
        "DFY": 2500.0}
ORDER = ["MK", "CV", "FX", "DMK", "DCV", "DFX", "FY", "DFY"]
DISKG = ("DMK", "DCV", "DFX", "DFY")        # the same programs on the Disk BASIC machines (the pages' reference: CF-3300)


def machines(group):
    if group in DISKG:
        return (("ref", ramrec.DISK_REF), ("zb", ramrec.DISK_ZB))
    return (("ref", ramrec.REF), ("zb", ramrec.ZB))

# FX: (fn, statement, what it separates, the USR form or None); S$ = "12" where the statement names it, assigned
# by the statement itself
FX = []
for _f in MKS:
    FX += [(_f, f'S$={_f}("A")', "a string as the argument", None),
           (_f, f"S$={_f}(1/0)", "the argument's own error", None),
           (_f, f"S$={_f}()", "no argument", None),
           (_f, f"S$={_f}(5,1)", "an extra argument", None),
           (_f, f"S$={_f}(5", "no closing parenthesis", None),
           (_f, f"S$={_f}", "no parenthesis", None),
           (_f, f"R={_f}(5)", "the result assigned to a number", None),
           (_f, f"S$={_f} (5)", "a space before the parenthesis", None),
           (_f, f"S$={_f}(7)", "a literal without a point", None),
           (_f, f"S$={_f}(2.5)", "a literal with a point", None),
           (_f, f"S$={_f}(1/3)", "an expression (a double)", None),
           (_f, f"S$={_f}(&H8000)", "a hex literal", None),
           (_f, f"S$={_f}(40000)", "40000 (beyond an integer)", None)]
for _f in CVS_:
    FX += [(_f, f"R={_f}(5)", "a number as the argument", None),
           (_f, f'R={_f}("A"+"B"+"C"+"D"+"E"+"F"+"G"+"H")', "an expression of 8 bytes", f'Q=USR({_f}("A"+"B"+"C"+"D"+"E"+"F"+"G"+"H"))'),
           (_f, f"R={_f}()", "no argument", None),
           (_f, f'R={_f}("AB","CD")', "an extra argument", None),
           (_f, f'R={_f}("ABCDEFGH"', "no closing parenthesis", None),
           (_f, f"R={_f}", "no parenthesis", None),
           (_f, f'S$={_f}("ABCDEFGH")', "the result assigned to a string", None)]
FX += [("CVI", "R=CVI(MKI$(-12345))", "a round trip", "Q=USR(CVI(MKI$(-12345)))"),
       ("CVS", "R=CVS(MKS$(-1.23456))", "a round trip", "Q=USR(CVS(MKS$(-1.23456)))"),
       ("CVD", "R=CVD(MKD$(1.2345678901234#))", "a round trip", "Q=USR(CVD(MKD$(1.2345678901234#)))"),
       ("CVI", 'S$="ABCDEFGH":R=CVI(MID$(S$,3))', "a string from MID$", 'Q=USR(CVI(MID$(S$,3)))')]

# FY (goldfish pass 1, 2026-11-24, scratchpad/REVIEW-m2-gMKCV1.md): negative Overflow for MKI$; MKS$'s exact ties and
# the near side of its Overflow; MID$ for CVS / CVD; a CV argument's own error; S$ set to "XY" before an error (is it
# left alone, or emptied?); a round trip whose value is not R's sentinel; non-canonical doubles through CVD
FY = [("MKI$", "S$=MKI$(-32769)", "-32769", None), ("MKI$", "S$=MKI$(-1E10)", "-1E10", None),
      ("MKI$", "S$=MKI$(-32768.9999#)", "-32768.9999 (fits after truncation)", None),
      ("MKS$", "S$=MKS$(1.234565#)", "an exact tie, even 6th digit", None),
      ("MKS$", "S$=MKS$(-1.234565#)", "an exact tie, negative", None),
      ("MKS$", "S$=MKS$(9.9999949999999D62)", "just below the Overflow threshold", None),
      ("CVS", 'S$="ABCDEFGHIJ":R=CVS(MID$(S$,3))', "a string from MID$", 'Q=USR(CVS(MID$(S$,3)))'),
      ("CVD", 'S$="ABCDEFGHIJ":R=CVD(MID$(S$,3))', "a string from MID$", 'Q=USR(CVD(MID$(S$,3)))'),
      ("CVI", "R=CVI(CHR$(1/0))", "the argument's own error", None),
      ("CVS", "R=CVS(CHR$(1/0))", "the argument's own error", None),
      ("CVD", "R=CVD(CHR$(1/0))", "the argument's own error", None),
      ("MKI$", 'S$="XY":S$=MKI$(32768)', "S$ before an Overflow", None),
      ("MKS$", 'S$="XY":S$=MKS$("A")', "S$ before a type error", None),
      ("CVI", 'S$="XY":S$=CVI("AB")', "S$ before a type error", None),
      ("CVI", "R=CVI(MKI$(-12346))", "a round trip, not the sentinel", "Q=USR(CVI(MKI$(-12346)))"),
      ("CVD", "R=CVD(CHR$(0)+CHR$(16)+STRING$(6,0))", "a double, exponent byte 0, digits 10 00 ...",
       "Q=USR(CVD(CHR$(0)+CHR$(16)+STRING$(6,0)))"),
      ("CVD", "R=CVD(CHR$(128)+CHR$(16)+STRING$(6,0))", "a double, exponent byte &H80, digits 10 00 ...",
       "Q=USR(CVD(CHR$(128)+CHR$(16)+STRING$(6,0)))"),
      ("CVD", "R=CVD(CHR$(65)+CHR$(26)+STRING$(6,0))", "a double with a non-BCD digit nibble",
       "Q=USR(CVD(CHR$(65)+CHR$(26)+STRING$(6,0)))")]

RECORD = [
    ramrec.ERRLINE,
    f'880 E=0:R={R_SENT}:S$="":POKE &HBF80,255:FOR K=1 TO 9:POKE A+K,0:NEXT:RETURN',
    "900 POKE A,E1:V=VARPTR(R):FOR K=0 TO 7:POKE A+10+K,PEEK(V+K):POKE A+29+K,PEEK(&HBF81+K):NEXT",
    "910 V=VARPTR(S$):L=PEEK(V):P=PEEK(V+1)+256*PEEK(V+2):POKE A+18,L:FOR K=0 TO 7:X=0:IF K<L THEN X=PEEK(P+K)",
    "920 POKE A+19+K,X:NEXT:POKE A+27,E2:POKE A+28,PEEK(&HBF80):A=A+37:RETURN",
]


def _num(ty, x):
    return str(TYPES[ty][2]) + "," + x


def program(group):
    """the typed lines (numbered program + RUN) and the case list [(id, meta)] in record order"""
    if group in DISKG:
        lines, cases = program(group[1:])
        cases = [(cid.replace(f"KMC {group[1:]} ", f"KMC {group} "), meta) for cid, meta in cases]
        _fits(group, cases)
        return lines, cases
    routine = [str(v) for v in kmath.ROUTINE]
    head = [kmath.head(), "20 FOR K=0 TO 17:READ X:POKE &HBF00+K,X:NEXT:DEFUSR=&HBF00"]
    if group == "MK":
        lines = head + [
            "30 READ I2:FOR J2=1 TO I2:READ J3,J5:GOSUB 880:ON J5 GOSUB 300,310,320",
            "40 E=0:ON 3*J3+J5-3 GOSUB 401,402,403,404,405,406,407,408,409:E1=E:E2=0:GOSUB 900:NEXT J2",
            "50 " + ramrec.TAIL,
            "300 READ N%:V=VARPTR(N%):FOR K=0 TO 1:POKE A+1+K,PEEK(V+K):NEXT:RETURN",
            "310 READ N!:V=VARPTR(N!):FOR K=0 TO 3:POKE A+1+K,PEEK(V+K):NEXT:RETURN",
            "320 READ N#:V=VARPTR(N#):FOR K=0 TO 7:POKE A+1+K,PEEK(V+K):NEXT:RETURN"]
        k = 401
        for f in MKS:
            for t in "I", "S", "D":
                lines.append(f"{k} S$={f}(N{TYPES[t][0]}):RETURN")
                k += 1
        vals, cases = [], []
        for f in MKS:
            for ty, x in MK_NUMS:
                vals += [str(MKS.index(f) + 1), str(TYPES[ty][2]), x]
                cases.append((f"KMC MK {len(cases)}", dict(fn=f, ty=ty, text=x, stmt=None, why=None, ustmt=None,
                                                          bytes=None)))
        lines += RECORD + ramrec.data(1000, routine + [str(len(cases))] + vals)
        _fits(group, cases)
        return lines + ["RUN"], cases
    if group == "CV":
        lines = head + [
            # IF L>0: an MSX FOR loop runs its body once even when it should not run at all (FOR K=1 TO 0)
            "30 READ I2:FOR J2=1 TO I2:READ J3:GOSUB 880:READ L:S$=\"\":IF L>0 THEN FOR K=1 TO L:READ X:S$=S$+CHR$(X):NEXT",
            "35 POKE A+9,L:V=VARPTR(S$):P=PEEK(V+1)+256*PEEK(V+2):FOR K=0 TO 7:X=0:IF K<L THEN X=PEEK(P+K)",
            "36 POKE A+1+K,X:NEXT",
            "40 E=0:ON J3 GOSUB 401,402,403:E1=E:E=0:ON J3 GOSUB 501,502,503:E2=E:GOSUB 900:NEXT J2",
            "50 " + ramrec.TAIL,
            "401 R=CVI(S$):RETURN", "402 R=CVS(S$):RETURN", "403 R=CVD(S$):RETURN",
            "501 Q=USR(CVI(S$)):RETURN", "502 Q=USR(CVS(S$)):RETURN", "503 Q=USR(CVD(S$)):RETURN"]
        vals, cases = [], []
        for f in CVS_:
            for bs, why in CV_STRS:
                vals += [str(CVS_.index(f) + 1), str(len(bs))] + [str(b) for b in bs]
                cases.append((f"KMC CV {len(cases)}", dict(fn=f, ty=None, text=None, stmt=None, why=why, ustmt=None,
                                                          bytes=bytes(bs))))
        lines += RECORD + ramrec.data(1000, routine + [str(len(cases))] + vals)
        _fits(group, cases)
        return lines + ["RUN"], cases
    # FX: two lines a case (the statement LAST on its line: RESUME NEXT after a syntax error goes to the next line)
    lines = head + ["25 GOTO 2000"]
    cases = []
    for i, (fn, stmt, why, ustmt) in enumerate(FX if group == "FX" else FY):
        n = 2000 + 2 * i
        lines.append(f"{n} GOSUB 880:{stmt}")
        lines.append(f"{n + 1} E1=E:E=0:" + (f"{ustmt}:E2=E" if ustmt else "E2=0") + ":GOSUB 900")
        cases.append((f"KMC {group} {i}", dict(fn=fn, stmt=stmt, why=why, ustmt=ustmt, ty=None, text=None, bytes=None)))
    lines += [f"{2000 + 2 * len(FX)} " + ramrec.TAIL] + RECORD + ramrec.data(1000, routine)
    _fits(group, cases)
    return lines + ["RUN"], cases


def _fits(group, cases):
    top = ramrec.DISK_TOP if group in DISKG else 0xF380
    assert 1 + REC * len(cases) + 1 <= top - ramrec.BASE, f"{group}: the records run past ${top:04X}"


def decode(hexs, n):
    rs, why = ramrec.frame(hexs, n, REC)
    if rs is None:
        return None, why
    out = []
    for r in rs:
        vt = r[28]
        dac = r[29:37]
        res = None
        if vt == 2:
            res = dac[2:4]
        elif vt in (4, 8):
            res = dac[:vt]
        sl = r[18]
        out.append(dict(e1=r[0], arg=r[1:9], alen=r[9], rbytes=r[10:18], sl=sl, sb=r[19:19 + min(sl, 8)],
                        e2=r[27], vt=vt, res=res))
    return out, None


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
        cap = ramrec.measure(lines, len(cases), REC, GAPS[g], machines=machines(g), disk=g in DISKG)
        bad = []
        for who in ("ref", "zb"):
            recs, why = decode(cap[who], len(cases))
            if recs is None:
                bad.append(f"{who}: {why}")
        text = open(path).read() if os.path.exists(path) else ""
        open(path, "w").write(ramrec.write_section(text, g, cap, len(cases), bad, [m for _w, m in machines(g)]))
        print(f"{g}: {len(cases)} cases; {'; '.join(bad) or 'both complete'}", flush=True)
        if not bad:
            ref, zb = (decode(cap[w], len(cases))[0] for w in ("ref", "zb"))
            diff = [cases[i][0] for i in range(len(cases)) if ref[i] != zb[i]]
            print(f"  {len(diff)} cases differ" + (": " + ", ".join(diff[:12]) if diff else ""), flush=True)
    print(f"wrote {os.path.relpath(path, ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
