#!/usr/bin/env python3
"""The fixture is exonerated (kwdrain_casoracle.out): a tape zerobas WROTE and
re-read itself is equally unreadable to the VG-8020. That leaves "the reference's
tape path", which is broad. One run narrows it:

  is it the TAPE PATH, or is it `CLOAD` specifically?

`LOAD"CAS:ZQ"` reads the same tape through a different verb. If both fail, the
machine's tape path is dead in this rig and the answer is apparatus. If LOAD works
and CLOAD does not, that is a finding about the REFERENCE's CLOAD and worth far
more than the keyword.
"""
import os, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl, probe_sides
tmp = tempfile.mkdtemp(prefix="kwcasor2_")
wav = os.path.join(tmp, "zbwrote.wav")

def run(side, lines, prologue, gap=90.0):
    cfg = probe_sides.sides(side)[side]
    caps = omsx_repl.run_cases(cfg["machine"], [("d", list(cfg["reset"]) + lines)],
                               batch=False, reset=(), boot=cfg["boot"],
                               step=5.0, cap_gap=gap, timeout=900.0,
                               prologue=prologue)
    cap = caps[0]
    rows = [cap[r*40:(r+1)*40].rstrip() for r in range(24)] if cap else []
    return " | ".join(r.strip() for r in rows if r.strip())

run("zb", ['10 PRINT"[Z9]"', 'CSAVE"ZQ"', '@WAIT30', 'PRINT"[W9]"'],
    (f"cassetteplayer new {{{wav}}}",))
print("tape written: %d bytes" % (os.path.getsize(wav) if os.path.exists(wav) else -1))
for side, lines, label in (
        ("vg8020", ['NEW', 'LOAD"CAS:ZQ"'],  "vg8020 LOAD\"CAS:ZQ\""),
        ("vg8020", ['NEW', 'CLOAD"ZQ"'],     "vg8020 CLOAD\"ZQ\"  (known-failing)"),
        ("zb",     ['NEW', 'LOAD"CAS:ZQ"'],  "zb     LOAD\"CAS:ZQ\" (control)"),
):
    print("%-34s %s" % (label, run(side, lines, (f"cassetteplayer {{{wav}}}",))[-85:]))
    sys.stdout.flush()
