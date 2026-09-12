import sys, re
sys.path.insert(0, "/Users/joost/projects/zerobas/probes/lib")
import omsx_repl, probe_sides
sides = probe_sides.sides("zb", "vg8020")
cases = [("default", ['PRINT"[D";PEEK(-3151);"]"']),
         ("keyoff",  ['KEY OFF:PRINT"[Y";PEEK(-3151);"]"'])]
for name in ("zb", "vg8020"):
    cfg = sides[name]
    caps = omsx_repl.run_cases(cfg["machine"], cases, batch=False, reset=(),
                               boot=cfg["boot"], step=10.0, cap_gap=90.0, timeout=600.0)
    vals = []
    for (tag, _), cap in zip(cases, caps):
        txt = re.sub(r"\s+", " ", cap if isinstance(cap, str) else str(cap))
        m = re.findall(r"\[[DY]\s*(-?\d+)\s*\]", txt)
        vals.append("%s=%s" % (tag, m[-1] if m else "NONE"))
    print("%-7s %s" % (name, "  ".join(vals)))
