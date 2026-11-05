#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-TRAPSTMT, measure first (2026-11-05): WHERE in a multi-statement line an
ordinary (non-latched) interrupt trap is dispatched.

ON INTERVAL=1 fires every frame; line 20 sets markers M=1..9 between its
statements, so the handler's H(M) histogram says which statement boundaries it
was dispatched at. Line-level dispatch puts everything in one bucket. Our own
program, typed in, the screen read:

    10 DIM H(9):ON INTERVAL=1 GOSUB 100:INTERVAL ON
    20 M=1:M=2:M=3:M=4:M=5:M=6:M=7:M=8:M=9:N=N+1:IF N<300 THEN 20
    30 INTERVAL OFF:PRINT "<";:FOR I=0 TO 9:PRINT H(I);:NEXT:PRINT ">":END
    100 H(M)=H(M)+1:RETURN

    python3 -u scratchpad/trapstmt_probe.py [MACHINE...]
"""
import os, re, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

PROG = ["10 DIM H(9):ON INTERVAL=1 GOSUB 100:INTERVAL ON",
        "20 M=1:M=2:M=3:M=4:M=5:M=6:M=7:M=8:M=9:N=N+1:IF N<300 THEN 20",
        '30 INTERVAL OFF:PRINT "<";:FOR I=0 TO 9:PRINT H(I);:NEXT:PRINT ">":END',
        "100 H(M)=H(M)+1:RETURN"]
MACHINES = ["Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK"]
# round 2: a handler that certainly outlasts a frame (a delay loop), so the
# event re-latches before RETURN. No grace after RETURN -> nothing advances
# (no output); a one-statement grace -> one main-line statement per dispatch.
SLOW = ["10 DIM H(9):ON INTERVAL=1 GOSUB 100:INTERVAL ON",
        "20 M=1:M=2:M=3:M=4:M=5:M=6:M=7:M=8:M=9:N=N+1:IF N<5 THEN 20",
        '30 INTERVAL OFF:PRINT "<";:FOR I=0 TO 9:PRINT H(I);:NEXT:PRINT ">":END',
        "100 H(M)=H(M)+1:FOR J=1 TO 40:NEXT:RETURN"]
# round 3: what the round-1 handler costs, in frames per 100 calls
COST = ["10 DIM H(9):M=3:T=TIME:FOR K=1 TO 100:GOSUB 100:NEXT",
        '30 PRINT "<";TIME-T;">":END',
        "100 H(M)=H(M)+1:RETURN"]
if "--cost" in sys.argv:
    sys.argv.remove("--cost")
    PROG = COST
if "--slow" in sys.argv:
    sys.argv.remove("--slow")
    PROG = SLOW
RX = re.compile(r"<[^<>]*>")


def main():
    for m in sys.argv[1:] or MACHINES:
        raw = omsx_repl.run_cases(m, [("direct", ["NEW"] + PROG + ["RUN"])],
                                  batch=False, reset=("", "SCREEN 0:WIDTH 40"),
                                  run_gap=60.0)[0] or ""
        flat = raw.replace("\n", "")
        run = flat[flat.rfind("RUN") + 3:] if "RUN" in flat else flat
        hits = RX.findall(run)
        print(f"{m[:12]:12s} {re.sub(' +', ' ', hits[-1]) if hits else 'NONE ' + run[-80:]}", flush=True)
    print(__import__("probe_refcache").summary())


if __name__ == "__main__":
    main()
