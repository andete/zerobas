#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-BFBYTE -- simulate the byte-wise fill BEFORE writing any Z80.

D-ARCMASK's rule: the sim runs ahead of the asm at every step. This models the
split exactly as `gbf_split` will compute it, renders both VRAM planes, and
checks them against EVERY plane reading D-BFPERF took from the VG-8020. If the
model cannot reproduce the reference here, no amount of assembler will.

The split, per scanline, with xl<=xr both already clamped to 0..255:

    fl = (xl + 7) >> 3          first cell wholly inside on the left
    fr = ((xr + 1) >> 3) - 1    last cell wholly inside
    whole bytes: cells fl..fr, when fl <= fr   (fr can be -1; fl can be 32,
                                                which is why both are computed
                                                in 16 bits, not 8)
    left  partial: xl..(xl|7)      iff xl & 7 != 0
    right partial: (xr & $F8)..xr  iff xr & 7 != 7

⚠️ THE 8-BIT TRAP THIS IS WRITTEN TO AVOID: xl+7 overflows a byte for xl>248
(255+7 = 262), and ((xr+1)>>3)-1 goes to -1 for xr<7. Computed in 8 bits,
`LINE(255,0)-(255,0),,BF` would report fl=0, fr=31 and blind-fill the whole
scanline. `edge_x255` below is that row.

    python3 -u scratchpad/bfbyte_sim.py
"""
from __future__ import annotations

W, H = 256, 192
BG = 4          # COLOR 15,4,7 -> every colour byte starts $04


def addr(x, y):
    return (y >> 3) * 256 + (x >> 3) * 8 + (y & 7)


class Planes:
    def __init__(self):
        self.pat = bytearray(6144)
        self.col = bytearray([BG] * 6144)

    def pixel(self, x, y, c):
        """The per-pixel read-modify-write: gfx_color_rmw's clash rule."""
        a = addr(x, y)
        m = 0x80 >> (x & 7)
        cb = self.col[a]
        fg, bg = cb >> 4, cb & 15
        if self.pat[a] & m:
            fg = c                      # already foreground -> restamp fg
        elif (self.pat[a] & ~m) == 0:
            fg = c                      # no other foreground pixel -> claim fg
        else:
            fg = c                      # clash: fg wins for the whole cell
        self.pat[a] |= m
        self.col[a] = (fg << 4) | bg

    def whole(self, cell, y, c):
        """THE FAST PATH: pattern blind-written $00, colour = C in the
        BACKGROUND nibble (fg forced to 0). Measured on the VG-8020 for C=15
        ($0f) and C=6 ($06), and over a pre-stained cell."""
        a = (y >> 3) * 256 + cell * 8 + (y & 7)
        self.pat[a] = 0x00
        self.col[a] = c                 # fg nibble 0, bg nibble C

    def fill_row(self, xl, xr, y, c):
        if xl > xr:
            xl, xr = xr, xl
        fl = (xl + 7) >> 3
        fr = ((xr + 1) >> 3) - 1
        if fl <= fr:
            for cell in range(fl, fr + 1):
                self.whole(cell, y, c)
            if xl & 7:
                for x in range(xl, (xl | 7) + 1):
                    self.pixel(x, y, c)
            if (xr & 7) != 7:
                for x in range(xr & 0xF8, xr + 1):
                    self.pixel(x, y, c)
        else:
            for x in range(xl, xr + 1):
                self.pixel(x, y, c)

    def bf(self, x1, y1, x2, y2, c):
        for y in range(min(y1, y2), max(y1, y2) + 1):
            self.fill_row(x1, x2, y, c)

    def line_h(self, x1, x2, y, c):
        for x in range(min(x1, x2), max(x1, x2) + 1):
            self.pixel(x, y, c)

    def read(self, base, n):
        return self.pat[base:base + n] if base < 0x2000 else \
            self.col[base - 0x2000:base - 0x2000 + n]


def hx(b):
    return b.hex()


# The MEASURED reference readings. cells 0..2 of cell-row 0 unless noted.
# (label, build(planes), expected pattern hex, expected colour hex)
CASES = [
    ("full_cell", lambda p: p.bf(0, 0, 7, 7, 15),
     "0000000000000000", "0f0f0f0f0f0f0f0f"),
    ("full_cell_c6", lambda p: p.bf(0, 0, 7, 7, 6),
     "0000000000000000", "0606060606060606"),
    ("full_cell_stained", lambda p: (p.line_h(0, 7, 0, 6), p.bf(0, 0, 7, 7, 15)),
     "0000000000000000", "0f0f0f0f0f0f0f0f"),
    ("half_cell", lambda p: p.bf(0, 0, 3, 7, 15),
     "f0f0f0f0f0f0f0f0", "f4f4f4f4f4f4f4f4"),
    ("line_not_fill", lambda p: p.line_h(0, 7, 0, 15),
     "ff00000000000000", "f404040404040404"),
    ("one_px", lambda p: p.bf(5, 3, 5, 3, 15),
     "0000000400000000", "040404f404040404"),
    ("c0_full", lambda p: p.bf(0, 0, 7, 7, 0),
     "0000000000000000", "0000000000000000"),
    ("teeth", lambda p: (p.bf(0, 0, 7, 7, 15), p.pixel(0, 0, 6)),
     "8000000000000000", "6f0f0f0f0f0f0f0f"),
]

# rows that span three cells: check all 24 bytes
SPAN = [
    ("fwd_span", lambda p: p.bf(3, 0, 20, 0, 15),
     "1f00000000000000" "0000000000000000" "f800000000000000",
     "f404040404040404" "0f04040404040404" "f404040404040404"),
    ("rev_span", lambda p: p.bf(20, 0, 3, 0, 15),
     "1f00000000000000" "0000000000000000" "f800000000000000",
     "f404040404040404" "0f04040404040404" "f404040404040404"),
    ("unaligned8", lambda p: p.bf(4, 0, 11, 0, 15),
     "0f00000000000000" "f000000000000000" "0000000000000000",
     "f404040404040404" "f404040404040404" "0404040404040404"),
]


def main() -> int:
    bad = 0
    print("=== D-BFBYTE: does the model reproduce the MEASURED reference? ===\n")
    for lbl, build, wp, wc in CASES:
        p = Planes()
        build(p)
        gp, gc = hx(p.read(0x0000, 8)), hx(p.read(0x2000, 8))
        ok = gp == wp and gc == wc
        bad += not ok
        print(f"  {'ok ' if ok else 'BAD'} {lbl:20} pattern={gp} colour={gc}")
        if not ok:
            print(f"      measured   pattern={wp} colour={wc}")
    for lbl, build, wp, wc in SPAN:
        p = Planes()
        build(p)
        gp, gc = hx(p.read(0x0000, 24)), hx(p.read(0x2000, 24))
        ok = gp == wp and gc == wc
        bad += not ok
        print(f"  {'ok ' if ok else 'BAD'} {lbl:20}")
        print(f"      model    pattern={gp}\n               colour={gc}")
        if not ok:
            print(f"      measured pattern={wp}\n               colour={wc}")

    print("\n=== the 8-bit traps, stated as splits ===")
    for xl, xr, why in [(255, 255, "edge_x255: xl+7 = 262 overflows a byte"),
                        (0, 6, "edge_short: fr = -1"),
                        (0, 255, "edge_full: every cell whole"),
                        (248, 255, "edge_last: the last cell, whole"),
                        (249, 255, "edge_lastpart: the last cell, partial")]:
        fl = (xl + 7) >> 3
        fr = ((xr + 1) >> 3) - 1
        n = fr - fl + 1 if fl <= fr else 0
        print(f"  xl={xl:3d} xr={xr:3d} -> fl={fl:2d} fr={fr:2d} whole={n:2d}"
              f"   {why}")

    print(f"\n=== model rows that MISS the measured reference: {bad} ===")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
