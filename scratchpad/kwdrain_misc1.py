import sys, re
sys.path.insert(0, "/Users/joost/projects/zerobas/probes/lib")
import omsx_repl, probe_sides
sides = probe_sides.sides("zb", "vg8020")
cases = [
    ("max.bare",   ['PRINT"[";MAX;"]"']),
    ("max.stub",   ['PRINT"[";ZQX;"]"']),
    ("lpos.plain", ['PRINT"[";LPOS(0);"]"']),
    ("lprint.pos", ['LPRINT"AB";:PRINT"[";LPOS(0);"]"']),
    ("strig.5",    ['PRINT"[";STRIG(5);"]"']),
    ("strig.stub", ['PRINT"[";ZQY(5);"]"']),
    ("inkey.len",  ['PRINT"[";LEN(INKEY$);"]"']),
]
for name in ("zb", "vg8020"):
    cfg = sides[name]
    caps = omsx_repl.run_cases(cfg["machine"], cases, batch=False, reset=(),
                               boot=cfg["boot"], step=10.0, cap_gap=90.0, timeout=600.0)
    out = []
    for (tag, _), cap in zip(cases, caps):
        txt = re.sub(r"\s+", " ", cap if isinstance(cap, str) else str(cap))
        m = re.findall(r"\[\s*(-?\d+)\s*\]", txt)
        e = re.search(r"(Illegal function call|Syntax error|[A-Za-z ]*error)", txt)
        out.append("%s=%s%s" % (tag, m[-1] if m else "NONE",
                                "/" + e.group(1).strip()[:12] if e and not m else ""))
    print("%-7s %s" % (name, "  ".join(out)))
