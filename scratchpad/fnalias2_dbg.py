#!/usr/bin/env python3
"""D-FNALIAS debug: raw screen of small programs on one machine (zb by default)."""
import os, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

M = os.environ.get("M", "C-BIOS_MSX1_EU_REPACK_DISK")
PROGS = {
    'rec1': ['10 ON ERROR GOTO 900', '20 DEF FNA(X)=FNA(X)', '60 PRINT FNA(1)', '70 END',
             '900 PRINT "[ERR";ERR;"AT";ERL;"]":END'],
    'rec0': ['10 ON ERROR GOTO 900', '20 DEF FNA=FNA', '60 PRINT FNA', '70 END',
             '900 PRINT "[ERR";ERR;"AT";ERL;"]":END'],
    'rec1n': ['20 DEF FNA(X)=FNA(X)', '60 PRINT FNA(1)', '70 END'],
    'rec1t': ['10 ON ERROR GOTO 900', '20 DEF FNA(X)=FNA(X)', '30 T=TIME', '60 PRINT FNA(1)', '70 END',
              '900 PRINT "[ERR";ERR;"AT";ERL;"T";TIME-T;"]":END'],
    'rec0t': ['10 ON ERROR GOTO 900', '20 DEF FNA=FNA', '30 T=TIME', '60 PRINT FNA', '70 END',
              '900 PRINT "[ERR";ERR;"AT";ERL;"T";TIME-T;"]":END'],
}
for name in (sys.argv[1:] or PROGS):
    cap = omsx_repl.run_cases(M, [("direct", ["NEW"] + PROGS[name] + ["RUN"])],
                              batch=False, reset=(), boot=8.0, run_gap=float(os.environ.get("RG", "25")))[0]
    print(f"--- {name}:\n" + "".join(cap or ["<NONE>"]), flush=True)
