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


# --- G4-arcbnd (docs/spec-basic-graphics-g4.md §5.4/§9): the arc cross- ------
# product mask polarity, pinned by scratchpad/g4_arc_boundary_capture.py.
# Both boundary tests are INCLUSIVE (<=0), and the resident's r-scaled S/E
# vectors NUDGE an artificial exact-zero rounding to +-1 (preserves direction
# at near-cardinal angles the reference is shown to distinguish -- e.g.
# CIRCLE(60,60),15,15,1.57,3.14 vs the SAME with a0=1.58 flip the inclusion
# of pixel (61,45) even though a bare round(r*cos(a0)) is identical (0) for
# both angles at r=15). Verified 4/4 exact on every pinned arc + 7/7 on the
# capture's boundary sweep BEFORE this asm rewrite; these tests lock the same
# arithmetic in the real asm (gfx_circ_keep + the resident's gfx_round_nonzero
# nudge, reproduced here in Python as the independent oracle).
import math  # noqa: E402


def rscale_vec_nudge(r, angle):
    """own-design: round(r*cos/sin(angle)), nudged to +-1 if the pre-round
    value was nonzero but rounds to 0 (G4-arcbnd). Matches gfx_round_nonzero
    + gfx_circ_axis_val (basic/graphics.asm)."""
    cx, cy = r * math.cos(angle), r * math.sin(angle)
    x = round(cx)
    if x == 0 and cx != 0:
        x = 1 if cx > 0 else -1
    y = round(cy)
    if y == 0 and cy != 0:
        y = 1 if cy > 0 else -1
    return x, -y


def py_cross(ax, ay, bx, by):
    return ax * by - ay * bx


def py_arc_arcbig(S, E):
    return py_cross(S[0], S[1], E[0], E[1]) >= 0


def py_arc_keep(S, E, arcbig, px, py):
    s_ok = py_cross(S[0], S[1], px, py) <= 0     # cross(S,P)<=0
    e_ok = py_cross(px, py, E[0], E[1]) <= 0     # cross(P,E)<=0
    return (s_ok and e_ok) if not arcbig else (s_ok or e_ok)


# (label, start_angle, end_angle) -- the 4 pinned arcs, re-used from G4_DATA
# for their (cx,cy,r) + captured point-set.
ARC_CASES = [
    ("arc_0_hpi", 0.0, 1.57), ("arc_hpi_pi", 1.57, 3.14),
    ("arc_wrap", 3.0, 1.0), ("arc_full628", 0.0, 6.28),
]


# =============================================================================
# TRIG-FREE arc boundary (spec §5.2.1 REVISED 2026-07-21) -- the independent
# Python oracle, host-fit + validated BEFORE writing the asm
# (scratchpad/g4_trigfree_final_model.py: ALL MATCH against every captured arc
# + round1 boundary re-capture). Reproduced here so the SAME battery drives the
# REAL asm (gfx_circ_bvec / gfx_circ_arcbig_calc / gfx_circ_boundary_prep,
# below) instead of just the OLD continuous-trig rscale_vec_nudge oracle.
# =============================================================================
PY_QTAB = []
for _i in range(65):
    _v = round(256 * math.sin(2 * math.pi * _i / 256))
    PY_QTAB.append(255 if _v > 255 else _v)


def py_qtab_fold(b):
    m = b & 0x7F
    return m if m <= 64 else 128 - m


def py_qtab_lookup(b):
    return PY_QTAB[py_qtab_fold(b & 0xFF)]


HALF_PI = math.pi / 2
PI_ = math.pi
THREE_HALF_PI = 3 * math.pi / 2


def py_raw_brad(theta_abs):
    """resident gfx_circ_boundary_prep: ONE bounded fp_mul (theta*128/pi) +
    round-half-up (gfx_round_arga_de) -- NOT masked/reduced."""
    return round(theta_abs * 128.0 / math.pi)


def py_resident_signs(theta_abs):
    """resident gfx_circ_boundary_prep: THREE bounded fp_cmp-style continuous
    compares (theta vs HALF_PI/THREE_HALF_PI/PI_), NOT derived from brad."""
    if theta_abs < HALF_PI:
        sign_c = 1
    elif theta_abs == HALF_PI:
        sign_c = 0
    elif theta_abs < THREE_HALF_PI:
        sign_c = -1
    elif theta_abs == THREE_HALF_PI:
        sign_c = 0
    else:
        sign_c = 1
    if theta_abs == 0:
        sign_s = 0
    elif theta_abs < PI_:
        sign_s = 1
    elif theta_abs == PI_:
        sign_s = 0
    else:
        sign_s = -1
    return sign_c, sign_s


def py_bvec_mag(r, tab):
    return (r * tab + 128) >> 8


def py_bvec_nudge(mag, sign):
    if sign == 0:
        return 0
    if mag != 0:
        return sign * mag
    return sign


def py_gfx_circ_bvec(bradlo, sign_c, sign_s, r):
    """tenant gfx_circ_bvec (pre-minor-scale; screen convention applied)."""
    tab_c = py_qtab_lookup((bradlo + 64) & 0xFF)
    x = py_bvec_nudge(py_bvec_mag(r, tab_c), sign_c)
    tab_s = py_qtab_lookup(bradlo & 0xFF)
    y = py_bvec_nudge(py_bvec_mag(r, tab_s), sign_s)
    return x, -y


def py_arcbig_calc(raw_s, raw_e):
    """tenant gfx_circ_arcbig_calc: mod-256 diff, with the exact-256-wrap fix
    (raw_e/raw_s differ but land in the SAME bucket -> forced big)."""
    diff = (raw_e - raw_s) & 0xFF
    if diff == 0 and raw_e != raw_s:
        return True
    return diff > 128


def py_bvec_record(theta_abs, r):
    """Resident-then-tenant, end to end (Python oracle): angle -> (Sx,Sy),
    raw_brad (the latter needed by py_arcbig_calc)."""
    raw = py_raw_brad(theta_abs)
    sc, ss = py_resident_signs(theta_abs)
    return py_gfx_circ_bvec(raw & 0xFF, sc, ss, r), raw


def zcirc_keep(m, arcf, svx, svy, evx, evy, arcbig, px, py):
    m.poke(m.addr("GFX_ARCF"), arcf)
    m.poke_w(m.addr("GFX_SVX"), _w16(svx))
    m.poke_w(m.addr("GFX_SVY"), _w16(svy))
    m.poke_w(m.addr("GFX_EVX"), _w16(evx))
    m.poke_w(m.addr("GFX_EVY"), _w16(evy))
    m.poke(m.addr("GFX_ARCBIG"), arcbig)
    m.poke_w(m.addr("GFX_PX"), _w16(px))
    m.poke_w(m.addr("GFX_PY"), _w16(py))
    cpu = m.call("gfx_circ_keep")
    return carry(cpu)


def zbvec(m, bradlo, bradhi, signc, signs, r, aspmaj=0, asps=256, dest="GFX_SVX"):
    """Drive the REAL tenant gfx_circ_bvec (sub/graphics.asm): pokes a 4-byte
    boundary record (brad_lo/hi, signc, signs) at GFX_SBRAD, GFX_R/ASPMAJ/ASPS,
    calls gfx_circ_bvec(HL=GFX_SBRAD, DE=dest), returns the (Vx,Vy) it wrote."""
    base = m.addr("GFX_SBRAD")
    m.poke(base, bytes([bradlo & 0xFF, bradhi & 0xFF, signc & 0xFF, signs & 0xFF]))
    m.poke_w(m.addr("GFX_R"), _w16(r))
    m.poke(m.addr("GFX_ASPMAJ"), aspmaj)
    m.poke_w(m.addr("GFX_ASPS"), _w16(asps))
    m.call("gfx_circ_bvec", h=(base >> 8) & 0xFF, l=base & 0xFF,
           d=(m.addr(dest) >> 8) & 0xFF, e=m.addr(dest) & 0xFF)
    return _rd16s(m, dest), _rd16s2(m, dest)


def _rd16s2(m, name):
    """second int16 (the Y half) at addr(name)+2."""
    b = m.peek(m.addr(name) + 2, 2)
    v = b[0] | (b[1] << 8)
    return v - 0x10000 if v >= 0x8000 else v


def zarcbig(m, raw_s, raw_e):
    """Drive the REAL tenant gfx_circ_arcbig_calc."""
    m.poke_w(m.addr("GFX_SBRAD"), _w16(raw_s))
    m.poke_w(m.addr("GFX_EBRAD"), _w16(raw_e))
    m.call("gfx_circ_arcbig_calc")
    return m.peek(m.addr("GFX_ARCBIG"))[0]


def zbvec_prep(m, sbrad, ssgnc, ssgns, ebrad, esgnc, esgns, r, aspmaj=0, asps=256):
    """Drive the REAL tenant gfx_circ_bvec_prep end to end: marshals the two
    boundary records + GFX_R/ASPMAJ/ASPS, calls it, returns (S, E, arcbig) as
    read back from GFX_SVX/SVY/EVX/EVY/GFX_ARCBIG."""
    m.poke(m.addr("GFX_SBRAD"), bytes([sbrad & 0xFF, (sbrad >> 8) & 0xFF,
                                        ssgnc & 0xFF, ssgns & 0xFF]))
    m.poke(m.addr("GFX_EBRAD"), bytes([ebrad & 0xFF, (ebrad >> 8) & 0xFF,
                                        esgnc & 0xFF, esgns & 0xFF]))
    m.poke_w(m.addr("GFX_R"), _w16(r))
    m.poke(m.addr("GFX_ASPMAJ"), aspmaj)
    m.poke_w(m.addr("GFX_ASPS"), _w16(asps))
    m.call("gfx_circ_bvec_prep")
    S = (_rd16s(m, "GFX_SVX"), _rd16s2(m, "GFX_SVX"))
    E = (_rd16s(m, "GFX_EVX"), _rd16s2(m, "GFX_EVX"))
    big = m.peek(m.addr("GFX_ARCBIG"))[0]
    return S, E, big


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


def zboundary_prep_resident(mt, cpt_addr, theta_abs, dest="GFX_SBRAD"):
    """Drive cpt_boundary_prep (the CIRCLE-parse tenant's moved brad/sign math,
    sub/circleparse.asm -- was resident gfx_circ_boundary_prep) on the page-1
    tenant machine `mt`: poke a canonical FPNUM into ARGA, point GFX_CS_AY at
    `dest`, call, return (brad_raw, sign_c, sign_s) from the record it wrote.
    RAM cells (ARGA/GFX_*) are addressed via RES_SYM (identical either side)."""
    poke_fpnum(mt, mt.addr("ARGA"), theta_abs)
    mt.poke_w(mt.addr("GFX_CS_AY"), mt.addr(dest))
    mt.call(cpt_addr)
    b = mt.peek(mt.addr(dest), 2)
    brad = b[0] | (b[1] << 8)
    signc = mt.peek(mt.addr(dest) + 2)[0]
    signs = mt.peek(mt.addr(dest) + 3)[0]
    to_signed = lambda v: v - 256 if v >= 128 else v
    return brad, to_signed(signc), to_signed(signs)


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
                    os.path.join(ROOT, "basic", "main-reloc.asm"), RES_ROM, RES_SYM],
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

    # --- gfx_cross_ge0: the integer arc cross-product sign test (spec §5.2) ----
    for ax, ay, bx, by in CROSS_CASES:
        m.poke_w(m.addr("GFX_CS_AX"), _w16(ax))
        m.poke_w(m.addr("GFX_CS_AY"), _w16(ay))
        m.poke_w(m.addr("GFX_CS_BX"), _w16(bx))
        m.poke_w(m.addr("GFX_CS_BY"), _w16(by))
        cpu = m.call("gfx_cross_ge0")
        got = carry(cpu)
        want = py_cross_ge0(ax, ay, bx, by)
        check(got == want, f"gfx_cross_ge0 A=({ax:4d},{ay:4d}) B=({bx:4d},{by:4d}) "
              f"-> {got} (want {want})")

    # --- gfx_circ_keep: the arc mask polarity, pinned by scratchpad/g4_arc_ -----
    # boundary_capture.py (G4-arcbnd). S=(1,0),E=(0,1) is a small(<=pi) sweep
    # covering the first quadrant; a battery of direct polarity/boundary checks
    # plus the FULL captured-arc integration test (below) locks the resolved rule.
    KEEP_CASES = [
        # arcf, S,         E,        arcbig, P,        want
        (1, (15, 0), (0, -15), 0, (15, 0), True),      # P == S itself -> keep
        (1, (15, 0), (0, -15), 0, (0, -15), True),     # P == E itself -> keep
        (1, (15, 0), (0, -15), 0, (11, -11), True),    # clearly inside
        (1, (15, 0), (0, -15), 0, (-11, -11), False),  # clearly outside
        (1, (1, -15), (-15, -1), 0, (1, -15), True),   # nudged S == the boundary pixel itself
        (0, (15, 0), (0, -15), 0, (-11, -11), True),   # ARCF=0 -> always keep
    ]
    for arcf, S, E, arcbig, P, want in KEEP_CASES:
        got = zcirc_keep(m, arcf, S[0], S[1], E[0], E[1], arcbig, P[0], P[1])
        check(got == want, f"gfx_circ_keep ARCF={arcf} S={S} E={E} big={arcbig} "
              f"P={P} -> {got} (want {want})")

    # --- FULL arc integration: octant generator + arc mask == every pinned -----
    # captured VG-8020 arc, EXACTLY (0 diffs) -- the crux-3 de-risker + the
    # G4-arcbnd resolution, emulator-free. Reproduces the resident's nudge in
    # Python (rscale_vec_nudge) as an independent oracle, then drives the REAL
    # asm (gfx_circ_init/next for the octant sequence, gfx_circ_keep for the
    # mask) to reproduce the identical point set.
    for label, s, e in ARC_CASES:
        d = G4_DATA[label]
        r = int(d["ops"].split(")")[1].split(",")[1])
        S = rscale_vec_nudge(r, abs(s))
        E = rscale_vec_nudge(r, abs(e))
        arcbig = 1 if py_arc_arcbig(S, E) else 0
        ref = {(x, y) for x, y in d["pts"]}
        got = set()
        for dx, dy in pymirror(zcirc_octant_steps(m, r)):
            if zcirc_keep(m, 1, S[0], S[1], E[0], E[1], arcbig, dx, dy):
                got.add((d["cx"] + dx, d["cy"] + dy))
        check(got == ref, f"gfx_circ arc {label} (S={S} E={E} big={arcbig}) == "
              f"captured VG-8020 (n={d['n']})"
              + ("" if got == ref else f"  DIFF {sorted(got ^ ref)[:6]}"))

    # teeth (anti-green-build): P==S and P==E (an endpoint testing itself, cross
    # product exactly 0) MUST be kept under the resolved inclusive rule; a
    # strict "<0"/">0" polarity would flip both to rejected. The two P==S/P==E
    # rows in KEEP_CASES above already assert `want=True` for exactly this
    # boundary case, so a regression to strict polarity fails THIS suite.
    check(zcirc_keep(m, 1, 15, 0, 0, -15, 0, 15, 0) is True,
          "teeth: P==S (cross==0 exactly) is kept under the inclusive <=0 rule")

    # =========================================================================
    # G4 TRIG-FREE arc boundary (spec §5.2.1 REVISED 2026-07-21) -- the
    # replacement for the float SIN/COS pipeline that infinite-looped
    # (scratchpad/g4_hang_probe.py). Drives the REAL new tenant asm
    # (gfx_circ_bvec / gfx_circ_arcbig_calc / gfx_circ_bvec_prep) against the
    # independent Python oracle above, host-fit BEFORE this asm was written
    # (scratchpad/g4_trigfree_final_model.py).
    # =========================================================================

    # --- gfx_circ_bvec: a battery of (brad, sign_c, sign_s, r) incl. every
    # brad the 4 pinned arcs + round1 re-captures actually use, plus the
    # near-cardinal brad=64/192 boundary where BOTH signs occur. ---
    BVEC_CASES = []
    for r in (15, 20, 1, 255):
        for bradlo in (0, 1, 40, 41, 63, 64, 65, 96, 122, 127, 128, 129, 160,
                       192, 200, 255):
            for sc in (1, -1, 0):
                for ss in (1, -1, 0):
                    BVEC_CASES.append((bradlo, sc, ss, r))
    for bradlo, sc, ss, r in BVEC_CASES:
        got = zbvec(m, bradlo, 0, sc & 0xFF, ss & 0xFF, r)
        want = py_gfx_circ_bvec(bradlo, sc, ss, r)
        check(got == want,
              f"gfx_circ_bvec brad={bradlo:3d} signc={sc:2d} signs={ss:2d} r={r:3d} "
              f"-> {got} (want {want})")

    # teeth: the near-cardinal nudge is what distinguishes brad=64 (cos~0) with
    # sign_c=+1 from sign_c=-1 -- a bare round(r*cos) (no nudge) would give 0
    # for BOTH, losing the direction the reference is shown to preserve
    # (spec §5.4, the 1.57-vs-1.58 pin). Assert the asm actually keeps them
    # apart AND matches the +-1 nudge exactly (not just "nonzero").
    xp, _ = zbvec(m, 64, 0, 1, 1, 15)
    xn, _ = zbvec(m, 64, 0, -1 & 0xFF, 1, 15)
    check(xp == 1 and xn == -1 and xp != xn,
          f"teeth: gfx_circ_bvec brad=64 nudge distinguishes sign_c=+1 ({xp}) "
          f"from sign_c=-1 ({xn})")

    # --- gfx_circ_arcbig_calc: mod-256 diff + the exact-wrap fix (raw_e/raw_s
    # differ but land in the SAME bucket, e.g. 0 vs 256 for a near-2pi sweep --
    # arc_full628's actual raw pair) ---
    ARCBIG_CASES = [
        (0, 64, False), (64, 0, True), (64, 128, False), (0, 256, True),
        (0, 0, False), (256, 0, True), (122, 41, True), (0, 122, False),
        (200, 210, False), (10, 200, True), (0, 129, True), (0, 128, False),
    ]
    for rs, re_, want in ARCBIG_CASES:
        got = bool(zarcbig(m, rs, re_))
        py_want = py_arcbig_calc(rs, re_)
        check(got == want == py_want,
              f"gfx_circ_arcbig_calc raw_s={rs} raw_e={re_} -> {got} (want {want})")

    # --- FULL trig-free pipeline: gfx_circ_bvec_prep + the (unchanged) octant
    # generator/mask == every pinned captured VG-8020 arc, EXACTLY (0 diffs).
    # This is the actual crux-3 de-risker for the REVISED design (the OLD
    # rscale_vec_nudge-fed integration test above only re-proves gfx_circ_keep's
    # polarity, not this new brad/table/nudge chain). angle -> (brad, signs) is
    # computed by py_raw_brad/py_resident_signs, standing in for the RESIDENT
    # gfx_circ_boundary_prep (proven separately below); everything from there
    # on (gfx_circ_bvec_prep, gfx_circ_arcbig_calc, the octant loop, the mask)
    # is the REAL asm.
    def full_trigfree(m, cx, cy, r, a0, a1, aspmaj=0, asps=256):
        raw_s = py_raw_brad(abs(a0))
        sc_s, ss_s = py_resident_signs(abs(a0))
        raw_e = py_raw_brad(abs(a1))
        sc_e, ss_e = py_resident_signs(abs(a1))
        S, E, big = zbvec_prep(m, raw_s & 0xFFFF, sc_s & 0xFF, ss_s & 0xFF,
                                raw_e & 0xFFFF, sc_e & 0xFF, ss_e & 0xFF,
                                r, aspmaj, asps)
        got = set()
        for dx, dy in pymirror(zcirc_octant_steps(m, r)):
            if zcirc_keep(m, 1, S[0], S[1], E[0], E[1], big, dx, dy):
                got.add((cx + dx, cy + dy))
        return got, S, E, big

    for label, s, e in ARC_CASES:
        d = G4_DATA[label]
        r = int(d["ops"].split(")")[1].split(",")[1])
        ref = {(x, y) for x, y in d["pts"]}
        got, S, E, big = full_trigfree(m, d["cx"], d["cy"], r, s, e)
        check(got == ref,
              f"TRIG-FREE gfx_circ_bvec_prep arc {label} (S={S} E={E} big={big}) "
              f"== captured VG-8020 (n={d['n']})"
              + ("" if got == ref else f"  DIFF {sorted(got ^ ref)[:6]}"))

    # round1 boundary re-captures (scratchpad/g4_arc_boundary_capture.py) --
    # the same targeted near-cardinal captures that pinned G4-arcbnd originally.
    for label, c in G4_BND["round1"].items():
        ops = c["ops"]
        args = ops.split(")", 1)[1].lstrip(",").split(",")
        r = int(args[0])
        a0, a1 = float(args[2]), float(args[3])
        ref = {(x, y) for x, y in c["pts"]}
        got, S, E, big = full_trigfree(m, c["cx"], c["cy"], r, a0, a1)
        check(got == ref,
              f"TRIG-FREE gfx_circ_bvec_prep {label} ({a0},{a1}) (S={S} E={E} "
              f"big={big}) == captured (n={len(ref)})"
              + ("" if got == ref else f"  DIFF {sorted(got ^ ref)[:6]}"))

    # teeth: flipping the start boundary's sign_c for arc_hpi_pi (a0=1.57,
    # quad-boundary brad=64) must regress the match -- proves the resident's
    # continuous quadrant sign (not a brad-derived one) is load-bearing.
    d = G4_DATA["arc_hpi_pi"]
    r = int(d["ops"].split(")")[1].split(",")[1])
    ref = {(x, y) for x, y in d["pts"]}
    raw_s = py_raw_brad(1.57)
    sc_s, ss_s = py_resident_signs(1.57)
    raw_e = py_raw_brad(3.14)
    sc_e, ss_e = py_resident_signs(3.14)
    S, E, big = zbvec_prep(m, raw_s, (-sc_s) & 0xFF, ss_s & 0xFF,
                            raw_e, sc_e & 0xFF, ss_e & 0xFF, r)
    bad = set()
    for dx, dy in pymirror(zcirc_octant_steps(m, r)):
        if zcirc_keep(m, 1, S[0], S[1], E[0], E[1], big, dx, dy):
            bad.add((d["cx"] + dx, d["cy"] + dy))
    check(bad != ref, "teeth: flipping arc_hpi_pi's start sign_c breaks the "
          "captured match (anti-green-build)")

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

    # --- cpt_boundary_prep (§5.2.1 REVISED, now the CIRCLE-parse TENANT's ---
    # moved brad + continuous quadrant-sign marshal, sub/circleparse.asm): driven
    # in the page-1-tenant memory map (main low-region float pack + sub page 1).
    # Battery incl. the 1.57-vs-1.58 pair (the whole point of the continuous-
    # not-brad-derived sign, spec §5.4) and every cardinal/near-cardinal edge.
    mt, subsym = make_p1_tenant_machine()
    cpt_bp = subsym["cpt_boundary_prep"]
    BOUNDARY_PREP_CASES = [
        0.0, 0.01, 1.0, 1.50, 1.504, 1.51, 1.55, 1.57, 1.58, 1.60,
        math.pi / 2, 3.0, 3.14, math.pi, 4.71238898038469, 6.28,
    ]
    for theta in BOUNDARY_PREP_CASES:
        brad, sc, ss = zboundary_prep_resident(mt, cpt_bp, theta)
        want_brad = py_raw_brad(theta)
        want_sc, want_ss = py_resident_signs(theta)
        check(brad == want_brad and sc == want_sc and ss == want_ss,
              f"cpt_boundary_prep theta={theta} -> brad={brad} "
              f"(want {want_brad}) signc={sc} (want {want_sc}) "
              f"signs={ss} (want {want_ss})")

    # teeth: 1.57 and 1.58 MUST resolve to different sign_c despite an
    # (almost certainly) identical brad -- the whole reason the sign comes
    # from a continuous compare, not brad>>6.
    b57, sc57, _ = zboundary_prep_resident(mt, cpt_bp, 1.57)
    b58, sc58, _ = zboundary_prep_resident(mt, cpt_bp, 1.58)
    check(sc57 != sc58, f"teeth: cpt_boundary_prep distinguishes theta=1.57 "
          f"(brad={b57} signc={sc57}) from 1.58 (brad={b58} signc={sc58})")

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
