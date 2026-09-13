#!/usr/bin/env python3
"""Chain so far: HANG -> `Skip : @ @@` -> `Skip : Q @` -> **`Found:ZQ`**. The
reference now decodes the HEADER block's name correctly and still does not finish
the load, so the DATA block is where it fails.

54 half-periods still land between the tones. This says WHERE they are relative to
the tape's structure — leader, header data, inter-block, or data block — because
"how many" has stopped being the useful question.
"""
import os, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl, probe_sides, cas_decode
tmp = tempfile.mkdtemp(prefix="outpos_")
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

# the tape's landmarks: the two leader runs
runs, cur, n, start = [], hp[0] <= thr, 0, 0
for i, h in enumerate(hp):
    short = h <= thr
    if short == cur:
        n += 1
    else:
        runs.append((cur, n, start)); cur, n, start = short, 1, i
runs.append((cur, n, start))
leaders = [(cnt, st) for sh, cnt, st in runs if sh and cnt > 200]
print("leaders (count, start index): %s" % leaders)
hdr_start = leaders[0][1] + leaders[0][0]
dat_lead, dat_start = leaders[1][1], leaders[1][1] + leaders[1][0]
print("header data: %d..%d | inter-block leader at %d | data block from %d"
      % (hdr_start, dat_lead, dat_lead, dat_start))

out = [(i, h) for i, h in enumerate(hp) if 11 <= h <= 17]
def where(i):
    if i < hdr_start: return "leader1"
    if i < dat_lead:  return "HEADER-data"
    if i < dat_start: return "leader2"
    return "DATA-block"
import collections
print("between-tone outliers: %d total, by region: %s"
      % (len(out), collections.Counter(where(i) for i, _ in out)))
print("first 12: %s" % [(i, h, where(i)) for i, h in out[:12]])
