import sys, re
sys.path.insert(0, "/Users/joost/projects/zerobas/probes/lib")
import omsx_repl, probe_sides
sides = probe_sides.sides("zb", "vg8020")
execs = {
  "onerr":  'ON ERROR GOTO 20:ERROR 7:END:PRINT"[R";ERR;ERL;"]":END',
  "resume": 'ON ERROR GOTO 30:ERROR 7:PRINT"[U";A;"]":END:A=5:RESUME NEXT',
  "defint": 'DEFINT A:A=1.7:PRINT"[";A;"]"',
}
cases = [(k, omsx_repl.as_stored(v)) for k, v in execs.items()]
for name in ("zb", "vg8020"):
    cfg = sides[name]
    caps = omsx_repl.run_cases(cfg["machine"], [("stored", b) for _, b in cases],
                               batch=False, reset=("NEW", "CLS"), boot=cfg["boot"],
                               step=10.0, cap_gap=90.0, timeout=600.0)
    out = []
    for (tag, _), cap in zip(cases, caps):
        txt = re.sub(r"\s+", " ", cap if isinstance(cap, str) else str(cap))
        m = re.findall(r"\[[RU]?\s*(-?\d+(?:\s+-?\d+)?)\s*\]", txt)
        out.append("%s=%s" % (tag, m[-1].strip() if m else "NONE"))
    print("%-7s %s" % (name, " | ".join(out)))
