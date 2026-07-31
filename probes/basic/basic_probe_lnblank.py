#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-LNBLANK -- WHAT A BLANK INSIDE A LINE NUMBER DOES.

Spec: docs/spec-basic-lnblank.md.  Measurement: docs/lnblank-msx1-characterization.md.

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
    ("dir-print",    ["PRINT 1 0"]),
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
SAY_ONLY = {lb for lb, _l in ERRB + DIRB}

CASES = NUM + BODY + LIT + DEC + REF + ERRB + DIRB

INFORMATIONAL = {"num-tab", "ref-list", "ref-delete", "ref-auto", "ref-renum",
                 "ref-else", "lit-varname", "dec-bin", "dec-eol", "dec-eolctl"}
CONTROLS = {"num-plain", "num-nospace", "num-stop", "num-lead", "num-zero",
            "lit-ctl", "lit-str", "lit-rem", "ref-ctl", "ref-sp",
            "dec-ctl", "dec-hexctl", "dec-dotlead0"}

# --- KNOWN_DIVERGE: filed, not fixed, and PINNED TO ITS EXACT VALUE ----------
# ⚠️ These are not suppressions. Each entry records what zerobas ACTUALLY reads,
# so the row passes only while it keeps diverging in EXACTLY that way. Fix the
# behaviour and the entry stops matching, the gate goes red, and the entry has to
# be RETIRED instead of rotting. That is how the five `lit-` entries D-LNBLANK
# filed here left: D-DECBLANK fixed the decimal-literal scanner and the allowlist
# reported them as agreeing, which is the message that closed them.
#
# What is left is ONE neighbouring defect, D-EXPBAD (docs/spec-basic-decblank.md
# §5.1). Both references CONSUME an exponent marker that turns out not to
# introduce an exponent, and force the literal to SINGLE; zerobas rolls the
# marker back and leaves it for the ordinary tokeniser (sub/tkfloat.asm
# tkf_try_exponent, own-design and never oracle-pinned).
#
# 🔴 THE `0` ROWS ARE WHY IT IS NOT THIS DEFECT: `dec-expbad0` / `dec-expbadsg0`
# carry NO BLANK AT ALL and read exactly the same as their blanked twins. A
# measurement that belongs to another defect is the D-MFDOM trap, and pinning all
# four here is what keeps the two apart.
#
# ⚠️ AND THE BLANKED PAIR IS ALSO A MUST-NOT-MOVE CELL OF D-DECBLANK. `1 EX` must
# keep reading `<12> EX` -- a rollback that unwinds the marker has to unwind the
# blank run in front of it too, and these two rows are the only witness that it
# does (knife K3). If they ever read `<12>EX`, the fix ate a blank it rejected.
KNOWN_DIVERGE = {
    "dec-expbad":    "line 20 | A<EF><12> EX",
    "dec-expbadsg":  "line 20 | A<EF><12> E<F1>X",
    "dec-expbad0":   "line 20 | A<EF><12>EX",
    "dec-expbadsg0": "line 20 | A<EF><12>E<F1>X",
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
