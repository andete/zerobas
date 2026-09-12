import sys, re
sys.path.insert(0, "/Users/joost/projects/zerobas/probes/lib")
import omsx_repl, probe_sides
sides = probe_sides.sides("zb", "vg8020", "cf3300")
stored = [
    ("new.tail",   'PRINT"[N1]":NEW'),
    ("new.alone",  'NEW'),
    ("new.then",   'PRINT"[N2]":NEW:PRINT"[N3]"'),
    ("clear.ctl",  'PRINT"[N4]":CLEAR'),
]
cases = [(t, ("stored", omsx_repl.as_stored(e))) for t, e in stored]
for name in ("zb", "vg8020", "cf3300"):
    if name not in sides: continue
    cfg = sides[name]
    caps = omsx_repl.run_cases(cfg["machine"], [s for _, s in cases], batch=False,
                               reset=("NEW", "CLS"), boot=cfg["boot"],
                               step=10.0, cap_gap=90.0, timeout=600.0)
    for (tag, _), cap in zip(cases, caps):
        txt = re.sub(r"\s+", " ", cap if isinstance(cap, str) else str(cap))
        print("%-7s %-10s %s" % (name, tag, txt[-70:]))
