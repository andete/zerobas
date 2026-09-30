#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-EOFMODE -- EOF(n) on a channel that is not open FOR INPUT.

Batch 8 (scratchpad/t6enum_b8_0930.out) measured ONE mode: `EOF(1)` on a channel
open FOR OUTPUT is 61 (Bad file mode) on the CF-3300 and silently answers here.
Before a mode test is written, every other mode is asked, because the test's
shape depends on them: APPEND (3) is an output mode too, and RANDOM (4) is the
mode MS Disk BASIC is documented to allow EOF on -- documentation is not a
measurement. INPUT is the control: a file with data reads 0, at the end -1.
"""
from __future__ import annotations
import os, re, shutil, sys, tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

SIDES = {"cf3300": ("National_CF-3300", 14.0),
         "zb": ("C-BIOS_MSX1_EU_REPACK_DISK", 8.0)}
E = ['90 PRINT"[E";ERR;"]":END', "RUN"]
CASES = [
    ("out",    ['10 ON ERROR GOTO 90', '20 OPEN"E1.TXT"FOR OUTPUT AS#1',
                '30 PRINT"[";EOF(1);"]":END'] + E),
    # 🔴 The first cut wrote E.TXT itself (OPEN/PRINT#/CLOSE, then re-OPEN): the
    # CF-3300 never came back from those three programs -- RUN still on screen at
    # a 120 s capture (dumped, eofmode_run.out's history). Not this item's subject;
    # the fixture's own HI.TXT (26 B) is opened instead, and nothing is written.
    ("app",    ['10 ON ERROR GOTO 90', '20 OPEN"HI.TXT"FOR APPEND AS#1',
                '30 PRINT"[";EOF(1);"]":END'] + E),
    ("rnd",    ['10 ON ERROR GOTO 90', '20 OPEN"R.DAT"AS#1',
                '30 PRINT"[";EOF(1);"]":END'] + E),
    ("rndput", ['10 ON ERROR GOTO 90', '20 OPEN"R2.DAT"AS#1 LEN=4',
                '30 PUT#1,1:PRINT"[";EOF(1);"]":END'] + E),
    ("in",     ['10 ON ERROR GOTO 90', '20 OPEN"HI.TXT"FOR INPUT AS#1',
                '30 PRINT"[";EOF(1);"]":END'] + E),
    ("inend",  ['10 ON ERROR GOTO 90', '20 OPEN"HI.TXT"FOR INPUT AS#1',
                '30 A$=INPUT$(26,#1)',
                '40 PRINT"[";EOF(1);"]":END'] + E),
    ("outtrap", ['10 ON ERROR GOTO 90', '20 OPEN"E3.TXT"FOR OUTPUT AS#1',
                 '30 A=EOF(1):PRINT"[";7;"]":END'] + E),
]


def main() -> int:
    for _, lines in CASES:
        for ln in lines:
            if len(ln) > 38:
                print(f"INSTRUMENT FAULT: {len(ln)} cols: {ln!r}")
                return 2
    out = {}
    for side, (machine, boot) in SIDES.items():
        tmp = tempfile.mkstemp(suffix=".dsk")[1]
        shutil.copyfile(os.path.join(REPO, "disk", "test720.dsk"), tmp)
        caps = omsx_repl.run_cases(machine, CASES, batch=False, boot=boot,
                                   reset=("", "SCREEN 0"), cap_gap=45.0,
                                   timeout=1800.0, diska=tmp)
        vals = []
        for cap in caps:
            ms = re.findall(r"\[\s*(E?)\s*(-?\d+)\s*\]", cap or "")
            vals.append(" ".join(("ERR " + v) if e else v for e, v in ms)
                        if ms else "<NO OUTPUT>")
        out[side] = vals
    print(f"{'case':8s} {'cf3300':>10s} {'zb':>10s}")
    for i, (name, _) in enumerate(CASES):
        a, b = out["cf3300"][i], out["zb"][i]
        print(f"{name:8s} {a:>10s} {b:>10s}  {'SAME' if a == b else 'DIFF'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
