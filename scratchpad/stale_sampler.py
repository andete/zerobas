#!/usr/bin/env python3
"""Sample, once a second, WHEN the repack ROMs go stale during a battery and
WHICH prerequisite's mtime moved to do it.

The battery calls this a FLAKE because the serial retry passes. run_gates.py's
own header already records one case where that verdict was wrong (a shared
tracked file read mid-write by `unit-test`). This does not ask whether the
retry passes; it asks what the tree looked like at the instant the probe
refused."""
import os, subprocess, sys, time

WATCH = ["build/basic-reloc.sym", "sub/basic-resident-abi.inc",
         "sub/math-coeffs.inc", "build/zerobas-main-eu.rom", "build/sub.rom",
         "build/basic.rom", "basic/sysvars.inc", "Makefile"]
TARGETS = ["build/zerobas-main-eu.rom", "build/sub.rom"]

def mt(p):
    try: return os.stat(p).st_mtime
    except OSError: return 0.0

base = {p: mt(p) for p in WATCH}
t0 = time.time()
prev_state = None
print(f"# sampling every 1s; baseline mtimes recorded at t=0", flush=True)
while True:
    if os.path.exists("/tmp/zerobas/SAMPLER_STOP"):
        break
    stale = []
    for t in TARGETS:
        rc = subprocess.run(["make", "-q", t], capture_output=True).returncode
        if rc != 0:
            stale.append(t)
    state = tuple(stale)
    if state != prev_state:
        el = time.time() - t0
        moved = [f"{p} (+{mt(p)-base[p]:.0f}s)" for p in WATCH if mt(p) != base[p]]
        print(f"[{el:7.1f}s] STALE={list(state) or 'none'}", flush=True)
        print(f"           mtimes moved since baseline: "
              f"{', '.join(moved) if moved else '(none)'}", flush=True)
        prev_state = state
    time.sleep(1)
print("# sampler stopped", flush=True)
