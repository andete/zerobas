#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""KDATA -- the measured cases behind docs/keywords/DATA.md, READ.md and RESTORE.md: the program region's first keyword
probe (D-KWSPEC; docs/keywords/spec-plan.md §2 region 7; docs/spec-method.md §3a). The read values and the errors go to
the screen, so this probe reads the SCREEN, as kstop.py, kerr.py and ktron.py do (their normalisation, machines, frame);
the model is kstop_model.py's small BASIC.

Clean room: typed BASIC in, the text screen out. No reference ROM byte is read.

    python3 probes/basic/spec/kdata.py [FX]"""
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

RUN = "KDA_run1.out"
MACHINES = kstop.MACHINES
P = '10 READ A$:PRINT "[";A$;"]"'

# (keyword, the typed lines after NEW / CLS, what it separates)
FX = [
    ("DATA", ["10 READ A,B:PRINT A;B", "20 DATA 1,2", "RUN"], "two numbers"),
    ("DATA", [P, "20 DATA PAD  ,X", "RUN"], "trailing spaces kept"),
    ("DATA", [P, "20 DATA HI THERE", "RUN"], "spaces inside kept"),
    ("DATA", [P, "20 DATA   Y", "RUN"], "leading spaces skipped"),
    ("DATA", ['10 READ A$,B:PRINT "[";A$;"]";B', '20 DATA "A,B",7', "RUN"], "quotes protect a comma"),
    ("DATA", ["10 READ A$", '20 DATA "A:B":C=7', '30 PRINT "[";A$;"]";C', "RUN"], "quotes protect a colon"),
    ("DATA", ["10 READ A$", '20 DATA "A:B:C=7', '30 PRINT "[";A$;"]";C', "RUN"], "an unterminated quote"),
    ("DATA", [P, '20 DATA "  X  "', "RUN"], "quoted spaces kept at both ends"),
    ("DATA", ["10 READ A,B,C:PRINT A;B;C", "20 DATA 1,,3", "RUN"], "an empty item into a number"),
    ("DATA", ['10 READ A$,B$:PRINT "[";A$;"][";B$;"]"', "20 DATA ,X", "RUN"], "an empty item into a string"),
    ("DATA", [P, "20 DATA 42", "RUN"], "digits into a string stay text"),
    ("DATA", ["10 READ A", "20 DATA X", "RUN"], "text into a number"),
    ("DATA", ["10 READ A:PRINT A", "20 END:DATA 5", "RUN"], "DATA after END on its line"),
    ("READ", ["10 READ A", "RUN"], "no DATA at all"),
    ("READ", ["10 READ A,B", "20 DATA 1", "RUN"], "out of DATA in the middle of a READ"),
    ("READ", ["10 READ A:PRINT A", "20 DATA 5,6", "RUN", "READ B:PRINT B"], "a direct READ goes on after the program"),
    ("READ", ["10 DIM A(3):READ A(9)", "20 DATA 1", "RUN"], "a bad subscript"),
    ("READ", ["10 READ A:PRINT A", "20 DATA 5,6", "RUN", "RUN"], "RUN goes back to the first item"),
    ("READ", ["10 READ A:PRINT A", "20 DATA 5,6", "RUN", "CLEAR", "READ B:PRINT B"], "CLEAR goes back to the first item"),
    ("READ", ["10 READ A:PRINT A", "20 DATA 5,6", "RUN", "30 REM", "READ B:PRINT B"], "an edit goes back to the first item"),
    ("READ", ["10 READ A%", "20 DATA 70000", "RUN"], "a number too large for an integer"),
    ("READ", ["10 READ A,B$:PRINT A;\"[\";B$;\"]\"", "20 DATA 1", "30 DATA Z", "RUN"], "across DATA lines"),
    ("RESTORE", ["10 READ A:RESTORE:READ B:PRINT A;B", "20 DATA 5,6", "RUN"], "RESTORE and the rest of the line"),
    ("RESTORE", ["10 RESTORE 30:READ A:PRINT A", "20 DATA 1", "30 DATA 2", "RUN"], "RESTORE n"),
    ("RESTORE", ["10 RESTORE 25:READ A:PRINT A", "20 DATA 1", "25 REM", "30 DATA 2", "RUN"],
     "RESTORE to a line without DATA"),
    ("RESTORE", ["10 RESTORE 99", "RUN"], "RESTORE to a missing line"),
    ("RESTORE", ["10 RESTORE X", "RUN"], "RESTORE and a variable"),
    ("RESTORE", ["10 RESTORE,", "RUN"], "RESTORE and a comma"),
    ("RESTORE", ["10 READ A:RESTORE 20:READ B:PRINT A;B", "20 DATA 5,6", "RUN"], "RESTORE n to the line just read"),
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
            out[who] += [NS(src=group, id=f"KDA {group} {i}", kw=kw, lines=lines, why=why, scr=data[group][who][i])
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
