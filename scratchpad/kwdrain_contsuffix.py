import sys, re
sys.path.insert(0, "/Users/joost/projects/zerobas/probes/lib")
import omsx_repl, probe_sides
sides = probe_sides.sides("zb", "vg8020")
cases = [
    ("direct.cont",  ("direct", ['CONT'])),                 # at the prompt: no line exists
    ("prog.cont",    ("stored", omsx_repl.as_stored('PRINT"[A]":CONT'))),
    ("prog.ifc",     ("stored", omsx_repl.as_stored('PRINT"[A]":DELETE 99'))),  # control
]
for name in ("zb", "vg8020"):
    cfg = sides[name]
    caps = omsx_repl.run_cases(cfg["machine"], [s for _, s in cases], batch=False,
                               reset=("NEW", "CLS"), boot=cfg["boot"],
                               step=10.0, cap_gap=90.0, timeout=600.0)
    for (tag, _), cap in zip(cases, caps):
        txt = re.sub(r"\s+", " ", cap if isinstance(cap, str) else str(cap))
        m = re.search(r"(Can't CONTINUE[^A-Z]*|Illegal function call[^A-Z]*)", txt)
        print("%-7s %-12s %r" % (name, tag, m.group(1).strip() if m else txt[-40:]))
