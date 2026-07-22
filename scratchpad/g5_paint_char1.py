#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""G5 PAINT black-box characterization on the Philips VG-8020, round 1.

Read-only investigation (nothing asserted): DUMP reference PAINT behaviour so the
G5 pins can be written from measured fact (the recurring arc lesson). No ROM
disassembly -- pure black box, mirrors g4_circle_char1.py.

Round 1 sections:
  C1 tokens   -- crunch of every PAINT form (grammar, STEP, omitted color/border,
                 MSX2-only tile$ form -> expect Syntax error on MSX1)
  C2 fill     -- draw a box (LINE ,B), PAINT interior a different colour with
                 border=box colour; capture BOTH pattern + colour planes -> shows
                 the filled extent AND how the colour attribute is written
  C4 defaults -- PAINT(x,y) with color and/or border omitted (what fills? what
                 bounds?)
  C5 workarea -- GRPAC/GXPOS after PAINT (seed? unchanged?)
  C6 errors   -- SCREEN0/1, colour/border >15, coord overflow, seed off-screen,
                 seed already ON the border colour, PAINT in an open field
"""
from __future__ import annotations
import os, sys, re
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

REF = os.environ.get("ZEROBAS_REF_MACHINE", "Philips_VG_8020")
TXTTAB = 0xF676
CTAB = 0x2000  # SCREEN 2 colour table base
INIT = "COLOR15,1,1:SCREEN2:CLS"


# ---- C1: token crunch -------------------------------------------------------
C1 = [
    "paint(50,50)",
    "paint(50,50),15",
    "paint(50,50),15,4",
    "paint step(5,5),15,4",
    "paint(50,50),,4",
    'paint(50,50),"AB",4',   # MSX2 tile$ form -> MSX1 Syntax error?
    "paint(50,50),15,4,7",   # extra arg -> Syntax error?
]


def c1_tokens():
    print("=== C1  PAINT token crunch (grammar) ===")
    specs = [("direct", [f"1 {b}"]) for b in C1]
    raws = omsx_repl.run_cases(REF, specs, batch=True, reset=("NEW",),
                               capture=("stored_line", TXTTAB), cart=None)
    for b, raw in zip(C1, raws):
        rb = bytes.fromhex(raw) if raw else b""
        body = rb[4:] if len(rb) >= 5 else b""
        s = " ".join(f"{x:02X}" for x in body) if body else "<not stored>"
        print(f"  {b:26s} -> {s}")


# ---- pixel-plane helpers (mirror g4) ----------------------------------------
def _band(x0, y0, x1, y1, pad=1):
    x0 = max(0, min(x0, x1) - pad); y0 = max(0, min(y0, y1) - pad)
    x1 = max(x0, x1) + pad; y1 = max(y0, y1) + pad
    return (x0, x1), (y0, y1)


def _band_segs(xr, yr, base=0):
    cols = range(xr[0] >> 3, (xr[1] >> 3) + 1)
    rows = range(yr[0] >> 3, (yr[1] >> 3) + 1)
    cells = [(cr, cc) for cr in rows for cc in cols]
    seg = [(base + cr * 256 + cc * 8, 8) for cr, cc in cells]
    return cells, seg


def _byte_at(hexbytes, cells, x, y):
    b = hexbytes
    idx = {cell: i for i, cell in enumerate(cells)}
    cell = (y >> 3, x >> 3)
    blk = idx[cell] * 8 + (y & 7)
    return b[blk] if blk < len(b) else 0


def _render(php, chp, cells, xr, yr):
    """Render pattern (# set / . clear) + a colour-plane hex summary per row."""
    pb = bytes.fromhex(php) if php else b""
    cb = bytes.fromhex(chp) if chp else b""
    rows = []
    for y in range(yr[0], yr[1] + 1):
        pbyte_line = []
        for x in range(xr[0], xr[1] + 1):
            v = _byte_at(pb, cells, x, y)
            bit = v & (0x80 >> (x & 7))
            pbyte_line.append("#" if bit else ".")
        # colour byte for the first cell-column of this row (fg|bg nibbles)
        cvals = []
        for cc in range(xr[0] >> 3, (xr[1] >> 3) + 1):
            cvals.append(f"{_byte_at(cb, cells, cc*8, y):02X}")
        rows.append("".join(pbyte_line) + "   [" + " ".join(cvals) + "]")
    return rows


def _capture_scene(prog, box):
    x0, y0, x1, y1 = box
    xr, yr = _band(x0, y0, x1, y1, pad=2)
    cells, pseg = _band_segs(xr, yr, base=0)
    _, cseg = _band_segs(xr, yr, base=CTAB)
    php = omsx_repl.run_cases(REF, [("stored", prog)], batch=False,
                              capture=("vram_segs", pseg))[0]
    chp = omsx_repl.run_cases(REF, [("stored", prog)], batch=False,
                              capture=("vram_segs", cseg))[0]
    return _render(php, chp, cells, xr, yr), xr, yr


# ---- C2: basic bounded fill -------------------------------------------------
def c2_fill():
    print("\n=== C2  bounded fill: box colour15, PAINT interior 4 border 15 ===")
    box = (16, 16, 40, 40)
    prog = [INIT, "LINE(16,16)-(40,40),15,B", "PAINT(28,28),4,15", "GOTO 40"]
    rows, xr, yr = _capture_scene(prog, box)
    print(f"  x{xr} y{yr}  (pattern | [colour bytes per 8-col])")
    for y, r in zip(range(yr[0], yr[1] + 1), rows):
        print(f"   y{y:3d} {r}")


# ---- C4: defaults -----------------------------------------------------------
def c4_defaults():
    for label, paintstmt in [
        ("nocolor_noborder", "PAINT(28,28)"),
        ("color_noborder",   "PAINT(28,28),4"),
        ("nocolor_border",   "PAINT(28,28),,15"),
    ]:
        print(f"\n=== C4  {label}: box15  {paintstmt} ===")
        box = (16, 16, 40, 40)
        prog = [INIT, "LINE(16,16)-(40,40),15,B", paintstmt, "GOTO 40"]
        rows, xr, yr = _capture_scene(prog, box)
        for y, r in zip(range(yr[0], yr[1] + 1), rows):
            print(f"   y{y:3d} {r}")


# ---- C5: work area ----------------------------------------------------------
def c5_workarea():
    print("\n=== C5  work area after PAINT ===")
    cases = [
        ("grpac", ["SCREEN2:PSET(5,5):LINE(16,16)-(40,40),15,B:PAINT(28,28),4,15",
                   'SCREEN0:PRINT"G";PEEK(&HFCB7)+256*PEEK(&HFCB8);PEEK(&HFCB9)+256*PEEK(&HFCBA)'], "G"),
        ("gxpos", ["SCREEN2:PSET(5,5):LINE(16,16)-(40,40),15,B:PAINT(28,28),4,15",
                   'SCREEN0:PRINT"X";PEEK(&HFCB3)+256*PEEK(&HFCB4);PEEK(&HFCB5)+256*PEEK(&HFCB6)'], "X"),
    ]
    specs = [("stored", p) for (l, p, _) in cases]
    outs = omsx_repl.run_cases(REF, specs, batch=True, reset=("NEW",),
                               capture="screen", cart=None)
    for (l, _, tag), o in zip(cases, outs):
        txt = " ".join((o or "").split())
        m = re.search(re.escape(tag) + r"[ \d\-]*", txt)
        print(f"  {l:8s} -> {m.group(0).strip() if m else '<none>'}   raw={txt[:40]!r}")


# ---- C6: errors / edges -----------------------------------------------------
def c6_errors():
    print("\n=== C6  errors / edges (K=ok, E<n>=err) ===")
    err = [
        ("scr0",       "SCREEN0:PAINT(28,28),4,15"),
        ("scr1",       "SCREEN1:PAINT(28,28),4,15"),
        ("color16",    "SCREEN2:PAINT(28,28),16,15"),
        ("border16",   "SCREEN2:PAINT(28,28),4,16"),
        ("colorneg",   "SCREEN2:PAINT(28,28),-1,15"),
        ("coord_ovf",  "SCREEN2:PAINT(32768,0),4,15"),
        ("seed_off",   "SCREEN2:PAINT(300,300),4,15"),
        ("seed_negoff","SCREEN2:PAINT(-5,-5),4,15"),
    ]
    progs = []
    for l, stmt in err:
        progs.append(("stored", ["ON ERROR GOTO 40", stmt,
                          'SCREEN0:PRINT"K":END', 'SCREEN0:PRINT"E";ERR:END']))
    outs = omsx_repl.run_cases(REF, progs, batch=True, reset=("NEW",),
                               capture="screen", cart=None)
    for (l, _), o in zip(err, outs):
        toks = [ln.strip() for ln in (o or "").splitlines()
                if ln.strip().startswith("K") or ln.strip().startswith("E")]
        print(f"  {l:12s} -> {toks}")


if __name__ == "__main__":
    c1_tokens()
    c2_fill()
    c4_defaults()
    c5_workarea()
    c6_errors()
