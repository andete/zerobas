#!/usr/bin/env python3
"""Four hypotheses refuted by measurement: leader LENGTH, inter-block SILENCE,
LEADING silence, and the mount form. Tone averages, framing and amplitude all
match. What has not been compared is the DISTRIBUTION of half-period durations —
and that is precisely what a BIOS's TAPION derives its 0/1 threshold from.

If zerobas's '0' bit sits at a different duration from the reference's while the
leader carrier matches, a threshold computed from the leader can reject every data
bit — which looks exactly like a search that never completes.
"""
import collections, os, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl, probe_sides, cas_decode
tmp = tempfile.mkdtemp(prefix="wavhist_")
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
    hist = collections.Counter(h for h in hp if h <= 40)
    print("=== %-7s half-period histogram (samples -> count), excluding gaps" % side)
    for dur in sorted(hist):
        print("      %3d samples (%5d Hz) : %6d" % (dur, fr / (2 * dur), hist[dur]))
    sys.stdout.flush()
