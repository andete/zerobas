#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""G4 CIRCLE characterization round 3 (VG-8020): dump machine-readable point-sets
(JSON) for the host fitter, plus remaining pins -- negative radius (isolated),
GXPOS/GYPOS residue pattern, aspect rounding, colour clash, arc wrap/full/degenerate.
Read-only, no ROM disassembly."""
from __future__ import annotations
import os, sys, re, json
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

REF = os.environ.get("ZEROBAS_REF_MACHINE", "Philips_VG_8020")
INIT = "COLOR15,1,1:SCREEN2:CLS"


def _band_segs(xr, yr):
    cols = range(xr[0] >> 3, (xr[1] >> 3) + 1)
    rows = range(yr[0] >> 3, (yr[1] >> 3) + 1)
    cells = [(cr, cc) for cr in rows for cc in cols]
    pseg = [(cr * 256 + cc * 8, 8) for cr, cc in cells]
    cseg = [(0x2000 + cr * 256 + cc * 8, 8) for cr, cc in cells]
    return cells, pseg, cseg


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


def dump_pointsets():
    """capture exact plotted pixels for circles + ellipses + arcs -> JSON oracle."""
    CASES = [
        # label, ops, cx, cy, band-half
        ("circ_r4",  "CIRCLE(40,40),4,15",  40, 40, 6),
        ("circ_r8",  "CIRCLE(40,40),8,15",  40, 40, 10),
        ("circ_r12", "CIRCLE(60,60),12,15", 60, 60, 14),
        ("circ_r20", "CIRCLE(80,80),20,15", 80, 80, 22),
        ("circ_r7",  "CIRCLE(40,40),7,15",  40, 40, 9),
        ("circ_r15", "CIRCLE(60,60),15,15", 60, 60, 17),
        ("ell_a025", "CIRCLE(80,80),20,15,,,.25", 80, 80, 22),
        ("ell_a05",  "CIRCLE(80,80),20,15,,,.5",  80, 80, 22),
        ("ell_a2",   "CIRCLE(80,80),20,15,,,2",   80, 80, 22),
        ("ell_a3",   "CIRCLE(80,80),20,15,,,3",   80, 80, 22),
        ("ell_a05r15","CIRCLE(60,60),15,15,,,.5", 60, 60, 17),
        ("arc_0_hpi", "CIRCLE(60,60),15,15,0,1.57",   60, 60, 17),
        ("arc_hpi_pi","CIRCLE(60,60),15,15,1.57,3.14",60, 60, 17),
        ("arc_wrap",  "CIRCLE(60,60),15,15,3,1",       60, 60, 17),   # end<start -> wrap thru 0
        ("arc_full628","CIRCLE(60,60),15,15,0,6.28",   60, 60, 17),   # ~full
    ]
    out = {}
    for label, ops, cx, cy, h in CASES:
        xr = (max(0, cx - h), cx + h); yr = (max(0, cy - h), cy + h)
        cells, pseg, _ = _band_segs(xr, yr)
        prog = [INIT, ops, "GOTO 30"]
        php = omsx_repl.run_cases(REF, [("stored", prog)], batch=False,
                                  capture=("vram_segs", pseg))[0]
        pts = _points(php, cells, xr, yr) if php else []
        out[label] = {"ops": ops, "cx": cx, "cy": cy, "pts": pts, "n": len(pts)}
        xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
        ext = (f"x{min(xs)}..{max(xs)}(w{max(xs)-min(xs)+1}) "
               f"y{min(ys)}..{max(ys)}(h{max(ys)-min(ys)+1})") if pts else "empty"
        print(f"  {label:12s} n={len(pts):3d}  {ext}")
    path = os.path.join(HERE, "g4_pointsets.json")
    with open(path, "w") as f:
        json.dump(out, f)
    print(f"  -> wrote {path}")


def clash():
    print("\n=== colour clash on a circle (CIRCLE(40,40),8,6) ===")
    # dump colour plane bytes of the covered cells
    cx, cy, r = 40, 40, 8
    xr = (cx - r - 1, cx + r + 1); yr = (cy - r - 1, cy + r + 1)
    cells, pseg, cseg = _band_segs(xr, yr)
    prog = [INIT, "CIRCLE(40,40),8,6", "GOTO 30"]
    col = omsx_repl.run_cases(REF, [("stored", prog)], batch=False,
                              capture=("vram_segs", cseg))[0]
    cb = bytes.fromhex(col) if col else b""
    seen = sorted({cb[i] for i in range(len(cb))})
    print("   colour bytes present:", " ".join(f"{v:02x}" for v in seen))


def rneg():
    print("\n=== negative radius (isolated; may be slow) ===")
    for r in ["-1"]:
        body = ["ON ERROR GOTO 40", f"SCREEN2:CIRCLE(30,30),{r},15",
                'SCREEN0:PRINT"K":END', 'SCREEN0:PRINT"E";ERR:END']
        out = omsx_repl.run_cases(REF, [("stored", body)], batch=False, reset=("NEW", "CLS"))[0]
        txt = " ".join("".join(out).split()) if out else ""
        print(f"  r={r:4s} -> raw={txt[:50]!r}")


def gxpos_pattern():
    print("\n=== GXPOS/GYPOS residue pattern (vary r, centre) ===")
    for cx, cy, r in [(30, 40, 10), (100, 50, 25), (60, 60, 5)]:
        body = [f"SCREEN2:CIRCLE({cx},{cy}),{r}",
                'SCREEN0:PRINT"GX";PEEK(&HFCB3)+256*PEEK(&HFCB4);',
                'PRINT"GY";PEEK(&HFCB5)+256*PEEK(&HFCB6)']
        out = omsx_repl.run_cases(REF, [("stored", body)], batch=False, reset=("NEW", "CLS"))[0]
        txt = " ".join("".join(out).split()) if out else ""
        m = re.search(r"GX\s*(-?\d+)\s*GY\s*(-?\d+)", txt)
        got = (int(m.group(1)), int(m.group(2))) if m else None
        print(f"  centre=({cx},{cy}) r={r:3d} -> GXPOS/GYPOS={got}   (r={r}, cy={cy})")


def aspect_round():
    print("\n=== aspect rounding (measure minor extent) ===")
    # r=20 aspect a -> minor = r*a (a<1) ; check round vs trunc via fractional targets
    cx = cy = 80
    for a, tgt in [(".3", "6.0"), (".35", "7.0"), (".175", "3.5"), (".075", "1.5")]:
        ops = f"CIRCLE({cx},{cy}),20,15,,,{a}"
        xr = (cx - 22, cx + 22); yr = (cy - 22, cy + 22)
        cells, pseg, _ = _band_segs(xr, yr)
        php = omsx_repl.run_cases(REF, [("stored", [INIT, ops, "GOTO 30"])], batch=False,
                                  capture=("vram_segs", pseg))[0]
        pts = _points(php, cells, xr, yr) if php else []
        ys = [p[1] for p in pts]
        h = (max(ys) - min(ys) + 1) if pts else 0
        yr_ = (h - 1) // 2
        print(f"  aspect={a:6s} (20*a={tgt}) -> height={h} => y-radius={yr_}")


def main():
    print("=== dump point-sets for host fitter ===")
    dump_pointsets()
    clash()
    rneg()
    gxpos_pattern()
    aspect_round()
    print("\n(done round 3)")


if __name__ == "__main__":
    main()
