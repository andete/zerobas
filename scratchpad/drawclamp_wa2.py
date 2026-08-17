#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-DRAWCLAMP part A round 2 -- WHAT GOES IN GXPOS/GYPOS, and it is NOT raw.

Round 1 settled the filed residual (GRPACX/GRPACY keep the RAW p2 on both
machines, every row agreeing) and then found something NOBODY PREDICTED, in
two rows written as ordinary coverage:

    draw_m_off  PSET(10,10):DRAW"A0S4M300,250"     ref W 300 250 255 191
                                                   zb  W 300 250 300 250
    boxf_off    LINE(0,0)-(300,250),,BF            ref W 300 250 255 191
                                                   zb  (unmeasured -- the
                                                        full-screen fill outran
                                                        even a 20 s step)

GRPAC keeps the raw p2 in BOTH; the PENDING-TARGET pair GXPOS/GYPOS does not.
On the reference it holds a CLAMPED coordinate after a drawn DRAW move and
after a BF fill -- while plain LINE and the B outline leave it raw. zerobas
writes raw everywhere.

🔴 I PREDICTED raw/raw FOR draw_m_off. That is a VALUE-LEVEL MISS inside a row
set whose SHAPE was right, which is exactly the failure mode this project keeps
re-learning: the row was designed to confirm G6's `gdrw_gxpos` rule and instead
refuted it.

Four hypotheses for the DRAW residue (G6's measured rule is `raw_greatery`):

    raw_greatery      the endpoint with the greater y, ties to the target, RAW
    clamp_greatery    ...the same endpoint, CLAMPED
    clamp_target      always the clamped target
    last_plotted      the last pixel the rasteriser actually plots (endpoints
                      clamped, then the major-ascending sort decides which end
                      comes last)

`draw_m_off` alone cannot separate the last three -- they coincide on it. The
rows below are built so each pair comes apart somewhere.

    python3 -u scratchpad/drawclamp_wa2.py [--dry]
"""
from __future__ import annotations

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))

W, H = 256, 192


def u16(v):
    return v & 0xFFFF


def clamp_pt(x, y):
    return (min(max(x, 0), W - 1), min(max(y, 0), H - 1))


def last_plotted(x1, y1, x2, y2):
    """gfx_bres_init sorts so the MAJOR axis ascends, so the last pixel plotted
    is the clamped endpoint with the greater major coordinate."""
    a, b = clamp_pt(x1, y1), clamp_pt(x2, y2)
    if abs(b[1] - a[1]) > abs(b[0] - a[0]):
        return max(a, b, key=lambda p: p[1])
    return max(a, b, key=lambda p: p[0])


def greatery(x1, y1, x2, y2):
    """G6's measured rule: the endpoint with the greater y, ties to the TARGET."""
    return (x2, y2) if y2 >= y1 else (x1, y1)


DRAW_HYPS = ("raw_greatery", "clamp_greatery", "clamp_target", "last_plotted")


def draw_pred(start, target, h):
    if h == "raw_greatery":
        p = greatery(*start, *target)
    elif h == "clamp_greatery":
        p = clamp_pt(*greatery(*start, *target))
    elif h == "clamp_target":
        p = clamp_pt(*target)
    else:
        p = last_plotted(*start, *target)
    return (u16(p[0]), u16(p[1]))


# BF: p2 raw, p2 clamped, or the clamped box's BOTTOM-RIGHT (the last row the
# fill paints) -- which differs from the clamped p2 whenever p2 is the box's
# TOP-LEFT corner.
BF_HYPS = ("raw_p2", "clamp_p2", "clamp_botright")


def bf_pred(p1, p2, h):
    if h == "raw_p2":
        p = p2
    elif h == "clamp_p2":
        p = clamp_pt(*p2)
    else:
        a, b = clamp_pt(*p1), clamp_pt(*p2)
        p = (max(a[0], b[0]), max(a[1], b[1]))
    return (u16(p[0]), u16(p[1]))


RD = ('SCREEN0:PRINT"W";PEEK(&HFCB7)+256*PEEK(&HFCB8);'
      'PEEK(&HFCB9)+256*PEEK(&HFCBA);'
      'PEEK(&HFCB3)+256*PEEK(&HFCB4);'
      'PEEK(&HFCB5)+256*PEEK(&HFCB6)')

# label, ops, grpac (raw, known from round 1), hyp family, args, why
CASES = [
    ("ctl_dead", "", None, None, None,
     "⭐ DEAD SUBJECT: no statement at all. Round 1 read W 0 0 0 0."),

    ("ctl_draw_on", 'PSET(10,10):DRAW"A0S4M100,80"', (100, 80), "draw",
     ((10, 10), (100, 80)),
     "GREEN CONTROL: fully on screen -- all four DRAW hypotheses coincide."),

    ("draw_m_off", 'PSET(10,10):DRAW"A0S4M300,250"', (300, 250), "draw",
     ((10, 10), (300, 250)),
     "ROUND 1's ROW, repeated verbatim as the anchor: ref said 255 191. It "
     "kills raw_greatery and cannot separate the other three."),

    ("draw_up_off", 'PSET(100,150):DRAW"A0S4M300,-50"', (300, 65486), "draw",
     ((100, 150), (300, -50)),
     "⭐ the target is ABOVE the start, so the greater-y endpoint is the START "
     "(100,150) -- on screen, hence clamp-proof. clamp_target/last_plotted say "
     "(255,0). Separates {raw,clamp}_greatery from {clamp_target,last_plotted}."),

    ("draw_left_down", 'PSET(200,100):DRAW"A0S4M-300,+150"', (65436, 250), "draw",
     ((200, 100), (-100, 250)),
     "⭐ x-major going LEFT and DOWN: the greater-y endpoint is the target "
     "(clamped (0,191)), but the LAST PLOTTED pixel is the greater-x end, "
     "(200,100). Separates clamp_target from last_plotted."),

    ("draw_blank_off", 'PSET(10,10):DRAW"A0S4BM300,250"', (300, 250), None, None,
     "CONTROL: a BLANK move draws nothing, so GXPOS must stay on the PSET's "
     "(10,10) under every hypothesis (round 1 agreed: W 300 250 10 10)."),

    ("bf_small_off", "LINE(200,150)-(300,250),,BF", (300, 250), "bf",
     ((200, 150), (300, 250)),
     "⭐ BF with p2 off both edges, but the CLAMPED box is only 56x42 so the "
     "fill is cheap -- round 1's full-screen BF outran a 20 s step on zerobas "
     "and returned None. clamp_p2 == clamp_botright here."),

    ("bf_p2_topleft", "LINE(200,150)-(-30,-20),,BF", (65506, 65516), "bf",
     ((200, 150), (-30, -20)),
     "⭐ p2 is the box's TOP-LEFT: clamp_p2 says (0,0) while clamp_botright "
     "says (200,150). The row that separates 'the clamped p2' from 'the last "
     "pixel the fill painted'."),

    ("bf_ctl_on", "LINE(20,20)-(60,60),,BF", (60, 60), "bf",
     ((20, 20), (60, 60)),
     "GREEN CONTROL: BF fully on screen -- all three BF hypotheses coincide."),

    ("box_off", "LINE(0,0)-(300,250),,B", (300, 250), "bf",
     ((0, 0), (300, 250)),
     "the OUTLINE arm, repeated: round 1 read raw 300 250 on the reference, "
     "unlike its own BF sibling. Scored against the BF hypotheses to make that "
     "asymmetry explicit rather than assumed."),
]


def preds_for(label, grpac, fam, args):
    if fam is None:
        return {}
    hyps = DRAW_HYPS if fam == "draw" else BF_HYPS
    f = draw_pred if fam == "draw" else bf_pred
    return {h: f(args[0], args[1], h) for h in hyps}


def main() -> int:
    print("=== D-DRAWCLAMP part A round 2: what goes in GXPOS/GYPOS ===\n")
    allp = {}
    live = 0
    for label, ops, grpac, fam, args, why in CASES:
        p = preds_for(label, grpac, fam, args)
        allp[label] = (grpac, p)
        print(f"  {label:16} {ops or '(nothing)'}")
        if grpac:
            print(f"      GRPAC (raw p2, round 1): {u16(grpac[0])} {u16(grpac[1])}")
        for h, v in p.items():
            print(f"      GXPOS {h:16} {v[0]} {v[1]}")
        d = len(set(p.values()))
        live += d > 1
        print(f"      DISCRIMINATING POWER: {d}"
              f"{'  ⚠️ VACUOUS' if d <= 1 else ''}")
        print(f"      why: {why}")
    print(f"\n  rows that can discriminate: {live} of {len(CASES)}")
    if "--dry" in sys.argv:
        return 0

    import omsx_repl  # noqa: E402
    REF = os.environ.get("ZEROBAS_REF_MACHINE", "Philips_VG_8020")
    ZB = os.environ.get("ZEROBAS_SUBROM_INTTEST_MACHINE",
                        "C-BIOS_MSX1_EU_REPACK_DISK")
    specs = [("stored", ["SCREEN2" + (":" + ops if ops else ""), RD])
             for _, ops, _, _, _, _ in CASES]

    def answer(raw):
        if not raw:
            return None
        txt = " ".join("".join(raw).split())
        m = re.search(r"W[ \d\-]*", txt)
        return re.sub(r"\s+", " ", m.group(0)).strip() if m else None

    print(f"\n--- MEASURED  ref={REF}  zb={ZB} (boot-per-case, step 30) ---")
    ref = omsx_repl.run_cases(REF, specs, batch=False, step=30.0)
    zb = omsx_repl.run_cases(ZB, specs, batch=False, step=30.0)
    bad = 0
    for (label, ops, grpac, fam, args, why), r, z in zip(CASES, ref, zb):
        ra, za = answer(r), answer(z)
        grpac_p = p = allp[label][1]
        names = []
        if ra:
            got = ra.split()[3:5] if len(ra.split()) >= 5 else None
            names = [h for h, v in p.items()
                     if got and [str(v[0]), str(v[1])] == got]
        bad += ra != za
        print(f"  {'agree' if ra == za else 'DIFF '} {label:16} ref={ra!r}")
        print(f"        zb   ={za!r}   GXPOS matches: {names or 'NONE'}")
    print(f"\n=== rows where the machines DIFFER: {bad} ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
