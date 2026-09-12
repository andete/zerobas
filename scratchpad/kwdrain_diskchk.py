import sys, re
sys.path.insert(0, "/Users/joost/projects/zerobas/probes/lib")
import omsx_repl, probe_sides
sides = probe_sides.sides("zb")
cfg = sides["zb"]
cases = [
    ("dskf.0",   'PRINT"[";DSKF(0);"]"'),
    ("dskf.stub",'PRINT"[";ZDF(0);"]"'),
    ("lof.bare", 'PRINT"[";LOF(1);"]"'),
    ("loc.bare", 'PRINT"[";LOC(1);"]"'),
    ("eof.bare", 'PRINT"[";EOF(1);"]"'),
    ("close.ok", 'CLOSE:PRINT"[C9]"'),
]
caps = omsx_repl.run_cases(cfg["machine"], [("direct", [e]) for _, e in cases],
                           batch=False, reset=(), boot=cfg["boot"],
                           step=10.0, cap_gap=90.0, timeout=600.0)
for (tag, _), cap in zip(cases, caps):
    txt = re.sub(r"\s+", " ", cap if isinstance(cap, str) else str(cap))
    m = re.findall(r"\[\s*(-?\d+|C9)\s*\]", txt)
    e = re.search(r"(Bad file number|Illegal function call|Syntax error|File not open|[A-Za-z ]*error)", txt)
    print("%-10s %-6s %s" % (tag, m[-1] if m else "NONE", e.group(1).strip()[:22] if e else ""))
