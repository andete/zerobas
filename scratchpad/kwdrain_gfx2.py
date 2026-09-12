import sys, re
sys.path.insert(0, "/Users/joost/projects/zerobas/probes/lib")
import omsx_repl, probe_sides
sides = probe_sides.sides("zb", "vg8020")
cases = [
    ("circle.rim",  ['10 SCREEN2:CIRCLE(50,50),10,15:A=POINT(60,50):SCREEN0:PRINT"[X";A;"]"', "RUN"]),
    ("circle.ctr",  ['10 SCREEN2:CIRCLE(50,50),10,15:A=POINT(50,50):SCREEN0:PRINT"[X";A;"]"', "RUN"]),
    ("draw.right",  ['10 SCREEN2:PSET(10,10),15:DRAW"C15R5":A=POINT(14,10):SCREEN0:PRINT"[X";A;"]"', "RUN"]),
    ("sprite.read", ['10 SPRITE$(0)=STRING$(8,255):A=ASC(SPRITE$(0)):PRINT"[X";A;"]"', "RUN"]),
    ("base.0",      ['10 A=BASE(0):PRINT"[X";A;"]"', "RUN"]),
    ("base.2",      ['10 A=BASE(2):PRINT"[X";A;"]"', "RUN"]),
    ("base.10",     ['10 A=BASE(10):PRINT"[X";A;"]"', "RUN"]),
]
for name in ("zb", "vg8020"):
    cfg = sides[name]
    caps = omsx_repl.run_cases(cfg["machine"], cases, batch=False, reset=(),
                               boot=cfg["boot"], step=10.0, cap_gap=90.0, timeout=600.0)
    out = []
    for (tag, _), cap in zip(cases, caps):
        txt = re.sub(r"\s+", " ", cap if isinstance(cap, str) else str(cap))
        m = re.findall(r"\[X\s*(-?\d+)\s*\]", txt)
        out.append("%s=%s" % (tag, m[-1] if m else "NONE"))
    print("%-7s %s" % (name, "  ".join(out)))
