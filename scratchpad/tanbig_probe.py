#!/usr/bin/env python3
"""D-TANBIG, measure first (2026-10-27): SIN, COS and TAN of growing arguments,
to find where the reference starts raising and what each prints before it.

Our own program, one case per boot: line 20 is the case under ON ERROR, then a
marker; the handler prints ERR and ERL. Typed BASIC in, the screen out.

    10 ON ERROR GOTO 90
    20 <the case>
    30 PRINT "OK":END
    90 PRINT "E";ERR;ERL:END

    python3 -u scratchpad/tanbig_probe.py [MACHINE...]
"""
import os, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

CASES = {'e1E10': 'X=1E10:PRINT SIN(X);COS(X):PRINT TAN(X)',
         'e1E13': 'X=1E13:PRINT SIN(X);COS(X):PRINT TAN(X)',
         'e1E14': 'X=1E14:PRINT SIN(X);COS(X):PRINT TAN(X)',
         'e1E15': 'X=1E15:PRINT SIN(X);COS(X):PRINT TAN(X)',
         'e1E16': 'X=1E16:PRINT SIN(X);COS(X):PRINT TAN(X)',
         'e1E17': 'X=1E17:PRINT SIN(X);COS(X):PRINT TAN(X)',
         'e1E20': 'X=1E20:PRINT SIN(X);COS(X):PRINT TAN(X)',
         'e1E30': 'X=1E30:PRINT SIN(X);COS(X):PRINT TAN(X)',
         'e1E38': 'X=1E38:PRINT SIN(X);COS(X):PRINT TAN(X)',
         'e1p5E15': 'X=1.5E15:PRINT SIN(X);COS(X):PRINT TAN(X)',
         'e3E15': 'X=3E15:PRINT SIN(X);COS(X):PRINT TAN(X)',
         'em1E38': 'X=-1E38:PRINT SIN(X);COS(X):PRINT TAN(X)',
         'e1D30': 'X=1D30:PRINT SIN(X);COS(X):PRINT TAN(X)'}
CASES2 = {"e"+e: f"X={e}:PRINT SIN(X);COS(X):PRINT TAN(X)"
          for e in ["1E11", "1E12", "2E13", "3E13", "5E13", "7E13"]}
if "--bisect" in sys.argv:
    sys.argv.remove("--bisect")
    CASES = CASES2
MACHINES = ["Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK"]


def main():
    for m in sys.argv[1:] or MACHINES:
        for name, d in CASES.items():
            lines = ["10 ON ERROR GOTO 90", f"20 {d}", '30 PRINT "OK":END',
                     '90 PRINT "E";ERR;ERL:END', "RUN"]
            scr = omsx_repl.run_cases(m, [("direct", lines)], batch=False, boot=14.0,
                                      reset=("SCREEN 0:WIDTH 40", "NEW"), step=4.0,
                                      run_gap=10.0)[0]
            rows = [scr[i:i + 40].rstrip() for i in range(0, len(scr or ""), 40)]
            if "RUN" in rows:
                rows = rows[rows.index("RUN") + 1:]
            out = " | ".join(r for r in rows if r.strip() and r.strip() != "Ok") or "<NO OUTPUT>"
            print(f"{m:30s} {name:8s} {d:24s} [{out}]", flush=True)


if __name__ == "__main__":
    main()
