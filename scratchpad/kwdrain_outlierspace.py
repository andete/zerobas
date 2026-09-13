#!/usr/bin/env python3
"""The symmetric merge-point loop did NOT clear the residual (~46 outliers, and the
load still does not complete). One hypothesis fits the COUNT: the 8th data bit of
every byte leaves the loop (`djnz` not taken) instead of going round it, so its
tail is a different shape from the other seven — and ~37 bytes on this tape means
~37 such bits, close to what is left.

If that is right the outliers are periodic at the BYTE rate, not scattered. This
measures their spacing in bits rather than guessing from the count.
"""
import os, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl, probe_sides, cas_decode
tmp = tempfile.mkdtemp(prefix="ospace_")
wav = os.path.join(tmp, "t.wav")
cfg = probe_sides.sides("zb")["zb"]
omsx_repl.run_cases(cfg["machine"],
                    [("d", list(cfg["reset"]) + ['10 PRINT"[Z9]"', 'CSAVE"ZQ"', '@WAIT30'])],
                    batch=False, reset=(), boot=cfg["boot"], step=5.0,
                    cap_gap=150.0, timeout=1200.0,
                    prologue=(f"cassetteplayer new {{{wav}}}",))
s, fr = cas_decode.read_samples(wav)
hp = cas_decode.half_periods(cas_decode.zero_crossings(s))
thr = cas_decode.auto_threshold(hp)
# skip the opening leader
i = 0
while i < len(hp) and hp[i] <= thr:
    i += 1
out = [j for j in range(i, len(hp)) if 11 <= hp[j] <= 17]
print("outliers after the first leader: %d" % len(out))
print("first 20 indices: %s" % out[:20])
gaps = [b - a for a, b in zip(out, out[1:])]
import collections
print("gap histogram (half-periods between consecutive outliers):")
for g, n in collections.Counter(gaps).most_common(8):
    print("      gap %4d : %3d times" % (g, n))
