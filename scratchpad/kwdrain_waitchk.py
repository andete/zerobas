#!/usr/bin/env python3
"""Does `WAIT` return? Batch 3's row blocked FOR EVER because `WAIT p,0` can
never be satisfied, and a blocking row takes every case after it down with it.
So the mask is chosen from a MEASURED port value (INP(&HA8) = 240 and
INP(&HA9) = 255 on both machines, scratchpad/kwdrain_misc3.out) and proved to
return HERE, alone, before any row exists.

The control is the point: `wait.0` is batch 3's own mask-0 form, which MUST NOT
return -- if it does, the port is not what this reasoning assumes."""
import os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl, probe_sides
CASES = [
    ("wait.a8ff", 'WAIT &HA8,&HFF:PRINT"[X1]"'),
    ("wait.a9ff", 'WAIT &HA9,&HFF:PRINT"[X2]"'),
    ("wait.0",    'WAIT &HA8,0:PRINT"[X3]"'),      # the control: must NOT return
]
for name in (sys.argv[1:] or ["zb"]):
    cfg = probe_sides.sides(name)[name]
    specs = [("stored", omsx_repl.as_stored(l)) for _, l in CASES]
    caps = omsx_repl.run_cases(cfg["machine"], specs, batch=True,
                               reset=cfg["reset"] + ("NEW", "CLS"),
                               boot=cfg["boot"], step=3.5, cap_gap=12.0,
                               timeout=600.0)
    print("=== %s" % name)
    for (tag, l), cap in zip(CASES, caps):
        txt = re.sub(r"\s+", " ", cap if isinstance(cap, str) else str(cap))
        m = re.findall(r"\[X(\d)\]", txt)
        print("  %-10s %-6s | %s" % (tag, m[-1] if m else "NONE", txt[-90:]))
    sys.stdout.flush()
