#!/usr/bin/env python3
"""WHERE does the DATA cursor reset belong? The measured defect is that zerobas
never seeds it outside RUN/RESTORE, so a direct-mode READ seeks from an
uninitialised pointer. The FIX could sit in `vars_reset` -- the routine RUN, NEW,
CLEAR/MAXFILES and every program EDIT all reach -- but that would also decide
what CLEAR and an EDIT do to a POSITIONED cursor, and those are behaviours, not
implementation details.

So ask the reference. Each case positions the cursor by reading the first item,
then does one thing, then reads again: `7` means the cursor RESET, `8` means it
kept its position.
"""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl, probe_sides

SETUP = ['NEW', '10 DATA 7,8', '20 READ ZV', '30 PRINT"[";ZV;"]"', 'RUN']
CASES = [
    ("after RUN, READ again",   ['READ ZW', 'PRINT"<";ZW;">"']),
    ("CLEAR then READ",         ['CLEAR', 'READ ZW', 'PRINT"<";ZW;">"']),
    ("an EDIT then READ",       ['40 REM', 'READ ZW', 'PRINT"<";ZW;">"']),
    ("RESTORE then READ",       ['RESTORE', 'READ ZW', 'PRINT"<";ZW;">"']),
]
for side in ("vg8020", "zb"):
    cfg = probe_sides.sides(side)[side]
    print("=== %s" % side)
    for label, extra in CASES:
        caps = omsx_repl.run_cases(cfg["machine"],
                                   [("c", list(cfg["reset"]) + SETUP + extra)],
                                   batch=False, reset=(), boot=cfg["boot"], step=1.0,
                                   cap_gap=6.0, timeout=600.0)
        cap = caps[0]
        rows = [cap[r*40:(r+1)*40].rstrip() for r in range(24)] if cap else []
        rows = [r.strip() for r in rows if r.strip()]
        # the VG-8020's function-key display is the last row and hides the answer
        rows = [r for r in rows if not r.startswith("color")]
        print("   %-22s %s" % (label, " | ".join(rows[-2:])))
        sys.stdout.flush()
print()
print("READ IT AS: <7> the cursor RESET to the program top; <8> it kept position.")
