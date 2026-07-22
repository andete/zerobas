#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""G3 LINE characterization round 2 (VG-8020): fix the round-1 mistakes (POINT was
read AFTER SCREEN0 -> text plane). Here every pixel read is a VRAM band dump while
still in SCREEN 2 (GOTO-self hold), and the error cases are boot-per-case with a
clear ERR print. Answers: THE CLIPPING MODEL (draw partial / no-op / error?),
exact ERR numbers, STEP-STEP relativity, continuation pixels."""
from __future__ import annotations
import os, sys, re
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

REF = os.environ.get("ZEROBAS_REF_MACHINE", "Philips_VG_8020")
INIT = "COLOR15,1,1:SCREEN2:CLS"


def band_segs(xr, yr):
    cols = range(xr[0] >> 3, (xr[1] >> 3) + 1)
    rows = range(yr[0] >> 3, (yr[1] >> 3) + 1)
    cells = [(cr, cc) for cr in rows for cc in cols]
    return cells, [(cr * 256 + cc * 8, 8) for cr, cc in cells]


def bitmap(hexstr, cells, xr, yr):
    b = bytes.fromhex(hexstr)
    idx = {cell: i for i, cell in enumerate(cells)}
    out = []
    for y in range(yr[0], yr[1] + 1):
        row = []
        for x in range(xr[0], xr[1] + 1):
            blk = idx[(y >> 3, x >> 3)] * 8 + (y & 7)
            bit = b[blk] & (0x80 >> (x & 7)) if blk < len(b) else 0
            row.append("#" if bit else ".")
        out.append("".join(row))
    return out


# Pixel band dumps (clip model + continuation + STEP-STEP), hold SCREEN2.
PIX = [
    # CLIP: line runs off top-left; ideal y=x through origin. Does the on-screen
    # part (0,0)-(50,50) get drawn (=> LINE CLIPS) or nothing (=> no-op)?
    ("clip_negTL",  "LINE(-100,-100)-(50,50),15",  (0, 24), (0, 24)),
    # CLIP: one endpoint far off the right/bottom. Ideal slope 190/510~0.373.
    ("clip_offBR",  "LINE(0,0)-(510,190),15",      (0, 24), (0, 12)),
    # fully off-screen: expect a blank band on-screen
    ("clip_alloff", "LINE(300,300)-(400,400),15",  (0, 24), (0, 24)),
    # continuation LINE-(x,y): from last point (3,3) to (3,10) -> vertical seg
    ("cont",        "PSET(3,3):LINE-(3,12),15",    (0, 8),  (0, 15)),
    # STEP-STEP relativity: PSET(10,10) then STEP(2,2)-STEP(3,3). If BOTH relative
    # to (10,10): (12,12)-(13,13). If 2nd relative to 1st endpoint: (12,12)-(15,15).
    ("step_step",   "PSET(10,10):LINE STEP(2,2)-STEP(3,3),15", (8, 23), (8, 23)),
    # LINE(x,y)-(x,y) degenerate (single point)
    ("degenerate",  "LINE(5,5)-(5,5),15",          (0, 12), (0, 12)),
]


def pixels():
    for label, ops, xr, yr in PIX:
        cells, seg = band_segs(xr, yr)
        prog = [INIT, ops, "GOTO 30"]
        hx = omsx_repl.run_cases(REF, [("stored", prog)], batch=False,
                                 capture=("vram_segs", seg))[0]
        print(f"\n-- {label}: {ops}   x{xr} y{yr}")
        if not hx:
            print("   <no capture>"); continue
        for r in bitmap(hx, cells, xr, yr):
            print("   " + r)


# Error cases boot-per-case, clear print. ERR printed as "E=<n>".
ERRC = [
    ("ovf_end_x",  ["ON ERROR GOTO 100", "SCREEN2:LINE(0,0)-(32768,0),15",
                    'PRINT"OK":END', 'PRINT"E=";ERR:END']),
    ("ovf_start",  ["ON ERROR GOTO 100", "SCREEN2:LINE(-32769,0)-(5,5),15",
                    'PRINT"OK":END', 'PRINT"E=";ERR:END']),
    ("scr0",       ["ON ERROR GOTO 100", "SCREEN0:LINE(0,0)-(10,10),15",
                    'PRINT"OK":END', 'PRINT"E=";ERR:END']),
    ("scr1",       ["ON ERROR GOTO 100", "SCREEN1:LINE(0,0)-(10,10),15",
                    'PRINT"OK":END', 'PRINT"E=";ERR:END']),
    # box in-range, but does ,B with color omitted then ,B work? (syntax survey)
    ("box_nocol",  ["ON ERROR GOTO 100", "SCREEN2:LINE(1,1)-(9,9),,B",
                    'PRINT"OK":END', 'PRINT"E=";ERR:END']),
]


def errors():
    for label, body in ERRC:
        out = omsx_repl.run_cases(REF, [("stored", body)], batch=False,
                                  reset=("NEW", "CLS"))[0]
        txt = " ".join("".join(out).split()) if out else ""
        m = re.search(r"(E=\s*\d+|OK)", txt)
        print(f"  {label:12s} -> {m.group(0) if m else '<none>'!r:8}   raw={txt[:60]!r}")


def main():
    print("=== CLIP MODEL + continuation + STEP-STEP (VRAM band, SCREEN2 held) ===")
    pixels()
    print("\n=== ERR numbers + syntax survey (boot-per-case) ===")
    errors()
    print("\n(done)")


if __name__ == "__main__":
    main()
