import sys, re
sys.path.insert(0, "/Users/joost/projects/zerobas/probes/lib")
import omsx_repl, probe_sides
sides = probe_sides.sides("zb", "vg8020")
direct = [
    ("pad.9",     'PRINT"[";PAD(9);"]"'),
    ("pad.stub",  'PRINT"[";ZPA(9);"]"'),
    ("pdl.13",    'PRINT"[";PDL(13);"]"'),
    ("pdl.stub",  'PRINT"[";ZPB(13);"]"'),
    ("attr.bare", 'PRINT"[";ATTR$;"]"'),
    ("attr.stub", 'PRINT"[";ZAT$;"]"'),
]
stored = [
    ("stop.prog", 'PRINT"[T1]":STOP'),
    ("new.prog",  'PRINT"[N1]":NEW'),
]
cases = [(t, ("direct", [e])) for t, e in direct] + \
        [(t, ("stored", omsx_repl.as_stored(e))) for t, e in stored]
for name in ("zb", "vg8020"):
    cfg = sides[name]
    caps = omsx_repl.run_cases(cfg["machine"], [s for _, s in cases], batch=False,
                               reset=("NEW", "CLS"), boot=cfg["boot"],
                               step=10.0, cap_gap=90.0, timeout=600.0)
    out = []
    for (tag, _), cap in zip(cases, caps):
        txt = re.sub(r"\s+", " ", cap if isinstance(cap, str) else str(cap))
        mk = re.search(r"\[(T1|N1)\]", txt)
        m = re.findall(r"\[\s*(-?\d+)\s*\]", txt)
        e = re.search(r"(Illegal function call|Syntax error|[Bb]reak in \d+|[Bb]reak)", txt)
        v = mk.group(1) if mk else (m[-1] if m else "NONE")
        out.append("%s=%s%s" % (tag, v, "/" + e.group(1)[:14] if e else ""))
    print("%-7s %s" % (name, "  ".join(out)))
