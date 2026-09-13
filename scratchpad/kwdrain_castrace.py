#!/usr/bin/env python3
"""🔬 STOP INFERRING THE WRITER'S TIMING FROM A RECORDING — ASK THE CPU.

Every reading in this defect so far came from the WAV: zerobas writes a tape,
the WAV is decoded, half-periods are counted in SAMPLES. That measures the
writer CONVOLVED with whatever the emulated cassette port does to it, and it
quantises to the sample rate, which is why "38 vs 46 outliers" could never say
WHICH emission was late.

A watchpoint on the PPI control register writes both edges of every cassette
cycle with the emulator's own clock attached. The reference machine runs the
SAME program through the SAME watchpoint, so the two half-period sequences are
directly comparable in T-STATES, with no recording in between.

`0x0A`/`0x0B` are the BSR commands that clear/set port C bit 5 (the cassette
output); every other write to $AB (key click, CAPS, motor) is filtered out.
"""
import os, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
sys.path.insert(0, os.path.join(ROOT, "probes", "disk"))
import omsx_repl, probe_sides
from collections import Counter

Z80 = 3579545.0  # MSX1 CPU clock; T-states = seconds * Z80

def trace(side):
    tmp = tempfile.mkdtemp(prefix="castrace_")
    log = os.path.join(tmp, "edges.txt")
    wav = os.path.join(tmp, "t.wav")
    cfg = probe_sides.sides(side)[side]
    prologue = (
        f"cassetteplayer new {{{wav}}}",
        f"set ::cst [open {{{log}}} w]",
        "fconfigure $::cst -buffering line",
        "debug set_watchpoint write_io 0xAB {} "
        "{puts $::cst \"[machine_info time] $::wp_last_value\"}",
    )
    omsx_repl.run_cases(cfg["machine"],
                        [("d", list(cfg["reset"]) + ['10 PRINT"[Z9]"',
                                                    'CSAVE"ZQ"', '@WAIT30'])],
                        batch=False, reset=(), boot=cfg["boot"], step=5.0,
                        cap_gap=90.0, timeout=1200.0, prologue=prologue)
    edges = []
    for ln in open(log):
        p = ln.split()
        if len(p) == 2 and p[1] in ("10", "11"):   # 0x0A / 0x0B, decimal
            edges.append((float(p[0]), int(p[1])))
    return edges

def halves(edges):
    """(phase, T-states) per half-period. The BSR value that OPENED the half
    names it: 0x0B set port C bit 5, 0x0A cleared it."""
    return [("HI" if edges[i][1] == 11 else "LO",
             round((edges[i+1][0] - edges[i][0]) * Z80))
            for i in range(len(edges) - 1)]

# The two tones are far apart (~750 T and ~1500 T), so a midpoint splits them
# with no judgement call; within each tone the two PHASES are the subject.
for side in ("vg8020", "zb"):
    h = halves(trace(side))
    print("%s  (%d half-periods)" % (side, len(h)))
    for tone, lo, hi in (("short", 400, 1100), ("long", 1100, 2200)):
        for phase in ("HI", "LO"):
            vals = [t for p, t in h if p == phase and lo <= t < hi]
            if not vals:
                continue
            c = Counter(vals).most_common(3)
            print("   %-5s %s  n=%-6d mode=%-5d  %s"
                  % (tone, phase, len(vals), c[0][0],
                     " ".join("%d x%d" % (v, n) for v, n in c)))
    for tone, lo, hi in (("short", 400, 1100), ("long", 1100, 2200)):
        m = {p: Counter(t for q, t in h if q == p and lo <= t < hi).most_common(1)
             for p in ("HI", "LO")}
        if m["HI"] and m["LO"]:
            a, b = m["HI"][0][0], m["LO"][0][0]
            print("   %-5s duty skew LO-HI = %+d T   (full cycle %d T)"
                  % (tone, b - a, a + b))
    sys.stdout.flush()
