#!/usr/bin/env python3
"""Reproduce ONE cold case and ONE restore case with timing + hb diagnostics."""
import os, sys, time
ROOT = "/Users/joost/projects/zerobas"
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
sys.path.insert(0, os.path.join(ROOT, "scratchpad"))
import omsx_repl, circmiss_probe as cm

side = sys.argv[1] if len(sys.argv) > 1 else "zb"
cfg = cm.SIDES[side]
machine, boot = cfg["machine"], cfg["boot"]
label = "r.miss"
spec = ("direct", list(cfg["reset"]) + cm.CASES[label] + ["RUN"])
print("spec lines:", spec[1], flush=True)

t0 = time.time()
cold = omsx_repl.run_batch(machine, [spec], boot=boot, reset=(), step=3.0,
                           cap_gap=8.0, timeout=300.0, capture="screen")[0]
print(f"COLD wall={time.time()-t0:.1f}s cap_none={cold is None} face={cm.face(cold)!r}", flush=True)

state = os.path.join(ROOT, "scratchpad", "ss_diff_states", side)
oms = state + ".oms"
if not os.path.exists(oms):
    oms = omsx_repl.make_savestate(machine, state, boot=boot)
print("state:", oms, flush=True)
t0 = time.time()
rest = omsx_repl.run_batch(machine, [spec], boot=0.0, state_load=oms, reset=(),
                           step=3.0, cap_gap=8.0, timeout=300.0, capture="screen")[0]
print(f"RESTORE wall={time.time()-t0:.1f}s cap_none={rest is None} face={cm.face(rest)!r}", flush=True)
print("raw_eq:", cold == rest, flush=True)
