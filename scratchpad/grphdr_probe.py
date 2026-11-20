#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-PAINTRAMCLASH (Joost 2026-11-20: "why not figure what cells the reference uses for this and just use the
same?"): WHERE does each machine keep a GRP: channel's pending CHR$(1) -- the state zerobas keeps in GRP_HDR?
Black box: SCREEN 2, OPEN "GRP:" AS #1, then one of
  none     nothing printed
  pend     PRINT #1,CHR$(1);           (the header pending)
  done     PRINT #1,CHR$(1);CHR$(65);  (consumed by the next byte)
  pend2    PRINT #1,"AB";CHR$(1);      (pending after other output)
then the program loops and the work area $F380-$FFFF is read by the debugger. A cell that differs in BOTH pending
cases from BOTH others is a candidate. No ROM byte is read.
    python3 -u scratchpad/grphdr_probe.py > scratchpad/GRPHDR_run1.out"""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl, probe_sides  # noqa: E402

TAILS = {"none": "", "pend": "PRINT #1,CHR$(1);", "done": "PRINT #1,CHR$(1);CHR$(65);",
         "pend2": "PRINT #1,\"AB\";CHR$(1);"}
BASE, LEN = 0xF380, 0x10000 - 0xF380 - 1
for side in sys.argv[1:] or ("vg8020", "cf3300", "zb"):
    m = probe_sides.MACHINES[side]
    dumps = {}
    for name, tail in TAILS.items():
        prog = ["10 SCREEN 2:OPEN \"GRP:\" AS #1:" + tail, "20 GOTO 20", "RUN"]
        h = omsx_repl.run_batch(m["machine"], [("direct", prog)], boot=m["boot"], reset=m["reset"],
                                capture=("mem_abs", [(BASE, LEN)]))[0] or ""
        dumps[name] = bytes.fromhex(h) if len(h) == 2 * LEN else None
        print(f"{side:7} {name:6} {'ok' if dumps[name] else '<no dump>'}")
    if not all(dumps.values()):
        continue
    d = dumps
    for i in range(LEN):
        p, p2, n, k = d["pend"][i], d["pend2"][i], d["none"][i], d["done"][i]
        if p != n and p != k and p2 != n and p2 != k:
            print(f"  ${BASE + i:04X}: pend {p:02X} pend2 {p2:02X} none {n:02X} done {k:02X}")
