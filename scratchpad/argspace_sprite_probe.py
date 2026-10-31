import os, sys, re
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl, probe_sides
SIDES = probe_sides.sides("vg8020", "cf3300", "zb")
for tag, st in [("s.ctl", 'SPRITE$(0)="AB"'), ("s.sp", 'SPRITE$(0)= "AB"')]:
    for side, c in SIDES.items():
        p = ["10 ON ERROR GOTO 900", "20 SCREEN 1", f"30 {st}", '40 R$=LEFT$(SPRITE$(0),2)',
             '50 SCREEN 0:PRINT"ZQ";0;",";R$;"QZ":END', '900 SCREEN 0:PRINT"ZQ";ERR;",";R$;"QZ":END']
        raw = "".join(omsx_repl.run_cases(c["machine"], [("direct", list(c["reset"]) + p + ["RUN"])],
              batch=False, reset=(), boot=c["boot"], step=4.0, run_gap=10.0, cap_gap=4.0, timeout=420.0)[0] or "")
        v = [g for g in re.findall(r'ZQ\s*([0-9]+)\s*,\s*([A-Z\-]*)\s*QZ', raw) if not any(ch in "".join(g) for ch in '"$;')]
        print(tag, side, v[-1] if v else None, flush=True)
