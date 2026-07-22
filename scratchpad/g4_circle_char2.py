#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""G4 CIRCLE characterization round 2 (VG-8020): errors isolated (fresh boot per
case so one hang can't poison the batch), GXPOS/GYPOS re-measure, aspect-ratio
scaling, and start/end-angle arcs. Read-only, no ROM disassembly."""
from __future__ import annotations
import os, sys, re
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
    return cells, pseg


def _bitmap(hexstr, cells, xr, yr):
    b = bytes.fromhex(hexstr)
    idx = {cell: i for i, cell in enumerate(cells)}
    rows = []
    for y in range(yr[0], yr[1] + 1):
        line = []
        for x in range(xr[0], xr[1] + 1):
            cell = (y >> 3, x >> 3)
            blk = idx[cell] * 8 + (y & 7)
            bit = b[blk] & (0x80 >> (x & 7)) if blk < len(b) else 0
            line.append("#" if bit else ".")
        rows.append("".join(line))
    return rows


def _draw_and_dump(ops, cx, cy, r, label):
    xr = (max(0, cx - r - 1), cx + r + 1)
    yr = (max(0, cy - r - 1), cy + r + 1)
    cells, pseg = _band_segs(xr, yr)
    prog = [INIT, ops, "GOTO 30"]
    php = omsx_repl.run_cases(REF, [("stored", prog)], batch=False,
                              capture=("vram_segs", pseg))[0]
    print(f"\n  -- {label}: {ops}")
    if not php:
        print("     <no capture>"); return
    rows = _bitmap(php, cells, xr, yr)
    for rr in rows:
        print("     " + rr)
    pts = [(x, y) for y in range(yr[0], yr[1] + 1) for x in range(xr[0], xr[1] + 1)
           if rows[y - yr[0]][x - xr[0]] == "#"]
    if pts:
        xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
        print(f"     x {min(xs)}..{max(xs)} (w={max(xs)-min(xs)+1})  "
              f"y {min(ys)}..{max(ys)} (h={max(ys)-min(ys)+1})  n={len(pts)}")


# ---- C6b: errors, one fresh boot each --------------------------------------
ERR_CASES = [
    ("r0",         "SCREEN2:CIRCLE(30,30),0,15"),
    ("rneg",       "SCREEN2:CIRCLE(30,30),-5,15"),
    ("center_off", "SCREEN2:CIRCLE(300,300),10,15"),
    ("center_neg", "SCREEN2:CIRCLE(-5,-5),10,15"),
    ("center_ovf", "SCREEN2:CIRCLE(32768,0),10,15"),
    ("r_ovf",      "SCREEN2:CIRCLE(0,0),32768,15"),
    ("scr0",       "SCREEN0:CIRCLE(30,30),10,15"),
    ("scr1",       "SCREEN1:CIRCLE(30,30),10,15"),
    ("aspect_neg", "SCREEN2:CIRCLE(30,30),10,15,,,-1"),
    ("badcolor",   "SCREEN2:CIRCLE(30,30),10,16"),
]


def c6_errors():
    print("=== C6b  errors (isolated boots) ===")
    for label, act in ERR_CASES:
        body = ["ON ERROR GOTO 40", act,
                'SCREEN0:PRINT"K":END', 'SCREEN0:PRINT"E";ERR:END']
        out = omsx_repl.run_cases(REF, [("stored", body)], batch=False,
                                  reset=("NEW", "CLS"))[0]
        txt = " ".join("".join(out).split()) if out else ""
        mk = re.search(r"\bK\b", txt); me = re.search(r"E\s*-?\d+", txt)
        ans = ("K (no error)" if mk and not me
               else (me.group(0).replace(' ', '') if me else "?(hang/empty)"))
        print(f"  {label:12s} -> {ans:16}  raw={txt[:40]!r}")


# ---- C5b: GXPOS/GYPOS after CIRCLE -----------------------------------------
def c5_workarea():
    print("\n=== C5b  work area after CIRCLE(30,40),10 (fresh) ===")
    body = ["SCREEN2:PSET(5,5):CIRCLE(30,40),10",
            'SCREEN0:PRINT"GX";PEEK(&HFCB3)+256*PEEK(&HFCB4);',
            'PRINT"GY";PEEK(&HFCB5)+256*PEEK(&HFCB6);',
            'PRINT"AX";PEEK(&HFCB7)+256*PEEK(&HFCB8);',
            'PRINT"AY";PEEK(&HFCB9)+256*PEEK(&HFCBA)']
    out = omsx_repl.run_cases(REF, [("stored", body)], batch=False, reset=("NEW", "CLS"))[0]
    print("   ", " ".join("".join(out).split())[:80] if out else "<empty>")


# ---- C3: aspect scaling ----------------------------------------------------
def c3_aspect():
    print("\n=== C3  aspect ratio scaling (CIRCLE(64,64),20,15,,,A) ===")
    for a in ["0.5", "1", "2", "3", ".25"]:
        ops = f"CIRCLE(64,64),20,15,,,{a}"
        _draw_and_dump(ops, 64, 64, 22, f"aspect={a}")


# ---- C4: start/end-angle arcs ----------------------------------------------
def c4_arcs():
    print("\n=== C4  start/end-angle arcs (CIRCLE(40,40),15,15,S,E) ===")
    # radians; MSX angle 0 = +x (right), pi/2 up or down? measure. 3.14~pi, 1.57~pi/2
    ARCS = [
        ("q_0_to_hpi",   "CIRCLE(40,40),15,15,0,1.57"),
        ("q_hpi_to_pi",  "CIRCLE(40,40),15,15,1.57,3.14"),
        ("half_0_to_pi", "CIRCLE(40,40),15,15,0,3.14"),
        ("neg_start",    "CIRCLE(40,40),15,15,-1.57,0"),   # negative -> also radius line?
        ("neg_both",     "CIRCLE(40,40),15,15,-0.1,-1.57"),
    ]
    for label, ops in ARCS:
        _draw_and_dump(ops, 40, 40, 17, label)


def main():
    c6_errors()
    c5_workarea()
    c3_aspect()
    c4_arcs()
    print("\n(done round 2)")


if __name__ == "__main__":
    main()
