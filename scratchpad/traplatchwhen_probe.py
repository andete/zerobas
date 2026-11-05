#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-TRAPLATCHWHEN, measure first (2026-11-05): WHEN a held-back trap fires
after `INTERVAL ON` (or `KEY(n) ON` etc. -- here INTERVAL).

The handler records, at its own dispatch, C (statements the main loop ran since
`INTERVAL ON`) and E (TIME frames since then); TIME is work-area RAM. Our own
program, typed in, the screen read:

    10 ON INTERVAL=50 GOSUB 100:INTERVAL ON:D=-1
    20 INTERVAL STOP:T=TIME
    30 IF TIME-T<120 THEN 30              <- two periods pass while stopped
    40 C=0:T0=TIME:INTERVAL ON
    50 C=C+1:IF C<<N> AND D<0 THEN 50
    60 PRINT "<";D;E;">":END
    100 IF D<0 THEN D=C:E=TIME-T0:INTERVAL OFF
    110 RETURN

Variant `sync`: line 40 first waits for TIME to tick (`T1=TIME`/`IF TIME=T1`),
so INTERVAL ON lands right after an interrupt -- separates "the next interrupt"
from "the next statement boundary".

    python3 -u scratchpad/traplatchwhen_probe.py [MACHINE...]
"""
import os, re, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

BASE = ["10 ON INTERVAL=50 GOSUB 100:INTERVAL ON:D=-1",
        "20 INTERVAL STOP:T=TIME",
        "30 IF TIME-T<120 THEN 30",
        "40 C=0:T0=TIME:INTERVAL ON",
        "50 C=C+1:IF C<3000 AND D<0 THEN 50",
        '60 PRINT "<";D;E;">":END',
        "100 IF D<0 THEN D=C:E=TIME-T0:INTERVAL OFF",
        "110 RETURN"]
SYNC = [l if not l.startswith("40 ") else
        "40 T1=TIME\n45 IF TIME=T1 THEN 45 ELSE C=0:T0=TIME:INTERVAL ON" for l in BASE]
CASES = {"plain": BASE, "sync": [x for l in SYNC for x in l.split("\n")]}
# round 2: INTERVAL ON mid-line, with statements after it on the SAME line
MID = [l if not l.startswith("40 ") else "40 C=0:T0=TIME:INTERVAL ON:C=C+1:C=C+1:C=C+1:C=C+1"
       for l in BASE]
GOTO = [l if not l.startswith("40 ") else "40 C=0:T0=TIME:INTERVAL ON:GOTO 50" for l in BASE]
REM = [l if not l.startswith("40 ") else "40 C=0:T0=TIME:INTERVAL ON:REM X" for l in BASE]
if "--round2" in sys.argv:
    sys.argv.remove("--round2")
    CASES = {"mid": MID, "goto": GOTO, "rem": REM}
MACHINES = ["Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK"]
RX = re.compile(r"<[^<>]*>")


def main():
    for m in sys.argv[1:] or MACHINES:
        for name, lines in CASES.items():
            raw = omsx_repl.run_cases(m, [("direct", ["NEW"] + lines + ["RUN"])],
                                      batch=False, reset=("", "SCREEN 0"),
                                      run_gap=40.0)[0] or ""
            flat = raw.replace("\n", "")
            run = flat[flat.rfind("RUN") + 3:] if "RUN" in flat else flat
            hits = RX.findall(run)
            print(f"{m[:12]:12s} {name:6s} {hits[-1] if hits else 'NONE ' + run[-60:]}",
                  flush=True)
    print(__import__("probe_refcache").summary())


if __name__ == "__main__":
    main()
