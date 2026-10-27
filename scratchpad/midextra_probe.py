#!/usr/bin/env python3
"""D-MIDEXTRA, measure first (2026-10-27): MID$ with a 4th argument, and the
MID$ statement with a target that is not a string variable.

Our own program, one case per boot: line 20 is the case under ON ERROR, then a
marker; the handler prints ERR and ERL. Typed BASIC in, the screen out.

    10 ON ERROR GOTO 90
    20 <the case>
    30 PRINT "OK":END
    90 PRINT "E";ERR;ERL:END

    python3 -u scratchpad/midextra_probe.py [MACHINE...]
"""
import os, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

CASES = {"fn4":     'PRINT MID$("AB",1,1,1)',
         "fn4s":    'PRINT MID$("AB",1,1,"Q")',
         "fn3ok":   'PRINT MID$("AB",2,1)',
         "fn3sp":   'PRINT MID$("AB",1 1)',
         "stnum":   'MID$(5,1)="X"',
         "stexpr":  'A$="AB":MID$(A$+"",1)="X"',
         "stnvar":  'A=1:MID$(A,1)="X"',
         "st4":     'A$="AB":MID$(A$,1,1,1)="X"',
         "stok":    'A$="AB":MID$(A$,2)="X":PRINT A$'}
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
