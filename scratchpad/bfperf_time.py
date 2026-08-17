#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-BFPERF -- how long does a box FILL take, reference vs zerobas?

Filed by D-DRAWCLAMP (§7): `LINE(0,0)-(300,250),,BF` returned NO reading at all
on zerobas boot-per-case at step 20, while the VG-8020 answered. A 56x42 fill
was fine, so it is slowness rather than a hang -- but the factor was never
measured, and **no gate measures time**.

Method is D-ARCMASK's ([`arcmask_time.py`](arcmask_time.py)): `TIME` is the VDP
frame counter, and an EMPTY FOR loop of the SAME iteration count is measured on
the SAME machine and subtracted, because BASIC's own FOR/NEXT costs real ticks
and costs DIFFERENT ticks on two different ROMs.

⚠️ Iteration counts differ per row (a full-screen fill cannot be run 20 times),
so the empty-loop control is measured at EVERY distinct N -- a baseline
borrowed across N would be a scaled guess, not a reading.

The diagnostic pair is `bf_1row` vs `bf_1col`: the same routine, 256 pixels in
ONE scanline versus 192 scanlines of ONE pixel. If the per-row setup dominates
the per-pixel cost, `bf_1col` is the expensive one and the fix is the row loop;
if the per-pixel VDP read-modify-write dominates, `bf_1row` is.

    python3 -u scratchpad/bfperf_time.py [--dry]
"""
from __future__ import annotations

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))

REF = os.environ.get("ZEROBAS_REF_MACHINE", "Philips_VG_8020")
ZB = os.environ.get("ZEROBAS_SUBROM_INTTEST_MACHINE",
                    "C-BIOS_MSX1_EU_REPACK_DISK")

# label, N, ops, px drawn, why
CASES = [
    ("bf_dead", 20, "LINE(10,10)-(10,10),15,BF", 1,
     "⭐ DEAD SUBJECT: a 1x1 fill. Whatever this costs is the fixed per-CALL "
     "overhead -- marshalling, the mode gate, the work area -- not the filling."),
    ("bf_cell", 20, "LINE(8,8)-(15,15),15,BF", 64,
     "one character cell, 8x8: the smallest fill that spans a whole byte."),
    ("bf_1row", 8, "LINE(0,0)-(255,0),15,BF", 256,
     "⭐ 256 px in ONE scanline: per-PIXEL cost, one row of setup."),
    ("bf_1col", 8, "LINE(0,0)-(0,191),15,BF", 192,
     "⭐ 192 scanlines of ONE px: per-ROW cost, minimal pixels. Against "
     "bf_1row this says which loop to attack."),
    ("bf_64", 4, "LINE(10,10)-(73,73),15,BF", 64 * 64,
     "a 64x64 block -- the shape a real program fills."),
    ("bf_full", 1, "LINE(0,0)-(255,191),15,BF", 256 * 192,
     "⭐ THE WHOLE SCREEN, 49152 px: the row that returned nothing."),
    ("bf_off", 1, "LINE(0,0)-(300,250),15,BF", 256 * 192,
     "the residual's OWN row. Post-D-DRAWCLAMP its clamped box IS the whole "
     "screen, so it must cost the same as bf_full -- a consistency control on "
     "the clamp, measured in time instead of pixels."),
    ("box_full", 8, "LINE(0,0)-(255,191),15,B", 2 * (256 + 192),
     "the OUTLINE of the same box: four segments, no fill. Separates the "
     "rasteriser from the filling."),
    ("line_diag", 8, "LINE(0,0)-(255,191),15", 256,
     "one long segment, 256 px -- the same rasteriser, one call."),
]


def prog(ops, n):
    body = ["COLOR15,4,7:SCREEN2", "T=TIME"]
    body.append(f"FORI=1TO{n}:{ops}:NEXT" if ops else f"FORI=1TO{n}:NEXT")
    body += ["U=TIME", 'SCREEN0:PRINT"T=";U-T', "GOTO 60"]
    return body


def ticks(machine, ops, n, step):
    import omsx_repl
    out = omsx_repl.run_cases(machine, [("stored", prog(ops, n))],
                              batch=False, step=step)[0]
    m = re.search(r"T=\s*(-?\d+)", out or "")
    return int(m.group(1)) if m else None


def main() -> int:
    ns = sorted({n for _, n, _, _, _ in CASES})
    print("=== D-BFPERF: box-fill cost, reference vs zerobas ===")
    print(f"ref={REF}  zb={ZB}   TIME = VDP frames, 20 ms each (both EU)\n")
    print(f"  empty-loop controls needed at N = {ns}")
    for lbl, n, ops, px, why in CASES:
        print(f"  {lbl:10} N={n:<3} {px:6d} px  {ops}")
        print(f"      why: {why}")
    if "--dry" in sys.argv:
        return 0

    def step_for(n, px):
        return 240.0 if px > 10000 else 90.0 if px > 1000 else 30.0

    base = {}
    for n in ns:
        st = 60.0
        r, z = ticks(REF, "", n, st), ticks(ZB, "", n, st)
        base[n] = (r, z)
        print(f"\n  loop_only N={n:<3} raw ref={r} zb={z}   (subtracted below)")

    print("\n--- per SINGLE call, milliseconds (loop control subtracted) ---")
    print(f"  {'row':10} {'px':>7} {'reference':>11} {'zerobas':>11} "
          f"{'ratio':>8} {'zb us/px':>9}")
    rows = []
    for lbl, n, ops, px, why in CASES:
        st = step_for(n, px)
        r, z = ticks(REF, ops, n, st), ticks(ZB, ops, n, st)
        br, bz = base[n]
        rn = None if r is None or br is None else (r - br) * 20.0 / n
        zn = None if z is None or bz is None else (z - bz) * 20.0 / n
        rat = f"{zn / rn:.2f}x" if rn and zn and rn > 0 else "-"
        upx = f"{zn * 1000.0 / px:.1f}" if zn else "-"
        rows.append((lbl, px, rn, zn, rat))
        print(f"  {lbl:10} {px:7d} "
              f"{('%.1f ms' % rn) if rn is not None else 'NO READING':>11} "
              f"{('%.1f ms' % zn) if zn is not None else 'NO READING':>11} "
              f"{rat:>8} {upx:>9}")
    print("\n⚠️ a row reading NO READING on one machine only is a RIG result, "
          "not a finding -- raise its step and re-run before quoting it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
