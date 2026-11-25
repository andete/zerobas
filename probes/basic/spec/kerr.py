#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""KERR -- the measured cases behind docs/keywords/ERROR.md, ERR.md, ERL.md and RESUME.md (with ON ERROR GOTO's
handler mechanics): the errors region's second keyword probe (D-KWSPEC; docs/keywords/spec-plan.md §2 region 6;
docs/spec-method.md §3a).

A RAM-record probe cannot hold these: its own frame catches every error with ON ERROR / RESUME NEXT -- the keywords
under test. So this probe reads the SCREEN, as kstop.py does (its normalisation, its machines): each case is a fresh
`NEW` / `CLS`, a short program typed, then the commands the case names. A case's output is tagged `[...]` or is a
number PRINTed on its own.

Clean room: typed BASIC in, the text screen out. No reference ROM byte is read.

    python3 probes/basic/spec/kerr.py [FX]"""
import json
import os
import sys
from types import SimpleNamespace as NS

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import kstop  # noqa: E402
import omsx_repl  # noqa: E402

RUN = "KER_run1.out"
MACHINES = kstop.MACHINES
H = "10 ON ERROR GOTO 100"

# (keyword, the typed lines after NEW / CLS, what it separates)
FX = [
    # ERROR
    ("ERROR", ["10 ERROR 11", "RUN"], "ERROR n in a program"),
    ("ERROR", ["ERROR 11"], "ERROR n typed"),
    ("ERROR", ["10 ERROR 200", "RUN"], "a code with no message"),
    ("ERROR", ["10 ERROR 0", "RUN"], "ERROR 0"),
    ("ERROR", ["10 ERROR 256", "RUN"], "ERROR 256"),
    ("ERROR", ["10 ERROR 1.7", "RUN"], "a fractional code"),
    ("ERROR", ['10 ERROR "A"', "RUN"], "a string code"),
    ("ERROR", ["10 ERROR", "RUN"], "no code"),
    ("ERROR", ["10 ERROR 70000", "RUN"], "a code past 65535"),
    ("ERROR", ["10 ERROR 1,1", "RUN"], "a comma after the code"),
    ("ERROR", [H, "20 ERROR 200", '100 PRINT "[";ERR;ERL;"]":END', "RUN"], "a handler sees ERROR's code"),
    ("ERROR", [H, "20 END", '100 PRINT "[";ERR;ERL;"]":END', "RUN", "ERROR 7"], "a typed ERROR reaches the handler"),
    # ERR / ERL
    ("ERR", [H, "20 X=1/0", "30 END", '100 PRINT "[";ERR;ERL;"]":RESUME NEXT', "RUN"], "ERR and ERL in a handler"),
    ("ERR", ["10 X=1/0", "RUN", "PRINT ERR;ERL"], "ERR and ERL after an untrapped error"),
    ("ERR", ["PRINT ERR;ERL"], "ERR and ERL before any error"),
    ("ERR", [H, "20 X=1/0", '30 PRINT "[";ERR;ERL;"]":END', "100 RESUME NEXT", "RUN"], "RESUME NEXT: ERR 0, ERL kept"),
    ("ERL", ["PRINT 1/0", "PRINT ERR;ERL"], "an error typed at the prompt"),
    ("ERL", ["10 X=1/0", "RUN", "PRINT 1/0", "PRINT ERR;ERL"], "a typed error after a program's"),
    ("ERR", ["10 A=ERR 1", "RUN"], "something after ERR"),
    # RESUME
    ("RESUME", [H, "20 D=0", '30 X=1/D:PRINT "[";X;"]":END', "100 D=1:RESUME", "RUN"], "RESUME runs the statement again"),
    ("RESUME", [H, "20 D=0", '30 X=1/D:PRINT "[";X;"]":END', "100 D=1:RESUME 0", "RUN"], "RESUME 0 is RESUME"),
    ("RESUME", [H, '20 X=1/0:PRINT "[B]"', '30 PRINT "[C]":END', "100 RESUME NEXT", "RUN"], "RESUME NEXT, same line"),
    ("RESUME", [H, "20 X=1/0", '30 PRINT "[C]":END', "100 RESUME NEXT", "RUN"], "RESUME NEXT, the next line"),
    ("RESUME", [H, '20 PRINT ":";1/0:PRINT "[B]":END', "100 RESUME NEXT", "RUN"], "RESUME NEXT and a colon in a string"),
    ("RESUME", [H, "20 X=1/0", '30 PRINT "[C]"', '40 PRINT "[D]":END', "100 RESUME 40", "RUN"], "RESUME n"),
    ("RESUME", [H, "20 X=1/0", "100 RESUME 99", "RUN"], "RESUME to a missing line"),
    ("RESUME", ["10 RESUME", "RUN"], "RESUME with no error"),
    ("RESUME", [H, "20 X=1/0", '30 PRINT "[C]"', '100 PRINT "[H]"', "RUN"], "a handler running off the end"),
    ("RESUME", [H, "20 X=1/0", '30 PRINT "[C]"', '100 PRINT "[H]"', "RUN", "PRINT ERR;ERL"],
     "ERR and ERL after No RESUME"),
    ("RESUME", [H, '20 X=1/0:PRINT "[B]":END', "100 Y=1/0:RESUME NEXT", "RUN"], "an error inside the handler"),
    ("RESUME", [H, '20 X=1/0:PRINT "[B]":END', "100 ON ERROR GOTO 0", "RUN"], "ON ERROR GOTO 0 inside the handler"),
    ("RESUME", ["10 ON ERROR GOTO 999", '20 PRINT "[B]"', "RUN"], "ON ERROR GOTO a missing line"),
    ("RESUME", [H, "20 ON ERROR GOTO 0", '30 X=1/0:PRINT "[B]"', '100 PRINT "[H]":RESUME NEXT', "RUN"],
     "ON ERROR GOTO 0 outside a handler disarms"),
    ("RESUME", [H, '20 X=1/0:PRINT "[B]":END', '100 PRINT "[H]":ON ERROR GOTO 200:RESUME NEXT',
                '200 PRINT "[I]":RESUME NEXT', "RUN"], "ON ERROR GOTO inside the handler re-arms"),
    ("RESUME", [H, '20 X=1/0:PRINT "[B]":END', "100 ON ERROR GOTO A", "RUN"], "ON ERROR GOTO and a variable"),
    ("RESUME", [H, "20 X=1/0:Y=1/0", '30 PRINT "[";ERR;"]":END', '100 PRINT "[H]";ERR;:RESUME NEXT', "RUN"],
     "the handler catches each error again after RESUME"),
    ("RESUME", [H, "20 END", '100 PRINT "[H]":RESUME NEXT', "RUN", "PRINT 1/0:PRINT \"[T]\""],
     "a typed error with a handler armed"),
    ("RESUME", [H, "20 X=1/0", '30 PRINT "[C]":END', '100 PRINT "[H]":RUN 30', "RUN", "RESUME"],
     "RUN inside the handler, then a typed RESUME"),
    # added after the first run (KST FY 3: after a handler ENDed, a typed RESUME is not trapped -- RESUME's own error,
    # or a disarmed handler?)
    ("RESUME", [H, "20 X=1/0", '100 PRINT "[H]":END', "RUN", 'PRINT 1/0:PRINT "[T]"'],
     "a typed error after a handler ended with END"),
    ("RESUME", [H, "20 END", '100 PRINT "[H]":END', "RUN", "RESUME"], "a typed RESUME with a handler armed"),
]

# GROUP FY -- goldfish pass 1 (scratchpad/REVIEW-m2-gkwerr.md): the cases that separate the rules' rivals
FY = [
    ("RESUME", [H, "20 X=1/0", '100 PRINT "[H]"', '110 PRINT "[I]"', "RUN", "PRINT ERR;ERL"],
     "No RESUME names the last line that ran"),
    ("RESUME", [H, '20 X=1/0:Y=1/0:PRINT "[B]":END', '100 PRINT "[H]":ON ERROR GOTO 200:RESUME NEXT',
                '200 PRINT "[I]":RESUME NEXT', "RUN"], "ON ERROR GOTO n in a handler arms n for the next error"),
    ("RESUME", [H, '20 X=1/D:PRINT "[B]":END', "100 D=1:ON ERROR GOTO 0", "RUN"], "GOTO 0 re-raises, not re-runs"),
    ("ERR", [H, "20 D=0", '30 X=1/D:PRINT "[";ERR;ERL;"]":END', "100 D=1:RESUME", "RUN"], "RESUME clears ERR"),
    ("ERR", [H, "20 X=1/0", '30 PRINT "[C]"', '40 PRINT "[";ERR;ERL;"]":END', "100 RESUME 40", "RUN"],
     "RESUME n clears ERR"),
    ("ERR", ["10 PRINT ERR;ERL", "20 X=1/0", "RUN", "RUN"], "ERR and ERL across RUN"),
    ("ERR", ["10 X=1/0", "RUN", "CLEAR", "PRINT ERR;ERL"], "ERR and ERL across CLEAR"),
    ("ERR", ["10 X=1/0", "RUN", "NEW", "PRINT ERR;ERL"], "ERR and ERL across NEW"),
    ("ERR", ["10 X=1/0", "RUN", "20 REM", "PRINT ERR;ERL"], "ERR and ERL across an edit"),
    ("RESUME", [H, "20 X=1/0", '30 PRINT "[C]"', '100 PRINT "[H]"', "RUN", "RESUME NEXT"],
     "a typed RESUME after No RESUME"),
    ("RESUME", [H, '20 X=1/0:PRINT "[B]":END', "100 Y=1/0:RESUME NEXT", "RUN", "RESUME NEXT"],
     "a typed RESUME after an error in the handler"),
    ("RESUME", [H, '20 GOSUB 50:PRINT "[R]":END', '50 X=1/0:PRINT "[S]":RETURN', "100 RESUME NEXT", "RUN"],
     "an error inside a GOSUB, RESUME NEXT, RETURN"),
    ("RESUME", [H, '20 X=1/0:PRINT "[B]"', "30 RETURN", '100 GOSUB 200:PRINT "[X]":END', "200 RESUME NEXT", "RUN"],
     "a GOSUB in the handler outlives its RESUME"),
    ("RESUME", [H, "20 X=1/0", '30 NEXT:PRINT "[N]"', "100 FOR I=1 TO 2:RESUME NEXT", "RUN"],
     "a FOR opened in the handler"),
    ("RESUME", [H, "20 FOR I=1 TO 3:X=1/0:PRINT I;:NEXT", '30 PRINT "[E]":END', "100 RESUME NEXT", "RUN"],
     "an error inside a FOR body"),
    ("RESUME", ["10 ON ERROR GOTO 30", "20 GOTO 40", "30 RESUME NEXT", "40 X=1/0", "RUN"],
     "RESUME NEXT after the program's last statement"),
    ("RESUME", [H, "20 END", '100 PRINT "[H]";:RESUME NEXT', "RUN", 'PRINT "[A]";:X=1/0'],
     "RESUME NEXT after a typed line's last statement"),
    ("RESUME", [H, "20 END", "100 D=1:RESUME", "RUN", 'D=0:PRINT 1/D:PRINT "[T]"'], "RESUME retries a typed statement"),
    ("RESUME", [H, "20 END", '30 PRINT "[C]":END', "100 RESUME 30", "RUN", 'PRINT 1/0:PRINT "[T]"'],
     "RESUME n from a typed error"),
    ("ERROR", [H, "20 END", "100 PRINT ERR;ERL;:RESUME NEXT", "RUN", 'ERROR 7:PRINT "[T]"'],
     "a typed ERROR, the handler, then the typed line goes on"),
    ("RESUME", [H, '20 X=1/0:PRINT "[B]":END', '100 RESUME NEXT:PRINT "[Z]"', "RUN"], "statements after RESUME"),
    ("RESUME", [H, '20 X=1/0:PRINT "[B]":END', "100 RESUME A", "RUN"], "RESUME and a variable"),
    ("RESUME", [H, "20 ON ERROR GOTO", "30 X=1/0", '100 PRINT "[H]":RESUME NEXT', "RUN"], "a bare ON ERROR GOTO"),
    ("RESUME", [H, "20 ON ERROR GOTO A", "30 X=1/0", '100 PRINT "[H]":RESUME NEXT', "RUN"],
     "ON ERROR GOTO A outside a handler"),
    ("ERROR", ["10 ERROR 40000", "RUN"], "ERROR 40000"),
    ("ERROR", ["10 ERROR -32769", "RUN"], "ERROR -32769"),
    ("ERROR", ["10 ERROR 300,1", "RUN"], "a code out of range, then a comma"),
    ("ERROR", [H, "20 ERROR 22", '100 PRINT "[H]";ERR:END', "RUN"], "ERROR 22 reaches the handler"),
    ("RESUME", [H, '20 X=1/0:PRINT "[B]":END', "100 ON ERROR GOTO 0", "RUN", "PRINT ERR;ERL", "CONT"],
     "after the GOTO 0 re-raise: ERR, ERL and CONT"),
]
GROUPS = {"FX": FX, "FY": FY}


def measure(group):
    got = {}
    for who, m in MACHINES:
        raw = omsx_repl.run_cases(m, [("direct", ["NEW", "CLS"] + lines) for _, lines, _ in GROUPS[group]],
                                  batch=False)
        got[who] = [kstop.normalise(r) for r in raw]
    return got


def live_copy(run_file, td):
    """tools/spec_live.py's hook (kstop.py's): zerobas's screens re-measured into a copy of the run file"""
    data = json.load(open(run_file))
    for group, cases in GROUPS.items():
        raw = omsx_repl.run_cases(MACHINES[1][1], [("direct", ["NEW", "CLS"] + lines) for _, lines, _ in cases],
                                  batch=False)
        zb = [kstop.normalise(r) for r in raw]
        if any(z is None for z in zb):
            return None
        sys.stdout.write(f"  live {os.path.basename(run_file)} {group}: zerobas "
                         f"{'as committed' if zb == data[group]['zb'] else 'CHANGED since the committed run'}\n")
        data[group]["zb"] = zb
    live = os.path.join(td, os.path.basename(run_file))
    with open(live, "w") as f:
        json.dump(data, f, indent=1)
    return live


def load(run=RUN):
    data = json.load(open(os.path.join(ROOT, "scratchpad", run)))
    out = {"ref": [], "zb": []}
    for group, cases in GROUPS.items():
        for who in ("ref", "zb"):
            out[who] += [NS(src=group, id=f"KER {group} {i}", kw=kw, lines=lines, why=why, scr=data[group][who][i])
                         for i, (kw, lines, why) in enumerate(cases)]
    return out


def main(argv):
    path = os.path.join(ROOT, "scratchpad", RUN)
    data = json.load(open(path)) if os.path.exists(path) else {}
    for group in [g for g in GROUPS if g in argv] or list(GROUPS):
        got = data[group] = measure(group)
        with open(path, "w") as f:
            json.dump(data, f, indent=1)
        cases = GROUPS[group]
        n = sum(1 for a, b in zip(got["ref"], got["zb"]) if a != b)
        print(f"{group}: {len(cases)} cases, {n} differ")
        for i, (a, b) in enumerate(zip(got["ref"], got["zb"])):
            mark = "" if a == b else "  <<"
            print(f"{i:2d} {cases[i][2][:44]:44s}{mark}\n    ref {a}\n    zb  {b}" if mark
                  else f"{i:2d} {cases[i][2][:44]:44s} {a}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
