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

# --- the `expk` battery: DOES A RESERVED WORD AT THE MARKER SURVIVE? ----------
# D-EXPKW.  ⚠️ THIS IS THE CELL THE `exp` BATTERY ABOVE COULD NOT SEE.  Its header
# enumerates three things the filed rows cannot say; this is a FOURTH, and it is
# the one that broke two acceptance suites.  Every row D-EXPBAD measured put a
# NON-reserved tail behind the marker (`1E`, `1E+`, `1EX`, `12345EX`, `1E#`), so
# "the digits are optional and THERE IS NO FAILURE CASE" was generalised over a
# sample that contained no counter-example.  `EQV` and `ELSE` both begin with `E`:
#
#     PRINT 0 EQV 0     zerobas -> `0E` + variable `QV` + `0`   (three PRINT items)
#     IF 0 THEN A=1.5 ELSE PRINT 9    zerobas -> no $A1 at all, so NEITHER arm runs
#
# TWO RULES, AND EVERY ROW IS CHOSEN TO SEPARATE THEM:
#
#   rule B (blank)   -- the blank run before the marker is what protects the word,
#                       so `1EQV` would lose its `E` on the references too.
#   rule W (word)    -- a RESERVED WORD starting at the marker wins over the
#                       exponent, blank or no blank.  `1EQV` keeps `EQV`.
#
# The `0` rows (no blank) are the whole separation: rule B and rule W predict the
# SAME bytes for every blank-bearing row and DIFFERENT bytes without one.
# `expk-nonkw`/`expk-nonkwq` are the GREEN controls -- a non-reserved tail behind
# a blank must STILL have its marker eaten, or the rule is "a blank protects
# everything" and D-DECBLANK's `dec-expboth` (`1 E 2` -> 100) is refuted.
EXPK = [
    # ★ THE PAIR THAT SEPARATES B FROM W, on the operator that broke logicops
    ("expk-eqv",     ["20 A=1 EQV 2"]),   # blank + reserved word
    ("expk-eqv0",    ["20 A=1EQV 2"]),    # ★ NO BLANK -- B says eaten, W says kept
    # ★ THE SAME SEAM ON THE WORD THAT BROKE float-acceptance
    # ⚠️ THE CLAUSE IS `B=2`, NOT A BARE `2`, AND THAT IS NOT COSMETIC. The first
    # cut typed `20 A=1 ELSE 2`, where the references store the trailing number as
    # a line-number REFERENCE (`<0E><02><00>`, implicit GOTO) and zerobas stores
    # the integer constant `<13>`. That is the separately-filed `$0E`-refs
    # divergence (`ref-else`, still open), so the row diverged for TWO reasons at
    # once and could confirm neither: with the marker bug fixed it stayed red, and
    # with it unfixed a reader would have credited the wrong cause. An assignment
    # clause reaches the same $A1 and carries no line-number reference.
    ("expk-else",    ["20 A=1 ELSE B=2"]),  # ELSE crunches to COLON,$A1
    ("expk-else0",   ["20 A=1ELSE B=2"]),
    # ★ THE float-acceptance ROW'S OWN BYTES -- this is what ties the two suites
    # together.  If the $A1 is absent here, `reg.C.if_skip_over_float` is not a
    # tok_skip stride bug at all and its filed name is the wrong subject.
    ("expk-ifelse",  ["20 IF 0 THEN A=1.5 ELSE B=2"]),
    # 🔴 THIS WAS PINNED AS THIS BATTERY'S CONTROL AND IT MEASURED RED.  The SAME
    # line with an INTEGER literal, written on the assumption that only a FLOAT
    # reaches the exponent scan, so a surviving $A1 here would localise the defect
    # to the float path.  `1` reaches tkf_try_exponent exactly as `1.5` does --
    # that is the whole mechanism of `dec-ebig` -- so this line loses its $A1 too.
    # Re-aimed: it is the row that says `reg.C.if_skip_over_float` is not about
    # floats, and the fix must make BOTH lines green or it is aimed at the wrong
    # scanner.
    ("expk-ifelsei", ["20 IF 0 THEN A=1 ELSE B=2"]),
    # a third E-word, and a FUNCTION token rather than a statement one
    ("expk-erl",     ["20 A=1 ERL"]),
    # ★ GREEN CONTROLS: a NON-reserved tail must still lose its marker (rule C
    # from the `exp` battery), blank or not.  Without these, "a blank protects
    # the marker" would explain every red row above and be wrong.
    ("expk-nonkw",   ["20 A=1 EX"]),      # blank + non-reserved -> marker EATEN
    # 🔴 THIS ROW WAS PINNED AS A GREEN CONTROL AND THE REFERENCES REFUTED IT.
    # It was written to say "the rule is a WHOLE word, not the letters E,Q" by
    # predicting `EQ` -- no keyword -- loses its marker.  Both references KEEP it.
    # That single reading is what retired the keyword-match reading and sent this
    # slice to the `expw` alphabet walk.  It is re-aimed, not deleted: it is now
    # the bounding row that says the test is the LETTER and not the word.
    ("expk-nonkwq",  ["20 A=1 EQ"]),
    # the D marker has its own reserved words, and D carries PRECISION (dec-dmark)
    ("expk-dim",     ["20 A=1 DIM B"]),
    ("expk-dim0",    ["20 A=1DIM B"]),
    ("expk-nonkwd",  ["20 A=1 DX"]),      # CONTROL: D + non-reserved -> eaten,
                                          # and still a DOUBLE
    # lowercase: match_kw upcases, so W predicts the word is still seen
    ("expk-low",     ["20 A=1 eqv 2"]),
    # CONTROL: a WELL-FORMED exponent with the word behind it.  The word is not
    # at the marker, so B and W agree -- it must survive under either rule.
    ("expk-okdig",   ["20 A=1E2 EQV 3"]),
]

# --- the `expw` battery: THE WHOLE SECOND-LETTER ALPHABET ---------------------
# 🔴 ROUND 3 SAMPLED, AND THE SAMPLE GAVE TWO DIFFERENT WRONG RULES.  `EQV`/`ELSE`
# keep their marker; `ERL`/`EX` lose it -- so it is not "a reserved word wins".
# `EQ` keeps it too, and `EQ` is no word at all -- so it is not that either, and
# `EQ` was pinned as a CONTROL predicting the opposite.  Both candidate rules
# survive the round-3 rows; neither survives all of them.
#
# One row cannot separate two rules and neither can six.  This battery walks the
# CONTIGUOUS second-letter space -- `20 A=1 E<c>` and `20 A=1 D<c>` for all 26 --
# so the boundary is read off a complete space instead of guessed from the four
# letters that happened to start a keyword somebody thought of.
#
# The readout is the literal's own TOKEN, which says everything in one byte:
#   <12>              the marker was NOT consumed -- still the INTEGER 1
#   <1D>A<10><00><00> consumed as an E marker -- forced to SINGLE
#   <1F>A<10>x6       consumed as a D marker  -- forced to DOUBLE (precision kept)
EXPW = ([(f"expw-e{c.lower()}", [f"20 A=1 E{c}"]) for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"]
        + [(f"expw-d{c.lower()}", [f"20 A=1 D{c}"]) for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"])

# --- the `expb` battery: WHERE THE TWO-LETTER LOOKAHEAD'S BOUNDARIES ARE ------
# The walk answered the rule: the `E` marker survives iff the next character is
# `L` or `Q`, and the `D` marker never survives (26/26 eaten).  That set is not
# arbitrary -- `ELSE` and `EQV` are the ONLY reserved words starting with `E`
# that can legally FOLLOW a numeric constant, and no `D` word can.  But it is
# measurably a LETTER test and not a keyword match: `1 EQ` and `1 EL` keep the
# marker and neither is a word, while `1 ERL` -- which IS one -- loses it.
#
# ⚠️ THE FIX HAS TO PUT THE TEST SOMEWHERE, AND THE BLANK RUN DECIDES WHERE.
# D-DECBLANK established that `tkf_fetch` walks blanks transparently, and
# D-EXPBAD's own header records that committing at the wrong point silently EATS
# a blank while every filed row stays green.  A two-letter lookahead lands in
# exactly that seam, and nothing measured so far says whether the `L`/`Q` is
# reachable ACROSS a blank or only immediately behind the marker.  These rows are
# the whole difference between two implementations that pass every row above.
EXPB = [
    ("expb-elblk",   ["20 A=1 E L"]),     # ★ blank BETWEEN marker and the letter
    ("expb-eqblk",   ["20 A=1 E Q"]),     # ★ the same on the other protected letter
    ("expb-elsign",  ["20 A=1 E+L"]),     # a sign IS consumed -- does L still protect
                                          # behind it, or is the test only at the
                                          # character right after the marker?
    ("expb-elnoblk", ["20 A=1EL"]),       # no blank anywhere: protected (expk-eqv0's
                                          # shape, on the other letter)
    ("expb-ellow",   ["20 A=1 el"]),      # lowercase second letter, no keyword behind
    ("expb-elq3",    ["20 A=1 ELQ"]),     # an arbitrary THIRD letter: the rule is the
                                          # two-letter prefix, so this must be KEPT
    ("expb-eldig",   ["20 A=1E2L"]),      # CONTROL: a WELL-FORMED exponent eats E2,
                                          # so the L is not at a marker at all
    ("expb-eldot",   ["20 A=.5EL"]),      # a dot-leading literal reaches the same scan
    ("expb-elpct",   ["20 A=1EL%"]),      # marker NOT consumed -> has_exp clear -> the
                                          # suffix scan is NOT skipped (dec-ebadsfx's
                                          # quirk inverted).  The `%` must apply.
    ("expb-dlblk",   ["20 A=1 D L"]),     # CONTROL: D has NO protected letter, so the
                                          # blank seam cannot change its answer
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

# --- the `lnl` battery: HOW FAR DOES A LINE-NUMBER LIST RUN? (D-LNLIST) -------
# The DENOMINATOR of the defect D-NAMDOT filed and did not fix. `dot-goto`
# (`20 GOTO 1.5`) is ONE row, and one row is a SAMPLE of this surface, not the
# surface -- the trap D-NOTOPEN2 hit (3 of 7 rows gave a different answer than
# all 7).
#
#     20 GOTO 1.5   ref -> <89> <0E><01><00>.<0E><05><00>
#                   zb  -> <89> <0E><01><00><1D>@P<00><00>
#
# The reference crunches `1` to $0E,0001, copies the '.' VERBATIM, and crunches
# `5` as a SECOND $0E. THREE NAMED RULES, AND EVERY ROW BELOW SEPARATES THEM:
#
#   rule E (end)  -- the list ends at the first character that is not a digit
#                    and not a ','. zerobas today (tokenise.inc bl_num).
#   rule D (dot)  -- '.' JOINS ',' as a separator that does not end the list;
#                    everything else still ends it.
#   rule A (any)  -- after a branch keyword the crunch STAYS in line-number
#                    mode: every digit run becomes $0E,<v> and every other
#                    character is copied verbatim, until some terminator. What
#                    that terminator is (EOL? ':'? a quote? a keyword?) is
#                    itself unmeasured, so the rows below ask.
#
# ⚠️ E, D AND A ALL PREDICT THE SAME BYTES FOR `dot-goto` UNDER D AND A ALIKE.
# The filed row cannot tell D from A at all -- that is exactly why it may not be
# fixed from the row that found it. The `lnl-plus`/`lnl-semi`/`lnl-alpha` group
# is the only thing that can, and the `lnl-colon` group is the only thing that
# can say where the mode STOPS.
#
# ⚠️ ONLY=lnl ALSO SELECTS the `lnld` say rows (what the bytes MEAN). Use
# ONLY=lnl,ref,dot to pull in the must-not-move cells of both neighbours.
LNL = [
    # --- is it the '.', or ANY non-digit? -----------------------------------
    # Under D exactly one of these (the dot, measured as `dot-goto`) grows a
    # second $0E and all of these stay single; under A every one of them does.
    ("lnl-plus",     ["20 GOTO 1+5"]),      # an arithmetic operator
    ("lnl-minus",    ["20 GOTO 1-5"]),      # ...and the other sign
    ("lnl-star",     ["20 GOTO 1*5"]),
    ("lnl-semi",     ["20 GOTO 1;5"]),      # pure punctuation, no operator meaning
    ("lnl-hash",     ["20 GOTO 1#5"]),      # a type suffix character
    ("lnl-alpha",    ["20 GOTO 1X5"]),      # a LETTER: starts a name in tk_loop
    ("lnl-paren",    ["20 GOTO 1(5)"]),
    ("lnl-quote",    ['20 GOTO 1"5"']),     # a string literal: tk_string is
                                            # tk_loop's, not branch_lineno's
    # --- how far does the mode run, and what ENDS it? -----------------------
    ("lnl-three",    ["20 GOTO 1.5.7"]),    # THREE $0E's, or does it stop at two?
    ("lnl-colon",    ["20 GOTO 1.5:A=7"]),  # does the mode survive a STATEMENT
                                            # separator -- is the 7 crunched too?
    ("lnl-colctl",   ["20 GOTO 1:A=7"]),    # CONTROL for it: same shape, NO dot,
                                            # so the mode was never extended
    # --- blanks around the separator ----------------------------------------
    # bl_yes copies blanks verbatim BEFORE a slot, and D-LNBLANK R5 made a blank
    # INSIDE the number transparent. Whether the copied '.' sits inside that
    # machinery or beside it is a different question from whether it separates.
    ("lnl-blkl",     ["20 GOTO 1 .5"]),     # blank before the dot
    ("lnl-blkr",     ["20 GOTO 1. 5"]),     # blank after the dot
    ("lnl-blk2",     ["20 GOTO 1 . 5"]),    # both
    # --- the dot with NO number in front of it ------------------------------
    ("lnl-lead",     ["20 GOTO .5"]),       # is there a first $0E at all?
    ("lnl-bare",     ["20 GOTO ."]),        # a dot and nothing else
    # --- does it reach the OTHER branch keywords, or only GOTO? -------------
    # The `ref` battery already has a `1 0` row for each of the six; these mirror
    # them with a '.'. A rule that holds for GOTO alone is a different rule.
    ("lnl-gosub",    ["20 GOSUB 1.5"]),
    ("lnl-then",     ["20 IF A THEN 1.5"]),
    ("lnl-restore",  ["20 RESTORE 1.5"]),
    ("lnl-run",      ["20 RUN 1.5"]),
    ("lnl-resume",   ["20 RESUME 1.5"]),
    # --- interaction with the REAL comma list -------------------------------
    ("lnl-on1",      ["20 ON A GOTO 1.5,2"]),   # dot in the FIRST slot
    ("lnl-on2",      ["20 ON A GOTO 1,2.5"]),   # dot in a LATER slot
    # --- round 2: WHAT ELSE CLEARS THE MODE? --------------------------------
    # ⚠️ ADDED AFTER ROUND 1 REFUTED RULE D OUTRIGHT. `1+5` crunches to
    # $0E,1 <F1> $0E,5 and `1;5` to $0E,1 ; $0E,5, so the '.' the TODO filed this
    # under is not special at all -- rule A holds and the mode runs to the end of
    # the STATEMENT (`lnl-colon`: after the ':' the 7 is an ordinary $18). That
    # makes "what turns it off" the whole remaining question, and round 1 only
    # answered ':'. A rule may not be shipped one row wider than its denominator.
    #
    # 🔴 `lnl-thenpr` IS THE ROW THAT MATTERS MOST IN THIS PROBE. If a statement
    # keyword does NOT clear the mode, then `IF A THEN PRINT 5` crunches its 5 as
    # a LINE NUMBER and every such program breaks. zerobas cannot regress here
    # today because it has no mode at all -- an implementation of rule A can, and
    # this is the cell that would say so.
    ("lnl-thenpr",   ["20 IF A THEN PRINT 5"]),  # a STATEMENT keyword
    ("lnl-kw",       ["20 GOTO 1 AND 5"]),       # an OPERATOR keyword
    ("lnl-fnkw",     ["20 GOTO 1+ABS(5)"]),      # a FUNCTION keyword
    ("lnl-name",     ["20 GOTO X,5"]),           # a NAME -- `lnl-alpha` showed a
                                                 # name EATS a following digit, so
                                                 # the ',' is what makes this ask
                                                 # whether the mode itself survived
    ("lnl-qtail",    ['20 GOTO 1"A"5']),         # a STRING LITERAL
    ("lnl-hex",      ["20 GOTO &H10"]),          # a radix prefix, not a digit run
    # --- round 3: WHERE IS THE BOUNDARY? ------------------------------------
    # 🔴 ROUND 2 SPLIT THE TOKENS AND MY OWN `lnl-colon` TURNED OUT TO BE
    # CONFOUNDED. `+` `-` `*` do NOT clear the mode but `AND`, `ABS` and `PRINT`
    # do -- so it is not "a token clears it", and it is not a value threshold
    # either ($F1..$F3 keep it, $F6 AND drops it, and $91 PRINT is BELOW all of
    # them and drops it). And `lnl-colon` cannot say whether ':' clears the mode,
    # because the statement after it begins `A=7` and `lnl-name` shows a NAME
    # clears it on its own. A row whose payload carries TWO candidate causes
    # measures neither.
    ("lnl-colsep",   ["20 GOTO 1:5"]),      # ':' then a DIGIT -- no name in the way
    ("lnl-namemid",  ["20 GOTO 1,X,5"]),    # a name MID-LIST, not at the start
    # The symbol/word split, pinned across the operator range rather than
    # sampled at three points: $EE..$FC are contiguous tokens and round 2 read
    # only $F1/$F2/$F3 (keep) and $F6 (drop).
    ("lnl-slash",    ["20 GOTO 1/5"]),      # $F4
    ("lnl-pow",      ["20 GOTO 1^5"]),      # $F5
    ("lnl-or",       ["20 GOTO 1 OR 5"]),   # $F7 -- a WORD, like AND
    ("lnl-mod",      ["20 GOTO 1 MOD 5"]),  # $FB -- a WORD, above the symbols
    ("lnl-idiv",     ["20 GOTO 1\\5"]),     # $FC -- a SYMBOL, above the words
    ("lnl-eq",       ["20 GOTO 1=5"]),      # $EF
    ("lnl-lt",       ["20 GOTO 1<5"]),      # $F0
    ("lnl-gt",       ["20 GOTO 1>5"]),      # $EE
    # --- round 4: the ABBREVIATIONS, which do not go through the word path ---
    # ⚠️ ROUND 3 SAYS THE DISCRIMINATOR IS ALPHABETIC-vs-SYMBOLIC, and zerobas'
    # tokeniser already splits exactly there: word keywords go through match_kw,
    # symbolic operators through the tk_op_* arms. `?` and `_` are the two
    # characters that break that alignment -- they are SYMBOLS that expand to
    # WORD tokens ($91 PRINT, and CALL) without ever entering match_kw. If the
    # reference clears on them, an implementation hung off match_kw is wrong on
    # a shape as ordinary as `IF A THEN ?5`.
    ("lnl-quest",    ["20 IF A THEN ?5"]),        # '?' -> PRINT ($91)
    ("lnl-under",    ["20 IF A THEN _X 5"]),      # '_' -> CALL
    ("lnl-call",     ["20 IF A THEN CALL X 5"]),  # ...and the spelled-out CALL,
                                                  # which BYPASSES branch_lineno
                                                  # (tokenise.inc tk_call_name)
    # 🔴 `lnl-under` AND `lnl-call` ARE BOTH CONFOUNDED AND THE ROW BELOW IS WHY
    # THEY STAY ANYWAY. Both read `_X 5` / <CA> X 5 -- the trailing 5 is stored
    # as VERBATIM ASCII, so the CALL device-name scan reached across the blank
    # and took it before any numeric path could see it. They measure the name
    # scan, not the mode, and a row carrying two candidate causes measures
    # neither. `+` is the way past it: round 3 pins that a SYMBOLIC operator
    # leaves the mode armed, so a $0E here means CALL did not clear it and a
    # <16> means it did. (They are kept because that verbatim `5` is itself a
    # reading nobody had, and the zb column decides whether it is a new item.)
    ("lnl-callp",    ["20 IF A THEN CALL X+5"]),
    # 🔴 AND `lnl-callp` WAS EATEN TOO -- the reference stores `<CA> X5`, having
    # dropped the '+' ENTIRELY and kept the 5 as verbatim ASCII. Three rows, three
    # times the device-name scan reached the digit first. The way past it is not a
    # different operator but a different TERMINATOR: '(' is what ends an extended
    # statement's name (`_NAME(args)`), and round 3 already pins that a '(' on its
    # own leaves the mode ARMED (`lnl-paren`). So a $0E here means CALL did not
    # clear the mode and a <16> means it did -- with no name scan in the way.
    ("lnl-callpar",  ["20 IF A THEN CALL X(5)"]),
    ("lnl-underpar", ["20 IF A THEN _X(5)"]),
    ("lnl-apos",     ["20 GOTO 1'5"]),            # "'" -> REM: swallows the rest
    # 🔴 THE TRAP-PARSER SHAPES, PINNED HERE ON PURPOSE. `ON KEY GOSUB` and
    # `ON STRIG GOSUB` walk the crunched list looking for $0E, and bl_num's own
    # comment records what happened the last time this path emitted the wrong
    # number of them: the parsers ran off the end of their list and the executor
    # landed on a bare literal (`syntax error in 10`). Any change to how many
    # $0E bytes a list carries has to answer to these two rows.
    ("lnl-empty",    ["20 ON KEY GOSUB 100,,600"]),
    ("lnl-empty2",   ["20 ON STRIG GOSUB ,300"]),
    # --- CONTROLS: E, D and A predict the SAME bytes ------------------------
    ("lnl-ctl",      ["20 GOTO 15"]),       # CONTROL: the same digits, no dot
    ("lnl-nokw",     ["20 A=1.5"]),         # CONTROL: NO branch keyword, so `1.5`
                                            # is an ordinary single-precision
                                            # literal. MUST NOT MOVE: it is the
                                            # cell that says the rule is scoped to
                                            # branch_lineno and not to the number
                                            # scanner every other battery pins.
]

# --- the `cnm` battery: HOW FAR DOES THE `CALL` DEVICE-NAME SCAN REACH? -------
# D-CNAME. The DENOMINATOR of the defect D-LNLIST filed and did not fix. THREE
# rows found it, and all three were D-LNLIST rows that got EATEN -- none of them
# was designed to measure this at all:
#
#     20 IF A THEN _X 5      ref -> _X 5      zb -> _X <16>
#     20 IF A THEN CALL X 5  ref -> <CA> X 5  zb -> <CA> X <16>
#     20 IF A THEN CALL X+5  ref -> <CA> X5   zb -> <CA> X<F1><16>
#
# Three rows are a SAMPLE of this surface, not the surface -- the trap D-NOTOPEN2
# hit (3 of 7 rows gave a different answer than all 7), and D-LNLIST's own
# headline is that sampling three operators produced an apparent contradiction
# whose classes turned out INTERLEAVED.
#
# ⚠️ THESE ROWS DROP THE `IF A THEN`. The filed three carry it because they were
# asking a LINE-NUMBER MODE question; that question is ANSWERED (lnl-callpar /
# lnl-underpar) and carrying the mode here would put a second candidate cause in
# every payload -- the `lnl-colon` mistake, one slice later. At statement level
# the discriminator is crisp: a `5` the scan ate reads as ASCII `5`, a `5` the
# scan let go reads as the ordinary integer <16>. `cnm-thenctl` is the row that
# says the two contexts are the same scan.
#
# FOUR NAMED RULES, AND THE WALK BELOW SEPARATES THEM:
#
#   rule N (name)      -- the scan copies identifier chars (letter/digit,
#                         upcased) and STOPS at the first other character, which
#                         is then tokenised normally. zerobas today
#                         (tk_call_name/tcn_name; is_ident_cont is letter-or-
#                         digit, so not even '.' continues).
#   rule S (skip)      -- the scan copies identifier chars and blanks and DROPS
#                         every other character, running on until a TERMINATOR
#                         from some set. Fits both filed rows: the blank in
#                         `X 5` was kept, the '+' in `X+5` was dropped, and both
#                         kept their digit.
#   rule P (plus-only) -- rule N, except that '+' specifically is swallowed. Also
#                         fits both filed rows. It predicts `CALL X-5` ->
#                         `<CA> X<F2><16>` where S predicts `<CA> X5`.
#   rule V (verbatim)  -- everything copied verbatim to a terminator. ALREADY
#                         REFUTED by `lnl-callp` (the '+' is not in the stored
#                         line at all); named so the walk's rows can be read
#                         against it without re-deriving why it is dead.
#
# ⚠️ S AND P PREDICT THE SAME BYTES FOR EVERY ROW THAT FOUND THIS DEFECT. That is
# the whole reason for the walk: one row proves a defect EXISTS, not what the
# RULE is (docs/lnlist-msx1-characterization.md §1).
#
# ⚠️ MUST-NOT-MOVE, AND `cnm-format` IS PINNED HERE BECAUSE IT IS SHIPPED.
# `call format` -> `CA 20 46 4F 52 4D 41 54`: the extended name is NOT
# keyword-crunched, so FORMAT does not become FOR+MAT. Any widening of this scan
# has to answer to that cell, and to `diskbasic-acceptance`, which RUNS it.
CNM = [
    # --- CONTROLS: N, S and P predict the SAME bytes -------------------------
    ("cnm-ctl",      ["20 CALL X"]),        # name runs to EOL
    ("cnm-par",      ["20 CALL X(5)"]),     # '(' ends an extended name on every
                                            # rule (this is `lnl-callpar` with
                                            # the line-number mode taken out)
    ("cnm-thenctl",  ["20 IF A THEN CALL X"]),  # same scan after THEN?
    ("cnm-noblk",    ["20 CALLX5"]),        # no blank at all: match_kw still
                                            # takes CALL, then the name is `X5`
    ("cnm-format",   ["20 CALL FORMAT"]),   # THE SHIPPED ORACLE. MUST NOT MOVE.
    # --- the walk: `20 CALL X<c>5`, one character at a time -------------------
    # Under N every one of these stores `<CA> X` + the ordinary tokenisation of
    # `<c>5`; under S every one stores `<CA> X5` with <c> gone; under P only the
    # '+' row does. The operator range is walked CONTIGUOUSLY rather than
    # sampled, because that is exactly where D-LNLIST found the classes
    # interleaved ($FC keeps, $FB clears, with no threshold between them).
    ("cnm-plus",     ["20 CALL X+5"]),      # $F1 -- the filed row, at statement
                                            # level and with no mode in the way
    ("cnm-minus",    ["20 CALL X-5"]),      # $F2 -- S says `X5`, P says `X<F2><16>`
    ("cnm-star",     ["20 CALL X*5"]),      # $F3
    ("cnm-slash",    ["20 CALL X/5"]),      # $F4
    ("cnm-pow",      ["20 CALL X^5"]),      # $F5
    ("cnm-idiv",     ["20 CALL X\\5"]),     # $FC -- a SYMBOL above the words
    ("cnm-eq",       ["20 CALL X=5"]),      # $EF
    ("cnm-lt",       ["20 CALL X<5"]),      # $F0
    ("cnm-gt",       ["20 CALL X>5"]),      # $EE
    ("cnm-semi",     ["20 CALL X;5"]),      # pure punctuation, no operator meaning
    ("cnm-comma",    ["20 CALL X,5"]),      # the ARGUMENT separator of an
                                            # extended statement
    ("cnm-colon",    ["20 CALL X:5"]),      # the STATEMENT separator: if this is
                                            # not a terminator, `CALL X:PRINT`
                                            # cannot work at all
    ("cnm-dot",      ["20 CALL X.5"]),      # D-NAMDOT made '.' an identifier char
                                            # to the tokeniser -- but NOT to
                                            # is_ident_cont, which this scan uses
    ("cnm-hash",     ["20 CALL X#5"]),      # type-suffix characters: a name may
    ("cnm-dollar",   ["20 CALL X$5"]),      #  legitimately end at one of these
    ("cnm-pct",      ["20 CALL X%5"]),
    ("cnm-excl",     ["20 CALL X!5"]),
    ("cnm-amp",      ["20 CALL X&5"]),      # a radix prefix with no radix letter
    ("cnm-at",       ["20 CALL X@5"]),
    ("cnm-quest",    ["20 CALL X?5"]),      # a SYMBOL that expands to a word
                                            # token ($91 PRINT) -- dropped, or
                                            # does it terminate and expand?
    ("cnm-apos",     ["20 CALL X'5"]),      # ...and the other one ("'" -> REM,
                                            # which swallows the rest of the line)
    ("cnm-rpar",     ["20 CALL X)5"]),      # the CLOSING paren, unmatched
    ("cnm-quote",    ['20 CALL X"5"']),     # a string literal
    ("cnm-blk",      ["20 CALL X 5"]),      # the filed blank row, at statement level
    # --- blanks: the scan copies LEADING blanks today, but past the name? -----
    ("cnm-blk2",     ["20 CALL X  5"]),     # a RUN of blanks mid-name
    ("cnm-blkpre",   ["20 CALL  X 5"]),     # two blanks BEFORE the name
    ("cnm-twoword",  ["20 CALL X Y"]),      # blank between two name-ish words:
                                            # one name, or a name and a variable?
    ("cnm-digit1",   ["20 CALL 5X"]),       # a DIGIT as the first name character
    # --- upcasing -------------------------------------------------------------
    # ⚠️ `cnm-lower` MANGLES INTERMITTENTLY IN A BATCH -- RE-RUN IT ALONE BEFORE
    # READING A FAILURE AS A DIVERGENCE. It has come back `REFUSED (empty
    # program)` from zerobas three times (the pre-fix pass, and knives K1 and K4,
    # neither of which can reach a payload with no $21..$2F character and no
    # ':'), and read `<CA> ABC` every time it was re-run ALONE on the same
    # installed build. 🔴 The flake is intermittent BETWEEN runs and deterministic
    # WITHIN one -- openMSX is deterministic, so both boots of a `--repeat 2`
    # batch reproduced the refusal identically and the run reported no UNSTABLE.
    # `--repeat` cannot catch this class (docs/cname-msx1-characterization.md §3).
    ("cnm-lower",    ["20 CALL abc"]),      # does the reference upcase at all?
    ("cnm-lowmix",   ["20 CALL aB3d"]),     # ...through a digit, mid-name
    ("cnm-lowplus",  ["20 CALL x+y"]),      # lower case ACROSS a dropped char:
                                            # if S holds, is the `y` upcased too?
    # --- is a reserved WORD crunched inside the name? -------------------------
    ("cnm-kw",       ["20 CALL PRINT"]),    # the whole name IS a keyword
    ("cnm-kwmid",    ["20 CALL XFORY"]),    # ...and one buried inside it
    # --- is the name BOUNDED? -------------------------------------------------
    # ⚠️ 34 CHARACTERS, AND THE LENGTH IS A CONSTRAINT OF THE APPARATUS. The echo
    # guard matches whole SCREEN ROWS (echo_missing), so any payload longer than
    # the display width wraps and can never match -- the first cut of this row
    # was 43 chars and read `MANGLED` on BOTH references identically, which is
    # the signature of a geometry limit rather than a machine transform. 26 name
    # characters is still far past MSX's 16-byte PROCNM device-name buffer, so
    # the question survives the shortening.
    ("cnm-long",     ["20 CALL ABCDEFGHIJKLMNOPQRSTUVWXYZ"]),
    # --- ':' with a REAL statement behind it ----------------------------------
    # 🔴 THE MOST CONSEQUENTIAL ROW IN THE BATTERY. If ':' does not terminate the
    # scan, `CALL X:PRINT 5` stores one long name and the second statement never
    # exists. `cnm-colon` asks the same thing with a bare digit; this one asks it
    # where the answer decides whether ordinary programs still run.
    ("cnm-colstmt",  ["20 CALL X:PRINT 5"]),
    # --- round 2: the KEEP side, walked instead of sampled --------------------
    # 🔴 ROUND 1 SPLIT THE PUNCTUATION AND THE OPERATORS LANDED ON BOTH SIDES.
    # `+ - * /` are DROPPED and `^ \ = < >` are KEPT, so "it is an operator"
    # explains nothing; what separates them is the numeric range, `< '0'`. All
    # FIFTEEN characters of $21..$2F were walked, so the drop side is a
    # denominator. The keep side is NOT: round 1 read $3B..$40 plus $5C and $5E,
    # eight of the ~20 non-identifier characters at or above $3B, and D-LNLIST's
    # headline is that the classes turned out INTERLEAVED with no threshold
    # between them. These rows read every remaining printable one.
    ("cnm-lbrk",     ["20 CALL X[5"]),      # $5B -- between '@'..'Z' and '\'
    ("cnm-rbrk",     ["20 CALL X]5"]),      # $5D
    ("cnm-under",    ["20 CALL X_5"]),      # $5F -- ⚠️ '_' IS ITSELF THE CALL
                                            # ABBREVIATION. Kept, dropped, or a
                                            # terminator like ':' and '('?
    ("cnm-bq",       ["20 CALL X`5"]),      # $60 -- the last one below 'a'
    ("cnm-tilde",    ["20 CALL X~5"]),      # $7E
    # 🔴 `{` ($7B), `|` ($7C) AND `}` ($7D) ARE NOT DELIVERABLE THROUGH THIS
    # HARNESS AND THE ECHO GUARD IS THE ONLY REASON THAT IS KNOWN. Rows for all
    # three were written, run, and DELETED: `{` and `|` produced <NO CAPTURE> on
    # both references, and `}` -- the dangerous one -- produced a perfectly
    # ordinary reading that AGREED on both machines and was stable across two
    # boots:
    #
    #     cnm-rbrc   typed `20 CALL X}5`   both refs -> line 20 | <CA> X{5}
    #
    # A stored line containing a '{' and a '}' from a payload that had neither.
    # Without the guard that row would have been written up as a finding about
    # '}' in a name scan the machine never saw one in. They are recorded in
    # docs/cname-msx1-characterization.md §7 as NOT MEASURED rather than kept as
    # rows that cannot be delivered ([[apparatus-is-part-of-the-measurement]]).
    # --- round 2: the rules COMPOSED, not asked one at a time -----------------
    # Each round-1 row isolates one character. A rule that holds for each of them
    # separately can still be wrong about what happens when a drop, a kept blank
    # and a terminator meet in one name -- which is the shape a real extended
    # statement has.
    ("cnm-plpar",    ["20 CALL X+(5)"]),    # a DROPPED char immediately before
                                            # the '(' terminator
    ("cnm-mix",      ["20 CALL A+B C(1)"]),  # drop, kept blank and terminate,
                                            # all in one name
    # --- '_' parity: does the abbreviation take the SAME scan? ----------------
    # ⚠️ ONLY `_X 5` AND `_X(5)` HAVE EVER BEEN MEASURED. zerobas falls '_'
    # through into tk_call_name, so it is the same code -- but "the same code in
    # zerobas" is not a reading about the reference.
    ("cnm-uctl",     ["20 _X"]),
    ("cnm-upar",     ["20 _X(5)"]),
    ("cnm-uplus",    ["20 _X+5"]),
    ("cnm-uminus",   ["20 _X-5"]),
    ("cnm-usemi",    ["20 _X;5"]),
    ("cnm-ucolon",   ["20 _X:5"]),
    ("cnm-ublk",     ["20 _X 5"]),
    ("cnm-ulow",     ["20 _abc"]),
    ("cnm-ucolstmt", ["20 _X:PRINT 5"]),
]

# --- the `cnmd` battery: WHAT THE EATEN CHARACTERS MEAN -----------------------
# ⚠️ SAY-MODE ONLY. Storing `X5` instead of `X` + <F1> + <16> is only a
# divergence worth fixing if it changes what the machine DOES, and the CALL
# dispatcher matches the stored name against the extended-statement handlers in
# every slot -- so a name that grew a trailing `5` is a DIFFERENT name.
#
# ⚠️ THE PAYLOAD ABORTS ON PURPOSE, so the brackets may NOT live on the payload
# line: an untrapped error never reaches its own ']' and `<none>` on every side
# compares EQUAL (docs/namedot-msx1-characterization.md §4). `ERR` is asked on
# the NEXT line, in direct mode, where it prints its brackets either way.
#
# ⚠️ NO `CALL FORMAT` ROW. It is a shipped verb that WRITES A DISK and prompts;
# `cnm-format` pins its bytes and `diskbasic-acceptance` is what runs it.
CNMD = [
    ("cnmd-ctl",     ["10 CALL X", "RUN", 'PRINT"[";ERR;"]"']),   # CONTROL: a
                                            # plain unknown device name
    ("cnmd-blk",     ["10 CALL X 5", "RUN", 'PRINT"[";ERR;"]"']),
    ("cnmd-plus",    ["10 CALL X+5", "RUN", 'PRINT"[";ERR;"]"']),
    # 🔴 THE THREE ROWS ABOVE CANNOT SEPARATE THE RULES AND THIS PAIR IS WHY
    # THEY ARE NOT THE WHOLE BATTERY. An unknown device raises `Syntax error`
    # whether its name came out `X`, `X5` or `X 5`, so all three read the same on
    # every side -- they pin that the fix does not change the error CLASS, and
    # they measure nothing about the name. The only extended statement that
    # EXISTS on either reference is `CALL FORMAT`, which writes a disk, so a row
    # that reaches a live handler cannot be written (characterization §7).
    #
    # This pair asks the one semantic question that IS reachable: does ':' still
    # END the statement? `ON ERROR` + `RESUME NEXT` resumes at the NEXT
    # STATEMENT, so `A` reads 7 only if the ':' terminated the name scan and
    # `A=7` is a statement of its own. A widened scan that swallows ':' makes
    # line 20 a single statement and RESUME NEXT skips to line 30 with A=0.
    # ⚠️ A MUST-NOT-MOVE CELL, not a red row: both references AND zerobas
    # terminate at ':' today, and the pair exists to say the fix still does.
    ("cnmd-colstmt", ["10 ON ERROR GOTO 100", "20 CALL X:A=7",
                      '30 PRINT"[";A;ERR;"]"', "100 RESUME NEXT", "RUN"]),
    ("cnmd-colctl",  ["10 ON ERROR GOTO 100", "20 A=0:A=7",
                      '30 PRINT"[";A;ERR;"]"', "100 RESUME NEXT", "RUN"]),
]

# --- the `lnld` battery: WHAT A LINE-NUMBER LIST MEANS, not what it stores ----
# ⚠️ SAY-MODE ONLY, and the byte gloss cannot substitute for it. Two extra $0E
# bytes in a stored line are only a divergence worth fixing if the executor reads
# them, and the trap parsers (ON KEY/ON STRIG GOSUB) walk a crunched list looking
# for exactly that byte -- emitting more or fewer of them than today can run them
# off the end of their list. These rows ask the machine which $0E it honours.
#
# ⚠️ EVERY PAYLOAD PRINTS BRACKETS, AND `ERR` IS WHY THEY CAN. A payload whose
# statement ABORTS never reaches its own ']', so the very behaviour under test
# destroys the reading and `<none>` on every side compares EQUAL
# (docs/namedot-msx1-characterization.md §4). The target lines record WHERE the
# branch landed in A and the trailing PRINT reads A and ERR together, so one
# bracket span carries both "which line ran" and "did it abort".
LNLD = [
    # WHICH $0E does GOTO honour -- the first, or the last?
    ("lnld-goto",    ["10 GOTO 30.40", "30 A=30:END", "40 A=40:END", "RUN",
                      'PRINT"[";A;ERR;"]"']),
    ("lnld-ctl",     ["10 GOTO 30", "30 A=30:END", "40 A=40:END", "RUN",
                      'PRINT"[";A;ERR;"]"']),   # CONTROL: no dot -> 30, ERR 0
    # ⚠️ THESE TWO ARE THE PAIR THAT ANSWERS IT. If only the FIRST reference is
    # honoured, a missing SECOND target is harmless (30, ERR 0) and a missing
    # FIRST one aborts (0, ERR 8 = Undefined line number). If the LAST is
    # honoured the two readings swap. Either row ALONE is ambiguous.
    ("lnld-und2",    ["10 GOTO 30.99", "30 A=30:END", "RUN",
                      'PRINT"[";A;ERR;"]"']),   # second target does NOT exist
    ("lnld-und1",    ["10 GOTO 99.30", "30 A=30:END", "RUN",
                      'PRINT"[";A;ERR;"]"']),   # first target does NOT exist
    # Does the '.' make a new LIST SLOT? ON 2 GOTO picks the second entry, so
    # under "the dot separates entries" this lands on 40 and under "commas only"
    # it lands on 50. The single most decisive row in the battery.
    ("lnld-on",      ["10 ON 2 GOTO 30.40,50", "30 A=30:END", "40 A=40:END",
                      "50 A=50:END", "RUN", 'PRINT"[";A;ERR;"]"']),
    ("lnld-onctl",   ["10 ON 2 GOTO 30,50", "30 A=30:END", "40 A=40:END",
                      "50 A=50:END", "RUN", 'PRINT"[";A;ERR;"]"']),  # CONTROL: 50
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
SAY_ONLY = {lb for lb, _l in ERRB + DIRB + DOTD + LNLD + CNMD}

CASES = (NUM + BODY + LIT + DEC + EXP + EXPK + EXPW + EXPB + NAM + DOT + REF + LNL + CNM
         + ERRB + DIRB + DOTD + LNLD + CNMD)

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
            # D-EXPKW: B and W predict the SAME bytes for these five. The four
            # non-reserved tails must KEEP losing their marker (rule C) or the
            # reading "a blank protects the word" is what the reds really say.
            # D-EXPKW. ⚠️ `expk-ifelsei` WAS PINNED HERE AND MEASURED RED. It was
            # written to exonerate the literal scanner by using an INTEGER, on the
            # assumption that only a float literal reaches the exponent scan. It
            # does not: `1` reaches it too, so `IF 0 THEN A=1 ELSE B=2` loses its
            # $A1 exactly like the float line. It is a gating row, and the one
            # that says this defect has nothing to do with floats.
            "expk-nonkw", "expk-nonkwd", "expk-okdig",
            "expb-eldig", "expb-dlblk",
            "nam-ctl", "nam-eqnum", "nam-amp0",
            # D-NAMDOT: F and N predict the SAME bytes for these five.
            "dot-ctl", "dot-let", "dot-start", "dot-str", "dot-rem", "dot-data",
            "dotd-ctl",
            # D-LNLIST: E, D and A predict the SAME bytes for these three.
            "lnl-ctl", "lnl-nokw", "lnl-colctl", "lnld-ctl", "lnld-onctl",
            # ...and the two rows that got a digit PAST the CALL device-name
            # scan: '(' ends the extended-statement name and leaves the mode
            # armed (lnl-paren), so the <16> here is CALL/'_' clearing it.
            "lnl-callpar", "lnl-underpar",
            # D-CNAME: N, S and P predict the SAME bytes for these six. The
            # `format` cell is MUST-NOT-MOVE and shipped, not merely agreeing.
            "cnm-ctl", "cnm-par", "cnm-thenctl", "cnm-noblk", "cnm-format",
            "cnm-uctl", "cnm-upar", "cnmd-ctl", "cnmd-colctl"}

# --- KNOWN_DIVERGE: EMPTY, and every cohort that ever sat here has retired -----
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
#   * the ONE `dot-goto` row D-NAMDOT filed -> RETIRED by D-LNLIST
#     (docs/spec-basic-lnlist.md), same message a FOURTH time: the allowlist
#     reported the row as AGREEING and the gate went red until the entry was
#     deleted. Four cohorts now, and not one of them has rotted.
#
# 🔴 AND `dot-goto` IS THE ONE THAT SHOWS WHY THE PIN MATTERS MOST WHEN THE FILED
# TITLE IS WRONG. It was filed as "a '.' does not end a line-number list". The
# '.' turned out not to be the subject at all -- after a branch keyword the
# reference is in a MODE in which EVERY digit run is a $0E reference, `1+5` and
# `1;5` and `1\5` included, and `1.5.7` carries three. One row could not tell
# those rules apart, and the pin is what kept it measurable until a battery could.
#
#   * the THREE `lnl-` rows D-LNLIST filed -> RETIRED by D-CNAME
#     (docs/spec-basic-cname.md), same message a FIFTH time: the allowlist
#     reported all three as AGREEING and the gate went red until the entries were
#     deleted. FIVE cohorts now, and not one of them has rotted.
#
# 🔴 AND THE `lnl-` COHORT IS THE ONE THAT SHOWS THE PIN CATCHING A RULE THAT WAS
# WRONG IN BOTH DIRECTIONS. The three rows were filed as "the scan stops short --
# the reference reaches further", which is true and which suggests a rule that
# measurement REFUTED: `; < = > ? @ [ \\ ] ^ _ ` ~` are KEPT verbatim and the scan
# runs past them, while `+ - * /` are DROPPED and `^ \\ = < >` are not, so no
# property of the operator or its token byte separates them. The boundary is the
# ASCII range $21..$2F, which only a contiguous walk could show
# (docs/cname-msx1-characterization.md §2). Three rows agreed with two different
# wrong rules; the pin is what kept them measurable until a 56-row battery could
# tell them apart.
#
# ⚠️ THE SET IS EMPTY, AND THAT IS A STATE TO DEFEND RATHER THAN A DEFAULT. An
# empty allowlist means every gating row in this probe agrees with BOTH references
# right now. Adding an entry is how a KNOWN divergence stays measurable; leaving
# one in after it agrees is how an allowlist rots.
KNOWN_DIVERGE = {}


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


def run_side(side, cases, repeat, echo, saymode=False, isolate=False):
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
    # `isolate` forces boot-per-case: the SELF-HEAL pass (main) re-runs suspect
    # rows this way, so a batched delivery mangle cannot be reported as a finding.
    batch = (not isolate) and not any(lb in SAY_ONLY for lb, _l in cases)
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

    # --- SELF-HEAL: re-run every SUSPECT row boot-per-case ---------------------
    # ⚠️ A BATCHED DELIVERY MANGLE LOOKS EXACTLY LIKE A DIVERGENCE, AND `--repeat`
    # CANNOT SEE IT. openMSX is deterministic, so a harness race reproduces
    # IDENTICALLY on every boot: `cnm-lower` (`20 CALL abc`) read
    # `REFUSED (empty program)` on both boots of a `--repeat 2` batch -- no
    # UNSTABLE reported -- and read `<CA> ABC` every time it was re-run ALONE on
    # the very same installed build (docs/cname-msx1-characterization.md §3).
    # Repetition guards a FLICKERING fault; this guards a STICKY one.
    #
    # This is omsx_repl.run_differential's self-heal, ported: that helper re-runs
    # any disagreeing case boot-per-case so its verdicts "equal a full
    # boot-per-case run". This probe compares THREE sides, so it drives run_cases
    # per side and never inherited it.
    #
    # ⚠️ THE HEAL IS ASYMMETRIC AND MAY NOT BE MISTAKEN FOR `--repeat`. It re-runs
    # only rows that already look wrong, so it can turn a false FAIL into a pass
    # and can NEVER catch a false PASS. In the differential direction that is
    # exactly right (a mangle fails loudly and safely). In the ORACLE-LOCK
    # direction a mangle is a false PASS FOREVER, and `--repeat 2` remains the
    # only guard for it -- this changes nothing about that requirement.
    #
    # 🔴 INFORMATIONAL ROWS ARE HEALED TOO, AND THAT IS THE CONTROL. `ref-list`,
    # `ref-delete`, `ref-auto`, `ref-renum`, `ref-else`, `dec-eol` and `dec-eolctl`
    # diverge for real, measured reasons. They are re-run boot-per-case on every
    # gate and they MUST STILL DIVERGE -- which is what says the heal re-measures
    # a row rather than manufacturing agreement. A run in which they came back
    # agreeing would be the heal itself failing, not seven defects fixing
    # themselves ([[apparatus-is-part-of-the-measurement]]).
    if not args.echo:
        suspect = [i for i, (label, _l) in enumerate(sel)
                   if any(is_bad(cols[s][i]) for s in sides)
                   or len({cols[s][i] for s in sides}) > 1]
        if suspect:
            # ⚠️ REPORTED IN TWO GROUPS ON PURPOSE. The informational rows heal on
            # EVERY run by construction, so folding them in with the rest would
            # make a permanently non-empty list and drown the one line that
            # matters: a GATING row needing the heal. That is either a delivery
            # mangle or a real divergence, and either way a human should see it.
            exp = [i for i in suspect if sel[i][0] in INFORMATIONAL]
            unexp = [i for i in suspect if sel[i][0] not in INFORMATIONAL]
            print(f"SELF-HEAL: re-running {len(suspect)} suspect row(s) "
                  f"boot-per-case -- a batched mangle reads exactly like a "
                  f"divergence, and --repeat cannot tell them apart.")
            if unexp:
                print("  ⚠️ GATING rows needing the heal (a batched mangle, or a "
                      "real divergence -- read the healed value below):")
                for i in unexp:
                    print(f"      {sel[i][0]:13} batched: "
                          + " | ".join(f"{s}={cols[s][i]}" for s in sides))
            if exp:
                print("  informational rows (these heal every run BY DESIGN and "
                      "are the control: they must STILL diverge afterwards):")
                print("      " + ", ".join(sel[i][0] for i in exp))
            sub = [sel[i] for i in suspect]
            for s in sides:
                healed = run_side(s, sub, args.repeat, args.echo, args.say,
                                  isolate=True)
                for j, i in enumerate(suspect):
                    cols[s][i] = healed[j]
            laundered = [sel[i][0] for i in exp
                         if len({cols[s][i] for s in sides}) == 1]
            if laundered:
                print("\n🔴 SELF-HEAL FAILURE -- these rows diverge for measured "
                      "reasons and came back AGREEING, so the heal is "
                      "manufacturing agreement rather than re-measuring:")
                for lb in laundered:
                    print(f"      {lb}")
                return 1
            print()

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
