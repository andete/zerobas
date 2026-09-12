import sys, re
sys.path.insert(0, "/Users/joost/projects/zerobas/probes/lib")
import omsx_repl, probe_sides

sides = probe_sides.sides("zb", "vg8020")
def prog(n):
    return ["10 FOR I=1 TO %d" % n, "20 GOSUB 100", "30 NEXT",
            "40 PRINT\"[\";I;\"]\"", "50 END", "100 RETURN", "RUN"]

for name in ("zb", "vg8020"):
    cfg = sides[name]
    cases = [("n%d" % n, prog(n)) for n in (50, 200, 400, 800)]
    caps = omsx_repl.run_cases(cfg["machine"], cases, batch=False, reset=(),
                               boot=cfg["boot"], step=5.0, cap_gap=45.0, timeout=600.0)
    for (tag, _), cap in zip(cases, caps):
        txt = cap if isinstance(cap, str) else str(cap)
        m = re.search(r"\[\s*([0-9]+)\s*\]", txt)
        err = re.search(r"([A-Za-z ]*error[A-Za-z ]*)", txt)
        print("%-7s %-5s -> %s   %s" % (name, tag,
              ("[%s]" % m.group(1)) if m else "NO OUTPUT",
              (err.group(1).strip() if err else "")))
