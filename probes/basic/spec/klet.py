#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""KLET -- the measured cases behind docs/keywords/LET.md and SWAP.md: the operators region's second keyword probe,
the two assignment statements (D-KWSPEC; docs/keywords/spec-plan.md §2 region 4; docs/spec-method.md §3a). The run
file is the shared RAM-record harness's (probes/basic/spec/ramrec.py).

Clean room: typed BASIC in, RAM out. The program is TYPED on each machine; it runs every case and POKEs a record of
the outcome into RAM, which the harness reads after the program's own done flag. No reference ROM byte is read; the
record area ends below $F380 (asserted).

THE SETUP SEPARATES (spec-method §3a): every case starts from NOTHING -- its own line begins with `CLEAR` (no
variable, no array; `ON ERROR` set again) -- so "the variable did not exist yet" is a real starting state; the
statement under test is LAST on its line (RESUME NEXT after an error, even a Syntax error, continues on the next
line); the next line records ERR and up to two variables the case names, read through VARPTR AFTER the case (reading
a variable that the case did not create creates it, holding 0 or "" -- the rules say which cases that is). The
probe's own variables all start with W (WE, WV, WK, WP, WL, WX), so no case's variable shares their first two
characters.

THE RECORD (19 bytes per case, from $C001):
  0 E        ERR after the case's statement (0: none)
  1 T1       the first variable's type: 2 / 4 / 8 (a number: VARPTR's bytes follow), 3 (a string: its length, then
             its first 7 bytes); 0: none
  2-9        its bytes
  10 T2      the second variable's, the same way
  11-18      its bytes

THE GROUP (case ids "KLT FX <i>"): FX, every case of LET and SWAP.

    python3 probes/basic/spec/klet.py [--out scratchpad/KLT_run1.out]"""
import os
import sys
from types import SimpleNamespace as NS

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, HERE)
import ramrec  # noqa: E402

REC = 19
RUN = "KLT_run1.out"
GAPS = {"FX": 4000.0}
ORDER = ["FX"]

# (keyword, statement(s) -- the one under test last --, what it separates, the variables to read)
FX = [
    ("LET", "A%=1.7", "a single into an integer", ["A%"]),
    ("LET", "A%=-1.7", "a negative single into an integer", ["A%"]),
    ("LET", "A%=2.5", "2.5 into an integer", ["A%"]),
    ("LET", "A%=32767.9", "32767.9 into an integer", ["A%"]),
    ("LET", "A%=-32768.9", "-32768.9 into an integer", ["A%"]),
    ("LET", "A%=32768", "32768 into an integer", ["A%"]),
    ("LET", "A!=1234567", "1234567 into a single", ["A!"]),
    ("LET", "A!=1.2345649999999#", "a double just below a tie into a single", ["A!"]),
    ("LET", "A!=1.234565#", "a tie into a single", ["A!"]),
    ("LET", "A!=-1.234565#", "a negative tie into a single", ["A!"]),
    ("LET", "A#=1.5!", "a single into a double", ["A#"]),
    ("LET", "A#=1/3", "a double expression into a double", ["A#"]),
    ("LET", "A=7%", "an integer into a plain (double) name", ["A"]),
    ("LET", "LET A=5", "LET written out", ["A"]),
    ("LET", "ZQ9=5:ZQ7=ZQ7+1", "two names with the same first two characters", ["ZQ9", "ZQ7"]),
    ("LET", "DEFINT D:D=2.7", "DEFINT decides a plain name's type", ["D=2"]),
    ("LET", 'A$="AB":A$=A$+"C"', "a string", ["A$"]),
    ("LET", 'LET A="X"', "a string into a number (A new)", ["A"]),
    ("LET", "A$=5", "a number into a string (A$ new)", ["A$"]),
    ("LET", "A=3:A=1/0", "the right side's own error (A kept)", ["A"]),
    ("LET", "B=1/0", "the right side's own error (B new)", ["B"]),
    ("LET", "Q$(0)=1", "a number into a string array element", ["Q$(0)"]),
    ("LET", "LET 5=1", "a number as the target", []),
    ("LET", 'LET "A"=1', "a string as the target", []),
    ("LET", "LET TIME=5", "TIME as LET's target", []),
    ("LET", "LET", "LET alone", []),
    ("LET", "LET A", "no `=`", []),
    ("SWAP", "A=1:B=2:SWAP A,B", "two doubles", ["A", "B"]),
    ("SWAP", "A%=1:B%=-2:SWAP A%,B%", "two integers", ["A%", "B%"]),
    ("SWAP", "A!=1.5:B!=-2.5:SWAP A!,B!", "two singles", ["A!", "B!"]),
    ("SWAP", 'A$="X":B$="YZ":SWAP A$,B$', "two strings", ["A$", "B$"]),
    ("SWAP", "A=1:SWAP A,A", "a variable with itself", ["A"]),
    ("SWAP", "A%=1:B!=2.5:SWAP A%,B!", "integer and single", ["A%", "B!"]),
    ("SWAP", "A!=1:B#=2:SWAP A!,B#", "single and double", ["A!", "B#"]),
    ("SWAP", "A%=1:B=2:SWAP A%,B", "integer and a plain (double) name", ["A%", "B"]),
    ("SWAP", 'A=1:B$="X":SWAP A,B$', "a number and a string", ["A", "B$"]),
    ("SWAP", "DEFINT C:C=1:D=2:SWAP C,D", "DEFINT makes C an integer, D a double", ["C=2", "D"]),
    ("SWAP", "B=1:SWAP A,B", "the first variable new", ["A", "B"]),
    ("SWAP", "A=1:SWAP A,B", "the second variable new", ["A", "B"]),
    ("SWAP", "A=1:SWAP A,Q(0)", "an array never DIMmed", ["A", "Q(0)"]),
    ("SWAP", "DIM Q(2):Q(1)=5:A=1:SWAP A,Q(1)", "an array element", ["A", "Q(1)"]),
    ("SWAP", 'Q$(0)="P":Q$(1)="QR":SWAP Q$(0),Q$(1)', "string array elements", ["Q$(0)", "Q$(1)"]),
    ("SWAP", "DIM Q(2):A=1:SWAP A,Q(9)", "a subscript out of range", ["A"]),
    ("SWAP", "SWAP", "SWAP alone", []),
    ("SWAP", "A=1:SWAP A", "one variable", ["A"]),
    ("SWAP", "A=1:SWAP A,1", "a number as the second", ["A"]),
    ("SWAP", "A=1:SWAP 1,A", "a number as the first", ["A"]),
    ("SWAP", "A=1:B=2:SWAP A,B+0", "an expression as the second", ["A", "B"]),
    ("SWAP", "A=1:B=2:SWAP (A),B", "a parenthesis", ["A", "B"]),
    ("SWAP", "A=1:B=2:SWAP A,B,C", "a third variable", ["A", "B"]),
    ("SWAP", "A=1:SWAP A,B,C", "a third, the second new", ["A", "B"]),
    ("SWAP", "SWAP A,B$", "a type mismatch, both new", ["A", "B$"]),
    ("SWAP", 'A$="AB":B$=STRING$(20,"X"):SWAP A$,B$:C$=STRING$(50,"Y")', "strings after a later allocation",
     ["A$", "B$"]),
    ("SWAP", 'Q$(0)="P":Q$(1)="QR"', "string array elements, no SWAP (apparatus)", ["Q$(0)", "Q$(1)"]),
    ("SWAP", 'Q$(0)="P":Q$(1)="QR":SWAP Q$(1),Q$(0)', "string array elements, the other order", ["Q$(0)", "Q$(1)"]),
    ("SWAP", "A=1:B=2:SWAP A,B-0", "an expression as the second, minus", ["A", "B"]),
    ("SWAP", "A=1:B=2:SWAP A,B*1", "an expression as the second, times", ["A", "B"]),
]


def _read(slot, name, base):
    """BASIC that POKEs variable `name`'s type and bytes into the record's slot (1 or 2)"""
    o = base + (1 if slot == 1 else 10)
    if name.split("(")[0].endswith("$"):
        return (f"WV=VARPTR({name}):WL=PEEK(WV):WP=PEEK(WV+1)+256*PEEK(WV+2):POKE {o},3:POKE {o + 1},WL:"
                f"FOR WK=0 TO 6:WX=0:IF WK<WL THEN WX=PEEK(WP+WK)\n"
                f"POKE {o + 2}+WK,WX:NEXT")
    if "=" in name:                      # "D=2": a plain name whose type a DEFINT made an integer
        name, nb = name.split("=")[0], 2
    else:                                # a suffix says it; a plain name is a double (no DEF in force)
        nb = {"%": 2, "!": 4, "#": 8}.get(name.split("(")[0][-1], 8)
    return f"WV=VARPTR({name}):POKE {o},{nb}:FOR WK=0 TO {nb - 1}:POKE {o + 1}+WK,PEEK(WV+WK):NEXT"


def program(group="FX"):
    lines = ["10 CLEAR 300,&HBF00:POKE &HC000,0:GOTO 2000", "800 WE=ERR:RESUME NEXT"]
    cases = []
    n = 2000
    for i, (kw, stmt, why, reads) in enumerate(FX):
        base = 0xC001 + REC * i
        # every W variable exists BEFORE the case: a variable created later moves the arrays, and an array
        # element's VARPTR taken before that would then point at stale bytes (measured 2026-11-24: both machines)
        lines.append(f"{n} CLEAR 300,&HBF00:ON ERROR GOTO 800:WE=0:WV=0:WL=0:WP=0:WK=0:WX=0:{stmt}")
        n += 1
        lines.append(f"{n} POKE {base},WE:FOR WK=1 TO 18:POKE {base}+WK,0:NEXT")
        n += 1
        for s, name in enumerate(reads, 1):
            for part in _read(s, name, base).split("\n"):
                lines.append(f"{n} {part}")
                n += 1
        cases.append((f"KLT FX {i}", dict(kw=kw, stmt=stmt, why=why, reads=reads)))
    lines.append(f"{n} POKE &HC001+{REC * len(FX)},&HC3:POKE &HC000,&H5A:END")
    assert 1 + REC * len(cases) + 1 <= 0xF380 - ramrec.BASE
    return lines + ["RUN"], cases


def decode(hexs, n):
    rs, why = ramrec.frame(hexs, n, REC)
    if rs is None:
        return None, why
    out = []
    for r in rs:
        vs = []
        for o in (1, 10):
            t = r[o]
            if t == 3:
                vs.append(("$", bytes(r[o + 2:o + 2 + min(r[o + 1], 7)]), r[o + 1]))
            elif t in (2, 4, 8):
                vs.append(({2: "%", 4: "!", 8: "#"}[t], bytes(r[o + 1:o + 1 + t]), None))
            else:
                vs.append(None)
        out.append(dict(e=r[0], v1=vs[0], v2=vs[1]))
    return out, None


def load(group="FX", run=RUN):
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
    if "--out" in argv:
        path = os.path.join(ROOT, argv[argv.index("--out") + 1])
    lines, cases = program()
    if "--lines" in argv:
        print("\n".join(lines))
        return 0
    cap = ramrec.measure(lines, len(cases), REC, GAPS["FX"])
    bad = []
    for who in ("ref", "zb"):
        recs, why = decode(cap[who], len(cases))
        if recs is None:
            bad.append(f"{who}: {why}")
    text = open(path).read() if os.path.exists(path) else ""
    open(path, "w").write(ramrec.write_section(text, "FX", cap, len(cases), bad))
    print(f"FX: {len(cases)} cases; {'; '.join(bad) or 'both complete'}", flush=True)
    if not bad:
        ref, zb = (decode(cap[w], len(cases))[0] for w in ("ref", "zb"))
        diff = [cases[i][0] for i in range(len(cases)) if ref[i] != zb[i]]
        print(f"  {len(diff)} cases differ" + (": " + ", ".join(diff[:12]) if diff else ""), flush=True)
    print(f"wrote {os.path.relpath(path, ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
