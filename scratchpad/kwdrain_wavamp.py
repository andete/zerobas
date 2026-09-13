#!/usr/bin/env python3
"""Two hypotheses refuted by measurement: leader LENGTH (16 000 cycles, a WAV the
same size as the reference's — still hangs) and the missing inter-block SILENCE
(spliced into zerobas's own tape — still hangs). And the VG never prints `Found:`,
so it is failing on the HEADER block, before either could matter.

Tone frequency and data framing already match. What has NOT been compared is the
signal itself — amplitude, shape, DC level. cas_decode works from zero crossings,
which are blind to all three.
"""
import os, sys, tempfile, wave
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl, probe_sides
tmp = tempfile.mkdtemp(prefix="wavamp_")
for side in ("vg8020", "zb"):
    cfg = probe_sides.sides(side)[side]
    wav = os.path.join(tmp, f"{side}.wav")
    omsx_repl.run_cases(cfg["machine"],
                        [("d", list(cfg["reset"]) + ['10 PRINT"[Z9]"', 'CSAVE"ZQ"', '@WAIT30'])],
                        batch=False, reset=(), boot=cfg["boot"], step=5.0,
                        cap_gap=150.0, timeout=1200.0,
                        prologue=(f"cassetteplayer new {{{wav}}}",))
    with wave.open(wav, "rb") as w:
        p = w.getparams()
        raw = w.readframes(w.getnframes())
    print("=== %-7s channels=%d sampwidth=%d rate=%d frames=%d"
          % (side, p.nchannels, p.sampwidth, p.framerate, p.nframes))
    if p.sampwidth == 1:
        vals = list(raw)
    else:
        import array
        a = array.array("h"); a.frombytes(raw); vals = list(a)
    print("    min=%d max=%d  distinct values=%d" % (min(vals), max(vals), len(set(vals))))
    print("    first 40 samples: %s" % vals[:40])
    sys.stdout.flush()
