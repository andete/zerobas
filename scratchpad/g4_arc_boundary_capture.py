#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""G4 arc-boundary residual capture (G4-arcbnd / G4-spoke, docs/spec-basic-
graphics-g4.md §5.4/§9). Targeted VG-8020 captures beyond the original g4_
circle_char1..3.py pass, run AFTER the host-fit python model (scratchpad/
g4_circle_fit.py) already flagged exactly two residual pixels (arc_hpi_pi
misses (61,45); arc_wrap misses (68,47)) under the best integer cross-product
polarity found (S-side <=0, E-side <0 strict, ARCBIG >=0 inclusive).

Round 1: re-confirm the two known residual pixels reproduce (not a one-off
capture glitch). Round 2: probe just past/before the boundary (start=1.55/
1.58 instead of 1.57) to see whether the reference's own boundary is a clean
threshold near the point's true angle, or itself looks like a rounded-vector
artifact (informs whether closer clean-room matching is achievable at all).
Round 3: negative-angle spoke colour-plane readback with a PRE-EXISTING
differently-coloured pixel at the spoke endpoint, to see whether draw order
(spoke vs arc) is observable at all when both use the SAME colour argument
(reasoned: gfx_color_rmw is idempotent for a repeated same-colour write, so
order should be unobservable for every spec-pinned case, which all use one
colour for the whole CIRCLE statement).

Method: KEYBUF-injection via omsx_repl.py on Philips_VG_8020; VRAM pattern+
colour planes read back mid-GOTO-self loop. No ROM disassembly.
"""
from __future__ import annotations
import os, sys, json
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

REF = os.environ.get("ZEROBAS_REF_MACHINE", "Philips_VG_8020")
INIT = "COLOR15,1,1:SCREEN2:CLS"


def _band_segs(xr, yr, color=False):
    off = 0x2000 if color else 0
    cols = range(xr[0] >> 3, (xr[1] >> 3) + 1)
    rows = range(yr[0] >> 3, (yr[1] >> 3) + 1)
    cells = [(cr, cc) for cr in rows for cc in cols]
    return cells, [(off + cr * 256 + cc * 8, 8) for cr, cc in cells]


def _points(hexstr, cells, xr, yr):
    b = bytes.fromhex(hexstr)
    idx = {cell: i for i, cell in enumerate(cells)}
    pts = []
    for y in range(yr[0], yr[1] + 1):
        for x in range(xr[0], xr[1] + 1):
            cell = (y >> 3, x >> 3)
            blk = idx[cell] * 8 + (y & 7)
            if blk < len(b) and (b[blk] & (0x80 >> (x & 7))):
                pts.append([x, y])
    return pts


def capture_pointset(label, ops, cx, cy, h):
    xr = (max(0, cx - h), cx + h)
    yr = (max(0, cy - h), cy + h)
    cells, pseg = _band_segs(xr, yr)
    prog = [INIT, ops, "GOTO 30"]
    php = omsx_repl.run_cases(REF, [("stored", prog)], batch=False,
                              capture=("vram_segs", pseg))[0]
    pts = _points(php, cells, xr, yr) if php else []
    return pts


def round1_reconfirm():
    print("=== round 1: re-confirm the two known residual pixels ===")
    cases = [
        ("arc_hpi_pi_reconfirm", "CIRCLE(60,60),15,15,1.57,3.14", 60, 60, 17, (61, 45)),
        ("arc_wrap_reconfirm", "CIRCLE(60,60),15,15,3,1", 60, 60, 17, (68, 47)),
    ]
    out = {}
    for label, ops, cx, cy, h, watch in cases:
        pts = capture_pointset(label, ops, cx, cy, h)
        present = list(watch) in pts
        out[label] = {"ops": ops, "cx": cx, "cy": cy, "pts": pts, "n": len(pts)}
        print(f"  {label:24s} watch={watch} present={present} (n={len(pts)})")
    return out


def round2_threshold():
    print("\n=== round 2: sweep start angle around the (61,45) boundary ===")
    # (61,45) = offset (1,-15) from (60,60); true angle atan2(15,1) ~= 1.5042 rad,
    # below the nominal a0=1.57 the existing capture used. Sweep a0 across that
    # true-angle threshold, end fixed at 3.14 (deep inside, unambiguous).
    watch = (61, 45)
    out = {}
    for a0 in ("1.50", "1.504", "1.51", "1.55", "1.57", "1.58", "1.60"):
        label = f"sweep_a0_{a0}"
        ops = f"CIRCLE(60,60),15,15,{a0},3.14"
        pts = capture_pointset(label, ops, 60, 60, 17)
        present = list(watch) in pts
        out[label] = {"ops": ops, "a0": a0, "present": present, "n": len(pts)}
        print(f"  a0={a0:6s} watch={watch} present={present} (n={len(pts)})")
    return out


def round3_spoke_order():
    print("\n=== round 3: spoke/arc draw-order colour-plane readback ===")
    # Pre-plot a DIFFERENT colour at the negative-start spoke's endpoint pixel
    # (centre + (r,0) for start=0, i.e. (75,60) for centre (60,60) r=15) BEFORE
    # the CIRCLE call, then check whether the arc-vs-spoke internal draw order
    # is observable in the final colour byte (it uses the SAME colour arg as
    # the arc/circle itself, so gfx_color_rmw should be idempotent either way).
    cx, cy, r = 60, 60, 15
    px, py = cx + r, cy  # start=0 endpoint (spoke target when start<0)
    ops = f"PSET({px},{py}),9:CIRCLE({cx},{cy}),{r},6,-0.01,1.57"
    xr = (px - 1, px + 1)
    yr = (py - 1, py + 1)
    cells, cseg = _band_segs(xr, yr, color=True)
    prog = [INIT, ops, "GOTO 30"]
    col = omsx_repl.run_cases(REF, [("stored", prog)], batch=False,
                              capture=("vram_segs", cseg))[0]
    print(f"  colour bytes at/around ({px},{py}) after PSET,9 then CIRCLE,,6,-0.01,1.57: {col}")
    return {"ops": ops, "px": px, "py": py, "colour_hex": col}


def main():
    r1 = round1_reconfirm()
    r2 = round2_threshold()
    r3 = round3_spoke_order()
    path = os.path.join(HERE, "g4_arc_boundary_capture.json")
    with open(path, "w") as f:
        json.dump({"round1": r1, "round2": r2, "round3": r3}, f, indent=1)
    print(f"\n-> wrote {path}")


if __name__ == "__main__":
    main()
