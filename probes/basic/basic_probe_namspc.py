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
import re
import shutil
import sys

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lib"))
import omsx_repl                                                 # noqa: E402
import probe_report                                              # noqa: E402
import probe_tmp                                                 # noqa: E402

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
    # 🔴 THESE ROWS ARE `dskerr`/`errface`, NOT `dsk`/`bracket`, AND A KNIFE IS
    # WHAT SAID SO. They were `bracket` rows until 2026-08-21; knife K-FE1
    # (D-FNEXPR -- destroy the terminator fname_expr appends to the staged name)
    # reddened ONE row of fifteen, and the screen showed why:
    #     ZBRUN
    #     load error
    #     [OK]
    # `parse_disk_fcb`'s reject reaches `bl_load_error`, which PRINTS and
    # RETURNS -- so the program runs on and prints its `[OK]` UNDERNEATH the
    # message, and `bracket()` looks for `[` BEFORE it looks for an error. All
    # thirteen scored GREEN while the machine was refusing every filename
    # ([[readout-blind-to-its-own-subject]]).
    # 🎯 D-FNARG2 ALREADY FOUND THIS CLASS AND FIXED IT FOR THE OTHER FOUR
    # VERBS -- `errface()` exists because of it. Fixing SAVE/LOAD/BLOAD/FILES
    # and leaving OPEN/KILL/NAME on `bracket` is guarding one instance of a
    # class and calling the class guarded
    # ([[a-fix-falsifies-the-justification-beside-it]]). The healthy readings are
    # UNCHANGED by the switch -- `errface` returns the `[...]` span when there is
    # no error -- which is what makes this a coverage fix and not a rescoring.
    #
    # 🔴 THE THREE `FOR` FORMS ARE NOT DECORATION. `OPEN A$ AS #1` and
    # `OPEN A$ FOR INPUT AS #1` reach the name through DIFFERENT parse paths in
    # do_open (the mode clause sits between them), so a fix sited at one is not
    # automatically a fix at the other -- and one row cannot say which
    # ([[one-row-cannot-separate-two-rules]]).
    ("f.lit",     "dskerr", ['OPEN"FA1.DAT"AS #1', 'CLOSE#1', 'PRINT"[OK]"']),
    ("f.var",     "dskerr", ['A$="FA2.DAT"', 'OPEN A$ AS #1', 'CLOSE#1',
                          'PRINT"[OK]"']),
    ("f.expr",    "dskerr", ['A$="FA3"', 'OPEN A$+".DAT" AS #1', 'CLOSE#1',
                          'PRINT"[OK]"']),
    ("f.paren",   "dskerr", ['A$="FA4.DAT"', 'OPEN(A$)AS #1', 'CLOSE#1',
                          'PRINT"[OK]"']),
    ("f.inlit",   "dskerr", ['OPEN"FA5.DAT"AS #1', 'CLOSE#1',
                          'OPEN"FA5.DAT"FOR INPUT AS #1', 'CLOSE#1',
                          'PRINT"[OK]"']),
    ("f.invar",   "dskerr", ['OPEN"FA6.DAT"AS #1', 'CLOSE#1', 'A$="FA6.DAT"',
                          'OPEN A$ FOR INPUT AS #1', 'CLOSE#1', 'PRINT"[OK]"']),
    ("f.outvar",  "dskerr", ['A$="FA7.DAT"', 'OPEN A$ FOR OUTPUT AS #1', 'CLOSE#1',
                          'PRINT"[OK]"']),
    ("f.appvar",  "dskerr", ['A$="FA8.DAT"', 'OPEN A$ FOR APPEND AS #1', 'CLOSE#1',
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
    ("f.applit",  "dskerr", ['OPEN"FB1.DAT"FOR APPEND AS #1', 'CLOSE#1',
                          'PRINT"[OK]"']),
    ("f.appvarx", "dskerr", ['OPEN"FB2.DAT"AS #1', 'CLOSE#1', 'A$="FB2.DAT"',
                          'OPEN A$ FOR APPEND AS #1', 'CLOSE#1', 'PRINT"[OK]"']),
    ("f.killlit", "dskerr", ['OPEN"FA9.DAT"AS #1', 'CLOSE#1', 'KILL"FA9.DAT"',
                          'PRINT"[OK]"']),
    ("f.killvar", "dskerr", ['OPEN"FAA.DAT"AS #1', 'CLOSE#1', 'A$="FAA.DAT"',
                          'KILL A$', 'PRINT"[OK]"']),
    ("f.namelit", "dskerr", ['OPEN"FAB.DAT"AS #1', 'CLOSE#1',
                          'NAME"FAB.DAT"AS"FAC.DAT"', 'PRINT"[OK]"']),
    ("f.namevar", "dskerr", ['OPEN"FAD.DAT"AS #1', 'CLOSE#1', 'A$="FAD.DAT"',
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
    # 🎯 THE ROW `do_files`' OP-SELECTOR GUARD HAS NEVER HAD (TODO, filed
    # 2026-08-21 by D-FNEXPR2 §3.5 AGAINST ITS OWN FIX). `do_files` parks its
    # dirverb op selector on the stack across the filespec parse because
    # `str_eval` can now run `INPUT$(n,#ch)`, which reaches the drive through
    # `fatprim_bounce` and overwrites `DISKOP_OP`. The BALANCE of that push/pop
    # is pinned by every FILES row; the CLOBBER protection was pinned by nothing,
    # because **no row in any battery executed `FILES INPUT$(n,#ch)`** — so a
    # knife unparking the selector would have reddened nothing, and that is a
    # claim about the ROW SET, not about the code [[a-shadowed-guard-has-no-knife]].
    # 🔴 AND THE SHAPE THE FILING PROPOSED DOES NOT REACH THE CASE. Written as
    # `OPEN"HI.TXT"FOR INPUT AS #1` / `FILES INPUT$(3,#1)`, the row is green
    # under a knife that restores the pre-fix head-write — measured, with every
    # plain FILES row correctly holding, so the cut was right and the ROW was
    # blind. HI.TXT is 26 bytes: the whole file arrives in the buffer at OPEN, so
    # the 3-byte read touches no FAT primitive and never writes DISKOP_OP.
    # 🎯 The read has to force a REFILL. TEST.BIN is 2048 bytes, so two 255-byte
    # reads leave the channel 2 bytes short of the 512-byte sector boundary and
    # the filespec's OWN `INPUT$(3,#1)` is the one that crosses it
    # [[a-coverage-row-whose-geometry-cannot-reach-the-case]].
    # 🔴 AND THE READ'S BYTES MUST NOT REACH THE NAME. `FILES INPUT$(3,#1)` on
    # TEST.BIN builds a filespec out of CONTROL BYTES, and that DIVERGES —
    # CF-3300 `Bad file name`, zerobas `File not found` (filed separately; it is
    # a real finding and not this row's subject). `LEFT$(…,0)` keeps the read and
    # discards its bytes, so the filespec is the same literal `f.fileslit` uses
    # and the only thing this row varies is whether a drive access happened
    # during the parse.
    # 🔴 AND IT IS *NOT* YET A PIN — SAID HERE RATHER THAN ASSUMED. Under a
    # faithful pre-fix knife (`scratchpad/filesinp_knife.py`: the selector
    # written at the HEAD again and re-read from the cell at the call, with the
    # push/pop balance untouched so the two properties are cut separately) this
    # row HOLDS, while every plain FILES row correctly holds too — so the cut is
    # right and the row is still blind to the clobber.
    # 🔬 The clobber itself IS real: a throw-away diagnostic row read `DISKOP_OP`
    # ($E9FB) either side of the very `INPUT$` and found **7 = 
    # DISKOP_SEL_FAT_READ_FILE_SECTOR** — the file read does reach
    # `fatprim_bounce`. It wrote the same 7 the two 255-byte reads had already
    # left, which is why the before/after pair alone cannot show it. (That row is
    # deleted rather than kept: `$E9FB` is zerobas's own sysvar, so it is
    # meaningless on the CF-3300 and DIFFs by construction.)
    # ⚠️ So the open question is now sharp and is filed: handing the dirverb
    # tenant selector 7 instead of the FILES selector changes nothing observable
    # in these rows, and WHY is unmeasured.
    # ⚠️ `CLEAR 1000` FIRST, and BEFORE the OPEN: two 255-byte reads do not fit
    # the default 200-byte string pool (the row read `<Out of string space>` on
    # both sides), and `CLEAR` closes channels, so it cannot come after.
    ("f.filesinp", "dskerr", ['CLEAR 1000',
                              'OPEN"TEST.BIN"FOR INPUT AS #1',
                              'A$=INPUT$(255,#1):A$=INPUT$(255,#1)',
                              'FILES "FC*.*"+LEFT$(INPUT$(3,#1),0)',
                              'PRINT"[OK]"']),
    ("f.fileslit", "dskerr", ['FILES"FC*.*"', 'PRINT"[OK]"']),
    ("f.filesvar", "dskerr", ['A$="FC*.*"', 'FILES A$', 'PRINT"[OK]"']),

    # === D-FILESIDE: the row that scores WHAT WAS PRINTED BEFORE THE ERROR ===
    # 🔴 `f.filesvar` AGREES WITH D-FNARG'S RULE BY COINCIDENCE OF FACE.
    # Measured 2026-08-20 (§4.2 above): `FILES A$` does not refuse the non-quote
    # here at all -- basic/files.asm reads it as NO FILESPEC (`jr nz,
    # df_nofilespec`), LISTS THE WHOLE DIRECTORY, and only then derails on the
    # unconsumed `A$`. The CF-3300 lists nothing and raises `File not found`.
    #
    # 🎯 AND NO ROW SCORED THAT. `errface()` takes the last message; the five
    # directory lines above it are structurally invisible to it, so a machine
    # that refused `FILES A$` cleanly at the PARSE would read exactly the same
    # `<Syntax error>`. The apparatus could not tell a fix from a no-op, which
    # is why this row lands BEFORE any decision about the ROM.
    #
    # The two 🟢 controls are what make the third row evidence: without
    # `f.filesbare` a count of 0 could mean "the machine printed nothing" or "the
    # counter is blind", and those are the two readings this project keeps
    # confusing ([[spokeline-slice]], [[gateblind-slice]]).
    ("f.filesbare", "dsklist", ['FILES', 'PRINT"[OK]"']),
    ("f.fileslitl", "dsklist", ['FILES"FC*.*"', 'PRINT"[OK]"']),
    ("f.filesvarl", "dsklist", ['A$="FC*.*"', 'FILES A$', 'PRINT"[OK]"']),

    # === m.* A MALFORMED FILESPEC: does the reject STOP the listing? =========
    # Noticed 2026-08-21 walking D-FNEXPR2's sites, never measured. On this side
    # `parse_disk_fcb` refuses a name that will not fit 8.3 with
    # `jp bl_load_error`, and `load_error` PRINTS AND RETURNS -- from inside
    # parse_disk_fcb, so the `ret` lands in the CALLER and `do_files` walks the
    # directory anyway with a half-built pattern. That is the nested-reject
    # hazard sub/bload.asm already names in prose [[load-error-is-not-abort]];
    # what is new is that `listface` can SEE it, because it reports the entry
    # COUNT beside the face.
    # 🎯 `N entries + <face>` IS THE WHOLE POINT OF THE READOUT HERE. "printed an
    # error" and "listed anyway" are two independent facts and either alone is
    # satisfied by the wrong machine: a reject that lists reads the same as a
    # clean reject if you only look at the message, and the same as a clean
    # listing if you only count entries.
    # 🟢 The controls above (f.filesbare / f.fileslitl) are what make a count
    # meaningful at all -- without them 0 could equally be "the counter is blind".
    # === D-FSPECCHAR: the 8.3 character domain (2026-09-05) =================
    # `build_83_name` refused NUL, `"`, `.` and a leading space and NOTHING else,
    # so a filespec of control bytes read `File not found` here and `Bad file
    # name` on the CF-3300. The domain was swept at 45 byte values
    # (`scratchpad/fspecchar_probe.py`); these five are its corners.
    # 🔴 THE TWO ACCEPTED ROWS ARE THE LOAD-BEARING ONES. `$80` accepted beside
    # `$FF` refused is what forbids re-writing this as a high-bit test, and `>`
    # accepted is what forbids reading `<`/`>` as a separator pair. Without them
    # the three refusals are equally explained by a check that is too broad.
    ("m.ctlchar", "dskerr", ['FILES CHR$(4)+"BC.TXT"', 'PRINT"[OK]"']),
    ("m.sepchar", "dskerr", ['FILES CHR$(58)+"BC.TXT"', 'PRINT"[OK]"']),
    ("m.ffchar",  "dskerr", ['FILES CHR$(255)+"BC.TXT"', 'PRINT"[OK]"']),
    ("m.hi80",    "dskerr", ['FILES CHR$(128)+"BC.TXT"', 'PRINT"[OK]"']),
    ("m.gtchar",  "dskerr", ['FILES CHR$(62)+"BC.TXT"', 'PRINT"[OK]"']),
    ("m.long",    "dsklist", ['FILES"TOOLONGNAME.EXT"', 'PRINT"[OK]"']),
    ("m.longext", "dsklist", ['FILES"AB.EXTRA"', 'PRINT"[OK]"']),
    ("m.both",    "dsklist", ['FILES"TOOLONGNAME.EXTRA"', 'PRINT"[OK]"']),
    ("m.twodot",  "dsklist", ['FILES"A.B.C"', 'PRINT"[OK]"']),
    ("m.empty",   "dsklist", ['FILES""', 'PRINT"[OK]"']),
    # ...and the BOUNDARY of `Bad file name`, because two rows naming it do not
    # say what the rule IS. A dot alone, a bare drive colon and a blank all
    # probe different halves of "what makes a filespec malformed".
    ("m.dot",     "dsklist", ['FILES"."', 'PRINT"[OK]"']),
    ("m.dotdot",  "dsklist", ['FILES".."', 'PRINT"[OK]"']),
    ("m.colon",   "dsklist", ['FILES"A:B"', 'PRINT"[OK]"']),
    ("m.blank",   "dsklist", ['FILES" "', 'PRINT"[OK]"']),
    # 🔴 THE SAME CLASS AS `m.blank`, FOUND 2026-09-05 CHECKING D-FSPECCHAR FOR
    # OVER-REACH: a filespec that is ONLY a drive prefix is also "no filespec at
    # all" on the reference, which lists the directory, while `build_83_name`'s
    # empty-name test refuses it. ⚠️ It is NOT a regression from the character
    # check -- `bn_done`'s comment has named `"A:"` as a rejected case all along,
    # and `FILES"A:HI.TXT"` / `OPEN"A:HI.TXT"` are OK on both sides, so the drive
    # prefix is stripped before the name builder and the new `:` rule never sees
    # it.
    ("m.drvbare", "dsklist", ['FILES"A:"', 'PRINT"[OK]"']),
    # 🟢 …AND THE THREE ROWS THAT SAY WHERE THE FIX MAY NOT GO. `m.blank`'s
    # deferral note said the other verbs were "unmeasured"; they are measured
    # now, and they AGREE: a bare drive prefix is `Bad file name` on both sides
    # for KILL, LOAD and SAVE, because those verbs have no "no filespec" meaning
    # to fall back to. So the empty-name rejection in `bn_done` is CORRECT and
    # must stay -- loosening it would fix `m.drvbare` by breaking these three.
    # The fix belongs in `do_files`, which is the only caller with a bare form.
    ("m.drvkill", "dskerr", ['KILL"A:"', 'PRINT"[OK]"']),
    ("m.drvload", "dskerr", ['LOAD"A:"', 'PRINT"[OK]"']),
    ("m.drvsave", "dskerr", ['SAVE"A:"', 'PRINT"[OK]"']),

    # === v.* THE SAME MALFORMED FORMS ON THE OTHER DISK VERBS ================
    # 🎯 THE MEASUREMENT `parse_disk_fcb`'s ELEVEN CALLERS DEMAND. D-FSPEC found
    # `Bad file name` at FILES for a second dot, an empty string and a bare dot.
    # The check belongs in parse_disk_fcb -- shared by LOAD, SAVE, BLOAD, KILL,
    # NAME and OPEN -- so whether the rule is UNIFORM across those verbs decides
    # whether the fix is one site or several, and that is not guessable
    # [[a-shared-tail-is-not-a-decision]].
    # ⚠️ Each verb gets the same two forms so the rows are comparable ACROSS the
    # table and not only against their own reference; `""` and `"A.B.C"` are the
    # two D-FSPEC showed the reference refusing outright.
    ("v.kempty",  "dskerr", ['KILL""', 'PRINT"[OK]"']),
    ("v.k2dot",   "dskerr", ['KILL"A.B.C"', 'PRINT"[OK]"']),
    ("v.lempty",  "dskerr", ['LOAD""', 'PRINT"[OK]"']),
    ("v.l2dot",   "dskerr", ['LOAD"A.B.C"', 'PRINT"[OK]"']),
    ("v.sempty",  "dskerr", ['SAVE""', 'PRINT"[OK]"']),
    ("v.s2dot",   "dskerr", ['SAVE"A.B.C"', 'PRINT"[OK]"']),
    ("v.oempty",  "dskerr", ['OPEN""AS #1', 'CLOSE#1', 'PRINT"[OK]"']),
    ("v.o2dot",   "dskerr", ['OPEN"A.B.C"AS #1', 'CLOSE#1', 'PRINT"[OK]"']),

    # === w.* WHAT AN OVER-LONG NAME ACTUALLY BECOMES =========================
    # 🎯 THE ROWS THAT SEPARATE TWO RULES THAT AGREE ON EVERY *ERROR* ROW.
    # "reject an over-long name" and "truncate it" both produce `File not found`
    # at FILES on a disk with no matching file, so no error-face row can tell
    # them apart [[two-rules-that-coincide-on-every-row-you-have]]. SAVE writes,
    # so the DIRECTORY says which: the entry count changes, and the created name
    # is visible in the listing.
    # 🔴 THE ANSWER IS NEITHER "REJECT" NOR "TRUNCATE AT THE DOT". The reference
    # takes 8 characters for the name and then the NEXT THREE POSITIONALLY as
    # the extension, ignoring the dot once the name is full:
    # `SAVE"TOOLONGNAME.BAS"` creates **TOOLONGN.AME**. An over-long EXTENSION is
    # simply truncated (`AB.EXTRA` -> `AB.EXT`), and neither is an error.
    ("w.savelong", "dsklist", ['A=1', 'SAVE"TOOLONGNAME.BAS"', 'FILES',
                               'PRINT"[OK]"']),
    ("w.saveext",  "dsklist", ['A=1', 'SAVE"AB.EXTRA"', 'FILES', 'PRINT"[OK]"']),
    # the CONTROL: an exact 8.3 fit must ADD an entry on both sides, or a changed
    # count above says nothing about truncation.
    # ⚠️ A FULL THREE-CHARACTER EXTENSION, AND THAT IS THE INSTRUMENT'S RULE, NOT
    # A STYLE CHOICE. `DIRENT` matches `8 chars + '.' + 3 chars`, so an entry
    # whose extension is SHORTER loses its padding when it falls at the end of a
    # screen row and is not counted -- `SAVE"ABCDEFGH.IJ"` read 5 entries on BOTH
    # sides and looked like a save that never happened on either.
    ("w.savefit",  "dsklist", ['A=1', 'SAVE"ABCDEFGH.IJK"', 'FILES',
                               'PRINT"[OK]"']),
    # 🎯 AND THE ROW THAT PINS THE NAME, not just the count. `6 entries` is
    # equally satisfied by a save that truncated AT THE DOT (`TOOLONGN.BAS`),
    # so the count alone cannot say the split was POSITIONAL. Save under the
    # over-long name, then list the name the positional rule predicts: exactly
    # one entry iff `TOOLONGNAME.BAS` became `TOOLONGN.AME`.
    ("w.savepos",  "dsklist", ['A=1', 'SAVE"TOOLONGNAME.BAS"',
                               'FILES"TOOLONGN.AME"', 'PRINT"[OK]"']),
    # ...and its NEGATIVE twin: the truncate-at-the-dot name must NOT exist.
    ("w.savenodot", "dsklist", ['A=1', 'SAVE"TOOLONGNAME.BAS"',
                                'FILES"TOOLONGN.BAS"', 'PRINT"[OK]"']),

    # === D-FNFUND: THE ROWS THAT MAKE `dev_cmp`'s MISS ARM LIVE ===============
    # 🔴 K-FF1 (`dcmp_miss:` `pop hl` -> `pop bc`, i.e. the miss arm stops
    # restoring HL) REDDENED NOTHING ON THE ROW SET AS IT STOOD, AND THAT WAS A
    # CLAIM ABOUT THE ROWS, NOT ABOUT THE CODE. `dev_cmp` (basic/files.asm) tests
    # `jr nz,dcmp_miss` BEFORE the `inc hl`, so a mismatch at character 0 never
    # advanced HL and "not restoring it" is a no-op. Every filename in both
    # batteries -- FA1.DAT, FB2.DAT, FC*.* , and cassave's CAS:PA -- mismatches
    # `LPT:` / `CRT:` / `CAS:` at character 0. A green knife on that set is a
    # SHADOWED guard, not coverage ([[a-shadowed-guard-has-no-knife]]).
    #
    # 🎯 A FILENAME THAT SHARES ITS LEADING CHARACTERS WITH A DEVICE NAME IS
    # WHAT MAKES THE ARM REACHABLE, and it is a real BASIC claim in its own
    # right: `CRT.DAT` and `CAS.DAT` are FILENAMES -- a device name needs the
    # colon -- so both must survive the dispatch untouched.
    #   d.opendev  `CRT.DAT` mismatches `CRT:` at char 3 (HL advanced 3)
    #   d.savedev  `CAS.DAT` mismatches `CAS:` at char 3, AT THE CARVE SITE
    #              (basic/save.asm `do_save`, one of the two hand-rolled copies
    #              this slice collapsed onto `dev_cmp`)
    #
    # 🎯 AND THE SECOND VERB IS WHAT MAKES THE ROW A READING RATHER THAN A
    # ROUND TRIP. `do_kill` (basic/files.asm:1327) goes STRAIGHT to
    # `parse_disk_fcb` -- no device dispatch at all -- so it sees the true
    # filename whatever the dispatch did to the first verb's copy of it. A row
    # that both WROTE and READ through the dispatch would corrupt the name
    # identically on both sides and agree with itself; that is the shape
    # [[fileside-slice]] was filed for. Written through the dispatch, read
    # around it.
    # ⚠️ `dskerr`/`errface` DELIBERATELY, NOT `dsk`/`bracket`: this row's
    # subject is a FAILURE, and `load_error`'s printed faces would sit
    # UNDERNEATH a `[OK]` that `bracket()` finds first
    # ([[readout-blind-to-its-own-subject]]).
    # 🔴 AND THE FIRST DRAFT OF THESE TWO ROWS READ `<NO OUTPUT>` ON *BOTH*
    # SIDES -- THE CAPTURE WINDOW, NOT THE MACHINE. `OPEN..FOR OUTPUT` +
    # `CLOSE` + `KILL` (and `SAVE` + `KILL`) do more disk work than any row
    # here, and at the default `step` the screen was still blank when it was
    # scraped; at `step=12.0` both read `OK` on both sides. Two 🟢 SHAPE
    # CONTROLS said which variable it was: `XRT.DAT` / `XAS.DAT` -- the same
    # shape with a name sharing NOTHING with a device -- read `<NO OUTPUT>`
    # too, so it was the SHAPE and never the name. The pair was rebuilt on
    # shapes MEASURED to fit the default window (`f.killlit`'s proven
    # `OPEN..AS #1`, and `SAVE` alone as in `f.savelit`).
    # 🎯 The scorer is what stopped this becoming a reading: both sides
    # AGREEING on a sentinel is excluded from agreement by construction, so the
    # rows reported "without a reference" instead of green
    # ([[apparatus-is-part-of-the-measurement]], the too-short-window entry).
    #
    # ⚠️ `d.savedev` HAS NO SECOND VERB, and that is a measured trade, not an
    # oversight: `SAVE` + `KILL` overruns the window. It discriminates because
    # what the knife leaves `do_save` looking at was MEASURED, not assumed --
    # `SAVE".DAT"` prints `load error` (an empty 8.3 base is refused by
    # `build_83_name`). So a green `d.savedev` says the dispatch left the name
    # alone; it could not catch a hypothetical corruption that landed on some
    # OTHER valid name. `d.opendev` keeps its second verb and has no such gap.
    ("d.opendev",  "dskerr", ['OPEN"CRT.DAT"AS #1', 'CLOSE#1',
                              'KILL"CRT.DAT"', 'PRINT"[OK]"']),
    ("d.savedev",  "dskerr", ['SAVE"CAS.DAT"', 'PRINT"[OK]"']),

    # === D-FNEXPR2: WHAT DOES A **NON-STRING** ARGUMENT DO? ==================
    # D-FNEXPR shipped `fname_expr` with its non-string face DELIBERATELY
    # PRESERVED and the question FILED (docs/spec-basic-fnexpr.md §3.3): "the
    # reference may well answer `Type mismatch` -- PLAY's own string operand
    # does -- but that is UNMEASURED, so today's face is preserved rather than
    # guessed at." These eight rows are that measurement, and they are what
    # decides whether the `load error` family should RAISE.
    #
    # 🎯 THE DECISION IS PER VERB AND THE THREE FACES MUST NOT BE ASSUMED TO
    # CONVERGE. zerobas answers a non-quote with THREE different things today:
    # `Syntax error` RAISED (OPEN/KILL/NAME, via stmt_error), `load error`
    # PRINTED-AND-RETURNED (SAVE/LOAD/BLOAD, via load_error), and a WHOLE
    # DIRECTORY LISTING followed by a late `Syntax error` (FILES, via
    # df_nofilespec). Each row below asks its own verb.
    # ⚠️ `dskerr` NOT `dsk`: every subject here is a FAILURE, and `load error`
    # prints and returns, so a `[OK]` lands UNDERNEATH it and `bracket()` would
    # find the `[` first ([[readout-blind-to-its-own-subject]]).
    # ⚠️ n.filesnum is `dsklist` as well as `dskerr`-shaped for exactly
    # D-FILESIDE's reason: the face alone cannot tell "refused at the parse"
    # from "listed the disk, THEN refused".
    ("n.opennum",  "dskerr", ['OPEN 5 AS #1', 'PRINT"[OK]"']),
    ("n.killnum",  "dskerr", ['KILL 5', 'PRINT"[OK]"']),
    ("n.savenum",  "dskerr", ['SAVE 5', 'PRINT"[OK]"']),
    ("n.loadnum",  "dskerr", ['LOAD 5', 'PRINT"[OK]"']),
    ("n.bloadnum", "dskerr", ['BLOAD 5', 'PRINT"[OK]"']),
    ("n.filesnum", "dsklist", ['FILES 5', 'PRINT"[OK]"']),
    # 🔴 AND THE ROW THAT SAYS WHETHER "NON-STRING -> Type mismatch" IS THE
    # WHOLE RULE. D-MISS-1 measured the LET mirror and found it is NOT:
    # `A$=1/0` answers **Division by zero**, not Type mismatch, because the
    # reference EVALUATES first and the RHS's own fault wins
    # (basic/missing.asm els_typecheck, and it is why that routine calls
    # check_expr_errors before type_mismatch_error). `stmt_error` carries the
    # same rule for D-STMTPEND. Whether a FILENAME operand obeys it too is a
    # second claim and gets its own row rather than an analogy
    # [[a-rule-can-claim-more-than-its-evidence]].
    ("n.savediv",  "dskerr", ['SAVE 1/0', 'PRINT"[OK]"']),
    ("n.opendiv",  "dskerr", ['OPEN 1/0 AS #1', 'PRINT"[OK]"']),
    # ⚠️ AND THE BARE FORMS, BECAUSE THE FIX MOVES THEIR FACE TOO. `SAVE` with
    # no argument at all reaches the same gate a non-string does, so converting
    # that gate changes what a bare verb answers whether or not anybody meant
    # it to. An unmeasured face change is exactly the thing D-FNEXPR §3.3
    # refused to make; these rows are what stops this one being that.
    ("n.savebare", "err", ['SAVE', 'PRINT"[OK]"']),
    ("n.loadbare", "err", ['LOAD', 'PRINT"[OK]"']),
    ("n.bloadbare", "err", ['BLOAD', 'PRINT"[OK]"']),

    # === D-FNEXPR2: IS `RUN` REALLY AMBIGUOUS? ===============================
    # TODO.md and docs/spec-basic-fnexpr.md §2 both name `RUN`'s bare-RUN
    # fallthrough (basic/cload.asm:185) as "genuinely ambiguous with
    # RUN <lineno>" and price it as a probable DECLINE. That is a claim about
    # the TOKEN STREAM, and this project has an instrument for claims about the
    # token stream -- the `t.*` rows, which read the STORED LINE BYTES rather
    # than the screen ([[read-the-artifact-when-the-screen-cannot-witness]]).
    #
    # 🎯 IF `RUN 30` STORES A LINE-NUMBER TOKEN AND `RUN A$` STORES NAME BYTES,
    # THE TWO ARE NOT AMBIGUOUS AT ALL and the filed decline is priced against
    # an obstacle that is not there ([[a-filed-blocker-can-name-the-wrong-obstacle]]).
    # basic/tokenise.inc arms line-number mode on RUN_TOKEN and emits
    # LINENO_TOKEN ($0E) + a 16-bit value; whether the REFERENCES do the same is
    # what these two rows ask.
    ("t.runnum",  "tok", ['1 RUN 30']),
    ("t.runvar",  "tok", ['1 RUN A$']),
    # ...and the runtime half. 🔴 THE `[R]` MARKER IS NOT DECORATION: if `RUN A$`
    # falls through to a BARE RUN the program restarts forever, and a silent
    # infinite loop would read `<NO OUTPUT>` -- indistinguishable from a machine
    # that printed nothing. Printing a marker every iteration fills the screen
    # instead, so the loop reads `<RUN SCROLLED OFF>`, which this probe already
    # treats as a reading and not a silence. Three outcomes, three distinct
    # readings: `<File not found>` = RUN takes the expression, `<Syntax error>`
    # / `<Type mismatch>` = it refuses it, `<RUN SCROLLED OFF>` = it ate it as a
    # bare RUN.
    ("n.runvar",   "dskerr", ['PRINT"[R]"', 'A$="FCZ.DAT"', 'RUN A$',
                              'PRINT"[OK]"']),
    # 🟢 The literal control for the row above: `RUN"FCZ.DAT"` on a file that is
    # not there. Without it a red `n.runvar` has two candidate causes -- "RUN
    # refuses expressions" and "RUN cannot load a disk program at all".
    ("n.runlit",   "dskerr", ['RUN"FCZ.DAT"', 'PRINT"[OK]"']),

    # === D-FNRUN: the second data point, and the control the fix must not break
    # 🔴 ONE DATA POINT IS NOT A RULE. `n.runvar` alone would be satisfied by
    # "also accept a bare string variable", which is the cheap wrong fix
    # D-FNEXPR's `f.expr` was built to rule out at OPEN. Same row, one verb over.
    ("n.runexpr",  "dskerr", ['PRINT"[R]"', 'A$="FCZ"', 'RUN A$+".DAT"',
                              'PRINT"[OK]"']),
    # 🔴 AND THE ROW THAT SAYS THE FIX DOES NOT CLAIM MORE THAN IT DOES.
    # `RUN <lineno>` is the form the filed decline said could not be told apart
    # from `RUN <expression>`. The token rows say it CAN be (t.runnum/t.runvar),
    # and D-FNRUN's fix dispatched on LINENO_TOKEN ($0E) -- but dispatching on it
    # only routed that form to `run_prog`, which IGNORED the line number and
    # restarted from the top. ✅ GRADUATED 2026-08-22 (D-RUNLINE): `dr_lineno`
    # resolves the operand through GOTO's own `goto_resolve` and enters
    # `run_prog_at`, so execution begins AT the line. It was RED here for one day
    # by design -- the row existed so D-FNRUN could not be read as having fixed a
    # form it merely learned to RECOGNISE.
    # ⚠️ NOT `dskerr`: no disk is involved, so the VG-8020 is a legitimate
    # SECOND reference here and the row is stronger for it.
    ("n.runline",    "run", ['GOTO 40', 'PRINT"[B]"', 'END', 'RUN 20']),
    # ⚠️ THE DESIGN ASSERTS ERR 8 AND NOTHING MEASURED IT. `goto_resolve` carries
    # GOTO's undefined-line check, so `RUN 99` inherits `Undefined line number`
    # "for free" -- which is exactly the kind of claim that turns out to be wrong.
    # ONE line, so the error is the whole reading: a fixture that printed first
    # would mix a value and a face into one span.
    ("n.runundef",   "run", ['RUN 99']),
    # ⚠️ AND THE `RESTORE_LINE` CLAIM. RUN resets the DATA cursor to the PROGRAM
    # TOP, so starting at line 30 must still READ the DATA in line 10. run_prog's
    # two stores were ONE before this slice (`ld hl,TXTBASE` fed both CURLINE and
    # RESTORE_LINE); splitting them is what this row is for. If RESTORE_LINE had
    # followed the start line, this reads `Out of DATA` instead of 7.
    ("n.rundata",    "run", ['DATA 7', 'GOTO 40',
                             'READ A : PRINT"[";A;"]" : END', 'RUN 30']),
    # 🟢 ...and the control that stops `<NO OUTPUT>` above from meaning "the
    # machine cannot print". A silent infinite loop and a program that printed
    # nothing read IDENTICALLY; only this row separates them.
    ("n.runlinectl", "run", ['PRINT"[B]"', 'END']),
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
    "s.ifctl", "s.forctl", "s.dimctl", "s.readctl", "s.swapctl", "z.fldctl",
    # D-FILESIDE: LITERAL wants, and the literal is the whole point -- see the
    # note above CONTROL_WANT.
    "f.filesbare", "f.fileslitl",
    # D-FNRUN: `n.runline`'s control, and it is GATED rather than merely printed
    # for the reason D-FILESIDE gated its two: an ungated control can go quiet
    # and take its row's meaning with it. `n.runline` reads a zerobas RESTART
    # LOOP, which prints nothing; without a row proving this fixture prints at
    # all, "the machine printed nothing" and "the machine hung" are the same
    # reading.
    "n.runlinectl")
CONTROL_WANT = {"c.let": " 7 ", "r.digctl": " 7 ", "r.strctl": "HI",
                "r.pctctl": " 7 ", "r.bangctl": " 7 ", "r.hashctl": " 7 ",
                "s.ifctl": "OK", "s.forctl": "OK", "s.dimctl": " 7 ",
                "s.readctl": " 7 ", "s.swapctl": " 9  7 ", "z.fldctl": "OK",
                # 🔴 THESE TWO ARE NOT PINNED FOR TIDINESS. `listface` runs on
                # BOTH sides, so a counter that matches nothing reads
                # `0 entries` in both columns and the row AGREES -- green while
                # measuring nothing. Cross-side agreement is the wrong
                # instrument for a readout both sides share. A literal want
                # turns that into a POSITIVE CONTROL FAILING ON A REFERENCE,
                # which this probe already reports as an instrument fault
                # (exit 2, nothing scored) rather than as a regression. Knife
                # K-FS1 is the cut that proves it.
                # ⚠️ FIXTURE-COUPLED ON PURPOSE: `6 entries` is the file count
                # of disk/test720.dsk (TEST.BIN, HI.TXT, PROG.BIN, PROG.BAS,
                # PROG2.BAS, PROG3.BAS). Change that image and this goes red on
                # a REFERENCE, which is the correct loud failure -- the rows
                # below it are measuring a directory listing and there is no
                # honest way to read one without knowing what is in it.
                # 🟢 IT DID EXACTLY THAT ON 2026-09-15 (D-KWRUNFILE), and the
                # count moved 5 -> 6 because `PROG3.BAS` was added on purpose:
                # `RUN"<file>"` and `LOAD",R"` REPLACE the running program, so
                # the only witness a row can have is output from the LOADED
                # program, and every other `.BAS` on the image only POKEs.
                "f.filesbare": "6 entries + OK",
                "f.fileslitl": "0 entries + <File not found>",
                # 🟢 `10 PRINT"[B]" / 20 END` -- the same fixture as n.runline
                # with the GOTO/RUN pair taken out. A literal want, so a
                # REFERENCE failing it is an instrument fault (exit 2) and not a
                # regression.
                "n.runlinectl": "B"}
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
# 🔴 D-FSPEC (2026-09-04): FILESPEC VALIDATION, measured and deferred on a
# MEASURED BLAST RADIUS. The reference refuses a malformed 8.3 filespec with
# `Bad file name`; zerobas builds a pattern that simply matches nothing and says
# `File not found`. And a BLANK filespec is "no filespec at all" there -- it
# lists the whole directory -- where here it is another `File not found`.
# ⚠️ THE FIX BELONGS IN `parse_disk_fcb`, WHICH HAS ELEVEN CALL SITES
# (basic/files.asm:768 names them: LOAD, SAVE, BLOAD, KILL, NAME, FILES...), so
# it is one routine serving every disk verb and a change there changes all of
# them [[a-shared-tail-is-not-a-decision]]. The same forms have NOT been measured
# on those verbs, and doing that is the next step -- not writing the check.
# 🟢 The disk ROM has room (8910 B free, 2026-09-04), so this is deferred on the
# MEASUREMENT that is missing, not on a wall.
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
# 🔴 D-FSPEC (2026-09-04): FILESPEC VALIDATION, measured and deferred on a
# MEASURED BLAST RADIUS. The reference refuses a malformed 8.3 filespec with
# `Bad file name`; zerobas builds a pattern that simply matches nothing and says
# `File not found`. And a BLANK filespec is "no filespec at all" there -- it
# lists the whole directory -- where here it is another `File not found`.
# ⚠️ THE FIX BELONGS IN `parse_disk_fcb`, WHICH HAS ELEVEN CALL SITES
# (basic/files.asm:768 names them: LOAD, SAVE, BLOAD, KILL, NAME, FILES...), so
# it is one routine serving every disk verb and a change there changes all of
# them [[a-shared-tail-is-not-a-decision]]. The same forms have NOT been measured
# on those verbs, and doing that is the next step -- not writing the check.
# 🟢 The disk ROM has room (8910 B free, 2026-09-04), so this is deferred on the
# MEASUREMENT that is missing, not on a wall.
# 🟢 D-DEFERPIN (2026-09-05): each value is a `probe_report.Deferral`, so the
# FACES that make the deferral true are pinned and drift EITHER WAY is RED. This
# probe is why: its three bare-verb deferrals carried the reason "`Missing
# operand` on the CF-3300, `Syntax error` here" long after all three machines had
# come to print `Missing operand`, under a ⚠️ of its own saying the reason must
# not go stale. A warning is not a check.
DEFERRED: dict[str, "probe_report.Deferral"] = {
    # ✅ ALL THIRTEEN OTHER D-FSPEC ROWS GRADUATED THE SAME DAY THEY WERE FILED
    # and are ORDINARY SCORED ROWS above: build_83_name truncates positionally
    # instead of rejecting, and parse_disk_fcb RAISES `Bad file name` (ERR 56)
    # instead of load_error's print-and-return. A deferral honoured is worth more
    # than one filed [[a-deferral-honoured-is-worth-more-than-one-filed]].
    # ⚠️ THESE TWO STAY: a BLANK filespec -- and, from 2026-09-05, a DRIVE-PREFIX
    # -ONLY one -- is "no filespec at all" on the reference (it lists the whole
    # directory), which is a `do_files` question and not a parse_disk_fcb one.
    # ✅ "unmeasured on the other verbs" IS NO LONGER TRUE: `KILL"A:"`,
    # `LOAD"A:"` and `SAVE"A:"` all read `Bad file name` on BOTH sides
    # (m.drvkill/m.drvload/m.drvsave, scored). So the empty-name rejection is
    # right for every verb that has no bare form, and the fix must go in
    # `do_files` -- those three rows are what would catch it going anywhere else.
    # ✅ m.blank and m.drvbare GRADUATED 2026-10-09 (D-FILESBARE): FILES now
    # lists the disk for a blank or drive-only pattern, in disk.rom's hk_files
    # (hkf_pat) -- NOT in the shared builder, and m.drvkill / m.drvload /
    # m.drvsave stayed green to show it. Both are scored rows now.
}

# ✅ ALL EIGHT D-FNARG2 ROWS GRADUATED 2026-08-21 (D-FNEXPR2) and are ORDINARY
# SCORED ROWS above: f.savelit, f.savevar, f.loadlit, f.loadvar, f.bloadlit,
# f.bloadvar, f.fileslit, f.filesvar -- and `f.filesvarl` with them. Thirteen
# more graduated one commit earlier under D-FNEXPR. The deferral was honoured by
# FIXING the rows [[a-deferral-honoured-is-worth-more-than-one-filed]].
#
# 🔴 AND TWO OF THE EIGHT HAD ALREADY BEEN GREEN FOR A DAY WHEN THIS SLICE
# STARTED. Re-read at `cffb34d` before a line of ROM changed, `f.loadlit` and
# `f.bloadlit` BOTH answered `<File not found>` on BOTH sides -- closed by
# D-LOADERR-FIX (2026-08-20) and D-BLNF (2026-08-21) as a SIDE EFFECT, while
# this dict still described them as the `load error` half and TODO.md still
# ranked the whole family as open. A deferred row is only a denominator while
# somebody re-reads it; nobody had. Same shape as the gap sweep's D-LINEMAX
# ("22/53, awaiting sign-off" over an item that had shipped 60/60).
# 🎯 So the residual's own name was wrong: what remained of the "`load error`
# family" was not a FACE question at all. `load_error`'s printed non-raising
# face had already been retired at LOAD and BLOAD; the four rows that still
# diverged -- f.savevar, f.loadvar, f.bloadvar, f.filesvar -- were every one of
# them the ARGUMENT SHAPE, i.e. D-FNEXPR's rule at four more verbs.
#
# PREDICTIONS FOR THE FIX, written here BEFORE the run (cf3300 / zb-after):
#   f.savevar    OK                          / OK
#   f.loadvar    <File not found>            / <File not found>
#   f.bloadvar   <File not found>            / <File not found>
#   f.filesvar   <File not found>            / <File not found>
#   f.filesvarl  0 entries + <File not found>/ 0 entries + <File not found>
#   n.opennum    <Type mismatch>             / <Type mismatch>
#   n.killnum    <Type mismatch>             / <Type mismatch>
#   n.savenum    <Type mismatch>             / <Type mismatch>
#   n.loadnum    <Type mismatch>             / <Type mismatch>
#   n.bloadnum   <Type mismatch>             / <Type mismatch>
#   n.filesnum   0 entries + <Type mismatch> / 0 entries + <Type mismatch>
#   n.savediv    <Division by zero>          / <Division by zero>
#   n.opendiv    <Division by zero>          / <Division by zero>
#   f.paren      OK                          / <Type mismatch>   (still DEFERRED,
#                and it MOVES: `Syntax error` -> `Type mismatch`, see below)
#   n.savebare   <Missing operand>           / <Syntax error>    [2026-09-05:
#   n.loadbare   <Missing operand>           / <Syntax error>     zb now reads
#   n.bloadbare  <Missing operand>           / <Syntax error>     <Missing
#                operand> on all THREE machines and these rows are SCORED --
#                see "NO LONGER DEFERRED (1)" below. The faces above are what
#                they read when this table was taken and stand as taken.]
#   n.runvar     <File not found>            / <RUN SCROLLED OFF> (DEFERRED: RUN
#                is not converted by this slice -- see its own note)

# --- NO LONGER DEFERRED (1): the BARE forms AGREE, measured 2026-09-05 -------
# 🟢 D-MISSOPMSG. These three were deferred with the reason *"`Missing operand`
# on the CF-3300, `Syntax error` here"*, and 🔴 THAT REASON WENT STALE WITHOUT
# ANYTHING SAYING SO -- which is precisely the failure its own ⚠️ warned about one
# round earlier. `scratchpad/missop_msg_probe.py` reads the printed text:
#
#     row      vg8020            cf3300            zb
#     q.save   Missing operand   Missing operand   Missing operand
#     q.load   Missing operand   Missing operand   Missing operand
#     q.bload  Missing operand   Missing operand   Missing operand
#     d.err24  Missing operand   Missing operand   Missing operand  <- the TABLE
#     d.err2   Syntax error      Syntax error      Syntax error     <- CONTROL
#
# 🎯 `d.err24` IS WHAT SEPARATES THE TWO EXPLANATIONS: sub/errmsg.asm:231's
# `em_missing_operand` is wired and reachable, so the old face was about which
# CODE the verb raised, not about a missing message. So they are SCORED now.
#
# 📏 AND THEY GAINED A SECOND REFERENCE. They were kind `dskerr`, which is
# skipped on the diskless VG-8020 on the rule that a machine without a disk
# controller cannot express a disk question -- true of `FIELD`, NOT true here:
# a bare verb fails in the PARSE, before anything chooses cassette or disk, and
# the VG-8020 answers `Missing operand` too (row q.save above, measured on it
# directly). Kind `err` is `errface` WITHOUT that skip. 🔴 A row parked on one
# oracle by a rule about its NEIGHBOURS is a coverage claim nobody re-measured.
#
# ⚠️ WHAT REMAINS OPEN IS ONE ROW AND IT IS NOT HERE: `A$=+` reads `Syntax
# error` here against `Missing operand` on both references (ERR 2 vs 24) -- the
# unary-plus item, which is blocked on a main page-1 carve.

# --- STILL DEFERRED (2): RUN, and its filed blocker is REFUTED --------------
# `RUN A$` is `File not found` on the CF-3300 (row n.runvar) against the 🟢
# literal control `RUN"FCZ.DAT"` (n.runlit), which agrees on both sides -- so
# RUN reaches the file system with a LITERAL here and refuses an EXPRESSION.
# 🔴 AND WHAT IT DOES INSTEAD IS WORSE THAN A REFUSAL: `do_run` reads any
# non-quote as a BARE RUN, so `RUN A$` RESTARTS THE PROGRAM, forever. The `[R]`
# marker in the fixture is what makes that visible -- a silent infinite loop
# would have read `<NO OUTPUT>`, i.e. as a machine that printed nothing.
#
# 🎯 AND THE REASON THE FIX WAS FILED AS A PROBABLE DECLINE IS MEASURED FALSE.
# TODO.md and docs/spec-basic-fnexpr.md §2 both call `RUN`'s fallthrough
# "genuinely ambiguous with RUN <lineno>". That is a claim about the TOKEN
# STREAM, and `t.runnum` / `t.runvar` read the STORED LINE BYTES on all three
# machines:
#     1 RUN 30   ->  8a 20 0e 1e 00 00     RUN_TOKEN, ' ', $0E + word 30
#     1 RUN A$   ->  8a 20 41 24 00        RUN_TOKEN, ' ', "A$"
# byte-identical on vg8020, cf3300 and zb. The tokeniser has ALREADY separated
# them -- LINENO_TOKEN ($0E) is emitted for the line-number form and nothing
# else -- so a parser that tests for $0E first is not guessing at anything.
# The blocker named an obstacle that is not there
# [[a-filed-blocker-can-name-the-wrong-obstacle]].
# ⚠️ NOT FIXED HERE ANYWAY, and deliberately: this slice's subject is the four
# verbs the `load error` residual named, RUN's conversion is a separate edit
# with its own knife, and a decline that has been REFUTED is worth more filed
# accurately than folded in quietly.
# ✅ `n.runvar` AND `n.runexpr` GRADUATED 2026-08-21 (D-FNRUN) and are ordinary
# scored rows above. `RUN A$` and `RUN A$+".DAT"` load and run the named program;
# they were a bare-RUN fallthrough that RESTARTED THE PROGRAM FOREVER.
#
# 🔴 WHAT STAYS DEFERRED IS `RUN <lineno>`, AND IT IS HERE SO THE SLICE CANNOT
# BE READ AS HAVING FIXED A FORM IT MERELY LEARNED TO RECOGNISE. Dispatching on
# LINENO_TOKEN routes that form to `run_prog`, which ignores the number and
# restarts from the TOP; both references restart AT the line and print `[B]`.
# 🎯 AND THE FACE IS NOT WHAT "IGNORE THE OPERAND" WOULD PRODUCE -- it is
# `Syntax error`, not the silent restart loop -- which says the arm does
# something beyond ignoring it. Experiment E-FR1 settled that rather than
# leaving it a hunch: swapping this arm's `jp run_prog` for `jp run_prog_top`
# (D-RUNTAIL's own top-level entry, a 0-BYTE target change) moves the reading
# to `<NO OUTPUT>` -- an honest silent restart. So the `Syntax error` IS
# D-RUNTAIL's nested-run corruption, at the one arm that slice did not convert.
# ⚠️ NOT SHIPPED, deliberately: neither state matches the reference, so there is
# no measured reason to prefer the hang, and the swap also moves bare `RUN`
# inside a program, which no row drives. Filed with the reading.
# ✅ GRADUATED 2026-08-22 (D-RUNLINE, docs/spec-basic-runline.md): `dr_lineno`
# resolves the operand through GOTO's own `goto_resolve` and enters `run_prog_at`,
# so execution begins AT the line and all three sides read `B`. 23 B, funded by
# D-SEEDHOLE2's carve -- page 1 was 11 B before it and 31 B after.
# 🔴 THE E-FR1 HALF ABOVE IS *STILL* NOT SHIPPED, and this slice honoured that
# deferral rather than overriding it. `dr_stored` keeps `jp run_prog`. The reason
# has sharpened: a bare RUN inside a running program CLEARS VARIABLES, so it
# restarts FOREVER on the references too -- the row cannot read a value, it has to
# separate "hangs silently" (correct) from "prints a bogus error then stops" (the
# defect) on a TIMEOUT, with a control saying the fixture would have printed. That
# is what "a form no row drives" actually costs to fix. Spec §4.

# ✅ `f.paren` GRADUATED 2026-08-21 (D-STRPAREN) and is an ordinary scored row.
# It was the ONE row of fourteen D-FNEXPR's filename fix did not close, and
# D-FNEXPR was right to refuse to charge it to the filename gate: `(A$)` was
# refused in EVERY string context, not just a filename one, so the fix belonged
# to the string EVALUATOR. `str_eval_paren` (basic/strvar.asm) closed it along
# with ten sibling contexts measured in basic_probe_strparen.py.
# 🎯 THE DEFERRAL IS WHAT MADE THAT POSSIBLE. Charging the row to the filename
# gate would have priced a string-evaluator hole against the wrong verb and
# probably bought a `(` case that only `fname_expr` could reach
# [[a-deferral-honoured-is-worth-more-than-one-filed]].
# ⚠️ Its own denominator lives in `basic_probe_strparen.py` (eleven contexts,
# three controls, TWO references -- this row has one, being Disk BASIC). This
# row is the FILENAME instance of that rule and stays here, where its siblings
# are.
# ✅ D-FILESIDE'S ROW GRADUATED 2026-08-21 (D-FNEXPR2). `f.filesvarl` was a
# MEASURED, FILED divergence -- the machine listed a whole directory the
# reference never lists, then derailed on the unconsumed argument -- and it is
# an ordinary scored row now, because `do_files` tests for an ARGUMENT instead
# of for a QUOTE and hands it to `fname_expr`. 🎯 IT IS THE ROW THAT PROVES THE
# FIX IS A FIX: the FACE alone reads the same whether the machine refuses at the
# parse or lists five files first, which is why D-FILESIDE built `listface` in
# the first place, and it is the entry COUNT that separates them (5 -> 0).


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
          # 🔴 D-FNEXPR2: ADDED BECAUSE ITS ABSENCE READ AS A SILENCE, AGAIN.
          # `SAVE 1/0` and `OPEN 1/0 AS #1` both scored `<NO OUTPUT>` on the
          # CF-3300 in the first characterization round -- the machine printed
          # `Division by zero` and the classifier could not name it, which is
          # bit-for-bit the shape that made D-FNARG2 add `File not found` here.
          # A classifier that cannot name an error reports it as a SILENCE, and
          # a silence is what a diverging pair agrees on.
          "Division by zero",
          # 🔴 AND THE SAME AGAIN, ONE ROUND LATER. `SAVE` / `LOAD` / `BLOAD`
          # with NO argument answer `Missing operand in 10` on the CF-3300 --
          # raised, with a line number -- and that read as `<NO OUTPUT>` too
          # until the name was here. It is the THIRD wording basic/missing.asm
          # els_typecheck already records zerobas as not producing (D-MISS-1
          # kept `Syntax error` for the LET mirror `A$=`), so naming it is what
          # lets these rows stay an honest DEFERRED divergence instead of a
          # silence that looks like agreement.
          # 🟢 2026-09-05 (D-MISSOPMSG): "a THIRD wording zerobas does not
          # produce here" is FALSIFIED -- sub/errmsg.asm:231 carries it and all
          # three machines now print `Missing operand` for these verbs, so the
          # rows are SCORED. The sentence above is kept because it is why the
          # name is in this list at all; only its tense is wrong.
          "Missing operand",
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
    # 🔴 THE SCREEN HAD TEXT AND THE ALPHABET COULD NOT NAME IT (D-ALPHAGATE).
    # That is a fault in THIS PROBE, not a missing reading, and it must not wear
    # `<NO OUTPUT>`'s clothes -- that sentinel routes the row to "without a
    # reference", a sentence about the MACHINE that reads as "nothing to see".
    # `Missing operand` was absent from three separate alphabets and cost real
    # readings each time. Carry the text so the next omission is loud
    # [[an-unnamed-outcome-reads-as-no-outcome]].
    if txt.replace("Ok", "").strip():
        return f"<UNREADABLE: {txt.strip()[:48]}>"
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
    # 🔴 THE SCREEN HAD TEXT AND THE ALPHABET COULD NOT NAME IT (D-ALPHAGATE).
    # That is a fault in THIS PROBE, not a missing reading, and it must not wear
    # `<NO OUTPUT>`'s clothes -- that sentinel routes the row to "without a
    # reference", a sentence about the MACHINE that reads as "nothing to see".
    # `Missing operand` was absent from three separate alphabets and cost real
    # readings each time. Carry the text so the next omission is loud
    # [[an-unnamed-outcome-reads-as-no-outcome]].
    if txt.replace("Ok", "").strip():
        return f"<UNREADABLE: {txt.strip()[:48]}>"
    return "<NO OUTPUT>"


# --- listface: the DIRECTORY LINES, then the error (D-FILESIDE) -------------
# A THIRD readout rather than a change to either of the two above, for the same
# reason `errface()` was a third rather than a reordering of `bracket()`: 58
# scored rows depend on `bracket()`'s "value first" order and 8 more on
# `errface()`'s "error first", and none of them is under test here.
#
# ⚠️ AN 8.3 ENTRY, NOT A WORD. MSX `FILES` prints `NAME    .EXT` -- the name
# space-padded to 8, then `.`, then the extension padded to 3 -- so the pattern
# below matches a DIRECTORY ENTRY and not, say, the `A$="FC*.*"` in the program
# text (which is above the `RUN` anchor and never in this window anyway).
DIRENT = re.compile(r"[A-Z0-9$_@!&#%~(){}\-][A-Z0-9$_@!&#%~(){}\- ]{7}"
                    r"\.[A-Z0-9$_@!&#%~(){}\- ]{3}")


def listface(raw: str | None) -> str:
    """How many directory entries the RUN printed, AND what ended it.

    Both halves in one string on purpose: `0 entries` alone is satisfied by a
    machine that cannot list a directory at all, and `<Syntax error>` alone is
    exactly the reading that hid this divergence."""
    if raw is None:
        return "<NO CAPTURE>"
    tail = omsx_repl.screen_tail(raw, "RUN")
    if tail is None:
        return ("<RUN SCROLLED OFF>" if str(raw).strip() else "<NO CAPTURE>")
    txt = " ".join(str(tail).split("\n"))
    n = len(DIRENT.findall(txt))
    face = "<none>"
    # 🔴 EVERY MESSAGE ON THE SCREEN, IN SCREEN ORDER -- NOT THE FIRST MATCH IN
    # `ERRORS`. This returned `f"<{e}>"` at the first hit and broke, so a row that
    # printed TWO messages silently lost one, and WHICH one survived was decided
    # by the ORDER OF THE TUPLE rather than by the machine. It cost a published
    # conclusion: `FILES"TOOLONGNAME.EXTRA"` prints `load error` AND THEN
    # `File not found`, and because "File not found" sits three entries earlier
    # in ERRORS the face read `<File not found>` alone -- from which D-FSPEC
    # concluded, twice and in a commit message, that the filed `load error`
    # symptom "is not reproduced". It is reproduced; the readout was hiding it.
    # A readout blind to its own subject fails by AGREEING
    # [[readout-blind-to-its-own-subject]].
    hits = sorted(((txt.find(e), e) for e in ERRORS if e in txt))
    if hits:
        face = "<" + "+".join(e for _i, e in hits) + ">"
    if not hits:
        i, j = txt.find("["), txt.find("]", txt.find("[") + 1)
        if i >= 0 and j > i:
            face = txt[i + 1:j]
        # 🔴 THE SCREEN HAD TEXT AND NEITHER THE ALPHABET NOR A `[...]` SPAN
        # COULD NAME IT (D-ALPHAGATE). `<none>` here would say "the listing ended
        # cleanly" about a screen carrying something nobody modelled -- the same
        # shape as this function's own `<File not found>`-alone bug above, where
        # a readout blind to part of its subject failed by AGREEING. Subtract the
        # directory lines first, or every FILES row would look unreadable.
        elif DIRENT.sub("", txt).replace("Ok", "").strip():
            face = f"<UNREADABLE: {DIRENT.sub('', txt).strip()[:48]}>"
    return f"{n} entries + {face}"


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
        if kind in ("dsk", "dskerr", "dsklist") and side in NO_DISK_SIDES:
            # NOT a reading. A diskless machine cannot express the question, and
            # recording its `Syntax error` as an answer would manufacture an
            # agreement with zerobas out of an absent disk controller.
            out[label] = "<NO DISK ON THIS SIDE>"
            continue
        kw = {}
        if cfg["diska"]:
            dsk = probe_tmp.tmp(f"zb_namspc_{side}_{label}.dsk")
            shutil.copy(TEST_DSK, dsk)
            kw["diska"] = dsk
        if kind == "tok":
            caps = omsx_repl.run_cases(
                cfg["machine"], [("direct", list(cfg["reset"]) + list(lines))],
                batch=False, reset=(), boot=cfg["boot"], step=cfg["step"],
                capture=("stored_line", TXTTAB), **kw)
            out[label] = tokens(caps[0])
            continue
        body = [f"{10 * (k + 1)} {ln}" for k, ln in enumerate(lines)]
        # 🔴 A DISK ROW GETS AT LEAST THE CF-3300's WINDOW ON EVERY SIDE (S10.B
        # increment 2, 2026-10-06). `f.appvarx` (OPEN..AS, CLOSE, OPEN..FOR
        # APPEND, CLOSE) runs 2.28 s on ours and 3.40 s on the CF-3300 (marker to
        # marker), which this table gave 4.5 s and ours 2.5 -- ours was scraped
        # still running and read UNREADABLE while being the FASTER machine. The
        # rows' subject is the name parse, not the time.
        step = cfg["step"]
        if kind in ("dsk", "dskerr", "dsklist"):
            step = max(step, SIDES["cf3300"]["step"])
        caps = omsx_repl.run_cases(
            cfg["machine"],
            [("direct", list(cfg["reset"]) + body + ["RUN"])],
            batch=False, reset=(), boot=cfg["boot"], step=step, **kw)
        out[label] = {"dskerr": errface, "err": errface,
                      "dsklist": listface}.get(kind, bracket)(caps[0])
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
    rotted: list[tuple[str, str]] = []
    for lab in present:
        vals = {s: results[s][lab] for s in sides if lab in results[s]}
        refs = {s: v for s, v in vals.items()
                if s in ("vg8020", "cf3300") and v not in SENTINELS}
        if lab in DEFERRED:
            deferred += 1
            moved = DEFERRED[lab].drift(vals)
            if moved:
                rotted.append((lab, moved))
            print(probe_report.row("....", lab, LABEL_W, vals,
                                   f"   [{DEFERRED[lab]}]"
                                   + (f"   🔴 FACE ROTTED: {moved}" if moved else "")))
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
    if rotted:
        print("\U0001f534 DEFERRED FACE(S) ROTTED — a deferral is a PIN, not a note "
              "(D-DEFERPIN). The row still may not be scored; what moved is the "
              "reading the deferral's REASON is written about, so the reason is "
              "now describing a machine that no longer exists:")
        for lab, why in rotted:
            print(f"    {lab}  {why}")
    if a.gate and (dis or rotted):
        sys.stderr.write(f"namspc: {dis} reading(s) diverge, "
                         f"{len(rotted)} deferred face(s) rotted\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
