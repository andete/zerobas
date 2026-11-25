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


def measure():
    got = {}
    for who, m in MACHINES:
        raw = omsx_repl.run_cases(m, [("direct", ["NEW", "CLS"] + lines) for _, lines, _ in FX], batch=False)
        got[who] = [normalise(r) for r in raw]
    return got


def live_copy(run_file, td):
    """tools/spec_live.py's hook for a probe off the RAM-record harness: zerobas's screens re-measured on the current
    build into a copy of the run file; the reference's side stays as committed (never re-run). None: no reading."""
    data = json.load(open(run_file))
    raw = omsx_repl.run_cases(MACHINES[1][1], [("direct", ["NEW", "CLS"] + lines) for _, lines, _ in FX], batch=False)
    zb = [normalise(r) for r in raw]
    if any(z is None for z in zb):
        return None
    sys.stdout.write(f"  live {os.path.basename(run_file)}: zerobas "
                     f"{'as committed' if zb == data['zb'] else 'CHANGED since the committed run'}\n")
    data["zb"] = zb
    live = os.path.join(td, os.path.basename(run_file))
    with open(live, "w") as f:
        json.dump(data, f, indent=1)
    return live


def load(run=RUN):
    data = json.load(open(os.path.join(ROOT, "scratchpad", run)))
    out = {}
    for who in ("ref", "zb"):
        out[who] = [NS(src="FX", id=f"KST FX {i}", kw=kw, lines=lines, why=why, scr=data[who][i])
                    for i, (kw, lines, why) in enumerate(FX)]
    return out


def main(argv):
    path = os.path.join(ROOT, "scratchpad", RUN)
    got = measure()
    with open(path, "w") as f:
        json.dump(got, f, indent=1)
    n = sum(1 for a, b in zip(got["ref"], got["zb"]) if a != b)
    print(f"FX: {len(FX)} cases, {n} differ")
    for i, (a, b) in enumerate(zip(got["ref"], got["zb"])):
        mark = "" if a == b else "  <<"
        print(f"{i:2d} {FX[i][2][:44]:44s}{mark}\n    ref {a}\n    zb  {b}" if mark else f"{i:2d} {FX[i][2][:44]:44s} {a}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
