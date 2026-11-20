#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-TRGFLGISR part 2: TRGFLG ($F3E8) and the PSG's R15 / R14 with port 1's trigger A or B HELD on
the RP2040-Zero rig (probes/lib/rigfw.py). Black box: a BASIC PEEK of the published cell after a delay
loop, so several key scans have run, then the PSG registers read through ports $A0 / $A2 (I/O state).
No ROM byte is read.
    ZEROBAS_REFCACHE=0 python3 -u scratchpad/trgflg_rig_probe.py > scratchpad/TRGFLG_rig1.out
    ZEROBAS_REFCACHE=0 python3 -u scratchpad/trgflg_rig_probe.py portb > scratchpad/TRGFLG_rig2.out"""
import os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl, probe_sides, rigfw  # noqa: E402

PROG = ["10 FOR I=1 TO 400:NEXT",
        "20 T=PEEK(&HF3E8):OUT &HA0,15:R=INP(&HA2):OUT &HA0,14:J=INP(&HA2)",
        "30 PRINT \"T=\";T;\"R15=\";R;\"R14=\";J", "RUN"]
port = rigfw.find()
assert port, "no rig board answers"
try:
    portb = "portb" in sys.argv[1:]       # the same stick plugged into joystick port 2 instead
    for state in ("centre", "trig1", "trig2"):
        rigfw.set_state(port, state)
        pro = rigfw.prologue(state)
        if portb:
            pro = tuple(c.replace("plug joyporta", "plug joyportb") for c in pro)
        for side in ("vg8020", "cf3300", "zb"):
            m = probe_sides.MACHINES[side]
            scr = omsx_repl.run_batch(m["machine"], [("direct", PROG)], boot=m["boot"], reset=m["reset"],
                                      prologue=pro)[0] or ""
            v = re.findall(r"T=\s*(\d+)\s*R15=\s*(\d+)\s*R14=\s*(\d+)", scr)
            if v:
                t, r, j = (int(x) for x in v[-1])
                print(f"{state:6} {side:7} TRGFLG ${t:02X}  R15 ${r:02X}  R14 ${j:02X}")
            else:
                print(f"{state:6} {side:7} <none>")
finally:
    rigfw.set_state(port, "centre")
