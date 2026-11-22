#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""D-TAPELEADEREND / D-TAPESTARTBIT: two half-periods of a tape WRITE, in T-states, on each machine. The C-BIOS
0.32 port measured (on zerobas's own tape routines, ported) the leader's LAST low half at 1043 T against the
VG-8020's 740-756, and a byte's start-bit low half at 1597 T against 1492. Black box: a watchpoint on the PPI
control register ($AB) logs every cassette-out edge (BSR $0A / $0B) with the emulator's clock during a CSAVE
(scratchpad/kwdrain_castrace.py's method). Then:
  leader end  the LO half just before the first LONG half after a run of short ones (one per block's leader);
  start bit   the LO half of each long cycle that follows 4 short cycles (the previous byte's stop bits).
No ROM byte is read.
    python3 -u scratchpad/castrace_lead.py > scratchpad/CASTRACE_LEAD_run1.out"""
import os, sys, tempfile
from collections import Counter
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl, probe_sides  # noqa: E402

Z80 = 3579545.0


def trace(side):
    tmp = tempfile.mkdtemp(prefix="castl_")
    log, wav = os.path.join(tmp, "edges.txt"), os.path.join(tmp, "t.wav")
    cfg = probe_sides.sides(side)[side]
    pro = (f"cassetteplayer new {{{wav}}}", f"set ::cst [open {{{log}}} w]", "fconfigure $::cst -buffering line",
           "debug set_watchpoint write_io 0xAB {} {puts $::cst \"[machine_info time] $::wp_last_value\"}")
    omsx_repl.run_cases(cfg["machine"], [("d", list(cfg["reset"]) + ['10 PRINT"[Z9]"', 'CSAVE"ZQ"', '@WAIT30'])],
                        batch=False, reset=(), boot=cfg["boot"], step=5.0, cap_gap=90.0, timeout=1200.0,
                        prologue=pro)
    e = [(float(p[0]), int(p[1])) for p in (ln.split() for ln in open(log)) if len(p) == 2 and p[1] in ("10", "11")]
    return [("HI" if e[i][1] == 11 else "LO", round((e[i + 1][0] - e[i][0]) * Z80)) for i in range(len(e) - 1)]


def long_(t):
    return 1100 <= t < 2200


for side in sys.argv[1:] or ("vg8020", "zb"):
    h = trace(side)
    # polarity-agnostic (run 1's HI-first assumption found nothing on the VG-8020, which writes the other phase):
    # a long cycle = two consecutive long halves; 'leader end' = the half before the first long cycle after >= 40
    # short halves; 'start bit' = the long cycle's two halves after 8 short halves (the stop bits).
    lead, start1, start2 = [], [], []
    for i in range(8, len(h) - 1):
        if long_(h[i][1]) and long_(h[i + 1][1]) and not long_(h[i - 1][1]):
            if all(not long_(x) for _, x in h[i - 8:i]):
                start1.append(h[i][1])
                start2.append(h[i + 1][1])
            if i >= 41 and all(not long_(x) for _, x in h[i - 41:i - 1]):
                lead.append(f"{h[i - 1][0]} {h[i - 1][1]}")
    print(f"{side:7} halves {len(h)}", flush=True)
    for name, v in (("leader end", lead), ("start bit 1st", start1), ("start bit 2nd", start2)):
        c = Counter(v).most_common(4)
        print(f"{side:7} {name:14} n={len(v):<5} " + " ".join(f"{a} x{b}" for a, b in c), flush=True)
