#!/usr/bin/env python3
"""🔴 PAD's row is BLIND to a dispatch cut and the reason is instructive: its
observation is an ERROR. `PRINT PAD(9)` is deliberately out of range, so a real
PAD raises Illegal function call while an absent PAD auto-dims an array and prints
0 — which discriminates TOKENISED from NOT. Cut PAD's dispatch and the word is
still tokenised, the fallback still errors, and the row sees no difference.

A row that observes a VALUE cannot be fooled that way: the cut turns a number into
an error. So find an in-range PAD(n) that answers the SAME value on both machines
and is therefore usable as the row's reading.
"""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl, probe_sides

LINES = ['NEW'] + ['PRINT"<";PAD(%d);">"' % n for n in range(8)]
for side in ("vg8020", "zb"):
    cfg = probe_sides.sides(side)[side]
    # with a TOUCHPAD PLUGGED: the device exists in openMSX and
    # basic_probe_input_devices.py already uses it, so the question is whether it
    # moves PAD off the 0 that both machines answer bare.
    caps = omsx_repl.run_cases(cfg["machine"], [("c", list(cfg["reset"]) + LINES)],
                               batch=False, reset=(), boot=cfg["boot"], step=1.0,
                               cap_gap=6.0, timeout=600.0,
                               prologue=("plug joyporta touchpad",))
    cap = caps[0]
    rows = [cap[r*40:(r+1)*40].rstrip() for r in range(24)] if cap else []
    rows = [r.strip() for r in rows if r.strip() and not r.startswith("color")]
    vals = [r for r in rows if r.startswith("<")]
    print("%-8s %s" % (side, " ".join(vals)))
    sys.stdout.flush()
