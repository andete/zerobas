#!/usr/bin/env python3
"""D-DEFFNPARAM, measure first (2026-10-27): which DEF FN formal lists does the
VG-8020 refuse AT THE DEF, and with what error?

Our own program, one case per boot: line 10 is the DEF under ON ERROR, then a
marker; the handler prints ERR and ERL. Typed BASIC in, the screen out.

    10 ON ERROR GOTO 90
    20 <the DEF>
    30 PRINT "OK":END
    90 PRINT "E";ERR;ERL:END

    python3 -u scratchpad/deffnparam_probe.py [MACHINE...]
"""
import os, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

CASES = {"num":     "DEF FNA(5)=1",
         "strnum":  "DEF FNA$(5)=1",
         "empty":   "DEF FNA()=1",
         "second":  "DEF FNA(X,5)=1",
         "lead":    "DEF FNA(,X)=1",
         "trail":   "DEF FNA(X,)=1",
         "nosep":   "DEF FNA(X Y)=1",
         "expr":    "DEF FNA(X+1)=1",
         "noclose": "DEF FNA(X=1",
         "twoclose": "DEF FNA(X))=1",
         "noeq":    "DEF FNA(X)1",
         "spaces":  "DEF FNA( X , Y )=X+Y",
         "ok":      "DEF FNA(X,Y)=X+Y",
         "aryform": "DEF FNA(C(1))=1"}
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
