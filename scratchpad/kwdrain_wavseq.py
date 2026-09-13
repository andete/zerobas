#!/usr/bin/env python3
"""WHERE does the jitter sit? `cas_cycle` is a tight djnz pair, so a half-period
inside one cycle is constant by construction. What is NOT constant is the code
BETWEEN cycles (pop/pop/djnz/rra/push/push/jr/call cas_short|cas_long/call), which
runs while the output line is still holding its last level — so it should stretch
the half-period that SPANS a bit boundary, by a data-dependent amount.

This prints the half-period SEQUENCE right after the leader, so the outliers can be
located rather than inferred: if the stretched ones land on bit boundaries, the
inter-cycle overhead is the mechanism.
"""
import os, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl, probe_sides, cas_decode
tmp = tempfile.mkdtemp(prefix="wavseq_")
for side in ("vg8020", "zb"):
    cfg = probe_sides.sides(side)[side]
    wav = os.path.join(tmp, f"{side}.wav")
    omsx_repl.run_cases(cfg["machine"],
                        [("d", list(cfg["reset"]) + ['10 PRINT"[Z9]"', 'CSAVE"ZQ"', '@WAIT30'])],
                        batch=False, reset=(), boot=cfg["boot"], step=5.0,
                        cap_gap=150.0, timeout=1200.0,
                        prologue=(f"cassetteplayer new {{{wav}}}",))
    s, fr = cas_decode.read_samples(wav)
    hp = cas_decode.half_periods(cas_decode.zero_crossings(s))
    thr = cas_decode.auto_threshold(hp)
    # first half-period past the opening leader run
    i = 0
    while i < len(hp) and hp[i] <= thr:
        i += 1
    print("=== %-7s leader ends at half-period %d; the next 64:" % (side, i))
    seq = hp[i:i + 64]
    for row in range(0, len(seq), 16):
        print("      %s" % " ".join("%2d" % h for h in seq[row:row + 16]))
    sys.stdout.flush()
