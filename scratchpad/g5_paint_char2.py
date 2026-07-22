#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""G5 PAINT characterization round 2 (VG-8020) — THE CRUX.

Round-1 fix: capture pattern AND colour plane in ONE boot (consistent snapshot),
and render EFFECTIVE colour per pixel (fg nibble if bit set, else bg nibble) —
that is what the pixel actually displays and the only faithful view of a
SCREEN-2 colour-clash fill.

Scenes (each a bounded box so the whole result fits a small VRAM band):
  S1 basic   box col15, PAINT interior 4 border 15          (clean fill)
  S2 leak    box col15, PAINT interior 4 border 7 (!=box)   (does it leak out?)
  S3 clash   narrow box: interior 1 group wide, border+fill share a group
  S4 concave U-shaped wall inside the box (scanline-seed wrap test)
  S5 field   empty screen, PAINT(128,96),4,4 — capture 4 corners (edge clip)
  S6 brd16   box col15, PAINT interior 4 border 16          (border out-of-range)
  S7 tile    box col15, PAINT(28,28),"A",15 (MSX2 tile$)    (runtime err? K?)
"""
from __future__ import annotations
import os, sys, re
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

REF = os.environ.get("ZEROBAS_REF_MACHINE", "Philips_VG_8020")
CTAB = 0x2000
INIT = "COLOR15,1,1:SCREEN2:CLS"
HEX = "0123456789ABCDEF"


def _band(x0, y0, x1, y1, pad=2):
    x0 = max(0, min(x0, x1) - pad); y0 = max(0, min(y0, y1) - pad)
    x1 = max(x0, x1) + pad; y1 = max(y0, y1) + pad
    return (x0, x1), (y0, y1)


def _cells(xr, yr):
    cols = range(xr[0] >> 3, (xr[1] >> 3) + 1)
    rows = range(yr[0] >> 3, (yr[1] >> 3) + 1)
    return [(cr, cc) for cr in rows for cc in cols]


def capture_effcolor(prog, box, pad=2):
    """Return (eff_rows, xr, yr): eff_rows[i] is a string of hex-nibble effective
    colours (fg if pattern bit set, else bg) for each pixel in the band, from ONE
    boot (pattern+colour segments concatenated)."""
    x0, y0, x1, y1 = box
    xr, yr = _band(x0, y0, x1, y1, pad)
    cells = _cells(xr, yr)
    pseg = [(cr * 256 + cc * 8, 8) for cr, cc in cells]
    cseg = [(CTAB + cr * 256 + cc * 8, 8) for cr, cc in cells]
    hexcat = omsx_repl.run_cases(REF, [("stored", prog)], batch=False,
                                 capture=("vram_segs", pseg + cseg),
                                 step=4.0, cap_gap=4.0)[0]
    if not hexcat:
        return None, xr, yr
    allb = bytes.fromhex(hexcat)
    half = len(allb) // 2
    pat, col = allb[:half], allb[half:]
    idx = {cell: i for i, cell in enumerate(cells)}
    eff_rows, pat_rows = [], []
    for y in range(yr[0], yr[1] + 1):
        eff, pr = [], []
        for x in range(xr[0], xr[1] + 1):
            blk = idx[(y >> 3, x >> 3)] * 8 + (y & 7)
            pv = pat[blk] if blk < len(pat) else 0
            cv = col[blk] if blk < len(col) else 0
            bit = pv & (0x80 >> (x & 7))
            eff.append(HEX[(cv >> 4) if bit else (cv & 15)])
            pr.append("#" if bit else ".")
        eff_rows.append("".join(eff)); pat_rows.append("".join(pr))
    return (eff_rows, pat_rows), xr, yr


def show(label, prog, box, pad=2):
    print(f"\n=== {label} ===")
    res, xr, yr = capture_effcolor(prog, box, pad)
    if not res:
        print("  <no capture>"); return
    eff_rows, pat_rows = res
    print(f"  x{xr} y{yr}   effective colour (hex nibble per pixel)")
    for y, e, p in zip(range(yr[0], yr[1] + 1), eff_rows, pat_rows):
        print(f"   y{y:3d} {e}   {p}")


def main():
    show("S1 basic  box15 PAINT(28,28),4,15",
         [INIT, "LINE(16,16)-(40,40),15,B", "PAINT(28,28),4,15", "GOTO 40"],
         (16, 16, 40, 40))
    show("S2 leak   box15 PAINT(28,28),4,7  (border!=box)",
         [INIT, "LINE(16,16)-(40,40),15,B", "PAINT(28,28),4,7", "GOTO 40"],
         (14, 14, 44, 44), pad=2)
    show("S3 clash  narrow box x=(18,29) PAINT interior 4 border15",
         [INIT, "LINE(18,18)-(29,34),15,B", "PAINT(23,26),4,15", "GOTO 40"],
         (18, 18, 29, 34))
    show("S4 concave U-wall inside box",
         [INIT, "LINE(16,16)-(40,40),15,B", "LINE(28,16)-(28,34),15",
          "PAINT(20,30),4,15", "GOTO 40"],
         (16, 16, 40, 40))
    show("S6 brd16  box15 PAINT(28,28),4,16",
         [INIT, "LINE(16,16)-(40,40),15,B", "PAINT(28,28),4,16", "GOTO 40"],
         (16, 16, 40, 40))
    # S7 tile runtime: does PAINT(x,y),"A",15 error on MSX1?
    prog7 = ["ON ERROR GOTO 40", 'SCREEN2:LINE(16,16)-(40,40),15,B:PAINT(28,28),"A",15',
             'SCREEN0:PRINT"K":END', 'SCREEN0:PRINT"E";ERR:END']
    o7 = omsx_repl.run_cases(REF, [("stored", prog7)], batch=False, capture="screen")[0]
    t7 = " ".join((o7 or "").split())
    m = re.search(r"[KE][ \d\-]*", t7)
    print(f"\n=== S7 tile PAINT(x,y),\"A\",15 -> {m.group(0).strip() if m else '?'}  raw={t7[:40]!r} ===")
    # S8 four-arg runtime: PAINT(x,y),4,15,7
    prog8 = ["ON ERROR GOTO 40", 'SCREEN2:PAINT(28,28),4,15,7',
             'SCREEN0:PRINT"K":END', 'SCREEN0:PRINT"E";ERR:END']
    o8 = omsx_repl.run_cases(REF, [("stored", prog8)], batch=False, capture="screen")[0]
    t8 = " ".join((o8 or "").split())
    m = re.search(r"[KE][ \d\-]*", t8)
    print(f"=== S8 four-arg PAINT(x,y),4,15,7 -> {m.group(0).strip() if m else '?'}  raw={t8[:40]!r} ===")


if __name__ == "__main__":
    main()
