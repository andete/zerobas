#!/usr/bin/env python3
"""🔴 A TIER 3 disk row found `DSKF(9)` answering a NUMBER where the reference says
`Bad drive name`. Before filing, find the BOUNDARY: which drive numbers does each
machine accept, and does zerobas answer the same figure for all of them (a range
check missing entirely) or a different one per drive (a range check that is merely
too wide)? Those are different defects with different fixes.
"""
import os, sys, shutil, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
sys.path.insert(0, os.path.join(ROOT, "probes", "disk"))
import omsx_repl, probe_sides

DSK = os.path.join(ROOT, "disk", "test720.dsk")
# the DISK-equipped reference is the National CF-3300; the VG-8020 is diskless
for side in ("cf3300", "zb"):
    cfg = probe_sides.sides(side)[side]
    fh = tempfile.NamedTemporaryFile(suffix=".dsk", delete=False); fh.close()
    shutil.copy(DSK, fh.name)
    # ⚠️ DRIVE 2 IS EXCLUDED AND THAT IS MEASURED, NOT CAUTION: on the CF-3300
    # `DSKF(2)` prints `Insert diskette for drive B: and strike a key when ready`
    # and WAITS, which ate the next typed line and failed the run's echo check.
    # A row that prompts is a row that eats its successors (silent-failure mode 5).
    lines = ['NEW'] + ['PRINT"<";DSKF(%s);">"' % d for d in ("0", "1", "9")]
    caps = omsx_repl.run_cases(cfg["machine"], [("c", list(cfg["reset"]) + lines)],
                               batch=False, reset=(), boot=cfg["boot"], step=5.0,
                               cap_gap=20.0, timeout=900.0, diska=fh.name)
    cap = caps[0]
    rows = [cap[r*40:(r+1)*40].rstrip() for r in range(24)] if cap else []
    rows = [r.strip() for r in rows if r.strip() and not r.startswith("color")]
    print("=== %-12s %s" % (side, " | ".join(rows[-7:])))
    sys.stdout.flush()
print()
print("READ IT AS: drives 0,1,2,3,9 in order. The reference's boundary is the")
print("subject; a figure where it says `Bad drive name` is the defect.")
