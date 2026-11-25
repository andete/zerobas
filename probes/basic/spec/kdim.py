#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""KDIM -- the measured cases behind docs/keywords/DIM.md, ERASE.md and CLEAR.md: the program region's second keyword
probe (D-KWSPEC; docs/keywords/spec-plan.md §2 region 7; docs/spec-method.md §3a). It reads the SCREEN, as kstop.py,
kerr.py, ktron.py and kdata.py do (their normalisation, machines, frame); the model is kstop_model.py's small BASIC.
The memory-limit cases are far from the boundary (`DIM A%(20000)`, `CLEAR 30000` exceed ANY free memory a 32 K
VG-8020 has), so no case depends on a free-memory figure.

Clean room: typed BASIC in, the text screen out. No reference ROM byte is read.

    python3 probes/basic/spec/kdim.py [FX]"""
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

RUN = "KDM_run1.out"
MACHINES = kstop.MACHINES

# (keyword, the typed lines after NEW / CLS, what it separates)
FX = [
    ("DIM", ["10 DIM A(3):A(3)=7:PRINT A(3);A(0)", "RUN"], "subscripts from 0 to the bound"),
    ("DIM", ["10 DIM A(3):A(4)=1", "RUN"], "past the bound"),
    ("DIM", ["10 A(10)=5:PRINT A(10)", "RUN"], "an undeclared array has bound 10"),
    ("DIM", ["10 A(11)=5", "RUN"], "past an undeclared array's bound"),
    ("DIM", ["10 DIM A(2,3):A(2,3)=4:PRINT A(2,3)", "RUN"], "two dimensions"),
    ("DIM", ["10 DIM A(-1)", "RUN"], "a negative bound"),
    ("DIM", ["10 DIM A(70000)", "RUN"], "a bound past 65535"),
    ("DIM", ["10 DIM A(10000)", "RUN"], "more than 65535 bytes of doubles"),
    ("DIM", ["10 DIM Q%(200,200)", "RUN"], "more than 65535 bytes from small bounds"),
    ("DIM", ["10 DIM A%(20000)", "RUN"], "more than free memory"),
    ("DIM", ["10 DIM A(2):DIM A(2)", "RUN"], "DIM twice"),
    ("DIM", ['10 DIM A("X")', "RUN"], "a string bound"),
    ("DIM", ["10 DIM 5", "RUN"], "a number for a name"),
    ("DIM", ["10 DIM", "RUN"], "DIM alone"),
    ("DIM", ["10 DIM A,", "RUN"], "a trailing comma"),
    ("DIM", ["10 ON ERROR GOTO 90:DIM P(3),Q(-1)", "20 END", '90 DIM P(5):PRINT "[N]":END', "RUN"],
     "the arrays before a failing one stay"),
    ("DIM", ['10 DIM A:PRINT "[";A;"]"', "RUN"], "a name without bounds"),
    ("DIM", ["10 DIM A%(2),A(2):A%(1)=1.7:A(1)=1.7:PRINT A%(1);A(1)", "RUN"], "an integer array and a double one"),
    ("ERASE", ["10 DIM A(2):A(1)=5:ERASE A:PRINT A(1)", "RUN"], "ERASE, then the name used again"),
    ("ERASE", ["10 ERASE A", "RUN"], "ERASE an array that does not exist"),
    ("ERASE", ["10 DIM A(2):ERASE A:ERASE A", "RUN"], "ERASE twice"),
    ("ERASE", ["10 DIM A(2):ERASE A%", "RUN"], "ERASE another type's array"),
    ("ERASE", ["10 ERASE", "RUN"], "ERASE alone"),
    ("ERASE", ["10 DIM A(2):ERASE A(1)", "RUN"], "ERASE an element"),
    ("ERASE", ["10 ON ERROR GOTO 90:DIM P(3):ERASE P,Q", "20 END", '90 DIM P(5):PRINT "[E]":END', "RUN"],
     "the names before a failing one are erased"),
    ("ERASE", ['10 DIM A(2):ERASE A:DIM A(5):PRINT "[R]"', "RUN"], "DIM again after ERASE"),
    ("CLEAR", ["10 A=5:CLEAR:PRINT A", "RUN"], "CLEAR clears the variables"),
    ("CLEAR", ["10 ON ERROR GOTO 90:CLEAR", "20 X=1/0", '90 PRINT "[H]":END', "RUN"], "CLEAR switches ON ERROR off"),
    ("CLEAR", ["10 READ A:CLEAR:READ B:PRINT A;B", "20 DATA 1,2", "RUN"], "CLEAR takes READ back to the first item"),
    ("CLEAR", ['10 CLEAR:PRINT "[K]"', "RUN"], "the program goes on after CLEAR"),
    ("CLEAR", ['10 CLEAR 500:PRINT FRE("")', "RUN"], "CLEAR n sets the string space"),
    ("CLEAR", ['PRINT FRE("")'], "the string space at start-up"),
    ("CLEAR", ["10 CLEAR 500", "RUN", "CLEAR", 'PRINT FRE("")'], "a bare CLEAR keeps the size"),
    ("CLEAR", ['10 CLEAR 300,&HC000:PRINT FRE("")', "RUN"], "moving the top keeps the size"),
    ("CLEAR", ["10 CLEAR -1", "RUN"], "a negative size"),
    ("CLEAR", ["10 CLEAR 70000", "RUN"], "a size past 65535"),
    ("CLEAR", ["10 CLEAR 30000", "RUN"], "more string space than memory"),
    ("CLEAR", ['10 CLEAR "A"', "RUN"], "a string size"),
    ("CLEAR", ["10 CLEAR 200,&H7000", "RUN"], "a top below &H8000"),
    ("CLEAR", ["10 CLEAR 200,", "RUN"], "a comma and no top"),
    ("CLEAR", ["10 CLEAR,", "RUN"], "a comma and no size"),
    ("CLEAR", ["10 A=5:ON ERROR GOTO 90:CLEAR -1", "20 END", '90 PRINT "[";A;"]":END', "RUN"],
     "a refused CLEAR changes nothing"),
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
            out[who] += [NS(src=group, id=f"KDM {group} {i}", kw=kw, lines=lines, why=why, scr=data[group][who][i])
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
