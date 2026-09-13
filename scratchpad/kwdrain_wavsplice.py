#!/usr/bin/env python3
"""THE DECISIVE EXPERIMENT, and it needs no rebuild.

The reference's tape carries ONE 1.12 s SILENCE at the block boundary; zerobas's
carries none (max half-period 20 samples). If that gap is what a real BIOS needs to
re-lock, then splicing silence into ZEROBAS'S OWN recording — changing nothing
else — must make the VG-8020 read it.

  arm 1  zerobas's tape, untouched          -> expected HANG (known)
  arm 2  the same tape + 1.1 s of silence   -> if it READS, the gap is the defect

`PRINT"[P9]"` after the CLOAD is the prompt witness: without it a hang and a silent
completion look the same.
"""
import os, struct, sys, tempfile, wave
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl, probe_sides, cas_decode

tmp = tempfile.mkdtemp(prefix="splice_")
cfg = probe_sides.sides("zb")["zb"]
wav = os.path.join(tmp, "zb.wav")
omsx_repl.run_cases(cfg["machine"],
                    [("d", list(cfg["reset"]) + ['10 PRINT"[Z9]"', 'CSAVE"ZQ"', '@WAIT30'])],
                    batch=False, reset=(), boot=cfg["boot"], step=5.0,
                    cap_gap=150.0, timeout=1200.0,
                    prologue=(f"cassetteplayer new {{{wav}}}",))

# locate the SECOND leader run: the data block's leader. The gap belongs just
# before it, which is where the reference's own silence sits.
s, fr = cas_decode.read_samples(wav)
xs = cas_decode.zero_crossings(s)
hp = cas_decode.half_periods(xs)
thr = cas_decode.auto_threshold(hp)
runs, cur, n, start = [], hp[0] <= thr, 0, 0
for i, h in enumerate(hp):
    short = h <= thr
    if short == cur:
        n += 1
    else:
        runs.append((cur, n, start)); cur, n, start = short, 1, i
runs.append((cur, n, start))
leaders = [r for r in runs if r[0] and r[1] > 200]
print("leader runs (kind short, count, first half-period index): %s" % (leaders,))
boundary_hp = leaders[1][2]                      # start of the data block's leader
boundary_sample = xs[boundary_hp]
print("splice point: half-period %d -> sample %d of %d (%.2fs)"
      % (boundary_hp, boundary_sample, len(s), boundary_sample / fr))

with wave.open(wav, "rb") as w:
    params, raw = w.getparams(), w.readframes(w.getnframes())
sw, ch = params.sampwidth, params.nchannels
off = boundary_sample * sw * ch
silence = (b"\x80" if sw == 1 else b"\x00\x00") * int(1.1 * fr) * ch
out = os.path.join(tmp, "zb_gapped.wav")
with wave.open(out, "wb") as w:
    w.setparams(params)
    w.writeframes(raw[:off] + silence + raw[off:])
print("spliced tape: %d bytes (was %d)" % (os.path.getsize(out), os.path.getsize(wav)))

def read_on_vg(tape):
    c = probe_sides.sides("vg8020")["vg8020"]
    caps = omsx_repl.run_cases(c["machine"],
                               [("d", list(c["reset"]) + ["NEW", 'CLOAD"ZQ"', 'PRINT"[P9]"'])],
                               batch=False, reset=(), boot=c["boot"], step=5.0,
                               cap_gap=200.0, timeout=1800.0, cassette=tape)
    cap = caps[0]
    rows = [cap[r*40:(r+1)*40].rstrip() for r in range(24)] if cap else []
    return " | ".join(r.strip() for r in rows if r.strip())[-58:]

print("arm 1  zerobas tape, untouched : %s" % read_on_vg(wav))
print("arm 2  + 1.1 s silence spliced : %s" % read_on_vg(out))
