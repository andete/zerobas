#!/usr/bin/env python3
"""🔴 A TAPE ZEROBAS RECORDED IS UNREADABLE BY THE VG-8020, while zerobas reads it
back perfectly and the VG reads a clean-room `.cas` of the SAME program. If that
holds up it is not an apparatus fact — it is a faithfulness defect: a tape saved
on zerobas cannot be loaded on a real MSX.

Before believing it, the two cheap alternative explanations:
  * SLOW, not silent  -- a much longer capture window
  * HUNG, not silent  -- does the machine reach a prompt afterwards? A row that
    ends at `Ok` completed and found nothing; one that never prompts is stuck.
Full screens, not tails, so the difference is visible rather than inferred.
"""
import os, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
sys.path.insert(0, os.path.join(ROOT, "probes", "disk"))
import omsx_repl, probe_sides, cas_encode
from bas_tokenise import make_multiline_program

tmp = tempfile.mkdtemp(prefix="wavread_")
cas = os.path.join(tmp, "zq.cas")
open(cas, "wb").write(
    cas_encode.build_cas_basic("ZQ", make_multiline_program([(10, 'PRINT"[Z9]"')], 0x8001)))
wav = os.path.join(tmp, "zbwrote.wav")

def run(side, lines, gap=90.0, **kw):
    cfg = probe_sides.sides(side)[side]
    caps = omsx_repl.run_cases(cfg["machine"], [("d", list(cfg["reset"]) + lines)],
                               batch=False, reset=(), boot=cfg["boot"],
                               step=5.0, cap_gap=gap, timeout=1200.0, **kw)
    cap = caps[0]
    rows = [cap[r*40:(r+1)*40].rstrip() for r in range(24)] if cap else []
    return [r.strip() for r in rows if r.strip()]

cfg = probe_sides.sides("zb")["zb"]
run("zb", ['10 PRINT"[Z9]"', 'CSAVE"ZQ"', '@WAIT30'],
    prologue=(f"cassetteplayer new {{{wav}}}",))
print("zerobas-written WAV: %d bytes" % os.path.getsize(wav))

# `PRINT"[P9]"` AFTER the load is the prompt witness: it only appears if CLOAD
# came back at all, so "hung" and "completed, found nothing" stop looking alike.
for label, side, tape, gap in (
        ("vg8020 .cas  (control)", "vg8020", cas, 90.0),
        ("vg8020 WAV   gap 90",    "vg8020", wav, 90.0),
        ("vg8020 WAV   gap 300",   "vg8020", wav, 300.0),
        ("zb     WAV   (control)", "zb",     wav, 90.0),
):
    rows = run(side, ["NEW", 'CLOAD"ZQ"', 'PRINT"[P9]"'], gap=gap, cassette=tape)
    print("%-24s %s" % (label, " | ".join(rows[-5:])))
    sys.stdout.flush()
