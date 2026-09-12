import sys, re
sys.path.insert(0, "/Users/joost/projects/zerobas/probes/lib")
import omsx_repl, probe_sides
cfg = probe_sides.sides("zb")["zb"]
cases = [
    ("inp.value",  ['PRINT"[I";INP(&HA8);"]"']),
    ("inp.ge0",    ['PRINT"[I";INP(&HA8)>=0;"]"']),
    ("inp.gt0",    ['PRINT"[I";INP(&HA8)>0;"]"']),
    ("stub.ge0",   ['PRINT"[I";ZZQ(0)>=0;"]"']),      # an undefined name = the stub shape
    ("vdp.value",  ['PRINT"[V";VDP(1);"]"']),
    ("stub.vdp",   ['PRINT"[V";ZZR(1);"]"']),
]
caps = omsx_repl.run_cases(cfg["machine"], cases, batch=False, reset=(),
                           boot=cfg["boot"], step=10.0, cap_gap=90.0, timeout=600.0)
for (tag, _), cap in zip(cases, caps):
    txt = re.sub(r"\s+", " ", cap if isinstance(cap, str) else str(cap))
    m = re.findall(r"\[[IV]\s*(-?\d+)\s*\]", txt)
    print("%-11s %s" % (tag, m[-1] if m else "NONE"))
