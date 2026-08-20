#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""D-NAMSPC — a SPACE *inside* a variable reference's NAME, or before its type
suffix.

D-TGTSPC closed the `(` position (`NEXT A (1)`) and DEFERRED two rows it could
not reach, filing them as one residual in `TODO.md`:

  x.dollar  FOR A=1 TO 2 / NEXT A $(1)   both refs: NEXT without FOR   zb: Syntax error
  x.name    FOR AB=1 TO 2 / NEXT A B     both refs: OK                 zb: NEXT without FOR

🎯 `x.name` IS THE ONE THAT SIZES THIS. `NEXT A B` *completing a `FOR AB` loop*
means the reference treats a space INSIDE a variable name as insignificant. That
is `var_name_key` / `var_str_type` (basic/vars.asm), one cursor position BEFORE
the one D-TGTSPC touched -- and those two routines have **11 + 16 call sites**,
so the rule would reach every variable reference in every expression rather than
the nine lvalue targets D-TGTSPC fixed.

🔴 TWO ROWS ARE NOT A RULE, AND THE DENOMINATOR IS NOT THE LVALUE ONE. Four
questions decide how big this slice is, and no measured row asks any of them:

  1. WHERE may the space fall? Before the second letter (`A B`), before a DIGIT
     (`A 1`), before each of the four type suffixes (`A %` `A !` `A #` `A $`),
     more than once, and between two names run together (`AB CD`).
  2. 🎯 IS IT AN LVALUE RULE OR A UNIVERSAL ONE? `PRINT A B`, `A B=1` and
     `IF A B=1 THEN` never touch `tgt_parse`. If those collapse too, the fix is
     in the NAME SCAN and reaches the whole interpreter; if only targets do, it
     is something else. THIS IS THE READING THAT DECIDES THE SIZE OF THE SLICE.
  3. 🔴 DOES IT SURVIVE THE CRUNCH? If the reference's TOKENISER strips a space
     inside a name, the fix belongs in the tokeniser and every parser-side byte
     goes in the wrong file -- and ON SCREEN THE TWO HYPOTHESES ARE
     INDISTINGUISHABLE. The `t.*` rows read the STORED LINE BYTES back through
     TXTTAB (basic_probe_crunch.py's own instrument), which is the row that
     decided D-TGTSPC's whole design ([[read-the-artifact-when-the-screen-cannot-witness]]).
  4. WHAT DOES THE TWO-CHARACTER KEY DO? `A B C` and `AB CD` say whether a
     space-separated name still collides with the contiguous one.

🔴 AND THE CONSTRAINT THAT PRICES IT: A NAME THAT CONTAINS A KEYWORD. This
tree's tokeniser matches keywords at EVERY position mid-identifier, exactly like
MS-BASIC -- `SCORE` crunches as `SC` + `OR` ($F7) + `E` (docs/dev-workflow.md
§"Tokeniser quirks"). So `t.kw` / `t.and` ask whether the crunch also matches
ACROSS a space, and `z.kw` asks what the parser must therefore STILL refuse. A
space-skipping NAME SCAN cannot be cleverer than the tokeniser that ran first.

🟢 EVERY SPACED ROW CARRIES ITS OWN CONTIGUOUS POSITIVE CONTROL ON THE SAME
FIXTURE. Without it a red spaced row has two candidate causes
([[row-with-two-candidate-causes]]) -- `AB%` typed scalars, `DIM`, `SWAP`,
`READ` and `IF` are each machinery a spaced row would otherwise be accused of.

🔴 A CONTROL FAILING ON A **REFERENCE** AND ON **ZEROBAS** ARE DIFFERENT EVENTS
([[classify-a-control-failure-by-which-side-failed-it]]): a reference miss means
the fixture is broken -> exit 2, score nothing; a zerobas miss is an ordinary
divergence, scored, and it SCOPES its site.

⚠️ `r.hash` DISCRIMINATES ON CONSUMPTION, NOT ON IDENTITY, and says so rather
than being quietly counted with the other three suffixes: an unsuffixed name's
DEFtbl default is DOUBLE, so `AB` and `AB#` are the SAME cell either way. What
the row separates is "the `#` was eaten after the space" from "it was not"
(which leaves a stray `#` in the expression). The `%`, `!` and `$` rows separate
IDENTITIES and are the stronger three.

THE READING is the `[...]` span printed BY THE RUN, taken from the screen tail
after `RUN` -- never the whole screen ([[readout-blind-to-its-own-subject]]) --
except for the `t.*` rows, whose reading is the stored line's token bytes.

🔴 AND `<RUN SCROLLED OFF>` IS A READING, NOT A SILENCE. The first draft of
`bracket()` returned `<NO OUTPUT>` whenever `RUN` was no longer on the SCREEN 0
page. Five rows read that way, and every one is a zerobas RUNAWAY: `PRINT A 1`,
`PRINT AB %`, `PRINT AB !`, `PRINT AB #` and `PRINT AB $` fill the screen with
` 0 ` forever, because the PRINT item loop never advances past the character
after the name. Recording a HANG as "no output" would have understated the
divergence these rows measure -- they are not "a Syntax error instead of a
value", they are a program that does not stop.

Clean-room: observed screen output and observed RAM only; both reference ROMs
are black boxes.
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

TXTTAB = 0xF676   # sysvar: 2-byte LE pointer to the BASIC text base

SIDES = {
    "vg8020": dict(machine="Philips_VG_8020", boot=8.0, step=2.5,
                   reset=("NEW",), diska=False),
    "cf3300": dict(machine="National_CF-3300", boot=14.0, step=4.5,
                   reset=("", "SCREEN 0", "NEW"), diska=True),
    "zb":     dict(machine=ZB_MACHINE, boot=8.0, step=2.5,
                   reset=("NEW",), diska=True),
}

# (label, kind, [lines])
#   kind "tok" -> the STORED line's body bytes (hex); the lines are already
#                 numbered and are never RUN
#   kind "run" -> the `[...]` span the RUN printed; lines are numbered 10,20,..
CASES = [
    # === 0. THE TOKENISER — is the space even THERE? the row that decides
    #        WHICH FILE the fix belongs in. =================================
    ("t.ctl",     "tok", ['1 AB=1']),
    ("t.name",    "tok", ['1 A B=1']),
    ("t.dctl",    "tok", ['1 AB$="X"']),
    ("t.dollar",  "tok", ['1 AB $="X"']),
    ("t.digctl",  "tok", ['1 A1=1']),
    # 🔴 THE `TKNAME` QUESTION, AND IT IS THE ONE THAT COULD MOVE THE FIX INTO
    # THE TOKENISER. A digit is copied VERBATIM only while the in-name flag
    # ($E028) says we are mid-name; otherwise it BEGINS A NUMBER LITERAL. If a
    # space clears that flag, `A 1` stores `A` + a numeric constant and no
    # parser-side name scan can ever rejoin them.
    ("t.dig",     "tok", ['1 A 1=1']),
    # 🔴 THE KEYWORD CONSTRAINT. `SCORE` crunches as `SC` + `OR` + `E` here and
    # on both references. Does the crunch also match a keyword ACROSS a space?
    ("t.kwctl",   "tok", ['1 SCORE=1']),
    ("t.kw",      "tok", ['1 SC ORE=1']),
    ("t.andctl",  "tok", ['1 AND=1']),
    ("t.and",     "tok", ['1 A ND=1']),
    # ...and the same question from the other side: the CONTIGUOUS form is a
    # keyword and the SPACED form is not, which is what says the match is
    # POSITIONAL and a space genuinely blocks it.
    ("t.absctl",  "tok", ['1 ABS=1']),
    ("t.abs",     "tok", ['1 A BS=1']),

    # === 1. R-VALUE — a space inside a name in an EXPRESSION ===============
    #        (ev_f_var / str_eval_one -> var_str_type + var_name_key). NONE of
    #        these reaches tgt_parse: this group is what says whether the rule
    #        is UNIVERSAL or merely an lvalue one.
    ("c.let",     "run", ['AB=7', 'PRINT"[";AB;"]"']),
    ("r.name",    "run", ['AB=7', 'PRINT"[";A B;"]"']),
    ("r.multi",   "run", ['AB=7', 'PRINT"[";A  B;"]"']),
    # 3rd+ name chars are consumed and ignored everywhere else in this tree;
    # these two say whether that still holds once a space is in the middle.
    ("r.three",   "run", ['AB=7', 'PRINT"[";A B C;"]"']),
    ("r.run",     "run", ['AB=7', 'PRINT"[";AB CD;"]"']),
    # 🔴 THE `A=3` LINE IS LOAD-BEARING AND WAS ADDED BY DRAFTING THE KNIVES
    # FIRST. Without it `A1` and `A` are never separated, so a cut that folds a
    # digit second character into the ignored 3rd+ tail corrupts the key
    # SYMMETRICALLY -- the store and the read-back both land in the same wrong
    # cell and every digit row stays green ([[knife-that-reddens-nothing-is-the-finding]]).
    ("r.digctl",  "run", ['A1=7', 'A=3', 'PRINT"[";A1;"]"']),
    ("r.dig",     "run", ['A1=7', 'A=3', 'PRINT"[";A 1;"]"']),
    ("r.strctl",  "run", ['AB$="HI"', 'PRINT"[";AB$;"]"']),
    ("r.instr",   "run", ['AB$="HI"', 'PRINT"[";A B$;"]"']),
    ("r.dollar",  "run", ['AB$="HI"', 'PRINT"[";AB $;"]"']),
    ("r.pctctl",  "run", ['AB%=7', 'PRINT"[";AB%;"]"']),
    ("r.pct",     "run", ['AB%=7', 'PRINT"[";AB %;"]"']),
    ("r.bangctl", "run", ['AB!=7', 'PRINT"[";AB!;"]"']),
    ("r.bang",    "run", ['AB!=7', 'PRINT"[";AB !;"]"']),
    ("r.hashctl", "run", ['AB#=7', 'PRINT"[";AB#;"]"']),
    ("r.hash",    "run", ['AB#=7', 'PRINT"[";AB #;"]"']),

    # === 2. ASSIGNMENT — the space on the STORE side (ex_let) ==============
    #        read back through the CONTIGUOUS name, so a green row is a claim
    #        about the KEY and not merely about the parse surviving.
    ("a.name",    "run", ['A B=7', 'PRINT"[";AB;"]"']),
    ("a.dig",     "run", ['A 1=7', 'A=3', 'PRINT"[";A1;"]"']),
    ("a.str",     "run", ['A B$="HI"', 'PRINT"[";AB$;"]"']),
    ("a.dollar",  "run", ['AB $="HI"', 'PRINT"[";AB$;"]"']),
    # the TWO-CHARACTER KEY: a fully spaced 3-char name must still key (A,B)
    ("a.sig",     "run", ['A B C=7', 'PRINT"[";AB;"]"']),

    # === 3. OTHER STATEMENT SURFACES — each a different var_name_key /
    #        var_str_type caller, none of them tgt_parse's ==================
    ("s.ifctl",   "run", ['AB=7', 'IF AB=7 THEN PRINT"[OK]"']),
    ("s.if",      "run", ['AB=7', 'IF A B=7 THEN PRINT"[OK]"']),
    ("s.forctl",  "run", ['FOR AB=1 TO 2', 'NEXT AB', 'PRINT"[OK]"']),
    ("s.for",     "run", ['FOR A B=1 TO 2', 'NEXT AB', 'PRINT"[OK]"']),
    # ⇐ THE RESIDUAL'S OWN ROW: D-TGTSPC's deferred `x.name`, verbatim.
    ("s.next",    "run", ['FOR AB=1 TO 2', 'NEXT A B', 'PRINT"[OK]"']),
    ("s.dimctl",  "run", ['DIM AB(3)', 'AB(1)=7', 'PRINT"[";AB(1);"]"']),
    ("s.dim",     "run", ['DIM A B(3)', 'AB(1)=7', 'PRINT"[";AB(1);"]"']),
    ("s.ary",     "run", ['DIM AB(3)', 'A B(1)=7', 'PRINT"[";AB(1);"]"']),
    ("s.readctl", "run", ['DATA 7', 'READ AB', 'PRINT"[";AB;"]"']),
    ("s.read",    "run", ['DATA 7', 'READ A B', 'PRINT"[";AB;"]"']),
    ("s.swapctl", "run", ['AB=7', 'CD=9', 'SWAP AB,CD',
                          'PRINT"[";AB;CD;"]"']),
    ("s.swap",    "run", ['AB=7', 'CD=9', 'SWAP A B,CD',
                          'PRINT"[";AB;CD;"]"']),

    # === 4. THE KEYWORD CONSTRAINT, AT RUNTIME ============================
    # 🎯 `A ND` is NOT the AND token (t.and): `ND` is no keyword, so the spaced
    # form is an ordinary name while the CONTIGUOUS `AND` is $F6. The reading
    # says which variable the reference formed out of it.
    ("k.and",     "run", ['AN=7', 'PRINT"[";A ND;"]"']),
    # ...and the same for a FUNCTION name: `ABS` is a token, `A BS` is not.
    ("k.abs",     "run", ['AB=7', 'PRINT"[";A BS;"]"']),

    # === 5. THE NEGATIVE CONTROLS =========================================
    # 🔴 A SPACE-SKIPPING NAME SCAN MUST NOT BE CLEVERER THAN THE TOKENISER
    # THAT ALREADY RAN. `SC ORE` carries the `OR` token in its middle (t.kw), so
    # no parser can read it back as the name `SCORE`, and this row is what stops
    # "the fix works" from meaning "the fix rewrites the crunch"
    # ([[gate-whose-answer-is-an-error-passes-a-dead-subject]]).
    ("z.kw",      "run", ['SC ORE=7', 'PRINT"[OK]"']),
    # 🎯 THE CONVERSE OF `s.next`, AND IT IS THE ROW THAT SAYS THE SPACED NAME
    # IS A DIFFERENT VARIABLE RATHER THAN TOLERATED JUNK. There is no `FOR AB`
    # frame here, so if `A B` really is the name `AB` the loop must NOT close.
    ("z.miss",    "run", ['FOR A=1 TO 2', 'NEXT A B', 'PRINT"[OK]"']),

    # === 6. A TRAILING SPACE AFTER THE NAME — the "must not disturb" set ===
    # A name-scan skip advances the cursor past trailing spaces on the way to
    # looking for a suffix, exactly as D-TGTSPC's did one position later. These
    # three are GREEN on all three sides BEFORE the fix, which is what makes
    # them able to catch a widened scan that eats one delimiter too many.
    ("w.let",     "run", ['AB =7', 'PRINT"[";AB;"]"']),
    ("w.print",   "run", ['AB=7', 'PRINT"[";AB ;"]"']),
    ("w.for",     "run", ['FOR AB =1 TO 2', 'NEXT', 'PRINT"[OK]"']),
    ("w.comma",   "run", ['AB=7', 'CD=9', 'SWAP AB ,CD',
                          'PRINT"[";AB;CD;"]"']),

    # === 7. 🔴 WHAT THE JOIN COSTS — the ONE construct it takes away ========
    # `AS` is NOT in `basic/kwtable.inc` and is NOT a token: `ex_field` reads it
    # as the two literal characters 'A','S' after a full `eval` of the width
    # (basic/field.asm:272). So a NAME as the width is followed by bare letters,
    # and a name scan that skips spaces must swallow them.
    # 🎯 AND THE REFERENCE DOES EXACTLY THAT -- IT REFUSES THE PROGRAM. Measured
    # on the CF-3300: `FIELD#1,10 AS A$(1)` is OK and `FIELD#1,N AS A$(1)` is
    # `Type mismatch`. zerobas accepted the second BEFORE D-NAMSPC, precisely
    # because its name scan stopped at the space; it now refuses it too, though
    # with the wrong error (see the DEFERRED note below). So this row is where
    # "the fix works" would otherwise hide a construct that stops working, and it
    # is measured rather than argued
    # ([[a-priced-decline-is-a-claim-about-a-design]]).
    ("z.fldctl",  "dsk", ['DIM A$(3)', 'OPEN"TS.DAT"AS #1', 'N=10',
                          'FIELD#1,10 AS A$(1)', 'CLOSE#1', 'PRINT"[OK]"']),
    ("z.fldvar",  "dsk", ['DIM A$(3)', 'OPEN"TS.DAT"AS #1', 'N=10',
                          'FIELD#1,N AS A$(1)', 'CLOSE#1', 'PRINT"[OK]"']),
    # 🎯 AND THE ROW THAT SAYS `z.fldvar` IS NOT THIS SLICE'S DEFECT. There is
    # NO SPACE anywhere in the reference below: `B$` is spelled contiguously and
    # is simply the wrong TYPE for a field width. The CF-3300 answers `Type
    # mismatch`; zerobas answers `OK`, because `ex_field`'s `call eval`
    # (basic/field.asm:270) never checks what the width evaluates TO. That is
    # what makes `z.fldvar`'s residual gap an ERROR-CLASS defect in FIELD rather
    # than a name-scan one, and it is a MEASUREMENT rather than an argument
    # ([[row-with-two-candidate-causes]]).
    ("z.fldstr",  "dsk", ['DIM A$(3)', 'B$="X"', 'OPEN"TS.DAT"AS #1',
                          'FIELD#1,B$ AS A$(1)', 'CLOSE#1', 'PRINT"[OK]"']),
    # 🟢 ...and the join itself, with FIELD taken out of the picture entirely:
    # `N AS A$(1)` in an ordinary numeric assignment. Both references AND
    # zerobas answer `Type mismatch` -- the scan really does fold the whole thing
    # into the string array element `NA$(1)`, which is the mechanism §3.3 of the
    # spec predicts and the proof that `z.fldvar` fails downstream of it.
    ("z.join",    "run", ['DIM A$(3)', 'N=10', 'X=N AS A$(1)', 'PRINT"[OK]"']),
    ("z.joinnum", "run", ['NAS=4', 'N=10', 'X=N AS A', 'PRINT"[";X;"]"']),
    # --- D-FNARG: the FILENAME-ARGUMENT denominator ---------------------------
    # D-NAMSPC filed ONE row as a residual -- `OPEN A$ AS #1` is `Syntax error`
    # here and `OK` on the CF-3300 -- and said in the same breath what it needed:
    # "OPEN / KILL / NAME / SAVE / LOAD / BLOAD x (literal / variable /
    # expression), plus whether the same holds for FOR INPUT/OUTPUT/APPEND".
    # ⚠️ NOTHING TO DO WITH SPACES: the `$` suffix terminates the name scan
    # before the ` AS`, so these read the same before and after D-NAMSPC. They
    # are here because this is the probe with the fixtures, not because the rule
    # is this slice's.
    #
    # PREDICTIONS, WRITTEN BEFORE THE RUN:
    #   every `*lit` control  ` OK ` on the CF-3300 (they are the working form)
    #   every variable / expression form  cf3300 ` OK `, zerobas `Syntax error`
    # i.e. the reference takes a string EXPRESSION wherever it takes a filename,
    # and zerobas takes a LITERAL only. If any `*lit` row diverges the fixture is
    # broken and no other row here means anything.
    #
    # 🔴 THE THREE `FOR` FORMS ARE NOT DECORATION. `OPEN A$ AS #1` and
    # `OPEN A$ FOR INPUT AS #1` reach the name through DIFFERENT parse paths in
    # do_open (the mode clause sits between them), so a fix sited at one is not
    # automatically a fix at the other -- and one row cannot say which
    # ([[one-row-cannot-separate-two-rules]]).
    ("f.lit",     "dsk", ['OPEN"FA1.DAT"AS #1', 'CLOSE#1', 'PRINT"[OK]"']),
    ("f.var",     "dsk", ['A$="FA2.DAT"', 'OPEN A$ AS #1', 'CLOSE#1',
                          'PRINT"[OK]"']),
    ("f.expr",    "dsk", ['A$="FA3"', 'OPEN A$+".DAT" AS #1', 'CLOSE#1',
                          'PRINT"[OK]"']),
    ("f.paren",   "dsk", ['A$="FA4.DAT"', 'OPEN(A$)AS #1', 'CLOSE#1',
                          'PRINT"[OK]"']),
    ("f.inlit",   "dsk", ['OPEN"FA5.DAT"AS #1', 'CLOSE#1',
                          'OPEN"FA5.DAT"FOR INPUT AS #1', 'CLOSE#1',
                          'PRINT"[OK]"']),
    ("f.invar",   "dsk", ['OPEN"FA6.DAT"AS #1', 'CLOSE#1', 'A$="FA6.DAT"',
                          'OPEN A$ FOR INPUT AS #1', 'CLOSE#1', 'PRINT"[OK]"']),
    ("f.outvar",  "dsk", ['A$="FA7.DAT"', 'OPEN A$ FOR OUTPUT AS #1', 'CLOSE#1',
                          'PRINT"[OK]"']),
    ("f.appvar",  "dsk", ['A$="FA8.DAT"', 'OPEN A$ FOR APPEND AS #1', 'CLOSE#1',
                          'PRINT"[OK]"']),
    # 🔴 `f.appvar` READ `<NO OUTPUT>` ON THE CF-3300 -- NOT A VALUE, A READOUT
    # ANOMALY, and it has TWO candidate causes: the VARIABLE filename (this
    # battery's subject) or `FOR APPEND` on a file that does not exist (FA8.DAT
    # was never created, unlike f.invar's fixture). One row cannot separate them,
    # so these two change ONE variable each
    # ([[row-with-two-candidate-causes]]).
    #   f.applit    APPEND + LITERAL  + missing file  -> isolates the MODE
    #   f.appvarx   APPEND + VARIABLE + existing file -> isolates the ARGUMENT
    # PREDICT: if the mode is the cause, f.applit also reads `<NO OUTPUT>` and
    # f.appvarx reads cf3300 ` OK ` / zb `Syntax error` like every other variable
    # row. If the ARGUMENT is the cause, the opposite.
    ("f.applit",  "dsk", ['OPEN"FB1.DAT"FOR APPEND AS #1', 'CLOSE#1',
                          'PRINT"[OK]"']),
    ("f.appvarx", "dsk", ['OPEN"FB2.DAT"AS #1', 'CLOSE#1', 'A$="FB2.DAT"',
                          'OPEN A$ FOR APPEND AS #1', 'CLOSE#1', 'PRINT"[OK]"']),
    ("f.killlit", "dsk", ['OPEN"FA9.DAT"AS #1', 'CLOSE#1', 'KILL"FA9.DAT"',
                          'PRINT"[OK]"']),
    ("f.killvar", "dsk", ['OPEN"FAA.DAT"AS #1', 'CLOSE#1', 'A$="FAA.DAT"',
                          'KILL A$', 'PRINT"[OK]"']),
    ("f.namelit", "dsk", ['OPEN"FAB.DAT"AS #1', 'CLOSE#1',
                          'NAME"FAB.DAT"AS"FAC.DAT"', 'PRINT"[OK]"']),
    ("f.namevar", "dsk", ['OPEN"FAD.DAT"AS #1', 'CLOSE#1', 'A$="FAD.DAT"',
                          'B$="FAE.DAT"', 'NAME A$ AS B$', 'PRINT"[OK]"']),
    # === D-FNARG2: the FOUR VERBS THE RULE CLAIMED AND NEVER MEASURED ==========
    # D-FNARG's §4 says the divergence is "one mechanism reached from 11 call
    # sites" and names five files -- but its rows only ever drove `OPEN`, `KILL`
    # and `NAME`. `SAVE` (x2), `LOAD`/`CLOAD` (x2), `BLOAD` (x1) and `FILES`
    # were PREDICTED BY MECHANISM AND NOT MEASURED, which is a rule claiming
    # more than its evidence [[a-rule-can-claim-more-than-its-evidence]].
    #
    # 🎯 LOAD AND BLOAD NEED NO FIXTURE, AND THAT IS THE DESIGN. Point them at a
    # file that does not exist: the reference reaches the OPEN and answers
    # `File not found`, zerobas refuses at the PARSE with `Syntax error`. The
    # literal control proves the parse is reached and the file really is absent,
    # so the two sentinels cannot be confused with each other -- and neither row
    # writes to the disk image, so neither can perturb the other.
    # ⚠️ `File not found` had to be ADDED to ERRORS for this; before that it fell
    # through to `<NO OUTPUT>`, which is the agreeing-on-nothing shape this file
    # exists to avoid. Adding a name to a classifier can change a SHIPPED row's
    # reading, so the full gate is re-run, not just these rows.
    #
    # ROUND 1 PREDICTIONS (2026-08-20) AND WHAT THEY COST, cf3300 / zb:
    #   f.savelit   OK / OK               -> OK / OK                ✅ exact
    #   f.savevar   OK / <Syntax error>   -> OK / OK                🔴
    #   f.loadlit   FNF / FNF             -> FNF / OK               🔴
    #   f.loadvar   FNF / <Syntax error>  -> FNF / OK               🔴
    #   f.bloadlit  FNF / FNF             -> FNF / OK               🔴
    #   f.bloadvar  FNF / <Syntax error>  -> FNF / OK               🔴
    #   f.fileslit  OK / OK               -> FNF / FNF              🔴 (agree)
    #   f.filesvar  OK / <Syntax error>   -> FNF / <Syntax error>   🔴 half
    # 🔴 SIX OF THE EIGHT ZEROBAS READINGS WERE `OK` AND EVERY ONE OF THEM WAS
    # THE READOUT LYING. The screen said `load error` and then `[OK]`, and
    # `bracket()` looks for `[` before it looks for an error. See `errface()`.
    # 🎯 ROUND 2 PREDICTIONS, with the error-first readout:
    #   f.savelit   OK  / OK                 <- 🟢 control (a real save)
    #   f.savevar   OK  / <load error>
    #   f.loadlit   FNF / <load error>       <- the literal control DIVERGES
    #   f.loadvar   FNF / <load error>
    #   f.bloadlit  FNF / <load error>       <- ditto
    #   f.bloadvar  FNF / <load error>
    #   f.fileslit  FNF / FNF                <- 🟢 control, both refuse
    #   f.filesvar  FNF / <Syntax error>
    # 🎯 THE CONTRAST IS THE POINT: FILES goes through `files.asm` and RAISES a
    # real `Syntax error`; SAVE/LOAD/BLOAD go through `load_error`
    # (basic/bload.asm), which PRINTS a lowercase string and RETURNS -- no ERR
    # code, no line number, no ON ERROR trap, and the program runs on.
    # ⚠️ LFILES IS NOT MEASURED AND IS NOT AN OMISSION: it writes to the PRINTER,
    # so no screen readout can see it. It is the 11th site and stays predicted.
    ("f.savelit",  "dskerr", ['SAVE"FC1.DAT"', 'PRINT"[OK]"']),
    ("f.savevar",  "dskerr", ['A$="FC2.DAT"', 'SAVE A$', 'PRINT"[OK]"']),
    ("f.loadlit",  "dskerr", ['LOAD"FCZ.DAT"', 'PRINT"[OK]"']),
    ("f.loadvar",  "dskerr", ['A$="FCZ.DAT"', 'LOAD A$', 'PRINT"[OK]"']),
    ("f.bloadlit", "dskerr", ['BLOAD"FCY.BIN"', 'PRINT"[OK]"']),
    ("f.bloadvar", "dskerr", ['A$="FCY.BIN"', 'BLOAD A$', 'PRINT"[OK]"']),
    ("f.fileslit", "dskerr", ['FILES"FC*.*"', 'PRINT"[OK]"']),
    ("f.filesvar", "dskerr", ['A$="FC*.*"', 'FILES A$', 'PRINT"[OK]"']),
]

# 🔴 ORACLE STRENGTH IS NOT UNIFORM. The `z.fld*` rows are Disk BASIC; a diskless
# VG-8020 answers `Syntax error` to `FIELD`, so it is not an oracle for them --
# it is a machine that cannot express the question. Same disposition as
# basic_probe_tgtspc.py / basic_probe_lvsites.py.
NO_DISK_SIDES = ("vg8020",)

# `t.*` controls have no literal oracle: their want is whatever the REFERENCES
# stored, which basic_probe_crunch.py already gates zerobas against byte for
# byte. Checked below by cross-side comparison, never by a hard-coded string, so
# this probe does not re-state the crunch oracle.
TOK_CONTROLS = ("t.ctl", "t.dctl", "t.digctl", "t.kwctl", "t.andctl",
                "t.absctl")
CONTROLS = TOK_CONTROLS + (
    "c.let", "r.digctl", "r.strctl", "r.pctctl", "r.bangctl", "r.hashctl",
    "s.ifctl", "s.forctl", "s.dimctl", "s.readctl", "s.swapctl", "z.fldctl")
CONTROL_WANT = {"c.let": " 7 ", "r.digctl": " 7 ", "r.strctl": "HI",
                "r.pctctl": " 7 ", "r.bangctl": " 7 ", "r.hashctl": " 7 ",
                "s.ifctl": "OK", "s.forctl": "OK", "s.dimctl": " 7 ",
                "s.readctl": " 7 ", "s.swapctl": " 9  7 ", "z.fldctl": "OK"}
NEGATIVE = ("z.kw", "z.miss")
LABEL_W = 10

# Each spaced row is evidence about the SPACE only while its own site's
# CONTIGUOUS control is green on zerobas.
SITE_CONTROL = {
    "t.name": "t.ctl", "t.dollar": "t.dctl", "t.dig": "t.digctl",
    "t.kw": "t.kwctl", "t.and": "t.andctl", "t.abs": "t.absctl",
    "r.name": "c.let", "r.multi": "c.let", "r.three": "c.let",
    "r.run": "c.let", "r.dig": "r.digctl",
    "r.instr": "r.strctl", "r.dollar": "r.strctl",
    "r.pct": "r.pctctl", "r.bang": "r.bangctl", "r.hash": "r.hashctl",
    "a.name": "c.let", "a.sig": "c.let", "a.dig": "r.digctl",
    "a.str": "r.strctl", "a.dollar": "r.strctl",
    "s.if": "s.ifctl", "s.for": "s.forctl", "s.next": "s.forctl",
    "s.dim": "s.dimctl", "s.ary": "s.dimctl",
    "s.read": "s.readctl", "s.swap": "s.swapctl",
    "z.miss": "s.forctl", "z.kw": "c.let",
    "k.and": "c.let", "k.abs": "c.let",
    "w.let": "c.let", "w.print": "c.let", "w.for": "s.forctl",
    "w.comma": "s.swapctl", "z.fldvar": "z.fldctl",
    "z.fldstr": "z.fldctl", "z.join": "c.let", "z.joinnum": "c.let",
}

# --- DEFERRED: measured, printed, NEVER scored ------------------------------
# 🔴 THE TWO `FIELD` ROWS ARE A DIVERGENCE THIS SLICE CANNOT CLOSE, AND THE
# ROW THAT SAYS SO HAS NO SPACE IN IT. `ex_field` (basic/field.asm:270) `eval`s
# its width and never checks the TYPE of the result, so `FIELD#1,B$ AS A$(1)`
# -- contiguous, no space anywhere -- is `OK` here and `Type mismatch` on the
# CF-3300 (`z.fldstr`). Once the name scan joins `N AS A$(1)` the same way the
# reference does, `z.fldvar` reaches that identical missing check: the CF-3300
# refuses the width BEFORE looking for its literal `AS`, while this tree gets
# as far as the missing `AS` and says `Syntax error`.
# 🎯 `z.join` / `z.joinnum` are the CONTROL for that claim -- the same joined
# reference with FIELD taken out, agreeing on all three sides. Scoring the two
# `fld` rows would charge the name scan for FIELD's error classification and
# leave no row able to separate them ([[one-row-cannot-separate-two-rules]]).
# Filed in TODO.md as its own residual with these four readings as its
# denominator; a deferred row that started AGREEING would itself be a finding.
# ✅ EMPTY SINCE D-FLDWIDTH (2026-08-08). Both rows are now ORDINARY SCORED
# ROWS: `ex_field` type-checks and domain-checks its width (a byte argument --
# docs/spec-basic-fldwidth.md), so `z.fldstr` and `z.fldvar` both read
# `Type mismatch`, which is what the CF-3300 has answered all along. The
# deferral was honoured rather than merely filed
# ([[a-deferral-honoured-is-worth-more-than-one-filed]]).
DEFERRED: dict[str, str] = {
    # D-FNARG denominator rows: measured, printed, NEVER scored until the rule is
    # settled and a fix is priced. A deferred row that started AGREEING would
    # itself be a finding.
    lab: "DEFERRED — D-FNARG filename-argument denominator (TODO: `OPEN A$ AS #1`)"
    for lab in ("f.lit", "f.var", "f.expr", "f.paren", "f.inlit", "f.invar",
                "f.outvar", "f.appvar", "f.applit", "f.appvarx", "f.killlit",
                "f.killvar", "f.namelit", "f.namevar",
                # D-FNARG2, 2026-08-20: the four verbs the rule claimed and had
                # never driven.
                "f.savelit", "f.savevar", "f.loadlit", "f.loadvar",
                "f.bloadlit", "f.bloadvar", "f.fileslit", "f.filesvar")
}


SENTINELS = ("<NO CAPTURE>", "<NO OUTPUT>", "<NOT STORED>",
             "<RUN SCROLLED OFF>", "<NO DISK ON THIS SIDE>")

ERRORS = ("Syntax error", "Type mismatch", "Subscript out of range",
          "Redimensioned array", "Illegal function call", "Out of memory",
          "Out of string space", "Overflow", "Out of DATA",
          "NEXT without FOR", "Undefined line number",
          # D-FNARG2: the disk-side faces the SAVE/LOAD/BLOAD rows turn on. Until
          # 2026-08-20 these fell through to `<NO OUTPUT>` -- a real error read as
          # a silence, and a silence is what a diverging pair agrees on.
          "File not found", "Device I/O error", "Disk offline", "Bad file name",
          # 🔴 NOT AN MSX ERROR NAME. `load error` is zerobas's OWN lowercase
          # string (basic/bload.asm `err_io`), printed by a routine that RETURNS
          # instead of raising. It has to be nameable or it reads as a silence.
          "load error")


def bracket(raw: str | None) -> str:
    """The `[...]` span the RUN printed, or a sentinel naming what came instead.

    🔴 THE TAIL AFTER `RUN`, NOT THE WHOLE SCREEN -- see the module docstring."""
    if raw is None:
        return "<NO CAPTURE>"
    tail = omsx_repl.screen_tail(raw, "RUN")
    if tail is None:
        # 🔴 NOT `<NO OUTPUT>` -- THE OPPOSITE, AND THE FIRST DRAFT SAID THE
        # WRONG ONE. `RUN` is off the top of a SCREEN 0 page because the program
        # printed MORE than a screenful: five rows here read this way and every
        # one is a zerobas RUNAWAY (a PRINT item loop that never advances past
        # the character after the name). Naming it "no output" would have
        # recorded a hang as a silence, and a hang is the stronger divergence.
        return ("<RUN SCROLLED OFF>" if str(raw).strip() else "<NO CAPTURE>")
    txt = " ".join(str(tail).split("\n"))
    i = txt.find("[")
    j = txt.find("]", i + 1)
    if i >= 0 and j > i:
        return txt[i + 1:j]
    for e in ERRORS:
        if e in txt:
            return f"<{e}>"
    return "<NO OUTPUT>"


# 🔴 ERROR-FIRST, AND THE FIRST DRAFT OF THE D-FNARG2 ROWS WAS BLIND WITHOUT IT.
# `bracket()` above looks for `[` BEFORE it looks for an error, which is right
# for a row whose subject is a VALUE. It is wrong for a row whose subject is a
# FAILURE, because zerobas's SAVE/LOAD/BLOAD failure path PRINTS and RETURNS
# (`load_error`, basic/bload.asm: print_msg + ret, no raise) -- so the program
# runs on and prints its `[OK]` UNDERNEATH the message. All four zerobas rows
# read `OK` while the screen said `load error`, which is exactly the readout
# blind to its own subject the module docstring warns about
# [[readout-blind-to-its-own-subject]]. A separate function rather than a
# reordering: 58 scored rows depend on `bracket()`'s order and none of them is
# under test here.
def errface(raw: str | None) -> str:
    """The ERROR the RUN produced, or the `[...]` span if there was none."""
    if raw is None:
        return "<NO CAPTURE>"
    tail = omsx_repl.screen_tail(raw, "RUN")
    if tail is None:
        return ("<RUN SCROLLED OFF>" if str(raw).strip() else "<NO CAPTURE>")
    txt = " ".join(str(tail).split("\n"))
    for e in ERRORS:
        if e in txt:
            return f"<{e}>"
    i, j = txt.find("["), txt.find("]", txt.find("[") + 1)
    if i >= 0 and j > i:
        return txt[i + 1:j]
    return "<NO OUTPUT>"


def tokens(raw: str | None) -> str:
    """The stored line's BODY bytes: everything after link(2) + lineno(2), up to
    and including the 0x00 terminator. `<NOT STORED>` when the line never made
    it into the program area (a crunch that errored leaves link == 00 00)."""
    if not raw:
        return "<NOT STORED>"
    b = bytes.fromhex(raw)
    if len(b) < 5:
        return "<NOT STORED>"
    return b[4:].hex()


def run_side(side: str, only: list[str]) -> dict:
    cfg = SIDES[side]
    out = {}
    for label, kind, lines in CASES:
        if only and label not in only:
            continue
        if kind in ("dsk", "dskerr") and side in NO_DISK_SIDES:
            # NOT a reading. A diskless machine cannot express the question, and
            # recording its `Syntax error` as an answer would manufacture an
            # agreement with zerobas out of an absent disk controller.
            out[label] = "<NO DISK ON THIS SIDE>"
            continue
        kw = {}
        if cfg["diska"]:
            dsk = os.path.join(tempfile.gettempdir(),
                               f"zb_namspc_{side}_{label}.dsk")
            shutil.copy(TEST_DSK, dsk)
            kw["diska"] = dsk
        if kind == "tok":
            caps = omsx_repl.run_cases(
                cfg["machine"], [("direct", list(cfg["reset"]) + list(lines))],
                batch=False, boot=cfg["boot"], step=cfg["step"],
                capture=("stored_line", TXTTAB), **kw)
            out[label] = tokens(caps[0])
            continue
        body = [f"{10 * (k + 1)} {ln}" for k, ln in enumerate(lines)]
        caps = omsx_repl.run_cases(
            cfg["machine"],
            [("direct", list(cfg["reset"]) + body + ["RUN"])],
            batch=False, boot=cfg["boot"], step=cfg["step"], **kw)
        out[label] = (errface if kind == "dskerr" else bracket)(caps[0])
    return out


def main() -> int:
    ap = argparse.ArgumentParser(
        description="D-NAMSPC: a space INSIDE a variable name / before its "
                    "type suffix")
    ap.add_argument("--sides", default="vg8020,cf3300,zb")
    ap.add_argument("--only", default="")
    ap.add_argument("--gate", action="store_true",
                    help="exit 1 unless every scored row matches its reference")
    a = ap.parse_args()

    sides = [s for s in a.sides.split(",") if s]
    only = [o for o in a.only.split(",") if o]
    for s in sides:
        if s not in SIDES:
            sys.stderr.write(f"unknown side {s!r}\n")
            return 2

    results = {s: run_side(s, only) for s in sides}
    present = [lab for lab, _, _ in CASES
               if any(lab in results[s] for s in sides)]

    print("D-NAMSPC — a SPACE inside a variable reference's NAME / before its "
          f"suffix   sides: {', '.join(sides)}")
    print("=" * 78)

    def want(ctl: str):
        """A `t.*` control's want is whatever the REFERENCES stored; every other
        control has a literal."""
        if ctl not in TOK_CONTROLS:
            return CONTROL_WANT[ctl]
        refs = {results[s].get(ctl) for s in ("vg8020", "cf3300")
                if s in results and results[s].get(ctl) not in
                (None,) + SENTINELS}
        return list(refs)[0] if len(refs) == 1 else None

    # 🔴 ONLY A REFERENCE CAN SAY THE APPARATUS IS BROKEN. A control that fails
    # on `zb` is a finding and is scored below like any other row.
    bad = []
    for ctl in CONTROLS:
        if ctl not in present:
            continue
        for s in sides:
            if s == "zb":
                continue                # a zerobas miss is a RESULT, not a break
            got = results[s].get(ctl)
            if got in (None, "<NO DISK ON THIS SIDE>"):
                continue                # not a reading, not a failure
            exp = want(ctl)
            if exp is None:
                continue                # a t.* control with a single reference
            if got != exp:
                bad.append((ctl, s, got, exp))
    if bad:
        for lab, s, got, exp in bad:
            print(probe_report.row("FAIL", lab, LABEL_W, {s: got},
                                   "   [POSITIVE CONTROL]"))
            print(f"        wanted {exp!r}")
        print("\n*** A POSITIVE CONTROL FAILED ON A REFERENCE, so nothing was "
              "measured.\n"
              "    Each control is the CONTIGUOUS form of its own row's "
              "fixture -- the same\n"
              "    program with the space taken out. A REFERENCE failing it "
              "means the fixture\n"
              "    is broken, not that the rule is wrong. (A control failing "
              "on `zb` is NOT\n"
              "    this: that is an ordinary divergence and IS scored, because "
              "only a\n"
              "    reference is supposed to be right.) Check build/*.rom, `make "
              "repack-machine`\n"
              "    and `make latch-check`, THEN re-read the rows. Exit 2 (not "
              "1) = the\n"
              "    instrument was broken, NOT a regression.")
        for lab in present:
            vals = {s: results[s][lab] for s in sides if lab in results[s]}
            print(probe_report.row("....", lab, LABEL_W, vals,
                                   "   (not scored)"))
        print(probe_report.footer(len(bad) + len(present), 0,
                                  "NOT MEASURED (a positive control failed)"))
        return 2

    def ctl_red_on_zb(ctl: str) -> bool:
        got = results.get("zb", {}).get(ctl)
        if got in (None, "<NO DISK ON THIS SIDE>"):
            return False
        exp = want(ctl)
        return exp is not None and got != exp

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

    agree = dis = noref = onlyone = refsplit = deferred = 0
    for lab in present:
        vals = {s: results[s][lab] for s in sides if lab in results[s]}
        refs = {s: v for s, v in vals.items()
                if s in ("vg8020", "cf3300") and v not in SENTINELS}
        if lab in DEFERRED:
            deferred += 1
            print(probe_report.row("....", lab, LABEL_W, vals,
                                   f"   [{DEFERRED[lab]}]"))
            continue
        note = "   [POSITIVE CONTROL]" if lab in CONTROLS else ""
        if lab in NEGATIVE:
            note = "   [NEGATIVE CONTROL — both references REFUSE this]"
        own = SITE_CONTROL.get(lab)
        if own and own in present and ctl_red_on_zb(own):
            note += ("   [ITS OWN CONTIGUOUS CONTROL IS RED ON zb — this row "
                     "is NOT evidence about the SPACE]")
        if not refs:
            noref += 1
            print(probe_report.row("....", lab, LABEL_W, vals,
                                   "   [NO REFERENCE ON ANY REQUESTED SIDE]"))
            continue
        if len(set(refs.values())) > 1:
            refsplit += 1
            dis += 1
            print(probe_report.row("DIFF", lab, LABEL_W, vals,
                                   note + "   [REFERENCES DISAGREE — no oracle "
                                          "for this row]"))
            continue
        if len(refs) == 1:
            onlyone += 1
            note += f"   [ONE REFERENCE ONLY ({list(refs)[0]}) — Disk BASIC]"
        oracle = list(refs.values())[0]
        zb = vals.get("zb")
        ok = zb == oracle and zb not in SENTINELS
        agree += ok
        dis += not ok
        print(probe_report.row("ok" if ok else "DIFF", lab, LABEL_W, vals, note))

    print(probe_report.footer(len(present), len(present) - noref - deferred,
                              f"{agree} agree, {dis} diverge, "
                              f"{noref} without a reference, "
                              f"{deferred} deferred (not scored)"))
    print("=" * 78)
    print(f"{agree}/{agree + dis} readings match their reference "
          f"({len(CASES)} cases, {len(CONTROLS)} positive controls, "
          f"{len(NEGATIVE)} negative controls, "
          f"{onlyone} row(s) with ONE reference only, "
          f"{noref} row(s) without a reference, "
          f"{refsplit} row(s) where the references disagree, "
          f"{len(DEFERRED)} DEFERRED row(s) measured but not scored)")
    print("🔴 ORACLE STRENGTH IS NOT UNIFORM: the `z.fld*` rows are Disk BASIC, "
          "which a diskless VG-8020 cannot express — they rest on the CF-3300 "
          "ALONE. Every other row here has two references.")
    print("DENOMINATOR: (WHERE the space falls inside a reference: before the "
          "2nd LETTER, before a DIGIT, before each of the four type suffixes "
          "`% ! # $`, MORE THAN ONCE, and between two names run together) x "
          "(the POSITION the reference stands in: r-value expression, LET "
          "target, IF condition, FOR, NEXT, DIM, an array element lvalue, READ, "
          "SWAP -- none of which except NEXT/READ reaches tgt_parse), plus "
          "whether the space SURVIVES THE CRUNCH at all (t.*, read from the "
          "stored line bytes, which is what says whether the fix belongs in the "
          "tokeniser or the parser), plus what the TWO-CHARACTER KEY does with "
          "a space in the middle (r.three / r.run / a.sig), plus the KEYWORD "
          "constraint (t.kw / t.and / t.abs / k.and / k.abs: this tokeniser matches keywords at "
          "every position mid-identifier, so a spaced name can be crunched into "
          "a TOKEN before any parser sees it, and z.kw is the RUNTIME negative "
          "control that says a name so tokenised must STAY refused), plus the "
          "converse row that says the joined name is a DIFFERENT variable and "
          "not tolerated junk (z.miss), plus the TRAILING-space set (w.*) that "
          "is green BEFORE and must stay green AFTER. Every spaced row carries "
          "the CONTIGUOUS form of its own "
          "fixture as its positive control. NOT COVERED: a TAB or other "
          "whitespace byte; DIRECT mode (TODO.md's `dir-name` residual); a space "
          "inside a DEF FN name or a line-number list; `RSET` and the FIELD "
          "family (D-TGTSPC's nine lvalue surfaces already carry the `(` "
          "position and share one parse site).")
    if a.gate and dis:
        sys.stderr.write(f"namspc: {dis} reading(s) diverge\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
