#!/usr/bin/env python3
"""🔴 THE REFERENCE'S TAPE BEGINS WITH SILENCE AND ZEROBAS'S DOES NOT — visible in
the SAMPLES (VG: first 40 all 128, the DC centre; zerobas: carrier from sample 2)
and INVISIBLE in the zero-crossing view that every earlier arm used, which is why
three hypotheses were chased first.

tape/PROVENANCE.md already knows this shape from the other side: CAS_FLATMAX is
sized to cover "openMSX's ~2 s LONG_SILENCE pre-leader gap" — i.e. our READER
expects leading silence, and openMSX's `.cas` playback supplies it. Nothing ever
asked whether our WRITER emits one.

Splice silence onto the FRONT of zerobas's own tape and ask the reference.
"""
import os, sys, tempfile, wave
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl, probe_sides
tmp = tempfile.mkdtemp(prefix="lead2_")

def record(side):
    cfg = probe_sides.sides(side)[side]
    w = os.path.join(tmp, f"{side}.wav")
    omsx_repl.run_cases(cfg["machine"],
                        [("d", list(cfg["reset"]) + ['10 PRINT"[Z9]"', 'CSAVE"ZQ"', '@WAIT30'])],
                        batch=False, reset=(), boot=cfg["boot"], step=5.0,
                        cap_gap=150.0, timeout=1200.0,
                        prologue=(f"cassetteplayer new {{{w}}}",))
    return w

def lead_silence(path):
    with wave.open(path, "rb") as w:
        fr, raw = w.getframerate(), w.readframes(w.getnframes())
    n = 0
    for v in raw:
        if v != 128:
            break
        n += 1
    return n, n / fr

vg = record("vg8020")
zb = record("zb")
for lab, p in (("vg8020", vg), ("zb", zb)):
    n, secs = lead_silence(p)
    print("%-7s leading silence: %d samples (%.3f s)" % (lab, n, secs))

with wave.open(zb, "rb") as w:
    params, raw = w.getparams(), w.readframes(w.getnframes())
out = os.path.join(tmp, "zb_lead.wav")
pad = b"\x80" * int(2.0 * params.framerate)
with wave.open(out, "wb") as w:
    w.setparams(params); w.writeframes(pad + raw)
print("spliced 2.0 s of leading silence: %d bytes (was %d)"
      % (os.path.getsize(out), os.path.getsize(zb)))

def read_on_vg(tape):
    c = probe_sides.sides("vg8020")["vg8020"]
    caps = omsx_repl.run_cases(c["machine"],
                               [("d", list(c["reset"]) + ["NEW", 'CLOAD"ZQ"', 'PRINT"[P9]"'])],
                               batch=False, reset=(), boot=c["boot"], step=5.0,
                               cap_gap=200.0, timeout=1800.0, cassette=tape)
    cap = caps[0]
    rows = [cap[r*40:(r+1)*40].rstrip() for r in range(24)] if cap else []
    return " | ".join(r.strip() for r in rows if r.strip())[-56:]

print("arm 1  zerobas tape, untouched   : %s" % read_on_vg(zb))
print("arm 2  + 2 s LEADING silence     : %s" % read_on_vg(out))
