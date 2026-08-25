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
import decimal
import json
import os
from _tmp import tp
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from msxtest import Machine, carry, load_symbols  # noqa: E402

decimal.getcontext().prec = 40
D = decimal.Decimal


def poke_fpnum(m, base, value):
    """Write an FPNUM record (sign:1, dexp:2, dig:15) at `base` representing the
    exact decimal `value` (own copy of test_float.py's helper -- kept local so
    this file stays self-contained). 0 -> canonical zero."""
    value = D(value)
    if value == 0:
        m.poke(base, bytes(18))
        return
    sign = 0x80 if value < 0 else 0x00
    mag = -value if value < 0 else value
    digits, exp = mag.as_tuple().digits, mag.as_tuple().exponent
    dec_exp = len(digits) + exp
    dig14 = (list(digits) + [0] * 14)[:14]
    m.poke(base, bytes([sign]))
    m.poke_w(base + 1, dec_exp & 0xFFFF)
    m.poke(base + 3, bytes(dig14 + [0]))


# --- G4 CIRCLE (docs/spec-basic-graphics-g4.md) --------------------------------
# The TENANT (sub/graphics.asm, rom_base=0) and, since the G4 REVISED trig-free
# arc rewrite shrank the resident stub, the RESIDENT (ex_circle, basic/graphics.
# asm, rom_base=$2812 via main-reloc.asm) are both testable here.
G4_DATA = json.load(open(os.path.join(ROOT, "scratchpad", "g4_pointsets.json")))
G4_BND = json.load(open(os.path.join(ROOT, "scratchpad", "g4_arc_boundary_capture.json")))


def midpoint_circle_octants(r):
    """own-design integer midpoint circle (spec §4.1); the same function as
    scratchpad/g4_circle_fit.py's host-fit oracle."""
    pts = set()
    x, y = 0, r
    d = 1 - r
    while x <= y:
        for sx in (1, -1):
            for sy in (1, -1):
                pts.add((sx * x, sy * y))
                pts.add((sx * y, sy * x))
        if d < 0:
            d += 2 * x + 3
        else:
            d += 2 * (x - y) + 5
            y -= 1
        x += 1
    return pts


def gfx_scale_off(off, S):
    sign = 1 if off >= 0 else -1
    mag = (abs(off) * S + 128) >> 8
    return sign * mag


def py_cross_ge0(ax, ay, bx, by):
    return (ax * by - ay * bx) >= 0


SCALE_CASES = [
    (0, 256), (10, 256), (-10, 256), (20, 128), (-20, 128), (255, 256),
    (100, 64), (-100, 64), (7, 200), (-7, 200), (1, 1), (-1, 1), (0, 0),
    (255, 255), (-255, 255), (128, 200), (-128, 200),
]

CROSS_CASES = [
    (1, 0, 0, 1), (0, 1, 1, 0), (1, 1, -1, 1), (1, 1, 1, -1),
    (5, 0, 0, 5), (0, 0, 5, 5), (5, 5, 0, 0),
    (-3, 4, 4, 3), (4, 3, -3, 4),
    (100, 50, -50, 100), (-50, 100, 100, 50),
    (200, 200, 200, 200), (-1, -1, -1, -1), (-5, 0, 0, -5),
    (0, -5, -5, 0), (3, -4, -4, -3),
]


def _w16(v):
    return v & 0xFFFF


# --- D-ARCMASK (2026-08-17, docs/arcmask-msx1-characterization.md §5.5): -----
# the arc mask is a STEP-INDEX WEDGE. The angle is marshalled at SINGLE
# precision into (oct_raw, u14); the boundary is pos = (u14*M)>>14 into octant
# oct&7 with M = floor(r/sqrt(2)); a point is kept iff its normalized
# (octant, pos) pair lies in the closed cyclic interval [S, E]. The Python
# oracle below is the one the asm was simulated against BEFORE it was written
# (scratchpad/arcmask_asmsim2.py: 53/54 whole reference planes, 4/4 r=15
# point sets, 7/7 near-cardinal sweep). It replaces the retired cross-product
# oracle (rscale_vec_nudge / py_gfx_circ_bvec / py_arcbig_calc / PY_QTAB).
import math  # noqa: E402
from decimal import ROUND_DOWN, ROUND_HALF_UP  # noqa: E402

D4PI = D("1.27323954473516")     # 4/pi: 14 significant digits + guard, the
                                 # same record GFX_K_4PI carries


def py_bcd6(x):
    """P1 -- the SINGLE-precision model: 6 significant digits, half-up."""
    d = D(str(x))
    if d == 0:
        return D(0)
    return d.quantize(D(1).scaleb(d.adjusted() - 5), rounding=ROUND_HALF_UP)


def py_fp14(d):
    """a 14-significant-digit BCD result (the mathpack's width)."""
    if d == 0:
        return D(0)
    return d.quantize(D(1).scaleb(d.adjusted() - 13), rounding=ROUND_DOWN)


def py_marshal(theta):
    """cpt_boundary_prep: |angle| -> (oct_raw, u14), both trunc'd."""
    q = py_fp14(py_bcd6(theta) * D4PI)
    o = int(q)
    u = int(py_fp14((q - o) * 16384))
    return o, u


def py_mmax(r):
    """gfx_circ_wedge_prep's M: candidate multiply + the one floor
    correction. Equal to floor(r/sqrt(2)) on ALL 32768 radii (exhaustive,
    arcmask_asmsim2.py); the bare multiply is wrong on 410 of them."""
    m = (r * 46341) >> 16
    if 2 * m * m > r * r:
        m -= 1
    return m


def py_wedge(os_, us, oe_, ue, r):
    """gfx_circ_wedge_prep's boundary/flag outputs from the two records."""
    M = py_mmax(r)
    S = (os_ & 7, (us * M) >> 14)
    E = (oe_ & 7, (ue * M) >> 14)
    fullw = 1 if (S == E and (os_, us) != (oe_, ue)) else 0
    wrapf = 1 if (fullw == 0 and S > E) else 0
    return M, S, E, wrapf, fullw


def py_keep(M, S, E, wrapf, fullw, octant, qx):
    """gfx_circ_keep: the normalized pair compare."""
    if fullw:
        return True
    pos = qx if octant % 2 == 0 else M - qx
    o = octant
    if M:
        if pos >= M:
            o, pos = o + 1, pos - M
        if pos < 0:
            o, pos = o - 1, pos + M
    P = (o & 7, pos)
    if not wrapf:
        return S <= P <= E
    return P >= S or P <= E


def pymirror8(x, y):
    """gco_emit8's eight mirrors WITH their static octants, in call order."""
    return [((x, y), 6), ((x, -y), 1), ((-x, y), 5), ((-x, -y), 2),
            ((y, x), 7), ((y, -x), 0), ((-y, x), 4), ((-y, -x), 3)]


def py_spoke_vec(octant, pos, r):
    """gwp_spoke_vec: the octant point at a boundary, pre-minor-scale."""
    k = pos if octant % 2 == 0 else py_mmax(r) - pos
    last = None
    for qx, qy in pymidpoint(r):
        last = (qx, qy)
        if qx == k:
            break
    qx, qy = last
    for (vx, vy), o in pymirror8(qx, qy):
        if o == octant:
            return vx, vy


# (label, start_angle, end_angle) -- the 4 pinned arcs, re-used from G4_DATA
# for their (cx,cy,r) + captured point-set.
ARC_CASES = [
    ("arc_0_hpi", 0.0, 1.57), ("arc_hpi_pi", 1.57, 3.14),
    ("arc_wrap", 3.0, 1.0), ("arc_full628", 0.0, 6.28),
]


def zcirc_keep(m, arcf, M, S, E, wrapf, fullw, octant, qx):
    """Drive the REAL gfx_circ_keep: wedge cells + GFX_QX poked, octant in A."""
    m.poke(m.addr("GFX_ARCF"), arcf)
    m.poke_w(m.addr("GFX_M"), _w16(M))
    m.poke(m.addr("GFX_WS_O"), S[0])
    m.poke_w(m.addr("GFX_WS_P"), _w16(S[1]))
    m.poke(m.addr("GFX_WE_O"), E[0])
    m.poke_w(m.addr("GFX_WE_P"), _w16(E[1]))
    m.poke(m.addr("GFX_WRAPF"), wrapf)
    m.poke(m.addr("GFX_FULLW"), fullw)
    m.poke_w(m.addr("GFX_QX"), _w16(qx))
    cpu = m.call("gfx_circ_keep", a=octant)
    return carry(cpu)


def _rdw(m, name):
    b = m.peek(m.addr(name), 2)
    return b[0] | (b[1] << 8)


def zwedge_prep(m, soct, su14, eoct, eu14, r, sneg=0, eneg=0,
                aspmaj=0, asps=256):
    """Drive the REAL gfx_circ_wedge_prep end to end: pokes the two
    (oct_raw, u14) records + R/SNEG/ENEG/ASPMAJ/ASPS, calls it, returns
    (M, S, E, wrapf, fullw) read back from the wedge cells."""
    m.poke_w(m.addr("GFX_SOCT"), _w16(soct))
    m.poke_w(m.addr("GFX_SU14"), _w16(su14))
    m.poke_w(m.addr("GFX_EOCT"), _w16(eoct))
    m.poke_w(m.addr("GFX_EU14"), _w16(eu14))
    m.poke_w(m.addr("GFX_R"), _w16(r))
    m.poke(m.addr("GFX_SNEG"), sneg)
    m.poke(m.addr("GFX_ENEG"), eneg)
    m.poke(m.addr("GFX_ASPMAJ"), aspmaj)
    m.poke_w(m.addr("GFX_ASPS"), _w16(asps))
    m.call("gfx_circ_wedge_prep")
    M = _rdw(m, "GFX_M")
    S = (m.peek(m.addr("GFX_WS_O"))[0], _rdw(m, "GFX_WS_P"))
    E = (m.peek(m.addr("GFX_WE_O"))[0], _rdw(m, "GFX_WE_P"))
    return (M, S, E, m.peek(m.addr("GFX_WRAPF"))[0],
            m.peek(m.addr("GFX_FULLW"))[0])


def make_p1_tenant_machine():
    """A machine in the PAGE-1-TENANT memory map: main low-region float pack +
    main page-0 (from the reloc image at $2812) with the sub-ROM's page 1
    ($4000-$7FFF, the CIRCLE-parse tenant + its moved float glue) overlaid on top
    of main page 1. This is exactly what a page-1 CALSLT sees -- so the tenant's
    cpt_boundary_prep can call fp_cmp/fp_mul/... (low region, present) and read its
    own GFX_*_PI constants (sub page 1). Returns (machine, sub_symbols)."""
    m = Machine(RES_ROM, RES_SYM, rom_base=RELOC_BASE)
    sub_bytes = open(SUB_ROM, "rb").read()
    m.mem[0x4000:0x8000] = sub_bytes[0x4000:0x8000]   # overlay the sub tenant page 1
    return m, load_symbols(SUB_SYM)


def zboundary_prep_resident(mt, cpt_addr, theta_abs, dest="GFX_SOCT"):
    """Drive cpt_boundary_prep (the CIRCLE-parse tenant's D-ARCMASK
    single-precision marshal, sub/circleparse.asm) on the page-1 tenant
    machine `mt`: poke a canonical FPNUM into ARGA, point GFX_CS_AY at
    `dest`, call, return the (oct_raw, u14) record it wrote. Pass theta as a
    STRING for an exact BCD image of the BASIC literal."""
    poke_fpnum(mt, mt.addr("ARGA"), theta_abs)
    mt.poke_w(mt.addr("GFX_CS_AY"), mt.addr(dest))
    mt.call(cpt_addr)
    b = mt.peek(mt.addr(dest), 4)
    return b[0] | (b[1] << 8), b[2] | (b[3] << 8)


def zcirc_full_draw(m, cx, cy, r):
    """Drive the REAL gfx_circle_op loop end-to-end, including its OWN gco_loop
    termination test -- unlike zcirc_octant_steps, which drives gfx_circ_init/
    next via a PYTHON-decided "while x<=y" and never exercises the asm's own
    termination check. This is the actual site of the r=0 bug (signed vs.
    unsigned compare when QY goes negative -- see the G4 slice report)."""
    m.poke_w(m.addr("GFX_CXC"), _w16(cx))
    m.poke_w(m.addr("GFX_CYC"), _w16(cy))
    m.poke_w(m.addr("GFX_R"), _w16(r))
    m.poke(m.addr("GFX_ASPMAJ"), 0)
    m.poke_w(m.addr("GFX_ASPS"), 256)
    m.poke(m.addr("GFX_ARCF"), 0)
    m.poke(m.addr("GFX_C"), 15)
    m.call("gfx_circle_op", max_steps=200_000)


def zcirc_octant_steps(m, r):
    """Drive gfx_circ_init/gfx_circ_next (sub/graphics.asm); collect the raw
    (x,y) stepper sequence (pre-mirroring) -- mirrors zbres's role for the
    G3 Bresenham test below."""
    m.poke_w(m.addr("GFX_R"), _w16(r))
    m.call("gfx_circ_init")
    x, y = _rd16s(m, "GFX_QX"), _rd16s(m, "GFX_QY")
    steps = [(x, y)]
    while x <= y:
        m.call("gfx_circ_next")
        x, y = _rd16s(m, "GFX_QX"), _rd16s(m, "GFX_QY")
        if x <= y:
            steps.append((x, y))
    return steps


def pymirror(steps):
    pts = set()
    for x, y in steps:
        for sx in (1, -1):
            for sy in (1, -1):
                pts.add((sx * x, sy * y))
                pts.add((sx * y, sy * x))
    return pts

SUB_ROM = tp("zb_graphics_sub.rom")
SUB_SYM = tp("zb_graphics_sub.sym")
RES_ROM = tp("zb_graphics_res.rom")
RES_SYM = tp("zb_graphics_res.sym")
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

# --- gfx_bres_init at the $8000 fixed point (D-NEG8K) -------------------------
# docs/fixpoint8000-msx1-sweep.md §4.1. gfx_abs16($8000) returns $8000 -- the
# value is its own two's-complement negation, and ABS_CASES above already
# asserts that. This block asserts the half that makes it CORRECT rather than a
# defect: every consumer in gfx_bres_init reads that result as an UNSIGNED
# magnitude. GFX_CNT counts down with `dec hl` + an or-zero test, GFX_ERR is a
# LOGICAL `srl h / rr l`, and the steep test compares with `sbc hl,de` + CF. So
# a 32768-wide span is a real 32768 steps, not a wrapped -32768.
#
# Reachable from `LINE(-32768,0)-(0,0)`, which the emulator probe deliberately
# does NOT run (32768 masked plot steps -- see basic_probe_graphics.py's
# ovf_ok_min note, which picks a one-pixel span for exactly that reason). Here
# it costs one call and draws nothing.
# (x1, y1, x2, y2, dmaj, dmin, cnt, err, steep)
BRES_8000_CASES = [
    (-0x8000, 0, 0, 0, 0x8000, 0, 0x8000, 0x4000, 0),   # dx = +$8000, x-major
    (0, 0, -0x8000, 0, 0x8000, 0, 0x8000, 0x4000, 0),   # dx = -$8000, same magnitude
    # y-major: the swap makes DMAJ the LARGER of the two (ady), DMIN adx --
    # this row's expectation was written INVERTED first and the test corrected
    # it; the source says so in as many words ("steep (y-major): DMAJ=ady,
    # DMIN=adx (swap)") and the prediction was made without re-reading it.
    (0, -0x8000, 0, 0, 0x8000, 0, 0x8000, 0x4000, 1),   # dy = $8000 -> y-major
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


# --- G5 PAINT (docs/spec-basic-graphics-g5.md) -----------------------------
# The tenant's span-fill engine (sub/graphics.asm gfx_paint_flood/_process/
# _scan_row + the GFX_PSTK stack) is pure RAM-and-VDP-access logic; msxtest has
# no VDP model (the real hardware colour-clash/latch behaviour is differential-
# only, probes/basic_probe_graphics.py), so gfx_border_read (the border test's
# VDP read) and gfx_paint_plot (the paint) are TRAPPED against a host-side
# "virtual screen" dict {(x,y): colour} -- everything ELSE under test (the span
# stack, the extend/scan/push/pop control flow) is the REAL assembled tenant.
def py_paint_flood(screen, w, h, seed, C, B):
    """Own-design oracle mirroring gfx_paint_inside's own rule EXACTLY: 4-
    connected flood from seed, painting C, stopping a walk at a pixel whose
    colour is already B OR already C (see sub/graphics.asm gfx_paint_op's
    header for why "already C" is needed, not just "!=B" -- the teeth test
    below). BIT-AWARE (matches the gfx_paint_read/gfx_paint_inside VG-8020
    bug fix, sub/graphics.asm): a pixel not present in `screen` is UNDRAWN
    background -- it can never be a B-border (only an actual drawn pixel can
    be), it is only short-circuited by the "already C" rule. `screen` (the
    virtual VDP model this whole test file uses) already encodes "drawn" as
    "has an entry" -- a fixture never stores a drawn pixel whose colour is 0,
    so this is a faithful mapping, not a new fixture requirement. screen is
    mutated in place; returns the painted-pixel set."""
    def inside(x, y):
        if not (0 <= x < w and 0 <= y < h):
            return False
        if (x, y) in screen:
            colour = screen[(x, y)]
            return colour != B and colour != C
        return C != 0               # background (bit clear) -- B can't block it
    sx, sy = seed
    if not inside(sx, sy):
        return set()
    stack, painted = [(sx, sy)], set()
    while stack:
        x, y = stack.pop()
        if not inside(x, y):
            continue
        screen[(x, y)] = C
        painted.add((x, y))
        for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
            if inside(nx, ny):
                stack.append((nx, ny))
    return painted


def run_asm_paint(m, screen, seed, C, B):
    """Drive the REAL gfx_paint_op against `screen` (mutated in place) via
    trapped gfx_paint_read/gfx_paint_plot. Returns GFX_POVF (1 = the span
    stack overflowed and the fill aborted early).

    gfx_paint_read (not gfx_border_read -- the VG-8020 bug fix,
    sub/graphics.asm gfx_paint_read's own header) reports BOTH the effective
    colour AND whether the pixel is DRAWN (present in `screen`) via Zf: a
    pixel absent from `screen` is undrawn background, Zf=1. This host model
    cannot represent real VDP colour-CLASH (one group's shared attribute
    byte) -- that mechanism is VDP-differential-only, gated by
    probes/basic/basic_probe_graphics.py's PAINT phases, not here; this
    trapped model validates the pure flood-fill graph-walk (topology, stack
    behaviour, termination) against the Python oracle below."""
    m.poke(m.addr("GFX_PTOP"), 0)
    m.poke(m.addr("GFX_POVF"), 0)

    def do_read(mm):
        pt = (mm.cpu.e, mm.cpu.d)
        drawn = pt in screen
        mm.cpu.a = screen.get(pt, 0)
        mm.cpu.f = 0x00 if drawn else 0x40   # Zf=1 iff bit CLEAR (background)
    m.trap("gfx_paint_read", do_read)

    def do_plot(mm):
        x = mm.peek(mm.addr("GFX_PTESTX"))[0]
        y = mm.peek(mm.addr("GFX_PTESTY"))[0]
        c = mm.peek(mm.addr("GFX_C"))[0]
        screen[(x, y)] = c
    m.trap("gfx_paint_plot", do_plot)

    # 🔴 D-PAINTVRAM: THE SECOND WRITE PATH. A span's WHOLE CELLS no longer go
    # through gfx_paint_plot at all -- gfx_paint_row splits the span the way
    # gbf_row splits a `,BF` scanline and writes each fully-covered cell BLIND
    # through gfx_span_bytes (pattern $00 + the colour in the background nibble,
    # D-BFBYTE's storage rule, which is what both references leave and this ROM
    # did not: docs/spec-basic-paintvram.md). Without this trap those pixels are
    # simply absent from the model, gfx_paint_read then reports them UNDRAWN, and
    # the graph-walk under test is being driven by a screen that never got
    # painted -- the three whole-algorithm cases below failed exactly that way.
    # in: B = cell count, D = y, E = x of the first (cell-aligned) whole cell.
    # This model is still a PIXEL model; the byte ENCODING it stands for is
    # gated by basic_probe_graphics.py's PHASE H-V, not here.
    def do_span_bytes(mm):
        n, y, x0 = mm.cpu.b, mm.cpu.d, mm.cpu.e
        c = mm.peek(mm.addr("GFX_C"))[0]
        for k in range(n * 8):
            screen[(x0 + k, y)] = c
    m.trap("gfx_span_bytes", do_span_bytes)

    # ...and SCREEN 2 explicitly. gfx_paint_row and gbf_row both branch on
    # gfx_is_mc (SCRMOD == 3), and until D-PAINTVRAM nothing in this file set
    # SCRMOD at all -- the SCREEN-2 arm was being taken by whatever the simulated
    # RAM happened to hold. An implicit mode is not a mode.
    m.poke(m.addr("SCRMOD"), 2)
    m.poke_w(m.addr("GXPOS"), seed[0])
    m.poke_w(m.addr("GYPOS"), seed[1])
    m.poke(m.addr("GFX_C"), C)
    m.poke(m.addr("GFX_B"), B)
    m.call("gfx_paint_op", max_steps=4_000_000)
    return m.peek(m.addr("GFX_POVF"))[0]


def rect_ring(x0, y0, x1, y1):
    """The 4 edges of an axis-aligned rectangle, as a set of (x,y) points."""
    pts = set()
    for x in range(x0, x1 + 1):
        pts.add((x, y0)); pts.add((x, y1))
    for y in range(y0, y1 + 1):
        pts.add((x0, y)); pts.add((x1, y))
    return pts


def naive_flood_pushes(w, h, seed, B, budget):
    """Teeth oracle: the SAME per-pixel stack shape as a scanline flood, but
    WITHOUT gfx_paint_inside's "already == C" stop (only "!= B") -- a painted
    pixel (marked 1, deliberately != B) always re-qualifies as fillable, so
    revisits never stop. Pure Python; returns the push count (capped at
    `budget`) to show it explodes rather than converging."""
    def inside_naive(x, y, scr):
        return 0 <= x < w and 0 <= y < h and scr.get((x, y), 0) != B
    scr, stack, pushes = {}, [seed], 0
    while stack and pushes < budget:
        x, y = stack.pop()
        if not inside_naive(x, y, scr):
            continue
        scr[(x, y)] = 1
        for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
            if inside_naive(nx, ny, scr):
                stack.append((nx, ny))
                pushes += 1
    return pushes


def build_sub():
    subprocess.run(["pasmo", "-I", os.path.join(ROOT, "sub"), "--bin",
                    os.path.join(ROOT, "sub", "sub.asm"), SUB_ROM, SUB_SYM],
                   check=True, capture_output=True, cwd=ROOT)


def build_reloc():
    subprocess.run(["pasmo", "--bin",
                    os.path.join(ROOT, "basic", "main.asm"), RES_ROM, RES_SYM],
                   check=True, capture_output=True, cwd=ROOT)



# --- G6 DRAW (docs/spec-basic-graphics-g6.md §3/§4) --------------------------
# The two pure leaves of the DRAW tenant. Both are exactly-measured rules, so
# the fixtures below ARE the measurements (scratchpad/g6_draw_notes.md §3/§4),
# not a re-derivation of the implementation.
#
#   gdrw_scale   distance = signed16((n * S) mod 65536) / 4, truncating TOWARD
#                ZERO. The wrap is load-bearing: it is what makes `U32767` move
#                DOWN one pixel on the reference.
#   gdrw_rotate  one angle step is (dx,dy) -> (dy,-dx); A1 turns U into L.
def zscale(m, n, s):
    m.poke_w(m.addr("GFX_DARG"), n & 0xFFFF)
    m.poke(m.addr("GFX_DSCALE"), [s & 0xFF])
    m.call("gdrw_scale")
    return _rd16s(m, "GFX_DARG")


def py_scale(n, s):
    p = (n * s) & 0xFFFF
    if p >= 0x8000:
        p -= 0x10000
    return int(p / 4) if p < 0 else p // 4     # truncate toward zero


def zrotate(m, dx, dy, angle):
    m.poke_w(m.addr("GFX_DDX"), dx & 0xFFFF)
    m.poke_w(m.addr("GFX_DDY"), dy & 0xFFFF)
    m.poke(m.addr("GFX_DANGLE"), [angle])
    m.call("gdrw_rotate")
    return _rd16s(m, "GFX_DDX"), _rd16s(m, "GFX_DDY")


# (n, S) pairs: the five large-count wraps MEASURED on the reference, the
# quarter-unit cases, and the negative-rounding cases that discriminate
# truncate-toward-zero from floor (S3U-10 gives 7 on the reference, not 8).
DRAW_SCALE_CASES = [(n, s) for n, s in [
    (10, 4), (1, 4), (0, 4), (10, 1), (10, 2), (10, 3), (10, 5), (10, 7),
    (2, 5), (100, 255), (1000, 9), (9000, 9), (20000, 5), (123, 4),
    (32767, 4), (32768, 4), (33000, 4), (40000, 4), (65535, 4),
    (-5, 4), (-10, 3), (-10, 5), (-2, 1), (-2, 3), (-1, 4),
]]

MEASURED_SCALE = {          # the reference's own answers, as dy for `U<n>`
    (32767, 4): -1, (32768, 4): 0, (33000, 4): 232, (40000, 4): 7232,
    (65535, 4): -1, (10, 3): 7, (10, 5): 12, (2, 5): 2, (-10, 3): -7,
}

ROTATE_CASES = [
    # (dx, dy, angle, want) -- U is (0,-10), E is (+10,-10)
    ((0, -10), 0, (0, -10)),
    ((0, -10), 1, (-10, 0)),      # A1 turns U into L (measured)
    ((0, -10), 2, (0, 10)),       # A2 turns U into D
    ((0, -10), 3, (10, 0)),       # A3 turns U into R
    ((10, -10), 1, (-10, -10)),   # A1 turns E into H (measured)
    ((10, 0), 1, (0, -10)),       # A1 turns R into U
]

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

    # --- gfx_bres_init at $8000 (D-NEG8K) ---
    for x1, y1, x2, y2, dmaj, dmin, cnt, err, steep in BRES_8000_CASES:
        for nm, v in (("GFX_X1", x1), ("GFX_Y1", y1), ("GFX_X2", x2), ("GFX_Y2", y2)):
            m.poke_w(m.addr(nm), v & 0xFFFF)
        m.call("gfx_bres_init")
        got = tuple(int.from_bytes(m.peek(m.addr(n), 2), "little")
                    for n in ("GFX_DMAJ", "GFX_DMIN", "GFX_CNT", "GFX_ERR"))
        got_steep = m.peek(m.addr("GFX_STEEP"), 1)[0]
        want = (dmaj, dmin, cnt, err)
        check(got == want and got_steep == steep,
              f"gfx_bres_init ({x1},{y1})-({x2},{y2}) -> dmaj/dmin/cnt/err="
              f"{got} steep={got_steep} (want {want} steep={steep})")

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

    # --- G4 CIRCLE tenant math (sub-rom, rom_base=0) ---------------------------
    # gfx_circ_init/next: the pure midpoint-circle stepper == pymidpoint (own
    # design, spec §4.1) for a battery incl. every captured radius + small edges.
    for r in (0, 1, 2, 3, 4, 7, 8, 12, 15, 20):
        want = midpoint_circle_octants(r)
        got = pymirror(zcirc_octant_steps(m, r))
        check(got == want, f"gfx_circ_init/next r={r:2d} octant set == pymidpoint oracle "
              f"({len(got)} pts)" + ("" if got == want else f"  DIFF {sorted(got ^ want)[:6]}"))

    # asm octants + centre == the CAPTURED VG-8020 circles (the real oracle,
    # scratchpad/g4_pointsets.json) -- the crux-1 de-risker, emulator-free.
    for label in ("circ_r4", "circ_r7", "circ_r8", "circ_r12", "circ_r15", "circ_r20"):
        d = G4_DATA[label]
        r = int("".join(c for c in label if c.isdigit()))
        ref = {(x, y) for x, y in d["pts"]}
        got = {(d["cx"] + dx, d["cy"] + dy) for dx, dy in pymirror(zcirc_octant_steps(m, r))}
        check(got == ref, f"gfx_circ asm+centre == captured VG-8020 {label} (n={d['n']})"
              + ("" if got == ref else f"  DIFF {sorted(got ^ ref)[:6]}"))

    # teeth: perturbing d0 (1-r -> -r) must break at least one radius
    def zcirc_bad_d0(m, r):
        m.poke_w(m.addr("GFX_R"), _w16(r))
        m.call("gfx_circ_init")
        m.poke_w(m.addr("GFX_QD"), _w16(r - 1))    # corrupt d0 (was 1-r; flip its sign)
        x, y = _rd16s(m, "GFX_QX"), _rd16s(m, "GFX_QY")
        steps = [(x, y)]
        while x <= y:
            m.call("gfx_circ_next")
            x, y = _rd16s(m, "GFX_QX"), _rd16s(m, "GFX_QY")
            if x <= y:
                steps.append((x, y))
        return steps
    bad = pymirror(zcirc_bad_d0(m, 15))
    good = midpoint_circle_octants(15)
    check(bad != good, "teeth: corrupting d0 changes the r=15 point set (anti-green-build)")

    # --- gco_loop termination (r=0 bug, G4 slice report): the REAL asm loop's --
    # own "while QX<=QY" test must be SIGNED. r=0 drives QY to -1 after the one
    # valid step; an unsigned cf-based test reads -1 as 65535 (never <= QX) and
    # the loop never stops, drawing extra garbage octant points. Drives the
    # actual gfx_circle_op loop (not just the pure init/next stepper, which is
    # driven by a PYTHON while-loop and never exercises the asm's own check) and
    # asserts it halts at the SAME (QX,QY) the pure stepper says is one-past-the-
    # last-valid-point, for a battery including the r=0 edge and every captured
    # radius.
    for r in (0, 1, 2, 3, 4, 7, 8, 12, 15, 20):
        zcirc_octant_steps(m, r)               # leaves the machine one step PAST
                                                # the last valid (x,y) (its own
                                                # python while-loop always calls
                                                # gfx_circ_next once more than it
                                                # appends) -- this IS the reference
                                                # termination point, read directly.
        want_x, want_y = _rd16s(m, "GFX_QX"), _rd16s(m, "GFX_QY")
        zcirc_full_draw(m, 50, 50, r)          # drives gco_loop's OWN check
        got_x, got_y = _rd16s(m, "GFX_QX"), _rd16s(m, "GFX_QY")
        check((got_x, got_y) == (want_x, want_y),
              f"gco_loop terminates r={r:2d} at ({got_x},{got_y}) (want ({want_x},{want_y}))")

    # --- gfx_circ_scale: the 8.8 minor-axis fixed-point scale (spec §4.2) ------
    for off, S in SCALE_CASES:
        m.poke_w(m.addr("GFX_ASPS"), _w16(S))
        v16 = _w16(off)
        cpu = m.call("gfx_circ_scale", h=(v16 >> 8) & 0xFF, l=v16 & 0xFF)
        got = cpu.hl - 0x10000 if cpu.hl >= 0x8000 else cpu.hl
        want = gfx_scale_off(off, S)
        check(got == want, f"gfx_circ_scale v={off:4d} S={S:3d} -> {got} (want {want})")

    # --- gfx_clamp_coords (D-SPOKELINE): every line endpoint clamps to the --
    # screen, X to 0..255, Y to 0..191 -- measured against the VG-8020 on 14
    # discriminating rows over all four edges (LINE, spokes, box outlines).
    CLAMP_CASES = [
        # (x1, y1, x2, y2) -> clamped
        ((10, 20, 200, 150), (10, 20, 200, 150)),      # on-screen: unchanged
        ((-40, 20, 100, 80), (0, 20, 100, 80)),        # x1 < 0
        ((300, 20, 100, 80), (255, 20, 100, 80)),      # x1 > 255
        ((50, 250, 120, 100), (50, 191, 120, 100)),    # y1 > 191
        ((128, 96, 129, -304), (128, 96, 129, 0)),     # the arc_big_r400 spoke
        ((300, 300, 400, 400), (255, 191, 255, 191)),  # fully off -> corner
        ((-50, -50, 305, 241), (0, 0, 255, 191)),      # both endpoints off
        ((0, 0, 255, 191), (0, 0, 255, 191)),          # exact bounds: unchanged
        ((256, 192, -1, -32768), (255, 191, 0, 0)),    # one-off + extremes
        ((32767, 0, 0, 32767), (255, 0, 0, 191)),      # int16 max both axes
    ]
    for coords, want in CLAMP_CASES:
        for name, v in zip(("GFX_X1", "GFX_Y1", "GFX_X2", "GFX_Y2"), coords):
            m.poke_w(m.addr(name), _w16(v))
        m.call("gfx_clamp_coords")
        got = tuple(_rd16s(m, n) for n in ("GFX_X1", "GFX_Y1", "GFX_X2",
                                           "GFX_Y2"))
        check(got == want, f"gfx_clamp_coords {coords} -> {got} (want {want})")

    # --- gbf_split (D-BFBYTE): the per-scanline run split ---------------------
    # fl = (xl+7)>>3, fr = ((xr+1)>>3)-1; B = fr-fl+1 whole bytes (0 = none),
    # D = x of the first whole cell. Both halves are computed in 16 bits, and
    # the last three rows are why: xl+7 overflows a byte above 248 and fr
    # reaches -1 below xr=7. In 8 bits `LINE(255,0)-(255,0),,BF` would report
    # 32 whole bytes and blind-fill the whole scanline.
    SPLIT_CASES = [
        # (xl, xr) -> (whole-byte count, x of the first whole cell)
        ((0, 7), (1, 0)),          # exactly one cell
        ((8, 15), (1, 8)),         # exactly one cell, not the first
        ((0, 15), (2, 0)),         # two cells
        ((3, 20), (1, 8)),         # partial | WHOLE | partial
        ((4, 11), (0, None)),      # 8 px, straddling: NO whole byte
        ((5, 5), (0, None)),       # one pixel
        ((0, 6), (0, None)),       # fr = -1
        ((0, 255), (32, 0)),       # the whole scanline
        ((1, 254), (30, 8)),       # the whole scanline bar both end pixels
        ((248, 255), (1, 248)),    # the LAST cell, whole
        ((249, 255), (0, None)),   # the last cell, partial -> fl = 32 > fr
        ((255, 255), (0, None)),   # ⚠️ xl+7 = 262: the 8-bit overflow row
    ]
    for (xl, xr), (want_n, want_x) in SPLIT_CASES:
        m.poke_w(m.addr("GFX_TX1"), _w16(xl))
        m.poke_w(m.addr("GFX_TX2"), _w16(xr))
        cpu = m.call("gbf_split")
        ok = cpu.b == want_n and (want_x is None or cpu.d == want_x)
        check(ok, f"gbf_split x={xl}..{xr} -> {cpu.b} whole byte(s) at x={cpu.d}"
                  f" (want {want_n}"
                  f"{'' if want_x is None else ' at x=%d' % want_x})")

    # gbf_shr3 is the 16-bit >>3 both halves lean on -- including the values a
    # byte cannot hold, which is the whole reason it is 16-bit.
    for v, want in ((0, 0), (7, 0), (8, 1), (255, 31), (256, 32), (262, 32),
                    (0xFFFF, 0x1FFF)):
        cpu = m.call("gbf_shr3", h=(v >> 8) & 0xFF, l=v & 0xFF)
        check(cpu.hl == want, f"gbf_shr3 {v} -> {cpu.hl} (want {want})")

    # --- gbf_max16 / gfx_bf_gxpos (D-DRAWCLAMP): a box FILL leaves the -------
    # CLAMPED BOX'S BOTTOM-RIGHT in GXPOS/GYPOS, while GRPACX/GRPACY keep the
    # raw p2 and the `B` OUTLINE arm leaves GXPOS raw too. Measured on the
    # VG-8020: `LINE(200,150)-(-30,-20),,BF` reports 200/150 -- which is what
    # separates max-on-each-axis from "the last pixel the fill painted" (the
    # fill runs bottom-to-top there, ending at y=0).
    MAX16_CASES = [
        ((0, 0), 0), ((5, 9), 9), ((9, 5), 9), ((7, 7), 7),
        ((0, 255), 255), ((255, 0), 255), ((191, 0), 191),
    ]
    for (a, b), want in MAX16_CASES:
        cpu = m.call("gbf_max16", h=(a >> 8) & 0xFF, l=a & 0xFF,
                     d=(b >> 8) & 0xFF, e=b & 0xFF)
        check(cpu.hl == want, f"gbf_max16 max({a},{b}) -> {cpu.hl} (want {want})")

    # The stash holds the CLAMPED corners in either order; the residue is the
    # per-axis max of the two, never p2 and never the last row painted.
    BF_GXPOS_CASES = [
        # (TX1, TY1, TX2, TY2) -> (GXPOS, GYPOS)
        ((20, 20, 60, 60), (60, 60)),        # on screen, p2 IS the bottom-right
        ((200, 150, 255, 191), (255, 191)),  # p2 off both edges, post-clamp
        ((200, 150, 0, 0), (200, 150)),      # p2 is the TOP-LEFT: p1 wins
        ((0, 191, 255, 0), (255, 191)),      # mixed: each axis decides alone
        ((255, 191, 255, 191), (255, 191)),  # degenerate
    ]
    for coords, want in BF_GXPOS_CASES:
        for name, v in zip(("GFX_TX1", "GFX_TY1", "GFX_TX2", "GFX_TY2"),
                           coords):
            m.poke_w(m.addr(name), _w16(v))
        m.call("gfx_bf_gxpos")
        got = (_rd16s(m, "GXPOS"), _rd16s(m, "GYPOS"))
        check(got == want, f"gfx_bf_gxpos {coords} -> {got} (want {want})")

    # --- gfx_circ_keep: the D-ARCMASK step-index wedge, driven point by ------
    # point against the Python oracle (py_keep, the pre-asm simulation).
    # Battery covers: both parities, both wrap states, FULLW, ARCF=0, the two
    # boundary-equality rows (closed interval), and the normalization edges --
    # pos = -1 (odd octant, qx = M+1) and pos = M (even octant, qx = M).
    KEEP_CASES = [
        # M, S,        E,        wrapf, fullw, octant, qx
        (67, (0, 10), (2, 5), 0, 0, 0, 10),     # P == S -> keep (closed)
        (67, (0, 10), (2, 5), 0, 0, 2, 62),     # odd o=2? no: o2 even par -- P == E via normalize? plain inside check below
        (67, (0, 10), (2, 5), 0, 0, 1, 30),     # inside, odd octant
        (67, (0, 10), (2, 5), 0, 0, 5, 30),     # clearly outside
        (67, (6, 60), (1, 20), 1, 0, 7, 30),    # wraps 0: inside the wrap
        (67, (6, 60), (1, 20), 1, 0, 3, 30),    # wraps 0: outside
        (67, (0, 10), (2, 5), 0, 1, 5, 30),     # FULLW overrides everything
        (67, (0, 10), (2, 5), 0, 0, 1, 68),     # odd octant, qx=M+1 -> pos=-1
        (67, (0, 10), (2, 5), 0, 0, 2, 67),     # even octant, qx=M -> carry
        (134, (1, 100), (2, 33), 0, 0, 1, 34),  # r=190 shapes
        (0, (0, 0), (0, 0), 0, 0, 3, 0),        # M=0 (r<=1): no normalize
    ]
    for M_, S, E, wrapf, fullw, oct_, qx in KEEP_CASES:
        got = zcirc_keep(m, 1, M_, S, E, wrapf, fullw, oct_, qx)
        want = py_keep(M_, S, E, wrapf, fullw, oct_, qx)
        check(got == want, f"gfx_circ_keep M={M_} S={S} E={E} w={wrapf} "
              f"f={fullw} o={oct_} qx={qx} -> {got} (want {want})")
    got = zcirc_keep(m, 0, 67, (0, 10), (2, 5), 0, 0, 5, 30)
    check(got is True, "gfx_circ_keep ARCF=0 -> always keep")

    # --- gfx_circ_wedge_prep: M = floor(r/sqrt(2)) EXACTLY ------------------
    # incl. three of the 410 radii where the bare (r*46341)>>16 overshoots --
    # the teeth for the 2*M*M<=r*r floor correction.
    for r in (0, 1, 2, 15, 24, 95, 190, 200, 1393, 2209, 3025, 23169, 32767):
        Mv, S, E, wrapf, fullw = zwedge_prep(m, 0, 0, 0, 0, r)
        want = math.isqrt(r * r // 2)
        check(Mv == want, f"wedge_prep M r={r} -> {Mv} (want floor(r/sqrt2)={want})")
    check(((1393 * 46341) >> 16) != math.isqrt(1393 * 1393 // 2),
          "teeth: r=1393 is a radius the UNCORRECTED multiply gets wrong, so "
          "the M row above fails if the correction is deleted")

    # --- wedge boundaries + WRAPF/FULLW from marshalled records -------------
    WEDGE_CASES = [
        # (soct, su14, eoct, eu14, r) -- vs the py_wedge oracle
        (0, 0, 1, 16367, 15),          # arc_0_hpi's actual records
        (1, 16367, 3, 16375, 15),      # arc_hpi_pi
        (3, 13387, 1, 4574, 15),       # arc_wrap: S > E -> WRAPF
        (0, 0, 7, 16315, 15),          # arc_full628: plain wide wedge
        (0, 0, 8, 0, 15),              # SAME cell, RAW differs -> FULLW
        (0, 0, 0, 0, 15),              # identical records -> zero-width wedge
        (1, 16367, 2, 191, 190),       # 1.57 vs 1.58 at r=190
    ]
    for soct, su, eoct, eu, r in WEDGE_CASES:
        got = zwedge_prep(m, soct, su, eoct, eu, r)
        want = py_wedge(soct, su, eoct, eu, r)
        check(got == want, f"wedge_prep ({soct},{su})..({eoct},{eu}) r={r} "
              f"-> {got} (want {want})")

    # --- spoke endpoint = the octant point at the boundary ------------------
    # G4-arcbnd round 3 (banked July, read by D-ARCMASK): the reference's
    # spoke at theta=-0.01 lands on (15,0) -- the octant point -- NOT on the
    # retired QTAB vector's nudged (15,-1). That row is the teeth here.
    SPOKE_CASES = [
        # theta, r, want (pre-scale vector, screen convention)
        (0.01, 15, (15, 0)),           # round 3: the defect the rewrite fixes
        (1.57, 15, (1, -15)),          # the gate's own spoke_270 endpoint
        (0.1, 15, (15, -1)),           # spoke_wedge2's short spoke
        (1.57, 400, (1, -400)),        # r=400: the QTAB 255-cap used to short
                                       # this to (1,-398)
        (3.14, 20, (-20, -1)),         # octant 3, step 1 mirrored: the
                                       # boundary is 0.002 rad shy of pi
        (4.71, 20, (-1, 20)),          # three-quarters, y positive (screen)
    ]
    for theta, r, want in SPOKE_CASES:
        os_, us = py_marshal(theta)
        zwedge_prep(m, os_, us, 0, 0, r, sneg=1)
        got = (_rd16s(m, "GFX_SVX"), _rd16s(m, "GFX_SVY"))
        check(got == want, f"spoke vec theta={theta} r={r} -> {got} "
              f"(want {want})")
    # minor scale applies to the spoke vector: ASPS=128 halves the minor (y)
    os_, us = py_marshal(0.5)
    zwedge_prep(m, os_, us, 0, 0, 100, sneg=1, asps=128)
    sx, sy = _rd16s(m, "GFX_SVX"), _rd16s(m, "GFX_SVY")
    zwedge_prep(m, os_, us, 0, 0, 100, sneg=1, asps=256)
    fx, fy = _rd16s(m, "GFX_SVX"), _rd16s(m, "GFX_SVY")
    check(sx == fx and sy == (0 - ((abs(fy) * 128 + 128) >> 8)),
          f"spoke vec minor scale: ASPS=128 halves y ({fx},{fy})->({sx},{sy})")

    # --- FULL integration: REAL wedge_prep + REAL octant loop + REAL keep ---
    # (static octant per mirror, the loop's own qx) == every captured VG-8020
    # arc + both round1 boundary re-captures, EXACTLY. The records are
    # marshalled by the Python oracle (the circleparse half is proven
    # separately below); everything else is the shipping asm.
    def full_arcmask(m, cx, cy, r, a0, a1):
        os_, us = py_marshal(abs(a0))
        oe_, ue = py_marshal(abs(a1))
        Mv, S, E, wrapf, fullw = zwedge_prep(m, os_, us, oe_, ue, r)
        got = set()
        for qx, qy in zcirc_octant_steps(m, r):
            for (dx, dy), o in pymirror8(qx, qy):
                if zcirc_keep(m, 1, Mv, S, E, wrapf, fullw, o, qx):
                    got.add((cx + dx, cy + dy))
        return got

    for label, a0, a1 in ARC_CASES:
        d = G4_DATA[label]
        r = int(d["ops"].split(")")[1].split(",")[1])
        ref = {(x, y) for x, y in d["pts"]}
        got = full_arcmask(m, d["cx"], d["cy"], r, a0, a1)
        check(got == ref, f"ARCMASK arc {label} == captured VG-8020 "
              f"(n={d['n']})"
              + ("" if got == ref else f"  DIFF {sorted(got ^ ref)[:6]}"))
    for label, c in G4_BND["round1"].items():
        args = c["ops"].split(")", 1)[1].lstrip(",").split(",")
        r = int(args[0])
        a0, a1 = float(args[2]), float(args[3])
        ref = {(x, y) for x, y in c["pts"]}
        got = full_arcmask(m, c["cx"], c["cy"], r, a0, a1)
        check(got == ref, f"ARCMASK {label} ({a0},{a1}) == captured "
              f"(n={len(ref)})"
              + ("" if got == ref else f"  DIFF {sorted(got ^ ref)[:6]}"))

    # --- the round2 near-cardinal sweep, through the REAL pipeline: the -----
    # 1.50..1.60 presence flags of pixel (61,45) (offset (1,-15), octant 1,
    # qx=1) -- the pin the retired +-1 nudge existed for, now carried by the
    # single-precision marshal + the wedge alone.
    for lbl, c in G4_BND["round2"].items():
        a0 = float(c["a0"])
        os_, us = py_marshal(a0)
        oe_, ue = py_marshal(3.14)
        Mv, S, E, wrapf, fullw = zwedge_prep(m, os_, us, oe_, ue, 15)
        got = zcirc_keep(m, 1, Mv, S, E, wrapf, fullw, 1, 1)
        check(got == c["present"], f"ARCMASK near-cardinal a0={a0}: (61,45) "
              f"{'kept' if got else 'dropped'} (ref: {c['present']})")

    # teeth (anti-green-build): corrupting the START boundary's pos by ONE
    # step must break a captured match -- the wedge is exact, not approximate.
    d = G4_DATA["arc_hpi_pi"]
    r = int(d["ops"].split(")")[1].split(",")[1])
    ref = {(x, y) for x, y in d["pts"]}
    os_, us = py_marshal(1.57)
    oe_, ue = py_marshal(3.14)
    Mv, S, E, wrapf, fullw = zwedge_prep(m, os_, us, oe_, ue, r)
    S_bad = (S[0], S[1] + 1)
    bad = set()
    for qx, qy in zcirc_octant_steps(m, r):
        for (dx, dy), o in pymirror8(qx, qy):
            if zcirc_keep(m, 1, Mv, S_bad, E, wrapf, fullw, o, qx):
                bad.add((d["cx"] + dx, d["cy"] + dy))
    check(bad != ref, "teeth: nudging WS_P by one step breaks the "
          "arc_hpi_pi captured match (anti-green-build)")

    # --- G5 PAINT (docs/spec-basic-graphics-g5.md) -- span-stack push/pop ---
    CAP = m.sym["GFX_PSTK_CAP"]
    m.poke(m.addr("GFX_PTOP"), 0)
    m.poke(m.addr("GFX_POVF"), 0)
    seq = [(1, 2, 3), (10, 20, 30), (191, 0, 255)]
    for y, xl, xr in seq:
        m.call("gfx_pstk_push", a=y, b=xl, c=xr)
    got = []
    while True:
        cpu = m.call("gfx_pstk_pop")
        if not carry(cpu):
            break
        got.append((cpu.a, cpu.b, cpu.c))
    check(got == list(reversed(seq)), f"gfx_pstk push/pop LIFO order {got}")

    m.poke(m.addr("GFX_PTOP"), 0)
    m.poke(m.addr("GFX_POVF"), 0)
    for i in range(CAP):
        m.call("gfx_pstk_push", a=i & 0xFF, b=0, c=0)
    top = m.peek(m.addr("GFX_PTOP"))[0]
    ovf = m.peek(m.addr("GFX_POVF"))[0]
    check(top == CAP and ovf == 0,
          f"gfx_pstk fills exactly to CAP={CAP} without overflow (top={top} ovf={ovf})")
    m.call("gfx_pstk_push", a=99, b=0, c=0)
    top2 = m.peek(m.addr("GFX_PTOP"))[0]
    ovf2 = m.peek(m.addr("GFX_POVF"))[0]
    check(top2 == CAP and ovf2 == 1,
          f"gfx_pstk push past CAP sets overflow, top unchanged (top={top2} ovf={ovf2})")
    # teeth: an entry that DOES land (index CAP-1, not dropped) must be poppable
    m.poke(m.addr("GFX_PTOP"), 0)
    m.poke(m.addr("GFX_POVF"), 0)
    for i in range(CAP - 1):
        m.call("gfx_pstk_push", a=0, b=0, c=0)
    m.call("gfx_pstk_push", a=77, b=88, c=99)      # the CAP-th (last legal) entry
    cpu = m.call("gfx_pstk_pop")
    check(carry(cpu) and (cpu.a, cpu.b, cpu.c) == (77, 88, 99),
          "teeth: the boundary (CAP-th) push actually stores its payload, "
          "not just bumps the counter (anti-green-build)")

    # --- G5 PAINT -- gfx_paint_inside/gfx_paint_passable decision logic -----
    # (gfx_paint_read trapped -- BIT-AWARE, the VG-8020 bug fix's own header
    # in sub/graphics.asm: a DRAWN pixel (bit_set=True) is tested against
    # both GFX_B and GFX_C; an UNDRAWN/background pixel (bit_set=False) is
    # NEVER a border -- only the "already C" rule can stop it there.)
    def trap_paint_read(mm, c, s):
        mm.cpu.a = c
        mm.cpu.f = 0x00 if s else 0x40     # Zf=1 iff bit CLEAR (background)

    for b, c, colour, bit_set, want in [
        (5, 5, 5, True,  False),  # drawn, == B -> not inside
        (5, 7, 7, True,  False),  # drawn, == C already -> not inside (own-design stop)
        (5, 7, 3, True,  True),   # drawn, neither -> inside
        (0, 0, 0, True,  False),  # drawn, C==B==colour (the C==B bounded-case collapse)
        (5, 7, 5, False, True),   # BUG FIX: background whose bg-nibble==B is
                                  # NEVER a border (an undrawn pixel can't be)
        (5, 7, 7, False, False),  # background whose bg-nibble==C -> still the
                                  # "already done" stop (a no-op PAINT, C==bg)
    ]:
        m.trap("gfx_paint_read", lambda mm, c=colour, s=bit_set: trap_paint_read(mm, c, s))
        m.poke(m.addr("GFX_B"), b)
        m.poke(m.addr("GFX_C"), c)
        m.poke(m.addr("GFX_PTESTX"), 10)
        m.poke(m.addr("GFX_PTESTY"), 10)
        cpu = m.call("gfx_paint_inside")
        check(carry(cpu) == want,
              f"gfx_paint_inside B={b} C={c} colour={colour} bit_set={bit_set} "
              f"-> {carry(cpu)} want {want}")

    # gfx_paint_passable: CF=1 iff NOT (drawn AND ==B) -- an already-C pixel
    # (drawn or background) IS passable here, unlike gfx_paint_inside (own
    # header: extend_lr's walk must cross an "eaten" pixel, not stop at it).
    for b, colour, bit_set, want in [
        (5, 5, True,  False),   # drawn, == B -> blocked
        (5, 3, True,  True),    # drawn, != B -> passable
        (5, 5, False, True),    # BUG FIX: background whose bg-nibble==B is
                                # still passable (never a real border)
        (5, 3, False, True),    # background, != B anyway -> passable
    ]:
        m.trap("gfx_paint_read", lambda mm, c=colour, s=bit_set: trap_paint_read(mm, c, s))
        m.poke(m.addr("GFX_B"), b)
        m.poke(m.addr("GFX_PTESTX"), 10)
        m.poke(m.addr("GFX_PTESTY"), 10)
        cpu = m.call("gfx_paint_passable")
        check(carry(cpu) == want,
              f"gfx_paint_passable B={b} colour={colour} bit_set={bit_set} "
              f"-> {carry(cpu)} want {want}")

    # --- G5 PAINT -- whole-algorithm span-fill vs the Python oracle ---------
    # Case A: bounded box, C==B -- fill self-limits to the interior (spec's
    # BOUNDED case).
    W, H = 40, 30
    walls_a = rect_ring(5, 5, 20, 20)
    screen_asm = {p: 2 for p in walls_a}
    screen_py = dict(screen_asm)
    seed_a = (12, 12)
    ovf_a = run_asm_paint(m, screen_asm, seed_a, C=2, B=2)
    want_a = py_paint_flood(screen_py, W, H, seed_a, C=2, B=2)
    got_a = {p for p, c in screen_asm.items() if c == 2 and p not in walls_a}
    check(ovf_a == 0 and got_a == want_a,
          f"G5 bounded box C==B: painted interior == oracle ({len(got_a)} pts)"
          + ("" if got_a == want_a else f"  DIFF {sorted(got_a ^ want_a)[:8]}"))
    leak = {p for p in got_a if not (5 < p[0] < 20 and 5 < p[1] < 20)}
    check(not leak, f"G5 bounded box: no leak outside the ring {sorted(leak)[:5]}")

    # Case B: concave L-shaped room, C!=B -- a notch wall juts partway into
    # the room; the fill must wrap around its open end into the far chamber.
    # (This case caught a REAL bug during implementation: gfx_paint_scan_row
    # only tests columns within its CALLER's [xL,xR], so a span popped by
    # gfx_paint_process must re-extend its own left/right bounds -- see
    # gfx_paint_extend_lr's header, sub/graphics.asm -- else the fill stalls
    # at the notch and never reaches the far chamber. Kept as a regression
    # case, not just a shape exercise.)
    walls_b = rect_ring(2, 2, 25, 20)
    for y in range(2, 12):
        walls_b.add((14, y))
    screen_asm_b = {p: 2 for p in walls_b}
    screen_py_b = dict(screen_asm_b)
    seed_b = (5, 5)
    ovf_b = run_asm_paint(m, screen_asm_b, seed_b, C=9, B=2)
    want_b = py_paint_flood(screen_py_b, W, H, seed_b, C=9, B=2)
    got_b = {p for p, c in screen_asm_b.items() if c == 9}
    check(ovf_b == 0 and got_b == want_b,
          f"G5 concave L-room C!=B: matches oracle ({len(got_b)} pts)"
          + ("" if got_b == want_b else f"  DIFF {sorted(got_b ^ want_b)[:8]}"))
    check(any(x > 14 for x, y in got_b),
          "G5 concave room: fill wraps around the notch into the far chamber")

    # Case C: seed at the screen corner (0,0) -- exercises the hardcoded
    # x=0/y=0 screen-edge stops against the REAL full domain (0..255x0..191);
    # an enclosing wall only on the right/bottom, relying on the screen edge
    # itself for the other two sides.
    walls_c = set()
    for y in range(0, 16):
        walls_c.add((15, y))
    for x in range(0, 16):
        walls_c.add((x, 15))
    screen_asm_c = {p: 2 for p in walls_c}
    screen_py_c = dict(screen_asm_c)
    seed_c = (0, 0)
    ovf_c = run_asm_paint(m, screen_asm_c, seed_c, C=4, B=4)
    want_c = py_paint_flood(screen_py_c, 256, 192, seed_c, C=4, B=4)
    got_c = {p for p, c in screen_asm_c.items() if c == 4}
    check(ovf_c == 0 and got_c == want_c and (0, 0) in got_c,
          f"G5 edge seed (0,0): matches oracle incl. the screen corner ({len(got_c)} pts)"
          + ("" if got_c == want_c else f"  DIFF {sorted(got_c ^ want_c)[:8]}"))

    # teeth: WITHOUT gfx_paint_inside's "already == C" stop (only "!= B"), a
    # naive flood on the SAME open room (case B, C!=B) never converges --
    # proves the own-design "!=B AND !=C" rule is load-bearing for
    # termination, not just an optimisation (see gfx_paint_op's own header).
    BUDGET = 20000
    naive_pushes = naive_flood_pushes(W, H, seed_b, B=2, budget=BUDGET)
    check(naive_pushes >= BUDGET,
          f"teeth: naive '!=B only' flood explodes past {BUDGET} pushes on the "
          f"SAME open room ({naive_pushes}) -- the 'already==C' rule is "
          "load-bearing for termination (anti-green-build)")
    check(len(want_b) < BUDGET,
          f"sanity: the real (correct) painted set is small/finite ({len(want_b)} "
          f"pts) vs the naive explosion's {BUDGET}+ pushes above")

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

    # --- cpt_boundary_prep (D-ARCMASK): the single-precision (oct_raw, u14) --
    # marshal, driven in the page-1-tenant memory map (main low-region float
    # pack + sub page 1). Angles are STRINGS: an exact BCD image of the BASIC
    # literal, which is what the resident's eval hands over. Battery incl. the
    # 1.5707963-vs-pi/2 pair -- the SINGLE-PRECISION pin: both round to
    # 1.57080 at 6 digits, so both must land in octant 2 exactly like the
    # reference (ctl_card_r95, ref 135 px vs zerobas-before 134).
    mt, subsym = make_p1_tenant_machine()
    cpt_bp = subsym["cpt_boundary_prep"]
    BOUNDARY_PREP_CASES = [
        "0", "0.01", "1", "1.50", "1.504", "1.51", "1.55", "1.57", "1.58",
        "1.60", "1.5707963", "1.5707963267949", "3", "3.14", "4.71", "6.28",
        "0.999999", "0.9999996",
    ]
    for theta in BOUNDARY_PREP_CASES:
        oct_, u14 = zboundary_prep_resident(mt, cpt_bp, theta)
        want_o, want_u = py_marshal(D(theta))
        check((oct_, u14) == (want_o, want_u),
              f"cpt_boundary_prep theta={theta} -> ({oct_},{u14}) "
              f"(want ({want_o},{want_u}))")

    # teeth 1: 1.57 and 1.58 MUST land in different octants (1 vs 2) -- the
    # wedge pin that replaced the continuous quadrant sign.
    o57, _ = zboundary_prep_resident(mt, cpt_bp, "1.57")
    o58, _ = zboundary_prep_resident(mt, cpt_bp, "1.58")
    check((o57, o58) == (1, 2), f"teeth: 1.57 -> octant {o57}, 1.58 -> "
          f"octant {o58} (want 1 vs 2)")
    # teeth 2: 1.5707963 lands EXACTLY where pi/2 does -- the 6-digit round
    # is load-bearing (delete P1 and this fails: trunc keeps it in octant 1).
    oa, ua = zboundary_prep_resident(mt, cpt_bp, "1.5707963")
    ob, ub = zboundary_prep_resident(mt, cpt_bp, "1.5707963267949")
    check((oa, ua) == (ob, ub) == (2, 0),
          f"teeth: single precision -- 1.5707963 ({oa},{ua}) == pi/2 "
          f"({ob},{ub}) == (2,0)")
    # teeth 3: the carry CHAIN (trailing nines propagating into digit 4):
    # 1.5707999 rounds to 1.57080 at 6 digits -- across pi/2 -- so it must
    # land in octant 2; a truncating P1 leaves it at 1.57079, octant 1.
    # (A carry that does NOT cross an octant boundary is invisible at u14
    # grain -- a 5e-7 relative change is under the 6e-5 u14 quantum -- which
    # is exactly why the teeth must sit on a boundary to bite.)
    oc, uc = zboundary_prep_resident(mt, cpt_bp, "1.5707999")
    check((oc, uc) == py_marshal(D("1.5707999")) and oc == 2,
          f"teeth: the 6-digit carry chain crosses pi/2 for 1.5707999 "
          f"-> ({oc},{uc}), want octant 2")

    # --- G6 DRAW leaves (same sub-ROM machine) ---
    for n, sc in DRAW_SCALE_CASES:
        got, want = zscale(m, n, sc), py_scale(n, sc)
        check(got == want, f"gdrw_scale n={n:>6} S={sc:>3} -> {got:>7} (want {want})")
    for (n, sc), want in MEASURED_SCALE.items():
        got = zscale(m, n, sc)
        check(got == want, f"gdrw_scale MEASURED n={n} S={sc} -> {got} (want {want})")
    # teeth: floor rounding instead of truncate-toward-zero would break exactly
    # the negative cases, so assert the two disagree where they should
    check(py_scale(-10, 3) == -7 and (-30 // 4) == -8,
          "teeth: the negative-count rule is truncate-toward-zero, not floor")
    for (dx, dy), ang, want in ROTATE_CASES:
        got = zrotate(m, dx, dy, ang)
        check(got == want, f"gdrw_rotate ({dx},{dy}) A{ang} -> {got} (want {want})")

    print("-------------------")
    print("test_graphics:", "PASS" if fails == 0 else f"FAIL ({fails})")
    return fails


if __name__ == "__main__":
    sys.exit(1 if run() else 0)
