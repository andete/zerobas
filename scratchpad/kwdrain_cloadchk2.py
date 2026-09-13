#!/usr/bin/env python3
"""Round 2. Round 1 found the readback — `Found:ZQ` reaches the SCREEN, so CLOAD
needs no new capture — and then found a second thing: the VG-8020 run was
UNUSABLE. All three cases showed the same stale screen INCLUDING THE CONTROL,
which is the tell that the run and not the verb had failed.

🔴 THE TAPE POSITION IS STATE THAT SURVIVES A CASE. On zerobas the second CLOAD
answered `load error` because the FIRST one had already consumed the tape. That is
the `AUTO` lesson in a different costume, so: BOOT-PER-CASE, a fresh tape per case.
"""
import os, re, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
sys.path.insert(0, os.path.join(ROOT, "probes", "disk"))
import omsx_repl, probe_sides, cas_encode
from bas_tokenise import make_multiline_program

TXTBASE = 0x8001
prog = make_multiline_program([(10, 'PRINT"[Z9]"')], TXTBASE)
tmp = tempfile.mkdtemp(prefix="kwcload2_")

CASES = [
    ("cload.named", 'CLOAD"ZQ"'),
    ("ctl.noverb",  'PRINT"[N9]"'),
]
for name in (sys.argv[1:] or ["zb", "vg8020"]):
    cfg = probe_sides.sides(name)[name]
    print("=== %s" % name)
    for tag, line in CASES:
        cas = os.path.join(tmp, f"{name}_{tag}.cas")
        open(cas, "wb").write(cas_encode.build_cas_basic("ZQ", prog))
        caps = omsx_repl.run_cases(cfg["machine"],
                                   [("stored", omsx_repl.as_stored(line))],
                                   batch=False, reset=cfg["reset"],
                                   boot=cfg["boot"], step=5.0, cap_gap=30.0,
                                   timeout=900.0,
                                   prologue=(f"cassetteplayer {{{cas}}}",))
        cap = caps[0]
        rows = [cap[r*40:(r+1)*40].rstrip() for r in range(24)] if cap else []
        shown = " | ".join(r.strip() for r in rows if r.strip())[-100:]
        print("  %-11s tail=%-14r screen=%s"
              % (tag, omsx_repl.screen_tail(cap, "RUN"), shown))
        sys.stdout.flush()
