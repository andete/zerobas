#!/usr/bin/env python3
"""D-PAINTMC — what does the reference's PAINT flood actually DO?

The SCREEN-3 blocker filed by D-SCREEN3 §5 is ALGORITHMIC: adjacent LOGICAL
pixels share one 4x4 cell, so the first cell painted to C reads as a border to
its own neighbours and the walk stops dead. Three hypotheses were filed for how
the reference escapes it:

  (1) it steps by CELL in MC rather than by pixel;
  (2) its span walk never re-tests an already-painted span (bookkeeping);
  (3) `gfx_paint_inside`'s `== C` stop is zerobas's OWN INVENTION -- the source
      comment says `own-design stop` and admits no captured case measures it --
      and the reference has no such rule.

(1) IS NOT OBSERVABLE. Every MC feature is cell-granular, so a cell walk and a
pixel walk paint the SAME SET; it is an implementation choice for us, not a claim
about the reference. (2) and (3) ARE observable, and one fixture separates them:

  put a region ALREADY COLOURED C inside an otherwise open area, with a border
  colour B that appears NOWHERE on the screen.

  * `== C` is a stop -> the fill halts at that region.
  * no `== C` stop    -> the fill crosses it (C != B, so it is "inside") -- and
    something OTHER than repainting has to make it terminate at all.

⚠️ A row reading 4 beyond the barrier AGREES for a second reason: the fill may
never have spread at all. Every `.stop` row is therefore paired with a `.spread`
row on the SAME program, reading a point the fill must have reached.

⚠️ FIXTURE SHAPE (the scout's; nothing else works): capture into a variable,
force SCREEN 0, THEN print -- a screen scrape cannot read PRINT while the VDP is
in a graphics mode. ON ERROR so a refusal is a readable value.

⚠️ TIMING IS PART OF THE MEASUREMENT. PAINT is genuinely slow in EMULATED time
and `step` is the RUN..capture gap. Round 1 ran at the 2.5 s default and read
`<NO OUTPUT>` on EVERY SCREEN-2 row of all three sides, including its own known
positive -- a capture fired mid-fill, wearing the face of a hang. The raw scrape
is a blank GRAPHICS screen, which is why the `box*` calibration rows below (the
smallest possible positive fill) come first. basic_probe_graphics.py's PAINT
phase uses step=90 for exactly this reason.
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
# ⚠️ PAINTMC_SIDES=vg8020,cf3300 measures the REFERENCES ALONE. That is not a
# convenience: the openMSX preflight REFUSES to boot the zb machine while the
# tree is mid-edit (it compares build/*.rom against their sources and reports
# STALE), which is the right answer -- an unbuilt ROM reads as an absent FEATURE.
# A reference-only round is how a question about the REFERENCE gets answered
# without rebuilding underneath a differential.
_only = os.environ.get("PAINTMC_SIDES")
if _only:
    SIDES = {k: v for k, v in SIDES.items() if k in _only.split(",")}

S2_STEP, S2_TMO = 90.0, 1800.0     # a 256x40 SCREEN-2 flood, the proven value
MC_STEP, MC_TMO = 30.0, 900.0      # 64x48 cells -- 16x fewer writes, still slow

CASES: dict[str, list[str]] = {}
STEP: dict[str, tuple[float, float]] = {}


def case(label, lines, mc=True):
    CASES[label] = lines
    STEP[label] = (MC_STEP, MC_TMO) if mc else (S2_STEP, S2_TMO)


# ===========================================================================
# 0. CALIBRATION ON KNOWN POSITIVES -- the smallest fill that can exist. If
#    these do not read what the shipped machine demonstrably does, nothing
#    below is a measurement.
# ===========================================================================
_BOX = ['SCREEN {m}:LINE(4,4)-(40,40),15,B', 'PAINT(20,20),9,15',
        'V={read}:SCREEN 0:PRINT"[";V;"]":END']
case("box2.in",   [ln.format(m=2, read="POINT(20,30)") for ln in _BOX], mc=False)
case("box2.out",  [ln.format(m=2, read="POINT(60,20)") for ln in _BOX], mc=False)
case("box2.wall", [ln.format(m=2, read="POINT(4,20)")  for ln in _BOX], mc=False)
case("box3.in",   [ln.format(m=3, read="POINT(20,30)") for ln in _BOX])
case("box3.out",  [ln.format(m=3, read="POINT(60,20)") for ln in _BOX])

# ===========================================================================
# 1. THE DECISIVE PAIR -- a barrier ALREADY COLOURED C, border B absent.
#    SCREEN 2 first: the mode where this engine's own-design `== C` stop is
#    LIVE, so a divergence here is a defect in shipped code, not a gap.
# ===========================================================================
_AC = ['SCREEN {m}:LINE(0,40)-(255,40),9', 'PAINT(10,10),9,15',
       'V={read}:SCREEN 0:PRINT"[";V;"]":END']
case("ac2.spread", [ln.format(m=2, read="POINT(10,0)")  for ln in _AC], mc=False)
case("ac2.stop",   [ln.format(m=2, read="POINT(10,60)") for ln in _AC], mc=False)
case("ac2.online", [ln.format(m=2, read="POINT(10,40)") for ln in _AC], mc=False)
case("ac3.spread", [ln.format(m=3, read="POINT(10,0)")  for ln in _AC])
case("ac3.stop",   [ln.format(m=3, read="POINT(10,60)") for ln in _AC])
case("ac3.online", [ln.format(m=3, read="POINT(10,40)") for ln in _AC])

# ===========================================================================
# 2. MC BORDER SEMANTICS -- re-verify the scout rather than trust it.
# ===========================================================================
_MB = ['SCREEN 3:LINE(0,40)-(255,40),7', '{paint}',
       'V={read}:SCREEN 0:PRINT"[";V;"]":END']
for _l, _p, _r in [
        ("mb.dflt.far", "PAINT(10,10),9",   "POINT(10,60)"),   # B defaults to C
        ("mb.b7.far",   "PAINT(10,10),9,7", "POINT(10,60)"),   # explicit border 7
        ("mb.b7.up",    "PAINT(10,10),9,7", "POINT(10,0)"),
        ("mb.b4.up",    "PAINT(10,10),9,4", "POINT(10,0)"),    # border == background
        ("mb.b4.seed",  "PAINT(10,10),9,4", "POINT(10,10)"),   # ...seed still painted?
]:
    case(_l, [ln.format(paint=_p, read=_r) for ln in _MB])

# ===========================================================================
# 3. TERMINATION with C != B and B NOWHERE ON SCREEN.
#    `== C` stop  -> the surface goes 9 and the program FINISHES.
#    no such stop -> nothing ever stops being "inside".
#    ⚠️ Both rows share one program: if the .seed row reads while .far does not,
#    the difference is the FILL's extent; if both are blank, the run never ended.
# ===========================================================================
_TM = ['SCREEN 3', 'PAINT(10,10),9,15',
       'V={read}:SCREEN 0:PRINT"[";V;"]":END']
case("tm3.far",  [ln.format(read="POINT(200,150)") for ln in _TM])
case("tm3.seed", [ln.format(read="POINT(10,10)")   for ln in _TM])

# ===========================================================================
# 4. A CONCAVE NOTCH THROUGH A ONE-CELL GAP. The wall leaves x=104..107 open --
#    exactly ONE 4-wide MC cell. The seed is ABOVE the wall; everything BELOW it
#    is reachable only through that gap, and only by a walk that RE-EXTENDS a
#    pushed span to its true width.
# ===========================================================================
_NT = ['SCREEN {m}:LINE(0,20)-(103,20),7:LINE(108,20)-(255,20),7',
       'PAINT(128,8),9,7', 'V={read}:SCREEN 0:PRINT"[";V;"]":END']
case("nt3.thru",  [ln.format(m=3, read="POINT(10,100)") for ln in _NT])
case("nt3.near",  [ln.format(m=3, read="POINT(128,60)") for ln in _NT])
case("nt3.wall",  [ln.format(m=3, read="POINT(50,20)")  for ln in _NT])
case("nt3.above", [ln.format(m=3, read="POINT(10,4)")   for ln in _NT])
case("nt2.thru",  [ln.format(m=2, read="POINT(10,100)") for ln in _NT], mc=False)
case("nt2.wall",  [ln.format(m=2, read="POINT(50,20)")  for ln in _NT], mc=False)

# ===========================================================================
# 5. THE SEED RULE. 🔴 `mb.b4.seed` came back 4 on BOTH references: with the
#    border equal to the BACKGROUND, multicolour PAINT paints NOTHING -- not even
#    the seed. That contradicts the SCREEN-2 rule this engine ships and gates on
#    (basic_probe_graphics.py `seed_on_wall_pixel`: a seed placed exactly on a
#    DRAWN pixel whose colour == B still floods past it). Either the seed rule
#    genuinely differs by mode, or `mb.b4` fails for some other reason and the
#    two are not the same question. These rows are the twin pair that decides it:
#    the SAME seed-on-a-B-coloured-wall geometry in BOTH modes.
_SD = ['SCREEN {m}:LINE(20,20)-(60,60),15,B', 'PAINT(20,20),9,15',
       'V={read}:SCREEN 0:PRINT"[";V;"]":END']
case("sd3.wall.in",   [ln.format(m=3, read="POINT(40,40)") for ln in _SD])
case("sd3.wall.seed", [ln.format(m=3, read="POINT(20,20)") for ln in _SD])
case("sd2.wall.in",   [ln.format(m=2, read="POINT(40,40)") for ln in _SD], mc=False)
case("sd2.wall.seed", [ln.format(m=2, read="POINT(20,20)") for ln in _SD], mc=False)

# ...and the same question for the OTHER stop: a seed already coloured C.
_SC = ['SCREEN {m}:PSET(10,10),9', 'PAINT(10,10),9,7',
       'V={read}:SCREEN 0:PRINT"[";V;"]":END']
case("sc3.up",   [ln.format(m=3, read="POINT(10,0)")  for ln in _SC])
case("sc3.seed", [ln.format(m=3, read="POINT(10,10)") for ln in _SC])
case("sc2.up",   [ln.format(m=2, read="POINT(10,0)")  for ln in _SC], mc=False)

# 6. DOMAIN EDGE: a border colour NO cell can ever hold. GFX_B is a full byte
#    (the resident does not range-check B -- spec §3/§5), and a multicolour cell
#    is a nibble, so 16 is unreachable in MC exactly as it is in SCREEN 2. The
#    SCREEN-2 battery already gates `border16_flood_ok`; this is its MC twin, and
#    it also exercises the new seed gate against a B nothing can equal.
_B16 = ['SCREEN {m}:LINE(0,40)-(255,40),7', 'PAINT(10,10),9,16',
        'V={read}:SCREEN 0:PRINT"[";V;"]":END']
case("b16.3.far", [ln.format(m=3, read="POINT(10,60)") for ln in _B16])
case("b16.3.up",  [ln.format(m=3, read="POINT(10,0)")  for ln in _B16])

# 🔴 7. THE BORDER DOMAIN IN MULTICOLOUR -- a row that AGREED BEFORE THE FIX FOR
#    THE WRONG REASON. `PAINT(10,10),9,16` is ERR 5 on both references in SCREEN 3
#    while `border16_flood_ok` has SCREEN 2 flooding happily on the same argument
#    (basic_probe_graphics.py PHASE H). Before D-PAINTMC every SCREEN-3 PAINT was
#    ERR 5 here, so the row agreed while measuring nothing. Sweep the boundary
#    rather than guess where it is -- and run the SCREEN-2 twin of the SAME
#    program, so "the mode" and "this fixture" are told apart.
_BD = ['SCREEN {m}:LINE(0,40)-(255,40),7', 'PAINT(10,10),9,{b}',
       'V=POINT(10,0):SCREEN 0:PRINT"[";V;"]":END']
for _l, _m, _b in [("bd3.15", 3, "15"), ("bd3.16", 3, "16"), ("bd3.17", 3, "17"),
                   ("bd3.255", 3, "255"), ("bd3.neg", 3, "-1"),
                   ("bd3.256", 3, "256"),
                   ("bd2.15", 2, "15"), ("bd2.16", 2, "16"),
                   ("bd2.255", 2, "255"), ("bd2.neg", 2, "-1"),
                   # the edge that NAMES the SCREEN-2 rule: is the domain
                   # "0..255" (a byte) or merely "not negative"?
                   ("bd2.256", 2, "256")]:
    case(_l, [ln.format(m=_m, b=_b) for ln in _BD], mc=(_m == 3))

# ===========================================================================
# 8. D-PAINTS2SEED: HOW BROAD IS THE SCREEN-2 SEED RULE?
#    `sc2.up` measured ONE case -- a seed PSET to 9 with C=9 -- and it refuses.
#    The rule "refuse a seed whose effective colour == C" is broader than that
#    case: it also covers an UNDRAWN seed, whose effective colour IS the
#    background by construction (gfx_paint_read's header), so that half only
#    arises when C == the background.
#
#    ⚠️ THAT HALF LOOKS UNOBSERVABLE AND IS NOT. Painting C == bg clashes to
#    "clear the bit" (the PSET rule), so a flood with C == bg ERASES every drawn
#    pixel it covers, while a refusal leaves them alone. Put a drawn pixel inside
#    the region and the two answers are 9 and 4:
#
#      LINE(20,20)-(60,60),15,B : PSET(40,40),9 : PAINT(30,30),4,15
#        refuse -> POINT(40,40) = 9      flood -> POINT(40,40) = 4
#
#    The .ctl row is the same geometry with a C that is NOT the background, and
#    exists so that "it refused" cannot be confused with "the fill never ran".
_SU = ['SCREEN 2:LINE(20,20)-(60,60),15,B', 'PSET(40,40),9', 'PAINT(30,30),{c},15',
       'V={read}:SCREEN 0:PRINT"[";V;"]":END']
case("su2.cbg", [ln.format(c=4, read="POINT(40,40)") for ln in _SU], mc=False)
case("su2.ctl", [ln.format(c=9, read="POINT(30,30)") for ln in _SU], mc=False)
# 🔴 su2.cbg AGREED ON ALL THREE SIDES AND IT WAS BUILT WRONG. Its drawn pixel is
# at (40,40), a DIFFERENT row from the seed, so reaching it needs a PUSH -- and a
# push goes through the `inside` test, which stops at `== C` on BOTH sides. With
# C == the background every undrawn pixel reads `== C`, so no span is ever pushed
# and (40,40) survives whether the seed was refused or not. The row cannot
# separate the two hypotheses it was built for.
# 🎯 THE FIX IS GEOMETRIC: put the drawn pixel on the SEED'S OWN ROW, which
# gfx_paint_extend_lr reaches with the looser `passable` walk, no push involved.
# Then a flood repaints it with C == bg, the PSET clash rule clears its bit, and
# it reads 4; a refusal leaves it 9.
_SUR = ['SCREEN 2:LINE(20,20)-(60,60),15,B', 'PSET(35,30),9',
        'PAINT(30,30),{c},15', 'V={read}:SCREEN 0:PRINT"[";V;"]":END']
case("su2.row.cbg", [ln.format(c=4, read="POINT(35,30)") for ln in _SUR], mc=False)
# ...and the control that the row walk really does run and really does reach x=33
# (with a C that is NOT the background, so the paint is visible).
case("su2.row.ctl", [ln.format(c=9, read="POINT(33,30)") for ln in _SUR], mc=False)

# ...and the drawn-seed case again, in THIS geometry rather than sc2's, so the
# rule is not resting on a single fixture shape either.
_SU2 = ['SCREEN 2:LINE(20,20)-(60,60),15,B', 'PSET(30,30),9',
        'PAINT(30,30),9,15', 'V={read}:SCREEN 0:PRINT"[";V;"]":END']
case("su2.drawn", [ln.format(read="POINT(50,50)") for ln in _SU2], mc=False)

# 🔴 9. THE ROW THAT GIVES K-PM3 ITS TEETH BACK. D-PAINTS2SEED's seed gate reads
#    the seed's COLOUR and ignores gfx_paint_read's Zf, where the gate it replaced
#    went through gfx_paint_passable, which consulted it. `cp $FF` (the MC arm's
#    "no cell is ever background") therefore only matters when B == the background
#    AND the seed is admitted -- and in mb.b4.* the seed IS the background, so it
#    is refused by colour alone and the walk never runs. K-PM3 went from two
#    reddened rows to ZERO with the ROM provably moved.
#    🎯 Admit the seed by DRAWING it first, and the walk then meets
#    background-coloured cells as borders, which is the thing `cp $FF` decides.
_B4X = ['SCREEN 3:PSET(10,10),9', 'PAINT(10,10),1,4',
        'V={read}:SCREEN 0:PRINT"[";V;"]":END']
case("b4x.seed", [ln.format(read="POINT(10,10)") for ln in _B4X])
case("b4x.far",  [ln.format(read="POINT(10,60)") for ln in _B4X])

# ===========================================================================
# 🔴 10. D-PAINTBORD -- WHERE IN THE PARSE DOES THE BORDER DOMAIN SIT?
#    §7 measured the DOMAIN (0..255 in SCREEN 2, 0..15 in MULTICOLOUR) and filed
#    the ORDERING as unmeasured. D-LINERR's whole finding is that WHERE a check
#    sits is itself a claim, and a 4th argument is the only thing that separates
#    the hypotheses, because everything else that could race the B domain
#    (off-screen seed, wrong mode, out-of-range C) also raises ERR 5:
#
#      `PAINT(10,10),9,16,`  in SCREEN 3  -> ERR 5  the domain is checked as B is
#                                                   parsed, ABOVE the grammar
#                                        -> ERR 2  the grammar wins
#
#    ⚠️ EVERY ROW HERE IS PAIRED WITH ITS IN-DOMAIN TWIN ON THE SAME PROGRAM.
#    `od3.b15c` / `od2.b16c` use a border that is LEGAL in that mode, so they
#    must read ERR 2 -- that is what proves the trailing comma is a 4th argument
#    at all and that this fixture reaches the grammar. Without them an ERR 2 on
#    the out-of-domain row would agree with "the check is missing" and with "the
#    fixture never got that far" alike.
#    ⚠️ And `od3.b16` / `od2.b256` are the SAME programs WITHOUT the trailing
#    comma: known ERR 5 from §7, re-run here as this round's own calibration on a
#    known positive at THIS step.
_OD = ['SCREEN {m}:LINE(0,40)-(255,40),7', 'PAINT(10,10),9,{b}{tail}',
       'V=POINT(10,0):SCREEN 0:PRINT"[";V;"]":END']
for _l, _m, _b, _t in [
        # --- MULTICOLOUR: 16 is OUTSIDE the domain, 15 inside ---
        ("od3.b16c",  3, "16",  ","),   # out-of-domain B + 4th arg -> ERR 5 or 2?
        ("od3.b15c",  3, "15",  ","),   # in-domain B + 4th arg -> must be ERR 2
        ("od3.b16",   3, "16",  ""),    # calibration: known ERR 5 (bd3.16)
        # --- SCREEN 2: 256 is OUTSIDE the domain, 16 inside ---
        ("od2.b256c", 2, "256", ","),   # out-of-domain B + 4th arg -> ERR 5 or 2?
        ("od2.b16c",  2, "16",  ","),   # in-domain B + 4th arg -> must be ERR 2
        ("od2.b256",  2, "256", ""),    # calibration: known ERR 5 (bd2.256)
]:
    case(_l, [ln.format(m=_m, b=_b, tail=_t) for ln in _OD], mc=(_m == 3))

BR = re.compile(r"\[([^\]]*)\]")
ERR = re.compile(r"^\s*([A-Z][A-Za-z' ]+ error|Illegal function call|Overflow|"
                 r"Out of memory|Type mismatch|Subscript out of range)", re.M)


def face(cap):
    if cap is None:
        return "<NO CAPTURE>"
    m = BR.search(cap)
    if m:
        return " ".join(m.group(1).split()) or "<empty>"
    e = ERR.search(cap)
    return f"<{e.group(1).strip()}>" if e else "<NO OUTPUT>"


def main() -> int:
    want = sys.argv[1:] or list(CASES)
    bad = [w for w in want if w not in CASES]
    if bad:
        print(f"unknown case(s): {bad}", file=sys.stderr)
        return 2
    for label in want:
        lines = CASES[label]
        step, tmo = STEP[label]
        body = ["10 ON ERROR GOTO 900"]
        body += [f"{20+10*k} {ln}" for k, ln in enumerate(lines)]
        body += ['900 SCREEN 0:PRINT"[ERR";ERR;"]":END']
        row = {}
        for side, cfg in SIDES.items():
            caps = omsx_repl.run_cases(
                cfg["machine"], [("direct", list(cfg["reset"]) + body + ["RUN"])],
                batch=False, boot=cfg["boot"], step=step, cap_gap=10.0,
                timeout=tmo)
            row[side] = face(caps[0])
            print(f"  {side:7s} {label:11s} -> {row[side]!r}", flush=True)
            if os.environ.get("PAINTMC_RAW"):
                print("      RAW " + repr((caps[0] or "")[-400:]), flush=True)
        if "vg8020" in row and "cf3300" in row:
            agree = "refs-agree" if row["vg8020"] == row["cf3300"] else "REFS DIFFER"
        else:
            agree = "one-ref-only"
        # ⚠️ A READOUT THAT LIES: with PAINTMC_SIDES=zb there is no reference in
        # THIS round, and comparing against `None` printed "zb=DIFF" on every row
        # of a run whose values all agreed with the readings taken earlier. Say
        # "no ref this round" instead -- the scoring is the knife runner's job.
        ref = row.get("vg8020", row.get("cf3300"))
        if "zb" not in row:
            zbm = "zb=<not run>"
        elif ref is None:
            zbm = "zb=<no ref this round>"
        else:
            zbm = "zb=" + ("same" if row["zb"] == ref else "DIFF")
        print(f"  ROW {label:11s} {agree:12s} {zbm}", flush=True)
    print("done", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
