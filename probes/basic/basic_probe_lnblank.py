#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-LNBLANK -- WHAT A BLANK INSIDE A LINE NUMBER DOES.

Spec: docs/spec-basic-lnblank.md.  Measurement: docs/lnblank-msx1-characterization.md.

⚠️ THIS PROBE HAS OUTGROWN ITS NAME, and every battery past `num` says so. It is
now the crunch's whole blank/charset surface, one slice at a time: `lit`/`dec`
(D-DECBLANK), `exp` (D-EXPBAD), `nam` (D-NAMBLANK) and `dot`/`dotd` (D-NAMDOT,
docs/spec-basic-namedot.md -- a '.' inside an identifier, which has nothing to do
with blanks at all: its decisive row `20 A=B.5` CONTAINS NO BLANK). Each battery
kept its rows here rather than forking a probe because the earlier slices' cells
are the later slices' MUST-NOT-MOVE controls, and ONLY= selects them together --
a knife that cannot see the cells it might break is not a knife.

WHY THIS EXISTS
===============
D-LINEMAX's `tok` battery had a FAILING TWO-SIDED CONTROL that had nothing to do
with line length (basic_probe_linemax.py:139):

    typed:      20 0#0#0#0#0#
    VG-8020 ->  line 200, body = 0x23 ('#') + four double literals
    zerobas ->  line 20,  body = five double literals

The reference's line-number scan crossed the blank and kept accumulating
(`20` + ` ` + `0` = 200); zerobas stopped at it. Same source text, different line
number AND different body. There it was a confound and the battery dodged it by
putting `A=` in the payload. Here it is the subject.

TWO NAMED RULES, AND EVERY ROW SEPARATES THEM
=============================================
  rule T (terminate) -- the scan ends at the first non-digit.  zerobas today.
  rule S (skip)      -- blanks are transparent; the scan ends at the first
                        non-digit, non-blank.

A row where T and S predict the SAME bytes is a CONTROL and is labelled one. It
is pinned BECAUSE it agrees: a cell pinned that way is what caught the regression
D-BADFNUM's signed-off design shipped. Every other row is chosen so the two rules
predict DIFFERENT bytes -- a cell that agrees can agree for the wrong reason.

TWO ORACLES, NOT ONE
====================
The whole slice rests on ONE filed row from ONE machine. Every row here is asked
of the VG-8020 *and* the CF-3300. A rule both show is a property of MSX-BASIC,
which is what zerobas is a faithful implementation of; a rule only one shows is a
property of that ROM, and copying it would be a mistake a single oracle cannot
detect. Affordable only because the readout is MEMORY, not screen: the CF-3300
boots Disk BASIC in SCREEN 1, which would otherwise need the whole geometry
dance diskbasic_probe_chancost.py carries.

THE INSTRUMENT
==============
`("stored_line", TXTTAB)` -- omsx_repl's __hex_line dereferences TXTTAB ($F676)
and returns the EXACT bytes of the first stored line, using the link word for the
extent so an embedded $00 in a value byte never truncates it. It is the only
readout that tells "different line number" from "different body", and the filed
row differs in BOTH.

⚠️ THE LINK WORD IS NEVER COMPARED. It is an ABSOLUTE address, and the CF-3300's
Disk BASIC text base is not the VG-8020's $8001 -- comparing raw captures would
report every row as divergent for a reason that is not a behaviour. `decode()`
reads the line number and body and drops the link.
"""
from __future__ import annotations
import argparse, os, shutil, sys, tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
import omsx_repl  # noqa: E402

TXTTAB = 0xF676          # sysvar: pointer to the BASIC text base (all machines)
SRC_DSK = os.path.join(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))), "disk", "test720.dsk")

ZB_MACHINE = os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")

# side -> how to drive it. `reset` is emitted before EVERY case.
#
# ⚠️ THE CF-3300's LEADING "" IS THE BOOT DATE PROMPT. An empty line injects a
# bare CR, which accepts the default date; at the BASIC prompt every later one is
# a no-op. Emitting it per case rather than once costs a step and needs no
# library change. Its 4.5 s cadence is not a guess -- D-LOF measured the CF-3300
# EATING keystrokes at shorter ones (diskbasic_probe_chancost.py:479).
#
# ⚠️ `diska` is a /tmp COPY, never the committed image: nothing here writes to a
# disk, but a probe that hands openMSX the repo's own .dsk is one bug away from
# mutating a committed artifact.
SIDES = {
    "vg8020": dict(machine="Philips_VG_8020", boot=8.0, step=2.5,
                   reset=("NEW",), diska=None),
    "cf3300": dict(machine="National_CF-3300", boot=14.0, step=4.5,
                   reset=("", "NEW"), diska=SRC_DSK),
    "zb":     dict(machine=ZB_MACHINE, boot=8.0, step=2.5,
                   reset=("NEW",), diska=None),
}
REF_SIDES = ("vg8020", "cf3300")

TAB = "\t"

# --- the `num` battery: the LEADING line number (program.asm parse_lineno) ----
# Payloads end in `REMX` because REM keeps the rest of its line VERBATIM on every
# MSX (basic/tokenise.inc:99/181), so the body reads back as $8F + 'X' with no
# token decoding needed and no second variable in the way.
NUM = [
    # label          typed lines                       role
    ("num-plain",    ["20 REMX"]),        # CONTROL: T and S both -> line 20
    ("num-nospace",  ["20REMX"]),         # CONTROL: no blank at all
    ("num-stop",     ["2 X=1"]),          # CONTROL: a letter stops the scan on
                                          # both (linemax:145 already asserts it)
    ("num-lead",     [" 20 REMX"]),       # CONTROL: dispatch_line skip_spaces
    ("num-blank1",   ["2 0 REMX"]),       # T -> line 2;  S -> line 20
    ("num-blank2",   ["2  0 REMX"]),      # is ANY RUN of blanks transparent?
    ("num-blank3",   ["2 0 0 REMX"]),     # T -> line 2;  S -> line 200
    ("num-filed",    ["20 0#0#0#0#0#"]),  # THE FILED ROW, reproduced verbatim
    ("num-mid",      ["20 0REMX"]),       # T -> line 20 + '0'; S -> line 200
    ("num-body1",    ["20  REMX"]),       # BODY-OFFSET axis: is a blank kept?
    ("num-body2",    ["20   REMX"]),      # three blanks
    ("num-zero",     ["0 REMX"]),         # CONTROL: line 0
    ("num-max",      ["6 5 5 2 9 REMX"]), # S -> 65529, the documented ceiling
    ("num-over",     ["6 5 5 3 0 REMX"]), # S -> 65530: accepted, or refused?
    ("num-huge",     ["9 9 9 9 9 REMX"]), # S -> 99999: wraps, or refused?
    # ⚠️ THE THREE ROWS ABOVE CANNOT ANSWER THE RANGE QUESTION ON A MACHINE THAT
    # STOPS AT THE BLANK, and that is a hole in this battery's own denominator.
    # zerobas reads `6 5 5 3 0 REMX` as line 6 -- so the row diverges for the
    # BLANK reason and says nothing at all about what it does with 65530. These
    # three ask the range question with no blank in the way, which separates "the
    # scan stops early" from "the ceiling is unguarded". It matters because
    # fixing the blank rule is what makes the big values REACHABLE: without a
    # range check, `9 9 9 9 9` would stop being a wrong-but-visible line 9 and
    # start being a SILENTLY WRAPPED line number.
    ("num-max0",     ["65529 REMX"]),     # CONTROL: the ceiling, no blanks
    ("num-over0",    ["65530 REMX"]),     # one past it, no blanks
    ("num-huge0",    ["99999 REMX"]),     # past 65535: wraps, or refused?
    # ⚠️ INFORMATIONAL, NON-GATING. The MSX line editor may expand TAB inside the
    # INPUT BUFFER, in which case this row measures the editor and not the scan.
    # Reported with that caveat whichever way it reads.
    ("num-tab",      ["2" + TAB + "0 REMX"]),
    # THE CRISPEST SEPARATOR IN THE BATTERY. Store line 20, then type `2 0` with
    # no body. Under S that is "delete line 20" -> the program is EMPTY. Under T
    # it is "delete line 2", which does not exist -> line 20 survives. The two
    # rules differ in the NUMBER OF STORED LINES, which no adjacent behaviour can
    # produce by accident -- so this is also the falsification witness (spec §6).
    ("num-only",     ["20 REMY", "2 0"]),
]

# --- the `lit` battery: is it the LINE-NUMBER scan, or the NUMBER scanner? ----
# The structural question, and the one that sizes the fix. If these come back
# S-shaped then the defect is not in the line-number scan at all and the spec is
# wrong about its own subject -- which is worth knowing BEFORE a fix, not after.
LIT = [
    ("lit-ctl",      ["20 A=10"]),        # CONTROL
    ("lit-assign",   ["20 A=1 0"]),
    ("lit-print",    ["20 PRINT 1 0"]),
    # ⚠️ THE FIRST RUN ANSWERED THIS BATTERY "S", AND THAT MOVED THE SUBJECT.
    # `20 A=1 0` crunched to the SINGLE literal 10 ($0F,$0A) on BOTH references
    # -- byte-identical to `20 A=10`. So blank-transparency is NOT a property of
    # the line-number scan, which is all the TODO filed; it is a property of the
    # NUMBER SCANNER. These rows measure how far that reaches, because a fix
    # aimed at one scanner and a fix aimed at all of them are different slices.
    ("lit-add",      ["20 A=1 0+2 0"]),   # two literals in one expression
    ("lit-hex",      ["20 A=&H1 F"]),     # does a HEX literal skip blanks too?
    ("lit-float",    ["20 A=1 . 5"]),     # the decimal point
    ("lit-exp",      ["20 A=1E 2"]),      # the exponent
    # GATING CONTROLS -- the two places a blank MUST survive. Any fix that makes
    # blanks transparent to a scanner must not reach inside a string literal or
    # a REM tail, and these are what say so.
    ("lit-str",      ['20 A$="1 0"']),
    ("lit-rem",      ["20 REM1 0"]),
    # ⚠️ INFORMATIONAL, and it asks how deep the rule goes: MS-BASIC's blank
    # handling is famously a property of the character FETCH, not of any one
    # scanner, in which case `A B` is the variable `AB`. If that reads S-shaped
    # too, the mechanism is one thing and not three -- worth knowing, out of
    # scope to act on here (spec §7).
    ("lit-varname",  ["20 A B=1"]),
]

# --- the `dec` battery: THE DENOMINATOR OF THE DECIMAL-LITERAL SCANNER -------
# D-DECBLANK (docs/spec-basic-decblank.md).  The five `lit` rows above are a
# SAMPLE, not a surface: they say the decimal scanner is blank-transparent
# somewhere between the digits, the dot and the exponent, and they say hex is
# not.  They do NOT say where the transparency stops on the OTHER side, and that
# is the question that decides the SHAPE of the fix.
#
# TWO RULES, AND THE ROWS ARE CHOSEN TO SEPARATE THEM:
#
#   rule L (lookahead)  -- a blank run is transparent only when what follows it
#                          CONTINUES the number.  A run that merely TRAILS the
#                          number is not the number's, and its blanks survive in
#                          the crunched bytes.  This is the shape parse_lineno /
#                          bl_acc already have (both look past the run and commit
#                          only when it ends in a digit).
#   rule G (greedy)     -- the literal scan fetches through blanks unconditionally
#                          (the MS-BASIC CHRGET shape), so a run that trails the
#                          number is CONSUMED and disappears from the stored line.
#
# `dec-trail` / `dec-trail2` are the pair that decides it, and no row already in
# this probe can: every `lit` row puts the blank BETWEEN two things that both
# belong to the number.  Implementing L when the reference is G (or the reverse)
# reproduces every filed row perfectly and gets the byte count wrong on programs
# nobody in this battery typed -- the D-ERR21 trap, where the WRONG
# implementation reproduced the filed measurement exactly.
#
# The rest of the battery is denominator: every place a decimal literal has an
# internal seam (the dot, the exponent marker, the exponent's sign, the type
# suffix), plus the two non-decimal radices `lit-hex` left unmeasured, plus the
# classification boundary the joined value has to flow through.
DEC = [
    ("dec-ctl",      ["20 A=1+2"]),        # CONTROL: no blank anywhere
    ("dec-hexctl",   ["20 A=&H12"]),       # CONTROL: pins the hex encoding, so
                                           # lit-hex's reading is attributable
    # ★ THE PAIR THAT SIZES THE FIX -- a blank run that does NOT end in a digit.
    ("dec-trail",    ["20 A=1 +2"]),       # L -> `<12> <F1><13>`; G -> `<12><F1><13>`
    ("dec-trail2",   ["20 A=1  +2"]),      # two of them: L keeps both, G eats both
    ("dec-run2",     ["20 A=1  0"]),       # is ANY RUN transparent between digits?
    # The internal seams.  `lit-float` put blanks on BOTH sides of the dot and
    # `lit-exp` put one after the marker; neither says whether the seam is
    # crossable from the LEFT, which is a different fetch in every candidate
    # implementation.
    ("dec-dotpre",   ["20 A=1 .5"]),       # blank before the '.'
    ("dec-dotpost",  ["20 A=1. 5"]),       # blank after the '.'
    ("dec-exppre",   ["20 A=1 E2"]),       # blank before the exponent marker
    ("dec-expsgn",   ["20 A=1E- 2"]),      # blank between the sign and the digits
    ("dec-expsgn2",  ["20 A=1E -2"]),      # blank between the marker and the sign
    ("dec-sfxh",     ["20 A=1 #"]),        # blank before a '#' type suffix
    ("dec-sfxp",     ["20 A=1 %"]),        # blank before a '%' type suffix
    # ⚠️ THE CLASSIFICATION BOUNDARY, REACHED THROUGH BLANKS.  D-LNBLANK's
    # ceiling was checked AFTER a lossy step and could not see a wrapped
    # accumulator; the analogous question here is whether the JOINED value still
    # decides int-vs-single.  32767 and 32768 differ by one and land on different
    # token types, so the pair reads the classification directly instead of
    # reasoning about where the bound sits.
    ("dec-int5",     ["20 A=3 2 7 6 7"]),  # joined = 32767 -> integer token
    ("dec-int6",     ["20 A=3 2 7 6 8"]),  # joined = 32768 -> single, NOT integer
    ("dec-mix",      ["20 A=1 0E 2"]),     # both axes at once: 10E2 = 1000
    ("dec-neg",      ["20 A=- 1"]),        # the blank is AFTER the unary minus,
                                           # i.e. before the scanner is entered
    # The other radices.  `lit-hex` says &H does not skip; a rule stated from one
    # radix is a sample of three.
    ("dec-oct",      ["20 A=&O1 7"]),      # octal (zerobas has &O: tokenise.inc:302)
    # ⚠️ INFORMATIONAL: zerobas' tk_hex knows &H and &O only.  If the references
    # accept &B this row measures a MISSING RADIX and not this defect -- a
    # neighbouring gap that earns its own item with these bytes attached.
    ("dec-bin",      ["20 A=&B1 1"]),
    # A DATA body is stored verbatim to the ':' on zerobas (tokenise.inc
    # tk_data_rest).  If the reference crunches numbers inside DATA the blank
    # rule would reach there too; if it does not, this is a bounding control
    # exactly like `lit-rem`.
    ("dec-data",     ["20 DATA 1 0"]),
    # --- round 2: WHAT HAPPENS WHEN THE THING PAST THE BLANK IS A FALSE START -
    # Round 1 answered rule L over rule G (`dec-trail`) and then widened the set
    # of characters that count as a CONTINUATION well past "a digit": the dot,
    # the exponent marker, the exponent's sign and a type suffix are all reachable
    # across a blank run.  That is a one-character lookahead -- and `E` is the one
    # continuation that can turn out NOT to be one, because a malformed exponent
    # (`1E` with no digits) has to roll back.
    #
    # ⚠️ SO THE LOOKAHEAD AND THE ROLLBACK ARE THE SAME DECISION, and rolling the
    # marker back without rolling the BLANKS back is a byte-level divergence no
    # round-1 row can see.  These rows put a false start behind every seam.
    ("dec-expbad",   ["20 A=1 EX"]),      # 'E' reached across a blank, then no digit
    ("dec-expbadsg", ["20 A=1 E+X"]),     # marker AND sign, still no digit
    ("dec-expboth",  ["20 A=1 E 2"]),     # blanks on BOTH sides of the marker
    ("dec-expblk",   ["20 A=1E 2 3"]),    # a blank INSIDE the exponent's digits
    ("dec-dotx",     ["20 A=1 .X"]),      # dot across a blank, no fraction digit
    ("dec-sfxb",     ["20 A=1 !"]),       # the third type suffix
    # ⚠️ INFORMATIONAL: a trailing blank at END OF LINE.  The MSX line editor may
    # strip it inside the input buffer, in which case this row measures the
    # editor and not the scan -- the same caveat `num-tab` carries.  The echo
    # guard is what tells the two apart.
    ("dec-eol",      ["20 A=1 "]),
    # --- round 3: the same false starts with NO BLANK IN THE WAY --------------
    # ⚠️ ROUND 2 SAID `1 EX` STORES A SINGLE 1 FOLLOWED BY `X` -- the blank AND
    # the marker both gone.  That is two claims at once, and only one of them is
    # about blanks.  zerobas' tkf_try_exponent rolls a malformed exponent back and
    # leaves the `E` for the ordinary tokeniser (sub/tkfloat.asm:~215, and its
    # header says in as many words that this is OWN-DESIGN, not oracle-pinned) --
    # so if the reference eats the marker with no blank present either, that is a
    # SEPARATE live divergence sitting under this one, and attributing it to the
    # blank rule would be the D-MFDOM trap: closing an item on a measurement that
    # belongs to a different defect.
    ("dec-expbad0",  ["20 A=1EX"]),       # CONTROL for dec-expbad: no blank
    ("dec-expbadsg0",["20 A=1E+X"]),      # CONTROL for dec-expbadsg: no blank
    ("dec-dotx0",    ["20 A=1.X"]),       # CONTROL for dec-dotx: no blank
    # ⚠️ AND `dec-eol` CANNOT BE READ WITHOUT THIS ROW.  A trailing blank is the
    # one payload the echo guard is structurally blind to (echo_missing rstrips
    # every screen row), so "the blank is gone" could be the crunch, the line
    # editor, or the injector.  REM keeps its tail VERBATIM on both references,
    # so a trailing blank there MUST survive the crunch -- if it does not, the
    # blank never reached the crunch and dec-eol measures the editor.
    #
    # ⚠️ BOTH TRAILING-BLANK ROWS ARE INFORMATIONAL *BY CONSTRUCTION*, and this
    # is an apparatus finding, not a choice: echo_missing() rstrips every screen
    # row, so a trailing blank can never be found in the echo no matter what the
    # machine did with it.  A payload whose delivery cannot be verified may not
    # gate -- it is reported, and it earns its reading only as a pair.
    ("dec-eolctl",   ["20 REMX "]),
    # --- round 4: the ENTRY to the literal scan, which is in the OTHER ROM ----
    # ⚠️ EVERY ROW ABOVE ENTERS `tk_float` ON A DIGIT.  A literal may also begin
    # with the DOT (`.5`), and that decision is taken in tk_loop's dispatch
    # (basic/tokenise.inc:70), which looks exactly ONE character past the '.' and
    # demands a digit.  A blank there is a cell no `tk_float` fix can reach, so a
    # slice that measured only the scanner would ship a hole its own rule
    # predicts -- the D-NOTOPEN2 trap, where 3 of 7 rows gave a different answer
    # than all 7.
    ("dec-dotlead0", ["20 A=.5"]),        # CONTROL: the '.'-led literal, no blank
    ("dec-dotlead",  ["20 A=. 5"]),       # a blank between the '.' and its digit
]

# --- the `exp` battery: D-EXPBAD, a MALFORMED exponent marker ----------------
# docs/spec-basic-expbad.md.  D-DECBLANK's denominator turned up four rows whose
# divergence has NOTHING to do with blanks (`20 A=1EX` reads the same with or
# without one), and filed them.  This battery is their denominator.
#
# TWO RULES, AND EVERY ROW IS CHOSEN TO SEPARATE THEM:
#
#   rule R (rollback) -- zerobas today.  A marker not followed by digits is put
#                        BACK; the literal classifies as if no exponent were
#                        typed, so `1EX` is the INTEGER 1 followed by `EX`.
#   rule C (consume)  -- both references.  The marker (and its sign) is EATEN and
#                        its mere presence forces the literal off the integer
#                        path: `1EX` is a SINGLE 1.0 followed by `X`.
#
# ⚠️ THE FILED ROWS PIN R-vs-C FOR `E` ONLY, AND ONLY WITH A LETTER BEHIND IT.
# Three things they cannot say, each of which changes the fix:
#   * `D` is the DOUBLE marker when the exponent is well formed.  Does a MALFORMED
#     `D` force double, or does the malformed path collapse to single?  Nothing
#     measured so far distinguishes "the marker was seen" from "the marker's
#     PRECISION was seen".  `dec-dmark` / `dec-dbad` are the only rows that can.
#   * tk_float SKIPS the type-suffix scan whenever has_exp is set (an oracle-
#     pinned quirk: `1e10#` leaves the `#` uneaten, sub/tkfloat.asm header).  If a
#     malformed marker sets has_exp too, then `1E#` must leave its `#` behind --
#     a consequence of the fix that no filed row tests.
#   * every filed row has D=1, where int and single are decided by the marker
#     alone.  `12345EX` is int-ELIGIBLE (D=5, <=32767), so R and C differ in the
#     token TYPE for a reason the D=1 rows cannot isolate.
EXP = [
    ("dec-eok",      ["20 A=1E1X"]),      # CONTROL: a WELL-FORMED exponent, then a
                                           # letter.  R and C agree -> 10, then `X`
    ("dec-emark",    ["20 A=1E"]),        # the marker with NOTHING after it
    ("dec-esign",    ["20 A=1E+"]),       # marker AND sign, nothing after
    ("dec-ebadneg",  ["20 A=1E-X"]),      # the '-' sign arm (only '+' was filed)
    # ★ THE PAIR THAT DECIDES WHETHER PRECISION SURVIVES A FAILED EXPONENT
    ("dec-dmark",    ["20 A=1D"]),        # D at EOL: double, or single?
    ("dec-dbad",     ["20 A=1DX"]),       # D then a letter
    # ★ THE SUFFIX CONSEQUENCE
    ("dec-ebadsfx",  ["20 A=1E#"]),       # '#' immediately behind the marker
    ("dec-ebadsfx2", ["20 A=1EX#"]),      # '#' behind the letter
    # ★ THE CLASSIFICATION CONSEQUENCE, at a digit count where it is visible
    ("dec-ebig",     ["20 A=12345EX"]),   # D=5 and <=32767: R -> a TWO-BYTE INT,
                                           # C -> a single.  Different token, not
                                           # just different trailing bytes
    ("dec-elow",     ["20 A=1ex"]),       # a LOWERCASE marker: is it a marker?
    # The other two scanners, as denominator.  A rule stated from `A=` alone is a
    # sample of the sites that crunch a number.
    ("dec-eref",     ["20 GOTO 1EX"]),    # a line-number REFERENCE (branch_lineno,
                                           # a different accumulator entirely)
    ("dec-edata",    ["20 DATA 1EX"]),    # CONTROL: a DATA body is verbatim
    # --- round 2: WHERE THIS RULE MEETS D-DECBLANK's -------------------------
    # ⚠️ THESE CELLS ARE CREATED BY THE FIX ITSELF and did not exist before it.
    # D-DECBLANK established that the cursor a literal scan reports is ONE PAST
    # THE LAST CHARACTER IT CONSUMED, so a blank run is kept unless what follows
    # it is consumed.  Making the marker consumable moves that boundary: in
    # `1E X` the marker IS consumed and the blank behind it is NOT, which no row
    # in either slice has ever asked.  Get the bookkeeping wrong and the blank
    # disappears (or the marker survives) with every filed row still green.
    ("dec-emarkblk", ["20 A=1E X"]),      # marker consumed, blank behind it kept?
    ("dec-emarkbl2", ["20 A=1E -X"]),     # blank, then a sign that IS consumed
    ("dec-esignblk", ["20 A=1E- X"]),     # sign consumed, blank behind IT kept?
    ("dec-dmarkblk", ["20 A=1D X"]),      # the same seam on the DOUBLE marker
    ("dec-edot",     ["20 A=1.EX"]),      # has_dot AND a failed marker together
    ("dec-ebadpct",  ["20 A=1E%"]),       # '%' normally forces INT -- skipped?
]

# --- the `nam` battery: DOES A BLANK BREAK A VARIABLE NAME? -------------------
# The TODO filed this as "`&B` is not a radix on MSX1 and zerobas half-crunches
# it anyway" (`dec-bin`, §1 of the characterization):
#
#     20 A=&B1 1   ref -> A<EF>&B1 1     VERBATIM
#                  zb  -> A<EF>&B1 <12>  the TRAILING 1 crunched
#
# ⚠️ AND THE `&` IS ALMOST CERTAINLY NOT THE SUBJECT. zerobas and both references
# AGREE about `&`: tk_hex (basic/tokenise.inc:294) knows `&H`/`&O`, and for `&B`
# or a bare `&` it does `dec hl` / `jp tk_copy` and copies the `&` verbatim --
# an oracle-pinned own-design descope its own header cites (`a=&b1010` ->
# `&B1010` ASCII on the VG-8020). The divergence is one byte further right, in
# the text `B1 1`, where `B1` is an ordinary VARIABLE NAME.
#
# TWO RULES, AND EVERY ROW IS CHOSEN TO SEPARATE THEM:
#
#   rule K (kill)   -- zerobas today. tk_loop reloads TKNAME into B and then
#                      ZEROES it at the top of every character; a blank reaches
#                      tk_copy, which never sets it again, so the in-a-name flag
#                      dies at every space and the next digit STARTS A NUMERIC
#                      CONSTANT.
#   rule P (persist)-- a blank is COPIED but changes no state, so the digit
#                      behind it still CONTINUES the name: `B1 1` is the single
#                      identifier `B11` stored verbatim, and `&` never mattered.
#
# ⚠️ AND `dec-oct` ALREADY ARGUES FOR P WITHOUT ANYBODY NOTICING. `20 A=&O1 7`
# reads `A<EF><0B><01><00> <18>` on BOTH references -- the octal token is not a
# name, so no name state survives it and the reference CRUNCHES the 7 exactly as
# zerobas does. Same shape as `dec-bin`, opposite reading, and the only
# difference between them is whether a NAME preceded the blank. That is P.
#
# So the first thing this battery does is ask the filed shape with NO `&` at all
# (`nam-digblk`). If that diverges too, the `&` in the filed row is a red herring
# and the item is a general tokeniser rule -- which changes both the SITE and the
# SIZE of the fix. The `&` axis is kept anyway, as denominator: a rule stated
# from the one row that happens to carry an `&` is a sample.
#
# ⚠️ THE MUST-NOT-MOVE CELLS ARE IN THE `lit`/`dec` BATTERIES, NOT HERE, and any
# knife or gate run on this battery has to carry them: `lit-assign` (`20 A=1 0`
# is the SINGLE literal 10 -- D-DECBLANK) and `lit-varname` (`20 A B=1` keeps its
# blank AND still crunches the 1). Scope with ONLY=nam,lit.
NAM = [
    ("nam-ctl",      ["20 A=B11"]),        # CONTROL: a name with digits, no blank
    ("nam-eqnum",    ["20 A= 1"]),         # CONTROL: a blank alone makes no name
                                           # state -- the digit still crunches
    # ★ THE ROW THAT DECIDES WHOSE DEFECT THIS IS: the filed shape, no '&'
    ("nam-digblk",   ["20 A=B1 1"]),       # K -> `B1 <12>`; P -> `B1 1` verbatim
    # ★ AND THE ROW THAT SAYS WHAT SETS THE STATE. If only nam-digblk diverges,
    # the flag is set by a DIGIT in a name; if this one diverges too, a LETTER
    # sets it and the rule is the whole identifier scan.
    ("nam-letblk",   ["20 A=B 1"]),
    ("nam-two",      ["20 A=AB 1"]),       # a two-letter name, not a one-char one
    ("nam-run",      ["20 A=B1  1"]),      # is ANY RUN of blanks transparent?
    ("nam-more",     ["20 A=B 1 0"]),      # TWO digits across TWO blanks: does the
                                           # whole run continue the name, or does
                                           # the flag survive exactly one hop?
    ("nam-op",       ["20 A=B 1+2"]),      # an operator must still BREAK the name:
                                           # the 2 crunches under both rules
    # ★ `$` is a type suffix, and whether it belongs to the name decides whether
    # this row follows nam-digblk or nam-eqnum. It separates "the in-a-name flag
    # persists" from the cruder "everything after a letter is verbatim".
    ("nam-sfx",      ["20 A=B$ 1"]),
    ("nam-lval",     ["20 B1 1=5"]),       # the same shape in an LVALUE position
    ("nam-print",    ["20 PRINT B1 1"]),   # after a KEYWORD token, not after '='
    ("nam-dot",      ["20 A=B .5"]),       # the '.'-led literal (tokenise.inc:70,
                                           # a one-char lookahead in the OTHER
                                           # file) reached across a name's blank
    # --- the `&` axis: the denominator of the filed row ----------------------
    ("nam-amp0",     ["20 A=&B11"]),       # CONTROL: the filed shape with NO blank
    # ★ IF `&` SETS STATE OF ITS OWN, THIS IS THE ROW THAT SAYS SO: a digit
    # DIRECTLY behind the '&', with no name in between. P -> crunched (the '&' is
    # inert); anything else means a second rule is hiding under the filed one.
    ("nam-amp1",     ["20 A=&1"]),
    ("nam-ampe",     ["20 A=&"]),          # a bare '&' at end of line
    ("nam-ampz",     ["20 A=&Z1 1"]),      # an unknown radix letter: `Z1` is a name
    ("nam-ampl",     ["20 A=&b1 1"]),      # lowercase, the case the filed oracle
                                           # `a=&b1010` was actually typed in
    # --- round 2: THE ROWS THAT SAY WHICH DEFECT EACH ROUND-1 ROW BELONGS TO ---
    # ⚠️ ROUND 1 CAME BACK P ON EVERY ROW BUT TWO, AND BOTH OF THOSE MAKE A CLAIM
    # ABOUT SOMETHING OTHER THAN BLANKS:
    #
    #   nam-dot  `20 A=B .5` -> `B .5`   the `.5` is NOT a float
    #   nam-sfx  `20 A=B$ 1` -> `B$ <12>` the digit IS crunched
    #
    # Read through the blank rule alone, the first says "a blank stops a literal
    # from starting" and the second says "a blank breaks a name after all" -- and
    # both readings are available only because nothing here pins what those rows
    # do with NO BLANK IN THE WAY. MS-BASIC allows `.` INSIDE an identifier
    # (`MY.VAR`), in which case `B .5` is the variable `B.5` and the row is about
    # the identifier CHARSET, not about blanks; and `$` is a type SUFFIX, which
    # ends an identifier wherever it appears. Attributing either to this defect
    # without its control is the D-MFDOM trap: closing an item on a measurement
    # that belongs to a different one.
    ("nam-dot0",     ["20 A=B.5"]),        # CONTROL for nam-dot: no blank. If this
                                           # reads `B.5` verbatim then '.' is an
                                           # IDENTIFIER character and nam-dot is a
                                           # SEPARATE defect to be filed, not fixed
    ("nam-sfx0",     ["20 A=B$1"]),        # CONTROL for nam-sfx: no blank
    ("nam-sfxp",     ["20 A=B% 1"]),       # a rule stated from `$` is a sample of
                                           # four suffixes; `%` is the second
    # ⚠️ A KEYWORD MATCH RUNS AT EVERY POSITION (tokenise.inc:93) and deliberately
    # leaves the in-a-name flag CLEAR, so under P the flag survives the blank and
    # is then killed by the keyword. Nothing measured says the reference agrees,
    # and a fix that makes blanks transparent inherits whatever this row says.
    ("nam-kw",       ["20 A=B AND 1"]),
    # ⚠️ A CELL THE FIX ITSELF CREATES. Under P the in-a-name flag is live when
    # the character behind the blank arrives, and three constructs are entered
    # WITHOUT consulting it: a keyword (nam-kw), a '.'-led literal (nam-dot) and
    # the `&H` radix scan. Two of the three are measured above; this is the third,
    # and it is the one that says the flag did not leak into tk_hex.
    ("nam-amph",     ["20 A=B &H1"]),
    # --- round 3: PLAIN PUNCTUATION, and this round exists because a KNIFE ----
    # 🔴 EVERY ROW ABOVE REACHES tk_copy THROUGH A BLANK, AN OPERATOR OR A TYPE
    # SUFFIX. Not one of them puts ORDINARY punctuation between a name and a
    # digit -- and tk_copy is the fallthrough target of the `is_letter` test, so
    # it is the single busiest exit in the whole loop. Knife K2 found the hole the
    # hard way: the first cut of this fix parked tk_blank immediately before
    # tk_copy, which put every punctuation character through a store of a register
    # `match_kw` had already clobbered, and all 31 rows stayed GREEN on whatever
    # value it happened to leave (spec §5, K2). These are the rows that would have
    # said so directly, and the ones that keep saying it.
    ("nam-paren",    ["20 A=B(1)"]),       # a subscript: '(' must break the name
    ("nam-parenblk", ["20 A=B( 1)"]),      # '(' THEN a blank: the '(' clears, the
                                           # blank preserves the CLEARED state
]

# --- the `dot` battery: IS '.' AN IDENTIFIER CHARACTER? (D-NAMDOT) -----------
# The DENOMINATOR of the defect D-NAMBLANK filed and did not fix. `nam-dot0`
# (`20 A=B.5`, NO BLANK IN IT) diverges on both references, so the claim is not
# about blanks at all -- and `nam-dot`/`nam-dot0` alone are a SAMPLE of two.
#
# TWO NAMED RULES, AND EVERY GATING ROW BELOW SEPARATES THEM:
#
#   rule F (float lead) -- a '.' is examined for a following digit at EVERY
#                          position, and a digit makes it lead a numeric
#                          constant. zerobas today (basic/tokenise.inc:81).
#   rule N (name char)  -- a '.' behind a LIVE name state CONTINUES the
#                          identifier; with no live name state it leads a
#                          literal exactly as today (`MY.VAR` is one name, and
#                          `.5` at the start of an expression is still 0.5).
#
# ⚠️ THE BOUNDING ROWS ARE THE POINT OF THIS BATTERY, not the divergent ones.
# A fix that reads "'.' is an identifier character" WITHOUT consulting the name
# state is a different rule from N, and it moves `dot-sfx`, `dot-paren` and
# `dot-kw` -- three cells that agree on all three sides TODAY. Those are the
# rows that tell N from "always ident", and neither filed row can.
#
# ⚠️ ONLY=dot ALSO SELECTS `nam-dot`/`nam-dot0` (the filed pair) AND the whole
# `dec-dot*` cohort -- `dec-dotlead0` (`20 A=.5`), `dec-dotlead` (`20 A=. 5`),
# `dec-dotpre`, `dec-dotpost`, `dec-dotx`, `dec-dotx0`. That is not an accident
# to be worked around: those are exactly the MUST-NOT-MOVE cells of a '.'-led
# literal, and a knife on this rule wants them in the same run for free.
DOT = [
    # --- the rows where F and N predict DIFFERENT bytes ---------------------
    ("dot-two",      ["20 A=B..5"]),       # F -> `B.` + a float; N -> `B..5`
    ("dot-dig",      ["20 A=B1.5"]),       # the name state set by a DIGIT carries
                                           # the dot too, or only a letter's does
    ("dot-many",     ["20 A=B.C.D"]),      # more than one dot in one identifier
    ("dot-blk2",     ["20 A=B . 5"]),      # a blank on BOTH sides of the dot: is
                                           # it the same rule across R-N1's blank?
    ("dot-lval",     ["20 B.5=7"]),        # LVALUE position, not just after '='
    ("dot-print",    ["20 PRINT B.5"]),    # after a KEYWORD token
    ("dot-op",       ["20 A=B.5+1"]),      # an operator must still BREAK the name
    # --- BOUNDING: where the name state is DEAD and the dot must still lead --
    # ⚠️ These agree on all three sides TODAY. They are what separates rule N
    # from "a '.' is an identifier char wherever it appears", and a fix that
    # moves any of them has implemented the wrong rule. Same shape as
    # `nam-paren`/`nam-parenblk`, which a KNIFE had to find in D-NAMBLANK.
    ("dot-sfx",      ["20 A=B$.5"]),       # a type suffix ENDS the identifier
    ("dot-paren",    ["20 A=B(.5)"]),      # '(' clears the state
    ("dot-kw",       ["20 A=B AND .5"]),   # a keyword clears the state
    ("dot-goto",     ["20 GOTO 1.5"]),     # a line-number REFERENCE: branch_lineno
                                           # is different code (D-LNBLANK R5)
    # --- CONTROLS: F and N predict the SAME bytes ---------------------------
    ("dot-ctl",      ["20 A=B."]),         # CONTROL: a dot with NO digit behind it
    ("dot-let",      ["20 A=B.C"]),        # CONTROL: a dot then a LETTER
    ("dot-start",    ["20 A=.B"]),         # CONTROL: dot at expression start, no
                                           # digit -- the `.5` cells' own control
    ("dot-str",      ['20 A$="B.5"']),     # CONTROL: inside a string literal
    ("dot-rem",      ["20 REM B.5"]),      # CONTROL: a REM tail is VERBATIM
    ("dot-data",     ["20 DATA B.5"]),     # CONTROL: a DATA body is VERBATIM
    # ⚠️ THE STORED BYTES CANNOT ANSWER THIS ONE and it is here to say so. Under
    # F and under N alike the '.' is copied and the `A` starts a name, so both
    # rules predict `.A<EF><12>`. Whether a name may BEGIN with a '.' is a
    # question only the `dotd-lead` say row can reach.
    ("dot-lead",     ["20 .A=1"]),
    # --- round 2: THE CELLS R-D2 MAKES REACHABLE FOR THE FIRST TIME ----------
    # ⚠️ ADDED BECAUSE THE ROUND-1 CONTROLS REFUTED THEIR OWN PREDICTION. Once a
    # '.' no longer needs a digit behind it (spec R-D2), the literal scanner is
    # entered on shapes nothing has ever asked it about: a '.' with NOTHING
    # after it, and a '.' whose next character is an EXPONENT MARKER. Round 1
    # measured a '.' followed by a LETTER and by an ASSIGNMENT, which is a
    # sample of the entry, not its surface -- the D-NOTOPEN2 trap. A rule may
    # not be shipped one row wider than its denominator.
    ("dot-eol",      ["20 A=."]),          # a bare '.' with nothing behind it
    ("dot-exp",      ["20 A=.E5"]),        # '.' straight into an exponent marker
]

# --- the `dir` battery: DIRECT MODE, which has no stored line to read ---------
# ⚠️ SAY-MODE ONLY, and it is here because direct mode is an EXECUTION MODE this
# project has repeatedly found uncovered while the verbs above it read as fully
# covered (docs/spec-basic-direct-mode-control-flow.md).  A line typed with no
# line number is crunched by the same tokeniser and then executed immediately, so
# it has no entry in TXTTAB and the memory readout cannot see it at all.
#
# Under rule T `PRINT 1 0` prints two numbers; under S it prints one.  MSX-BASIC
# pads a non-negative number with a leading blank and a trailing one, so the two
# readings are ` 1  0` and ` 10` -- different lengths, not just different spacing.
DIRB = [
    # ⚠️ THE BRACKETS ARE LOAD-BEARING AND THIS ROW HAD BEEN MISSING THEM. Every
    # SAY_ONLY row is read by `result_span_after_echo`, which returns the text
    # between the LAST '[' and its ']' (omsx_repl.py:518) -- so a payload that
    # prints no brackets can only ever read `<none>`, on EVERY side, which then
    # compares EQUAL and reports `agrees`. That is the same shape as the
    # chancost NOREAD guard: a sentinel that also means "no reading" is not a
    # measurement. Found 2026-07-31 while adding `dir-name` below, which had
    # inherited the same mistake. The row escaped the gate only because --say
    # rows are filtered out of `lnblank-acceptance` entirely; it was dormant, not
    # green. `PRINT 1 0` still asks the original question -- under K it prints two
    # numbers (` 1  0`) and under S one (` 10`) -- it just says so readably now.
    ("dir-print",    ['PRINT"[";1 0;"]"']),
    # ⚠️ THE STORED BYTES DO NOT SAY WHAT THE LINE MEANS, and the `nam` battery's
    # whole claim is that `B1 1` is the identifier `B11`. This asks the machine
    # instead of the byte gloss: assign through the blank, read back through the
    # joined name. Under P the two are the SAME VARIABLE and this reads 7; under
    # K the assignment is a syntax error and `B11` reads back 0.
    ("dir-name",     ["B1 1=7", 'PRINT"[";B11;"]"']),
]

# --- the `dotd` battery: WHAT A DOTTED NAME MEANS, not what it stores ---------
# ⚠️ SAY-MODE ONLY, and the byte gloss cannot substitute for it. `dot-lval` can
# only show that `B.5` was STORED as name bytes; whether the executor resolves
# those bytes to one variable -- and to WHICH one -- is a separate claim, and it
# is the claim that decides whether the run-time name scan (basic/vars.asm
# is_ident_cont / var_name_key) has to change at all.
#
# 🔴 AND THE ANSWER INVERTS THE BYTE BATTERY'S READING. The first cut of this
# battery asked `B.5=7` then `PRINT"[";B.5;"]"`, and BOTH references read
# `<none>` -- which compares EQUAL and would have reported `agrees`. Reading the
# SCREEN instead of the extracted value (the standing MO) showed why:
#
#     B.5=7               ->  Syntax error
#     PRINT"[";B.5;"]"    ->  `[ 0` then Syntax error   (no ']', hence no span)
#
# So the reference CRUNCHES `B.5` as verbatim name bytes and then REFUSES it at
# execute time: the run-time variable scanner stops at the '.', PRINT emits B's
# value (0) and chokes on the leftover `.5`. '.' is an identifier character to
# the TOKENISER and NOT to the EXECUTOR -- a genuine MSX1 asymmetry, and the
# reason `basic/vars.asm` must NOT be touched by this slice (spec §4).
#
# ⚠️ THE 2-SIGNIFICANT-CHARACTER QUESTION IS DISSOLVED, NOT ANSWERED. `B.5`
# never resolves to a variable at all, so asking whether its key is (B,.) --
# i.e. whether `B.9` is the same variable -- has no referent. That row is gone;
# `dotd-ctl` took its slot, because ERR=2 means nothing without a row that
# says what ERR reads when the SAME shape carries no dot.
#
# ⚠️ EVERY PAYLOAD PRINTS BRACKETS, AND `ERR` IS WHY THESE ROWS CAN. A payload
# whose statement ABORTS never reaches its own ']' -- so the very behaviour
# under test destroys the reading, and `<none>` on every side compares EQUAL
# (docs/nameblank-msx1-characterization.md §4.1). Asking ERR on the NEXT line
# always prints its brackets, and turns "did it abort" into a number.
DOTD = [
    ("dotd-var",     ["B.5=7", 'PRINT"[";ERR;"]"']),   # LVALUE: does it abort?
    ("dotd-ctl",     ["B5=7", 'PRINT"[";ERR;"]"']),    # CONTROL: same shape, NO
                                                       # dot -- ERR must read 0
    ("dotd-rd",      ["A=B.5", 'PRINT"[";ERR;"]"']),   # RVALUE, not just lvalue
    ("dotd-b5",      ["B.5=7", 'PRINT"[";B5;"]"']),    # nothing was assigned to B5
    ("dotd-lead",    [".A=1", 'PRINT"[";.A;"]"']),     # may a name BEGIN with '.'?
                                                       # (`.` is the NUMBER 0, so
                                                       # this prints TWO items)
]

# --- the `body` battery: WHERE THE BODY STARTS -------------------------------
# ⚠️ THE FIRST RUN PRODUCED THREE READINGS NO SINGLE RULE FITS, and the body
# offset is not a cosmetic detail -- it is part of the stored bytes a faithful
# implementation has to reproduce:
#
#     `20 REMX`  -> body `<8F>X`    -- the blank is GONE
#     `0 REMX`   -> body ` <8F>X`   -- the blank SURVIVES
#     `2 X=1`    -> body `X<EF><12>`-- gone again, and this is also one digit
#
# One digit and one blank gives a different answer in `0 REMX` than in `2 X=1`,
# so neither "digit count" nor "one blank is eaten" explains it on its own. This
# battery separates the three candidate variables -- how many DIGITS, how many
# BLANKS, and whether the VALUE 0 or the REM body is what is special -- by moving
# exactly one of them at a time. Reasoning did not produce a rule here; the rows
# are the only thing that will.
BODY = [
    ("body-d1",      ["1 REMX"]),         # 1 digit, 1 blank, non-zero
    ("body-d1b2",    ["1  REMX"]),        # 1 digit, 2 blanks
    ("body-d2",      ["12 REMX"]),        # 2 digits
    ("body-d3",      ["123 REMX"]),       # 3 digits
    ("body-d4",      ["1234 REMX"]),      # 4 digits
    ("body-z1",      ["0 REMX"]),         # the anomalous row, repeated here
    ("body-z2",      ["0  REMX"]),        # value 0, 2 blanks
    ("body-z0",      ["00 REMX"]),        # value 0 written with 2 digits
    ("body-zl",      ["01 REMX"]),        # a LEADING ZERO: value 1, 2 digits
    # ⚠️ `00 REMX` vs `01 REMX` says the discriminator is the VALUE and not the
    # leading digit -- but both reach that value with the digits ADJACENT. This
    # row reaches value 0 THROUGH a blank, which is the one way left for the rule
    # to be about the digit run rather than the value. A cell that agrees can
    # agree for the wrong reason; this is the row that says which.
    ("body-z00",     ["0 0 REMX"]),       # value 0, two digits, split by a blank
    ("body-x1",      ["1 X=1"]),          # 1 digit, non-REM body
    ("body-x2",      ["12 X=1"]),         # 2 digits, non-REM body
    ("body-x3",      ["123 X=1"]),        # 3 digits, non-REM body
    ("body-zx",      ["0 X=1"]),          # value 0, non-REM body
]

# --- the `ref` battery: a line-number REFERENCE inside a statement ------------
# tokenise.inc:444 branch_lineno -- DIFFERENT CODE from parse_lineno, and the
# TODO says in as many words to measure rather than assume it follows.
#
# The readout makes both halves visible at once: the crunched value appears as
# $0E,<lo>,<hi> and a blank that was COPIED rather than skipped appears as a $20
# byte. bl_yes copies blanks BEFORE the number verbatim, so `ref-sp` pins that
# behaviour separately from the blank INSIDE the number.
REF = [
    ("ref-ctl",      ["20 GOTO 10"]),         # CONTROL: $0E,0A,00
    ("ref-sp",       ["20 GOTO   10"]),       # CONTROL: leading blanks verbatim
    ("ref-goto",     ["20 GOTO 1 0"]),
    ("ref-gosub",    ["20 GOSUB 1 0"]),
    ("ref-then",     ["20 IF A THEN 1 0"]),
    ("ref-restore",  ["20 RESTORE 1 0"]),
    ("ref-run",      ["20 RUN 1 0"]),
    ("ref-resume",   ["20 RESUME 1 0"]),
    ("ref-onlist",   ["20 ON A GOTO 1 0,2 0"]),
    ("ref-oncomma",  ["20 ON A GOTO 1 0 , 2 0"]),
    # ⚠️ MEASURED, FILED, NOT FIXED (spec §7). zerobas emits $0E only for
    # GOTO/GOSUB/THEN/RESTORE/RUN/RESUME; LIST/DELETE/AUTO/RENUM are not in
    # bl_yes at all, so their arguments crunch as ordinary numeric literals. A
    # divergence here is a MISSING FEATURE sitting next to this defect, not this
    # defect -- it earns its own TODO item with these bytes attached. They are
    # measured anyway because leaving them out would sample the reference path
    # rather than cover it, which is the trap D-NOTOPEN2 hit (3 of 7 rows gave a
    # different answer than all 7).
    ("ref-list",     ["20 LIST 1 0"]),
    ("ref-delete",   ["20 DELETE 1 0"]),
    ("ref-auto",     ["20 AUTO 1 0"]),
    ("ref-renum",    ["20 RENUM 1 0"]),
    # ELSE <line> is a KNOWN, DOCUMENTED gap (tokenise.inc:441). Informational.
    ("ref-else",     ["20 IF A THEN 1 0 ELSE 2 0"]),
]

# --- the `err` battery: WHICH ERROR CLASS a rejected line number RAISES -------
# ⚠️ SAY-MODE ONLY. These rows read the SCREEN, not the stored line, so they
# cannot share the measurement run -- and their claim is not "what was stored"
# but "what does PRINT ERR read afterwards". The refusal happens at line ENTRY,
# not during RUN, so a handler cannot see it and asking afterwards is the only
# readout there is (the same reasoning basic_probe_linemax.py's `code` battery
# arrived at). `err-ctl` pins what ERR reads when NO error happened, so the
# reject row's value is a DIFFERENCE and not a number floating on its own.
ERRB = [
    ("err-over",     ["65530 REMX", 'PRINT"[";ERR;"]"']),
    ("err-ctl",      ["65529 REMX", 'PRINT"[";ERR;"]"']),
]
SAY_ONLY = {lb for lb, _l in ERRB + DIRB + DOTD}

CASES = NUM + BODY + LIT + DEC + EXP + NAM + DOT + REF + ERRB + DIRB + DOTD

# ⚠️ `dec-bin` AND `lit-varname` LEFT THIS SET IN D-NAMBLANK. Both were filed
# informational because nobody had a RULE for them: `dec-bin` was the `&B`
# half-crunch (whose `&` turned out to be inert -- nam-amp1) and `lit-varname` was
# "MS-BASIC's blank handling may be a property of the character fetch". R-N1 is
# that rule, so they are ordinary gating rows now: `dec-bin` is this defect's own
# filed row, and `lit-varname` is a bounding control of R-N3 (a blank inside a
# name is KEPT, and `=` still breaks the name).
INFORMATIONAL = {"num-tab", "ref-list", "ref-delete", "ref-auto", "ref-renum",
                 "ref-else", "dec-eol", "dec-eolctl"}
CONTROLS = {"num-plain", "num-nospace", "num-stop", "num-lead", "num-zero",
            "lit-ctl", "lit-str", "lit-rem", "ref-ctl", "ref-sp",
            "dec-ctl", "dec-hexctl", "dec-dotlead0",
            "dec-eok", "dec-edata",
            "nam-ctl", "nam-eqnum", "nam-amp0",
            # D-NAMDOT: F and N predict the SAME bytes for these five.
            "dot-ctl", "dot-let", "dot-start", "dot-str", "dot-rem", "dot-data",
            "dotd-ctl"}

# --- KNOWN_DIVERGE: two rows, and they are a DIFFERENT DEFECT -----------------
# ⚠️ These were never suppressions. Each entry recorded what zerobas ACTUALLY
# read, so a row passed only while it kept diverging in EXACTLY that way -- fix
# the behaviour and the entry stops matching, the gate goes RED, and the entry
# has to be RETIRED instead of rotting.
#
# Both cohorts left that way, one slice after the other:
#   * the five `lit-` rows D-LNBLANK filed -> retired by D-DECBLANK, when the
#     allowlist reported them as agreeing;
#   * the four `dec-expbad*` rows D-DECBLANK filed -> retired by D-EXPBAD
#     (docs/spec-basic-expbad.md), same message.
#
# 🔴 THE `0` ROWS ARE WHY D-EXPBAD WAS ITS OWN SLICE: `dec-expbad0` /
# `dec-expbadsg0` carry NO BLANK AT ALL and read exactly the same as their
# blanked twins, so the divergence could not belong to the blank rule. Closing it
# in D-DECBLANK would have been the D-MFDOM trap. They are ordinary gating rows
# now and still carry that separation.
#
#   * the two `nam-dot` rows D-NAMBLANK filed -> RETIRED by D-NAMDOT
#     (docs/spec-basic-namedot.md), same message: the allowlist reported them as
#     agreeing and the gate went red until the entries were deleted. Three
#     cohorts now, and not one of them rotted.
#
# ⚠️ AND IT IS NON-EMPTY AGAIN AS OF D-NAMDOT, for ONE row that is not that
# slice's defect either:
#
#     dot-goto  20 GOTO 1.5   ref -> <89> <0E><01><00>.<0E><05><00>
#                             zb  -> <89> <0E><01><00><1D>@P<00><00>
#
# 🔴 THE REFERENCE EMITS **TWO** LINE-NUMBER REFERENCES. It crunches `1` to
# $0E,0001, copies the '.' VERBATIM, and then crunches `5` to a SECOND $0E --
# its line-number LIST continuation treats a '.' as a separator that does not
# end the list, the same family as the empty-slot and blank-before-comma bugs
# already recorded in branch_lineno's own bl_num comment. That is
# DIFFERENT CODE from the tk_loop dispatch D-NAMDOT changes.
#
# ⚠️ AND THE EVIDENCE THAT IT IS INDEPENDENT IS THAT THE FIX DID NOT MOVE IT:
# zerobas read exactly these bytes before D-NAMDOT and after it. Neither R-D1 nor
# R-D2 predicts the row -- there is no name state after a line-number reference,
# so the '.' enters tk_float and takes `.5` with it. Filed in TODO.md with these
# bytes; closing it here would be the D-MFDOM trap.
#
# The entry is pinned to zerobas' EXACT reading, so it is a control and not a
# suppression: fix branch_lineno and it stops matching, the gate goes RED, and it
# has to be retired.
KNOWN_DIVERGE = {
    "dot-goto": "line 20 | <89> <0E><01><00><1D>@P<00><00>",
}


def battery(label):
    return label.split("-")[0]


# --- decoding ----------------------------------------------------------------
def gloss(b: bytes) -> str:
    """Body bytes -> a readable string: printable ASCII verbatim, everything else
    as <XX>. Byte-exact and legible in the same breath, so a characterization
    table can be read without a token decoder."""
    return "".join(chr(x) if 0x20 <= x < 0x7F else f"<{x:02X}>" for x in b)


def decode(hexstr):
    """One capture -> its reading. FOUR distinct values, never folded together:

      None                       -> NOCAPTURE: the run never produced a capture.
                                    ⚠️ FATAL. Two sides that both failed compare
                                    EQUAL and would print `agree`.
      "REFUSED (empty program)"  -> the line was rejected on entry. A BEHAVIOUR.
      "RUNT ..."                 -> a stored line too short to have a header.
      "line N | body"            -> the reading.

    The 2-byte LINK is dropped: it is an absolute address and the CF-3300's text
    base is not the VG-8020's."""
    if hexstr is None:
        return "NOCAPTURE"
    if hexstr == "":
        return "REFUSED (empty program)"
    b = bytes.fromhex(hexstr)
    if len(b) < 5:
        return f"RUNT {b.hex()}"
    lineno = b[2] | (b[3] << 8)
    body = b[4:]
    if body and body[-1] == 0:          # the line terminator, not a value byte:
        body = body[:-1]                # the link fixed the extent for us
    return f"line {lineno} | {gloss(body)}"


BAD = ("NOCAPTURE", "UNSTABLE")


def is_bad(v) -> bool:
    return any(v.startswith(p) for p in BAD)


# --- the echo guard ----------------------------------------------------------
# ⚠️ THE STANDARD ECHO GUARD SQUEEZES WHITESPACE, AND HERE THAT WOULD MAKE IT
# BLIND TO THE ONLY CHARACTER UNDER TEST. diskbasic_probe_chancost.py's
# echo_missing() collapses runs of blanks so a wrapped echo still matches; this
# subject IS the blank, so `2 0 REMX` and `20 REMX` would squeeze to the same
# string and a dropped space -- the exact mangle this guard exists to catch --
# would read as a clean echo. Blanks are compared INTACT. Nothing here is longer
# than 26 characters, so no echo wraps and the squeeze buys nothing anyway.
#
# ⚠️ AND NOT SQUEEZING IS WHAT EXPOSED THE LEFT MARGIN. The first cut compared
# `row.rstrip()` against the typed text and reported MANGLED for EVERY row on
# BOTH references -- while the memory pass was reading those same rows perfectly.
# The screen puts a two-column margin in front of everything:
#
#     row 0: '  Ok                 '
#     row 1: '  20 REMX            '
#
# The squeeze the other probes use had been hiding that margin, not tolerating
# it. `lstrip()` is NOT the fix either: `num-lead` types ' 20 REMX', whose
# leading blank is the measurement, and lstrip would eat it along with the
# margin. So the margin is MEASURED per capture -- the narrowest indent on the
# screen, which the prompt row always supplies -- and only exactly that many
# columns are removed. A payload's own leading blanks survive; an inserted or
# dropped one still fails.
def echo_missing(raw, lines, prompt):
    if raw is None:
        return ["<NO CAPTURE>"]
    rows = [raw[r * omsx_repl.COLS:(r + 1) * omsx_repl.COLS].rstrip()
            for r in range(omsx_repl.ROWS)]
    live = [r for r in rows if r.strip()]
    if not live:
        return ["<BLANK SCREEN>"]
    margin = min(len(r) - len(r.lstrip(" ")) for r in live)
    seen = {r[margin:] for r in live}
    seen |= {r[len(prompt):] for r in seen if prompt and r.startswith(prompt)}
    return [ln for ln in lines if ln not in seen]


# --- driving one side --------------------------------------------------------
def say(raw, lines, margin_lines):
    """What the machine PRINTED, with the case's own echo stripped off. A screen
    row built only from characters the CASE ITSELF typed is echo, not output.

    ⚠️ THE ECHO ALPHABET IS DERIVED FROM THE CASE, never hard-coded -- the same
    discipline basic_probe_linemax.py:364 arrived at after a hard-coded alphabet
    reported a battery's own echo as machine output on every row.

    This exists for ONE question the stored-line readout cannot answer: a row
    that reads `REFUSED (empty program)` says the line was rejected but not with
    WHICH ERROR. A refusal this project has to implement needs the reference's
    error CLASS, not just the fact of it."""
    if raw is None:
        return "NOCAPTURE"
    # ⚠️ `set(margin_lines)` would be a set of STRINGS, not characters, and would
    # exclude nothing -- the reset lines' own echo would then be reported as
    # machine output on every row. Join first.
    typed = set("".join(lines)) | set("".join(margin_lines))
    out = []
    # ⚠️ THE LAST ROW IS NOT OUTPUT -- the references draw the FUNCTION-KEY line
    # there (`color auto goto list run`) and zerobas draws nothing, so leaving it
    # in makes every row differ on furniture. Machine-agnostic and changes no
    # machine state, unlike `KEY OFF` (basic_probe_linemax.py:372).
    for r in range(omsx_repl.ROWS - 1):
        row = raw[r * omsx_repl.COLS:(r + 1) * omsx_repl.COLS].strip()
        for p in omsx_repl.PROMPTS:
            if row.startswith(p):
                row = row[len(p):].strip()
        if row and set(row) - typed:
            out.append(row)
    return "|".join(out) if out else "<nothing printed>"


def run_side(side, cases, repeat, echo, saymode=False):
    """Deliver `cases` to one machine and return a reading per case.

    ⚠️ REPEAT IS NOT OPTIONAL ON A REFERENCE PASS, AND THE REASON IS ASYMMETRIC.
    A dropped keystroke changes the stored bytes and looks EXACTLY like a
    semantic divergence. In the differential direction that produces a false
    FAIL -- loud, and safe. In the ORACLE-LOCK direction, where the reference's
    answer is written down as the oracle, it produces a false PASS forever. So
    every reference pass runs twice on independent boots and any row whose two
    readings differ is UNSTABLE and fatal. The two directions do not deserve the
    same guard."""
    cfg = dict(SIDES[side])
    diska = cfg.pop("diska")
    tmp = None
    if diska:
        tmp = tempfile.NamedTemporaryFile(suffix=".dsk", prefix=f"lnb_{side}_",
                                          delete=False).name
        shutil.copy(diska, tmp)
    reset = cfg.pop("reset")
    if echo or saymode:
        # The echo/say passes read the SCREEN, so every case must start from a cleared
        # one -- otherwise 30+ cases scroll each other off a 24-row display and a
        # missing echo means nothing. `SCREEN 0` is explicit because the CF-3300
        # boots Disk BASIC in SCREEN 1, whose name table this scraper does not
        # read. The MEMORY pass deliberately does NOT set it: a RAM reading is
        # mode-independent, so the memory pass observes each machine in its own
        # boot mode and only the guard pass perturbs it.
        reset = reset + ("SCREEN 0", "CLS")
    capture = "screen" if (echo or saymode) else ("stored_line", TXTTAB)

    # ⚠️ THE `err` ROWS MUST NOT SHARE A BOOT, AND BATCHED THEY MADE THEIR OWN
    # CONTROL AGREE FOR THE WRONG REASON. `reset` clears the PROGRAM; it does not
    # clear ERRCODE. Batched, `err-ctl` ran after `err-over` and read back the 2
    # that row had just raised -- on BOTH references:
    #
    #     err-ctl, batched after err-over : ref ` 2 `  -> agrees, measures nothing
    #     err-ctl, alone on a fresh boot  : the real value
    #
    # A row that reads leftover state cannot share a boot with the row that
    # leaves it. This is the identical trap basic_probe_linemax.py:276 recorded
    # for its `code` battery; it reappeared in a new probe within the hour.
    # ⚠️ AND BOOT-PER-CASE IGNORES `reset` ENTIRELY (omsx_repl.run_cases), which
    # is where the CF-3300's boot date-prompt CR and the say pass's `SCREEN 0`
    # live. Isolating the rows without carrying those forward left the CF-3300
    # sitting at its date prompt reading a SCREEN 1 name table through a 40-col
    # SCREEN 0 scraper -- `<none>` on both rows, which would have been reported
    # as the CF-3300 declining to answer. The isolation has to carry the setup,
    # so the reset lines are prepended to the case itself.
    batch = not any(lb in SAY_ONLY for lb, _l in cases)
    specs = [("direct", (list(reset) + lines) if not batch else lines)
             for _l, lines in cases]
    runs = []
    for _ in range(repeat):
        runs.append(omsx_repl.run_cases(
            cfg["machine"], specs, reset=reset, capture=capture,
            boot=cfg["boot"], step=cfg["step"], diska=tmp, batch=batch))
    if tmp:
        os.unlink(tmp)

    if saymode:
        out = []
        for i, (label, lines) in enumerate(cases):
            # ⚠️ SAY_ONLY ROWS MUST NOT USE say(). say() drops any row built
            # ONLY from characters the case typed, and `err-ctl`'s answer `[ 0 ]`
            # is exactly that -- the reset line `SCREEN 0` puts '0' into the
            # alphabet, so the control read `<nothing printed>` whether ERR was 0
            # or whether nothing printed at all. A sentinel that also means "no
            # reading" is not a measurement, and this one was sitting on the row
            # whose whole job is to be the contrast. These rows ANCHOR on the
            # echo of their own last line instead and read what follows it.
            # NOCAPTURE, not None: `is_bad` treats it as fatal, and a None here
            # would crash the printer rather than report an apparatus failure.
            rd = ((lambda raw: ("NOCAPTURE" if raw is None else
                                (omsx_repl.result_span_after_echo(raw, lines[-1])
                                 or "<none>")))
                  if label in SAY_ONLY else
                  (lambda raw: say(raw, lines, reset)))
            vals = [rd(r[i]) for r in runs]
            out.append(vals[0] if len(set(vals)) == 1
                       else f"UNSTABLE across {repeat} boots: {vals}")
        return out

    if echo:
        prompt = "ZB" if side == "zb" else "Ok"
        out = []
        for i, (label, lines) in enumerate(cases):
            miss = set()
            for r in runs:
                miss |= set(echo_missing(r[i], lines, prompt))
            out.append("ECHOED" if not miss else f"MANGLED not echoed: {sorted(miss)}")
        return out

    out = []
    for i, (label, _lines) in enumerate(cases):
        vals = [decode(r[i]) for r in runs]
        if len(set(vals)) != 1:
            out.append(f"UNSTABLE across {repeat} boots: {vals}")
        else:
            out.append(vals[0])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sides", default=",".join(REF_SIDES),
                    help="comma-separated: vg8020,cf3300,zb")
    ap.add_argument("--only", help="comma-separated label substrings")
    ap.add_argument("--repeat", type=int, default=2,
                    help="boots per side; 2 is mandatory for an ORACLE-LOCK pass")
    ap.add_argument("--echo", action="store_true",
                    help="run the ECHO GUARD pass (screen capture) instead of "
                         "the measurement: proves the cadence delivers these "
                         "payloads verbatim on this machine")
    ap.add_argument("--say", action="store_true",
                    help="report what each machine PRINTED (screen capture) "
                         "instead of the stored bytes: the only way to see the "
                         "error CLASS behind a `REFUSED (empty program)` row")
    ap.add_argument("--gate", action="store_true")
    args = ap.parse_args()

    sides = [s.strip() for s in args.sides.split(",") if s.strip()]
    for s in sides:
        if s not in SIDES:
            print(f"APPARATUS FAILURE: unknown side {s!r}")
            return 1
    want = [t.strip() for t in (args.only or "").split(",") if t.strip()]
    sel = [c for c in CASES if not want or any(t in c[0] for t in want)]
    # SAY_ONLY rows read the screen; they are invisible to the measurement
    # and echo passes rather than silently reading the wrong capture.
    sel = [c for c in sel if args.say or c[0] not in SAY_ONLY]
    if not sel:
        print("APPARATUS FAILURE: no rows selected")
        return 1
    if args.repeat < 1:
        print("APPARATUS FAILURE: --repeat must be >= 1")
        return 1

    cols = {s: run_side(s, sel, args.repeat, args.echo, args.say)
            for s in sides}

    wide = max(len(v) for vs in cols.values() for v in vs)
    wide = min(wide, 60)
    print(f"{'label':13} {'battery':8} " + " ".join(f"{s:{wide}}" for s in sides))
    for i, (label, lines) in enumerate(sel):
        tag = label + ("*" if label in INFORMATIONAL else
                       "^" if label in CONTROLS else "")
        print(f"{tag:13} {battery(label):8} "
              + " ".join(f"{cols[s][i][:wide]:{wide}}" for s in sides))
        print(f"{'':13} typed    {lines!r}")
    print("\n^ = two-sided control (T and S predict the SAME bytes)"
          "   * = informational, non-gating")

    if args.echo:
        # ⚠️ AN INFORMATIONAL ROW MAY FAIL THIS GUARD AS ITS MEASUREMENT, not as
        # an apparatus fault. `num-tab`'s whole premise is that the MSX line
        # editor may transform a TAB inside the input buffer -- if it does, the
        # echo cannot match what was injected, and that is the row's finding
        # rather than a mangle. Reported loudly, but it does not condemn the run;
        # a gating row that fails still does.
        soft, hard = [], []
        for i, (label, _l) in enumerate(sel):
            for s in sides:
                if cols[s][i] != "ECHOED":
                    (soft if label in INFORMATIONAL else hard).append(
                        f"{label} on {s}: {cols[s][i]}")
        if soft:
            print("\nINFORMATIONAL rows whose echo does not match what was "
                  "injected (the machine transformed it -- a reading, not a "
                  "fault):")
            for m in soft:
                print(f"  {m}")
        if hard:
            print("\nAPPARATUS FAILURE -- the harness did not type these "
                  "verbatim; no row in this run is a finding:")
            for m in hard:
                print(f"  {m}")
            return 1
        print("\nECHO GUARD: every gating payload typed verbatim on every side.")
        return 0

    # --- guards, BEFORE any row is read as a finding --------------------------
    bad = []
    for i, (label, _l) in enumerate(sel):
        for s in sides:
            if is_bad(cols[s][i]):
                bad.append(f"{label} on {s}: {cols[s][i]}")
    if bad:
        print("\nAPPARATUS FAILURE -- no row in this run is a finding:")
        for m in bad:
            print(f"  {m}")
        return 1

    if len(sides) < 2:
        return 0

    # --- the comparison -------------------------------------------------------
    # Every side must read IDENTICALLY. With two references that is "do the two
    # oracles agree with each other"; with zerobas in the list it is the
    # differential. Informational rows are reported but never gate.
    npass = ngate = 0
    diverge, stale = [], []
    for i, (label, _l) in enumerate(sel):
        vals = {cols[s][i] for s in sides}
        ok = len(vals) == 1
        # ⚠️ AN ALLOWLIST THAT MUST KEEP MATCHING IS A CONTROL; ONE THAT ONLY
        # SUPPRESSES IS ROT. A KNOWN_DIVERGE row passes only if it STILL diverges
        # AND zerobas still reads the EXACT value recorded when it was filed. Fix
        # the literal scanner and the entry stops matching, so the gate goes red
        # and the entry has to be retired -- which is the point. The references
        # must still agree with each other either way.
        if label in KNOWN_DIVERGE and "zb" in sides:
            ngate += 1
            refs = {cols[s][i] for s in sides if s != "zb"}
            want = KNOWN_DIVERGE[label]
            if ok:
                stale.append(f"{label}: allowlisted as divergent but the row now "
                             f"AGREES -- retire the entry")
            elif len(refs) > 1:
                stale.append(f"{label}: the REFERENCES disagree -- {refs}")
            elif cols["zb"][i] != want:
                stale.append(f"{label}: zerobas now reads {cols['zb'][i]!r}, "
                             f"filed as {want!r} -- the allowlist no longer "
                             f"describes the defect")
            else:
                npass += 1
            continue
        if label not in INFORMATIONAL:
            ngate += 1
            npass += 1 if ok else 0
        if not ok:
            diverge.append((label, {s: cols[s][i] for s in sides}))
    if stale:
        print("\nALLOWLIST FAILURE -- KNOWN_DIVERGE no longer describes zerobas:")
        for m in stale:
            print(f"  {m}")

    print(f"\n{npass}/{ngate} gating rows agree across {sides} "
          f"({len([l for l in KNOWN_DIVERGE if any(c[0] == l for c in sel)])} "
          f"of them allowlisted as KNOWN_DIVERGE, pinned to their exact value)")
    if diverge:
        print("\nDIVERGENT:")
        for label, d in diverge:
            note = "  (informational)" if label in INFORMATIONAL else ""
            print(f"  {label}{note}")
            for s, v in d.items():
                print(f"      {s:8} {v}")

    if stale:
        return 1
    return 1 if (args.gate and npass != ngate) else 0


if __name__ == "__main__":
    sys.exit(main())
