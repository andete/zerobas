import sys, re
sys.path.insert(0, "/Users/joost/projects/zerobas/probes/lib")
import omsx_repl, probe_sides
cfg = probe_sides.sides("zb")["zb"]
cases = [
    ("width.default", ['PRINT"[W";PEEK(-3152);"]"']),
    ("width.after",   ['WIDTH 37:PRINT"[W";PEEK(-3152);"]"']),
    ("color.default", ['PRINT"[O";PEEK(-3095);"]"']),
    ("color.after",   ['COLOR 7:PRINT"[O";PEEK(-3095);"]"']),
    ("cls.default",   ['PRINT:PRINT"[C";CSRLIN;"]"']),
    ("cls.after",     ['PRINT:CLS:PRINT"[C";CSRLIN;"]"']),
]
caps = omsx_repl.run_cases(cfg["machine"], cases, batch=False, reset=(),
                           boot=cfg["boot"], step=10.0, cap_gap=90.0, timeout=600.0)
for (tag, _), cap in zip(cases, caps):
    txt = re.sub(r"\s+", " ", cap if isinstance(cap, str) else str(cap))
    m = re.findall(r"\[[WOC]\s*(-?\d+)\s*\]", txt)
    print("%-14s %s" % (tag, m[-1] if m else "NONE"))
