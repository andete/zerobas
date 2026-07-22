#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""G3 LINE black-box characterization on the Philips VG-8020 (design input for
docs/spec-basic-graphics-g3.md). Read-only investigation: nothing is asserted,
we DUMP the reference behaviour so the G3 pins can be written from measured fact
(the recurring arc lesson). No ROM disassembly -- pure black box.

Sections:
  Q1 tokens      -- stored-line crunch of every LINE form (disambiguation)
  Q4/Q7/Q9 pixels-- exact pattern+colour plane for a battery of lines (band dump),
                    reconstructed to an ASCII bitmap so the Bresenham tie-breaking,
                    direction dependence, and colour clash are directly visible
  Q2/Q3/Q5/Q6/Q8 -- behavioural: clip vs no-op vs error, continuation, GRPAC after
                    LINE, box ,B/,BF, STEP  (POINT / PEEK probes, printed + captured)
"""
from __future__ import annotations
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

REF = os.environ.get("ZEROBAS_REF_MACHINE", "Philips_VG_8020")
TXTTAB = 0xF676


def paddr(x, y):
    return (y >> 3) * 256 + (x >> 3) * 8 + (y & 7)


# ---- Q1: token crunch -------------------------------------------------------
Q1 = [
    "line(0,0)-(10,10)",
    "line-(10,10)",
    "line(0,0)-(10,10),15",
    "line(0,0)-(10,10),15,b",
    "line(0,0)-(10,10),15,bf",
    "line(0,0)-(10,10),,b",
    "line step(1,1)-step(2,2)",
    "line(0,0)-step(10,10)",
    "line input a$",
]


def q1_tokens():
    print("=== Q1  LINE token crunch (disambiguation) ===")
    specs = [("direct", [f"1 {b}"]) for b in Q1]
    raws = omsx_repl.run_cases(REF, specs, batch=True, reset=("NEW",),
                               capture=("stored_line", TXTTAB), cart=None)
    for b, raw in zip(Q1, raws):
        body = bytes.fromhex(raw)[4:] if raw and len(bytes.fromhex(raw)) >= 5 else b""
        s = " ".join(f"{x:02X}" for x in body) if body else "<not stored>"
        print(f"  {b:26s} -> {s}")


# ---- Q4/Q7/Q9: exact pixel + colour plane (band dump) -----------------------
# Draw on a CLS'd bg-1 SCREEN 2 with fg 15, hold with GOTO-self, dump the pattern
# AND colour bytes of the char-cell band covering the line, reconstruct a bitmap.
INIT = "COLOR15,1,1:SCREEN2:CLS"

PIX_CASES = [
    ("horiz",       "LINE(0,2)-(20,2),15",          (0, 20), (0, 7)),
    ("vert",        "LINE(3,0)-(3,20),15",          (0, 7),  (0, 20)),
    ("diag45",      "LINE(0,0)-(15,15),15",         (0, 15), (0, 15)),
    ("shallow",     "LINE(0,0)-(20,7),15",          (0, 20), (0, 7)),
    ("steep",       "LINE(0,0)-(7,20),15",          (0, 7),  (0, 20)),
    ("negslope",    "LINE(0,15)-(15,0),15",         (0, 15), (0, 15)),
    ("rev_shallow", "LINE(20,7)-(0,0),15",          (0, 20), (0, 7)),   # Q9 vs 'shallow'
    ("box_b",       "LINE(1,1)-(14,10),15,B",       (0, 15), (0, 11)),  # Q6
    ("box_bf",      "LINE(1,1)-(14,10),15,BF",      (0, 15), (0, 11)),  # Q6
    ("clash_line",  "LINE(0,0)-(15,0),6",           (0, 15), (0, 1)),   # Q7 colour along a row
]


def _band_segs(xr, yr):
    cols = range(xr[0] >> 3, (xr[1] >> 3) + 1)
    rows = range(yr[0] >> 3, (yr[1] >> 3) + 1)
    cells = [(cr, cc) for cr in rows for cc in cols]
    pseg = [(cr * 256 + cc * 8, 8) for cr, cc in cells]
    cseg = [(0x2000 + cr * 256 + cc * 8, 8) for cr, cc in cells]
    return cells, pseg, cseg


def _bitmap(hexstr, cells, xr, yr):
    b = bytes.fromhex(hexstr)
    # map (cr,cc)->8-byte block index
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


def q_pixels():
    print("\n=== Q4/Q7/Q9  exact pattern+colour plane (VG-8020) ===")
    for label, ops, xr, yr in PIX_CASES:
        cells, pseg, cseg = _band_segs(xr, yr)
        prog = [INIT, ops, f"GOTO {30}"]
        php = omsx_repl.run_cases(REF, [("stored", prog)], batch=False,
                                  capture=("vram_segs", pseg))[0]
        col = omsx_repl.run_cases(REF, [("stored", prog)], batch=False,
                                  capture=("vram_segs", cseg))[0]
        print(f"\n  -- {label}: {ops}   x{xr} y{yr}")
        if not php:
            print("     <no pattern capture>")
            continue
        for r in _bitmap(php, cells, xr, yr):
            print("     " + r)
        # colour plane: one hex byte per char cell (row-major over cells)
        cb = bytes.fromhex(col) if col else b""
        # print colour byte of each 8x1 group actually touched (first byte of each cell block per row)
        print("     colour[cell,line]:", " ".join(
            f"{cb[i*8 + (yr[0] & 7)]:02x}" for i in range(len(cells))) if cb else "<none>")


# ---- Q2/Q3/Q5/Q6/Q8: behavioural -------------------------------------------
BEHAV = [
    # clip: draw a partly off-screen line; POINT the on-screen ideal-path points
    ("clip_partial", ["ON ERROR GOTO 100", "SCREEN2:COLOR15,1,1:CLS",
                      "LINE(0,0)-(510,190),15",   # slope ~ 0.3725; ideal passes (0,0)
                      "SCREEN0:PRINT\"C\";POINT(0,0)=15;POINT(255,95)=15;POINT(100,37)=15",
                      'PRINT"E";ERR:END'], "C"),
    ("fully_off",   ["ON ERROR GOTO 100", "SCREEN2:COLOR15,1,1:CLS",
                     "LINE(300,300)-(400,400),15",
                     "SCREEN0:PRINT\"F\";POINT(0,0)=15", 'PRINT"E";ERR:END'], "F"),
    ("neg_off",     ["ON ERROR GOTO 100", "SCREEN2:COLOR15,1,1:CLS",
                     "LINE(-100,-100)-(50,50),15",   # ideal y=x through origin
                     "SCREEN0:PRINT\"N\";POINT(0,0)=15;POINT(25,25)=15;POINT(50,50)=15",
                     'PRINT"E";ERR:END'], "N"),
    ("ovf_end",     ["ON ERROR GOTO 100", "SCREEN2:LINE(0,0)-(32768,0),15",
                     'SCREEN0:PRINT"O";0:END', 'SCREEN0:PRINT"E";ERR'], "E"),
    ("scr0_err",    ["ON ERROR GOTO 100", "SCREEN0:LINE(0,0)-(10,10),15",
                     'PRINT"K";0:END', 'PRINT"E";ERR'], "E"),
    # continuation + GRPAC after LINE (GRPACX=$FCB7, GRPACY=$FCB9)
    ("grpac_line",  ["SCREEN2:PSET(5,5):LINE(10,20)-(30,40)",
                     "SCREEN0:PRINT\"G\";PEEK(&HFCB7)+256*PEEK(&HFCB8);PEEK(&HFCB9)+256*PEEK(&HFCBA)"], "G"),
    ("cont_from",   ["SCREEN2:COLOR15,1,1:CLS:PSET(3,3):LINE-(3,10)",  # continue from (3,3)
                     "SCREEN0:PRINT\"D\";POINT(3,3)=15;POINT(3,6)=15;POINT(3,10)=15"], "D"),
    ("grpac_box",   ["SCREEN2:LINE(10,10)-(30,20),15,B",
                     "SCREEN0:PRINT\"B\";PEEK(&HFCB7)+256*PEEK(&HFCB8);PEEK(&HFCB9)+256*PEEK(&HFCBA)"], "B"),
    ("step_ends",   ["SCREEN2:COLOR15,1,1:CLS:PSET(10,10):LINE STEP(0,0)-STEP(5,5)",
                     "SCREEN0:PRINT\"S\";POINT(10,10)=15;POINT(15,15)=15;PEEK(&HFCB7)+256*PEEK(&HFCB8)"], "S"),
    ("nocolor_default", ["SCREEN2:COLOR7,1,1:CLS:LINE(0,0)-(5,0)",  # c omitted -> FORCLR=7
                         "SCREEN0:PRINT\"Z\";POINT(0,0);POINT(5,0)"], "Z"),
]


def q_behav():
    print("\n=== Q2/Q3/Q5/Q6/Q8  behavioural (clip / err / cont / GRPAC / box / STEP) ===")
    specs = [("stored", body) for _, body, _ in BEHAV]
    outs = omsx_repl.run_cases(REF, specs, batch=True, reset=("NEW", "CLS"))
    import re
    for (label, _, tag), raw in zip(BEHAV, outs):
        txt = " ".join("".join(raw).split()) if raw else ""
        m = re.search(re.escape(tag) + r"[ \d\-\.]*", txt)
        ans = m.group(0).strip() if m else "<none>"
        print(f"  {label:18s} -> {ans!r}")


def main():
    q1_tokens()
    q_pixels()
    q_behav()
    print("\n(done)")


if __name__ == "__main__":
    main()
