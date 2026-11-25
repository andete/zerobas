#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""KTRON -- the measured cases behind docs/keywords/TRON.md, TROFF.md and REM.md: the errors region's last keyword
probe (D-KWSPEC; docs/keywords/spec-plan.md §2 region 6; docs/spec-method.md §3a). TRON's trace goes to the screen, so
this probe reads the SCREEN, as kstop.py and kerr.py do (their normalisation, their machines, kerr.py's frame).

Clean room: typed BASIC in, the text screen out. No reference ROM byte is read.

    python3 probes/basic/spec/ktron.py [FX]"""
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

RUN = "KTN_run1.out"
MACHINES = kstop.MACHINES

# (keyword, the typed lines after NEW / CLS, what it separates)
FX = [
    ("TRON", ['10 PRINT "A"', '20 PRINT "B"', "TRON", "RUN"], "each line traced"),
    ("TRON", ['10 PRINT "A":PRINT "B"', "TRON", "RUN"], "one trace per line"),
    ("TRON", ['10 GOSUB 30:PRINT "R":END', '30 PRINT "S":RETURN', "TRON", "RUN"], "a GOSUB target traced, its return not"),
    ("TRON", ["10 FOR I=1 TO 2", "20 NEXT", "TRON", "RUN"], "a loop over two lines"),
    ("TRON", ['10 TRON:PRINT "A"', '20 PRINT "B"', "RUN"], "the TRON line itself is not traced"),
    ("TRON", ["TRON", 'PRINT "D"'], "a typed statement is not traced"),
    ("TRON", ['10 PRINT "A"', "TRON", "RUN", "RUN"], "the trace stays on through RUN"),
    ("TRON", ['10 PRINT "A"', "20 END", "TRON", "RUN"], "an END line is traced"),
    ("TRON", ['10 PRINT "A"', "TRON", "NEW", '10 PRINT "A"', "RUN"], "NEW switches the trace off"),
    ("TRON", ["10 TRON 1", "RUN"], "something after TRON"),
    ("TRON", ['10 PRINT "A";', '20 PRINT "B"', "TRON", "RUN"], "the trace has no new line of its own"),
    ("TRON", ['30000 PRINT "A"', "TRON", "RUN"], "a five-digit line"),
    ("TRON", ["10 GOTO 30", '20 PRINT "X"', '30 PRINT "Y"', "TRON", "RUN"], "a GOTO target traced"),
    ("TROFF", ['10 PRINT "A"', '20 TROFF:PRINT "B"', '30 PRINT "C"', "TRON", "RUN"], "the TROFF line is still traced"),
    ("TROFF", ["TROFF", '10 PRINT "A"', "RUN"], "TROFF when the trace is off"),
    ("TROFF", ["10 TROFF 1", "RUN"], "something after TROFF"),
    ("TROFF", ['10 PRINT "A"', "TRON", "RUN", "TROFF", "RUN"], "a typed TROFF"),
    ("REM", ['10 PRINT "A":REM PRINT "B"', "RUN"], "REM ends the line"),
    ("REM", ['10 PRINT "C" \'X', "RUN"], "the apostrophe without a colon"),
    ("REM", ["10 B=0:IF 0 THEN REM ELSE B=1", '20 PRINT "[";B;"]"', "RUN"], "REM swallows an ELSE"),
    ("REM", ['10 REM:PRINT "A"', '20 PRINT "B"', "RUN"], "a colon inside a REM"),
    ("REM", ["10 GOTO 20", "20 REM X", '30 PRINT "Z"', "RUN"], "a GOTO to a REM line"),
    ("REM", ['10 PRINT "A" REM X', "RUN"], "REM after a statement without a colon"),
    ("REM", ["REM typed", "PRINT 1"], "a typed REM"),
    ("REM", ['10 PRINT "A":\'B:PRINT "C"', "RUN"], "the apostrophe after a colon"),
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
            out[who] += [NS(src=group, id=f"KTN {group} {i}", kw=kw, lines=lines, why=why, scr=data[group][who][i])
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
