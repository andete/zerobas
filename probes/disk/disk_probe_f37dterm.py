#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""D-F37DTERM: BDOS $00 (TERMINATE) THROUGH $F37D FROM A BASIC PROGRAM -- the CF-3300 vs zerobas.

A BASIC program POKEs the stub `ld c,0 / call $F37D / ret` at &HD000 (CLEAR 200,&HD000 first) and runs

    30 DEFUSR=&HD000:X=USR(0):PRINT "AFTER"
    40 PRINT "LINE40"

then `PRINT FRE(0)` is typed. Rows: `after` -- does the rest of line 30 run (AFTER on the screen)? `next` -- does
line 40 run? `fre` -- FRE(0) after it (the CLEAR kept?). Measured by hand on 2026-11-26 (the item): the CF-3300 ends
the program silently -- neither AFTER nor LINE40, `Ok`, the CLEAR's FRE kept.

Clean room: typed BASIC in, the screen out. Exit 0 all SAME; 1 a divergence; 2 no reading.
"""
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
os.environ.setdefault("ZEROBAS_REFCACHE", "refs")
import omsx_repl  # noqa: E402
import probe_tmp  # noqa: E402

MACHINES = (("CF", "National_CF-3300"), ("ZB", os.environ.get("F37DTERM_ZB_MACHINE") or "C-BIOS_MSX1_EU_REPACK_DISK"))
# 🔴 THE KNOWN DIFFERENCE, PINNED (D-F37DTERMLINE, 2026-11-26, scratchpad/AE_f37dterm1.out): the disk ROM ends the run
# (ENDFLAG, as END), so line 40 no longer runs -- but the REST OF LINE 30 still does: the assignment's handler goes
# on to the next statement, and stopping it from inside the call needs BASIC's own seam. The row must still diverge
# exactly so (CF False, ZB True); SAME means the fix landed and the pin must go.
KNOWN = {"after": (False, True)}
PROG = ["NEW", "10 CLEAR 200,&HD000", "20 FOR I=0 TO 5:READ A:POKE &HD000+I,A:NEXT",
        '30 DEFUSR=&HD000:X=USR(0):PRINT "AFTER"', '40 PRINT "LINE40"', "50 DATA 14,0,205,125,243,201",
        "RUN", "PRINT FRE(0)"]


def reading(raw):
    if raw is None:
        return None
    rows = [raw[i:i + 40].strip() for i in range(0, len(raw), 40)]
    k = max((i for i, r in enumerate(rows) if r == "RUN"), default=None)
    if k is None:
        return None
    after = [r for r in rows[k + 1:] if r]
    fre = next((after[i + 1] for i, r in enumerate(after) if r.startswith("PRINT FRE") and i + 1 < len(after)), "?")
    return {"after": "AFTER" in after, "next": "LINE40" in after, "fre": fre}


def main():
    got = {}
    for side, m in MACHINES:
        dsk = probe_tmp.tmp(f"f37dterm_{side}.dsk")
        shutil.copyfile(os.path.join(REPO, "disk", "test720.dsk"), dsk)
        raw = omsx_repl.run_cases(m, [("direct", PROG)], batch=False, diska=dsk, boot=14.0,
                                  reset=("", "SCREEN 0"), step=3.0)[0]
        got[side] = reading(raw)
    if None in got.values():
        print(f"INSTRUMENT FAULT: no reading on {[s for s, v in got.items() if v is None]}")
        return 2
    bad = []
    for row in ("after", "next", "fre"):
        v = "SAME" if got["CF"][row] == got["ZB"][row] else "DIVERGES"
        if row in KNOWN:
            v = ("KNOWN DIFFERENCE (D-F37DTERMLINE)" if (got["CF"][row], got["ZB"][row]) == KNOWN[row]
                 else "SAME -- 🔴 D-F37DTERMLINE FIXED: drop the pin" if v == "SAME" else "DIVERGES (the pin moved)")
        bad += [row] if not v.startswith(("SAME", "KNOWN")) or "FIXED" in v else []
        print(f"ROW {row:6s} CF={got['CF'][row]!s:6s} ZB={got['ZB'][row]!s:6s} {v}")
    if got["CF"]["after"] or got["CF"]["next"]:
        print("INSTRUMENT FAULT: the CF-3300 ran on past TERMINATE -- the stub or the program is not what was measured")
        return 2
    print(f"\n{'PASS' if not bad else 'FAIL'}: BDOS $00 through $F37D ends the BASIC program")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
