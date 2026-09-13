#!/usr/bin/env python3
"""Leader LENGTH is refuted: at 16 000/8 000 cycles zerobas's recording is
456 904 bytes against the reference's 467 322 — the same size — and the VG-8020
still hangs. So the difference is in the SHAPE, not the amount.

This compares the two recordings half-period by half-period, using the tree's own
cas_decode primitives, and prints the structure rather than a summary: where the
leader ends, what the run lengths are, and what the actual sample durations look
like on each side.
"""
import os, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl, probe_sides, cas_decode

tmp = tempfile.mkdtemp(prefix="wavshape_")
def record(side):
    cfg = probe_sides.sides(side)[side]
    wav = os.path.join(tmp, f"{side}.wav")
    omsx_repl.run_cases(cfg["machine"],
                        [("d", list(cfg["reset"]) + ['10 PRINT"[Z9]"', 'CSAVE"ZQ"', '@WAIT30'])],
                        batch=False, reset=(), boot=cfg["boot"], step=5.0,
                        cap_gap=150.0, timeout=1200.0,
                        prologue=(f"cassetteplayer new {{{wav}}}",))
    return wav

for side in ("vg8020", "zb"):
    wav = record(side)
    s, fr = cas_decode.read_samples(wav)
    xs = cas_decode.zero_crossings(s)
    hp = cas_decode.half_periods(xs)
    thr = cas_decode.auto_threshold(hp)
    print("=== %s  framerate=%d  half-periods=%d  threshold=%.1f samples" %
          (side, fr, len(hp), thr))
    print("    first 30 half-period durations (samples): %s" % hp[:30])
    # run-length structure: how long is the opening short-tone run, and what
    # follows it? The leader is the opening run; the data begins at its end.
    runs, cur, n = [], hp[0] <= thr, 0
    for h in hp:
        short = h <= thr
        if short == cur:
            n += 1
        else:
            runs.append(("short" if cur else "LONG", n)); cur, n = short, 1
    runs.append(("short" if cur else "LONG", n))
    print("    first 12 runs (kind, count): %s" % runs[:12])
    big = [r for r in runs if r[1] > 200]
    print("    runs longer than 200 half-periods: %s" % big[:8])
    sys.stdout.flush()
