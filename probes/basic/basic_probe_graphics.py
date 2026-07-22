#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Graphics G2 acceptance — the load-bearing VG-8020 DIFFERENTIAL for PSET /
PRESET / POINT (docs/spec-basic-graphics-g2.md §8).

Two phases, each run on BOTH the Philips VG-8020 reference and the merged zerobas
machine (C-BIOS_MSX1_EU_REPACK_DISK), asserting byte/text-identical results:

  PHASE A -- pixel plane differential (the colour clash lives here). Each case runs
    `COLOR 15,4,7 : SCREEN 2` (the §11.3 pinned post-CLS state: every colour byte
    $04 = fg 0 | bg BAKCLR 4), then the PSET/PRESET ops, then spins in a GOTO-self
    loop so the SCREEN-2 "Ok" prompt never rewrites the top-left cells. We read the
    pattern byte AND the colour byte back from VRAM (debug read_block VRAM) mid-loop
    and assert both machines wrote identical bytes. Reading the COLOUR plane is the
    whole point (spec §8 teeth): a PSET that sets the right pattern bit but the wrong
    attribute nibble passes a pattern-only check while being wrong. (No VPOKE for the
    pre-state: a VPOKE leaves the VDP mid-write and perturbs the tenant's very next
    read -- COLOR/SCREEN gives the same known state without that hazard.)

  PHASE B -- behavioural differential (clip / errors / POINT / STEP). Cases print a
    tagged outcome to the SCREEN-0 text plane (ON ERROR traps the raisers); we
    compare the tag + its numeric answer (trailing prompt text ignored).

Boot-per-case in phase A (the GOTO-self loop blocks KEYBUF, so batching can't
advance). Needs the merged machine installed (make repack-machine) + openMSX.

    make graphics-acceptance      # or: python3 probes/basic/basic_probe_graphics.py
"""
from __future__ import annotations

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

REF = os.environ.get("ZEROBAS_REF_MACHINE", "Philips_VG_8020")
ZB = os.environ.get("ZEROBAS_SUBROM_INTTEST_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")

INIT = "COLOR15,4,7:SCREEN2"          # §11.3 state: colour plane = $04 (fg0|bg4)


def paddr(x: int, y: int) -> int:
    return (y >> 3) * 256 + (x >> 3) * 8 + (y & 7)


def prog(stmts: list[str]) -> list[str]:
    """Append a GOTO-self loop so the case holds SCREEN 2 (the prompt never
    corrupts the test cell). The loop line's number = 10*(len+1)."""
    return stmts + [f"GOTO {10 * (len(stmts) + 1)}"]


# label, ops (one line), pixel read back, expected pattern byte, expected colour byte
DRAW_CASES = [
    ("pset_single",   "PSET(0,0),15",                        (0, 0), "80", "f4"),
    ("pset_clash",    "PSET(0,0),15:PSET(1,0),6",            (0, 0), "c0", "64"),
    ("pset_clear_bg", "PSET(0,0),15:PSET(1,0),4",            (0, 0), "80", "f4"),
    ("preset_erase",  "PSET(0,0),15:PRESET(0,0)",            (0, 0), "00", "f4"),
    ("preset_color",  "PRESET(0,0),6",                       (0, 0), "80", "64"),
    ("pset_step",     "PSET(0,0),15:PSET STEP(1,0),9",       (0, 0), "c0", "94"),
    ("pset_mid",      "PSET(100,50),9",                      (100, 50), "08", "94"),
    ("pset_default",  "PSET(0,0)",                           (0, 0), "80", "f4"),  # c=FORCLR=15
    ("clip_noop",     "PSET(300,100):PSET(0,192):PSET(-1,0)",(0, 0), "00", "04"),
]


def phase_a() -> int:
    fails = 0
    print("=== PHASE A: pixel + colour plane differential (VG-8020 vs zerobas) ===")
    for label, ops, (x, y), ep, ec in DRAW_CASES:
        pa = paddr(x, y)
        segs = [(pa, 1), (pa + 0x2000, 1)]
        specs = [("stored", prog([INIT, ops]))]
        ref = omsx_repl.run_cases(REF, specs, batch=False, capture=("vram_segs", segs))[0]
        zb = omsx_repl.run_cases(ZB, specs, batch=False, capture=("vram_segs", segs))[0]
        ok = ref is not None and ref == zb
        note = "" if (zb and zb[:2] == ep and zb[2:4] == ec) else f"  [oracle {ep}{ec}]"
        fails += not ok
        rp = f"{ref[:2]}/{ref[2:4]}" if ref else "None"
        zp = f"{zb[:2]}/{zb[2:4]}" if zb else "None"
        print(f"  {'PASS' if ok else 'FAIL'} {label:14} ref={rp} zb={zp}{note}")
    return fails


# label, program lines, tag whose numeric answer we compare
BEHAV_CASES = [
    ("pset_scr0_err", ["ON ERROR GOTO 40", "SCREEN0:PSET(0,0)",
                       'PRINT"OK":END', 'PRINT"E";ERR:END'], "E"),
    ("pset_ovf_err",  ["ON ERROR GOTO 40", "SCREEN2:PSET(32768,0)",
                       'PRINT"OK":END', 'SCREEN0:PRINT"E";ERR:END'], "E"),
    ("pset_offscr_ok",["ON ERROR GOTO 40", "SCREEN2:PSET(300,100)",
                       'SCREEN0:PRINT"OK":END', 'PRINT"E";ERR:END'], "OK"),
    ("point_vals",    ["SCREEN2:COLOR15,4:PSET(50,50),9",
                       "A=POINT(50,50):B=POINT(51,50):C=POINT(300,300)",
                       'SCREEN0:PRINT"P";A;B;C'], "P"),
    ("point_step",    ["SCREEN2:COLOR15,4:PSET(50,50),9", "D=POINT STEP(0,0)",
                       'SCREEN0:PRINT"S";D'], "S"),
]


def _answer(raw: str | None, tag: str) -> str | None:
    """Extract `tag` and the numeric answer following it (digits/spaces/minus),
    stopping at the first other letter -- so the trailing BASIC prompt / 'Ok' /
    'No RESUME' text (which differs per machine) is ignored."""
    if not raw:
        return None
    txt = " ".join("".join(raw).split())
    m = re.search(re.escape(tag) + r"[ \d\-]*", txt)
    return re.sub(r"\s+", " ", m.group(0)).strip() if m else None


def phase_b() -> int:
    fails = 0
    print("=== PHASE B: behavioural differential (clip / errors / POINT / STEP) ===")
    specs = [("stored", body) for _, body, _ in BEHAV_CASES]
    ref = omsx_repl.run_cases(REF, specs, batch=True, reset=("NEW", "CLS"))
    zb = omsx_repl.run_cases(ZB, specs, batch=True, reset=("NEW", "CLS"))
    for (label, _, tag), r, z in zip(BEHAV_CASES, ref, zb):
        ra, za = _answer(r, tag), _answer(z, tag)
        ok = ra is not None and ra == za
        fails += not ok
        print(f"  {'PASS' if ok else 'FAIL'} {label:16} ref={ra!r} zb={za!r}")
    return fails


# =====================================================================
# G3 -- LINE (+ ,B / ,BF). docs/spec-basic-graphics-g3.md §8. The load-bearing
# differential: draw each LINE case on BOTH machines, read the pattern (and, where
# the clash matters, colour) plane of the covered band back, assert byte-identical.
# INIT clears SCREEN 2 to bg 1 / fg 15 so a drawn pixel = fg nibble F, bg = 1.
LINIT = "COLOR15,1,1:SCREEN2:CLS"


def band_segs(xr, yr, color=False):
    off = 0x2000 if color else 0
    cols = range(xr[0] >> 3, (xr[1] >> 3) + 1)
    rows = range(yr[0] >> 3, (yr[1] >> 3) + 1)
    return [(off + cr * 256 + cc * 8, 8) for cr in rows for cc in cols]


# label, ops, x-range, y-range, read-colour-plane?  (each a pinned §11 fact)
LINE_CASES = [
    ("shallow",     "LINE(0,0)-(20,7),15",            (0, 20), (0, 7),  False),
    ("steep",       "LINE(0,0)-(7,20),15",            (0, 7),  (0, 20), False),
    ("diag45",      "LINE(0,0)-(15,15),15",           (0, 15), (0, 15), False),
    ("negslope",    "LINE(0,15)-(15,0),15",           (0, 15), (0, 15), False),
    ("rev_shallow", "LINE(20,7)-(0,0),15",            (0, 20), (0, 7),  False),  # dir-indep
    ("horiz",       "LINE(0,3)-(20,3),15",            (0, 20), (0, 7),  False),
    ("vert",        "LINE(4,0)-(4,20),15",            (0, 7),  (0, 20), False),
    ("degenerate",  "LINE(5,5)-(5,5),15",             (0, 12), (0, 12), False),
    ("continuation","PSET(3,3):LINE-(3,12),15",       (0, 8),  (0, 15), False),
    ("step_chain",  "PSET(10,10):LINE STEP(2,2)-STEP(3,3),15", (8, 23), (8, 23), False),
    ("box_b",       "LINE(1,1)-(14,10),15,B",         (0, 15), (0, 11), False),
    ("box_bf",      "LINE(1,1)-(14,10),15,BF",        (0, 15), (0, 11), False),
    ("box_rev",     "LINE(14,10)-(1,1),15,B",         (0, 15), (0, 11), False),  # reversed corners
    ("clash_line",  "LINE(0,0)-(15,0),6",             (0, 15), (0, 1),  True),   # colour plane
    ("clip_negTL",  "LINE(-100,-100)-(50,50),15",     (0, 24), (0, 24), False),  # clip = masking
    ("clip_frac",   "LINE(-7,-2)-(60,18),15",         (0, 24), (0, 8),  False),  # frac-slope off-start
    ("clip_alloff", "LINE(300,300)-(400,400),15",     (0, 24), (0, 24), False),  # fully-off = blank
]


def phase_c() -> int:
    fails = 0
    print("=== PHASE C: LINE pixel/colour plane differential (VG-8020 vs zerobas) ===")
    for label, ops, xr, yr, col in LINE_CASES:
        segs = band_segs(xr, yr, color=col)
        specs = [("stored", prog([LINIT, ops]))]
        ref = omsx_repl.run_cases(REF, specs, batch=False, capture=("vram_segs", segs))[0]
        zb = omsx_repl.run_cases(ZB, specs, batch=False, capture=("vram_segs", segs))[0]
        ok = ref is not None and ref == zb
        fails += not ok
        plane = "colour" if col else "pattern"
        note = "" if ok else f"  ref={ref} zb={zb}"
        print(f"  {'PASS' if ok else 'FAIL'} {label:13} {plane} band {len(ref or '')//2}B{note}")
    return fails


# label, program lines, tag  (SCREEN0-funnelled behaviour: errors / GRPAC)
LINE_BEHAV = [
    ("ovf_end",   ["ON ERROR GOTO 40", "SCREEN2:LINE(0,0)-(32768,0),15",
                   'SCREEN0:PRINT"K":END', 'SCREEN0:PRINT"E";ERR:END'], "E"),
    # -32768 is a valid int16 -> no ERR 6 (unlike -32769). Tested with a SHORT
    # extreme-coordinate line: a full (0,0)-(-32768,0) span is a documented perf
    # edge (spec §4.4 / §9 G3-perf) -- masking iterates all 32768 off-screen steps
    # (~1 s under EI), too slow to differential on completion, so it is out of scope.
    ("ovf_ok_min",["ON ERROR GOTO 40", "SCREEN2:LINE(-32768,0)-(-32767,0),15",
                   'SCREEN0:PRINT"K":END', 'SCREEN0:PRINT"E";ERR:END'], "K"),
    ("scr0_err",  ["ON ERROR GOTO 40", "SCREEN0:LINE(0,0)-(10,10),15",
                   'SCREEN0:PRINT"K":END', 'SCREEN0:PRINT"E";ERR:END'], "E"),
    ("bf_scr0",   ["ON ERROR GOTO 40", "SCREEN0:LINE(0,0)-(9,9),15,BF",
                   'SCREEN0:PRINT"K":END', 'SCREEN0:PRINT"E";ERR:END'], "E"),
    ("nodash",    ["ON ERROR GOTO 40", "SCREEN2:LINE(5,5)",
                   'SCREEN0:PRINT"K":END', 'SCREEN0:PRINT"E";ERR:END'], "E"),
    ("badsuffix", ["ON ERROR GOTO 40", "SCREEN2:LINE(0,0)-(9,9),15,X",
                   'SCREEN0:PRINT"K":END', 'SCREEN0:PRINT"E";ERR:END'], "E"),
    ("grpac_line",["SCREEN2:PSET(5,5):LINE(10,20)-(30,40)",
                   'SCREEN0:PRINT"G";PEEK(&HFCB7)+256*PEEK(&HFCB8);PEEK(&HFCB9)+256*PEEK(&HFCBA)'], "G"),
    ("grpac_box", ["SCREEN2:LINE(10,10)-(30,20),15,B",
                   'SCREEN0:PRINT"B";PEEK(&HFCB7)+256*PEEK(&HFCB8);PEEK(&HFCB9)+256*PEEK(&HFCBA)'], "B"),
    ("off_ok",    ["ON ERROR GOTO 40", "SCREEN2:LINE(0,0)-(300,300),15",
                   'SCREEN0:PRINT"K":END', 'SCREEN0:PRINT"E";ERR:END'], "K"),
]


def phase_d() -> int:
    fails = 0
    print("=== PHASE D: LINE behaviour (errors / GRPAC / clip-ok) ===")
    specs = [("stored", body) for _, body, _ in LINE_BEHAV]
    ref = omsx_repl.run_cases(REF, specs, batch=True, reset=("NEW", "CLS"))
    zb = omsx_repl.run_cases(ZB, specs, batch=True, reset=("NEW", "CLS"))
    for (label, _, tag), r, z in zip(LINE_BEHAV, ref, zb):
        ra, za = _answer(r, tag), _answer(z, tag)
        ok = ra is not None and ra == za
        fails += not ok
        print(f"  {'PASS' if ok else 'FAIL'} {label:12} ref={ra!r} zb={za!r}")
    return fails



# =====================================================================
# G4 -- CIRCLE (+ aspect ellipse + start/end-angle arcs + negative-angle
# spokes). docs/spec-basic-graphics-g4.md §8. Same INIT/pattern as G3
# (LINIT: COLOR15,1,1:SCREEN2:CLS -- drawn pixel = fg 15, bg 1).

# label, ops, centre, half-band, read-colour-plane?
CIRCLE_CASES = [
    ("circ_r4",  "CIRCLE(40,40),4,15",  (40, 40), 6, False),
    ("circ_r7",  "CIRCLE(40,40),7,15",  (40, 40), 9, False),
    ("circ_r8",  "CIRCLE(40,40),8,15",  (40, 40), 10, False),
    ("circ_r12", "CIRCLE(60,60),12,15", (60, 60), 14, False),
    ("circ_r15", "CIRCLE(60,60),15,15", (60, 60), 17, False),
    ("circ_r20", "CIRCLE(80,80),20,15", (80, 80), 22, False),
    ("ell_a025", "CIRCLE(80,80),20,15,,,.25", (80, 80), 22, False),
    ("ell_a05",  "CIRCLE(80,80),20,15,,,.5",  (80, 80), 22, False),
    ("ell_a2",   "CIRCLE(80,80),20,15,,,2",   (80, 80), 22, False),
    ("ell_a3",   "CIRCLE(80,80),20,15,,,3",   (80, 80), 22, False),
    ("ell_a05r15", "CIRCLE(60,60),15,15,,,.5", (60, 60), 17, False),
    ("arc_0_hpi",    "CIRCLE(60,60),15,15,0,1.57",    (60, 60), 17, False),
    ("arc_hpi_pi",   "CIRCLE(60,60),15,15,1.57,3.14", (60, 60), 17, False),
    ("arc_wrap",     "CIRCLE(60,60),15,15,3,1",       (60, 60), 17, False),
    ("arc_full628",  "CIRCLE(60,60),15,15,0,6.28",    (60, 60), 17, False),
    ("spoke_270",    "CIRCLE(60,60),15,15,-1.57,0",   (60, 60), 17, False),
    ("spoke_wedge2", "CIRCLE(60,60),15,15,-0.1,-1.57", (60, 60), 17, False),
    ("clash_circle", "CIRCLE(40,40),8,6", (40, 40), 10, True),   # colour plane
    ("r_zero",       "CIRCLE(50,50),0,15", (50, 50), 2, False),
]


def phase_e() -> int:
    fails = 0
    print("=== PHASE E: CIRCLE pixel/colour plane differential (VG-8020 vs zerobas) ===")
    for label, ops, (cx, cy), h, col in CIRCLE_CASES:
        xr = (max(0, cx - h), cx + h)
        yr = (max(0, cy - h), cy + h)
        segs = band_segs(xr, yr, color=col)
        specs = [("stored", prog([LINIT, ops]))]
        ref = omsx_repl.run_cases(REF, specs, batch=False, capture=("vram_segs", segs))[0]
        zb = omsx_repl.run_cases(ZB, specs, batch=False, capture=("vram_segs", segs))[0]
        ok = ref is not None and ref == zb
        fails += not ok
        plane = "colour" if col else "pattern"
        note = "" if ok else f"  ref={ref} zb={zb}"
        print(f"  {'PASS' if ok else 'FAIL'} {label:14} {plane} band {len(ref or '')//2}B{note}")
    return fails


# label, program lines, tag  (SCREEN0-funnelled behaviour: errors / GRPAC / work-area)
# GXPOS=$FCB3/$FCB4 (LE), GYPOS=$FCB5/$FCB6, GRPACX=$FCB7/$FCB8, GRPACY=$FCB9/$FCBA
# (arc §11.5 / g4_circle_char3.py gxpos_pattern -- same cells LINE_BEHAV already reads).
CIRCLE_BEHAV = [
    ("ovf_centre", ["ON ERROR GOTO 40", "SCREEN2:CIRCLE(32768,0),10",
                    'SCREEN0:PRINT"K":END', 'SCREEN0:PRINT"E";ERR:END'], "E"),
    ("ovf_radius", ["ON ERROR GOTO 40", "SCREEN2:CIRCLE(0,0),32768",
                    'SCREEN0:PRINT"K":END', 'SCREEN0:PRINT"E";ERR:END'], "E"),
    ("scr0_err",   ["ON ERROR GOTO 40", "SCREEN0:CIRCLE(5,5),3",
                    'SCREEN0:PRINT"K":END', 'SCREEN0:PRINT"E";ERR:END'], "E"),
    ("colour16_err", ["ON ERROR GOTO 40", "SCREEN2:CIRCLE(5,5),3,16",
                      'SCREEN0:PRINT"K":END', 'SCREEN0:PRINT"E";ERR:END'], "E"),
    ("aspect_neg_err", ["ON ERROR GOTO 40", "SCREEN2:CIRCLE(5,5),3,,,,-1",
                        'SCREEN0:PRINT"K":END', 'SCREEN0:PRINT"E";ERR:END'], "E"),
    ("clip_offscr_ok", ["ON ERROR GOTO 40", "SCREEN2:CIRCLE(300,300),10",
                        'SCREEN0:PRINT"K":END', 'SCREEN0:PRINT"E";ERR:END'], "K"),
    ("clip_neg_ok",    ["ON ERROR GOTO 40", "SCREEN2:CIRCLE(-5,-5),10",
                        'SCREEN0:PRINT"K":END', 'SCREEN0:PRINT"E";ERR:END'], "K"),
    ("grpac_step", ["SCREEN2:PSET(10,10):CIRCLE STEP(5,5),8",
                    'SCREEN0:PRINT"G";PEEK(&HFCB7)+256*PEEK(&HFCB8);PEEK(&HFCB9)+256*PEEK(&HFCBA)'], "G"),
    ("work_quirk", ["SCREEN2:CIRCLE(30,40),10",
                    'SCREEN0:PRINT"W";PEEK(&HFCB3)+256*PEEK(&HFCB4);PEEK(&HFCB5)+256*PEEK(&HFCB6)'], "W"),
]


def phase_f() -> int:
    fails = 0
    print("=== PHASE F: CIRCLE behaviour (errors / GRPAC / work-area quirk) ===")
    specs = [("stored", body) for _, body, _ in CIRCLE_BEHAV]
    ref = omsx_repl.run_cases(REF, specs, batch=True, reset=("NEW", "CLS"))
    zb = omsx_repl.run_cases(ZB, specs, batch=True, reset=("NEW", "CLS"))
    for (label, _, tag), r, z in zip(CIRCLE_BEHAV, ref, zb):
        ra, za = _answer(r, tag), _answer(z, tag)
        ok = ra is not None and ra == za
        fails += not ok
        print(f"  {'PASS' if ok else 'FAIL'} {label:16} ref={ra!r} zb={za!r}")
    return fails


def phase_g_rneg() -> int:
    """G4-rneg (signed-off deviation, spec §9): the REFERENCE HANGS on a
    negative radius (unsigned-wrap), so this is NOT a differential -- only
    zerobas is exercised, asserting the documented ERR 5 deviation."""
    fails = 0
    print("=== PHASE G: CIRCLE negative radius (zerobas-only; reference hangs) ===")
    body = ["ON ERROR GOTO 40", "SCREEN2:CIRCLE(30,30),-1,15",
            'SCREEN0:PRINT"K":END', 'SCREEN0:PRINT"E";ERR:END']
    zb = omsx_repl.run_cases(ZB, [("stored", body)], batch=False, reset=("NEW", "CLS"))[0]
    za = _answer(zb, "E")
    ok = za is not None and za.strip() == "E 5"
    fails += not ok
    print(f"  {'PASS' if ok else 'FAIL'} rneg_err zb={za!r} (want 'E 5')")
    return fails


# =====================================================================
# G5 -- PAINT (SCREEN-2 flood fill). docs/spec-basic-graphics-g5.md §10.
# CRITICAL (the harness-budget trap, [[paint-slow-emulated-budget-trap]]):
# PAINT is genuinely SLOW in EMULATED time -- a small `step` (the default
# 2.5 s omsx_repl uses between the RUN line and the capture) fires the
# capture MID-FILL and looks like a hang or a wrong (partial) result. Every
# fill-differential case below uses a big `step` (>=55 s, matching the
# characterization's own g5_confirm.py step=35 for a similar arena) so the
# whole-screen C!=B flood case genuinely completes before capture. ALSO a big
# `timeout` (the WALL-CLOCK kill switch) -- the total scheduled emulated
# timeline is boot + (#lines+1)*step, and an insufficient timeout can KILL
# the openMSX process mid-write, truncating the capture to look like a clean
# all-zero/empty read that is easy to mistake for a real result (found the
# hard way while characterizing this gate; always re-verify a suspicious
# result at a bigger timeout before trusting it). Compare the EFFECTIVE
# colour (POINT), not raw VRAM planes -- bit-vs-bg is unobservable/impl-free
# per the spec's own traversal-order-independence argument (§3): a bounded
# C==B fill converges to the connected set, a C!=B fill converges to the
# whole clipped screen, REGARDLESS of algorithm.
#
# THE "BORDER EATEN" MECHANISM -- own investigation, empirically derived
# (black-box, no disassembly) while gating this slice, since the shipped
# implementation initially DIVERGED from VG-8020 on every C!=B case with a
# drawn wall in the way. Root-caused + fixed two real bugs in
# sub/graphics.asm (see gfx_paint_read/gfx_paint_passable/gfx_paint_flood's
# own headers for the full mechanism + fix rationale):
#   1. A "border" is a DRAWN (pattern-bit SET) pixel whose colour == B; an
#      UNDRAWN (background) pixel is NEVER a border, regardless of whether
#      its background nibble happens to equal B (a never-drawn pixel's
#      effective colour is always its group's bg, unaffected by ANY fg
#      change elsewhere -- so a plain "effective colour == B" test wrongly
#      blocked spreading into open space whenever the caller's B happened to
#      equal the current background colour, e.g. `PAINT(100,100),7,1` with
#      BAKCLR=1). Measured: the reference still floods that case.
#   2. The seed pixel is ALWAYS painted/used as the flood origin
#      UNCONDITIONALLY, even when its own effective colour already equals B
#      or C -- "== B stops the walk" only applies to pixels the flood
#      extends INTO, never to the seed itself. Measured: a seed placed
#      EXACTLY on a drawn border pixel (colour == B) still floods past it.
#   3. gfx_paint_extend_lr's own L/R walk must use the LOOSER "passable"
#      test (only a genuine drawn==B pixel stops it) and must PAINT each
#      newly-discovered pixel INLINE as it walks (not defer to a later
#      pass) -- a group's colour only actually changes the instant a pixel
#      in it is painted, so the walk needs to see that effect immediately
#      to cross a whole chain of single-pixel-wide "eaten" walls in one
#      pass. The STRICTER gfx_paint_inside (stops at ==B OR ==C) stays used
#      only for the "should I push a new span" decision (scan_row/the
#      seed's own extend), preserving the D3 stack-budget property (an
#      already-fully-painted region is never re-pushed).
# RESIDUAL, NARROWER FINDING (reported, not silently hidden): an enclosure
# whose walls are BYTE-ALIGNED to VRAM's 8-pixel colour-group boundaries in
# BOTH axes (e.g. a `,BF`-filled box at x=16..23/y=16..47, or a `,B` outline
# at exactly (16,16)-(40,40)) never shares a single VRAM group with anything
# outside it -- clash-based escape is topologically impossible under this
# (or seemingly any pixel-accurate) model, yet the VG-8020 reference still
# escapes such enclosures by some other, unreverse-engineered mechanism (no
# disassembly permitted). All fixtures below therefore use DELIBERATELY
# NON-byte-aligned coordinates (the common case -- a program rarely draws a
# box at exact multiples of 8), which is what the fix above is verified
# against; a byte-aligned enclosure is out of scope for this gate.
BOX = "LINE(20,20)-(60,60),15,B"       # a realistic (non-byte-aligned) 1px box

PAINT_STEP = 90.0     # emulated seconds RUN..capture (generous; see above)
PAINT_CAP_GAP = 10.0
PAINT_TIMEOUT = 900.0  # wall-clock kill switch -- generous (see above; the
                       # actual wall time is typically a few seconds under
                       # throttle-off, this just avoids a false truncation)


def paint_points_prog(setup: list[str], pts: list[tuple[int, int]]) -> list[str]:
    """SCREEN-2 setup + `pts`' POINT()s stashed to vars A,B,C.. then PRINTed
    (tagged "R") after SCREEN0 -- the g5_confirm.py methodology, the reliable
    pixel oracle (scratchpad/g5_paint_notes.md: POINT queried IN SCREEN 2,
    stashed, PRINTed after SCREEN0; the raw-VRAM renderer used during
    characterization had its own addressing bug)."""
    q = ":".join(f"{chr(65 + i)}=POINT({x},{y})" for i, (x, y) in enumerate(pts))
    pr = 'SCREEN0:PRINT"R";' + ";".join(chr(65 + i) for i in range(len(pts))) + ":END"
    return [LINIT] + setup + [q, pr]


def _points(raw: str | None, n: int) -> list[int] | None:
    if not raw:
        return None
    txt = " ".join("".join(raw).split())
    m = re.search(r"R((?:\s*-?\d+){%d})" % n, txt)
    return [int(v) for v in m.group(1).split()] if m else None


# label, setup ops, POINT sample coords (interior.., border.., far-outside)
PAINT_FILL_CASES = [
    # C==B self-limit: bounded to the box interior; the far corner (a
    # background pixel well outside) MUST stay untouched -- proves enclosure.
    ("box_bounded_c15b15", [BOX, "PAINT(40,40),15,15"],
     [(40, 40), (21, 21), (59, 59), (100, 100)]),
    # C!=B: the SAME box floods the WHOLE clipped screen (border "eaten" by
    # the group-row colour clash) -- the far corner becomes C too.
    ("box_flood_c4b15", [BOX, "PAINT(40,40),4,15"],
     [(40, 40), (21, 21), (59, 59), (100, 100)]),
    # A DIFFERENT self-colour bounded box (own fg/bg pair) -- extra
    # confidence beyond the primary fixture.
    ("box_bounded_c9b9", ["LINE(20,20)-(60,60),9,B", "PAINT(40,40),9,9"],
     [(40, 40), (21, 21), (59, 59), (100, 100)]),
    # STEP-relative seed (arc D1: same parse_coord as PSET) -- PSET plants
    # GXPOS/GYPOS near the box centre, PAINT STEP(5,5) reseeds at (40,40).
    # NB a literal STEP(0,0) (zero offset) is a REFERENCE-side degenerate
    # case (measured: it behaves unlike every other seed-placement case,
    # including a nonzero-offset STEP resolving to the exact same point) --
    # avoided here, out of scope for this gate.
    ("step_form", [BOX, "PSET(35,35)", "PAINT STEP(5,5),15,15"],
     [(40, 40), (21, 21), (59, 59), (100, 100)]),
    # Defaults: C omitted -> FORCLR (=15 per LINIT's COLOR15,1,1); B omitted
    # -> = C. Same bounded profile as box_bounded_c15b15 (C=B=15 either way).
    ("defaults_c_and_b", [BOX, "PAINT(40,40)"],
     [(40, 40), (21, 21), (59, 59), (100, 100)]),
    # ",,B" form: C omitted (-> FORCLR=15) but B explicit (=15) -- exercises
    # the empty-first-field comma path through the same bounded profile.
    ("comma_empty_c", [BOX, "PAINT(40,40),,15"],
     [(40, 40), (21, 21), (59, 59), (100, 100)]),
    # Border NOT range-checked (spec §3/§5): B=16 can never match a real 0..15
    # pixel, so this is really a C!=B flood (no error, whole screen -> C=1).
    ("border16_flood_ok", ["PAINT(5,5),1,16"],
     [(5, 5), (200, 150), (0, 0), (255, 191)]),
    # Seed on an OPEN background pixel whose colour happens to equal the
    # given border -- measured to still flood (bug #1 above: an undrawn
    # pixel is never a "border").
    ("seed_on_border_still_floods", ["PAINT(100,100),7,1"],
     [(100, 100), (6, 6)]),
    # Seed placed EXACTLY on a drawn wall pixel (its colour == the given
    # border) -- measured to still flood past it AND into the interior
    # (bug #2 above: the seed is unconditionally the flood origin).
    ("seed_on_wall_pixel", ["LINE(17,17)-(41,41),15,B", "PAINT(17,17),7,15"],
     [(17, 17), (29, 29), (6, 6)]),
]


def phase_h() -> int:
    fails = 0
    print("=== PHASE H: PAINT fill differential (VG-8020 POINT vs zerobas, "
          f"step={PAINT_STEP}s) ===")
    for label, setup, pts in PAINT_FILL_CASES:
        prog_lines = paint_points_prog(setup, pts)
        specs = [("stored", prog_lines)]
        ref = omsx_repl.run_cases(REF, specs, batch=False, step=PAINT_STEP,
                                  cap_gap=PAINT_CAP_GAP, timeout=PAINT_TIMEOUT)[0]
        zb = omsx_repl.run_cases(ZB, specs, batch=False, step=PAINT_STEP,
                                 cap_gap=PAINT_CAP_GAP, timeout=PAINT_TIMEOUT)[0]
        rp, zp = _points(ref, len(pts)), _points(zb, len(pts))
        ok = rp is not None and rp == zp
        fails += not ok
        print(f"  {'PASS' if ok else 'FAIL'} {label:22} ref={rp} zb={zp}")
    return fails


def phase_i_aliasing() -> int:
    """The RECURRING ALIASING BUG CLASS check (do not trust the static
    argument in basic/sysvars.inc's own GFX_PTOP header): run string-heap-
    heavy work (STRING$/MID$, which touch the temp-descriptor stack right
    below the PAINT span-stack window, $E3E1/TEMPBASE vs $E3E8/GFX_PTOP)
    immediately before a PAINT, in the SAME statement sequence, then assert
    BOTH the fill result (POINT samples) AND the string values (LEN) survive
    intact. A real aliasing bug would corrupt one or both."""
    fails = 0
    print("=== PHASE I: PAINT-after-string-heavy-work aliasing stress ===")
    # NB string length 40 (not e.g. 200): the VG-8020 REFERENCE's own string
    # heap raises "Out of string space" well before 200 chars for this
    # program (measured) -- unrelated to PAINT, just its resource limit. 40
    # is plenty to prove the corruption question either way.
    lines = [LINIT, 'A$=STRING$(40,"X")', 'B$=MID$(A$,10,20)', BOX,
             "PAINT(40,40),15,15",
             "L=LEN(A$):M=LEN(B$)",
             "P=POINT(40,40):Q=POINT(21,21):W=POINT(100,100)",
             'SCREEN0:PRINT"S";L;M;P;Q;W:END']
    specs = [("stored", lines)]
    ref = omsx_repl.run_cases(REF, specs, batch=False, step=PAINT_STEP,
                              cap_gap=PAINT_CAP_GAP, timeout=PAINT_TIMEOUT)[0]
    zb = omsx_repl.run_cases(ZB, specs, batch=False, step=PAINT_STEP,
                             cap_gap=PAINT_CAP_GAP, timeout=PAINT_TIMEOUT)[0]

    def vals(raw):
        if not raw:
            return None
        txt = " ".join("".join(raw).split())
        m = re.search(r"S((?:\s*-?\d+){5})", txt)
        return [int(v) for v in m.group(1).split()] if m else None

    rv, zv = vals(ref), vals(zb)
    ok = rv is not None and rv == zv
    fails += not ok
    print(f"  {'PASS' if ok else 'FAIL'} paint_after_string_heavy ref={rv} zb={zv} "
          "(L,M,P,Q,W = LEN(A$),LEN(B$),3x POINT)")
    return fails


# label, program lines, tag  (SCREEN0-funnelled errors; all raise BEFORE the
# tenant is ever invoked -- resident ex_paint's own grammar/range checks --
# so these are fast, default-step cases, unlike phase_h/i above)
PAINT_BEHAV = [
    ("scr0_err",       ["ON ERROR GOTO 40", "SCREEN0:PAINT(5,5)",
                        'SCREEN0:PRINT"K":END', 'SCREEN0:PRINT"E";ERR:END'], "E"),
    ("scr1_err",       ["ON ERROR GOTO 40", "SCREEN1:PAINT(5,5)",
                        'SCREEN0:PRINT"K":END', 'SCREEN0:PRINT"E";ERR:END'], "E"),
    ("colour16_err",   ["ON ERROR GOTO 40", "SCREEN2:PAINT(5,5),16",
                        'SCREEN0:PRINT"K":END', 'SCREEN0:PRINT"E";ERR:END'], "E"),
    ("colour_neg_err", ["ON ERROR GOTO 40", "SCREEN2:PAINT(5,5),-1",
                        'SCREEN0:PRINT"K":END', 'SCREEN0:PRINT"E";ERR:END'], "E"),
    ("offscreen_pos_err", ["ON ERROR GOTO 40", "SCREEN2:PAINT(300,100),15",
                           'SCREEN0:PRINT"K":END', 'SCREEN0:PRINT"E";ERR:END'], "E"),
    ("offscreen_neg_err", ["ON ERROR GOTO 40", "SCREEN2:PAINT(-5,-5),15",
                           'SCREEN0:PRINT"K":END', 'SCREEN0:PRINT"E";ERR:END'], "E"),
    ("ovf_err",        ["ON ERROR GOTO 40", "SCREEN2:PAINT(32768,0),15",
                        'SCREEN0:PRINT"K":END', 'SCREEN0:PRINT"E";ERR:END'], "E"),
    ("tile_str_err",   ["ON ERROR GOTO 40", 'SCREEN2:PAINT(5,5),"A",15',
                        'SCREEN0:PRINT"K":END', 'SCREEN0:PRINT"E";ERR:END'], "E"),
    # C=4,B=15 (NOT C=B) -- matches the exact combo the characterization
    # pinned (scratchpad/g5_paint_char2.py S8). Measured wrinkle: a C=B combo
    # here does NOT reject fast on the reference (it runs long enough to miss
    # the default small step -- looks like "no error" within budget, an
    # artifact of the reference's own internal check ordering, not a zerobas
    # difference); zerobas's own 4th-arg check is unconditional (grammar-only,
    # fires before any fill regardless of C/B -- basic/graphics.asm ep_syntax)
    # so only THIS pinned combo is a safe, fast differential case.
    ("fourth_arg_err", ["ON ERROR GOTO 40", "SCREEN2:PAINT(28,28),4,15,7",
                        'SCREEN0:PRINT"K":END', 'SCREEN0:PRINT"E";ERR:END'], "E"),
]


def phase_j() -> int:
    fails = 0
    print("=== PHASE J: PAINT errors (all pre-tenant, fast/default-step) ===")
    specs = [("stored", body) for _, body, _ in PAINT_BEHAV]
    ref = omsx_repl.run_cases(REF, specs, batch=True, reset=("NEW", "CLS"))
    zb = omsx_repl.run_cases(ZB, specs, batch=True, reset=("NEW", "CLS"))
    for (label, _, tag), r, z in zip(PAINT_BEHAV, ref, zb):
        ra, za = _answer(r, tag), _answer(z, tag)
        ok = ra is not None and ra == za
        fails += not ok
        print(f"  {'PASS' if ok else 'FAIL'} {label:18} ref={ra!r} zb={za!r}")
    return fails


# ===========================================================================
# G6 -- DRAW (docs/spec-basic-graphics-g6.md §10). Three phases:
#   K  the pixel differential (POINT-sampled, so pattern AND colour)
#   L  the error surface
#   M  the PERSISTENCE of S/A across RUN -- invisible to any single-program test
# ===========================================================================

# label, setup ops, POINT sample coords
DRAW_FILL_CASES = [
    # the eight directions, as a closed box drawn by DRAW alone
    ("box_udlr", ['PSET(20,20)', 'DRAW"A0S4R10D10L10U10"'],
     [(20, 20), (30, 20), (30, 30), (20, 30), (25, 20), (25, 25)]),
    # a diagonal: E moves n in BOTH axes
    ("diag_e", ['PSET(20,20)', 'DRAW"A0S4E10"'],
     [(20, 20), (25, 15), (30, 10), (25, 20)]),
    # DRAW's M-segment must be the SAME rasteriser as LINE (spec §2)
    ("m_line_identity", ['PSET(20,20)', 'DRAW"A0S4M53,37"'],
     [(20, 20), (30, 25), (40, 30), (53, 37), (40, 34)]),
    ("line_for_compare", ['LINE(20,20)-(53,37),15'],
     [(20, 20), (30, 25), (40, 30), (53, 37), (40, 34)]),
    # B = move without drawing; N = draw then restore
    ("blank_move", ['PSET(20,20)', 'DRAW"A0S4BR10D5"'],
     [(20, 20), (25, 20), (30, 20), (30, 25)]),
    ("no_update", ['PSET(20,20)', 'DRAW"A0S4NR10D5"'],
     [(25, 20), (30, 20), (20, 25), (25, 25)]),
    # scale (quarter units) and angle (relative motion only)
    ("scale_s8", ['PSET(50,50)', 'DRAW"A0S8R10"'],
     [(50, 50), (60, 50), (70, 50), (71, 50)]),
    ("scale_s2", ['PSET(50,50)', 'DRAW"A0S2R10"'],
     [(50, 50), (55, 50), (56, 50)]),
    ("angle_a1", ['PSET(50,50)', 'DRAW"S4A1R10"'],
     [(50, 50), (50, 45), (50, 40), (55, 50)]),
    ("angle_abs_m_unrotated", ['PSET(50,50)', 'DRAW"S4A1M70,50"'],
     [(50, 50), (60, 50), (70, 50)]),
    # substitutions
    ("eqvar", ['V=10', 'PSET(20,20)', 'DRAW"A0S4R=V;"'],
     [(20, 20), (25, 20), (30, 20), (31, 20)]),
    ("xsub", ['A$="R10"', 'PSET(20,20)', 'DRAW"A0S4XA$;D5"'],
     [(20, 20), (30, 20), (30, 25)]),
    ("xnest", ['A$="XB$;"', 'B$="R10"', 'PSET(20,20)', 'DRAW"A0S4XA$;"'],
     [(20, 20), (25, 20), (30, 20)]),
    # off-screen motion clips by masking (and does NOT error)
    ("clip_left", ['PSET(5,5)', 'DRAW"A0S4L100"'],
     [(5, 5), (2, 5), (0, 5)]),
    # negative count reverses; chaining + ';' separators
    ("neg_and_chain", ['PSET(40,40)', 'DRAW"A0S4U-5;R5"'],
     [(40, 40), (40, 45), (43, 45), (45, 45)]),
]

# The COLOUR rule (spec §6) is a CROSS-STATEMENT behaviour, so it gets its own
# fixtures: DRAW reads the shared attribute and writes it only on `C n`.
DRAW_COLOUR_CASES = [
    ("c_sets", ['PSET(20,20)', 'DRAW"A0S4C6R10"'], [(25, 20)]),
    ("c_persists_next_draw", ['PSET(20,20)', 'DRAW"A0S4C6R10"', 'DRAW"BM20,40R10"'],
     [(25, 20), (25, 40)]),
    # the discriminating one: a colourless DRAW inherits the PREVIOUS
    # statement's colour, so this draws in 4, not in FORCLR
    ("inherits_from_line", ['LINE(20,60)-(30,60),4', 'DRAW"BM20,80R10"'],
     [(25, 60), (25, 80)]),
    # ...while a colourless LINE re-stamps FORCLR, so the next DRAW is 15 again
    ("colourless_line_restamps", ['PSET(20,20)', 'DRAW"A0S4C6R10"',
                                  'LINE(20,100)-(30,100)', 'DRAW"BM20,120R10"'],
     [(25, 20), (25, 100), (25, 120)]),
]

# The error surface. Both outcomes are printed behind ONE distinctive tag
# ("ZK" ok / "ZE <n>" raised) so a case that is SUPPOSED to be accepted and a
# case that is supposed to raise are compared by the same extractor -- a
# per-case "expected" tag would silently pass whenever both machines produced
# the other outcome.
DRAW_BEHAV = [
    (l, ['ON ERROR GOTO 40', body, 'SCREEN0:PRINT"ZK":END',
         'SCREEN0:PRINT"ZE";ERR:END'])
    for l, body in [
        ("badletter",  'SCREEN2:DRAW"Z10"'),
        ("bare_s",     'SCREEN2:DRAW"SU10"'),
        ("bare_a",     'SCREEN2:DRAW"AU10"'),
        ("bare_c",     'SCREEN2:DRAW"CU10"'),
        ("bare_m",     'SCREEN2:DRAW"MU10"'),
        ("angle4",     'SCREEN2:DRAW"A4U10"'),
        ("colour16",   'SCREEN2:DRAW"C16U10"'),
        ("colour_neg", 'SCREEN2:DRAW"C-1U10"'),
        ("scale256",   'SCREEN2:DRAW"S256U10"'),
        ("scale255ok", 'SCREEN2:DRAW"S255U1":DRAW"S4"'),
        ("count_big",  'SCREEN2:DRAW"U99999"'),
        ("m_missing",  'SCREEN2:DRAW"M100"'),
        ("eq_nosemi",  'SCREEN2:V=10:DRAW"U=V"'),
        ("x_nosemi",   'SCREEN2:A$="U10":DRAW"XA$"'),
        ("lead_semi",  'SCREEN2:DRAW";U10"'),
        ("dbl_semi",   'SCREEN2:DRAW"U10;;D5"'),
        ("comma_sep",  'SCREEN2:DRAW"U10,D5"'),
        ("junk",       'SCREEN2:DRAW"U10*"'),
        ("screen0",    'SCREEN0:DRAW"U10"'),
        ("screen1",    'SCREEN1:DRAW"U10"'),
        ("numeric",    'SCREEN2:DRAW 5'),
        ("empty",      'SCREEN2:DRAW""'),
        ("bare_b",     'SCREEN2:DRAW"B"'),
        ("offscreen",  'SCREEN2:PSET(5,5):DRAW"U100"'),
        ("scale0",     'SCREEN2:DRAW"S0U10":DRAW"S4"'),
    ]
]


def _outcome(raw: str | None) -> str | None:
    """"ZK" (accepted) or "ZE <n>" (raised), whichever the case produced."""
    if not raw:
        return None
    txt = " ".join("".join(raw).split())
    m = re.search(r"Z[KE][ \d]*", txt)
    return re.sub(r"\s+", " ", m.group(0)).strip() if m else None


def phase_k() -> int:
    fails = 0
    print("=== PHASE K: DRAW pixel differential (POINT-sampled: pattern AND colour) ===")
    for label, setup, pts in DRAW_FILL_CASES + DRAW_COLOUR_CASES:
        specs = [("stored", paint_points_prog(setup, pts))]
        ref = omsx_repl.run_cases(REF, specs, batch=False)[0]
        zb = omsx_repl.run_cases(ZB, specs, batch=False)[0]
        ra, za = _points(ref, len(pts)), _points(zb, len(pts))
        ok = ra is not None and ra == za
        fails += not ok
        print(f"  {'PASS' if ok else 'FAIL'} {label:26} ref={ra} zb={za}")
    return fails


def phase_l() -> int:
    fails = 0
    print("=== PHASE L: DRAW errors + accepted edges ===")
    specs = [("stored", body) for _, body in DRAW_BEHAV]
    ref = omsx_repl.run_cases(REF, specs, batch=True, reset=("NEW", "CLS"))
    zb = omsx_repl.run_cases(ZB, specs, batch=True, reset=("NEW", "CLS"))
    for (label, _), r, z in zip(DRAW_BEHAV, ref, zb):
        ra, za = _outcome(r), _outcome(z)
        ok = ra is not None and ra == za
        fails += not ok
        print(f"  {'PASS' if ok else 'FAIL'} {label:14} ref={ra!r} zb={za!r}")
    return fails


def phase_m() -> int:
    """The S/A state survives a RUN (spec §4). Two programs run back to back in
    ONE boot: the first sets S8/A1, the second draws a plain U10 and reports
    where it ended up. A build that reset the state at statement/SCREEN/RUN
    entry passes every single-program test and fails only here."""
    fails = 0
    print("=== PHASE M: DRAW S/A persistence ACROSS RUN ===")
    rd = ('SCREEN0:PRINT"P";PEEK(&HFCB7)+256*PEEK(&HFCB8);'
          'PEEK(&HFCB9)+256*PEEK(&HFCBA)')
    specs = [
        ("stored", ['SCREEN2:DRAW"S8A1BM100,100"', 'PRINT"SET"']),
        ("stored", ['SCREEN2', 'PSET(100,100):DRAW"U10"', rd]),
        # and that an explicit reset in a later program takes effect
        ("stored", ['SCREEN2:DRAW"S4A0BM100,100"', 'PRINT"RST"']),
        ("stored", ['SCREEN2', 'PSET(100,100):DRAW"U10"', rd]),
    ]
    ref = omsx_repl.run_cases(REF, specs, batch=True, reset=("NEW",))
    zb = omsx_repl.run_cases(ZB, specs, batch=True, reset=("NEW",))
    for idx, label in ((1, "after S8/A1 in a PRIOR run"), (3, "after an explicit S4/A0")):
        ra, za = _answer(ref[idx], "P"), _answer(zb[idx], "P")
        ok = ra is not None and ra == za
        fails += not ok
        print(f"  {'PASS' if ok else 'FAIL'} {label:28} ref={ra!r} zb={za!r}")
    return fails


# ===========================================================================
# G7 sprites (docs/spec-basic-graphics-g7.md §10): Phases N / O / P.
# ===========================================================================
# Sprites are pure VRAM TABLE state, so the differential reads the attribute and
# pattern tables straight back out with VPEEK (no POINT sampling needed) -- the
# strongest form this arc has had: every byte the statement is supposed to write
# is compared, not a sampled consequence of it.
SPR_ATTR = 0x1B00
SPR_PAT = 0x3800


def spr_dump(base: str, n: int, extra="0") -> list[str]:
    """Stash n VRAM bytes AND the work-area values (still in the graphics mode)
    into one string, then print it in SCREEN 0. The work-area part must be read
    BEFORE the mode switch: C-BIOS's CHGMOD zeroes GXPOS/GYPOS where the
    reference's leaves them, which is a BIOS difference, not a statement one.
    CLEAR 2000 because the dump string plus the case's own strings must fit."""
    exprs = extra if isinstance(extra, (list, tuple)) else [extra]
    return ([f'A$="":FOR I=0 TO {n-1}:A$=A$+STR$(VPEEK({base}+I)):NEXT',
             'A$=A$+"|"']
            + [f'A$=A$+STR$({e})' for e in exprs]     # one per line: a stored line
            + ['SCREEN0:PRINT"R";A$'])                # longer than LINEMAX is truncated


def _spr_bytes(raw: str | None) -> str | None:
    """The dumped byte stream, with ALL whitespace removed: a 34-byte dump wraps
    the 40-column screen, and the two machines wrap at different columns, so a
    space-preserving compare would report a formatting difference as a data one.
    Every number carries STR$'s leading space, so the concatenated digit stream is
    still a faithful comparison of the same case on the two machines."""
    if not raw:
        return None
    txt = " ".join("".join(raw).split())
    m = re.search(r"R((?:\s*-?\d+)+\s*\|(?:\s*-?\d+)*)", txt)
    return re.sub(r"\s+", "", m.group(1)) if m else None


# label, program head, dump base, count, extra-print
SPRITE_CASES = [
    # --- SPRITE$ pattern writes: size, pad, truncate, index, wrap -----------
    ("pat_8_full",   "SCREEN2:SPRITE$(0)=STRING$(8,170)",      f"&H{SPR_PAT:04X}", 10, "0"),
    ("pat_8_short",  "SCREEN2:SPRITE$(1)=CHR$(255)",           f"&H{SPR_PAT+8:04X}", 10, "0"),
    ("pat_8_long",   "SCREEN2:SPRITE$(2)=STRING$(20,204)",     f"&H{SPR_PAT+16:04X}", 12, "0"),
    ("pat_8_empty",  "SCREEN2:SPRITE$(3)=STRING$(8,170):SPRITE$(3)=\"\"",
     f"&H{SPR_PAT+24:04X}", 8, "0"),
    ("pat_8_n255",   "SCREEN2:SPRITE$(255)=STRING$(8,204)",    f"&H{SPR_PAT+255*8:04X}", 8, "0"),
    ("pat_16_full",  "SCREEN2,2:SPRITE$(0)=STRING$(32,170)",   f"&H{SPR_PAT:04X}", 34, "0"),
    ("pat_16_short", "SCREEN2,2:SPRITE$(1)=STRING$(8,204)",    f"&H{SPR_PAT+32:04X}", 34, "0"),
    # n=255 in 16x16 addresses past 16 KB -> the reference WRAPS (D-G7-5)
    ("pat_16_wrap",  "SCREEN2,2:SPRITE$(255)=STRING$(32,170)", "&H17E0", 8, "0"),
    # --- SPRITE$ read-back: always the ENTRY size, never the assigned length -
    ("read_8",       "SCREEN2:SPRITE$(0)=CHR$(9):B$=SPRITE$(0)",
     f"&H{SPR_PAT:04X}", 2, ("LEN(B$)", "ASC(B$)", "ASC(MID$(B$,8,1))")),
    ("read_16",      "SCREEN2,2:SPRITE$(2)=STRING$(32,204):B$=SPRITE$(2)",
     f"&H{SPR_PAT+64:04X}", 2, ("LEN(B$)", "ASC(B$)", "ASC(MID$(B$,32,1))")),
    ("read_scr0",    "SCREEN2:SPRITE$(0)=CHR$(7):SCREEN0:B$=SPRITE$(0)",
     f"&H{SPR_PAT:04X}", 2, ("LEN(B$)", "ASC(B$)")),
    # --- PUT SPRITE attribute writes ---------------------------------------
    ("attr_full",    "SCREEN2:PUT SPRITE 0,(10,20),4,1",       f"&H{SPR_ATTR:04X}", 4, "0"),
    ("attr_plane5",  "SCREEN2:PUT SPRITE 5,(10,20),4,1",       f"&H{SPR_ATTR+20:04X}", 4, "0"),
    ("attr_neg_x",   "SCREEN2:PUT SPRITE 0,(-5,20),4,1",       f"&H{SPR_ATTR:04X}", 4, "0"),
    ("attr_neg_x32", "SCREEN2:PUT SPRITE 0,(-32,20),4,1",      f"&H{SPR_ATTR:04X}", 4, "0"),
    ("attr_ec_clear","SCREEN2:PUT SPRITE 0,(-5,20),4,1:PUT SPRITE 0,(60,20)",
     f"&H{SPR_ATTR:04X}", 4, "0"),
    ("attr_wrap_x",  "SCREEN2:PUT SPRITE 0,(300,20),4,1",      f"&H{SPR_ATTR:04X}", 4, "0"),
    ("attr_wrap_y",  "SCREEN2:PUT SPRITE 0,(10,300),4,1",      f"&H{SPR_ATTR:04X}", 4, "0"),
    ("attr_y209",    "SCREEN2:PUT SPRITE 0,(10,209),4,1",      f"&H{SPR_ATTR:04X}", 4, "0"),
    ("attr_omit_c",  "SCREEN2:PUT SPRITE 0,(70,80),9,1:PUT SPRITE 0,(30,40),,2",
     f"&H{SPR_ATTR:04X}", 4, "0"),
    ("attr_omit_p",  "SCREEN2:PUT SPRITE 0,(70,80),9,3:PUT SPRITE 0,(30,40),6",
     f"&H{SPR_ATTR:04X}", 4, "0"),
    ("attr_omit_xy", "SCREEN2:PUT SPRITE 0,(70,80),4,1:PUT SPRITE 0,,9",
     f"&H{SPR_ATTR:04X}", 4, "0"),
    ("attr_omit_all","SCREEN2:PUT SPRITE 2,(70,80),4,1:PUT SPRITE 2,,,7",
     f"&H{SPR_ATTR+8:04X}", 4, "0"),
    ("attr_step",    "SCREEN2:PSET(50,60):PUT SPRITE 0,STEP(10,20),4,1",
     f"&H{SPR_ATTR:04X}", 4, ("PEEK(&HFCB7)", "PEEK(&HFCB8)", "PEEK(&HFCB9)", "PEEK(&HFCBA)")),
    ("attr_float",   "SCREEN2:PUT SPRITE 0,(10.7,20.2),4.9,1.9", f"&H{SPR_ATTR:04X}", 4, "0"),
    ("attr_work",    "SCREEN2:PUT SPRITE 0,(-5,300),4,1", f"&H{SPR_ATTR:04X}", 4,
     # per-BYTE peeks: `PEEK+256*PEEK` of a negative coordinate exceeds int16, and
     # the two machines' expression arithmetic differs there (65531 vs -5) -- a
     # pre-existing arithmetic seam, nothing to do with the sprite statement.
     ("PEEK(&HFCB7)", "PEEK(&HFCB8)", "PEEK(&HFCB9)", "PEEK(&HFCBA)",
      "PEEK(&HFCB3)", "PEEK(&HFCB4)")),
    # 16x16: the pattern NUMBER is stored x4
    ("attr_16_pat1", "SCREEN2,2:PUT SPRITE 0,(10,20),4,1",     f"&H{SPR_ATTR:04X}", 4, "0"),
    ("attr_16_pat63","SCREEN2,2:PUT SPRITE 0,(10,20),4,63",    f"&H{SPR_ATTR:04X}", 4, "0"),
    ("attr_scr1",    "SCREEN1:PUT SPRITE 0,(10,20),4,1",       f"&H{SPR_ATTR:04X}", 4, "0"),
]


def phase_n() -> int:
    """Sprite table differential. BOOT-PER-CASE: the sprite tables live in VRAM
    and survive NEW, so a batched case would inherit the previous case's bytes --
    the exact confound that made round 2 of the characterization misread the
    omitted-argument rule (scratchpad/g7_sprite_notes.md)."""
    fails = 0
    print("=== PHASE N: sprite tables (attribute + pattern) differential ===")
    for label, head, base, n, extra in SPRITE_CASES:
        specs = [("stored", [f"CLEAR 2000:COLOR15,4,7:{head}"] + spr_dump(base, n, extra))]
        ref = omsx_repl.run_cases(REF, specs, batch=False)[0]
        zb = omsx_repl.run_cases(ZB, specs, batch=False)[0]
        ra, za = _spr_bytes(ref), _spr_bytes(zb)
        ok = ra is not None and ra == za
        fails += not ok
        print(f"  {'PASS' if ok else 'FAIL'} {label:15} ref={ra!r} zb={za!r}")
    return fails


# Both outcomes behind ONE tag (the Phase-L pattern), so an accepted<->raised
# flip cannot pass.
SPRITE_BEHAV = [
    (l, ['ON ERROR GOTO 40', body, 'SCREEN0:PRINT"ZK":END',
         'SCREEN0:PRINT"ZE";ERR:END'])
    for l, body in [
        ("spr_n256",    'SCREEN2:SPRITE$(256)=CHR$(1)'),
        ("spr_n_neg",   'SCREEN2:SPRITE$(-1)=CHR$(1)'),
        ("spr_n255",    'SCREEN2:SPRITE$(255)=CHR$(1)'),
        ("spr_numeric", 'SCREEN2:SPRITE$(0)=5'),
        ("spr_scr0_wr", 'SCREEN0:SPRITE$(0)=CHR$(1)'),
        ("spr_scr1_wr", 'SCREEN1:SPRITE$(0)=CHR$(1)'),
        ("spr_read_s0", 'SCREEN0:B$=SPRITE$(0)'),
        ("spr_read256", 'SCREEN2:B$=SPRITE$(256)'),
        ("spr_noparen", 'SCREEN2:SPRITE$0=CHR$(1)'),
        ("spr_noeq",    'SCREEN2:SPRITE$(0)'),
        ("spr_bare",    'SCREEN2:SPRITE'),
        ("spr_on",      'SCREEN2:SPRITE ON'),
        ("spr_off",     'SCREEN2:SPRITE OFF'),
        ("spr_stop",    'SCREEN2:SPRITE STOP'),
        ("spr_on_s0",   'SCREEN0:SPRITE ON'),
        ("put_plane32", 'SCREEN2:PUT SPRITE 32,(10,20),4,1'),
        ("put_plane31", 'SCREEN2:PUT SPRITE 31,(10,20),4,1'),
        ("put_planeneg",'SCREEN2:PUT SPRITE -1,(10,20),4,1'),
        ("put_col16",   'SCREEN2:PUT SPRITE 0,(10,20),16,1'),
        ("put_colneg",  'SCREEN2:PUT SPRITE 0,(10,20),-1,1'),
        ("put_pat255",  'SCREEN2:PUT SPRITE 0,(10,20),4,255'),
        ("put_pat256",  'SCREEN2:PUT SPRITE 0,(10,20),4,256'),
        ("put_pat64_16",'SCREEN2,2:PUT SPRITE 0,(10,20),4,64'),
        ("put_pat63_16",'SCREEN2,2:PUT SPRITE 0,(10,20),4,63'),
        ("put_patneg",  'SCREEN2:PUT SPRITE 0,(10,20),4,-1'),
        ("put_x40000",  'SCREEN2:PUT SPRITE 0,(40000,20),4,1'),
        ("put_x300",    'SCREEN2:PUT SPRITE 0,(300,20),4,1'),
        ("put_scr0",    'SCREEN0:PUT SPRITE 0,(10,20),4,1'),
        ("put_scr1",    'SCREEN1:PUT SPRITE 0,(10,20),4,1'),
        ("put_bare",    'SCREEN2:PUT SPRITE 0'),
        ("put_comma",   'SCREEN2:PUT SPRITE 0,'),
        ("put_5args",   'SCREEN2:PUT SPRITE 0,(10,20),4,1,9'),
        ("put_trailing",'SCREEN2:PUT SPRITE 0,(10,20),4,1,'),
        ("put_steponly",'SCREEN2:PUT SPRITE 0,STEP(10,20)'),
        ("put_halfxy",  'SCREEN2:PUT SPRITE 0,(,20),4,1'),
    ]
]


def phase_o() -> int:
    fails = 0
    print("=== PHASE O: sprite errors + accepted edges ===")
    specs = [("stored", body) for _, body in SPRITE_BEHAV]
    ref = omsx_repl.run_cases(REF, specs, batch=True, reset=("NEW", "CLS"))
    zb = omsx_repl.run_cases(ZB, specs, batch=True, reset=("NEW", "CLS"))
    for (label, _), r, z in zip(SPRITE_BEHAV, ref, zb):
        ra, za = _outcome(r), _outcome(z)
        ok = ra is not None and ra == za
        fails += not ok
        print(f"  {'PASS' if ok else 'FAIL'} {label:14} ref={ra!r} zb={za!r}")
    return fails


# label, program head, dump base, count, extra
SPRITE_STATE = [
    # mode-set init: y=209, pattern=plane, colour=FORCLR -- and x UNTOUCHED
    ("init_planes",  "COLOR15,1,1:SCREEN2:PUT SPRITE 0,(60,20),4,1:SCREEN2",
     f"&H{SPR_ATTR:04X}", 12, "PEEK(&HF3E0)"),
    ("init_forclr",  "COLOR4,1,1:SCREEN2", f"&H{SPR_ATTR:04X}", 8, "PEEK(&HF3E0)"),
    ("init_p31",     "COLOR15,1,1:SCREEN2", f"&H{SPR_ATTR+124:04X}", 4, "0"),
    ("cls_keeps",    "SCREEN2:PUT SPRITE 0,(60,20),4,1:SPRITE$(0)=CHR$(170):CLS",
     f"&H{SPR_ATTR:04X}", 4, "VPEEK(&H3800)"),
    ("pat_survives", "SCREEN2:SPRITE$(0)=CHR$(170):SCREEN2", f"&H{SPR_PAT:04X}", 4, "0"),
    # the sprite-size argument persists across a later bare SCREEN
    ("size_persist", "SCREEN2,2:SCREEN2:SPRITE$(0)=CHR$(9):B$=SPRITE$(0)",
     f"&H{SPR_PAT:04X}", 2, ("LEN(B$)", "PEEK(&HF3E0)")),
    ("size_persist0","SCREEN2,2:SCREEN0:SCREEN2:B$=SPRITE$(0)",
     f"&H{SPR_PAT:04X}", 2, ("LEN(B$)", "PEEK(&HF3E0)")),
    ("size_back",    "SCREEN2,2:SCREEN2,0:B$=SPRITE$(0)",
     f"&H{SPR_PAT:04X}", 2, ("LEN(B$)", "PEEK(&HF3E0)")),
    ("size_mag",     "SCREEN2,1:B$=SPRITE$(0)", f"&H{SPR_PAT:04X}", 2,
     ("LEN(B$)", "PEEK(&HF3E0)")),
    ("size_mag3",    "SCREEN2,3:B$=SPRITE$(0)", f"&H{SPR_PAT:04X}", 2,
     ("LEN(B$)", "PEEK(&HF3E0)")),
]


def phase_p() -> int:
    """Mode-set init + persistence -- the parts no single statement can show.
    Boot-per-case for the same VRAM-carry-over reason as Phase N."""
    fails = 0
    print("=== PHASE P: sprite table init, CLS, and the persistent size ===")
    for label, head, base, n, extra in SPRITE_STATE:
        specs = [("stored", [f"CLEAR 2000:{head}"] + spr_dump(base, n, extra))]
        ref = omsx_repl.run_cases(REF, specs, batch=False)[0]
        zb = omsx_repl.run_cases(ZB, specs, batch=False)[0]
        ra, za = _spr_bytes(ref), _spr_bytes(zb)
        ok = ra is not None and ra == za
        fails += not ok
        print(f"  {'PASS' if ok else 'FAIL'} {label:14} ref={ra!r} zb={za!r}")
    return fails


# ===========================================================================
# PHASE Q -- G8: VDP(n) / BASE(n) (docs/spec-basic-graphics-g8.md §7)
# ===========================================================================
BASETAB, RGSAV, SCRMOD_ADDR, G8_RES = 0xF3B3, 0xF3DF, 0xFCAF, 0xD100
G8_CAP = ("mem_abs", [(BASETAB, 40), (RGSAV, 9), (SCRMOD_ADDR, 1), (G8_RES, 1)])

# R7 is DELIBERATELY excluded from every register assertion: C-BIOS programs it
# (and, in SCREEN 0, R3/R5/R6) differently from the reference BIOS, a difference
# that sits BELOW the BASIC statement -- documented as G8-regdelta (spec §7).
# Wherever G8 reprograms, it writes ALL of R0..R6 from the (identical) table, so
# those seven ARE comparable; where it does not reprogram, only the table is.
def _g8_state(raw: str | None):
    if not raw:
        return None
    b = bytes.fromhex(raw)
    if b[50] != 7:                      # the case never reached its hold loop
        return None
    return ([b[2 * i] | (b[2 * i + 1] << 8) for i in range(20)], list(b[40:47]))


def _g8_prog(lines: list[str]):
    body = list(lines) + [f"POKE&H{G8_RES:04X},7"]
    return ("stored", body + [f"GOTO {(len(body) + 1) * 10}"])


# label, program lines, assert-registers-too?
G8_STATE = [
    # the plain single-mode reprogram (SCREEN 0 writes its own group)
    ("s0_name",    ["SCREEN0", "BASE(0)=&H0400"], True),
    ("s0_satr",    ["SCREEN0", "BASE(3)=&H1F00"], True),
    ("s0_spat",    ["SCREEN0", "BASE(4)=&H3000"], True),
    # THE off-by-one: SCREEN 1 programs from group 2, SCREEN 2 from group 3
    ("s1_name",    ["SCREEN1", "BASE(5)=&H0400"], True),
    ("s1_satr",    ["SCREEN1", "BASE(8)=&H1F00"], True),
    ("s2_name",    ["SCREEN2", "BASE(10)=&H1C00"], True),
    ("s2_satr",    ["SCREEN2", "BASE(13)=&H1F00"], True),
    ("s2_spat",    ["SCREEN2", "BASE(14)=&H3000"], True),
    # ...and it reads the OTHER group's words, not the written slot's
    ("s1_poison",  ["SCREEN0", "BASE(13)=&H0400", "SCREEN1", "BASE(8)=&H1F00"], True),
    ("s2_poison",  ["SCREEN0", "BASE(18)=&H0400", "SCREEN2", "BASE(13)=&H1F00"], True),
    ("s2_poison2", ["SCREEN0", "BASE(19)=&H1000", "SCREEN2", "BASE(14)=&H3000"], True),
    # the reprogram is WIDE: a register poked out of sync snaps back to the table
    ("s0_desync",  ["SCREEN0", "VDP(2)=5", "VDP(6)=5", "BASE(3)=&H1F00"], True),
    ("s2_desync",  ["SCREEN2", "VDP(2)=5", "VDP(6)=5", "BASE(13)=&H1F00"], True),
    # R1's non-mode bits survive (a SCREEN 2,1 sprite size in particular)
    ("s2_size",    ["SCREEN2,1", "BASE(13)=&H1F00"], True),
    ("s2_r1poke",  ["SCREEN2", "VDP(1)=&HE2", "BASE(13)=&H1F00"], True),
    # cross-group: the word is stored and NOTHING is programmed. Registers are
    # NOT compared here -- they still hold each BIOS's own mode-set values.
    ("x_s0_g2",    ["SCREEN0", "BASE(10)=&H1C00"], False),
    ("x_s2_g1",    ["SCREEN2", "BASE(5)=&H1C00"], False),
    ("x_s2_g3",    ["SCREEN2", "BASE(15)=&H0C00"], False),
    # a plain VDP register write reaches the mirror (the chip half is Q4)
    ("vdp_r7",     ["SCREEN2", "VDP(7)=&H4F"], True),
    ("vdp_r2",     ["SCREEN2", "VDP(2)=7"], True),
]


def phase_q_state() -> int:
    """Boot-per-case: each case holds its screen mode in a GOTO-self loop (a
    BASE write moves the name table, so the SCREEN-0 text scrape is useless
    here and the state is read from memory instead)."""
    fails = 0
    print("=== PHASE Q1: VDP/BASE state differential (table + R0..R6) ===")
    for label, lines, with_regs in G8_STATE:
        specs = [_g8_prog(lines)]
        r = _g8_state(omsx_repl.run_cases(REF, specs, batch=False,
                                          capture=G8_CAP, step=6.0)[0])
        z = _g8_state(omsx_repl.run_cases(ZB, specs, batch=False,
                                          capture=G8_CAP, step=6.0)[0])
        if r is None or z is None:
            ok, detail = False, f"ref={r is not None} zb={z is not None} (no capture)"
        elif with_regs:
            ok = r == z
            detail = f"regs ref={['%02x' % v for v in r[1]]} zb={['%02x' % v for v in z[1]]}"
        else:
            ok = r[0] == z[0]
            detail = "table-only (cross-group: no reprogram)"
        fails += not ok
        print(f"  {'PASS' if ok else 'FAIL'} {label:11} {detail}")
    return fails


# Behavioural cases, both outcomes behind one tag (the Phase-L/O pattern), so an
# accepted<->raised flip cannot pass. Grammar + domains from spec §3/§4.
#
# Every case that SUCCEEDS in writing a BASE word puts the default back before it
# prints: this phase batches, and a moved name table wrecks the SCREEN-0 scrape
# for every case AFTER it (which is exactly how the first run of this phase read
# as 34 spurious failures, on both machines at once).
G8_BEHAV = [
    (l, ['ON ERROR GOTO 40', body, 'SCREEN0:PRINT"ZK";A:END',
         'SCREEN0:PRINT"ZE";ERR:END'])
    for l, body in [
        # reads
        ("rd_vdp1",     'SCREEN2:VDP(1)=&HE2:A=VDP(1)'),
        ("rd_vdp8",     'SCREEN2:VDP(0)=2:A=VDP(8)-VDP(8)'),
        ("rd_vdp9",     'SCREEN2:A=VDP(9)'),
        ("rd_vdpneg",   'SCREEN2:A=VDP(-1)'),
        ("rd_vdp256",   'SCREEN2:A=VDP(256)'),
        ("rd_vdpfrac",  'SCREEN2:VDP(1)=&HE2:A=VDP(1.7)'),
        ("rd_vdpnegfr", 'SCREEN2:VDP(0)=3:A=VDP(-0.4)'),
        ("rd_base0",    'SCREEN2:A=BASE(0)'),
        ("rd_base10",   'SCREEN2:A=BASE(10)'),
        ("rd_base19",   'SCREEN2:A=BASE(19)'),
        ("rd_base20",   'SCREEN2:A=BASE(20)'),
        ("rd_baseneg",  'SCREEN2:A=BASE(-1)'),
        ("rd_base_s0",  'SCREEN0:A=BASE(10)'),
        ("rd_bare",     'SCREEN2:A=VDP'),
        ("rd_nopar",    'SCREEN2:A=VDP 0'),
        # write domains
        ("wr_vdp8",     'SCREEN2:VDP(8)=1'),
        ("wr_vdpneg",   'SCREEN2:VDP(-1)=1'),
        ("wr_vdp9",     'SCREEN2:VDP(9)=1'),
        ("wr_v256",     'SCREEN2:VDP(1)=256'),
        ("wr_vneg",     'SCREEN2:VDP(1)=-1'),
        ("wr_vfrac",    'SCREEN2:VDP(0)=2.7:A=VDP(0)'),
        ("wr_vnegfrac", 'SCREEN2:VDP(0)=-0.4:A=VDP(0)'),
        ("wr_v255fr",   'SCREEN2:VDP(0)=255.6:A=VDP(0)'),
        # BASE value grain, per slot kind, incl. the group-2 exception
        ("b_name_ok",   'SCREEN0:BASE(0)=&H0400:A=BASE(0):BASE(0)=0'),
        ("b_name_odd",  'SCREEN0:BASE(0)=&H0401'),
        ("b_name_80",   'SCREEN0:BASE(0)=&H0080'),
        ("b_colr_80",   'SCREEN0:BASE(1)=&H0080:A=BASE(1):BASE(1)=0'),
        ("b_colr_g2",   'SCREEN0:BASE(11)=&H0400'),
        ("b_colr_g2ok", 'SCREEN0:BASE(11)=&H2000:A=BASE(11):BASE(11)=&H2000'),
        ("b_patt_g2",   'SCREEN0:BASE(12)=&H0800'),
        ("b_patt_g1",   'SCREEN0:BASE(7)=&H0800:A=BASE(7):BASE(7)=0'),
        ("b_satr_80",   'SCREEN0:BASE(13)=&H0080:A=BASE(13):BASE(13)=&H1B00'),
        ("b_spat_400",  'SCREEN0:BASE(14)=&H0400'),
        ("b_spat_800",  'SCREEN0:BASE(14)=&H0800:A=BASE(14):BASE(14)=&H3800'),
        ("b_big",       'SCREEN0:BASE(10)=&H4000'),
        ("b_top",       'SCREEN0:BASE(10)=&H3800:A=BASE(10):BASE(10)=&H1800'),
        ("b_neg",       'SCREEN0:BASE(10)=-1'),
        ("b_n20",       'SCREEN0:BASE(20)=0'),
        ("b_nneg",      'SCREEN0:BASE(-1)=0'),
        # grammar
        ("g_let_vdp",   'SCREEN2:LET VDP(0)=2'),
        ("g_let_base",  'SCREEN2:LET BASE(0)=&H0400'),
        ("g_bare_stmt", 'SCREEN2:VDP(0)'),
        ("g_name_eq",   'SCREEN2:VDP=1'),
        ("g_base_eq",   'SCREEN2:BASE=1'),
        ("g_no_rhs",    'SCREEN2:VDP(0)='),
        ("g_no_paren",  'SCREEN2:VDP 0=1'),
        ("g_two_args",  'SCREEN2:VDP(0,1)=2'),
        ("g_list_rhs",  'SCREEN2:VDP(0)=1,2'),
        ("g_self",      'SCREEN2:VDP(0)=2:VDP(0)=VDP(0):A=VDP(0)'),
        ("g_base_self", 'SCREEN2:BASE(0)=BASE(0):A=BASE(0)'),
        ("g_str_val",   'SCREEN2:VDP(0)="A"'),
        ("g_str_idx",   'SCREEN2:VDP("A")=1'),
        ("g_str_base",  'SCREEN2:BASE(0)="A"'),
        # `FOR VDP(0)=0 TO 1` and `SWAP VDP(0),A` are ERR 2 on the reference and
        # are silently ACCEPTED here -- but that is NOT a G8 property: `FOR 1=0 TO
        # 1` and `SWAP 1,A` behave the same way, so it is a general FOR/SWAP
        # lvalue-validation gap (spec §7, G8-trapclass). Asserting it in this
        # phase would only lock in the wrong behaviour, so it is documented, not
        # gated.
        ("g_mid_stmt",  'SCREEN2:A=1:VDP(0)=2:B=3:A=VDP(0)'),
        ("g_if_stmt",   'SCREEN2:IF 1 THEN VDP(0)=2:A=VDP(0)'),
    ]
]


def phase_q_behav() -> int:
    fails = 0
    print("=== PHASE Q2: VDP/BASE reads, domains, grammar ===")
    specs = [("stored", body) for _, body in G8_BEHAV]
    ref = omsx_repl.run_cases(REF, specs, batch=True, reset=("NEW", "CLS"))
    zb = omsx_repl.run_cases(ZB, specs, batch=True, reset=("NEW", "CLS"))
    for (label, _), r, z in zip(G8_BEHAV, ref, zb):
        ra, za = _outcome(r), _outcome(z)
        ok = ra is not None and ra == za
        fails += not ok
        print(f"  {'PASS' if ok else 'FAIL'} {label:12} ref={ra!r} zb={za!r}")
    return fails


def phase_q_teeth() -> int:
    """THE TEETH. Everything above passes on an implementation that updates only
    the RAM mirrors and never touches the chip -- reads come back from the very
    cells the write filled. So: clear R1's interrupt-enable bit and watch TIME.
    Frozen (delta 0) means the VDP itself saw the write; still ticking means the
    write went nowhere. The control case must tick on the same machine, or a
    hung/idle emulator would read as a pass."""
    fails = 0
    print("=== PHASE Q3: does VDP(n)= reach the CHIP? (TIME freeze) ===")
    cases = [("ie_off", "VDP(1)=VDP(1)AND223"), ("control", "A=0")]
    jiffy = "(PEEK(&HFC9E)+256*PEEK(&HFC9F))"
    specs = [("stored", [
        f"POKE&H{G8_RES:04X},255",
        f"SCREEN0:{stmt}",
        f"T={jiffy}:FORI=1TO800:NEXT:D={jiffy}-T",
        "VDP(1)=VDP(1)OR32",
        f"POKE&H{G8_RES+1:04X},D-INT(D/256)*256:POKE&H{G8_RES:04X},0:END",
    ]) for _, stmt in cases]
    for mach in (REF, ZB):
        outs = omsx_repl.run_cases(mach, specs, batch=False,
                                   capture=("mem_abs", [(G8_RES, 3)]), step=25.0)
        for (label, stmt), o in zip(cases, outs):
            b = bytes.fromhex(o) if o else None
            delta = None if b is None or b[0] != 0 else b[1]
            want_zero = label == "ie_off"
            ok = delta is not None and ((delta == 0) if want_zero else (delta > 0))
            fails += not ok
            print(f"  {'PASS' if ok else 'FAIL'} {mach.split('_')[0]:8} {label:8} "
                  f"JIFFY delta={delta}")
    return fails


def main() -> int:
    fails = (phase_a() + phase_b() + phase_c() + phase_d()
              + phase_e() + phase_f() + phase_g_rneg()
              + phase_h() + phase_i_aliasing() + phase_j()
              + phase_k() + phase_l() + phase_m()
              + phase_n() + phase_o() + phase_p()
              + phase_q_state() + phase_q_behav() + phase_q_teeth())
    print("-------------------")
    print("graphics-acceptance:", "PASS" if fails == 0 else f"FAIL ({fails})")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
