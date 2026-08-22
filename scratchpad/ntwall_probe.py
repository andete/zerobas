#!/usr/bin/env python3
"""D-NTWALL scout — WHERE along the wall does the "border eaten" cascade stop?

`TODO.md` (filed 2026-08-22 by D-PAINTMC §7, row `nt2.wall`):

    SCREEN 2 : LINE(0,20)-(103,20),7 : LINE(108,20)-(255,20),7 : PAINT(128,8),9,7
    then POINT(50,20) reads 9 on both references and 7 here, while POINT(10,100)
    -- the fill's actual extent, through the one-cell gap -- agrees at 9.

⚠️ THE FILED ITEM'S OWN INSTRUCTION IS THE FIRST QUESTION, AND IT IS NOT
RHETORICAL: *ask whether the fill even paints the pixels in that group here,
before touching gfx_color_rmw.* A single sample at x=50 cannot tell

    (a) the cascade never started        -- the gap group was never recoloured
    (b) the cascade started and stopped  -- it ate rightward and not leftward
    (c) the cascade ran and this engine resolves the clash differently

apart. All three read 7 at x=50.

🎯 SO SAMPLE THE WHOLE WALL, not one point of it. SCREEN 2's colour table is one
byte per 8 pixels per SCANLINE, so y=20 is eleven independent colour groups
across the sampled x's, and the profile says exactly how far the eating reached
from each side of the gap. The gap is x=104..107, which is the LEFT half of the
group x=104..111 -- its right half (108..111) is wall. That asymmetry is the
whole fixture: the fill enters a group it SHARES with border pixels, and what
happens to those four pixels is the mechanism under test.

  x:    0    50   100  103 | 104  106 | 108  111 | 112  150  255
  grp:  0-7  48-55 96-103  | 104-111        | 112-119 ...
        <-------- wall -------->| gap |<- wall ->|<----- wall ----->

⚠️ TIMING: a 256x192 SCREEN-2 flood needs the proven step=90; the 2.5 s default
fires mid-fill and the raw scrape is a blank GRAPHICS screen.
"""
from __future__ import annotations
import os, re, sys

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "probes", "lib"))
import omsx_repl                                                  # noqa: E402

ZB_M = os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")
SIDES = {
    "vg8020": dict(machine="Philips_VG_8020", boot=8.0, reset=("NEW",)),
    "cf3300": dict(machine="National_CF-3300", boot=14.0,
                   reset=("", "SCREEN 0", "NEW")),
    "zb":     dict(machine=ZB_M, boot=8.0, reset=("NEW",)),
}
_only = os.environ.get("NTW_SIDES")
if _only:
    SIDES = {k: v for k, v in SIDES.items() if k in _only.split(",")}

STEP = float(os.environ.get("NTW_STEP", "90"))   # emulated s RUN..capture
TMO  = 1800.0
# ⚠️ NTW_STEP EXISTS BECAUSE A ROW WAS REPORTED AS A DIVERGENCE TWICE ON A VALUE
# THAT WAS NOT ONE. `v.thin` read `<NO OUTPUT>` on zb in rounds 2 AND 4 and the
# summary line printed `zb=DIFF` both times: the readout compares the zb face to
# the reference face and a missing capture is not equal to "9", so it scores as a
# divergence. It is a MISSING MEASUREMENT -- the capture firing before the fill
# ends. Round 4 said it would be re-run at a bigger step and then re-ran it at the
# same one, because the step was a module constant with no override.

NOTCH = ["SCREEN 2:LINE(0,20)-(103,20),7:LINE(108,20)-(255,20),7",
         "PAINT(128,8),9,7"]

# label -> (setup lines, sample points). Every sample is a POINT read into a
# variable; the capture is SCREEN 0 + PRINT, because a screen scrape cannot read
# PRINT while the VDP is in a graphics mode.
CASES: dict[str, tuple[list[str], list[tuple[int, int]]]] = {
    # THE PROFILE. Eleven groups across the wall, straddling the gap.
    "wall.row": (NOTCH, [(0, 20), (50, 20), (100, 20), (103, 20), (104, 20),
                         (106, 20), (108, 20), (111, 20), (112, 20), (150, 20),
                         (255, 20)]),
    # The neighbourhood: the rows immediately above and below the wall must be
    # the fill colour on BOTH sides of the gap -- that is what says the fill
    # really did surround the wall, so a 7 at y=20 is a border that SURVIVED and
    # not a region the fill never reached.
    "wall.near": (NOTCH, [(50, 19), (50, 21), (200, 19), (200, 21),
                          (128, 8), (10, 100)]),
    # 🟢 THE POSITIVE CONTROL FOR THE MECHANISM ITSELF. A wall with NO gap and a
    # seed above it: the fill cannot get past, so any eating here is the clash
    # rule acting on the group the fill DOES touch -- y=19, not y=20. If this
    # engine and the references agree on this one, the difference above is about
    # the CASCADE and not about whether "border eaten" exists at all.
    "solid.row": (["SCREEN 2:LINE(0,20)-(255,20),7", "PAINT(128,8),9,7"],
                  [(50, 20), (50, 19), (50, 21), (128, 8)]),
    # 🟢 ...and the shape the shipped gate already pins: a border colour that is
    # NOT on the wall, so C != B everywhere and the whole screen floods. It says
    # the fixture family works at all.
    "b15.row": (["SCREEN 2:LINE(0,20)-(255,20),7", "PAINT(128,8),9,15"],
                [(50, 20), (50, 19), (50, 21), (10, 100)]),
}

# ===========================================================================
# ROUND 2 — 🔴 ROUND 1 REFRAMED THE QUESTION, so round 2 asks the new one.
#
# Round 1, `wall.row`, y=20 across eleven colour groups:
#     refs  9 9 9 9 9 9 9 9 9 9 9      (x = 0 50 100 103 104 106 108 111 112 150 255)
#     zb    7 7 7 7 9 9 9 9 7 7 7
# 🎯 The cascade DID start here -- the filed item's own first question is
# answered: zerobas ate EXACTLY the one colour group the fill entered
# (x=104..111, the group holding the gap) and no other. That is not a bug in
# gfx_color_rmw; it is what the mechanism can do. Eating a group needs the fill
# to PAINT a pixel in it, painting a pixel needs to REACH it, and every pixel of
# the next group along the wall is a border until that group is eaten. The
# cascade cannot propagate, in either direction, by construction.
#
# 🔴 AND `solid.row` SAID SOMETHING LARGER THAN THE FILED ITEM. With NO GAP --
# `LINE(0,20)-(255,20),7 : PAINT(128,8),9,7` -- the references read 9 at (50,21),
# BELOW the wall, and zerobas reads 4. The reference's fill is not merely
# recolouring a wall it has reached; it is getting PAST a wall that has no gap.
#
# 🎯 SO THE HYPOTHESIS UNDER TEST IS NOW `spec-basic-graphics-g5.md` §5's OWN
# SENTENCE, which was measured for ONE geometry and may be the whole rule:
#
#     C != B  ->  FLOODS THE ENTIRE SCREEN, regardless of wall geometry.
#
# If so, zerobas reproduces it only when a wall pixel happens to SHARE a colour
# group with a pixel the fill can reach -- true for a vertical wall (the group
# straddles it) and false for a horizontal one (an 8x1 group on the wall's row is
# ALL wall).
#
# ⚠️ THE SECOND CAUSE OF "THE WHOLE SCREEN FLOODED" IS GOING AROUND THE WALL, and
# it is excluded by construction: every wall below spans its axis completely
# (x=0..255 or y=0..191), so there is no way around and a 9 on the far side can
# only have come THROUGH.
# 🟢 `v.group8` is the control that separates GEOMETRY from the rule. It is a
# vertical wall aligned to exactly one colour group (x=16..23), so no pixel of
# that group is ever reachable and zerobas can no more eat it than it can eat a
# horizontal one. If the references cross THAT too, the answer does not depend on
# orientation at all and "the group model" is not the explanation.
_H = "SCREEN 2:LINE(0,20)-({x2},{y2}),7"
CASES.update({
    # a wall 2 rows thick: does exactly ONE row get eaten, or all of it?
    "h2": ([_H.format(x2=255, y2=21), "PAINT(128,8),9,7"],
           [(50, 19), (50, 20), (50, 21), (50, 22), (10, 100)]),
    # ...and 4 rows thick, sampled row by row.
    "h4": ([_H.format(x2=255, y2=23), "PAINT(128,8),9,7"],
           [(50, 19), (50, 20), (50, 21), (50, 22), (50, 23), (50, 24),
            (10, 100)]),
    # a VERTICAL 1-px wall: here the 8-pixel group straddles the wall, so this
    # engine CAN eat it. Both sides are expected to cross -- the row that says
    # "border eaten" exists on this build at all.
    "v.thin": (["SCREEN 2:LINE(20,0)-(20,191),7", "PAINT(128,8),9,7"],
               [(20, 100), (19, 100), (10, 100), (0, 100), (128, 100)]),
    # 🟢 ...and a vertical wall filling exactly ONE colour group (x=16..23), so
    # no pixel of it is ever reachable, exactly like the horizontal case.
    "v.group8": (["SCREEN 2:LINE(16,0)-(23,191),7,BF", "PAINT(128,8),9,7"],
                 [(20, 100), (15, 100), (10, 100), (0, 100), (128, 100)]),
})

# ===========================================================================
# ROUND 3 — a SHARPER INSTRUMENT, and two apparatus faults from round 2 fixed.
#
# ⚠️ FIXTURE FAULT IN ROUND 2, FOUND BY READING THE NUMBERS: `h2` and `h4` were
# written as "a wall 2 / 4 rows thick" and they are NOT. `LINE(0,20)-(255,21),7`
# is a LINE, so it is a shallow DIAGONAL -- y=20 for the left half of the screen
# and y=21 for the right -- not a 2-row bar. `h4`'s zb reading says so out loud:
# (50,20) reads 9 and (50,21) reads 7, i.e. at x=50 the wall is on row 21, which
# a 2-row bar starting at y=20 could not produce. The thickness question is
# re-asked below with `,BF`, which is what draws a bar.
# ⚠️ AND AN APPARATUS READING MISREPORTED AS A DIVERGENCE: round 2's `v.thin`
# scored `zb=DIFF` on a zb value of `<NO OUTPUT>`. That is the capture firing
# mid-fill at step=90, not an answer -- the row is re-run here at a bigger step.
# A `<NO OUTPUT>` is never a divergence; it is a missing measurement.
#
# 🎯 AND THE REAL CHANGE: STOP INFERRING THE VRAM FROM `POINT`. `POINT` collapses
# the pattern bit and the two colour nibbles into one number, so "the wall reads
# 9" cannot say whether the wall pixel was PAINTED (pattern bit set, fg := 9) or
# merely RECOLOURED (bit already set, fg changed under it) -- and that is exactly
# the distinction the fix turns on. `VPEEK` reads the bytes.
#
# SCREEN 2 layout: pattern table at $0000, colour table at $2000, both 8 bytes
# per 8x8 character cell, so ONE COLOUR BYTE PER 8 PIXELS PER SCANLINE:
#     off = ((y\8)*32 + (x\8))*8 + (y AND 7)
#     pattern byte = off        colour byte = $2000 + off
# The colour byte is fg in the high nibble, bg in the low one.
# 🔴 (16,100), (20,100) and (23,100) ALL share pattern byte 3092 and colour byte
# 11284 -- that is the point of `vp.group8`: a vertical wall drawn exactly on
# x=16..23 owns a whole colour group at every y, so no pixel of it is ever
# reachable by a fill outside it. `.pre` reads the same bytes with NO PAINT, so
# what the wall itself writes is a MEASUREMENT and not an assumption.
#
# label -> (setup lines, BASIC expressions to read, step)
EXPR_CASES: dict[str, tuple[list[str], list[str], float]] = {}

_SOLID = ["SCREEN 2:LINE(0,20)-(255,20),7", "PAINT(128,8),9,7"]
_G8    = ["SCREEN 2:LINE(16,0)-(23,191),7,BF", "PAINT(128,8),9,7"]
_G8PRE = ["SCREEN 2:LINE(16,0)-(23,191),7,BF"]
# x=50, rows 19 / 20 / 21 -- above the wall, the wall, below it
_S_EXPR = ["VPEEK(563)", "VPEEK(8755)", "VPEEK(564)", "VPEEK(8756)",
           "VPEEK(565)", "VPEEK(8757)"]
# y=100, groups 8..15 / 16..23 (the wall) / 24..31
_G_EXPR = ["VPEEK(3084)", "VPEEK(11276)", "VPEEK(3092)", "VPEEK(11284)",
           "VPEEK(3100)", "VPEEK(11292)"]
EXPR_CASES["vp.solid"]     = (_SOLID,  _S_EXPR, 90.0)
EXPR_CASES["vp.g8"]        = (_G8,     _G_EXPR, 90.0)
EXPR_CASES["vp.g8.pre"]    = (_G8PRE,  _G_EXPR, 8.0)
# ...and the same three bytes with NO wall and NO paint, so "what does an
# untouched SCREEN 2 hold here" is measured rather than assumed.
EXPR_CASES["vp.blank"]     = (["SCREEN 2"], _G_EXPR, 8.0)

# ===========================================================================
# ROUND 4 — 🔴 THE CONTROL ROUND 3 SHOULD HAVE CARRIED, and it is decisive.
#
# Round 3 read the VRAM instead of POINT, and the readings do not say what the
# filed item says. On a fresh SCREEN 2 every colour byte is $04 (fg 0, bg 4) with
# the pattern byte clear -- so "the background is 4" is literally the BG NIBBLE.
# Then:
#
#   vp.g8.pre  `LINE(16,0)-(23,191),7,BF`, no PAINT, group x=16..23 at y=100
#     ALL THREE SIDES:  pattern 0   colour $07 (fg 0, bg 7)
#
# 🎯 `,BF` DOES NOT SET THE PATTERN BITS AT ALL. A fully covered group is written
# as "background = 7", bits clear -- the natural byte-at-a-time encoding, and both
# references do exactly the same thing. `POINT` cannot see this: it reports the BG
# nibble for a clear bit, so the wall READS as colour 7 either way.
# 🔴 AND THAT DISSOLVES `v.group8`, `h2b` and `h4b`, which all agreed on all three
# sides: those walls are not borders on ANY of the three, because an undrawn pixel
# is never a border. They agreed for a reason that has nothing to do with eating.
#
#   vp.solid   `LINE(0,20)-(255,20),7 : PAINT(128,8),9,7`, x=50, rows 19/20/21
#     refs:  0 $09 | 0 $09 | 0 $09        (fg 0, bg 9 -- everywhere)
#     zb:  255 $94 | 255 $74 | 0 $04      (bits SET, fg 9 / fg 7 / untouched)
#
# 🎯 SO THE TWO ENGINES PAINT DIFFERENT BYTES. The reference's fill writes the
# BACKGROUND nibble and leaves the pattern bits CLEAR; this engine's sets the bits
# and writes the FOREGROUND nibble. Both `POINT` as 9. ⚠️ `vp.g8` is the sharpest
# case: every side reads 9 at all three x, and the bytes behind those 9s are
# `0 $09` on the references and `255 $94` here -- a row that AGREES through the
# instrument it was written for and DIVERGES underneath it.
#
# 🔴 WHICH LEAVES EXACTLY ONE QUESTION, AND ROUND 3 CANNOT ANSWER IT. After the
# PAINT the wall row reads `0 $09` on the reference. That is consistent with BOTH
#   (a) the plain LINE left the bits CLEAR (bg=7), so the wall was never a border
#       on the reference and the fill simply walked through it; and
#   (b) the plain LINE set the bits (fg=7), the wall WAS a border, and PAINT
#       cleared the bits as it painted over it.
# Under (a) the divergence is in LINE and PAINT is innocent. Under (b) it is in
# PAINT. `.pre` reads the same bytes with NO PAINT, which separates them, and it
# is the control that should have been in round 3.
# ===========================================================================
# ROUND 5 — the mechanism, now that round 4 has said what the wall IS.
#
# 🔴 ROUND 4 SETTLED IT: a plain `LINE(0,20)-(255,20),7` writes pattern $FF and
# colour $74 (fg 7, bg 4) on ALL THREE SIDES, and a single `PSET(50,20),7` writes
# pattern $20 / $74 on all three. So the wall is a genuinely DRAWN border of
# colour 7 == B on the reference too, and hypothesis (a) is dead: the reference
# is not walking through a wall that was never there. Its PAINT crosses a real
# border, and afterwards that byte reads pattern 0 / $09 -- the bits CLEARED.
#
# 🎯 SO THE TWO QUESTIONS LEFT ARE BOTH ABOUT PAINT:
#   hp3  does the reference erase ONE wall row and stop, or all of them? Three
#        stacked plain LINEs; if it erases as it goes it reaches y=23, if it eats
#        one group's worth it stops at 21. This is the shape a fix has to match.
#   cb   is `C == B` still bounded on this geometry? `spec-basic-graphics-g5.md`
#        §5's dichotomy (C==B bounded / C!=B floods everything) was measured on a
#        BOX. If it holds here, the wall geometry is not what decides anything and
#        the filed item's "clash policy" framing is the wrong frame.
#        🟢 It is also the control that stops "the reference floods everything"
#        from being unfalsifiable: something must still bound it.
CASES.update({
    "hp3": (["SCREEN 2:LINE(0,20)-(255,20),7:LINE(0,21)-(255,21),7"
             ":LINE(0,22)-(255,22),7", "PAINT(128,8),9,7"],
            [(50, 19), (50, 20), (50, 21), (50, 22), (50, 23), (10, 100)]),
    "cb":  (["SCREEN 2:LINE(0,20)-(255,20),7", "PAINT(128,8),7,7"],
            [(50, 19), (50, 20), (50, 21), (10, 100)]),
})

EXPR_CASES["vp.solid.pre"] = (["SCREEN 2:LINE(0,20)-(255,20),7"], _S_EXPR, 8.0)
# ...and the one-pixel version, so "a plain plot sets the bit" is measured and not
# assumed from the LINE case.
EXPR_CASES["vp.pset.pre"]  = (["SCREEN 2:PSET(50,20),7"], _S_EXPR, 8.0)
# ...and a 1-row `,BF` bar in the SAME place, so LINE vs ,BF is a controlled
# comparison rather than a comparison across two different geometries.
EXPR_CASES["vp.bfrow.pre"] = (["SCREEN 2:LINE(0,20)-(255,20),7,BF"], _S_EXPR, 8.0)

CASES.update({
    # the thickness question, asked with `,BF` this time
    "h2b": (["SCREEN 2:LINE(0,20)-(255,21),7,BF", "PAINT(128,8),9,7"],
            [(50, 19), (50, 20), (50, 21), (50, 22), (10, 100)]),
    "h4b": (["SCREEN 2:LINE(0,20)-(255,23),7,BF", "PAINT(128,8),9,7"],
            [(50, 19), (50, 20), (50, 21), (50, 22), (50, 23), (50, 24),
             (10, 100)]),
})

ERR = re.compile(r"^\s*([A-Z][A-Za-z' ]+ error|Illegal function call|Overflow|"
                 r"Out of memory|Type mismatch|Subscript out of range)", re.M)


def read(cap, n):
    if cap is None:
        return "<NO CAPTURE>"
    txt = " ".join("".join(cap).split())
    m = re.search(r"R((?:\s*-?\d+){%d})" % n, txt)
    if m:
        return [int(v) for v in m.group(1).split()]
    e = ERR.search(txt)
    return f"<{e.group(1).strip()}>" if e else "<NO OUTPUT>"


def prog(setup, pts):
    q = ":".join(f"{chr(65 + i)}=POINT({x},{y})" for i, (x, y) in enumerate(pts))
    pr = 'SCREEN0:PRINT"R";' + ";".join(chr(65 + i) for i in range(len(pts))) + ":END"
    lines = list(setup) + [q, pr]
    return [f"{20 + 10 * k} {ln}" for k, ln in enumerate(lines)]


def expr_prog(setup, exprs):
    q = ":".join(f"{chr(65 + i)}={e}" for i, e in enumerate(exprs))
    pr = 'SCREEN0:PRINT"R";' + ";".join(chr(65 + i) for i in range(len(exprs))) + ":END"
    return [f"{20 + 10 * k} {ln}" for k, ln in enumerate(list(setup) + [q, pr])]


def run_expr(label) -> None:
    setup, exprs, step = EXPR_CASES[label]
    body = ["10 ON ERROR GOTO 900"] + expr_prog(setup, exprs)
    body += ['900 SCREEN 0:PRINT"[ERR";ERR;"]":END']
    row = {}
    for side, cfg in SIDES.items():
        caps = omsx_repl.run_cases(
            cfg["machine"], [("direct", list(cfg["reset"]) + body + ["RUN"])],
            batch=False, boot=cfg["boot"], step=step, cap_gap=10.0, timeout=TMO)
        v = read(caps[0], len(exprs))
        row[side] = v
        # print the colour bytes as fg/bg nibbles too -- the whole point
        if isinstance(v, list):
            pretty = " ".join(
                (f"{n:3d}" if i % 2 == 0 else f"{n:3d}(fg{n >> 4},bg{n & 15})")
                for i, n in enumerate(v))
        else:
            pretty = str(v)
        print(f"  {side:7s} {label:10s} {pretty}", flush=True)
    print(f"  EXP {label:10s} " + " ".join(exprs), flush=True)
    if "vg8020" in row and "cf3300" in row:
        agree = "refs-agree" if row["vg8020"] == row["cf3300"] else "REFS DIFFER"
        zbm = ("zb=" + ("same" if row.get("zb") == row["vg8020"] else "DIFF")
               if "zb" in row else "zb=<not run>")
    else:
        agree, zbm = "one-ref-only", "no ref this round"
    print(f"  ROW {label:10s} {agree:12s} {zbm}\n", flush=True)


def main() -> int:
    want = sys.argv[1:] or list(CASES) + list(EXPR_CASES)
    for label in want:
        if label in EXPR_CASES:
            run_expr(label)
            continue
        setup, pts = CASES[label]
        body = ["10 ON ERROR GOTO 900"] + prog(setup, pts)
        body += ['900 SCREEN 0:PRINT"[ERR";ERR;"]":END']
        row = {}
        for side, cfg in SIDES.items():
            caps = omsx_repl.run_cases(
                cfg["machine"], [("direct", list(cfg["reset"]) + body + ["RUN"])],
                batch=False, boot=cfg["boot"], step=STEP, cap_gap=10.0, timeout=TMO)
            row[side] = read(caps[0], len(pts))
            print(f"  {side:7s} {label:10s} {row[side]}", flush=True)
            if os.environ.get("NTW_RAW"):
                print("      RAW " + repr((caps[0] or "")[-400:]), flush=True)
        print(f"  PTS {label:10s} " + " ".join(f"({x},{y})" for x, y in pts),
              flush=True)
        if "vg8020" in row and "cf3300" in row:
            agree = "refs-agree" if row["vg8020"] == row["cf3300"] else "REFS DIFFER"
            zbm = ("zb=" + ("same" if row.get("zb") == row["vg8020"] else "DIFF")
                   if "zb" in row else "zb=<not run>")
        else:
            agree, zbm = "one-ref-only", "no ref this round"
        print(f"  ROW {label:10s} {agree:12s} {zbm}\n", flush=True)
    print("done", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
