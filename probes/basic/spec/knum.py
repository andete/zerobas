#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""KNUM -- the measured cases behind docs/keywords/STR$.md, VAL.md, HEX$.md, OCT$.md and BIN$.md: the strings
region's third keyword probe, the number <-> string family (D-KWSPEC; docs/keywords/spec-plan.md, docs/spec-method.md
§3a). The frame, the record framing and the run file are the shared RAM-record harness's (probes/basic/spec/ramrec.py).

Clean room: typed BASIC in, RAM out. The program is TYPED on each machine; it evaluates every case and POKEs a record
of the outcome into RAM, which the harness reads after the program's own done flag. No reference ROM byte is read.

THE SETUP SEPARATES (spec-method §3a):
  * a numeric argument is READ from DATA into a variable of the case's own type -- N% (integer), N! (single) or N#
    (double) -- and that variable's own bytes are recorded BEFORE the call (ramrec.number decodes them exactly), so
    the rules work from the value the function was given, not from the DATA text (READ's own rounding is not this
    page's subject);
  * a string result is recorded byte for byte (its first 24 bytes, then the length and the sum of all its bytes), so
    a leading or trailing space, an `E` or a `D`, a digit more or less, is seen -- never read through a string
    function, only VARPTR and PEEK;
  * a numeric result is R's own 8 bytes (a double): a VAL result of 6 digits and one of 14 differ there;
  * every case writes both result variables' sentinels first -- R$ = CHR$(250), R = -12345 -- so an error (which
    assigns nothing) cannot read as a result, and a function that writes the wrong kind of result is seen;
  * the numbers sit where rival rules disagree: truncation vs rounding vs INT (-.9, -.5, .5, 2.5, 32767.5, 65535.9),
    the range test before vs after truncation (-32768.5, 65535.5), both ends of -32768..65535, the fixed / exponent
    boundary of PRINT's format on both sides for single and double, 6 / 14 significant digits and one more;
  * VAL's strings are built in string space byte by byte, and the byte just AFTER the string in memory is recorded:
    the build leaves the string's own prefix behind it ("12" is followed by "1"), so a VAL that read past the end of
    its string is seen.

THE RECORD (47 bytes per case, from $C001):
  0 E          ERR after the case (0: none)
  1-8 ARG      the numeric argument's own bytes, read before the call (2 / 4 / 8 of them, the rest 0); VAL: byte 1
               is the byte after S$ in memory (0 for an empty S$), the rest 0
  9 RL         R$'s length (from its descriptor)
  10-33 RB     R$'s first 24 bytes (0 past its end)
  34-35 RS     the sum of all of R$'s bytes
  36-43 R      R's 8 bytes (a double)
  44 SL, 45-46 SS   S$ after the case: length, sum (VAL's source is kept)

THE GROUPS (case ids "KNM <group> ..."):
  SN    STR$(N): N%, N! and N# over SN_INT / SN_SGL / SN_DBL                 -> "KNM SN <type> <text>"
  RX    HEX$(N), OCT$(N), BIN$(N): N%, N!, N# over RX_INT / RX_SGL / RX_DBL  -> "KNM RX <fn> <type> <text>"
  VL    VAL(S$) over VL_SRC (byte strings)                                    -> "KNM VL <i>"
  FX    fixed statements (types, missing / extra arguments, spaces, literals, sub-strings; S$ = "12345", T$ = "6.5")
                                                                              -> "KNM FX <i>"

    python3 probes/basic/spec/knum.py [GROUP ...] [--out scratchpad/KNM_run1.out]
(run through tools/agent_wt.py: it boots the VG-8020 and zerobas's NODISK machine)."""
import os
import sys
from types import SimpleNamespace as NS

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, HERE)
import ramrec  # noqa: E402
import kstr  # noqa: E402  (BUILD, spec_values: a byte string from DATA, built in string space)

REC = 47
RUN = "KNM_run1.out"
R_SENT = -12345
TYPES = {"I": ("%", 2), "S": ("!", 4), "D": ("#", 8)}

SN_INT = ["0", "1", "-1", "5", "-34", "9", "10", "99", "100", "255", "32767", "-32767", "-32768"]
SN_SGL = ["0", "1", "-1", ".5", "-.5", "1.5", "-1.5", "10", "100", "1000", "10000", "32767", "32768", "65535",
          "99999", "100000", "999999", "1000000", "1100000", "1200000", "1234567", "123456", "12345.6", "1234.56",
          ".123456", ".0123456", ".00123456", ".1", ".01", ".02", ".012", ".001", ".0012", ".0001", "1E-5",
          "1.5E-5", "-1E-5", "-.01", "-.001", "1E-10", "1E5", "1E6", "1E7", "-1E6", "-999999", "1E10", "1.5E10",
          "1E37", "1E62", "9.99999E62", "1E-62", "1E-63", "1E-64", "1E-65", "1E13", "1E14", "1.5E13", "1.23456E13",
          "1.23456E14", "-1E13", "-1E14", ".0099", ".00999999", "99999.9"]
SN_DBL = ["0", "1", "-1", ".5", "1.5", "-1.5", "32768", "-32769", "1234567", "1234567.8", "1E6", "1E7",
          "12345678901234", "99999999999999", "100000000000000", "123456789012345", "1E13", "1E14", "1E15",
          "1E16", "-12345678901234", ".1", ".01", ".001", ".0012345678901234", ".012345678901234",
          ".12345678901234", ".33333333333333", "1.2345678901234", "1D-5", "-1D-5", "1D-10", "1D62", "1D-64",
          "9.9999999999999D62", "123456.7", "1234567890.12", "1.5D13", "1.2345678901234D13", ".0099", "1D-2",
          "9.9999999999999D-3", "12345678901.234", "-1D14"]
RX_INT = ["-32768", "-32767", "-1", "0", "1", "255", "256", "32767"]
RX_SGL = ["-32769", "-32768.5", "-.9", "1.5", "-1.5", "32767.9", "65535.9", "65536"]
RX_DBL = ["-1E10", "-70000", "-65536", "-32769", "-32768.5", "-32768", "-32767.9", "-32767", "-5.7", "-1.5", "-1",
          "-.9", "-.5", "-.1", "0", ".1", ".5", ".9", "1", "1.5", "2.5", "5.7", "7", "8", "15", "16", "255", "256",
          "4095", "4096", "32767", "32767.5", "32767.9", "32768", "32768.5", "40000", "65534.5", "65535", "65535.5",
          "65535.9", "65536", "70000", "1E10"]
RX_FNS = ["HEX$", "OCT$", "BIN$"]


def _vl():
    s = [b"", b" ", b"   ", b"ABC", b"12", b"-12", b"+12", b"1.5", b".5", b"5.", b"0", b"-0", b"00012", b"1E3",
         b"1D3", b"1e3", b"1d3", b"1E-3", b"1E+3", b"1E", b"1E+", b"1E-", b"E3", b".E3", b".", b"-", b"+", b"--1",
         b"+-1", b"-+1", b"12ABC", b"1.2.3", b"1,000", b"2+3", b"$12", b"1E3E3", b"1.5E1.5",
         b"1 2", b" - 12", b"1 . 5", b"1 E 3", b"1E- 3", b" 12", b"12 ", b"1" + b" " * 40 + b"2",
         b"\t12", b"1\t2", b"\n12", b"1\x002", b"\x0012", b"1\xff2",
         b"&HFF", b"&hff", b"&HfF", b"&O17", b"&o17", b"&B101", b"&b101", b"&H7FFF", b"&H8000", b"&HFFFF",
         b"&H10000", b"&H1FFFF", b"&HFFFFF", b"&O77777", b"&O100000", b"&O177777", b"&O200000", b"&B1111111111111111",
         b"&B10000000000000000", b"&HZZ", b"&HG", b"&O9", b"&O8", b"&B2", b"&H", b"&O", b"&B", b"&", b"&17",
         b"&Q1", b"-&H10", b"+&H10", b" &HFF", b"& H10", b"&H 10", b"&H1 0", b"&HFFg", b"&H00FF", b"&H0000FFFF",
         b"&H.5", b"&HFF.5", b"&HFFE1",
         b"1E99", b"1D99", b"-1E99", b"1E62", b"1E63", b"9.99999E62", b"9.999995E62", b"1E-62", b"1E-63", b"1E-64",
         b"1E-65", b"1E-66", b"1E-99", b"1D-64", b"1D-65",
         b"32767", b"32768", b"-32768", b"-32769", b"40000", b"65535", b"65536",
         b"123456", b"1234567", b"999999", b"9999995", b"9999994", b"12345678901234", b"123456789012345",
         b"1234567890123456", b"99999999999999", b"999999999999995", b"999999999999994",
         b"0.1234567", b"1.234565", b"1.23456789E3", b"1.23456789D3", b"1.234565E0", b"1.234575E0",
         b"1.2345649E0", b"1.2345651E0", b".1234567", b"1234567E-7",
         b"12%", b"12%3", b"1.5%", b"40000%", b"1!", b"1.5!", b"1234567!", b"1#", b"1.5#", b"12345678#",
         b"1.5!E3", b"1E3!",
         b"1" * 255, b"1" + b" " * 254, b" " * 254 + b"7", b"0" * 254 + b"7", b"." + b"0" * 70 + b"1",
         # added after the first run: which control characters are skipped, the & / letter gap, digit-count limits
         b"\r12", b"\x0b12", b"\x0c12", b"\x1c12", b"\x1f12", b"\x7f12", b"\xa012", b"1\n2", b"-\t12", b"1\t.\t5",
         b"1E\t3", b"&\tH10", b"&\nH10", b"&  H10", b"& O17", b"& B101", b"&H\t10",
         b"1" * 63, b"1" * 64, b"1" * 65, b"1" * 128, b"1" * 129, b"1" * 200,
         b"." + b"0" * 62 + b"1", b"." + b"0" * 63 + b"1", b"." + b"0" * 64 + b"1", b"5E-65", b"9.9E-65",
         b"12345678901234.5", b"12345678901234.4"]
    return s


VL_SRC = _vl()
GROUPS = {
    "SN": [("STR$", t, x) for t, xs in (("I", SN_INT), ("S", SN_SGL), ("D", SN_DBL)) for x in xs],
    "RX": [(f, t, x) for t, xs in (("I", RX_INT), ("S", RX_SGL), ("D", RX_DBL)) for x in xs for f in RX_FNS],
}
GAPS = {"SN": 3000.0, "RX": 3000.0, "VL": 4000.0, "FX": 600.0}

FX = [
    # (the keyword, the statement, what it separates); S$ = "12345", T$ = "6.5"
    ("STR$", "R$=STR$(5)", "plain"),
    ("STR$", "R$=STR$(-5)", "a negative number"),
    ("STR$", 'R$=STR$("A")', "a string as the argument"),
    ("STR$", "R$=STR$(S$)", "a string variable as the argument"),
    ("STR$", "R$=STR$(1/0)", "the argument's own error"),
    ("STR$", "R$=STR$()", "no argument"),
    ("STR$", "R$=STR$(5,1)", "an extra argument"),
    ("STR$", "R$=STR$(5", "no closing parenthesis"),
    ("STR$", "R$=STR$", "no parenthesis"),
    ("STR$", "R$=STR$ (5)", "a space before the parenthesis"),
    ("STR$", "R$=STR$( 5 )", "spaces around the argument"),
    ("STR$", "R$=STR$(5 )", "a space before the closing parenthesis"),
    ("STR$", "R$=STR$( 5)", "a space after the parenthesis"),
    ("STR$", "R$=STR$(&HFF)", "a hex argument"),
    ("STR$", "R$=STR$(&HFFFF)", "a hex argument past 32767"),
    ("STR$", "R$=STR$(5%)", "an integer literal"),
    ("STR$", "R$=STR$(1.5#)", "a double literal"),
    ("STR$", "R$=STR$(-0)", "minus zero"),
    ("STR$", "R$=STR$(1/4)", "an expression"),
    ("STR$", 'R$=STR$(5)+"X"', "the result in a concatenation"),
    ("STR$", "R=STR$(5)", "the result is a string"),
    ("VAL", "R=VAL(S$)", "plain"),
    ("VAL", "R=VAL(5)", "a number as the argument"),
    ("VAL", "R=VAL(1/0)", "the argument's own error"),
    ("VAL", "R=VAL()", "no argument"),
    ("VAL", 'R=VAL(S$,"2")', "an extra argument"),
    ("VAL", "R=VAL(S$", "no closing parenthesis"),
    ("VAL", "R=VAL", "no parenthesis"),
    ("VAL", "R=VAL (S$)", "a space before the parenthesis"),
    ("VAL", "R=VAL( S$ )", "spaces around the argument"),
    ("VAL", "R=VAL(S$ )", "a space before the closing parenthesis"),
    ("VAL", "R=VAL( S$)", "a space after the parenthesis"),
    ("VAL", 'R=VAL("12")', "a literal (in the program text)"),
    ("VAL", 'R=VAL("12" )', "a space before the closing parenthesis, a literal"),
    ("VAL", 'R=VAL("12")+1', "the result in arithmetic"),
    ("VAL", "R=VAL(LEFT$(S$,2))", "a LEFT$ of a longer string"),
    ("VAL", "R=VAL(MID$(S$,2,2))", "a MID$ of a longer string"),
    ("VAL", "R=VAL(RIGHT$(S$,2))", "a RIGHT$ of a longer string"),
    ("VAL", "R=VAL(S$+T$)", "a concatenation"),
    ("VAL", "R=VAL(T$+S$)", "a concatenation, the other way"),
    ("VAL", 'R=VAL("&HFF")', "a hex literal string"),
    ("VAL", 'R=VAL("")', "an empty literal"),
    ("VAL", 'R=VAL("1E99")', "an overflowing literal string"),
    ("VAL", 'R=VAL("&")', "a bare & in a literal string"),
    ("VAL", "R$=VAL(S$)", "the result is a number"),
]
for _f in RX_FNS:
    FX += [
        (_f, f"R$={_f}(255)", "plain"),
        (_f, f'R$={_f}("A")', "a string as the argument"),
        (_f, f"R$={_f}(S$)", "a string variable as the argument"),
        (_f, f"R$={_f}(1/0)", "the argument's own error"),
        (_f, f"R$={_f}()", "no argument"),
        (_f, f"R$={_f}(255,1)", "an extra argument"),
        (_f, f"R$={_f}(255", "no closing parenthesis"),
        (_f, f"R$={_f}", "no parenthesis"),
        (_f, f"R$={_f} (255)", "a space before the parenthesis"),
        (_f, f"R$={_f}( 255 )", "spaces around the argument"),
        (_f, f"R$={_f}(255 )", "a space before the closing parenthesis"),
        (_f, f"R$={_f}(&HFF)", "a hex argument"),
        (_f, f"R$={_f}(255%)", "an integer literal"),
        (_f, f"R$={_f}(70000)", "an overflowing literal"),
        (_f, f"R={_f}(255)", "the result is a string"),
    ]
FX_S, FX_T = b"12345", b"6.5"

RECORD = [
    "900 V=VARPTR(R$):GOSUB 950:POKE A,E:POKE A+9,RL:POKE A+34,S-INT(S/256)*256:POKE A+35,INT(S/256)",
    "905 FOR K=0 TO 23:X=0:IF K<RL THEN X=PEEK(P+K)",
    "906 POKE A+10+K,X:NEXT",
    "910 V=VARPTR(R):FOR K=0 TO 7:POKE A+36+K,PEEK(V+K):NEXT",
    "920 V=VARPTR(S$):GOSUB 950:POKE A+44,RL:POKE A+45,S-INT(S/256)*256:POKE A+46,INT(S/256):A=A+47:RETURN",
] + ramrec.STR_DIGEST + [ramrec.ERRLINE]


def program(group):
    """the typed lines (numbered program + RUN) and the case list [(id, meta)] in record order"""
    if group == "FX":
        lines = [ramrec.head(2000), "20 GOSUB 300:S$=Q$:GOSUB 300:T$=Q$:GOTO 2000"]
        cases = []
        for i, (fn, stmt, why) in enumerate(FX):
            lines.append(f"{2000 + 2 * i} E=0:R$=CHR$(250):R={R_SENT}:FOR K=1 TO 8:POKE A+K,0:NEXT:{stmt}")
            lines.append(f"{2001 + 2 * i} GOSUB 900")
            cases.append((f"KNM FX {i}", dict(fn=fn, stmt=stmt, why=why, s=FX_S, t=FX_T, ty=None, text=None)))
        lines += [f"{2000 + 2 * len(FX)} " + ramrec.TAIL] + kstr.BUILD + RECORD
        lines += ramrec.data(1000, kstr.spec_values(FX_S) + kstr.spec_values(FX_T))
        return lines + ["RUN"], cases
    if group == "VL":
        lines = [ramrec.head(2000),
                 "20 READ I1:FOR J1=1 TO I1:GOSUB 300:S$=Q$:V=VARPTR(S$):P=PEEK(V+1)+256*PEEK(V+2)",
                 "30 FOR K=2 TO 8:POKE A+K,0:NEXT:IF PEEK(V)=0 THEN POKE A+1,0 ELSE POKE A+1,PEEK(P+PEEK(V))",
                 f"40 E=0:R$=CHR$(250):R={R_SENT}:GOSUB 210:GOSUB 900:NEXT J1",
                 "70 " + ramrec.TAIL,
                 "210 R=VAL(S$):RETURN"] + kstr.BUILD + RECORD
        vals = [str(len(VL_SRC))]
        for s in VL_SRC:
            vals += kstr.spec_values(s)
        lines += ramrec.data(1000, vals)
        cases = [(f"KNM VL {i}", dict(fn="VAL", s=s, t=b"", ty=None, text=None)) for i, s in enumerate(VL_SRC)]
        return lines + ["RUN"], cases
    rows = GROUPS[group]
    fns = list(dict.fromkeys(f for f, _t, _x in rows))
    nf = len(fns)
    # DATA: per type block: the type's byte size, the count, the texts; 0 ends
    blocks = []
    for t in ("I", "S", "D"):
        xs = list(dict.fromkeys(x for _f, tt, x in rows if tt == t))
        if xs:
            blocks.append((t, xs))
    lines = [ramrec.head(2000),
             '15 S$=""',
             "20 READ TY:IF TY=0 THEN 70",
             "30 READ I2:FOR J2=1 TO I2:IF TY=2 THEN READ N% ELSE IF TY=4 THEN READ N! ELSE READ N#",
             f"40 FOR J4=1 TO {nf}:IF TY=2 THEN V=VARPTR(N%) ELSE IF TY=4 THEN V=VARPTR(N!) ELSE V=VARPTR(N#)",
             "45 FOR K=0 TO 7:X=0:IF K<TY THEN X=PEEK(V+K)",
             f"50 POKE A+1+K,X:NEXT K:E=0:R$=CHR$(250):R={R_SENT}:GOSUB 200:GOSUB 900:NEXT J4,J2:GOTO 20",
             "70 " + ramrec.TAIL,
             "200 ON J4 GOSUB " + ",".join(str(210 + 10 * k) for k in range(nf)) + ":RETURN"]
    for k, f in enumerate(fns):
        b = 210 + 10 * k
        lines += [f"{b} ON TY/2 GOTO {b + 1},{b + 2},{b + 2},{b + 3}",
                  f"{b + 1} R$={f}(N%):RETURN", f"{b + 2} R$={f}(N!):RETURN", f"{b + 3} R$={f}(N#):RETURN"]
    lines += RECORD
    vals = []
    for t, xs in blocks:
        vals += [str(TYPES[t][1]), str(len(xs))] + xs
    vals += ["0"]
    lines += ramrec.data(1000, vals)
    cases = []
    for t, xs in blocks:
        for x in xs:
            for f in fns:
                cid = f"KNM SN {t} {x}" if group == "SN" else f"KNM RX {f} {t} {x}"
                cases.append((cid, dict(fn=f, ty=t, text=x, s=b"", t=b"")))
    return lines + ["RUN"], cases


def decode(hexs, n):
    rs, why = ramrec.frame(hexs, n, REC)
    if rs is None:
        return None, why
    out = []
    for r in rs:
        try:
            rv = ramrec.number(r[36:44])
        except ValueError:
            rv = None
        rl = r[9]
        out.append(dict(e=r[0], arg=r[1:9], rl=rl, rb=r[10:34], rsum=r[34] | r[35] << 8, rbytes=r[36:44], r=rv,
                        sl=r[44], ss=r[45] | r[46] << 8))
    return out, None


def argval(c):
    """the numeric argument's exact value, from its own recorded bytes"""
    return ramrec.number(c.arg[:TYPES[c.ty][1]])


ORDER = ["SN", "RX", "VL", "FX"]


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
