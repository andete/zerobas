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


def main() -> int:
    fails = (phase_a() + phase_b() + phase_c() + phase_d()
              + phase_e() + phase_f() + phase_g_rneg())
    print("-------------------")
    print("graphics-acceptance:", "PASS" if fails == 0 else f"FAIL ({fails})")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
