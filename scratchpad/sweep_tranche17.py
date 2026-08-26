#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""TODO sweep 2026-08-26, tranche 17 — the spoke row, with a point the ARC cannot
paint.

Tranche 16 sampled centre+(15,0), which lies ON the arc, so the CIRCLE paints it
whether or not the SPOKE reaches it — the row agreed and could not have
disagreed. A point on the spoke RAY but strictly INSIDE the radius is painted by
the spoke ALONE.

The two candidate rays: the reference's endpoint offset (15,0) is the ray y=60
exactly; zerobas is claimed to use (15,-1), a ray that rises by 1 over 15 px and
so leaves y=60 for y=59 somewhere past the midpoint. Sampling y=60 AND y=59 at
three radii separates them.
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
    ("spoke.ray60", "y=60 at r=5/9/13 -- strictly inside the arc, spoke only",
     ["10 ON ERROR GOTO 100", f"20 SCREEN 2:{ARC}",
      "30 A=POINT(65,60):B=POINT(69,60):C=POINT(73,60)",
      '40 SCREEN 0:PRINT"[";A;B;C;"]":END',
      '100 E=ERR:SCREEN 0:PRINT"[ERR";E;"]"']),
    ("spoke.ray59", "the SAME radii one row up -- where a (15,-1) ray would go",
     ["10 ON ERROR GOTO 100", f"20 SCREEN 2:{ARC}",
      "30 A=POINT(65,59):B=POINT(69,59):C=POINT(73,59)",
      '40 SCREEN 0:PRINT"[";A;B;C;"]":END',
      '100 E=ERR:SCREEN 0:PRINT"[ERR";E;"]"']),
    ("spoke.absent.ctl", "a POSITIVE start angle draws NO spoke -- the same points "
                         "must be background, which is what proves these points are "
                         "the spoke's and not the arc's",
     ["10 ON ERROR GOTO 100", "20 SCREEN 2:CIRCLE(60,60),15,6,0.01,1.57",
      "30 A=POINT(65,60):B=POINT(69,60):C=POINT(73,60)",
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
            print(f"    {side:8s} {spans(res[side][i])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
