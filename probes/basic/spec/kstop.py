#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""KSTOP -- the measured cases behind docs/keywords/END.md, STOP.md, CONT.md and RUN.md: the flow region's last
keyword probe (D-KWSPEC; docs/keywords/spec-plan.md §2 region 5; docs/spec-method.md §3a). These statements stop or
restart the program, so the RAM-record harness (a program that records) cannot hold them: this probe reads the SCREEN.

Clean room: typed BASIC in, the text screen out (probes/lib/omsx_repl.py's SCREEN-0 capture). No reference ROM byte is
read.

EACH CASE is a fresh machine state (`NEW`, `CLS`), a short program typed, then the commands the case names (RUN,
CONT, ...). The screen after the `CLS` is NORMALISED: every line stripped; the prompt line -- "Ok" on the VG-8020, "ZB"
on zerobas, a deliberate difference (basic/repl.asm) -- read as `<prompt>`; the function-key line dropped; blank lines
dropped. The program's own output is tagged `[...]` so it cannot be confused with a message.

    python3 probes/basic/spec/kstop.py [--out scratchpad/KSP_run1.out]"""
import json
import os
import re
import sys
from types import SimpleNamespace as NS

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl  # noqa: E402

RUN = "KSP_run1.out"
MACHINES = (("ref", "Philips_VG_8020"), ("zb", "C-BIOS_MSX1_EU_REPACK_NODISK"))

# (keyword, the typed lines after NEW / CLS, what it separates)
FX = [
    ("END", ['10 PRINT "[A]":END:PRINT "[B]"', "RUN"], "END stops the program mid-line"),
    ("END", ['10 PRINT "[A]":END', '20 PRINT "[B]"', "RUN", "CONT"], "CONT after END"),
    ("END", ["END"], "END in direct mode"),
    ("END", ['10 GOSUB 30:PRINT "[A]"', "20 END", "30 END", "RUN"], "END inside a GOSUB"),
    ("STOP", ['10 PRINT "[A]":STOP:PRINT "[B]"', "RUN"], "STOP stops with Break in"),
    ("STOP", ['10 PRINT "[A]":STOP:PRINT "[B]"', "RUN", "CONT"], "CONT after STOP goes on after it"),
    ("STOP", ['10 GOSUB 30:PRINT "[C]":END', '30 PRINT "[A]":STOP:PRINT "[B]":RETURN', "RUN", "CONT"],
     "STOP inside a GOSUB, then CONT returns normally"),
    ("STOP", ['10 FOR I=1 TO 3:PRINT "[";I;"]";:STOP:NEXT', "RUN", "CONT", "CONT"], "STOP inside a FOR, CONT twice"),
    ("STOP", ["STOP"], "STOP in direct mode"),
    ("STOP", ['10 A=5:STOP:PRINT "[";A;"]"', "RUN", "A=7", "CONT"], "a variable changed while stopped"),
    ("CONT", ["CONT"], "CONT before anything ran"),
    ("CONT", ['10 PRINT "[A]":X=1/0:PRINT "[B]"', "RUN", "CONT"], "CONT after an error"),
    ("CONT", ['10 PRINT "[A]":STOP:PRINT "[B]"', "RUN", '20 PRINT "[C]"', "CONT"], "CONT after a line was added"),
    ("CONT", ['10 PRINT "[A]":STOP:PRINT "[B]"', "RUN", "PRINT 1+1", "CONT"], "CONT after a direct statement"),
    ("RUN", ['10 PRINT "[A]"', '20 PRINT "[B]"', "RUN 20"], "RUN n starts at line n"),
    ("RUN", ['10 PRINT "[A]"', "RUN 15"], "RUN to a line that does not exist"),
    ("RUN", ['10 PRINT "[";A;"]":A=5', "RUN", "RUN"], "RUN clears the variables"),
    ("RUN", ['10 PRINT "[A]":RUN 20', '20 PRINT "[B]"', "RUN"], "RUN inside a program"),
    ("RUN", ["RUN"], "RUN with no program"),
]

# GROUP FY -- goldfish pass 1 (scratchpad/REVIEW-m2-gkwstop.md): the cases that separate the rules' rivals.
P = '10 PRINT "[A]":STOP:PRINT "[B]"'
FY = [
    ("END", ['10 GOSUB 30:PRINT "[A]":END', "30 END:RETURN", "RUN", "CONT"], "END inside a GOSUB, then CONT"),
    ("END", ['10 PRINT "[A]":END:PRINT "[B]"', '20 PRINT "[C]"', "RUN", "CONT"], "CONT after a mid-line END"),
    ("END", ["10 OPEN \"CRT:\" FOR OUTPUT AS #1:END", "RUN", 'PRINT #1,"[X]"'], "END leaves a file open"),
    ("END", ["10 ON ERROR GOTO 100", "20 X=1/0", '100 PRINT "[H]":END', "RUN", "RESUME"], "END inside an error handler"),
    ("STOP", ['10 PRINT "[A]"', "20 STOP", "RUN"], "Break in names the STOP's own line"),
    ("STOP", ["10 ON ERROR GOTO 100", '20 X=1/0:PRINT "[B]":END', '100 PRINT "[H]":STOP:RESUME NEXT', "RUN", "CONT"],
     "STOP inside an error handler, then CONT"),
    ("STOP", ['10 FOR I=1 TO 3:PRINT "[";I;"]";:STOP:NEXT:PRINT "[E]"', "RUN", "CONT", "CONT", "CONT"],
     "STOP inside a FOR, CONT to the loop's end"),
    ("CONT", [P, "RUN", '10 PRINT "[A]":STOP:PRINT "[Z]"', "CONT"], "CONT after the stopped line was changed"),
    ("CONT", [P, "RUN", "20", "CONT"], "CONT after deleting a line that does not exist"),
    ("CONT", [P, '20 PRINT "[C]"', "RUN", "20", "CONT"], "CONT after deleting a line"),
    ("CONT", ["10 A=5:STOP", "RUN", "20 REM", "PRINT A"], "an edit clears the variables"),
    ("CONT", [P, "RUN", "NEW", "CONT"], "CONT after NEW"),
    ("CONT", [P, "RUN", "CLEAR", "CONT"], "CONT after CLEAR"),
    ("CONT", [P, "RUN", "RUN 15", "CONT"], "CONT after RUN to a missing line"),
    ("CONT", [P, "RUN", "STOP", "CONT"], "CONT after a typed STOP"),
    ("CONT", [P, "RUN", "END", "CONT"], "CONT after a typed END"),
    ("CONT", [P, "RUN", "PRINT 1/0", "CONT"], "CONT after a typed error"),
    ("CONT", [P, "RUN", "FOR J=1 TO 2:NEXT", "CONT"], "CONT after a typed FOR loop"),
    ("CONT", ['10 PRINT "[A]"', "RUN", "CONT", "CONT"], "CONT after the program ran to its end"),
    ("CONT", ['10 PRINT "[A]":X=1/D:PRINT "[B]"', "RUN", "D=1", "CONT"], "CONT after an error runs the statement again"),
    ("CONT", [P, "RUN", "CONT:PRINT 1"], "the rest of CONT's line"),
    ("CONT", ["10 CONT", "RUN"], "CONT inside a program"),
    ("RUN", ['10 PRINT "[";A$;"]":A$="X"', "RUN", "RUN"], "RUN clears a string"),
    ("RUN", ['10 DIM A(5):PRINT "[D]"', "RUN", "RUN"], "RUN clears an array"),
    ("RUN", ['10 READ A:PRINT "[";A;"]"', "20 DATA 1,2", "RUN", "RUN"], "RUN resets the DATA pointer"),
    ("RUN", ["10 ON ERROR GOTO 100", "20 STOP", "30 X=1/0", '100 PRINT "[H]":END', "RUN", "RUN 30"],
     "RUN resets ON ERROR"),
    ("RUN", ["10 A=5:RUN 30", '20 PRINT "[X]"', '30 PRINT "[";A;"]"', "RUN"], "RUN n inside a program clears and jumps"),
    ("RUN", ['10 V=VPEEK(4096):VPOKE 4096,V+1:PRINT "[";V;"]":IF V=1 THEN END', "20 RUN", "VPOKE 4096,0", "RUN"],
     "a bare RUN inside a program restarts it"),
    ("RUN", ["10 OPEN \"CRT:\" FOR OUTPUT AS #1:END", '20 PRINT #1,"[X]"', "RUN", "RUN 20"], "RUN closes a file"),
    ("RUN", ["10 A=5", "RUN", "PRINT A"], "the end of a run keeps the variables"),
    ("RUN", ['10 PRINT "[A]"', '20 PRINT "[B]"', "RUN20"], "RUN n without a space"),
    ("RUN", ['10 PRINT "[A]"', "RUN A+0"], "RUN and a number expression"),
    # FY 28's file was already closed by its END: these two keep it open across a STOP
    ("STOP", ["10 OPEN \"CRT:\" FOR OUTPUT AS #1:STOP", '20 PRINT #1,"[X]"', "RUN", "CONT"], "STOP leaves a file open"),
    ("RUN", ["10 OPEN \"CRT:\" FOR OUTPUT AS #1:STOP", '20 PRINT #1,"[X]"', "RUN", "RUN 20"],
     "RUN closes a file left open by STOP"),
]
GROUPS = {"FX": FX, "FY": FY}


def normalise(raw):
    if raw is None:
        return None
    raw = raw.replace("\r", "").replace("\n", "")
    lines = [raw[i:i + 40].strip() for i in range(0, len(raw), 40)]   # the SCREEN-0 capture: 40-column rows
    out = []
    for l in lines:
        if not l or re.fullmatch(r"color\s+auto\s+goto\s+list\s+run", l):
            continue
        out.append("<prompt>" if l in ("Ok", "ZB") else l)
    return out


def measure(group):
    got = {}
    for who, m in MACHINES:
        raw = omsx_repl.run_cases(m, [("direct", ["NEW", "CLS"] + lines) for _, lines, _ in GROUPS[group]],
                                  batch=False)
        got[who] = [normalise(r) for r in raw]
    return got


def sections(data):
    """the run file's groups: {group: {"ref": [...], "zb": [...]}} (the first run's file held FX's two lists bare)"""
    return data if "FX" in data else {"FX": data}


def live_copy(run_file, td):
    """tools/spec_live.py's hook for a probe off the RAM-record harness: zerobas's screens re-measured on the current
    build into a copy of the run file; the reference's side stays as committed (never re-run). None: no reading."""
    data = sections(json.load(open(run_file)))
    for group, cases in GROUPS.items():
        raw = omsx_repl.run_cases(MACHINES[1][1], [("direct", ["NEW", "CLS"] + lines) for _, lines, _ in cases],
                                  batch=False)
        zb = [normalise(r) for r in raw]
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
    data = sections(json.load(open(os.path.join(ROOT, "scratchpad", run))))
    out = {"ref": [], "zb": []}
    for group, cases in GROUPS.items():
        for who in ("ref", "zb"):
            out[who] += [NS(src=group, id=f"KST {group} {i}", kw=kw, lines=lines, why=why, scr=data[group][who][i])
                         for i, (kw, lines, why) in enumerate(cases)]
    return out


def main(argv):
    path = os.path.join(ROOT, "scratchpad", RUN)
    data = sections(json.load(open(path))) if os.path.exists(path) else {}
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
