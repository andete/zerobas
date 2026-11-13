#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-CLMLST: two published work-area cells BASIC keeps -- CLMLST ($F3B2, PRINT's last
comma-zone column) and CLIKSW ($F3DB, the key click switch) -- the VG-8020 against zerobas.

At power-on both references hold CLMLST 14 and CLIKSW 1; SCREEN / WIDTH recompute CLMLST
from LINLEN (WIDTH 32 -> 14, 20 -> 0, 37 / 40 -> 14; SCREEN 1 from LINL32), COLOR does not
(a POKEd 99 stays), and INITXT itself does not either (scratchpad/clmlst_probe2.out).
zerobas held 0 and 0 and never moved them (clmlst_probe1.out). One program reads them all.
Black box: work-area RAM only.

    python3 -u probes/basic/basic_probe_clmlst.py      (`make clmlst-acceptance`)
Exit 0 SAME; 1 a divergence; 2 the VG-8020 gave no reading.
"""
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

MACHINES = (("VG", "Philips_VG_8020"), ("ZB", "C-BIOS_MSX1_EU_REPACK_NODISK"))
PROG = ["NEW",
        "10 A=PEEK(&HF3B2):B=PEEK(&HF3DB):WIDTH 32:C=PEEK(&HF3B2):WIDTH 20:D=PEEK(&HF3B2)",
        "20 SCREEN 1:E=PEEK(&HF3B2):SCREEN 0:WIDTH 37:F=PEEK(&HF3B2):WIDTH 40:G=PEEK(&HF3B2)",
        "25 POKE &HF3B2,99:COLOR 15,4:H=PEEK(&HF3B2):POKE &HF3B2,14",
        '30 PRINT "[C";A;B;C;D;E;F;G;H;"]"', "RUN"]
LABEL = "boot-CLMLST CLIKSW | W32 W20 SCR1 W37 W40 | after COLOR (99 POKEd)"


def main():
    got = {}
    for side, m in MACHINES:
        raw = omsx_repl.run_cases(m, [("direct", PROG)], batch=False, reset=("",),
                                  step=3.0, run_gap=8.0)[0] or ""
        f = re.findall(r"\[C([ \d]+)\]", re.sub(r"\s+", " ", raw))
        got[side] = f[-1].split() if f else None
        print(f"{side} {LABEL} = {got[side]}", flush=True)
    if not got["VG"]:
        print("INSTRUMENT FAULT: the VG-8020 gave no reading")
        return 2
    ok = got["ZB"] == got["VG"]
    print(f"{'PASS' if ok else 'FAIL'}: CLMLST / CLIKSW as BASIC keeps them")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
