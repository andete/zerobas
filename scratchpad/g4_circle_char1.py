#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""G4 CIRCLE black-box characterization on the Philips VG-8020, round 1.
Read-only investigation (nothing asserted): DUMP the reference behaviour so the
G4 pins can be written from measured fact (the recurring arc lesson). No ROM
disassembly -- pure black box, mirrors g3_line_characterize.py.

Round 1 sections:
  C1 tokens   -- stored-line crunch of every CIRCLE form (grammar, STEP, arcs, aspect)
  C2 pixels   -- exact pattern plane for plain circles r=4/8/12/20 (default aspect):
                 reveals BOTH the midpoint octant variant AND the default aspect
                 (compare x-extent vs y-extent of the drawn shape)
  C5 workarea -- GRPAC/GXPOS after CIRCLE (centre? last octant point?)
  C6 errors   -- r=0, r<0, off-screen centre (clip vs err), SCREEN0/1, overflow
"""
from __future__ import annotations
import os, sys, re
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

REF = os.environ.get("ZEROBAS_REF_MACHINE", "Philips_VG_8020")
TXTTAB = 0xF676
INIT = "COLOR15,1,1:SCREEN2:CLS"


# ---- C1: token crunch -------------------------------------------------------
C1 = [
    "circle(30,30),10",
    "circle(30,30),10,15",
    "circle step(5,5),10",
    "circle(30,30),10,15,0,3.14",
    "circle(30,30),10,15,,,2",
    "circle(30,30),10,,,,0.5",
    "circle(30,30),10,15,-1,-2",
]


def c1_tokens():
    print("=== C1  CIRCLE token crunch (grammar) ===")
    specs = [("direct", [f"1 {b}"]) for b in C1]
    raws = omsx_repl.run_cases(REF, specs, batch=True, reset=("NEW",),
                               capture=("stored_line", TXTTAB), cart=None)
    for b, raw in zip(C1, raws):
        body = bytes.fromhex(raw)[4:] if raw and len(bytes.fromhex(raw)) >= 5 else b""
        s = " ".join(f"{x:02X}" for x in body) if body else "<not stored>"
        print(f"  {b:34s} -> {s}")


# ---- C2: exact pixel plane (default aspect) ---------------------------------
# centre chosen so the whole circle is on-screen for r<=20 and inside a small band.
PIX_CASES = [
    ("r4",  "CIRCLE(30,30),4,15",  (30, 4)),
    ("r8",  "CIRCLE(30,30),8,15",  (30, 8)),
    ("r12", "CIRCLE(40,40),12,15", (40, 12)),
    ("r20", "CIRCLE(50,50),20,15", (50, 20)),
]


def _band(cx, cy, r):
    x0, x1 = cx - r - 1, cx + r + 1
    y0, y1 = cy - r - 1, cy + r + 1
    x0 = max(0, x0); y0 = max(0, y0)
    return (x0, x1), (y0, y1)


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


def c2_pixels():
    print("\n=== C2  exact pattern plane, default aspect (VG-8020) ===")
    for label, ops, (c, r) in PIX_CASES:
        cx = int(re.search(r"\((\d+),(\d+)\)", ops).group(1))
        cy = int(re.search(r"\((\d+),(\d+)\)", ops).group(2))
        xr, yr = _band(cx, cy, r)
        cells, pseg = _band_segs(xr, yr)
        prog = [INIT, ops, "GOTO 30"]
        php = omsx_repl.run_cases(REF, [("stored", prog)], batch=False,
                                  capture=("vram_segs", pseg))[0]
        print(f"\n  -- {label}: {ops}   x{xr} y{yr}")
        if not php:
            print("     <no pattern capture>")
            continue
        rows = _bitmap(php, cells, xr, yr)
        for r_ in rows:
            print("     " + r_)
        # measure extents: width of widest row, height of tallest col
        set_pts = [(x, y) for y in range(yr[0], yr[1] + 1)
                   for x in range(xr[0], xr[1] + 1)
                   if rows[y - yr[0]][x - xr[0]] == "#"]
        if set_pts:
            xs = [p[0] for p in set_pts]; ys = [p[1] for p in set_pts]
            print(f"     x-extent {min(xs)}..{max(xs)} (w={max(xs)-min(xs)+1})  "
                  f"y-extent {min(ys)}..{max(ys)} (h={max(ys)-min(ys)+1})  npix={len(set_pts)}")


# ---- C5/C6 behavioural ------------------------------------------------------
BEHAV = [
    # GRPAC after CIRCLE (centre or last point?)  GRPACX=$FCB7 GRPACY=$FCB9
    ("grpac",       ["SCREEN2:PSET(5,5):CIRCLE(30,40),10",
                     'SCREEN0:PRINT"G";PEEK(&HFCB7)+256*PEEK(&HFCB8);PEEK(&HFCB9)+256*PEEK(&HFCBA)'], "G"),
    ("gxpos",       ["SCREEN2:PSET(5,5):CIRCLE(30,40),10",
                     'SCREEN0:PRINT"X";PEEK(&HFCB3)+256*PEEK(&HFCB4);PEEK(&HFCB5)+256*PEEK(&HFCB6)'], "X"),
    # errors (ON ERROR funnel -> E<err>, success -> K)
    ("r0",          ["ON ERROR GOTO 40", "SCREEN2:CIRCLE(30,30),0,15",
                     'SCREEN0:PRINT"K":END', 'SCREEN0:PRINT"E";ERR:END'], None),
    ("rneg",        ["ON ERROR GOTO 40", "SCREEN2:CIRCLE(30,30),-5,15",
                     'SCREEN0:PRINT"K":END', 'SCREEN0:PRINT"E";ERR:END'], None),
    ("center_off",  ["ON ERROR GOTO 40", "SCREEN2:CIRCLE(300,300),10,15",
                     'SCREEN0:PRINT"K":END', 'SCREEN0:PRINT"E";ERR:END'], None),
    ("center_ovf",  ["ON ERROR GOTO 40", "SCREEN2:CIRCLE(32768,0),10,15",
                     'SCREEN0:PRINT"K":END', 'SCREEN0:PRINT"E";ERR:END'], None),
    ("r_big",       ["ON ERROR GOTO 40", "SCREEN2:CIRCLE(128,96),200,15",
                     'SCREEN0:PRINT"K":END', 'SCREEN0:PRINT"E";ERR:END'], None),
    ("scr0",        ["ON ERROR GOTO 40", "SCREEN0:CIRCLE(30,30),10,15",
                     'PRINT"K":END', 'PRINT"E";ERR:END'], None),
    ("scr1",        ["ON ERROR GOTO 40", "SCREEN1:CIRCLE(30,30),10,15",
                     'PRINT"K":END', 'PRINT"E";ERR:END'], None),
    # clip: partly off-screen circle -> which on-screen points light?
    ("clip",        ["ON ERROR GOTO 40", "SCREEN2:COLOR15,1,1:CLS:CIRCLE(0,96),20,15",
                     'SCREEN0:PRINT"C";POINT(20,96)=15;POINT(0,76)=15;POINT(0,116)=15', 'PRINT"E";ERR:END'], "C"),
]


def c_behav():
    print("\n=== C5/C6  behavioural (GRPAC / errors / clip) ===")
    specs = [("stored", body) for _, body, _ in BEHAV]
    outs = omsx_repl.run_cases(REF, specs, batch=True, reset=("NEW", "CLS"))
    for (label, _, tag), raw in zip(BEHAV, outs):
        txt = " ".join("".join(raw).split()) if raw else ""
        if tag is None:
            mk = re.search(r"\bK\b", txt); me = re.search(r"E\s*-?\d+", txt)
            ans = ("K (no error)" if mk and not me
                   else (me.group(0).replace(' ', '') if me else "?"))
        else:
            m = re.search(re.escape(tag) + r"[ \d\-\.]*", txt)
            ans = m.group(0).strip() if m else "<none>"
        print(f"  {label:12s} -> {ans:16}  raw={txt[:46]!r}")


def main():
    c1_tokens()
    c2_pixels()
    c_behav()
    print("\n(done round 1)")


if __name__ == "__main__":
    main()
