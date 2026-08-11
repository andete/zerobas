#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""D-LINERR — LINE's SCREEN-mode refusal is the LAST thing it does, not the first.

WHERE THIS CAME FROM. D-STMTPEND (2026-08-09) filed one `graphics.asm`
divergence it could not close, the `c.line.tm` DEFERRED row of
`make stmtpend-acceptance`:

    LINE (0,0)-((Q$<5),1)      zerobas ERR 5   both references ERR 13

and diagnosed it as *"LINE raises its own Illegal function call EAGERLY FROM
INSIDE ITS COORDINATE PARSE"*.

🔴 THAT DIAGNOSIS IS WRONG, AND READING THE SITE IS ENOUGH TO SEE IT. There is
no ERR 5 anywhere in `parse_coord`. `ex_line_gfx` opens with

    ld a,(SCRMOD) / cp 2 / jp nz,gfx_err5

— three instructions, BEFORE the first coordinate byte is looked at — and the
filed row runs in the boot default SCREEN 0 (its `CLS` does not change the
mode). So zerobas answers ERR 5 to a statement whose coordinates it never
evaluated, and the references answer ERR 13 to the same statement. The question
is not "where does the coordinate parse raise": it is **WHERE IN THE STATEMENT
DOES THE MODE REFUSAL HAPPEN**, which is precisely D-SCRERR's ordering shape one
verb over.

⚠️ NOBODY HAS EVER MEASURED LINE'S ERROR SURFACE. `make graphics-acceptance`
covers what LINE DRAWS (docs/spec-basic-graphics-g3.md); what it REFUSES has no
denominator at all. One row is not a rule ([[lrvar-slice]]), so this probe
sweeps the whole surface and the filed row is one of seventy.

THE INSTRUMENT: `[ E , X , Y ]`, NOT A SCREEN SCRAPE.

LINE only draws in SCREEN 2, so every row changes the mode and a screen scrape
is blind to its own subject ([[readout-blind-to-its-own-subject]]) — the same
wall that made D-STMTPEND defer `u.scr.dz` and D-SCRERR stop scraping. So this
probe does not scrape, it ASKS:

    E = ERR                                   the error code, 0 if it completed
    X = PEEK(&HFCB7)+256*PEEK(&HFCB8)         GRPACX -- the LAST-REFERENCED
    Y = PEEK(&HFCB9)+256*PEEK(&HFCBA)         GRPACY -- POINT

captured in the HANDLER, before line 50 forces SCREEN 0 to make the PRINT
readable whatever mode line 30 left behind. (Published MSX system-variable
addresses; the identical read already ships in `basic_probe_graphics.py`
phases D/F, i.e. it is proven on both references.)

🔴 GRPAC IS NOT DECORATION — IT SAYS HOW FAR THE STATEMENT GOT. Every program
seeds `PSET(7,4)`, so GRPAC = (7,4) means "LINE moved nothing"; the LINE rows
draw `(11,12)-(20,21)`, so (11,12) means "the first endpoint was STAGED and the
statement then died", and (20,21) means "it ran to completion". Staging p1
before parsing p2 is what makes STEP chain (spec-basic-graphics-g3.md §3.3), so
it is a side effect BOTH sides must have, and it is the only window onto the
statement's interior that does not need a debugger.

🔴 THE SEED IS PART OF THE MEASUREMENT AND IS KNIFED (K-LE6). Without
`PSET(7,4)` a row whose answer is "nothing moved" is indistinguishable from a
row whose answer is (0,0).

THE ROW CLASSES:

  m.*  THE MODE ORDERING — the filed row's real class. The same LINE in SCREEN
       0/1/3, with the fault walked from the first coordinate to the colour to
       the box keyword. If a fault AFTER both coordinates still outranks the
       mode refusal, the refusal is at the DRAW and not at the entry.
  t.*  A TYPE fault in each of the four coordinate slots, in a colour, through
       STEP, and through the '-'-continuation form. SCREEN 2, so the mode
       question is out of the way and only the position varies.
  o.*  A DEFERRED NUMERIC fault in each slot, in all three distinct codes
       (11/6/5), plus the D-EVALCHK rows: a value that BOTH faults and
       overflows the int16 coercion reports whichever the routine consults
       first, and 70000+0*SQR(-1) -> 5 rather than 11 is what says the rule is
       "the expression's fault wins" and not "division by zero is special".
  c.*  THE COORDINATE DOMAIN — the int16 and byte edges, off-screen (legal, a
       silent no-op per spec §11.4), and the fractional boundary.
  k.*  THE COLOUR DOMAIN — zerobas masks with `and $0F` and raises nothing;
       CIRCLE/PAINT use a stricter 0..15 test. Which one does LINE use?
  a.*  THE ARGUMENT-LIST SHAPE — every place the grammar can END where a value
       was required (D-SCRERR found all four of SCREEN's are ERR 24, and
       nothing has ever checked whether LINE agrees), every missing delimiter,
       and the ,B/,BF suffixes as the accepting controls.
  p.*  PAINT'S OFF-SCREEN SEED versus ITS WRONG-MODE REFUSAL — the residual
       D-LINERR filed and did not run (spec-basic-lineerr.md §8.2). BOTH raise
       ERR 5, so the CODE cannot say which fired; only the WORK AREA can,
       because D-LINERR's fix writes it BETWEEN the two. See the block above
       CASES for what each row can and cannot distinguish.
  n.*  NEGATIVE CONTROLS, each agreeing for a reason INDEPENDENT of the claim.
  u.*  THE UNTRAPPED FACE: message text, its line, printed once, and whether
       the following line ran.

🟢 THE POSITIVE CONTROL FOR THE (X,Y) INSTRUMENT IS `m.s2.ok`. A clean
`LINE (11,12)-(20,21)` in SCREEN 2 must read ` 0 , 20 , 21 `: that proves the
GRPAC pair tracks the statement AND that the PSET(7,4) seed is overwritten by a
LINE that completes. It contains no reject at all, so it cannot fail because
this slice's ordering claim is wrong.

⚠️ Every row is a STORED program driven by `RUN`. In direct mode an abort on one
line does not stop the next.

Clean-room: observed screen output only; both reference ROMs are black boxes.
GRPACX/GRPACY and SCRMOD are published MSX system-variable addresses, not a
disassembly.
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lib"))
import omsx_repl                                                 # noqa: E402
import probe_report                                              # noqa: E402

ZB_MACHINE = os.environ.get("ZEROBAS_BASIC_MACHINE",
                            "C-BIOS_MSX1_EU_REPACK_DISK")
REPO = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
TEST_DSK = os.path.join(REPO, "disk", "test720.dsk")

SIDES = {
    "vg8020": dict(machine="Philips_VG_8020", boot=8.0, step=2.5,
                   reset=("NEW", "CLS"), diska=False),
    "cf3300": dict(machine="National_CF-3300", boot=14.0, step=4.5,
                   reset=("", "SCREEN 0", "NEW", "CLS"), diska=True),
    "zb":     dict(machine=ZB_MACHINE, boot=8.0, step=2.5,
                   reset=("NEW", "CLS"), diska=True),
}

# 🔴 THE SEED IS PART OF THE MEASUREMENT. `PSET(7,4)` gives GRPAC a value that no
# row's own coordinates can produce, so "the statement moved the last-referenced
# point" and "it did not" are DIFFERENT readings rather than both reading 0.
# `SCREEN 2` is needed for the PSET itself; rows that want another mode append
# their own `:SCREEN n` AFTER it, which is why the seed is a per-row string and
# not a constant. Q$ holds a string so the t.* rows are a TYPE fault and not an
# empty-variable one.
#
# Line 50's `SCREEN 0` is what makes the PRINT readable after a row that left the
# machine in SCREEN 2 or 3, and it CLEARS the screen, so the only '[' the reader
# can find is the printed one. X and Y are captured BEFORE it, on both paths.
TRAP_PROG = [
    "10 ON ERROR GOTO 100",
    '20 Q${seed}',
    "30 {stmt}",
    "40 E=0:X=PEEK({x0})+256*PEEK({x1}):Y=PEEK({y0})+256*PEEK({y1})",
    '50 SCREEN 0:PRINT"[";E;",";X;",";Y;"]":END',
    "100 E=ERR:X=PEEK({x0})+256*PEEK({x1}):"
    "Y=PEEK({y0})+256*PEEK({y1}):RESUME 50",
]

# The two halves of the graphics work area, both published MSX system-variable
# addresses (basic/sysvars.inc cites them for zerobas's own use; the identical
# reads already ship in basic_probe_graphics.py phases D/F).
#   GRPACX/GRPACY  the LAST-REFERENCED point -- what STEP and a bare `LINE -(x,y)`
#                  resolve against, i.e. the one with BASIC-visible consequences
#   GXPOS/GYPOS    the PENDING pixel target
# spec-basic-graphics-g3.md §11.5 says a LINE sets BOTH to p2. Every row reads
# GRPAC unless it is listed in GXPOS_ROWS below -- the w.* class, which exists
# because a fix that moves one half and not the other would be invisible to a
# GRPAC-only reading.
GRPAC_RD = dict(x0="&HFCB7", x1="&HFCB8", y0="&HFCB9", y1="&HFCBA")
GXPOS_RD = dict(x0="&HFCB3", x1="&HFCB4", y0="&HFCB5", y1="&HFCB6")
# ⚠️ NO SCREEN SEED IN THE UNTRAPPED TEMPLATE. `screen_tail` anchors on the
# echoed `RUN`, and any mode change clears it -- so a seed would blind every
# untrapped row on every side, including the references. That costs nothing
# here: SCREEN 0 is the boot mode, so the untrapped rows are exactly the
# wrong-mode rows, which is the class this slice is about.
UNTRAP_PROG = [
    '10 Q$="A"',
    "20 {stmt}",
    '30 PRINT"[RANON]"',
]

# The per-row seed tails. S2 is the plain one; the others select a mode AFTER
# the PSET, so GRPAC is seeded in every row regardless of the mode under test.
S2 = '="A":SCREEN 2:PSET(7,4)'
S0 = '="A":SCREEN 2:PSET(7,4):SCREEN 0'
S1 = '="A":SCREEN 2:PSET(7,4):SCREEN 1'
S3 = '="A":SCREEN 2:PSET(7,4):SCREEN 3'

DZ = "0*(1/0)"          # -> 11 division by zero
S5 = "0*SQR(-1)"        # ->  5 illegal function call
OV = "0*(1E38*1E38)"    # ->  6 overflow
TM = "(Q$<5)"           # -> 13 type mismatch  (ers_rhs_mismatch site)
MT = "(5<Q$)"           # -> 13 type mismatch  (evr_mismatch, the OTHER site)

P1 = "(11,12)"          # the first endpoint every LINE row uses
P2 = "(20,21)"          # the second

# (label, kind, seed, statement)   kind: "t" trapped / "u" untrapped
CASES = [
    # === m.* THE MODE ORDERING — where does the wrong-mode refusal happen? ===
    # 🟢 the instrument's own control first: a clean LINE in the RIGHT mode.
    ("m.s2.ok",   "t", S2, f"LINE {P1}-{P2}"),
    # the base rule: the same statement in each mode LINE does not draw in.
    ("m.s0",      "t", S0, f"LINE {P1}-{P2}"),
    ("m.s1",      "t", S1, f"LINE {P1}-{P2}"),
    ("m.s3",      "t", S3, f"LINE {P1}-{P2}"),
    # 🔴 THE FILED ROW, in this probe's grammar. Everything else in m.* exists
    # to say whether it is one row or a class.
    ("m.s0.tm",   "t", S0, f"LINE {P1}-({TM},21)"),
    # ...and the same fault walked BACKWARDS to the first slot the statement
    # reads. If the mode refusal were merely "late", these two would differ.
    ("m.s0.tm1",  "t", S0, f"LINE ({TM},12)-{P2}"),
    ("m.s0.dz",   "t", S0, f"LINE {P1}-({DZ},21)"),
    ("m.s0.ov",   "t", S0, f"LINE {P1}-(70000,21)"),
    # 🔴 ...and FORWARDS, past both coordinates. A fault in the COLOUR or in the
    # box keyword is after everything the statement parses; if the references
    # still report it over the mode, the mode refusal is at the DRAW.
    ("m.s0.col",  "t", S0, f"LINE {P1}-{P2},{DZ}"),
    ("m.s0.colt", "t", S0, f"LINE {P1}-{P2},{TM}"),
    ("m.s0.box",  "t", S0, f"LINE {P1}-{P2},,Z"),
    # a GRAMMAR fault (no value anywhere) in the wrong mode: which verdict?
    ("m.s0.syn",  "t", S0, f"LINE {P1}"),
    ("m.s0.dash", "t", S0, f"LINE {P1}-"),
    ("m.s0.bare", "t", S0, "LINE"),
    # the continuation form in the wrong mode: p1 comes from GRPAC, so this is
    # the one wrong-mode row whose first endpoint is not parsed at all.
    ("m.s0.cont", "t", S0, f"LINE -{P2}"),
    # a fully valid box statement in the wrong mode -- the plain refusal.
    ("m.s0.bf",   "t", S0, f"LINE {P1}-{P2},1,BF"),
    # does the answer depend on WHICH wrong mode? (SCREEN 1 has sprites and a
    # name table; SCREEN 0 has neither.)
    ("m.s1.tm",   "t", S1, f"LINE {P1}-({TM},21)"),
    ("m.s1.dz",   "t", S1, f"LINE {P1}-({DZ},21)"),

    # === t.* A TYPE FAULT IN EACH SLOT (SCREEN 2 — mode question out of the way)
    ("t.x1",      "t", S2, f"LINE ({TM},12)-{P2}"),
    ("t.y1",      "t", S2, f"LINE (11,{TM})-{P2}"),
    ("t.x2",      "t", S2, f"LINE {P1}-({TM},21)"),
    ("t.y2",      "t", S2, f"LINE {P1}-(20,{TM})"),
    # the OTHER mismatch site (evr_mismatch), and a bare string variable, which
    # reaches the type fault without a relational at all.
    ("t.mt",      "t", S2, f"LINE {P1}-({MT},21)"),
    ("t.strv",    "t", S2, f"LINE {P1}-(Q$,21)"),
    ("t.col",     "t", S2, f"LINE {P1}-{P2},Q$"),
    # through STEP, and through the '-'-continuation form (p1 = last point).
    ("t.step",    "t", S2, f"LINE STEP({TM},12)-{P2}"),
    ("t.cont",    "t", S2, f"LINE -({TM},21)"),

    # === o.* A DEFERRED NUMERIC FAULT IN EACH SLOT ==========================
    ("o.x1.dz",   "t", S2, f"LINE ({DZ},12)-{P2}"),
    ("o.y1.dz",   "t", S2, f"LINE (11,{DZ})-{P2}"),
    ("o.x2.dz",   "t", S2, f"LINE {P1}-({DZ},21)"),
    ("o.y2.dz",   "t", S2, f"LINE {P1}-(20,{DZ})"),
    ("o.x2.s5",   "t", S2, f"LINE {P1}-({S5},21)"),
    ("o.x2.ov",   "t", S2, f"LINE {P1}-({OV},21)"),
    ("o.col.dz",  "t", S2, f"LINE {P1}-{P2},{DZ}"),
    # 🔴 THE ROWS THAT PICK THE ROUTINE. A value that BOTH faulted and overflows
    # the int16 coercion reports whichever is consulted first. o.ov5 is the one
    # that says the rule is "a fault that already happened outranks the
    # coercion" and not "division by zero is special": a DIFFERENT code, 5.
    ("o.ovdz",    "t", S2, f"LINE {P1}-(70000+{DZ},21)"),
    ("o.ov5",     "t", S2, f"LINE {P1}-(70000+{S5},21)"),
    ("o.x1.ovdz", "t", S2, f"LINE (70000+{DZ},12)-{P2}"),
    ("o.col.ovdz","t", S2, f"LINE {P1}-{P2},70000+{DZ}"),

    # === c.* THE COORDINATE DOMAIN =========================================
    # Off-screen is LEGAL and a silent no-op (spec §11.4) -- these are the rows
    # that say the domain rule is about int16 and not about the screen.
    ("c.300",     "t", S2, f"LINE {P1}-(300,21)"),
    ("c.neg",     "t", S2, f"LINE {P1}-(-1,21)"),
    ("c.32767",   "t", S2, f"LINE {P1}-(32767,21)"),
    ("c.32768",   "t", S2, f"LINE {P1}-(32768,21)"),
    ("c.m32768",  "t", S2, f"LINE {P1}-(-32768,21)"),
    ("c.m32769",  "t", S2, f"LINE {P1}-(-32769,21)"),
    ("c.70000",   "t", S2, f"LINE {P1}-(70000,21)"),
    ("c.ovy2",    "t", S2, f"LINE {P1}-(20,70000)"),
    ("c.ovx1",    "t", S2, f"LINE (70000,12)-{P2}"),
    ("c.ovy1",    "t", S2, f"LINE (11,70000)-{P2}"),
    # truncate or round? GRPAC answers it: 20.6 lands on 20 or on 21.
    ("c.frac",    "t", S2, f"LINE {P1}-(20.6,21.6)"),

    # === k.* THE COLOUR DOMAIN =============================================
    # zerobas masked (`and $0F`, so 16 became 0 silently) at LINE *and* at PSET;
    # CIRCLE and PAINT use a strict 0..15 (gfx_store_colour_checked). Neither
    # LINE's nor PSET's colour had ever been measured.
    ("k.15",      "t", S2, f"LINE {P1}-{P2},15"),
    ("k.16",      "t", S2, f"LINE {P1}-{P2},16"),
    ("k.neg",     "t", S2, f"LINE {P1}-{P2},-1"),
    ("k.255",     "t", S2, f"LINE {P1}-{P2},255"),
    ("k.big",     "t", S2, f"LINE {P1}-{P2},70000"),
    ("k.frac",    "t", S2, f"LINE {P1}-{P2},1.6"),
    ("k.b16",     "t", S2, f"LINE {P1}-{P2},16,B"),
    # 🟢 THE ROW THAT KEEPS THE COLOUR FIX HONEST. zerobas masks PSET's colour
    # too, where CIRCLE/PAINT range-check 0..15. If LINE turns out to
    # range-check, that is an asymmetry between siblings, and this row is what
    # says the asymmetry is the REFERENCE's and not something this slice
    # introduced by "fixing" LINE into agreement with the wrong sibling.
    # 🔴 THIS COMMENT USED TO SAY THE MASK WAS "documented ... measured on the
    # VG-8020 (spec-basic-graphics-g2.md §11.9)". IT IS NOT AND IT WAS NOT.
    # spec-basic-graphics-g2.md has no §11.9 -- it has no §11 at all; its §11
    # references point into the ARC spec, whose §11.9 is about token
    # re-verification. The mask was own design whose code comment said "see G2
    # gate note", and no such note exists either. A citation that does not
    # resolve got UPGRADED into a measurement on the way to its second reader,
    # and `k.pset16` is what finally asked the machine. See
    # docs/spec-basic-lineerr.md §5.1.
    ("k.pset16",  "t", S2, "PSET(20,21),16"),

    # === a.* THE ARGUMENT-LIST SHAPE =======================================
    # D-SCRERR found every SCREEN slot that ENDS where a value was required is
    # ERR 24 (Missing operand), not ERR 2. Nothing has checked LINE.
    ("a.bare",    "t", S2, "LINE"),
    ("a.p1",      "t", S2, f"LINE {P1}"),
    ("a.dash",    "t", S2, f"LINE {P1}-"),
    ("a.dashc",   "t", S2, f"LINE {P1}-:V=1"),
    ("a.nox",     "t", S2, f"LINE (,12)-{P2}"),
    ("a.noy",     "t", S2, f"LINE (11,)-{P2}"),
    ("a.nocomma", "t", S2, f"LINE (11 12)-{P2}"),
    ("a.noclose", "t", S2, f"LINE (11,12-{P2}"),
    ("a.noparen", "t", S2, f"LINE 11,12-{P2}"),
    ("a.trailc",  "t", S2, f"LINE {P1}-{P2},"),
    # 🔴 a.trailc is ERR 24 on both references, which is D-SCRERR's Missing-
    # operand rule turning up at a second verb. These two say how WIDE that
    # rule is -- whether a `:` counts as "the list ended" the way end-of-line
    # does, at the colour slot and at the box slot. Without them the guard's
    # `cp ':'` arm would be an assumption copied from ex_screen's shape.
    ("a.trailcolon", "t", S2, f"LINE {P1}-{P2},:V=1"),
    ("a.boxcolon", "t", S2, f"LINE {P1}-{P2},1,:V=1"),
    ("a.badbox",  "t", S2, f"LINE {P1}-{P2},,Z"),
    ("a.boxc",    "t", S2, f"LINE {P1}-{P2},1,"),
    # 🟢 the ACCEPTING controls for the same grammar -- without these the a.*
    # class only says what is refused, never that the form is reachable.
    ("a.b",       "t", S2, f"LINE {P1}-{P2},,B"),
    ("a.bf",      "t", S2, f"LINE {P1}-{P2},,BF"),
    ("a.cb",      "t", S2, f"LINE {P1}-{P2},1,B"),
    ("a.cont",    "t", S2, f"LINE -{P2}"),
    ("a.step",    "t", S2, "LINE STEP(1,1)-STEP(2,2)"),
    ("a.colon",   "t", S2, f"LINE {P1}-{P2}:V=1"),

    # === v.* THE SAME ORDERING QUESTION AT THE SIBLING VERBS ================
    # 🔴 THIS CLASS EXISTS BECAUSE A NEGATIVE CONTROL DIVERGED. `n.pset0` was
    # written as "the wrong-mode rule at a DIFFERENT verb, which this slice
    # claims nothing about" and came back ' 5 , 20 , 21 ' / ' 5 , 7 , 4 ' -- the
    # SAME divergence as LINE's. So the mode precheck is not LINE's; it is
    # `gfx_err5`'s callers', and a fix that moves LINE alone would ship a
    # partial rule. Every resident graphics verb with a SCRMOD precheck is
    # therefore measured here, in the wrong mode, plain and with a fault.
    ("v.pset0",   "t", S0, "PSET(20,21)"),
    ("v.preset0", "t", S0, "PRESET(20,21)"),
    ("v.pset0.tm", "t", S0, f"PSET({TM},21)"),
    ("v.pset0.col", "t", S0, f"PSET(20,21),{DZ}"),
    ("v.circ0",   "t", S0, "CIRCLE(20,21),5"),
    ("v.circ0.tm", "t", S0, f"CIRCLE({TM},21),5"),
    ("v.circ0.r", "t", S0, f"CIRCLE(20,21),{DZ}"),
    ("v.paint0",  "t", S0, "PAINT(20,21)"),
    ("v.paint0.tm", "t", S0, f"PAINT({TM},21)"),
    # 🎯 THE ROWS THAT SITE EACH VERB'S GATE EXACTLY. For LINE and PSET the
    # measurement says the gate is between the MANDATORY arguments and the
    # OPTIONAL ones (a coordinate fault wins, a colour fault does not). CIRCLE
    # has TWO mandatory arguments (centre and radius) and PAINT has one, so
    # "after the mandatory ones" and "after everything" are different sites at
    # those two verbs and only these rows tell them apart -- which is the
    # difference between a pure MOVE and a coroutine rewrite.
    ("v.circ0.c", "t", S0, f"CIRCLE(20,21),5,{DZ}"),
    ("v.circ0.rt", "t", S0, f"CIRCLE(20,21),{TM}"),
    ("v.paint0.c", "t", S0, f"PAINT(20,21),{DZ}"),
    # ...and their SCREEN-2 twins, which say where the work area stands when the
    # option list faults in the mode where the statement is legal.
    ("v.pset2.col", "t", S2, f"PSET(20,21),{DZ}"),
    ("v.circ2.c", "t", S2, f"CIRCLE(20,21),5,{DZ}"),
    ("v.paint2.c", "t", S2, f"PAINT(20,21),{DZ}"),
    # the SCREEN-3 face of the same whole-feature gap m.s3 shows for LINE.
    ("v.pset3",   "t", S3, "PSET(20,21)"),
    ("v.draw0",   "t", S0, 'DRAW"U10"'),
    # 🟢 POINT has NO mode precheck by construction (spec §11.8 / G2-e: it works
    # in any mode), so it is the control that says the v.* divergences are about
    # the PRECHECK and not about "graphics in SCREEN 0" generally.
    ("v.point0",  "t", S0, "V=POINT(20,21)"),

    # === p.* PAINT'S OFF-SCREEN SEED versus ITS WRONG-MODE REFUSAL =========
    # 🔴 THE RESIDUAL D-LINERR FILED AND DID NOT RUN (spec-basic-lineerr.md
    # §8.2). `PAINT` answers ERR 5 to an off-screen seed AND to a wrong SCREEN
    # mode, so the code is blind to which one fired. Name the three events:
    #
    #     A = the WORK-AREA write   B = the MODE gate   C = the SEED range test
    #
    # D-LINERR pinned A < B (`v.paint0.c`: `PAINT(20,21),0*(1/0)` in SCREEN 0
    # is ERR 5 with GRPAC already on (20,21)). C was never sited against either:
    # `ex_paint` tests the seed FIRST because that is where G5 put it, and
    # spec-basic-graphics-g5.md §5's off-screen rule is a VG-8020 pin of the
    # ERROR CODE only (§11 C6) — it never asked where the work area stood.
    #
    # ⚠️ WHAT THESE ROWS CAN AND CANNOT DECIDE. C-vs-A is observable: a seed
    # that never reaches A leaves GRPAC on the (7,4) seed, one that passes it
    # leaves GRPAC on the raw unclipped coordinate (§4.4 of the notebook: LINE
    # already stores 300 as 300 and -1 as 65535). C-vs-B is NOT observable
    # through this instrument and no row here claims it: when a seed is BOTH
    # off-screen AND in the wrong mode, B and C raise the same code with the
    # same work area whichever runs first. So the measurable question is
    # "does the work area move before the off-screen refusal", and the answer
    # puts C below A — which, A and B being one `call gfx_point_gate`, puts it
    # below the gate. The residual is settled to exactly that extent.
    #
    # 🔴 NOT ADDED, DELIBERATELY: the SCREEN-3 face. Both references DRAW in
    # SCREEN 3 (rows m.s3 / v.pset3) but an off-screen seed refuses there too,
    # so `PAINT(300,100)` in SCREEN 3 would be ERR 5 on all three sides — a row
    # that AGREES for the WRONG REASON (zerobas's `cp 2`, the references' seed
    # test). A green row bought that way is worse than no row.
    ("p.off0",    "t", S0, "PAINT(300,100)"),
    # ...and the same statement in the mode where PAINT is LEGAL, so only C can
    # fire. THIS is the row that sites C against A with no mode confound.
    ("p.off2",    "t", S2, "PAINT(300,100)"),
    ("p.off1",    "t", S1, "PAINT(300,100)"),
    # the domain, so the class is not one coordinate: y past 191 but still a
    # legal byte, and the negative face (which §4.4 says reads back as 65535).
    ("p.oy0",     "t", S0, "PAINT(20,200)"),
    ("p.oy2",     "t", S2, "PAINT(20,200)"),
    ("p.neg0",    "t", S0, "PAINT(-1,100)"),
    ("p.neg2",    "t", S2, "PAINT(-1,100)"),
    ("p.negy2",   "t", S2, "PAINT(20,-1)"),
    # 🎯 THE EDGE, PINNED FROM BOTH SIDES. p.edge2 is the LAST on-screen point
    # and must be ACCEPTED; these two are its off-by-one neighbours in each
    # axis. Without p.edge2 the domain is claimed from outside only, and
    # "everything refuses" would score green.
    ("p.x256",    "t", S2, "PAINT(256,191)"),
    ("p.y192",    "t", S2, "PAINT(255,192)"),
    # 🟢 the coercion still outranks BOTH: past int16 is ERR 6 with the work
    # area unmoved, exactly as at LINE's `c.70000` / `k.big`.
    ("p.ov0",     "t", S0, "PAINT(70000,100)"),
    # the work area takes the RESOLVED point, not the literal: STEP off (7,4).
    ("p.step0",   "t", S0, "PAINT STEP(300,100)"),
    # 🟢 THE ACCEPTING CONTROLS. Both draw their own bounded box FIRST and
    # leave GRPAC on the box's SECOND endpoint, so the reading can only be the
    # seed if PAINT itself wrote it. Neither contains a reject, so no ordering
    # claim can make them fail — and without them every p.* row above is a
    # refusal, which a machine where PAINT does nothing at all would also pass.
    ("p.ok2",     "t", S2, "LINE(30,30)-(10,10),15,B:PAINT(20,20)"),
    ("p.edge2",   "t", S2, "LINE(255,191)-(250,186),15,B:PAINT(255,191)"),

    # === g.* `gfx_in_range`'s DOMAIN AT ITS **SILENT** CALLERS =============
    # 🔴 D-PAINTSEED pinned the 0..255 x 0..191 domain at `ex_paint` — the ONE
    # caller that RAISES. The same leaf decides a SILENT outcome at the other
    # two, and a shared engine's other callers are exactly what a fix (or a
    # pin) must measure [[a-shared-engine-fix-must-measure-its-other-callers]]:
    #
    #   gfx_plot_go (PSET/PRESET)  off-screen -> no plot, work area ALREADY moved
    #   ev_f_point  (POINT)        off-screen -> -1
    #
    # POINT's RETURN VALUE is read into this probe's existing instrument as
    # `PSET(V+1,V+1)`: -1 lands the work area on (0,0), a colour c on (c+1,c+1).
    # The +1 keeps it on the ACCEPTED PSET path, so the encoding does not lean
    # on the clip rule the g.ps.* rows are testing.
    ("g.ps.off",  "t", S2, "PSET(300,100)"),
    ("g.ps.x256", "t", S2, "PSET(256,191)"),
    ("g.ps.y192", "t", S2, "PSET(255,192)"),
    ("g.ps.edge", "t", S2, "PSET(255,191)"),
    ("g.ps.neg",  "t", S2, "PSET(-1,100)"),
    ("g.pr.off",  "t", S2, "PRESET(300,100)"),
    ("g.pt.off",  "t", S2, "V=POINT(300,100):PSET(V+1,V+1)"),
    ("g.pt.x256", "t", S2, "V=POINT(256,191):PSET(V+1,V+1)"),
    ("g.pt.y192", "t", S2, "V=POINT(255,192):PSET(V+1,V+1)"),
    ("g.pt.neg",  "t", S2, "V=POINT(-1,100):PSET(V+1,V+1)"),
    # 🟢 …and the two rows that say POINT returns a REAL COLOUR and not just
    # -1-or-0, without which every row above agrees with a POINT that is broken
    # in the same direction.
    ("g.pt.edge", "t", S2, "PSET(255,191):V=POINT(255,191):PSET(V+1,V+1)"),
    ("g.pt.clear", "t", S2, "V=POINT(100,100):PSET(V+1,V+1)"),
    # POINT does not move the LAST-REFERENCED point, plain or through STEP.
    ("g.pt.on",   "t", S2, "V=POINT(20,21)"),
    ("g.pt.step", "t", S2, "V=POINT STEP(1,1)"),

    # === w.* THE OTHER HALF OF THE WORK AREA ===============================
    # Identical statements to rows above, read through GXPOS/GYPOS instead of
    # GRPACX/GRPACY. spec-basic-graphics-g3.md §11.5 claims a LINE sets both to
    # p2; if a wrong-mode LINE moves one and not the other, a GRPAC-only row set
    # cannot see it -- and a fix sited at either half would be scored by rows
    # that never look at the other.
    ("w.s2",      "t", S2, f"LINE {P1}-{P2}"),
    ("w.s0",      "t", S0, f"LINE {P1}-{P2}"),
    ("w.s0.tm",   "t", S0, f"LINE {P1}-({TM},21)"),
    ("w.s2.col",  "t", S2, f"LINE {P1}-{P2},{DZ}"),
    # 🔴 …and the p.* rows' GXPOS twins. `gfx_work_area` writes both halves
    # together, so zerobas CANNOT split them — but that is the claim, not the
    # evidence: K-LE3 found LINE's p1 staging writing only GRPAC, on a row whose
    # GRPAC twin was already green. The references are black boxes and get the
    # same two-halves reading here that they got there.
    ("w.paint0.off", "t", S0, "PAINT(300,100)"),
    ("w.paint2.off", "t", S2, "PAINT(300,100)"),
    # 🔴 …AND THE HALF `v.point0` CANNOT SEE. `ev_f_point`'s own comment says
    # "POINT is READ-ONLY: it resolves STEP against the last point but does NOT
    # move it" — and three lines below it writes GXPOS/GYPOS as the tenant's
    # marshal target, on the ON-SCREEN path only. `v.point0` reads GRPAC, which
    # POINT provably does not touch on either side, so that row is blind to the
    # claim its own comment makes. If a reference's coordinate scan writes GXPOS
    # BEFORE the range test — which is exactly what D-PAINTSEED just measured
    # `PAINT` doing — then `w.pt.off` diverges and zerobas's write is on the
    # wrong side of the test. This is K-LE3's shape a third time.
    ("w.pt.on",   "t", S2, "V=POINT(20,21)"),
    ("w.pt.off",  "t", S2, "V=POINT(300,100)"),
    ("w.pt.step", "t", S2, "V=POINT STEP(1,1)"),
    ("w.ps.off",  "t", S2, "PSET(300,100)"),

    # === n.* NEGATIVE CONTROLS =============================================
    ("n.zork",    "t", S2, "ZORK 1,2"),
    ("n.dzw",     "t", S2, f"WIDTH {DZ}+1"),
    ("n.tmw",     "t", S2, "WIDTH Q$"),

    # === u.* THE UNTRAPPED FACE ============================================
    # No seed, so these run in the boot mode -- SCREEN 0, i.e. exactly the
    # wrong-mode class, for free.
    ("u.s0",      "u", "", f"LINE {P1}-{P2}"),
    ("u.s0.tm",   "u", "", f"LINE {P1}-({TM},21)"),
    ("u.s0.dz",   "u", "", f"LINE {P1}-({DZ},21)"),
    ("u.s0.col",  "u", "", f"LINE {P1}-{P2},{DZ}"),
    ("u.bare",    "u", "", "LINE"),
    ("u.zork",    "u", "", "ZORK 1,2"),
]

# 🟢 POSITIVE CONTROLS, both readings covered. 🔴 EVERY ONE IS FIXED BY
# SOMETHING OTHER THAN THIS SLICE'S CLAIM.
CONTROLS = ("m.s2.ok", "n.zork", "n.dzw", "u.zork")

CONTROL_WANT = {
    # the (X,Y) INSTRUMENT itself: a clean LINE in SCREEN 2 over a PSET(7,4)
    # seed. No reject anywhere in the row, so no ordering claim can make it
    # fail; if GRPAC did not track the statement this reads (7,4).
    "m.s2.ok": " 0 , 20 , 21 ",
    # a genuine syntax error in a statement that is not LINE: ERR 2, and the
    # seeded last-referenced point is untouched.
    "n.zork":  " 2 , 7 , 4 ",
    # an ordinary numeric fault at a reader that checked long before this slice.
    "n.dzw":   " 11 , 7 , 4 ",
    # the untrapped reading -- ONE message, naming its line, line 30 skipped.
    "u.zork":  "Syntax error in 20",
}

NEGATIVE = {
    "m.s2.ok": "NEGATIVE CONTROL — the (X,Y) instrument: a clean LINE completes",
    "k.15":    "NEGATIVE CONTROL — an in-domain colour is accepted",
    "c.300":   "NEGATIVE CONTROL — off-screen is LEGAL (a silent no-op)",
    "a.b":     "NEGATIVE CONTROL — the ,B form is reachable and accepted",
    "a.cont":  "NEGATIVE CONTROL — the '-' continuation form is accepted",
    "w.s2":    "NEGATIVE CONTROL — the GXPOS instrument: a drawn LINE moves it",
    "p.ok2":   "NEGATIVE CONTROL — a legal PAINT completes and the SEED is what "
               "lands in the work area (the box left it elsewhere)",
    "p.edge2": "NEGATIVE CONTROL — (255,191) is ON-screen: the domain edge from "
               "INSIDE, so p.x256/p.y192 are an edge and not 'all refuse'",
    "g.ps.edge": "NEGATIVE CONTROL — the same edge from inside at the SILENT "
                 "caller: (255,191) plots",
    "g.pt.edge": "NEGATIVE CONTROL — POINT returns a REAL COLOUR (15+1), not "
                 "just -1-or-0, so the g.pt.* readings mean something",
    "g.pt.clear": "NEGATIVE CONTROL — POINT reads the BACKGROUND (4+1) on an "
                  "untouched pixel",
    "n.zork":  "NEGATIVE CONTROL — a syntax error outside LINE stays ERR 2",
    "n.dzw":   "NEGATIVE CONTROL — one numeric fault at a checking reader",
    "n.tmw":   "NEGATIVE CONTROL — a type fault at a checking reader is 13",
    "v.point0": "NEGATIVE CONTROL — POINT has no precheck: not 'graphics in "
                "SCREEN 0' generally",
    "u.zork":  "NEGATIVE CONTROL — the untrapped reading itself",
}
LABEL_W = 12

_S3 = ("DEFERRED — SCREEN 3 (multicolour) DRAWS on both references; zerobas "
       "has no SCREEN-3 pixel op at all, so its `cp 2` refuses the mode. A "
       "WHOLE-FEATURE gap (a second rasteriser, a second address/clash model), "
       "not an error-surface defect: this slice moved WHERE the refusal "
       "happens, and the refusal itself is correct for every mode zerobas "
       "implements. Measured, priced at nothing, filed in TODO.md")

DEFERRED: dict[str, str] = {
    # Measured, not scored, each with the reason it is out of this slice's reach.
    "m.s3": _S3,
    "v.pset3": _S3,
}

SENTINELS = ("<NO CAPTURE>", "<NO ECHO>")


def clip_at_prompt(tail: str) -> str:
    """Drop everything from the first row that BEGINS with a prompt token.

    zerobas emits `ZB` with no trailing newline, so the prompt shares a row with
    the next echoed line and `omsx_repl.screen_tail`'s own prompt terminator
    never fires on zb (D-ONERR0, docs/onerr0-msx1-characterization.md §3.1)."""
    out = []
    for row in tail.split("|"):
        if any(row.startswith(p) for p in omsx_repl.PROMPTS):
            break
        out.append(row)
    return "|".join(out)


GXPOS_ROWS = frozenset(("w.s2", "w.s0", "w.s0.tm", "w.s2.col",
                        "w.paint0.off", "w.paint2.off",
                        "w.pt.on", "w.pt.off", "w.pt.step", "w.ps.off"))

# 🔴 A ROW THAT IS MERELY SLOW READS AS A DIVERGENCE, AND DID. `c.32767` and
# `c.m32768` came back `<NO CAPTURE>` on zb in the first sweep and would have
# been written up as two more defects. They are not: at a longer window zerobas
# answers EXACTLY what both references answer (` 0 , 32767 , 21 ` and
# ` 0 , 32768 , 21 `). The cause is a documented DESIGN choice, not a fault --
# the tenant rasterises over the TRUE int16 endpoints and masks per pixel, that
# per-pixel mask BEING the clip (spec-basic-graphics-g3.md §3.4/§4.4), so a
# 32767-pixel span really is walked pixel by pixel where the references clip
# first and walk ~250. It is a speed difference, and this probe measures error
# surfaces, so the window is widened for those two rows rather than the finding
# being mis-filed. Measured: 2.5 s no, 12 s yes, 40 s identical to 12 s.
SLOW_ROWS = {"c.32767": 12.0, "c.m32768": 12.0}


def program(label: str, kind: str, seed: str, stmt: str) -> list[str]:
    tpl = TRAP_PROG if kind == "t" else UNTRAP_PROG
    rd = GXPOS_RD if label in GXPOS_ROWS else GRPAC_RD
    return [ln.format(stmt=stmt, seed=seed, **rd) for ln in tpl]


def read_case(kind: str, raw: str | None) -> str:
    if raw is None:
        return "<NO CAPTURE>"
    if kind == "t":
        v = omsx_repl.result_span(raw)
        return "<NO CAPTURE>" if v is None else v
    t = omsx_repl.screen_tail(raw, "RUN")
    return "<NO ECHO>" if t is None else clip_at_prompt(t)


def run_side(side: str, only: list[str]) -> dict:
    cfg = SIDES[side]
    out = {}
    for label, kind, seed, stmt in CASES:
        if only and label not in only:
            continue
        kw = {}
        if cfg["diska"]:
            dsk = os.path.join(tempfile.gettempdir(),
                               f"zb_line_{side}_{label}.dsk")
            shutil.copy(TEST_DSK, dsk)
            kw["diska"] = dsk
        lines = list(cfg["reset"]) + program(label, kind, seed, stmt) + ["RUN"]
        step = max(cfg["step"], SLOW_ROWS.get(label, 0.0))
        caps = omsx_repl.run_cases(
            cfg["machine"], [("direct", lines)],
            batch=False, boot=cfg["boot"], step=step, **kw)
        out[label] = read_case(kind, caps[0])
    return out


DENOMINATOR = (
    "(WHERE IN `LINE` A FAULT HAPPENS) x (WHAT KIND OF FAULT IT IS), crossed "
    "with the SCREEN MODE. The POSITION axis is swept structurally rather than "
    "sampled: LINE's grammar is `LINE [[STEP](x1,y1)] - [STEP](x2,y2) "
    "[,[c][,B|BF]]`, so every slot that reaches a VALUE is x1, y1, x2, y2 and "
    "c -- all five carry a type fault (t.*) and the first four plus c carry a "
    "deferred numeric one (o.*) -- and every slot that can END where a value "
    "was required is swept by a.* (bare, p1 only, a bare '-', an empty x or y, "
    "a trailing comma after the colour, and a box field with no keyword), which "
    "is every path through ex_line_gfx and parse_coord. The FAULT axis is the "
    "four distinct pending codes 11/6/5/13 (each contributing 0 so the row "
    "says WHICH fault survived), plus the coercion's own ERR 6 alone and "
    "TOGETHER with a pending code -- the pair that says which of the two is "
    "consulted first. The MODE axis is complete for an MSX1: 0, 1, 2, 3. The "
    "VALUE domain sweeps the int16 edges (32767/32768, -32768/-32769), past "
    "int16 (70000), off-screen-but-legal (300, -1), and the fractional "
    "boundary in a slot where truncate-vs-round is visible in GRPAC. NOT "
    "swept: what LINE DRAWS once it is accepted (`make graphics-acceptance` "
    "owns that, spec-basic-graphics-g3.md), the box tenant's clipping, and "
    "PAINT/CIRCLE's own colour domains (spec-basic-graphics-g4/g5)."
)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="D-LINERR: LINE's wrong-mode refusal, and its whole error "
                    "surface")
    ap.add_argument("--sides", default="vg8020,cf3300,zb")
    ap.add_argument("--only", default="")
    ap.add_argument("--gate", action="store_true",
                    help="exit 1 unless every row agrees across sides")
    a = ap.parse_args()

    sides = [s for s in a.sides.split(",") if s]
    only = [o for o in a.only.split(",") if o]
    for s in sides:
        if s not in SIDES:
            sys.stderr.write(f"unknown side {s!r}\n")
            return 2

    results = {s: run_side(s, only) for s in sides}
    present = [lab for lab, _, _, _ in CASES
               if any(lab in results[s] for s in sides)]

    print("D-LINERR — LINE's SCREEN-mode refusal is the LAST thing it does    "
          f"sides: {', '.join(sides)}")
    print("=" * 78)

    bad = []
    for ctl in CONTROLS:
        if ctl not in present:
            continue
        for s in sides:
            got = results[s].get(ctl)
            if got != CONTROL_WANT[ctl]:
                bad.append((ctl, s, got))
    if bad:
        for lab, s, got in bad:
            print(probe_report.row("FAIL", lab, LABEL_W, {s: got},
                                   "   [POSITIVE CONTROL]"))
            print(f"        wanted {CONTROL_WANT[lab]!r}")
        print("\n*** A POSITIVE CONTROL FAILED, so nothing below it was "
              "measured.\n"
              "    m.s2.ok = the (X,Y) INSTRUMENT — GRPACX/GRPACY track the "
              "statement, and\n"
              "              a LINE that COMPLETES overwrites the PSET(7,4) "
              "seed. If this\n"
              "              is red, every X,Y reading below it is "
              "meaningless.\n"
              "    n.zork  = a syntax error OUTSIDE LINE is still ERR 2, and "
              "the seed holds.\n"
              "    n.dzw   = an ordinary numeric fault reports its OWN code "
              "(11).\n"
              "    u.zork  = the UNTRAPPED reading — ONE message, naming its "
              "line.\n"
              "    🔴 None of the four can fail because this slice's claim is "
              "wrong: three\n"
              "    contain no reject at all, and the fourth is not a LINE.\n"
              "    🔴 CLASSIFY BY WHICH SIDE FAILED: red on a REFERENCE is a "
              "broken fixture\n"
              "    (report it, score nothing); red on zb is an ordinary "
              "divergence that\n"
              "    belongs in the row set, not in the control set.\n"
              "    Check build/*.rom, `make repack-machine` and `make "
              "latch-check`, THEN\n"
              "    re-read the rows. Exit 2 (not 1) = the instrument was "
              "broken.")
        for lab in present:
            vals = {s: results[s][lab] for s in sides if lab in results[s]}
            print(probe_report.row("....", lab, LABEL_W, vals,
                                   "   (not scored)"))
        print(probe_report.footer(len(bad) + len(present), 0,
                                  "NOT MEASURED (a positive control failed)"))
        return 2

    if len(sides) < 2:
        n = 0
        for lab in present:
            for s in sides:
                if lab in results[s]:
                    print(probe_report.row("--", lab, LABEL_W,
                                           {s: results[s][lab]}))
                    n += 1
        print(probe_report.footer(n, 0, "CHARACTERIZATION (one side)"))
        print("=" * 78)
        print(f"{n} row(s) on {sides[0]} — no agreement verdict from one side")
        return 0

    agree = dis = refsplit = deferred = 0
    for lab in present:
        vals = {s: results[s][lab] for s in sides if lab in results[s]}
        ok = len(set(vals.values())) == 1 and len(vals) > 1
        if any(v in SENTINELS for v in vals.values()):
            ok = False
        refs = {vals[s] for s in ("vg8020", "cf3300") if s in vals}
        if lab in DEFERRED:
            deferred += 1
            print(probe_report.row("....", lab, LABEL_W, vals,
                                   f"   [{DEFERRED[lab]}]"))
            continue
        agree += ok
        dis += not ok
        note = "   [POSITIVE CONTROL]" if lab in CONTROLS else ""
        if lab in NEGATIVE:
            note = f"   [{NEGATIVE[lab]}]"
        if len(refs) > 1:
            refsplit += 1
            note += "   [REFERENCES DISAGREE — no oracle for this row]"
        print(probe_report.row("ok" if ok else "DIFF", lab, LABEL_W, vals, note))

    print(probe_report.footer(len(present), len(present) - deferred,
                              f"{agree} agree, {dis} diverge, "
                              f"{deferred} deferred (not scored)"))
    print("=" * 78)
    print(f"{agree}/{agree + dis} readings agree "
          f"({len(CASES)} cases, {len(CONTROLS)} positive controls, "
          f"{len(NEGATIVE)} negative controls, "
          f"{refsplit} row(s) with no oracle, "
          f"{len(DEFERRED)} DEFERRED row(s) measured but not scored)")
    print("READING: trapped rows are `[ ERR , GRPACX , GRPACY ]` — the error "
          "code and the LAST-REFERENCED POINT the statement left behind, "
          "captured in the handler over a `PSET(7,4)` seed. (7,4) = LINE moved "
          "nothing; (11,12) = the first endpoint was staged and it then died; "
          "(20,21) = it ran to completion. The w.* rows read GXPOS/GYPOS "
          "instead — the OTHER half of the work area, same statements. "
          "Untrapped rows are the clipped screen tail of `RUN`.")
    print("SIDES: vg8020,cf3300,zb — LINE, PSET, SCREEN, ON ERROR, ERR, RESUME "
          "and PEEK are core MSX-BASIC, present on every MSX1, so BOTH "
          "references are legitimate oracles for every row here")
    print("DENOMINATOR: " + DENOMINATOR)
    if a.gate and dis:
        sys.stderr.write(f"lineerr: {dis} reading(s) diverge\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
