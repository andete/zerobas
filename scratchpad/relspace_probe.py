#!/usr/bin/env python3
"""D-RELSPACE, measure first (2026-10-31): a space between a TWO-character
relational operator and its string right-hand side (D-REREAD batch 6 reviewer).

Our own program, one case per boot: line 20 is the case under ON ERROR, then a
marker; the handler prints ERR and ERL. Typed BASIC in, the screen out.

    10 ON ERROR GOTO 90
    20 <the case>
    30 PRINT "OK":END
    90 PRINT "E";ERR;ERL:END

    python3 -u scratchpad/relspace_probe.py [MACHINE...]
"""
import os, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

CASES = {"le_sp":    'PRINT "A"<= "B"',
         "le":       'PRINT "A"<="B"',
         "ne_sp":    'PRINT "A"<>  "B"',
         "ge_sp":    'PRINT "A">= "B"',
         "lt_sp":    'PRINT "A"< "B"',
         "var_le":   'A$="A":PRINT A$ <= "B"',
         "mid_sp":   'PRINT "A"< = "B"'}
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
