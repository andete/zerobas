#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""KDEFTYPE -- the measured cases behind docs/keywords/DEFINT.md, DEFSNG.md, DEFDBL.md and DEFSTR.md: the errors
region's first keyword probe (D-KWSPEC; docs/keywords/spec-plan.md §2 region 6; docs/spec-method.md §3a). The run file
is the shared RAM-record harness's (probes/basic/spec/ramrec.py); the frame is kgosub.py's.

Clean room: typed BASIC in, RAM out. No reference ROM byte is read; the record area ends below $F380 (asserted).

EACH CASE IS A BLOCK OF 30 LINES from its base n: line n starts from nothing (`CLEAR`, `ON ERROR` set again), runs
the statement(s) under test and ends `GOTO n+25`; the case's own extra lines sit at n+5 .. n+20 (`{L5}` ..); n+25
records. A case may leave a number in WV#. RESUME NEXT carries on after an error; the FIRST and the LAST error are
both kept. EVERY PROBE VARIABLE CARRIES A SUFFIX (WE% WF% WX% WK% WA! WV#): a case's `DEFSTR A-Z` must not retype the
probe's own bookkeeping (a suffix always wins).

A VARIABLE'S TYPE is the byte before its name, PEEK(VARPTR(v)-3): 2 integer, 3 string, 4 single, 8 double. $EE: VARPTR
refused the name (error 5: the variable does not exist -- reading a name does not create it); 0: no name to read.

THE RECORD (13 bytes per case, from $C001):
  0     E   the FIRST error (0: none)
  1     F   the LAST error
  2-4   T   the types of the case's (up to) three named variables
  5-12  V   WV#'s eight bytes (ramrec.number); WV# starts at -77, so a value the case never wrote reads -77
  13    Z   the case's own index (WZ%), set at the END of its own line (after the case's statements -- a CLEAR in
            them would wipe it): a line the machine refused when it was TYPED (the first run's `A=1E63`) leaves the
            previous case's index here

THE GROUP (case ids "KDT FX <i>"): FX, every case of DEFINT, DEFSNG, DEFDBL and DEFSTR.

    python3 probes/basic/spec/kdeftype.py [--out scratchpad/KDT_run1.out]"""
import os
import sys
from types import SimpleNamespace as NS

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, HERE)
import ramrec  # noqa: E402

REC = 14
RUN = "KDT_run1.out"
GAPS = {"FX": 4000.0, "FY": 4000.0}
SENTINEL = -77                 # WV# before the case: a value the case did not write reads as this

# (keyword, line n's statements, {offset: the line's statements}, the names whose type is read, what it separates)
FX = [
    # no DEF at all
    ("DEFDBL", "A=1/3:WV#=A", {}, "A", "no DEF: an unsuffixed name is double"),
    ("DEFDBL", "DEFSNG A:DEFDBL A:A=1/3:WV#=A", {}, "A", "DEFDBL after DEFSNG"),
    ("DEFDBL", "DEFINT A-Z:DEFDBL A-Z:B=1.7:WV#=B", {}, "B", "DEFDBL A-Z undoes DEFINT A-Z"),
    # DEFINT
    ("DEFINT", "DEFINT A:A=1.7:WV#=A", {}, "A", "DEFINT: the fraction is lost"),
    ("DEFINT", "DEFINT A:A=-1.7:WV#=A", {}, "A", "DEFINT: a negative fraction (truncate or floor)"),
    ("DEFINT", "DEFINT A:A=2.5:WV#=A", {}, "A", "DEFINT: a half"),
    ("DEFINT", "DEFINT A-C:B=1.7:WV#=B", {}, "ABD", "a range covers the letters inside it"),
    ("DEFINT", "DEFINT A,C:B=1.7:C=1.7:WV#=B", {}, "ABC", "a list covers only its letters"),
    ("DEFINT", "DEFINT A-C,X-Z:Y=1.7:D=1.7:WV#=Y", {}, "YD", "two ranges"),
    ("DEFINT", "DEFINT A-A:A=1.7:WV#=A", {}, "A", "a one-letter range"),
    ("DEFINT", "DEFINT A:A#=1.5:A!=2.5:WV#=A#", {}, "A", "a suffix wins over DEF"),
    ("DEFINT", "A=7:DEFINT A:WV#=A", {}, "A", "the type is looked up at each use: the double A is not the int A"),
    ("DEFINT", "A=7:DEFINT A:A=3:DEFDBL A:WV#=A", {}, "A", "two A's side by side: back to the double one"),
    ("DEFINT", "DEFINT A:DEFDBL A:A=1.7:WV#=A", {}, "A", "the last DEF for a letter wins"),
    ("DEFINT", "DEFINT I:FOR I=1 TO 3:NEXT:WV#=I", {}, "I", "a FOR variable follows DEF"),
    ("DEFINT", "DEFINT A:RESTORE {L5}:READ A:WV#=A", {5: "DATA 2.6"}, "A", "a READ variable follows DEF"),
    ("DEFINT", "DEFINT A:A=40000", {}, "A", "an integer out of range"),
    ("DEFINT", "DEFINT A:A=-32768:WV#=A", {}, "A", "the lowest integer"),
    ("DEFINT", "DEFINT A:DIM A(2):A(1)=1.7:WV#=A(1)", {}, "", "an array follows DEF"),
    ("DEFINT", "DIM A(2):DEFINT A:A(1)=1.7:WV#=A(1)", {}, "", "an array dimensioned before DEF"),
    ("DEFINT", "defint a:a=1.7:WV#=A", {}, "A", "lower case"),
    ("DEFINT", "DEFINT A:CLEAR 300,&HBF00:A=1.7:WV#=A", {}, "A", "CLEAR undoes DEF"),
    ("DEFINT", "DEFINT A:WV#=A+0.5", {}, "A", "an int name read before it exists"),
    ("DEFINT", "DEFINT 5", {}, "", "not a letter"),
    ("DEFINT", "DEFINT A-", {}, "", "a range without its end"),
    ("DEFINT", "DEFINT A-1", {}, "", "a range ending in a digit"),
    ("DEFINT", "DEFINT Z-A:Z=1.7:WV#=Z", {}, "Z", "a reversed range"),
    ("DEFINT", "DEFINT", {}, "", "nothing to declare"),
    ("DEFINT", "DEFINT AB", {}, "", "two letters glued"),
    ("DEFINT", "DEFINT AC=7", {}, "C", "a letter, then an assignment glued on"),
    ("DEFINT", "DEFINT A B", {}, "", "two letters with a space"),
    ("DEFINT", "DEFINT A,", {}, "", "a trailing comma"),
    ("DEFINT", "DEFINT A-B-C", {}, "", "a range of three"),
    ("DEFINT", "DEFINT A$", {}, "", "a suffix in the list"),
    ("DEFINT", "DEFINT A:B=1.7:WV#=B", {}, "AB", "a letter DEF does not name stays double"),
    # DEFSNG
    ("DEFSNG", "DEFSNG A:A=1/3:WV#=A", {}, "A", "DEFSNG: six digits"),
    ("DEFSNG", "DEFSNG A:A=1.23456789:WV#=A", {}, "A", "DEFSNG rounds the seventh digit"),
    ("DEFSNG", "DEFSNG A:A=1.2345649:WV#=A", {}, "A", "DEFSNG below the half"),
    # 1E63 is Overflow when the LINE IS TYPED (it is never stored; the first run read the previous case's record)
    ("DEFSNG", "DEFSNG A:A=9.99999E62:WV#=A", {}, "A", "a single at the top of the range"),
    ("DEFSNG", "DEFSNG A-Z:B=1/3:WV#=B#", {}, "B", "DEFSNG A-Z; a double read through another suffix"),
    # DEFSTR
    ("DEFSTR", 'DEFSTR A:A="XY":WV#=LEN(A)', {}, "A", "DEFSTR: a string without $"),
    ("DEFSTR", "DEFSTR A:A=1", {}, "A", "a number into a DEFSTR name"),
    ("DEFSTR", "DEFSTR A:WV#=LEN(A)", {}, "A", "a DEFSTR name read before it exists"),
    ("DEFSTR", 'DEFSTR A:A$="Q":WV#=LEN(A)', {}, "A", "A and A$ are the same variable"),
    ("DEFSTR", 'DEFSTR A-Z:B="XYZ":WV#=LEN(B)', {}, "B", "DEFSTR A-Z"),
    ("DEFSTR", "DEFSTR A:A=1/3", {}, "A", "an expression into a DEFSTR name"),
    ("DEFSTR", 'DEFINT A:DEFSTR A:A="Z":WV#=ASC(A)', {}, "A", "DEFSTR after DEFINT"),
    ("DEFSTR", 'DEFSTR S:S=STR$(5):WV#=LEN(S)', {}, "S", "a string function into a DEFSTR name"),
    ("DEFSTR", "DEFSTR A:DIM A(2):A(1)=\"KL\":WV#=LEN(A(1))", {}, "", "a DEFSTR array"),
    ("DEFSTR", "DEFSTR 1", {}, "", "DEFSTR: not a letter"),
    ("DEFSNG", "DEFSNG Z-A", {}, "", "DEFSNG: a reversed range"),
    ("DEFDBL", "DEFDBL", {}, "", "DEFDBL: nothing to declare"),
    # added after the first run: how much of a list stands before a bad item, and where spaces may go
    ("DEFINT", "DEFINT A,5:A=1.7:WV#=A", {}, "A", "a bad item after a good one"),
    ("DEFINT", "DEFINT A-C,Z-A:B=1.7:WV#=B", {}, "B", "a bad range after a good one"),
    ("DEFINT", "DEFINT A - C:B=1.7:WV#=B", {}, "B", "spaces around the dash"),
    ("DEFINT", "DEFINT A ,B:B=1.7:WV#=B", {}, "B", "a space before the comma"),
    ("DEFINT", "DEFINT AB:A=1.7:WV#=A", {}, "A", "is the item before a glued letter applied"),
    ("DEFINT", "DEFINT A-CD:B=1.7:WV#=B", {}, "B", "is a range before a glued letter applied"),
]

# GROUP FY -- goldfish pass 1 (scratchpad/REVIEW-m2-gkwdeft.md): the cases that separate the rules' rivals
FY = [
    ("DEFINT", "DEFINT A:A=32767.9:WV#=A", {}, "A", "the cut before the range test (32767.9)"),
    ("DEFINT", "DEFINT A:A=32768", {}, "A", "32768"),
    ("DEFINT", "DEFINT A:A=-32768.5:WV#=A", {}, "A", "the cut before the range test (-32768.5)"),
    ("DEFINT", "DEFINT A:A=-32769", {}, "A", "-32769"),
    ("DEFINT", "DEFINT A:A=40000:WV#=A+.5", {}, "A", "a new variable after an error holds 0"),
    ("DEFINT", "DEFINT A:A=5:A=40000:WV#=A", {}, "A", "an existing variable after an error keeps its value"),
    ("DEFINT", "DEFINT A:AB=1.7:BA=1.7:WV#=AB+BA", {}, "", "a longer name follows its first letter"),
    ("DEFINT", "DEFINT A:ABC=1:ABD=2:WV#=ABC", {}, "", "two significant characters"),
    ("DEFINT", "DEFINT A:A%=5:WV#=A", {}, "A", "A and A% are one variable after DEFINT A"),
    ("DEFSNG", "DEFSNG A:A!=2.5:WV#=A", {}, "A", "A and A! are one variable after DEFSNG A"),
    ("DEFDBL", "A#=1/3:WV#=A", {}, "A", "A and A# are one variable with no DEF"),
    ("DEFINT", "DEFINT A-:A=1.7:WV#=A", {}, "A", "the start of an unfinished range"),
    ("DEFINT", "DEFINT A B:A=1.7:WV#=A", {}, "A", "the item before a space and a letter"),
    ("DEFINT", "DEFINT A,:A=1.7:WV#=A", {}, "A", "the item before a trailing comma"),
    ("DEFINT", "DEFINT A$:A=1.7:WV#=A", {}, "A", "the letter before a suffix"),
    ("DEFINT", "DEFINT A-B-C:B=1.7:WV#=B", {}, "B", "the range before a second dash"),
    ("DEFINT", "DEFINT A, B:B=1.7:WV#=B", {}, "B", "a space after the comma"),
    ("DEFINT", "DEFINT A :A=1.7:WV#=A", {}, "A", "a space before the colon"),
    ("DEFSTR", 'DEFSTR A,5:A="X":WV#=LEN(A)', {}, "A", "DEFSTR: a bad item after a good one"),
    ("DEFSNG", "DEFSNG AB:A=1/3:WV#=A", {}, "A", "DEFSNG: a glued letter"),
    ("DEFDBL", "DEFINT A:DEFDBL A-:A=1.7:WV#=A", {}, "A", "DEFDBL: an unfinished range"),
    ("DEFDBL", "DEFINT A-Z:DEFDBL A-C,Z-A:B=1/3:WV#=B", {}, "B", "DEFDBL: a reversed range after a good one"),
    ("DEFINT", "DEFINT I:FOR I=1.7 TO 3:NEXT:WV#=I", {}, "I", "a FOR start is cut"),
    ("DEFSNG", 'DEFSNG A:A="X"', {}, "A", "DEFSNG: a string into the name"),
    ("DEFSNG", "DEFSNG A:A=9.9999999E62", {}, "A", "DEFSNG: rounding past the top of the range"),
    ("DEFSNG", "DEFSNG A:A=1.234565:WV#=A", {}, "A", "DEFSNG: an exact half"),
    ("DEFINT", "DIM A(2):A(1)=1.7:DEFINT A:WV#=A(1)", {}, "", "a new type names a new array"),
    ("DEFINT", "DIM A(2):A(1)=1.7:DEFINT A:A(1)=3:DEFDBL A:WV#=A(1)", {}, "", "back to the first array"),
    ("DEFINT", "DIM A(2):DEFINT A:DIM A(2)", {}, "", "DIM after a new type is no error"),
    ("DEFINT", "DEFINT X:DEF FNB(X)=X:WV#=FNB(1.7)", {}, "", "a DEF FN parameter follows DEF"),
    ("DEFINT", "DEFINT A:DEF FNA(X)=X/2:WV#=FNA(3)", {}, "", "a DEF FN name follows DEF"),
    ("DEFINT", "DEFINT A-Z:CLEAR:Z=1.7:WV#=Z", {}, "Z", "CLEAR puts every letter back"),
    ("DEFINT", "DEFINT A:A=1/0", {}, "A", "the variable is made before its value is worked out"),
]
GROUPS = {"FX": FX, "FY": FY}


def _read(name, o):
    # T := $EE first: VARPTR of a variable that does not exist is error 5; the record line's handler (900) sets WX%
    # and a false IF skips the rest of the line, so the $EE stays (kfor.py's frame).
    return f"WX%=0:POKE {o},238:WA!=VARPTR({name}):IF WX%=0 THEN POKE {o},PEEK(WA!-3)"


def program(group="FX"):
    lines = ["10 CLEAR 300,&HBF00:POKE &HC000,0:GOTO 2000", "800 IF WE%=0 THEN WE%=ERR", "810 WF%=ERR:RESUME NEXT",
             "900 WX%=1:RESUME NEXT"]
    cases = []
    n = 2000
    for i, (kw, main, subs, names, why) in enumerate(GROUPS[group]):
        base = 0xC001 + REC * i
        m = {f"L{k}": n + k for k in (5, 10, 15, 20)}
        lines.append(f"{n} CLEAR 300,&HBF00:ON ERROR GOTO 800:WE%=0:WF%=0:WV#={SENTINEL}:" + main.format(**m) + f":WZ%={i}" + f":GOTO {n + 25}")
        for k, t in sorted(subs.items()):
            lines.append(f"{n + k} {t.format(**m)}")
        rec = n + 25
        lines.append(f"{rec} ON ERROR GOTO 900:POKE {base},WE%:POKE {base + 1},WF%:POKE {base + 2},0:"
                     f"POKE {base + 3},0:POKE {base + 4},0:WA!=VARPTR(WV#):"
                     f"FOR WK%=0 TO 7:POKE {base + 5}+WK%,PEEK(WA!+WK%):NEXT:POKE {base + 13},WZ%")
        for j, v in enumerate(names):
            lines.append(f"{rec + 1 + j} " + _read(v, base + 2 + j))
        cases.append((f"KDT {group} {i}", dict(kw=kw, stmt=main, subs=subs, names=names, why=why, idx=i)))
        n += 30
    lines.append(f"{n} ON ERROR GOTO 0:POKE &HC001+{REC * len(cases)},&HC3:POKE &HC000,&H5A:END")
    # the typed program must fit below HIMEM: as TEXT, 18.3 K (this probe's first FX) and 19.7 K (FX with the Z byte)
    # ran; 27.6 K (kfor.py, unrolled) stopped both machines while it was typed. Between them, the line is drawn here.
    assert sum(len(t) + 1 for t in lines) < 21000, "the program outgrows the RAM below &HBF00: split the group"
    assert 1 + REC * len(cases) + 1 <= 0xF380 - ramrec.BASE
    return lines + ["RUN"], cases


def decode(hexs, n):
    rs, why = ramrec.frame(hexs, n, REC)
    if rs is None:
        return None, why
    return [dict(e=r[0], f=r[1], t=list(r[2:5]), v=ramrec.number(bytes(r[5:13])), z=r[13]) for r in rs], None


def load(group=None, run=RUN):
    """the cases of one group, or (group None) of every group, in GROUPS' order"""
    if group is None:
        parts = [load(g, run) for g in GROUPS]
        return {who: [c for p in parts for c in p[who]] for who in ("ref", "zb")}
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
    path = os.path.join(ROOT, "scratchpad", RUN)
    groups = [g for g in GROUPS if g in argv] or list(GROUPS)
    if "--lines" in argv:
        print("\n".join(program(groups[0])[0]))
        return 0
    for group in groups:
        lines, cases = program(group)
        cap = ramrec.measure(lines, len(cases), REC, GAPS[group])
        bad = []
        for who in ("ref", "zb"):
            recs, why = decode(cap[who], len(cases))
            if recs is None:
                bad.append(f"{who}: {why}")
        text = open(path).read() if os.path.exists(path) else ""
        open(path, "w").write(ramrec.write_section(text, group, cap, len(cases), bad))
        print(f"{group}: {len(cases)} cases; {'; '.join(bad) or 'both complete'}", flush=True)
        if not bad:
            ref, zb = (decode(cap[w], len(cases))[0] for w in ("ref", "zb"))
            for i, (a, b) in enumerate(zip(ref, zb)):
                mark = "" if a == b else "  <<"
                ran = "" if a["z"] == i else f"  🔴 RAN? z={a['z']}"
                print(f"{i:2d} {cases[i][1]['why'][:48]:48s} ref e{a['e']} f{a['f']} t{a['t']} v{float(a['v']):.10g}"
                      f"{ran}" + (f"\n{'':51s}zb  e{b['e']} f{b['f']} t{b['t']} v{float(b['v']):.10g}{mark}"
                                  if mark else ""))
    print(f"wrote {os.path.relpath(path, ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
