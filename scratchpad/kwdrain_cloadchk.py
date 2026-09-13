#!/usr/bin/env python3
"""D-KWCLOAD: is there a SCREEN-visible readback for `CLOAD` after all?

The rig exists (I wrongly filed that it did not): `cas_encode.build_cas_basic`
synthesises a playable `.cas`, and openMSX mounts one. What was said to block the
verb is the readback — CLOAD replaces the program and returns to command level,
so nothing in the same case observes it.

⚠️ ONE THING THAT CLAIM NEVER CHECKED: MSX BASIC PRINTS WHILE IT SEARCHES A TAPE.
If `Found:NAME` reaches the screen, the readback is right there and needs no new
capture at all. Asked here before either route is built.

`CLOAD` is a MAIN-ROM cassette verb, so the VG-8020 is its oracle — no disk.
"""
import os, re, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
sys.path.insert(0, os.path.join(ROOT, "probes", "disk"))
import omsx_repl, probe_sides, cas_encode
from bas_tokenise import make_multiline_program

TXTBASE = 0x8001
prog = make_multiline_program([(10, 'PRINT"[Z9]"')], TXTBASE)
cas = os.path.join(tempfile.mkdtemp(prefix="kwcload_"), "zq.cas")
open(cas, "wb").write(cas_encode.build_cas_basic("ZQ", prog))
print("fixture: %s (%d bytes), program = 10 PRINT\"[Z9]\"" % (cas, os.path.getsize(cas)))

CASES = [
    ("cload.named", 'CLOAD"ZQ"'),
    ("cload.bare",  'CLOAD'),
    ("ctl.noverb",  'PRINT"[N9]"'),
]
for name in (sys.argv[1:] or ["zb", "vg8020"]):
    cfg = probe_sides.sides(name)[name]
    specs = [("stored", omsx_repl.as_stored(l)) for _, l in CASES]
    caps = omsx_repl.run_cases(cfg["machine"], specs, batch=True,
                               reset=cfg["reset"] + ("NEW", "CLS"),
                               boot=cfg["boot"], step=5.0, cap_gap=30.0,
                               timeout=900.0,
                               prologue=(f"cassetteplayer {{{cas}}}",))
    print("=== %s" % name)
    for (tag, l), cap in zip(CASES, caps):
        rows = [cap[r*40:(r+1)*40].rstrip() for r in range(24)] if cap else []
        shown = " | ".join(r.strip() for r in rows if r.strip())[-110:]
        print("  %-11s tail=%-22r screen=%s"
              % (tag, omsx_repl.screen_tail(cap, "RUN"), shown))
    sys.stdout.flush()
