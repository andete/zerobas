#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-DRAWCLAMP part A -- THE WORK AREA AFTER AN OFF-SCREEN LINE, read DIRECTLY.

D-SPOKELINE filed this as "unmeasured, a LINE STEP pair row would say". It does
not need a plane at all: GRPACX/GRPACY ($FCB7/$FCB9) and GXPOS/GYPOS ($FCB3/
$FCB5) are PEEKable published work-area cells, so one PRINT per case reads the
answer as a NUMBER instead of inferring it from a rasterised second segment.

Two hypotheses per row:

    raw      -- the cells keep the coordinate as typed  (zerobas today: the
                gfx_line_op writes are ABOVE the gfx_clamp_coords call)
    clamped  -- the cells keep the screen-clamped coordinate

⚠️ PRIOR, not proof: D-PAINTSEED measured `PAINT(300,100)` leaving BOTH cell
pairs on the RAW (300,100) on both references (basic/graphics.asm ~line 607).
PAINT *refuses* its seed though -- it never reaches a rasteriser -- so it says
nothing about the cells after a LINE that actually clamps and draws.

Rows carry a SECOND instrument (`PSET STEP` / `LINE STEP` read back) because the
direct PEEK and the STEP resolution are different readers of the same cell, and
D-GIRDOM's lesson is that a control is honest only about the cell it reads.

    python3 -u scratchpad/drawclamp_wa.py [--dry]
"""
from __future__ import annotations

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))

W, H = 256, 192


def u16(v: int) -> int:
    return v & 0xFFFF


def clamp_pt(x: int, y: int) -> tuple[int, int]:
    return (min(max(x, 0), W - 1), min(max(y, 0), H - 1))


# --- the readout tails -----------------------------------------------------
# GRPACX=$FCB7/8, GRPACY=$FCB9/A (the LAST-REFERENCED point -- STEP's base)
# GXPOS =$FCB3/4, GYPOS =$FCB5/6 (the pending-target cells)
RD_BOTH = ('SCREEN0:PRINT"W";PEEK(&HFCB7)+256*PEEK(&HFCB8);'
           'PEEK(&HFCB9)+256*PEEK(&HFCBA);'
           'PEEK(&HFCB3)+256*PEEK(&HFCB4);'
           'PEEK(&HFCB5)+256*PEEK(&HFCB6)')


def rd_step(dx: int, dy: int) -> str:
    """SECOND INSTRUMENT: resolve a STEP against the cell, then read the
    RESOLVED point back. PSET STEP writes GRPAC/GXPOS = the resolved coord
    (basic/graphics.asm ex_pset), so this reports base+(dx,dy) -- but note it
    reports the coordinate PSET *stored*, so it is only honest where the
    resolved point is itself on screen."""
    return f'PSET STEP({dx},{dy}):' + RD_BOTH


# label, ops (before the readout), readout tail, (grpac,gxpos) predicate, why
#
# pred(mode) -> (grpacx, grpacy, gxposx, gyposy) as the PEEK would report them.
def case(label, ops, tail, pred, why):
    return (label, ops, tail, pred, why)


def line_pred(p2, mode, gx=None):
    """A LINE writes both cell pairs = p2 (spec G3 §11.5). `gx` overrides the
    GXPOS pair where the statement is known to differ."""
    x, y = p2
    if mode == "clamped":
        x, y = clamp_pt(x, y)
    g = (u16(x), u16(y))
    return g + (g if gx is None else gx)


CASES = [
    case("dead_noline", "", RD_BOTH,
         lambda m: None,
         "DEAD SUBJECT: no LINE, no DRAW, no PSET -- what does a boot report? "
         "Both hypotheses are silent here; a row that ANSWERS is the rig "
         "telling us the cells are already non-zero before any statement."),

    case("ctl_line_on", "LINE(10,20)-(100,80)", RD_BOTH,
         lambda m: line_pred((100, 80), m),
         "GREEN CONTROL: p2 fully on screen, raw == clamped. VACUOUS by "
         "construction -- it proves the instrument reads a LINE at all."),

    case("line_off_r", "LINE(0,0)-(300,100)", RD_BOTH,
         lambda m: line_pred((300, 100), m),
         "⭐ p2 off the RIGHT edge only. raw 300 vs clamped 255."),

    case("line_off_b", "LINE(0,0)-(100,250)", RD_BOTH,
         lambda m: line_pred((100, 250), m),
         "⭐ p2 off the BOTTOM edge only. raw 250 vs clamped 191."),

    case("line_off_both", "LINE(0,0)-(300,250)", RD_BOTH,
         lambda m: line_pred((300, 250), m),
         "⭐ the residual's own row: p2 off BOTH edges."),

    case("line_off_neg", "LINE(100,100)-(-50,-30)", RD_BOTH,
         lambda m: line_pred((-50, -30), m),
         "⭐ p2 NEGATIVE: raw reads back as 65486/65506, clamped as 0/0. The "
         "loudest possible separation -- five digits vs one."),

    case("line_alloff", "LINE(300,300)-(400,400)", RD_BOTH,
         lambda m: line_pred((400, 400), m),
         "⭐ the FULLY off-screen LINE (the one that lights (255,191) on a "
         "VG-8020). raw 400/400 vs clamped 255/191."),

    case("line_p1_off", "LINE(-50,-30)-(100,100)", RD_BOTH,
         lambda m: line_pred((100, 100), m),
         "CONTROL: p1 off screen, p2 on. Both hypotheses say 100/100 -- so a "
         "DIFF here means the cells take p1 or a clamp artefact, not p2."),

    case("box_off", "LINE(0,0)-(300,250),,B", RD_BOTH,
         lambda m: line_pred((300, 250), m),
         "the BOX arm of the same op -- does the outline path write the same "
         "cells with the same rawness?"),

    case("boxf_off", "LINE(0,0)-(300,250),,BF", RD_BOTH,
         lambda m: line_pred((300, 250), m),
         "the FILL arm."),

    case("step_after_off", "LINE(0,0)-(300,250)", rd_step(-100, -100),
         lambda m: (lambda b: line_pred(b, "raw"))(
             tuple(a + d for a, d in zip(
                 clamp_pt(300, 250) if m == "clamped" else (300, 250),
                 (-100, -100)))),
         "⭐ SECOND INSTRUMENT: STEP(-100,-100) resolves against the cell and "
         "PSET stores the resolved point. raw -> (200,150); clamped -> "
         "(155,91). Both land ON SCREEN, so PSET's own range gate cannot "
         "confound the reading."),

    case("draw_bm_off", 'PSET(10,10):DRAW"A0S4BM300,250"', RD_BOTH,
         lambda m: (lambda c: (u16(c[0]), u16(c[1]), 10, 10))(
             clamp_pt(300, 250) if m == "clamped" else (300, 250)),
         "⭐ DRAW's CURSOR after a BLANK absolute move off both edges. GXPOS "
         "must stay on the PSET's (10,10): a B move does not touch it "
         "(measured, G6)."),

    case("draw_m_off", 'PSET(10,10):DRAW"A0S4M300,250"', RD_BOTH,
         lambda m: (lambda c: (u16(c[0]), u16(c[1]), u16(c[0]), u16(c[1])))(
             clamp_pt(300, 250) if m == "clamped" else (300, 250)),
         "⭐ DRAW's cursor after a DRAWN absolute move off both edges. GXPOS "
         "follows gdrw_gxpos: target.y >= start.y here, so the target wins."),

    case("draw_step_after", 'PSET(10,10):DRAW"A0S4BM300,250"', rd_step(-100, -100),
         lambda m: (lambda b: line_pred(b, "raw"))(
             tuple(a + d for a, d in zip(
                 clamp_pt(300, 250) if m == "clamped" else (300, 250),
                 (-100, -100)))),
         "SECOND INSTRUMENT on DRAW's cursor."),
]

MODES = ("raw", "clamped")


def fmt(p):
    return "W " + " ".join(str(v) for v in p) if p else None


def main() -> int:
    print("=== D-DRAWCLAMP part A: the work area after an off-screen LINE ===")
    print("    raw     = cells keep the coordinate as typed (zerobas today)")
    print("    clamped = cells keep the screen-clamped coordinate\n")
    preds = {}
    for label, ops, tail, pred, why in CASES:
        p = {m: fmt(pred(m)) for m in MODES}
        preds[label] = p
        distinct = len(set(p.values()))
        print(f"  {label:16} {ops or '(nothing)'}")
        for m in MODES:
            print(f"      {m:8} {p[m]}")
        print(f"      DISCRIMINATING POWER: {distinct}"
              f"{'  ⚠️ VACUOUS' if distinct == 1 else ''}")
        print(f"      why: {why}")
    live = sum(len(set(preds[c[0]].values())) > 1 for c in CASES)
    print(f"\n  rows that can discriminate: {live} of {len(CASES)}")
    if "--dry" in sys.argv:
        return 0

    import omsx_repl  # noqa: E402
    REF = os.environ.get("ZEROBAS_REF_MACHINE", "Philips_VG_8020")
    ZB = os.environ.get("ZEROBAS_SUBROM_INTTEST_MACHINE",
                        "C-BIOS_MSX1_EU_REPACK_DISK")

    specs = [("stored", ["SCREEN2" + (":" + ops if ops else ""), tail])
             for _, ops, tail, _, _ in CASES]

    def answer(raw):
        if not raw:
            return None
        txt = " ".join("".join(raw).split())
        m = re.search(r"W[ \d\-]*", txt)
        return re.sub(r"\s+", " ", m.group(0)).strip() if m else None

    # ⚠️ RIG: round 1 ran batch=True/step=2.5 and zerobas returned None for
    # `boxf_off` and EVERY case after it -- the full-screen BF fill (the clamped
    # box is the WHOLE screen) outran the step budget and desynchronised the
    # rest of the batch. That is a ONE-SIDED RIG FAILURE, not a finding. Both
    # machines are re-run with the SAME settings; never a batched reference
    # against an unbatched zerobas.
    slow = "--slow" in sys.argv
    kw = (dict(batch=False, step=20.0) if slow
          else dict(batch=True, reset=("NEW", "CLS"), step=12.0))
    print(f"\n--- MEASURED  ref={REF}  zb={ZB}  ({kw}) ---")
    ref = omsx_repl.run_cases(REF, specs, **kw)
    zb = omsx_repl.run_cases(ZB, specs, **kw)
    bad = 0
    for (label, ops, tail, _, _), r, z in zip(CASES, ref, zb):
        ra, za = answer(r), answer(z)
        names = [m for m in MODES if preds[label][m] == ra]
        agree = "agree" if ra == za else "DIFF "
        bad += ra != za
        print(f"  {agree} {label:16} ref={ra!r}")
        print(f"        zb   ={za!r}   ref matches: {names or 'NONE'}")
    print(f"\n=== rows where the machines DIFFER: {bad} ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
