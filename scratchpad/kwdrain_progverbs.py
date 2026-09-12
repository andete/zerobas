import sys, re
sys.path.insert(0, "/Users/joost/projects/zerobas/probes/lib")
import omsx_repl, probe_sides
sides = probe_sides.sides("zb", "vg8020")
# each: a stored program whose SECOND statement is the verb under test
execs = {
  "list":   'PRINT"[A]":LIST',
  "llist":  'PRINT"[A]":LLIST',
  "delete": 'PRINT"[A]":DELETE 99',
  "renum":  'PRINT"[A]":RENUM',
  "auto":   'PRINT"[A]":AUTO',
  "cont":   'PRINT"[A]":CONT',
  "run":    'PRINT"[A]":END',        # control: END in the same slot
}
cases = [(k, ("stored", omsx_repl.as_stored(v))) for k, v in execs.items()]
for name in ("zb", "vg8020"):
    cfg = sides[name]
    caps = omsx_repl.run_cases(cfg["machine"], [s for _, s in cases], batch=False,
                               reset=("NEW", "CLS"), boot=cfg["boot"],
                               step=10.0, cap_gap=90.0, timeout=600.0)
    for (tag, _), cap in zip(cases, caps):
        txt = re.sub(r"\s+", " ", cap if isinstance(cap, str) else str(cap))
        e = re.search(r"([A-Za-z ]*error[A-Za-z ]*|Illegal function call)", txt)
        print("%-7s %-7s %-22s %s" % (name, tag, e.group(1).strip()[:20] if e else "(no error)", txt[-42:]))
