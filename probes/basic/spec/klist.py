#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""KLIST -- the measured cases behind docs/keywords/NEW.md, LIST.md, DELETE.md and RENUM.md: the program region's
third keyword probe (D-KWSPEC; docs/keywords/spec-plan.md §2 region 7; docs/spec-method.md §3a). The program text and
the messages go to the screen, so this probe reads the SCREEN, as kstop.py ... kdim.py do (their normalisation,
machines, frame); the model is kstop_model.py's small BASIC. AUTO (it needs CTRL+STOP) and LLIST (a printer) are not
here: their pages' Open lists say so.

Clean room: typed BASIC in, the text screen out. No reference ROM byte is read.

    python3 probes/basic/spec/klist.py [FX]"""
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

RUN = "KNL_run1.out"
MACHINES = kstop.MACHINES
P4 = ['10 PRINT "A"', '20 PRINT "B"', '30 PRINT "C"', '40 PRINT "D"']
ST = ["10 A=5:STOP", "20 PRINT A", "30 REM", "RUN"]

# (keyword, the typed lines after NEW / CLS, what it separates)
FX = [
    ("NEW", ['10 PRINT "A"', "NEW", "LIST"], "NEW erases the program"),
    ("NEW", ["10 A=5", "RUN", "NEW", "PRINT A"], "NEW clears the variables"),
    ("NEW", ["10 CLEAR 500", "RUN", "NEW", 'PRINT FRE("")'], "NEW keeps the string space"),
    ("NEW", ['10 PRINT "A":NEW:PRINT "B"', '20 PRINT "C"', "RUN", "LIST"], "NEW inside a program stops it"),
    ("NEW", ['10 PRINT "A"', "NEW 1", "LIST"], "something after NEW erases nothing"),
    ("NEW", ["10 ON ERROR GOTO 90", "20 END", '90 PRINT "[H]":END', "RUN", "NEW", "PRINT 1/0"],
     "NEW switches ON ERROR off"),
    ("LIST", P4 + ["LIST 20"], "LIST n"),
    ("LIST", P4 + ["LIST 15-35"], "a range whose ends do not exist"),
    ("LIST", P4 + ["LIST 20-"], "a range open at the top"),
    ("LIST", P4 + ["LIST -30"], "a range open at the bottom"),
    ("LIST", P4 + ["LIST 30-20"], "a reversed range"),
    ("LIST", P4 + ["LIST 25"], "a line that is not there"),
    ("LIST", P4 + ["LIST 10,30"], "a comma"),
    ("LIST", P4 + ['LIST 20:PRINT "Z"'], "LIST ends the line"),
    ("LIST", ST + ["LIST 20", "CONT"], "LIST keeps the variables and CONT"),
    ("LIST", P4 + ["LIST 20", "LIST ."], "LIST . after a LIST"),
    ("LIST", ["10 A=0.5:B=1.5D3:C=0.123456789", "LIST"], "numbers listed in the machine's spelling"),
    ("LIST", ["10 LIST 20", '20 PRINT "B"', "RUN"], "LIST inside a program stops it"),
    ("LIST", ["LIST"], "LIST with no program"),
    ("DELETE", P4 + ["DELETE 20", "LIST"], "DELETE n"),
    ("DELETE", P4 + ["DELETE 15-30", "LIST"], "a low end that does not exist"),
    ("DELETE", P4 + ["DELETE 20-35", "LIST"], "a high end that does not exist"),
    ("DELETE", P4 + ["DELETE -30", "LIST"], "a range open at the bottom"),
    ("DELETE", P4 + ["DELETE 20-", "LIST"], "a range open at the top"),
    ("DELETE", P4 + ["DELETE", "LIST"], "DELETE alone"),
    ("DELETE", P4 + ["DELETE 30-20", "LIST"], "a reversed range"),
    ("DELETE", P4 + ["DELETE 10,30", "LIST"], "a comma"),
    ("DELETE", ST + ["DELETE 30", "CONT"], "DELETE is an edit: no CONT"),
    ("DELETE", ST + ["DELETE 30", "PRINT A"], "DELETE is an edit: the variables go"),
    ("DELETE", P4 + ['DELETE 20:PRINT "Z"', "LIST"], "DELETE ends the line"),
    ("RENUM", ["5 GOTO 9", '7 PRINT "X"', '9 PRINT "Y"', "RENUM", "LIST"], "RENUM"),
    ("RENUM", ["5 GOTO 9", '7 PRINT "X"', '9 PRINT "Y"', "RENUM 100", "LIST"], "RENUM n"),
    ("RENUM", ['10 PRINT "A"', '20 PRINT "B"', "30 GOTO 20", "RENUM 100,20", "LIST"], "RENUM n,old"),
    ("RENUM", ['5 PRINT "A"', '7 PRINT "B"', "RENUM ,,5", "LIST"], "RENUM ,,inc starts at 10"),
    ("RENUM", ["5 GOTO 77", "RENUM", "LIST"], "a reference to a missing line"),
    ("RENUM", ['5 PRINT "GOTO 7":REM 9', "7 RESTORE 7:GOSUB 7:ON 1 GOTO 7,5", "RENUM", "LIST"],
     "references rewritten, text left alone"),
    ("RENUM", ['10 PRINT "A"', "RENUM 10,,0", "LIST"], "an increment of 0"),
    ("RENUM", ['10 PRINT "A"', '20 PRINT "B"', '30 PRINT "C"', "RENUM 20,30", "LIST"], "lines that would overlap"),
    ("RENUM", ST + ["RENUM 100", "CONT"], "RENUM keeps the variables and CONT"),
]
GROUPS = {"FX": FX}



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
            out[who] += [NS(src=group, id=f"KNL {group} {i}", kw=kw, lines=lines, why=why, scr=data[group][who][i])
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
