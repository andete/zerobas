#!/usr/bin/env python3
"""The run-length structures are IDENTICAL apart from leader length — which the
16 000-cycle rebuild already refuted. But the decode summary reported a long-tone
average of 183 Hz for the reference against 1169 Hz for zerobas, and 183 Hz means
half-periods FAR longer than any data bit (~19 samples). Something in the
reference's tape is nearly flat and nothing in ours is.

Flat = SILENCE: no zero crossings, so a gap shows up as one enormous half-period.
This finds them and says where they sit.
"""
import os, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl, probe_sides, cas_decode
tmp = tempfile.mkdtemp(prefix="wavgap_")
for side in ("vg8020", "zb"):
    cfg = probe_sides.sides(side)[side]
    wav = os.path.join(tmp, f"{side}.wav")
    omsx_repl.run_cases(cfg["machine"],
                        [("d", list(cfg["reset"]) + ['10 PRINT"[Z9]"', 'CSAVE"ZQ"', '@WAIT30'])],
                        batch=False, reset=(), boot=cfg["boot"], step=5.0,
                        cap_gap=150.0, timeout=1200.0,
                        prologue=(f"cassetteplayer new {{{wav}}}",))
    s, fr = cas_decode.read_samples(wav)
    xs = cas_decode.zero_crossings(s)
    hp = cas_decode.half_periods(xs)
    big = [(i, h) for i, h in enumerate(hp) if h > 40]      # >2x a data LONG
    print("=== %-7s half-periods=%-6d  max=%-6d  (a data LONG is ~19 samples)"
          % (side, len(hp), max(hp)))
    print("    half-periods over 40 samples: %d  %s"
          % (len(big), [(i, h) for i, h in big[:6]]))
    tot = sum(h for _, h in big)
    print("    total time in those: %.2f s of %.2f s" % (tot / fr, sum(hp) / fr))
    sys.stdout.flush()
