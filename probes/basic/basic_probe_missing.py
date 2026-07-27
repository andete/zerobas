#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""LOCATE / SWAP / TRON / TROFF / MOTOR -- the MISSING class, characterised.

WHY THIS EXISTS
===============
docs/kwsweep-msx1-coverage.md classifies the 34 absent MSX1 reserved words into
SILENT-GAP (a wrong answer, no error), MISSING (an honest syntax error) and
NO-ORACLE. The SILENT-GAP class is now EMPTY (`2facfc0`). This probe measures
the whole of what remains that is a *slice* rather than an arc: the five MISSING
**statements**. `DEF FN`/`FN` is deliberately out of scope -- it is an arc
(a definition table, argument binding, re-entrant evaluation), not a slice.

These five are the OPPOSITE measurement problem from the SILENT-GAP words. There
the danger was that zerobas answered and the answer was wrong; here zerobas says
`syntax error` and everybody can see it. So the risk this probe manages is not
"is it wrong" but **"what exactly does the reference do"** -- and four of the
five have surfaces that are easy to guess wrong:

  LOCATE   three arguments, two of them OMITTABLE (`LOCATE ,3`), with a bound
           check whose limit is the *current WIDTH*, not 40.
  SWAP     the only statement in the language that writes TWO lvalues. Its type
           rule (must the two agree? at what granularity -- numeric vs string,
           or int vs sng vs dbl?) is not derivable from anything else.
  TRON     emits output *around* other statements. Its decoration format and,
           more importantly, its SCOPE (direct mode? does RUN reset it?) is
           pure convention.
  MOTOR    the only one whose whole effect is ELECTRICAL. See §MOTOR below --
           this probe measures its LANGUAGE surface and says so, rather than
           pretending a screen scrape can see a relay.

THE BRACKET CONVENTION COLLIDES WITH TRON -- ON PURPOSE, SO IT IS HANDLED
=========================================================================
Every other probe in this tree reads a value out of `PRINT "[";X;"]"`. The
reference's TRON decoration is *itself* bracketed (`[10][20]`), so a trace row
read through `result_span` would happily return a slice of the trace and call it
the answer. Trace rows therefore use a DIFFERENT readout (`screen`, the whole
collapsed screen after an in-program `CLS`) and never touch `result_span`.

THE INSTRUMENT IS PINNED BEFORE ANY POSITION IS COMPARED
========================================================
The cursor-cluster slice learned this the hard way: the two machines BOOT AT
DIFFERENT TEXT WIDTHS (reference 37, zerobas 39), and SCREEN 0 centres the text
area, so every absolute column is offset until `WIDTH 40` is pinned. Every
positional row here leads with `WIDTH 40:CLS:`. See
docs/cursor-vg8020-characterization.md §1.1.

LOCATE IS MEASURED BY GRID, NOT BY CSRLIN/POS
=============================================
`CSRLIN`/`POS` landed in `99c0f6d` and are gated 67/67, so they are legitimate
calibration -- but they are the READ side of exactly the state LOCATE WRITES.
A wrong LOCATE and a wrong CSRLIN could cancel and read as correct. The screen
grid is an independent instrument: LOCATE is measured by where a marker LANDS,
and CSRLIN/POS appear only in the `xchk` battery as a declared cross-check.

MOTOR -- WHAT THIS PROBE CAN AND CANNOT SEE
===========================================
`MOTOR`'s effect is the cassette relay. A SCREEN 0 scrape cannot see it, and no
amount of case-writing changes that. This probe measures the LANGUAGE surface
only: which argument forms the reference ACCEPTS, which it rejects, and with
which error. Whether the relay actually closes is a tape-component question and
is left to the spec as an explicitly open item -- recorded, not silently
skipped. A row here that reads `Ok` means "accepted", never "worked".

Clean-room: types lines, reads the screen. The reference ROM is never read as
code. See CONTRIBUTING.md.

USAGE
    python3 probes/basic/basic_probe_missing.py
    ... --gate              # treat the five as implemented -> every row two-sided
    ... --only locate       # cal | locate | locerr | locrow | xchk | swap
    ...                     # | swaperr | trace | motor | motorline
    ... --boot-per-case
"""
from __future__ import annotations

import argparse
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

REF_MACHINE = "Philips_VG_8020"
ZB_MACHINE = os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")
COLS, ROWS = 40, 24

# A case naming any of these is NOT calibration until --gate says otherwise.
# Matched against the bare uppercase words of the line. TROFF contains TRON as a
# substring only in the other direction, so both are listed explicitly.
UNDER_TEST = ("LOCATE", "SWAP", "TRON", "TROFF", "MOTOR")

# --- battery 1: CALIBRATION -- the instrument, using no word under test -----
# Two jobs. (a) pin the grid, so a positional divergence below is LOCATE's and
# not the width difference. (b) pin the VALUE and ERROR readouts that the SWAP
# battery depends on -- including the manual three-line exchange SWAP replaces,
# which is what says "the two machines agree about what an exchange MEANS"
# before any row asks whether SWAP performs one.
CAL = [
    ("cal-home",      'WIDTH 40:CLS:PRINT CHR$(35)',                    "marker"),
    ("cal-lead2",     'WIDTH 40:CLS:PRINT "AB";CHR$(35)',               "marker"),
    ("cal-row1",      'WIDTH 40:CLS:PRINT "A":PRINT CHR$(35)',          "marker"),
    ("cal-row2",      'WIDTH 40:CLS:PRINT:PRINT:PRINT CHR$(35)',        "marker"),
    # the exchange SWAP replaces, done by hand -- the semantic baseline
    ("cal-xchg-num",  'A=1:B=2:C=A:A=B:B=C:PRINT "[";A;B;"]"',          "value"),
    ("cal-xchg-str",  'A$="P":B$="QQ":C$=A$:A$=B$:B$=C$:PRINT "[";A$;B$;"]"',
                                                                        "value"),
    ("cal-xchg-int",  'A%=1:B%=2:C%=A%:A%=B%:B%=C%:PRINT "[";A%;B%;"]"', "value"),
    ("cal-xchg-arr",  'DIM Q(3):Q(0)=7:Q(1)=9:C=Q(0):Q(0)=Q(1):Q(1)=C:PRINT "[";Q(0);Q(1);"]"',
                                                                        "value"),
    # the undefined-variable value SWAP rows will read against
    ("cal-undef",     'PRINT "[";B;"]"',                                "value"),
    ("cal-undef-str", 'PRINT "[";B$;"]"',                               "value"),
    # error-readout calibration: the two wordings SWAP's reject rows will hit,
    # raised by constructs that have nothing to do with this slice
    ("cal-err-type",  'A=1:A$=A',                                       "tail"),
    ("cal-err-syn",   'PRINT 1,,,',                                     "tail"),
    # `Illegal function call` must be shown REACHABLE on both machines before
    # any D-MISS-2 row is read as "zerobas cannot raise it". ASC("") is the
    # control: not under test, and correct on both today.
    ("cal-err-fc",    'PRINT ASC("")',                                  "tail"),
    # the trace battery's screen readout, on a program that never traces
    ("cal-trace-null", 'CLS:PRINT "A":PRINT "B"',                       "screen"),

    # --- D-MISS-1: the TYPE-MISMATCH ASYMMETRY, found by the two rows above ---
    # `A$=A` (numeric -> string variable) reads `syntax error` on zerobas where
    # the reference says `Type mismatch`; the MIRROR (`A=A$`) is already correct
    # on both. These rows state the RULE rather than the one data point, so the
    # fix has a shape: which SIDE of the assignment, and does the offending
    # expression's FORM (literal / variable / expression / function) matter?
    ("d1-str-num-var", 'A=1:A$=A',                                      "tail"),
    ("d1-str-num-lit", 'A$=1',                                          "tail"),
    ("d1-str-num-exp", 'A$=1+1',                                        "tail"),
    ("d1-str-num-fn",  'A$=LEN("x")',                                   "tail"),
    ("d1-str-let",     'A=1:LET A$=A',                                  "tail"),
    ("d1-str-typed",   'A%=1:A$=A%',                                    "tail"),
    ("d1-num-str-var", 'A$="x":A=A$',                                   "tail"),   # mirror: correct today
    ("d1-num-str-lit", 'A="x"',                                         "tail"),
    ("d1-num-str-fn",  'A=CHR$(65)',                                    "tail"),
    ("d1-arr-str-num", 'DIM Q$(3):Q$(0)=1',                             "tail"),
    ("d1-arr-num-str", 'DIM Q(3):Q(0)="x"',                             "tail"),

    # --- D-MISS-2: CHR$ accepts its whole ARGUMENT DOMAIN silently -----------
    # `PRINT CHR$(-1)` and `CHR$(256)` raise `Illegal function call` on the
    # reference; zerobas prints a character and carries on -- no error, no
    # diagnostic. A SILENT wrong answer in a word the string engine already
    # gates, which is a different animal from the empty SILENT-GAP *class*
    # (absent reserved words) and is why it survived it.
    #
    # LEN(), not PRINT, for the in-domain rows: CHR$(0) and CHR$(255) emit
    # control characters that a name-table scrape renders as blanks, so a value
    # readout would report "" for a correct answer and "" for a broken one.
    ("d2-chr-0",      'PRINT "[";LEN(CHR$(0));"]"',                     "value"),
    ("d2-chr-65",     'PRINT "[";CHR$(65);"]"',                         "value"),
    ("d2-chr-255",    'PRINT "[";LEN(CHR$(255));"]"',                   "value"),
    ("d2-chr-frac",   'PRINT "[";CHR$(65.7);"]"',                       "value"),
    ("d2-chr-round",  'PRINT "[";CHR$(64.5);"]"',                       "value"),
    # OUT-OF-DOMAIN rows carry NO sentinel and NO brackets, deliberately. The
    # first revision wrote them as `Z=99:PRINT "[";LEN(CHR$(256));"]":Z=1` --
    # 37 source chars, which with zerobas's then-3-char `zb>` echo prefix was
    # exactly one column too wide to echo on one 40-column row. The wrapped echo broke the tail
    # anchor and THREE rows read `<no result>` on BOTH machines, i.e. AGREED,
    # while one side errored and the other did not. See MAX_ECHO below, which
    # now makes that impossible rather than unlikely.
    #
    # The tail readout needs no sentinel here: a rejected call leaves the error
    # message and an accepted one leaves the NUMBER, so the two readings are
    # already distinct.
    ("d2-chr-256",    'PRINT LEN(CHR$(256))',                           "tail"),
    ("d2-chr-neg",    'PRINT LEN(CHR$(-1))',                            "tail"),
    ("d2-chr-huge",   'PRINT LEN(CHR$(99999))',                         "tail"),
    ("d2-chr-32768",  'PRINT LEN(CHR$(32768))',                         "tail"),
    # the family CHR$ shares its argument coercion with -- are THEY checked?
    ("d2-string-neg", 'PRINT LEN(STRING$(-1,65))',                      "tail"),
    ("d2-string-256", 'PRINT LEN(STRING$(256,65))',                     "tail"),
    ("d2-left-neg",   'PRINT LEN(LEFT$("abc",-1))',                     "tail"),
    ("d2-right-neg",  'PRINT LEN(RIGHT$("abc",-1))',                    "tail"),
    ("d2-mid-neg",    'PRINT LEN(MID$("abc",-1))',                      "tail"),
    ("d2-mid-zero",   'PRINT LEN(MID$("abc",0))',                       "tail"),
    ("d2-space-neg",  'PRINT LEN(SPACE$(-1))',                          "tail"),
]

# A direct line whose ECHO wraps breaks the `tail` readout SILENTLY: screen_tail
# anchors STRICTLY on the echo, so both machines report `<no result>` and the row
# AGREES while one side errored and the other did not. 33 leaves margin for the
# reference's own indent. Enforced at startup, so this class of dead row cannot
# reach a conclusion again.
#
# The budget USED to be 40 - 3 = 37 because zerobas prefixed its echo with `zb>`.
# Since 2026-07-27 the prompt is `ZB` on a line of its own, so the echo gets all
# 40 columns and the limit could be raised -- deliberately NOT raised here. 33 is
# not costing this probe a case, and a readout guard is the last place to trade
# margin for room.
#
# ONLY `tail` is guarded, and the reason is worth stating: `value` rows survive a
# wrapped echo because result_span FALLS BACK to the last `[...]` anywhere on
# screen, which is the printed answer. Guarding them too was the first revision's
# over-correction -- it condemned 36 rows that demonstrably read correctly
# (cal-xchg-num is 37 chars and reported `2 1` on both machines).
#
# The split this forced is the better design anyway: a `tail` row measures the
# ERROR MESSAGE and stays short; a `value` row measures the EFFECT on the
# variables and may be as long as it needs. The original rows tried to do both at
# once, which is why they were all 37-55 chars.
MAX_ECHO = 33

# --- battery 2: LOCATE -- POSITION rows (screen-grid readout) ---------------
# Marker is CHR$(35): the literal '#' never appears in the typed line, so the
# grid search cannot find it inside an echoed command and report a confident,
# entirely wrong column (the cursor slice's scar).
# ⚠️ EVERY ROW PINS **BOTH** AXES: `WIDTH 40` for the column, `KEY OFF` for the
# row. The row pin is not decoration -- the two consoles have DIFFERENT ROW
# COUNTS by default. The reference reserves a function-key row at `KEY ON` (the
# boot state), so its bottom usable row is 22; zerobas paints no such row and
# bottoms out at 23. Unpinned, every row-clamp case compared 22 against 23 and
# went red for console chrome with nothing to do with LOCATE -- measured
# (locrow: the four lr-key-off-* rows agree EXACTLY, 22/22 and 23/23, while
# their unpinned twins do not). See docs/spec-basic-missing-class.md §7.2, which
# also records why hard-coding 22 into zerobas would be the WRONG way green:
# it would make zerobas's own last row unreachable by LOCATE while PRINT still
# scrolls onto it.
# The pin is set per row rather than once per battery, so no row depends on what
# ran before it.
LOCATE = [
    ("loc-5-3",       'WIDTH 40:KEY OFF:CLS:LOCATE 5,3:PRINT CHR$(35)'),
    ("loc-0-0",       'WIDTH 40:KEY OFF:CLS:LOCATE 0,0:PRINT CHR$(35)'),
    ("loc-home-after", 'WIDTH 40:KEY OFF:CLS:PRINT "AAA":LOCATE 0,0:PRINT CHR$(35)'),
    # ARGUMENT OMISSION -- the surface that is easiest to get wrong. Each of
    # these needs the cursor to be somewhere OTHER than home to be visible at
    # all, so each is preceded by output that moves it.
    ("loc-col-only",  'WIDTH 40:KEY OFF:CLS:PRINT "AAA":LOCATE 7:PRINT CHR$(35)'),
    ("loc-row-only",  'WIDTH 40:KEY OFF:CLS:PRINT "AAA";:LOCATE ,4:PRINT CHR$(35)'),
    ("loc-bare-semi", 'WIDTH 40:KEY OFF:CLS:PRINT "AAA";:LOCATE :PRINT CHR$(35)'),
    ("loc-col0-only", 'WIDTH 40:KEY OFF:CLS:PRINT "AAA";:LOCATE 0:PRINT CHR$(35)'),
    # ARGUMENT COERCION
    ("loc-float",     'WIDTH 40:KEY OFF:CLS:LOCATE 5.7,3.2:PRINT CHR$(35)'),
    ("loc-float-up",  'WIDTH 40:KEY OFF:CLS:LOCATE 4.5,2.5:PRINT CHR$(35)'),
    ("loc-expr",      'WIDTH 40:KEY OFF:CLS:LOCATE 2+3,1+2:PRINT CHR$(35)'),
    ("loc-var",       'WIDTH 40:KEY OFF:CLS:X=6:Y=2:LOCATE X,Y:PRINT CHR$(35)'),
    # THE THIRD ARGUMENT (cursor visibility). Its EFFECT is a blinking cursor,
    # which a name-table scrape cannot see; these rows measure only that the
    # form is accepted and does not disturb the position.
    ("loc-cur-0",     'WIDTH 40:KEY OFF:CLS:LOCATE 5,3,0:PRINT CHR$(35)'),
    ("loc-cur-1",     'WIDTH 40:KEY OFF:CLS:LOCATE 5,3,1:PRINT CHR$(35)'),
    # BOUNDS -- at the edge of the pinned 40x24 grid
    ("loc-max-col",   'WIDTH 40:KEY OFF:CLS:LOCATE 39,3:PRINT CHR$(35)'),
    ("loc-max-row",   'WIDTH 40:KEY OFF:CLS:LOCATE 5,22:PRINT CHR$(35)'),
    # WIDTH INTERACTION -- is the column limit WIDTH or the fixed 40? Only a
    # narrower width can tell the two apart, and the VRAM name table keeps its
    # 40-column stride at every WIDTH, so the scrape is unaffected.
    ("loc-w32-31",    'WIDTH 32:KEY OFF:CLS:LOCATE 31,3:PRINT CHR$(35)'),
    ("loc-w32-0",     'WIDTH 32:KEY OFF:CLS:LOCATE 0,3:PRINT CHR$(35)'),
    # SEQUENCING -- LOCATE is not one-shot state
    ("loc-twice",     'WIDTH 40:KEY OFF:CLS:LOCATE 20,5:LOCATE 3,1:PRINT CHR$(35)'),
    ("loc-then-print", 'WIDTH 40:KEY OFF:CLS:LOCATE 5,3:PRINT "AB";CHR$(35)'),
    ("loc-wrap",      'WIDTH 40:KEY OFF:CLS:LOCATE 38,3:PRINT "AB";CHR$(35)'),
]

# --- battery 3: LOCATE -- ERROR / scope rows (tail readout) -----------------
# NO `CLS:` on these rows. CLS wipes the typed echo, and the tail readout
# anchors the error text ON that echo -- with CLS every row reads `<no result>`
# and the battery measures nothing (the cursor slice's other scar). Cursor
# position is irrelevant to an error row.
#
# Every row that might NOT error leads with a SENTINEL assignment. Without one,
# "rejected before it ran" and "ran and did nothing observable" are the same
# reading.
# THE TAIL READOUT IS UNUSABLE FOR THESE ROWS, and finding out why is the whole
# reason this battery reads the WHOLE SCREEN instead.
#
# `screen_tail` anchors on the echo and looks AFTER it. But a partially-accepted
# LOCATE MOVES THE CURSOR FIRST and only then raises -- `LOCATE 1,1,1,1` applies
# its first two arguments, jumps to (1,1), and prints `Syntax error` there, which
# is ABOVE the echo. The tail readout saw nothing and reported `<no result>`,
# i.e. "no error", for a row that errors. The batched run had read it correctly
# only by accident (its `NEW:CLS` reset happened to leave the echo higher up),
# so the two runs DISAGREED -- which is how it was caught at all.
#
# `screen` finds the message wherever it landed. With a leading CLS the banner is
# gone, so a rejecting row reads as its message and an accepting row reads
# `<blank>`: two unambiguous readings that do not depend on where the cursor ends
# up. No echo anchor means no MAX_ECHO budget either.
#
# What each row DID when accepted -- a position, not just "no error" -- is the
# LOCACC grid battery below.
LOCERR = [
    ("le-col-w",      'CLS:WIDTH 40:LOCATE 40,0'),
    ("le-col-41",     'CLS:WIDTH 40:LOCATE 41,0'),
    ("le-col-255",    'CLS:LOCATE 255,0'),
    ("le-col-256",    'CLS:LOCATE 256,0'),
    ("le-col-neg",    'CLS:LOCATE -1,0'),
    ("le-row-24",     'CLS:LOCATE 0,24'),
    ("le-row-23",     'CLS:LOCATE 0,23'),
    ("le-row-neg",    'CLS:LOCATE 0,-1'),
    ("le-row-255",    'CLS:LOCATE 0,255'),
    ("le-row-256",    'CLS:LOCATE 0,256'),
    # narrower WIDTH -- is the column limit WIDTH, or the fixed 40?
    ("le-w32-32",     'CLS:WIDTH 32:LOCATE 32,0'),
    ("le-w32-39",     'CLS:WIDTH 32:LOCATE 39,0'),
    # SYNTAX shapes
    ("le-bare",       'CLS:LOCATE'),
    ("le-comma",      'CLS:LOCATE ,'),
    ("le-comma3",     'CLS:LOCATE ,,'),
    ("le-three",      'CLS:LOCATE 1,1,1'),
    ("le-four",       'CLS:LOCATE 1,1,1,1'),
    ("le-five",       'CLS:LOCATE 1,1,1,1,1'),
    ("le-cur-2",      'CLS:LOCATE 5,3,2'),
    ("le-cur-255",    'CLS:LOCATE 5,3,255'),
    ("le-cur-256",    'CLS:LOCATE 5,3,256'),
    ("le-cur-neg",    'CLS:LOCATE 5,3,-1'),
    # BEYOND int16 -- is the domain rule ONE error or TWO? D-MISS-2 found that
    # CHR$'s is two (`Illegal function call` inside the byte range, **Overflow**
    # past int16, raised by the coercion before the domain check runs), and the
    # first revision of this battery stopped at 256 -- so "LOCATE's rule is byte
    # domain -> Illegal function call" was measured only on the half of the
    # domain where the two hypotheses agree. `get_byte_arg` in the tree already
    # implements the two-stage rule, which makes reusing it either exactly right
    # or confidently wrong, with nothing measured in between.
    ("le-col-32768",  'CLS:LOCATE 32768,0'),
    ("le-col-99999",  'CLS:LOCATE 99999,0'),
    ("le-row-32768",  'CLS:LOCATE 0,32768'),
    ("le-cur-32768",  'CLS:LOCATE 5,3,32768'),
    ("le-col-neg32k", 'CLS:LOCATE -32769,0'),
    ("le-str",        'CLS:LOCATE "5",3'),
    ("le-trail",      'CLS:LOCATE 5,3,'),
    # SCREEN dependence: SCREEN 2 has no text cursor. Whether the reference
    # rejects or silently accepts is a real question the spec needs answered.
    # SCREEN 0 is restored on the SAME line, or the scrape reads a graphics
    # screen and every FOLLOWING case in the shared boot reads garbage too.
    ("le-scr2",       'SCREEN 2:LOCATE 5,3:SCREEN 0'),
    ("le-scr1",       'SCREEN 1:LOCATE 5,3:SCREEN 0'),
]

# --- battery 3b: LOCATE -- the ACCEPT side of the bound rows (grid readout) ---
# What a bound row that is NOT rejected actually DID. `none` = the marker never
# appeared (rejected, or the cursor went somewhere off the 40x24 grid); anything
# else is where an accepted out-of-range LOCATE put it -- clamped, wrapped, or
# straight through. A reject/accept verdict alone cannot tell those apart, and
# the implementation has to reproduce whichever one it is.
LOCACC = [
    ("la-col-40",     'WIDTH 40:KEY OFF:CLS:LOCATE 40,3:PRINT CHR$(35)'),
    ("la-col-41",     'WIDTH 40:KEY OFF:CLS:LOCATE 41,3:PRINT CHR$(35)'),
    ("la-col-255",    'WIDTH 40:KEY OFF:CLS:LOCATE 255,3:PRINT CHR$(35)'),
    ("la-row-23",     'WIDTH 40:KEY OFF:CLS:LOCATE 5,23:PRINT CHR$(35)'),
    ("la-row-24",     'WIDTH 40:KEY OFF:CLS:LOCATE 5,24:PRINT CHR$(35)'),
    ("la-w32-32",     'WIDTH 32:KEY OFF:CLS:LOCATE 32,3:PRINT CHR$(35)'),
    ("la-w32-39",     'WIDTH 32:KEY OFF:CLS:LOCATE 39,3:PRINT CHR$(35)'),
    ("la-cur-2",      'WIDTH 40:KEY OFF:CLS:LOCATE 5,3,2:PRINT CHR$(35)'),
]

# --- battery 3c: O-1 -- WHERE an accepted out-of-range LOCATE actually LANDS --
# The grid readout CANNOT answer this and the characterization says so: printing
# a marker on rows 22/23/24 scrolls the screen (the statement's own output, then
# the `Ok` prompt) before the scrape runs, so all three report row 20. That is a
# measurement the instrument destroyed, not a result.
#
# The scroll-free readout is to capture the cursor into VARIABLES on the line
# that moves it, and print them from a SEPARATE later line. Scrolling after the
# capture cannot change a number already in a variable, and the printing line
# starts from wherever the prompt left the cursor -- nowhere near the bottom.
#
# CSRLIN/POS are the READ side of the state LOCATE WRITES, which is exactly why
# §2 refused them as the gate's instrument for the POSITION battery. Here they
# are legitimate: this battery is REFERENCE-ONLY -- it asks what the reference
# does, using the reference's own gated instrument, and every in-range row it
# reads is corroborated independently by the grid battery above (loc-*). The
# cancellation risk it was refused for needs TWO implementations to cancel.
#
# `X=POS(0)` is captured on the setup line, BEFORE anything prints, so it is not
# the confounded reading of §3.4 -- there POS was evaluated mid-PRINT, 4 columns
# to the right of where LOCATE left it.
#
# KEY ON/OFF is in here because it may BE the answer. The reference boots with
# the function-key labels painted on the bottom row, and MSX reserves that row
# from the text area (CRTCNT). So "clamp to 23" and "clamp to CRTCNT-1" are two
# different implementations that agree at KEY ON and disagree at KEY OFF -- and
# only the second is `WIDTH`-relative's row-axis twin. KEY ON is restored ON THE
# SAME LINE, for the same reason le-scr1/le-scr2 restore SCREEN 0: a case that
# leaves the console reconfigured poisons every following case in a shared boot.
LOCROW_PROBE = 'PRINT "[";Y;X;"]"'
LOCROW = [
    # in-range controls -- these must reproduce the grid battery's answers, or
    # the instrument is not measuring what it claims to
    ("lr-in-5-3",     'WIDTH 40:CLS:LOCATE 5,3:Y=CSRLIN:X=POS(0)'),
    ("lr-in-21",      'WIDTH 40:CLS:LOCATE 5,21:Y=CSRLIN:X=POS(0)'),
    ("lr-in-22",      'WIDTH 40:CLS:LOCATE 5,22:Y=CSRLIN:X=POS(0)'),
    # THE OPEN QUESTION: accepted, out of range, where does it land?
    ("lr-row-23",     'WIDTH 40:CLS:LOCATE 5,23:Y=CSRLIN:X=POS(0)'),
    ("lr-row-24",     'WIDTH 40:CLS:LOCATE 5,24:Y=CSRLIN:X=POS(0)'),
    ("lr-row-25",     'WIDTH 40:CLS:LOCATE 5,25:Y=CSRLIN:X=POS(0)'),
    ("lr-row-255",    'WIDTH 40:CLS:LOCATE 5,255:Y=CSRLIN:X=POS(0)'),
    # is the clamp target the fixed bottom row, or CRTCNT-1?
    ("lr-key-off-22", 'WIDTH 40:CLS:KEY OFF:LOCATE 5,22:Y=CSRLIN:X=POS(0):KEY ON'),
    ("lr-key-off-23", 'WIDTH 40:CLS:KEY OFF:LOCATE 5,23:Y=CSRLIN:X=POS(0):KEY ON'),
    ("lr-key-off-24", 'WIDTH 40:CLS:KEY OFF:LOCATE 5,24:Y=CSRLIN:X=POS(0):KEY ON'),
    ("lr-key-off-255", 'WIDTH 40:CLS:KEY OFF:LOCATE 5,255:Y=CSRLIN:X=POS(0):KEY ON'),
    # the COLUMN axis through the same instrument -- the grid already settled
    # this (clamps to WIDTH-1), so agreement here is what says the instrument is
    # sound before its row answers are believed
    ("lr-col-39",     'WIDTH 40:CLS:LOCATE 39,3:Y=CSRLIN:X=POS(0)'),
    ("lr-col-40",     'WIDTH 40:CLS:LOCATE 40,3:Y=CSRLIN:X=POS(0)'),
    ("lr-col-255",    'WIDTH 40:CLS:LOCATE 255,3:Y=CSRLIN:X=POS(0)'),
    ("lr-w32-31",     'WIDTH 32:CLS:LOCATE 31,3:Y=CSRLIN:X=POS(0):WIDTH 40'),
    ("lr-w32-32",     'WIDTH 32:CLS:LOCATE 32,3:Y=CSRLIN:X=POS(0):WIDTH 40'),
    ("lr-w32-255",    'WIDTH 32:CLS:LOCATE 255,3:Y=CSRLIN:X=POS(0):WIDTH 40'),
    # BOTH axes out of range at once -- one clamp or two?
    ("lr-both-255",   'WIDTH 40:CLS:LOCATE 255,255:Y=CSRLIN:X=POS(0)'),
]

# --- battery 4: the DECLARED cross-check -- LOCATE read back by CSRLIN/POS ---
# Separated from the grid battery on purpose. CSRLIN/POS are the READ side of
# the state LOCATE WRITES, so a wrong pair could cancel; these rows are recorded
# as a consistency check between two independently-measured instruments, and the
# grid battery above is what the gate's teeth are in.
XCHK = [
    ("xc-5-3",        'WIDTH 40:CLS:LOCATE 5,3:PRINT "[";CSRLIN;POS(0);"]"'),
    ("xc-0-0",        'WIDTH 40:CLS:LOCATE 0,0:PRINT "[";CSRLIN;POS(0);"]"'),
    ("xc-col-only",   'WIDTH 40:CLS:PRINT "AAA":LOCATE 7:PRINT "[";CSRLIN;POS(0);"]"'),
    ("xc-row-only",   'WIDTH 40:CLS:PRINT "AAA";:LOCATE ,4:PRINT "[";CSRLIN;POS(0);"]"'),
    ("xc-max",        'WIDTH 40:CLS:LOCATE 39,22:PRINT "[";CSRLIN;POS(0);"]"'),
]

# --- battery 5: SWAP -- value rows -----------------------------------------
SWAP = [
    ("sw-num",        'A=1:B=2:SWAP A,B:PRINT "[";A;B;"]"'),
    ("sw-float",      'A=1.5:B=2.25:SWAP A,B:PRINT "[";A;B;"]"'),
    ("sw-str",        'A$="P":B$="QQ":SWAP A$,B$:PRINT "[";A$;B$;"]"'),
    ("sw-str-empty",  'A$="":B$="Q":SWAP A$,B$:PRINT "[";A$;"/";B$;"]"'),
    ("sw-int",        'A%=1:B%=2:SWAP A%,B%:PRINT "[";A%;B%;"]"'),
    ("sw-sng",        'A!=1.5:B!=2.5:SWAP A!,B!:PRINT "[";A!;B!;"]"'),
    ("sw-dbl",        'A#=1.5:B#=2.5:SWAP A#,B#:PRINT "[";A#;B#;"]"'),
    # IDENTITY and INVOLUTION -- a swap of a thing with itself, and twice
    ("sw-self",       'A=7:SWAP A,A:PRINT "[";A;"]"'),
    ("sw-twice",      'A=1:B=2:SWAP A,B:SWAP A,B:PRINT "[";A;B;"]"'),
    # ONE SIDE UNDEFINED -- does SWAP create the variable?
    ("sw-undef-r",    'A=1:SWAP A,B:PRINT "[";A;B;"]"'),
    ("sw-undef-l",    'B=1:SWAP A,B:PRINT "[";A;B;"]"'),
    ("sw-undef-both", 'SWAP A,B:PRINT "[";A;B;"]"'),
    ("sw-undef-str",  'A$="P":SWAP A$,B$:PRINT "[";A$;"/";B$;"]"'),
    # ARRAY ELEMENTS -- both sides, and mixed with a scalar
    ("sw-arr",        'DIM Q(3):Q(0)=7:Q(1)=9:SWAP Q(0),Q(1):PRINT "[";Q(0);Q(1);"]"'),
    ("sw-arr-scalar", 'DIM Q(3):A=1:Q(0)=5:SWAP A,Q(0):PRINT "[";A;Q(0);"]"'),
    ("sw-arr-str",    'DIM Q$(3):Q$(0)="P":Q$(1)="QQ":SWAP Q$(0),Q$(1):PRINT "[";Q$(0);Q$(1);"]"'),
    ("sw-arr-same",   'DIM Q(3):Q(0)=7:SWAP Q(0),Q(0):PRINT "[";Q(0);"]"'),
    # STRING IDENTITY -- does SWAP move BODIES or DESCRIPTORS? A long/short pair
    # whose bodies live in different heap places is the only way to tell a
    # descriptor exchange from a byte copy, and it is the question that decides
    # whether the implementation may touch the string heap at all.
    ("sw-str-len",    'A$="XY":B$=STRING$(20,66):SWAP A$,B$:PRINT "[";LEN(A$);LEN(B$);"]"'),
    ("sw-str-alias",  'A$="P":B$=A$:SWAP A$,B$:PRINT "[";A$;B$;"]"'),
    # does a swapped string survive a later heap event?
    ("sw-str-gc",     'A$="XY":B$=STRING$(20,66):SWAP A$,B$:C$=STRING$(30,67):PRINT "[";LEN(A$);LEN(B$);"]"'),
]

# --- battery 6: SWAP -- reject rows (tail readout) --------------------------
# Sentinel-first, same reason as LOCERR.
# CLS-led with the `screen` readout, for the same reason as LOCERR: the message
# is found wherever it lands, `<blank>` means accepted, and no echo anchor means
# no MAX_ECHO budget. SWAP does not move the cursor the way LOCATE does, so the
# tail readout was not actually broken here -- these are converted for uniformity
# and because `screen` also SHOWS a D-CUR-3 double error rather than hiding it.
SWAPERR = [
    ("se-mixed",      'CLS:A=1:B$="x":SWAP A,B$'),
    ("se-mixed-rev",  'CLS:A=1:B$="x":SWAP B$,A'),
    # NUMERIC SUBTYPES -- is the rule "numeric vs string" or "exact type"?
    # This is the single most load-bearing unknown in the SWAP surface: it
    # decides whether the implementation may move 8 bytes blindly or must
    # compare the two variables' types first.
    ("se-int-sng",    'CLS:A%=1:B!=2.5:SWAP A%,B!'),
    ("se-int-dbl",    'CLS:A%=1:B#=2.5:SWAP A%,B#'),
    ("se-sng-dbl",    'CLS:A!=1.5:B#=2.5:SWAP A!,B#'),
    ("se-int-plain",  'CLS:A%=1:B=2.5:SWAP A%,B'),
    # DEFINT changes what a bare name MEANS -- does that change the rule?
    ("se-defint",     'CLS:DEFINT C:C=1:D=2.5:SWAP C,D'),
    ("se-defint-ok",  'CLS:DEFINT C,D:C=1:D=2:SWAP C,D'),
    # SHAPE rejects
    ("se-one",        'CLS:A=1:SWAP A'),
    ("se-none",       'CLS:SWAP'),
    ("se-three",      'CLS:SWAP A,B,C'),
    ("se-lit-r",      'CLS:A=1:SWAP A,1'),
    ("se-lit-l",      'CLS:A=1:SWAP 1,A'),
    ("se-expr",       'CLS:A=1:B=2:SWAP A,B+0'),
    ("se-fn",         'CLS:A=1:SWAP A,LEN("x")'),
    ("se-paren",      'CLS:A=1:B=2:SWAP (A),B'),
    ("se-trail",      'CLS:A=1:B=2:SWAP A,B,'),
    # an UNDIMENSIONED array element -- auto-DIM, or Subscript out of range?
    ("se-arr-auto",   'CLS:A=1:SWAP A,Q(0)'),
    ("se-arr-oob",    'CLS:DIM Q(2):A=1:SWAP A,Q(9)'),
]

# --- battery 6b: the EFFECT of the SWAPERR rows that are NOT rejected --------
# A reject/accept verdict says nothing about what an ACCEPTED cross-type swap
# DID -- and that is the whole question for the numeric subtypes. Value rows, so
# the echo budget does not apply (result_span falls back to the printed answer).
# A row whose statement is rejected prints nothing and reads `<no result>`,
# which is the correct reading for it here.
SWAPEFF = [
    ("sf-int-sng",    'A%=1:B!=2.5:SWAP A%,B!:PRINT "[";A%;B!;"]"'),
    ("sf-int-dbl",    'A%=1:B#=2.5:SWAP A%,B#:PRINT "[";A%;B#;"]"'),
    ("sf-sng-dbl",    'A!=1.5:B#=2.5:SWAP A!,B#:PRINT "[";A!;B#;"]"'),
    ("sf-int-plain",  'A%=1:B=2.5:SWAP A%,B:PRINT "[";A%;B;"]"'),
    ("sf-defint",     'DEFINT C:C=1:D=2.5:SWAP C,D:PRINT "[";C;D;"]"'),
    ("sf-arr-auto",   'A=1:SWAP A,Q(0):PRINT "[";A;Q(0);"]"'),
]

# --- battery 7: TRON / TROFF -- whole-screen readout ------------------------
# Stored mode. Each program CLSes FIRST so the screen holds only its own output
# and the typed echo is gone -- which also means these rows must NOT use the
# `[...]` value convention: the reference's own trace decoration is bracketed,
# and result_span would return a slice of the trace and call it the answer.
#
# `(mode, body-statements)`: run through as_stored, numbered 10/20/... + RUN.
TRACE = [
    ("tr-basic",      ['CLS:TRON', 'PRINT "A"', 'TROFF', 'PRINT "B"']),
    ("tr-all",        ['CLS:TRON', 'PRINT "A"', 'PRINT "B"']),
    # does the decoration appear for EVERY statement, or every LINE?
    ("tr-multi-stmt", ['CLS:TRON', 'PRINT "A":PRINT "B"', 'PRINT "C"']),
    # control flow: does a jump trace the line it lands on?
    ("tr-goto",       ['CLS:TRON', 'GOTO 40', 'PRINT "SKIP"', 'PRINT "D"']),
    ("tr-forloop",    ['CLS:TRON', 'FOR I=1 TO 2', 'NEXT', 'TROFF']),
    ("tr-gosub",      ['CLS:TRON:GOSUB 40', 'TROFF', 'END', 'RETURN']),
    # SCOPE: does TROFF at the top mean the rest is silent?
    ("tr-off-first",  ['CLS:TROFF', 'PRINT "A"']),
    ("tr-off-mid",    ['CLS:TRON', 'PRINT "A"', 'TROFF', 'PRINT "B"', 'TRON',
                       'PRINT "C"']),
    # does the trace interleave with PRINT output, or own its own rows?
    ("tr-semi",       ['CLS:TRON', 'PRINT "A";', 'PRINT "B";', 'TROFF']),
    # LINE NUMBER WIDTH -- a 5-digit line number in the decoration
    ("tr-bignum",     ['CLS:TRON', 'PRINT "A"']),
]
# tr-bignum needs line numbers the 10/20/... numbering cannot give it; it is
# emitted with an explicit numbering below (see STORED_EXPLICIT).
STORED_EXPLICIT = {
    "tr-bignum": ['1 CLS:TRON', '30000 PRINT "A"', '32767 TROFF'],
}

# TRON's SCOPE across a run boundary, in DIRECT mode -- does TRON typed at the
# prompt trace the prompt's own statements, and does it survive into a RUN?
TRACE_DIRECT = [
    ("trd-direct",    'CLS:TRON:PRINT "A":TROFF',                       "screen"),
    ("trd-bare",      'CLS:TRON:TROFF',                                     "screen"),
    ("trd-arg",       'CLS:TRON 1',                                         "screen"),
    ("trd-troff-arg", 'CLS:TROFF 1',                                        "screen"),
]

# TRON's SCOPE ACROSS THE RUN BOUNDARY -- the question a single line cannot ask.
# Delivered as DIRECT lines: the numbered ones are STORED by the REPL rather than
# executed, the bare ones run at the prompt. So `TRON` here is typed at the
# prompt and RUN follows it, which is the only way to ask whether a direct-mode
# TRON traces a program -- and whether RUN resets it.
TRACE_SPAN = {
    # direct TRON, then RUN -> is the program traced?
    "trs-direct-into-run": ['10 CLS', '20 PRINT "A"', 'TRON', 'RUN'],
    # TRON inside the program, then a SECOND RUN -> did RUN reset it?
    "trs-survives-run":    ['10 CLS', '20 TRON', '30 PRINT "A"', 'RUN', 'RUN'],
    # END does not TROFF -- does the trace still decorate a later direct GOTO?
    "trs-after-end":       ['10 CLS:TRON', '20 PRINT "A"', '30 END', 'RUN'],
    # does NEW clear it? (nothing to trace afterwards, so this reads as the
    # absence of decoration on the stored-then-run program)
    "trs-new-clears":      ['10 CLS:TRON', '20 PRINT "A"', 'RUN', 'NEW',
                            '10 CLS', '20 PRINT "B"', 'RUN'],
}

# --- battery 8: MOTOR -- LANGUAGE SURFACE ONLY ------------------------------
# See the module docstring: a screen scrape cannot see the cassette relay. Every
# row is sentinel-first, so "accepted" and "rejected" are distinguishable; NO
# row here claims the motor turned. `MOTOR ON` with no cassette plugged is
# harmless on both machines (unlike LSTOUT, which HANGS when unplugged -- the
# reason LPRINT/LLIST are crunch-only in the sweep).
MOTOR = [
    ("mo-bare",       'CLS:MOTOR'),
    ("mo-on",         'CLS:MOTOR ON'),
    ("mo-off",        'CLS:MOTOR OFF'),
    ("mo-onoff",      'CLS:MOTOR ON:MOTOR OFF'),
    ("mo-twice",      'CLS:MOTOR:MOTOR'),
    # rejects -- ON/OFF are the only keywords; is STOP taken (as it is for
    # SPRITE/KEY/INTERVAL), and is a numeric argument accepted?
    ("mo-stop",       'CLS:MOTOR STOP'),
    ("mo-num",        'CLS:MOTOR 1'),
    ("mo-zero",       'CLS:MOTOR 0'),
    ("mo-str",        'CLS:MOTOR "ON"'),
    ("mo-var",        'CLS:A=1:MOTOR A'),
    ("mo-comma",      'CLS:MOTOR ON,OFF'),
    ("mo-trail",      'CLS:MOTOR ON,'),
]

# --- battery 8b: THE RELAY ITSELF (O-2, closed) ------------------------------
# Every row in MOTOR above reads <blank> for the accepted forms -- and would read
# <blank> just as happily if MOTOR were a parse that did NOTHING. That is the
# standing "a gate can be green while measuring nothing" trap, and for this word
# it is not hypothetical: `inc hl / jp exec_stmt` passes all five accept rows.
#
# The relay is invisible to a SCREEN 0 scrape, but it is NOT invisible to BASIC.
# The motor line is i8255 PPI Port C bit 4, 0 = motor ON, and Port C's OUTPUT
# LATCH reads back through port $AA -- which `INP` can reach from BASIC on BOTH
# machines. So this is a real two-sided differential (does the reference's relay
# move, and does ours move the same way), not an "it was accepted" row.
#
# Boot state is part of the measurement: mo-l-bare toggles from whatever the
# machine booted with, so it is only meaningful next to mo-l-boot, which reads
# the line before any MOTOR statement runs.
# ⚠️ PIN THE INSTRUMENT BEFORE READING IT. Port $AA is written decimal (170) and
# masked `AND16` with no spaces, both purely to fit MAX_ECHO -- and an
# echo-anchored row that fails to parse AGREES on both machines, which is the
# wrong-reason agreement this file's header warns about. So the first two rows
# are controls on the READOUT ITSELF: they use no port and no MOTOR, and they
# fail loudly if `AND16` ever stopped meaning "the AND operator applied to 16".
# The low nibble of Port C is the keyboard row select, so the mask is not
# optional -- printing the raw byte would compare scan state, not the relay.
MOTORLINE = [
    ("mo-l-ctl-1",    '?255AND16'),
    ("mo-l-ctl-0",    '?239AND16'),
    ("mo-l-boot",     '?INP(170)AND16'),
    ("mo-l-on",       'MOTOR ON:?INP(170)AND16'),
    ("mo-l-off",      'MOTOR OFF:?INP(170)AND16'),
    ("mo-l-bare",     'MOTOR:?INP(170)AND16'),
    # the toggle is a TOGGLE, not a set: twice returns to where it started
    ("mo-l-twice",    'MOTOR:MOTOR:?INP(170)AND16'),
    # ON is idempotent, and OFF after ON actually releases
    ("mo-l-on-on",    'MOTOR ON:MOTOR ON:?INP(170)AND16'),
    ("mo-l-on-off",   'MOTOR ON:MOTOR OFF:?INP(170)AND16'),
    # and the toggle form toggles relative to an explicit ON, not to boot state
    ("mo-l-on-bare",  'MOTOR ON:MOTOR:?INP(170)AND16'),
]


# --- readouts ---------------------------------------------------------------

def rows_of(raw: str | None) -> list[str]:
    if raw is None:
        return []
    return [raw[i * COLS:(i + 1) * COLS] for i in range(ROWS)]


def marker(raw: str | None, ch: str = "#") -> str:
    """Where the marker landed, as 'r,c'. The LOCATE battery reaches row 22, so
    unlike the cursor probe this searches the WHOLE screen, not the first six
    rows -- a search window shorter than the cases can reach would report
    `none` for a marker that landed perfectly (the T2 capture-window trap)."""
    for r, row in enumerate(rows_of(raw)):
        c = row.find(ch)
        if c >= 0:
            return f"{r},{c}"
    return "none"


def value(raw: str | None, line: str) -> str:
    """The bracketed answer, or `<aborted>` if the statement never printed one.

    The `result_span` FALLBACK IS LOAD-BEARING and must stay: several rows here
    are 51-63 chars, so their echo wraps and `result_span_after_echo` cannot
    anchor -- the whole `xchk` battery reads `<aborted>` without it, having read
    correct values with it. `result_span` rescues them because it takes the LAST
    `[` on screen, which is the printed answer whenever one was printed.

    What the fallback CANNOT do is notice when nothing was printed. Every value
    row's own echo contains `[` and `]` (inside its `PRINT "[";...` text), so on
    an aborted statement the last `[` is the ECHO's and the fallback returns a
    slice of the typed command -- readings like `";A%;B!;"` and `";C;D;"`, which
    is a confusing way to spell "nothing was printed" and invites reading
    punctuation as data.

    So the fallback is kept and its output is CLASSIFIED: printed output here is
    numbers and short literals and never contains `"` or `;`, while an echo
    slice always contains both (it is the inside of `"[";...;"]"`). A span
    carrying either is the echo, and the honest reading is `<aborted>`."""
    if raw is None:
        return "<no capture>"
    span = omsx_repl.result_span_after_echo(raw, line)
    if span is None:
        span = omsx_repl.result_span(raw)
        if span is not None and ('"' in span or ';' in span):
            span = None                 # that is the ECHO, not an answer
    if span is not None:
        return " ".join(span.split())
    tail = omsx_repl.screen_tail(raw, line)
    if tail:
        tail = " ".join(tail.split())
        if tail:
            return f"ERR:{tail}"
    return "<aborted>"


# The reference paints its FUNCTION-KEY LABELS on the bottom screen row and CLS
# does NOT wipe them; C-BIOS paints nothing there. So a whole-screen readout on a
# CLS-led program compared `A/B` against `A/B/color auto goto list run` and every
# trace row would have failed for a reason that has nothing to do with TRON.
# Caught by cal-trace-null, which is in the battery precisely to catch it.
#
# Dropped rather than suppressed with `KEY OFF`: the labels are console chrome,
# already a known divergence (like the different boot WIDTH), and turning them
# off would make the readout depend on `KEY` behaving identically on both sides.
# Every trace program CLSes first and prints well under 20 rows, so nothing this
# battery measures can reach the last row.
FKEY_ROW = ROWS - 1


PROMPTS = ("Ok", "ZB")


def screen(raw: str | None) -> str:
    """The screen, collapsed: every non-blank row joined by '/' with runs of
    spaces squeezed. For the trace battery, whose programs CLS first so this
    holds their output and nothing else. The trailing prompt is dropped (the
    reference closes with `Ok` and zerobas with `zb>`, a documented divergence
    that is not what these rows measure) and so is the function-key row.

    ⚠️ THE PROMPT IS STRIPPED AT THE END OF A ROW, NOT ONLY ON A ROW OF ITS OWN.
    That distinction is the whole point, and it took the TRON battery to expose
    it. **The reference emits a newline before its prompt when the cursor is not
    at column 0; zerobas prints its prompt where the cursor stands.** So after
    output that ends mid-row the reference puts `Ok` on the NEXT row (dropped by
    the whole-row test) while zerobas appends `zb>` to the output row (not
    dropped) -- and the row read `[20][30][30][40]` against
    `[20][30][30][40]zb>`.

    TRON makes that common because its decoration deliberately emits no newline
    of its own, so any program ending on a traced line stops mid-row. It is NOT
    a TRON divergence: `CLS:PRINT "A";` alone reproduces it with no word under
    test (reference `A` / `Ok` on two rows, zerobas `Azb>` on one). Recorded as
    its own finding; suppressed here because the prompt is console chrome and
    this readout already claimed to drop it.

    Safe for these batteries: their output is `[nnn]` decorations and the short
    literals A/B/C/D/SKIP, none of which can end in `Ok` or `zb>`."""
    if raw is None:
        return "<no capture>"
    out = []
    for r, row in enumerate(rows_of(raw)):
        if r == FKEY_ROW:
            continue
        t = " ".join(row.split())
        for p in PROMPTS:
            if t.endswith(p):
                t = t[:-len(p)].rstrip()
                break
        if not t:
            continue
        out.append(t)
    return "/".join(out) if out else "<blank>"


def agree(a: str, b: str) -> bool:
    """zerobas's lowercase error wording is a documented divergence, so anything
    that looks like an error message compares case-insensitively (the kwsweep
    layer-2 lesson)."""
    return a.lower() == b.lower() or a == b


class Case:
    def __init__(self, battery, label, line, readout, mode="direct",
                 lines=None, display=None):
        self.battery = battery
        self.label = label
        self.line = line                # echo anchor
        # what the REPORT shows. Normally the anchor is the case, but a
        # multi-line case's anchor is only its readout line -- printing that for
        # every LOCROW row would show `PRINT "[";Y;X;"]"` 18 times and hide the
        # LOCATE that is the actual subject.
        self.display = display if display is not None else line
        self.readout = readout          # value | marker | tail | screen
        self.mode = mode
        self.lines = lines if lines is not None else [line]
        # classify from ALL the case's lines, not just the echo anchor. For every
        # single-line case these are the same string; for a multi-line case the
        # anchor is the LAST line, and the LOCROW battery puts the word under
        # test on the FIRST one -- reading only the anchor would call it
        # calibration and run it two-sided against a zerobas that has no LOCATE.
        words = set(re.findall(r"[A-Z]+", " ".join(self.lines)))
        self.calib = not (words & (set(UNDER_TEST) - set(IMPLEMENTED)))
        self.ref = None
        self.zb = None

    def spec(self):
        return (self.mode, self.lines)

    def read(self, raw):
        if self.readout == "marker":
            return marker(raw)
        if self.readout == "screen":
            return screen(raw)
        if self.readout == "tail":
            # an err row must not go through the bracket readout: the ECHO
            # itself contains '[' and ']', so a span search happily returns a
            # slice of the command that was typed and calls it the answer.
            t = omsx_repl.screen_tail(raw, self.line)
            return " ".join(t.split()) if t else "<no result>"
        return value(raw, self.line)


IMPLEMENTED: set[str] = set()


def build() -> dict[str, list[Case]]:
    bat: dict[str, list[Case]] = {}
    bat["cal"] = [Case("cal", lb, ln, ro) for lb, ln, ro in CAL]
    bat["locate"] = [Case("locate", lb, ln, "marker") for lb, ln in LOCATE]
    bat["locerr"] = ([Case("locerr", lb, ln, "screen") for lb, ln in LOCERR]
                     + [Case("locerr", lb, ln, "marker") for lb, ln in LOCACC])
    bat["locrow"] = [Case("locrow", lb, LOCROW_PROBE, "value", mode="direct",
                          lines=[ln, LOCROW_PROBE], display=ln)
                     for lb, ln in LOCROW]
    bat["xchk"] = [Case("xchk", lb, ln, "value") for lb, ln in XCHK]
    bat["swap"] = [Case("swap", lb, ln, "value") for lb, ln in SWAP]
    bat["swaperr"] = ([Case("swaperr", lb, ln, "screen") for lb, ln in SWAPERR]
                      + [Case("swaperr", lb, ln, "value") for lb, ln in SWAPEFF])

    trace = []
    for lb, body in TRACE:
        if lb in STORED_EXPLICIT:
            continue
        trace.append(Case("trace", lb, " : ".join(body), "screen",
                          mode="stored", lines=body))
    for lb, numbered in STORED_EXPLICIT.items():
        # explicit line numbers -> deliver as DIRECT lines (each is already a
        # numbered program line, which the REPL stores rather than executes),
        # then RUN.
        trace.append(Case("trace", lb, " : ".join(numbered), "screen",
                          mode="direct", lines=numbered + ["RUN"]))
    trace += [Case("trace", lb, ln, ro) for lb, ln, ro in TRACE_DIRECT]
    for lb, lines in TRACE_SPAN.items():
        trace.append(Case("trace", lb, " : ".join(lines), "screen",
                          mode="direct", lines=lines))
    bat["trace"] = trace

    bat["motor"] = [Case("motor", lb, ln, "screen") for lb, ln in MOTOR]
    # O-2: the relay itself, read back through the PPI Port C output latch.
    # "tail" (the echo-anchored readout) -- these PRINT a number, so the answer
    # is the span after the echoed command line, exactly like the cal rows.
    bat["motorline"] = [Case("motorline", lb, ln, "tail", mode="direct")
                        for lb, ln in MOTORLINE]
    return bat


def check_echo_widths(bat: dict[str, list[Case]]) -> list[str]:
    """Every echo-anchored row must fit one screen row, or its readout dies
    silently and the row AGREES while measuring nothing (see MAX_ECHO). Returns
    the offenders; the probe REFUSES TO RUN rather than report dead rows."""
    bad = []
    for cases in bat.values():
        for c in cases:
            if c.readout != "tail" or c.mode != "direct":
                continue
            if len(c.line) > MAX_ECHO:
                bad.append(f"{c.battery}/{c.label}: {len(c.line)} chars "
                           f"(max {MAX_ECHO}) -- {c.line}")
    return bad


def main() -> int:
    global IMPLEMENTED
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--machine", default=REF_MACHINE)
    ap.add_argument("--zb-machine", dest="zb_machine", default=ZB_MACHINE)
    ap.add_argument("--only", help="cal | locate | locerr | locrow | xchk | "
                                   "swap | swaperr | trace | motor | motorline")
    ap.add_argument("--gate", action="store_true",
                    help="treat LOCATE/SWAP/TRON/TROFF/MOTOR as implemented -> "
                         "every row becomes a two-sided differential")
    ap.add_argument("--boot-per-case", dest="boot_per_case",
                    action="store_true")
    args = ap.parse_args()
    if args.gate:
        IMPLEMENTED = set(UNDER_TEST)

    bat = build()
    if args.only:
        if args.only not in bat:
            print(f"unknown battery {args.only!r}; pick one of {list(bat)}")
            return 2
        bat = {args.only: bat[args.only]}
    wide = check_echo_widths(bat)
    if wide:
        print("REFUSING TO RUN -- these echo-anchored rows wrap, so their "
              "readout would die silently and the row would AGREE while "
              "measuring nothing:")
        for w in wide:
            print(f"  {w}")
        return 2

    cases = [c for b in bat.values() for c in b]
    batch = not args.boot_per_case

    both = [c for c in cases if c.calib]
    refonly = [c for c in cases if not c.calib]

    if both:
        print(f"# {len(both)} two-sided -> {args.machine} + {args.zb_machine}")
        _, rr, zz = omsx_repl.run_differential(
            args.machine, args.zb_machine, [c.spec() for c in both],
            lambda i, r, z: agree(both[i].read(r), both[i].read(z)),
            batch=batch, reset=("NEW", "CLS"))
        for c, r, z in zip(both, rr, zz):
            c.ref, c.zb = c.read(r), c.read(z)
    if refonly:
        print(f"# {len(refonly)} reference-only -> {args.machine}")
        raws = omsx_repl.run_cases(args.machine, [c.spec() for c in refonly],
                                   batch=batch, reset=("NEW", "CLS"))
        for c, raw in zip(refonly, raws):
            c.ref = c.read(raw)

    ok = True
    if both:
        bad = 0
        print("\n=== CALIBRATION / GATE (must AGREE) ===")
        for c in both:
            good = agree(c.ref, c.zb)
            bad += not good
            ok = ok and good
            print(f"{'PASS' if good else 'FAIL':5} {c.battery:8} {c.label:14} "
                  f"{c.display[:34]:34} ref={c.ref[:22]:>22}  zb={c.zb[:22]:>22}")
        print(f"--- {len(both) - bad}/{len(both)} agree"
              + ("" if not bad else "   <-- red"))

    titles = {
        "cal": "CALIBRATION (shown above)",
        "locate": "LOCATE -- POSITIONS (row,col of the marker)",
        "locerr": "LOCATE -- ERRORS / BOUNDS",
        "locrow": "LOCATE -- O-1: WHERE an out-of-range arg LANDS (scroll-free)",
        "xchk": "LOCATE read back by CSRLIN/POS (declared cross-check)",
        "swap": "SWAP -- VALUES",
        "swaperr": "SWAP -- REJECTS / TYPE RULE",
        "trace": "TRON / TROFF -- SCREEN",
        "motor": "MOTOR -- LANGUAGE SURFACE ONLY (never 'the relay closed')",
        "motorline": "MOTOR -- THE RELAY ITSELF (PPI port C bit 4; 0 = motor ON)",
    }
    for name in ("locate", "locerr", "locrow", "xchk", "swap", "swaperr",
                 "trace", "motor"):
        if name not in bat:
            continue
        print(f"\n=== {titles[name]} — the ROM dictates ===")
        for c in bat[name]:
            twin = f"\n      {'':14} zb={c.zb}" if c.zb is not None else ""
            print(f"  {c.label:14} {c.display[:44]:44} -> {c.ref}{twin}")

    print("\n" + ("OK" if ok else "ATTENTION: see FAIL rows above"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
