import sys, re
sys.path.insert(0, "/Users/joost/projects/zerobas/probes/lib")
import omsx_repl, probe_sides
sides = probe_sides.sides("zb", "vg8020")
cases = [
    ("pdl.0",     ("direct", ['PRINT"[";PDL(0);"]"'])),
    ("pdl.stub0", ("direct", ['PRINT"[";ZPC(0);"]"'])),
    ("pdl.1",     ("direct", ['PRINT"[";PDL(1);"]"'])),
]
for name in ("zb", "vg8020"):
    cfg = sides[name]
    caps = omsx_repl.run_cases(cfg["machine"], [s for _, s in cases], batch=False,
                               reset=(), boot=cfg["boot"], step=10.0, cap_gap=90.0,
                               timeout=600.0)
    out = []
    for (tag, _), cap in zip(cases, caps):
        txt = re.sub(r"\s+", " ", cap if isinstance(cap, str) else str(cap))
        m = re.findall(r"\[\s*(-?\d+)\s*\]", txt)
        e = re.search(r"(Illegal function call|Syntax error|Subscript out of range)", txt)
        out.append("%s=%s%s" % (tag, m[-1] if m else "NONE", "/" + e.group(1)[:14] if e else ""))
    print("%-7s %s" % (name, "  ".join(out)))
