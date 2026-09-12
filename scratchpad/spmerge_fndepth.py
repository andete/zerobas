import sys, re
sys.path.insert(0, "/Users/joost/projects/zerobas/probes/lib")
import omsx_repl, probe_sides
sides = probe_sides.sides("zb", "vg8020")
def nest(d):
    # FNA(FNA(...FNA(1)...)) at depth d
    return "10 DEF FNA(X)=X+1", "20 PRINT\"[\";" + "FNA(" * d + "1" + ")" * d + ";\"]\""
cases = []
for d in (8, 10, 12, 16, 24):
    a, b = nest(d)
    cases.append(("d%d" % d, [a, b, "RUN"]))
for name in ("zb", "vg8020"):
    cfg = sides[name]
    caps = omsx_repl.run_cases(cfg["machine"], cases, batch=False, reset=(),
                               boot=cfg["boot"], step=10.0, cap_gap=90.0, timeout=600.0)
    out = []
    for (tag, _), cap in zip(cases, caps):
        txt = re.sub(r"\s+", " ", cap if isinstance(cap, str) else str(cap))
        m = re.search(r"\[\s*(-?[0-9]+)\s*\]", txt)
        e = re.search(r"(Out of memory|[A-Za-z ]*error)", txt)
        out.append("%s=%s" % (tag, m.group(1) if m else ("ERR:" + e.group(1).strip() if e else "NONE")))
    print("%-7s %s" % (name, "  ".join(out)))
