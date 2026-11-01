"""D-G8OPCLOB: does a VDP(n)= / BASE(n)= assignment still run its own op when the
index or the value calls POINT / SPRITE$ (which use the same graphics tenant)?

Each row reads the register / table address back BEFORE `SCREEN 0` (SCREEN
rewrites VDP(7)). Three sides: the reference VG-8020 and CF-3300, and zerobas.
"""
import os, sys, re
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl, probe_sides

SIDES = probe_sides.sides(*(os.environ.get("SIDES", "vg8020,cf3300,zb").split(",")))
SETUP = ['SPRITE$(0)=CHR$(0)', 'PSET(0,0),5']
ROWS = [
    ("v.ctl",   'VDP(7)=5',                       'R=VDP(7)'),
    ("v.point", 'VDP(7)=POINT(0,0)',              'R=VDP(7)'),
    ("v.idx",   'VDP(POINT(0,0)+2)=4',            'R=VDP(7)'),
    ("b.ctl",   'BASE(5)=2048',                   'R=BASE(5)'),
    ("b.spr",   'BASE(5)=2048+ASC(SPRITE$(0))',   'R=BASE(5)'),
    ("b.idx",   'BASE(5+ASC(SPRITE$(0)))=2048',   'R=BASE(5)'),
]
only = sys.argv[1:]
for tag, st, rd in ROWS:
    if only and tag not in only:
        continue
    for side, c in SIDES.items():
        p = ["10 ON ERROR GOTO 900", "20 SCREEN 2"] + \
            [f"{30 + k} {s}" for k, s in enumerate(SETUP)] + \
            [f"40 {st}", f"50 {rd}",
             '60 SCREEN 0:PRINT"ZQ";0;",";R;"QZ":END',
             '900 SCREEN 0:PRINT"ZQ";ERR;",";-1;"QZ":END']
        raw = "".join(omsx_repl.run_cases(
            c["machine"], [("direct", list(c["reset"]) + p + ["RUN"])],
            batch=False, reset=(), boot=c["boot"], step=4.0, run_gap=10.0,
            cap_gap=4.0, timeout=420.0)[0] or "")
        v = re.findall(r'ZQ\s*(-?[0-9]+)\s*,\s*(-?[0-9]+)\s*QZ', raw)
        print(tag, side, "ERR=%s R=%s" % v[-1] if v else None, flush=True)
