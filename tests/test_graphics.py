# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Unit test: graphics pixel-math leaves, no emulator (msxtest Z80 sim).

G1 (docs/spec-basic-graphics-g1.md §6): sub/graphics.asm `gfx_calc_addr` — the
SCREEN-2 (x,y) -> pattern-byte address + mask primitive.

G2 (docs/spec-basic-graphics-g2.md §8): the pure-math leaves G2 adds --
  * gfx_color_rmw     the colour-clash decision (sub/graphics.asm)  [rom_base=0]
  * gfx_point_extract the POINT pixel-colour read (sub/graphics.asm) [rom_base=0]
  * gfx_in_range      the resident on-screen range test (basic/graphics.asm)
                      -- repack-only, so built from main-reloc.asm [rom_base=$2812]

Oracle: the VG-8020 black-box pins (spec-basic-graphics.md §11.2/§11.3/§11.8 and
the G2 capture pass). Emulator-free -- assembles the real asm and drives it by
label. Locks the logic the load-bearing VG-8020 differential (basic_probe_
graphics.py) proves. Never ROM disassembly.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from msxtest import Machine, carry  # noqa: E402

SUB_ROM = "/tmp/zb_graphics_sub.rom"
SUB_SYM = "/tmp/zb_graphics_sub.sym"
RES_ROM = "/tmp/zb_graphics_res.rom"
RES_SYM = "/tmp/zb_graphics_res.sym"
RELOC_BASE = 0x2812

# --- gfx_calc_addr (G1): (x,y) -> (pattern byte addr, MSB-first mask) ---------
ADDR_CASES = [
    # x,   y,    addr,  mask
    (0,   0,     0,    0x80),   # origin
    (8,   0,     8,    0x80),   # next char column -> +8 bytes
    (0,   8,   256,    0x80),   # next char row    -> +256 bytes
    (3,   0,     0,    0x10),   # x&7=3 -> $80>>3
    (255, 191, 6143,   0x01),   # bottom-right pixel
    (1,   0,     0,    0x40),
    (7,   0,     0,    0x01),
    (9,   0,     8,    0x40),
    (128, 96, 3200,    0x80),
    (255, 0,   248,    0x01),
    (0,   191, 5895,   0x80),
]

# --- gfx_color_rmw (G2): in A=c, B=cur -> CF(set/clear) + A(new colour) --------
# Oracle: spec-basic-graphics.md §11.3. cur = hi(fg)|lo(bg); if c == bg nibble
# -> CLEAR (CF=0, colour untouched); else SET (CF=1, new = (c<<4)|bg).
#   (c,   cur,   set?, new_colour_if_set)
RMW_CASES = [
    (15, 0x04, True,  0xF4),   # PSET(0,0),15 after COLOR15,4 -> $F4 (§11.3)
    (6,  0xF4, True,  0x64),   # clash: PSET(1,0),6 rewrites the shared fg nibble -> $64
    (4,  0xF4, False, None),   # c == bg(4) -> clear the bit, colour untouched
    (1,  0x04, True,  0x14),   # disambiguation: bg=4, c=1 -> set, $14
    (13, 0x04, True,  0xD4),   # omitted-c PSET uses FORCLR=13 -> $D4
    (6,  0x64, True,  0x64),   # PRESET(0,0),6 == PSET,6 (§11.3)
    (0,  0x40, True,  0x00),   # c=0 (bg nibble 0) differs from cur bg(0)? bg=0,c=0 -> clear
]
# fix the last case: cur=0x40 -> bg nibble = 0, c=0 == bg -> CLEAR
RMW_CASES[-1] = (0, 0x40, False, None)

# --- gfx_point_extract (G2): in A=pattern, B=mask, C=colour -> A=nibble --------
#   bit set -> hi (fg) nibble ; bit clear -> lo (bg) nibble
#   (pattern, mask, colour, expected_nibble)
POINT_CASES = [
    (0x80, 0x80, 0xD4, 13),   # bit set, colour fg13|bg4 -> 13
    (0x00, 0x80, 0xD4, 4),    # bit clear -> bg 4
    (0x40, 0x40, 0x94, 9),    # bit set (mid mask), fg9|bg4 -> 9
    (0x00, 0x01, 0x94, 4),    # bit clear -> bg 4
    (0xFF, 0x01, 0x2A, 2),    # bit set, fg2|bg10 -> 2
]

# --- gfx_in_range (G2): in BC=x, DE=y (int16) -> CF=1 iff on-screen -----------
#   (x, y, in_range?)
RANGE_CASES = [
    (0, 0, True), (255, 191, True), (255, 0, True), (0, 191, True),
    (100, 100, True), (128, 96, True),
    (256, 0, False), (0, 192, False), (300, 100, False), (32767, 0, False),
    (0xFFFF, 0, False),      # -1
    (0, 0xFFFF, False),      # y = -1
    (100, 192, False),
]


# --- gfx_abs16 (G3): HL=|HL|, A=$01 if orig>=0 else $FF -----------------------
ABS_CASES = [
    (0, 0, 0x01), (5, 5, 0x01), (0x7FFF, 0x7FFF, 0x01),
    (-1, 1, 0xFF), (-5, 5, 0xFF), (-0x8000, 0x8000, 0xFF), (-100, 100, 0xFF),
]

# --- gfx_bres_init/next (G3): the Bresenham point set -------------------------
# Oracle: the VG-8020 captured bitmaps (scratchpad/g3_line_char.out). pybres()
# replicates the fitted variant (err=dmaj>>1, step when err>=dmaj, major sorted
# ascending) and is asserted == the captured ground truth below; the asm is then
# asserted == pybres over a battery -> asm == reference, transitively.
CAPTURED = {
    (0, 0, 20, 7): {(x, y) for y, xs in {
        0: [0, 1], 1: [2, 3, 4], 2: [5, 6, 7], 3: [8, 9], 4: [10, 11, 12],
        5: [13, 14, 15], 6: [16, 17, 18], 7: [19, 20]}.items() for x in xs},
    (0, 0, 7, 20): {(x, y) for x, ys in {
        0: [0, 1], 1: [2, 3, 4], 2: [5, 6, 7], 3: [8, 9], 4: [10, 11, 12],
        5: [13, 14, 15], 6: [16, 17, 18], 7: [19, 20]}.items() for y in ys},
    (0, 0, 15, 15): {(i, i) for i in range(16)},
    (0, 15, 15, 0): {(x, 15 - x) for x in range(16)},
}
# battery for asm == pybres (both directions -> direction independence; axis-aligned)
BRES_LINES = list(CAPTURED) + [
    (20, 7, 0, 0), (7, 20, 0, 0), (15, 15, 0, 0), (15, 0, 0, 15),  # reversed
    (0, 2, 20, 2), (3, 0, 3, 20), (5, 5, 5, 5),                     # horiz/vert/degenerate
    (0, 0, 200, 70), (200, 70, 0, 0), (10, 100, 100, 10),          # bigger, both dirs
]


def pybres(x0, y0, x1, y1):
    dx, dy = abs(x1 - x0), abs(y1 - y0)
    steep = dy > dx
    if steep:
        x0, y0, x1, y1, dx, dy = y0, x0, y1, x1, dy, dx
    if x0 > x1:
        x0, y0, x1, y1 = x1, y1, x0, y0
    sy = 1 if y1 >= y0 else -1
    err, y, pts = dx >> 1, y0, set()
    for x in range(x0, x1 + 1):
        pts.add((y, x) if steep else (x, y))
        err += dy
        if err >= dx:
            y += sy
            err -= dx
    return pts


def _rd16s(m, name):
    b = m.peek(m.addr(name), 2)
    v = b[0] | (b[1] << 8)
    return v - 0x10000 if v >= 0x8000 else v


def zbres(m, x0, y0, x1, y1):
    """Drive the real asm rasteriser: poke endpoints, init, then step, collecting
    the visited (CX,CY) points exactly as gfx_draw_seg's loop would plot them."""
    for name, val in (("GFX_X1", x0), ("GFX_Y1", y0), ("GFX_X2", x1), ("GFX_Y2", y1)):
        m.poke_w(m.addr(name), val & 0xFFFF)
    m.call("gfx_bres_init")
    pts = [(_rd16s(m, "GFX_CX"), _rd16s(m, "GFX_CY"))]
    cnt = int.from_bytes(m.peek(m.addr("GFX_CNT"), 2), "little")
    for _ in range(cnt):
        m.call("gfx_bres_next")
        pts.append((_rd16s(m, "GFX_CX"), _rd16s(m, "GFX_CY")))
    return set(pts)


def build_sub():
    subprocess.run(["pasmo", "-I", os.path.join(ROOT, "sub"), "--bin",
                    os.path.join(ROOT, "sub", "sub.asm"), SUB_ROM, SUB_SYM],
                   check=True, capture_output=True, cwd=ROOT)


def build_reloc():
    subprocess.run(["pasmo", "--bin",
                    os.path.join(ROOT, "basic", "main-reloc.asm"), RES_ROM, RES_SYM],
                   check=True, capture_output=True, cwd=ROOT)


def run():
    fails = 0

    def check(ok, msg):
        nonlocal fails
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL'} {msg}")

    # --- sub-ROM leaves (rom_base=0) ---
    build_sub()
    m = Machine(SUB_ROM, SUB_SYM, rom_base=0)

    for x, y, want_addr, want_mask in ADDR_CASES:
        cpu = m.call("gfx_calc_addr", d=y, e=x)
        check(cpu.hl == want_addr and cpu.c == want_mask,
              f"gfx_calc_addr x={x:>3} y={y:>3} -> addr={cpu.hl:>5} "
              f"(want {want_addr:>5}) mask=${cpu.c:02X} (want ${want_mask:02X})")

    for c, cur, want_set, want_new in RMW_CASES:
        cpu = m.call("gfx_color_rmw", a=c, b=cur)
        got_set = carry(cpu)
        ok = got_set == want_set and (not want_set or cpu.a == want_new)
        detail = f"CF={int(got_set)} A=${cpu.a:02X}" if got_set else f"CF={int(got_set)} (clear)"
        check(ok, f"gfx_color_rmw c={c:>2} cur=${cur:02X} -> {detail}"
                  + ("" if ok else f"  want set={want_set} new={want_new}"))

    for pat, mask, col, want in POINT_CASES:
        cpu = m.call("gfx_point_extract", a=pat, b=mask, c=col)
        check(cpu.a == want,
              f"gfx_point_extract pat=${pat:02X} mask=${mask:02X} col=${col:02X} "
              f"-> {cpu.a} (want {want})")

    # --- gfx_abs16 (G3) ---
    for v, want_abs, want_sign in ABS_CASES:
        cpu = m.call("gfx_abs16", h=(v >> 8) & 0xFF, l=v & 0xFF)
        check(cpu.hl == want_abs and cpu.a == want_sign,
              f"gfx_abs16 {v:>7} -> |{cpu.hl}| (want {want_abs}) "
              f"sign=${cpu.a:02X} (want ${want_sign:02X})")

    # --- pybres == the VG-8020 captured bitmaps (locks the oracle generator) ---
    for line, want in CAPTURED.items():
        got = pybres(*line)
        check(got == want, f"pybres{line} == captured VG-8020 bitmap "
              f"({len(got)} pts)" + ("" if got == want else f"  DIFF {got ^ want}"))

    # --- the asm rasteriser == pybres over the battery (=> == reference) -------
    for line in BRES_LINES:
        want = pybres(*line)
        got = zbres(m, *line)
        check(got == want, f"gfx_bres {line} -> {len(got)} pts"
              + ("" if got == want else f"  DIFF asm^py={sorted(got ^ want)[:6]}"))

    # --- resident leaf (repack build, rom_base=$2812) ---
    build_reloc()
    mr = Machine(RES_ROM, RES_SYM, rom_base=RELOC_BASE)
    for x, y, want in RANGE_CASES:
        cpu = mr.call("gfx_in_range", b=(x >> 8) & 0xFF, c=x & 0xFF,
                      d=(y >> 8) & 0xFF, e=y & 0xFF)
        got = carry(cpu)
        check(got == want,
              f"gfx_in_range x={x:>5} y={y:>5} -> {'in' if got else 'off':>3} "
              f"(want {'in' if want else 'off'})")

    print("-------------------")
    print("test_graphics:", "PASS" if fails == 0 else f"FAIL ({fails})")
    return fails


if __name__ == "__main__":
    sys.exit(1 if run() else 0)
