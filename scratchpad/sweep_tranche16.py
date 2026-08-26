#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""TODO sweep 2026-08-26, tranche 16 — the spoke-endpoint row, from the item's
own fixture.

The item was measured from BANKED data ('no gate row covers it'), so this is the
first time it has been put to a live machine since it was filed.
"""
import os
import sys

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "probes", "lib"))
import omsx_repl                                                  # noqa: E402
import probe_tmp                                                  # noqa: E402

SIDES = {
    "vg8020": dict(machine="Philips_VG_8020", boot=8.0, step=6.0,
                   reset=("NEW", "CLS")),
    "cf3300": dict(machine="National_CF-3300", boot=14.0, step=8.0,
                   reset=("", "SCREEN 0", "NEW", "CLS")),
    "zb": dict(machine=os.environ.get("ZEROBAS_BASIC_MACHINE",
                                      "C-BIOS_MSX1_EU_REPACK_DISK"),
               boot=8.0, step=6.0, reset=("NEW", "CLS")),
}
COLS, ROWS = 40, 24
ARC = "CIRCLE(60,60),15,6,-0.01,1.57"

CASES = [
    # The item: the reference's spoke reaches the OCTANT POINT (75,60); zerobas's
    # bvec rounds the sine to 0 and the nudge makes it (15,-1), a different line.
    # 🔴 THE ITEM'S FIXTURE SEEDS (75,60) WITH COLOUR 9 FIRST. The first draft
    # dropped the PSET and asked a DIFFERENT question -- whether the spoke paints
    # the pixel at all, rather than whether the spoke's colour 6 REACHES and
    # overwrites a pixel already holding 9. Same coordinates, different experiment.
    ("spoke.endpoint", "PSET(75,60),9 THEN the arc: does colour 6 reach it?",
     ["10 ON ERROR GOTO 100", f"20 SCREEN 2:PSET(75,60),9:{ARC}",
      "30 A=POINT(75,60):B=POINT(75,59):C=POINT(74,60)",
      '40 SCREEN 0:PRINT"[";A;B;C;"]":END',
      '100 E=ERR:SCREEN 0:PRINT"[ERR";E;"]"']),
    ("spoke.ctl", "the same arc, a point far off the spoke -- must be background",
     ["10 ON ERROR GOTO 100", f"20 SCREEN 2:{ARC}",
      "30 A=POINT(20,20):B=POINT(21,20):C=POINT(22,20)",
      '40 SCREEN 0:PRINT"[";A;B;C;"]":END',
      '100 E=ERR:SCREEN 0:PRINT"[ERR";E;"]"']),
    ("spoke.seed", "the item's own PSET seed alone -- pins that (75,60) is writable",
     ["10 ON ERROR GOTO 100", "20 SCREEN 2:PSET(75,60),9",
      "30 A=POINT(75,60):B=POINT(75,59):C=POINT(74,60)",
      '40 SCREEN 0:PRINT"[";A;B;C;"]":END',
      '100 E=ERR:SCREEN 0:PRINT"[ERR";E;"]"']),
]


def spans(scr):
    if scr is None:
        return None
    flat = " ".join(scr[r * COLS:(r + 1) * COLS].rstrip() for r in range(ROWS))
    out, i = [], 0
    while (a := flat.find("[", i)) >= 0 and (b := flat.find("]", a)) >= 0:
        out.append(flat[a + 1:b].strip()); i = b + 1
    return out


def main():
    res = {s: omsx_repl.run_cases(c["machine"],
                                  [("direct", l + ["RUN"]) for _, _, l in CASES],
                                  batch=True, reset=c["reset"], boot=c["boot"],
                                  step=c["step"], verify_delivery=False)
           for s, c in SIDES.items()}
    for i, (label, claim, _) in enumerate(CASES):
        print(f"\n=== {label} — {claim}")
        for side in SIDES:
            print(f"    {side:8s} POINT(75,60) POINT(75,59) POINT(74,60) = "
                  f"{spans(res[side][i])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
