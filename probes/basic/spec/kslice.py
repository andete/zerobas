#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""KSLICE -- the measured cases behind docs/keywords/LEFT$.md, RIGHT$.md and MID$.md (the function form):
the first keyword probe of the spec loop (D-KWSPEC; docs/keywords/spec-plan.md, docs/spec-method.md §3a).

Clean room: typed BASIC in, RAM out. The program is TYPED on each machine; it evaluates every case and POKEs a record
of the result into RAM, which the harness reads after the program's own done-flag (omsx_repl's sentinel capture).
No reference ROM byte is read, no hook followed.

THE SETUP SEPARATES (spec-method §3a):
  * the source string's byte at position p is CHR$(p) -- every position distinct, so "the first n" / "the last n" /
    "n from p" / "n from p-1" all give different first bytes, last bytes and checksums;
  * every count / position is given at values where the rival rules disagree: truncation vs rounding (.9, 1.5,
    1.9, 255.9, 32767.9), truncation vs INT (-.9, -.1), the overflow test before vs after truncation (-32768.5),
    5 vs 6 at both ends of the 16-bit range, 255 / 256, and the source length L itself, L - 1 and L + 1;
  * before each case R$ holds CHR$(250), so "no assignment" (an error) cannot read as a result.

THE RECORD (11 bytes per case, from $C001; $C000 is the done flag, $5A; a $C3 byte follows the last record):
  0 E      ERR after the case (0: none)
  1 RL     LEN of R$, read from its descriptor (VARPTR, PEEK -- no string function)
  2 FB     R$'s first byte (0 when empty)
  3 LB     R$'s last byte (0 when empty)
  4-5 S    the sum of R$'s bytes, LE
  6-7 W    the sum of (k * byte k), k from 1, mod 65536, LE  -- with distinct bytes, S and W pin WHICH bytes, in order
  8 SL     LEN of the source S$ after the case
  9-10 SS  the sum of S$'s bytes after the case (the source is kept)

THE GROUPS:
  LR   LEFT$(S$,N) / RIGHT$(S$,N): L in LR_L, N in NUMS          -> case id "KS LR <fn> L<l> N<n>"
  MID  MID$(S$,P[,M]): L in MID_L, P in MID_P, M in MID_M (None: the two-argument form) -> "KS MID L<l> P<p> M<m>"
  FX   fixed expressions (types, missing / extra arguments, spaces, nested; S$ = CHR$(1..5))   -> "KS FX <n>"

    python3 probes/basic/spec/kslice.py [--group LR|MID|FX ...] [--out scratchpad/KSL_run1.out]
(run through tools/agent_wt.py: it boots the VG-8020 and zerobas's NODISK machine)."""
import os
import sys
from types import SimpleNamespace as NS

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
ROOT = os.path.dirname(ROOT)
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
sys.path.insert(0, HERE)
import ramrec  # noqa: E402  (the shared RAM-record harness: frame, digest, run-file sections)

REF, ZB = ramrec.REF, ramrec.ZB
BASE = ramrec.BASE
REC = 11
RUN = "KSL_run1.out"

NUMS = ["-1E10", "-70000", "-32769", "-32768.5", "-32768", "-32767", "-1", "-.9", "-.1", "0", ".1", ".9", "1",
        "1.5", "2", "3", "4", "5", "6", "254", "255", "255.9", "256", "32767", "32767.9", "32768", "70000", "1E10"]
LR_L = [0, 1, 2, 5, 255]
LR_F = ["LEFT$", "RIGHT$"]
MID_L = [0, 1, 5, 255]
MID_P = ["-1", "0", ".9", "1", "1.9", "2", "3", "5", "6", "254", "255", "255.9", "256", "32768", "70000"]
MID_M = [None, "-1", "-.9", "0", ".9", "1", "2", "3", "4", "5", "254", "255", "255.9", "256", "32768"]
ABSENT = "-99999"

FX = [
    # (expression, what it separates)
    ("LEFT$(5,1)", "a number as the string"),
    ('LEFT$(S$,"A")', "a string as the count"),
    ("LEFT$(5,-1)", "the type before the count's range"),
    ("LEFT$(5,70000)", "the type before the count's overflow"),
    ("LEFT$(S$,1/0)", "the count's own error"),
    ("LEFT$(1/0,1)", "the string argument's own error"),
    ("LEFT$(S$)", "no count"),
    ("LEFT$()", "no argument"),
    ("LEFT$(S$,1,1)", "an extra argument"),
    ("LEFT$ (S$,2)", "a space before the parenthesis"),
    ("LEFT$( S$ , 2 )", "spaces around the arguments"),
    ("LEFT$(S$+S$,7)", "an expression as the string"),
    ("LEFT$(LEFT$(S$,4),2)", "nested"),
    ("LEFT$(S$,2%)", "an integer count"),
    ("LEFT$(S$,&H2)", "a hex count"),
    ("RIGHT$(5,1)", "a number as the string"),
    ('RIGHT$(S$,"A")', "a string as the count"),
    ("RIGHT$(5,-1)", "the type before the count's range"),
    ("RIGHT$(5,70000)", "the type before the count's overflow"),
    ("RIGHT$(S$,1/0)", "the count's own error"),
    ("RIGHT$(1/0,1)", "the string argument's own error"),
    ("RIGHT$(S$)", "no count"),
    ("RIGHT$()", "no argument"),
    ("RIGHT$(S$,1,1)", "an extra argument"),
    ("RIGHT$ (S$,2)", "a space before the parenthesis"),
    ("RIGHT$( S$ , 2 )", "spaces around the arguments"),
    ("RIGHT$(S$+S$,7)", "an expression as the string"),
    ("RIGHT$(RIGHT$(S$,4),2)", "nested"),
    ("MID$(S$)", "no position"),
    ("MID$()", "no argument"),
    ("MID$(S$,1,1,1)", "an extra argument"),
    ("MID$(5,1)", "a number as the string"),
    ('MID$(S$,"A")', "a string as the position"),
    ('MID$(S$,1,"A")', "a string as the count"),
    ('MID$(S$,0,"A")', "the position's range before the count's type"),
    ("MID$(5,0)", "the type before the position's range"),
    ('MID$(S$,70000,"A")', "the position's overflow before the count's type"),
    ("MID$(S$,1/0)", "the position's own error"),
    ("MID$(S$,1,1/0)", "the count's own error"),
    ("MID$(S$,0,1/0)", "the position's range before the count's own error"),
    ("MID$ (S$,2,2)", "a space before the parenthesis"),
    ("MID$( S$ ,2 ,2 )", "spaces around the arguments"),
    ("MID$(S$,-32769,1)", "a position below -32768"),
    ("MID$(S$+S$,4,4)", "an expression as the string"),
]

RECORD = [
    "900 V=VARPTR(R$):GOSUB 950:POKE A,E:POKE A+1,RL:POKE A+2,FB:POKE A+3,LB",
    "910 POKE A+4,S-INT(S/256)*256:POKE A+5,INT(S/256):POKE A+6,W-INT(W/256)*256:POKE A+7,INT(W/256)",
    "920 V=VARPTR(S$):GOSUB 950:POKE A+8,RL:POKE A+9,S-INT(S/256)*256:POKE A+10,INT(S/256):A=A+11:RETURN",
] + ramrec.STR_DIGEST + [ramrec.ERRLINE]
HEAD = ramrec.head(2000)
TAIL = ramrec.TAIL
_data = ramrec.data


def program(group):
    """the typed lines (numbered program + RUN) and the case list [(id, meta)] in record order"""
    if group in ("LR", "MID"):
        if group == "LR":
            ls, ps, ms = LR_L, NUMS, ["1", "2"]
            sub = ["200 ON M GOSUB 210,220:RETURN", "210 R$=LEFT$(S$,N):RETURN", "220 R$=RIGHT$(S$,N):RETURN"]
        else:
            ls, ps, ms = MID_L, MID_P, [ABSENT if m is None else m for m in MID_M]
            sub = [f"200 IF M={ABSENT}! THEN 220", "210 R$=MID$(S$,N,M):RETURN", "220 R$=MID$(S$,N):RETURN"]
        lines = [HEAD,
                 "20 READ I1:DIM LA(I1):FOR I=1 TO I1:READ LA(I):NEXT",
                 "30 READ I2:DIM PA(I2):FOR I=1 TO I2:READ PA(I):NEXT",
                 "40 READ I3:DIM MA(I3):FOR I=1 TO I3:READ MA(I):NEXT",
                 "50 FOR J1=1 TO I1:S$=\"\":IF LA(J1)>0 THEN FOR I=1 TO LA(J1):S$=S$+CHR$(I):NEXT",
                 "60 FOR J2=1 TO I2:FOR J3=1 TO I3:N=PA(J2):M=MA(J3):E=0:R$=CHR$(250)",
                 "70 GOSUB 200:GOSUB 900:NEXT J3,J2,J1",
                 "80 " + TAIL] + sub + RECORD
        lines += _data(1000, [str(len(ls))] + [str(x) for x in ls])
        lines += _data(1100, [str(len(ps))] + ps)
        lines += _data(1200, [str(len(ms))] + ms)
        cases = []
        for l in ls:
            for p in ps:
                for m in ms:
                    if group == "LR":
                        f = LR_F[int(m) - 1]
                        cases.append((f"KS LR {f} L{l} N{p}", dict(fn=f, l=l, n=float(p), ntext=p)))
                    else:
                        mm = None if m == ABSENT else m
                        cases.append((f"KS MID L{l} P{p} M{mm if mm is not None else '-'}",
                                      dict(fn="MID$", l=l, p=float(p), ptext=p,
                                           m=None if mm is None else float(mm), mtext=mm)))
        return lines + ["RUN"], cases
    lines = [HEAD, "20 S$=\"\":FOR I=1 TO 5:S$=S$+CHR$(I):NEXT"]
    cases = []
    for i, (expr, why) in enumerate(FX):
        lines.append(f"{100 + i} E=0:R$=CHR$(250):R$={expr}:GOSUB 900")
        cases.append((f"KS FX {i}", dict(fn=expr.split("(")[0].strip(), expr=expr, why=why)))
    lines += [f"{100 + len(FX)} " + TAIL] + RECORD
    return lines + ["RUN"], cases


GAPS = {"LR": 2000.0, "MID": 5000.0, "FX": 60.0}


def measure(group):
    lines, cases = program(group)
    return lines, cases, ramrec.measure(lines, len(cases), REC, GAPS[group])


def decode(hexs, n):
    rs, why = ramrec.frame(hexs, n, REC)
    if rs is None:
        return None, why
    recs = []
    for r in rs:
        recs.append(dict(e=r[0], rl=r[1], fb=r[2], lb=r[3], s=r[4] | r[5] << 8, w=r[6] | r[7] << 8, sl=r[8],
                         ss=r[9] | r[10] << 8))
    return recs, None


def load(group, run=RUN):
    """the cases of one group from the committed run file: {"ref": [...], "zb": [...]} (rules modules use this)"""
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
    groups = [g for g in ("LR", "MID", "FX") if g in argv] or ["LR", "MID", "FX"]
    path = os.path.join(ROOT, "scratchpad", RUN)
    if "--out" in argv:
        path = os.path.join(ROOT, argv[argv.index("--out") + 1])
    text = open(path).read() if os.path.exists(path) else ""
    for g in groups:
        lines, cases, cap = measure(g)
        bad = []
        for who in ("ref", "zb"):
            recs, why = decode(cap[who], len(cases))
            if recs is None:
                bad.append(f"{who}: {why}")
        text = ramrec.write_section(text, g, cap, len(cases), bad)
        print(f"{g}: {len(cases)} cases; {'; '.join(bad) or 'both complete'}", flush=True)
        if not bad:
            ref, zb = (decode(cap[w], len(cases))[0] for w in ("ref", "zb"))
            diff = [cases[i][0] for i in range(len(cases)) if ref[i] != zb[i]]
            print(f"  {len(diff)} cases differ" + (": " + ", ".join(diff[:12]) if diff else ""), flush=True)
    open(path, "w").write(text)
    print(f"wrote {os.path.relpath(path, ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
