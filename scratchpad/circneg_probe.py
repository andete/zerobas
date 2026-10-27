#!/usr/bin/env python3
"""D-CIRCNEGR, measure first (2026-10-27): what CIRCLE does with a negative (or
huge) radius -- the error, how long the draw takes (TIME, emulated jiffies) and
how many pattern-table bytes are non-zero afterwards. Our own program; typed
BASIC in, the text screen out (VPEEK of the pattern table is VRAM DATA the
program drew, not ROM).

    10 ON ERROR GOTO 90
    20 SCREEN 2:TIME=0:CIRCLE(99,99),<r>:T=TIME
    30 C=0:FOR I=0 TO 6143:IF VPEEK(I) THEN C=C+1
    40 NEXT:SCREEN 0:PRINT "T";T;"C";C:END
    90 SCREEN 0:PRINT "E";ERR;ERL:END

    python3 -u scratchpad/circneg_probe.py [MACHINE...]
"""
import os, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

RADII = ["5", "200", "-5", "-1", "-32768", "32767", "65535", "-32769", "70000"]
MACHINES = ["Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK"]


def main():
    for m in sys.argv[1:] or MACHINES:
        for r in RADII:
            lines = ["10 ON ERROR GOTO 90",
                     f"20 SCREEN 2:TIME=0:CIRCLE(99,99),{r}:T=TIME",
                     "30 C=0:FOR I=0 TO 6143:IF VPEEK(I) THEN C=C+1",
                     '40 NEXT:SCREEN 0:PRINT "T";T;"C";C:END',
                     '90 SCREEN 0:PRINT "E";ERR;ERL:END', "RUN"]
            scr = omsx_repl.run_cases(m, [("direct", lines)], batch=False, boot=14.0,
                                      reset=("SCREEN 0:WIDTH 40", "NEW"), step=4.0,
                                      run_gap=1200.0)[0]
            rows = [scr[i:i + 40].rstrip() for i in range(0, len(scr or ""), 40)]
            out = " | ".join(r2 for r2 in rows if r2.strip().startswith(("T", "E"))) or "<NO READING>"
            print(f"{m:30s} r={r:7s} [{out}]", flush=True)


if __name__ == "__main__":
    main()
