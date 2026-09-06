#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""D-FLDWIDTH — what a `FIELD` width may BE, and what `FIELD` does when it isn't.

The residual D-NAMSPC filed and DEFERRED in `TODO.md`: `ex_field`
(basic/field.asm:282) `eval`s its field width and NEVER CHECKS WHAT THE RESULT
IS, so a STRING is accepted as a field width. The row that says so has no space
in it at all:

  z.fldstr   FIELD#1,B$ AS A$(1)   CF-3300: Type mismatch   zerobas: OK

🔴 TWO ROWS ARE NOT A DENOMINATOR, AND "the width" IS FOUR QUESTIONS, NOT ONE.
The residual was filed with the TYPE half only. `ex_field` runs a `call eval`
for the CHANNEL as well, a `var_str_type` check on the TARGET, and the whole
`AS` item parse in a LOOP — so before any byte is priced this battery asks:

  1. WHAT TYPES may a width be? Eight NUMERIC spellings that must keep working
     (`%`/`!`/`#` scalars, a parenthesised unsuffixed name, `+`/`*` expressions,
     a numeric array element, `LEN()`, `VAL()`) against FOUR ways to reach a
     STRING (variable, literal, array element, function). A fix that refuses
     strings by refusing everything it cannot recognise would pass one row of
     the residual and break eight.
     ⚠️ 🎯 AND THE NUMERIC SPELLINGS ARE NOT FREE OF THE `AS` PROBLEM. `AS` is
     not a token (basic/kwtable.inc has no entry), so a width is followed by two
     bare LETTERS — and since D-NAMSPC an UNSUFFIXED name scan crosses a space.
     `FIELD#1,N AS A$` therefore parses as the single name `NA$`, which is why
     `N%`, `(N)` and `N(1)` are in this battery and a bare `N` is only in
     `s.join`: the suffix / `)` / `(` is what TERMINATES the scan before ` AS`.
  2. WHAT DOMAIN? 0, negative, past the BYTE (256/257 — `ex_field` keeps E and
     throws D away), past int16 (70000), a non-integer (10.7: truncate or
     round?), and a running total past the record length (200+100 over a
     256-byte record). ⚠️ D-LPTVERB's R-LS4 was filed with "out-of-byte"
     evidence that was IN byte range; every value here is checked against the
     bound it is supposed to leave.
  3. IS IT THE WIDTH ONLY, OR THE WHOLE STATEMENT? The CHANNEL is a second
     `call eval` with no type check either (`ch.str`), the TARGET's type test
     answers ERR 2 where its `LSET` twin answers ERR 13 (`t.num` vs the shipped
     `t.numctl`), and the item parse is a LOOP, so the SECOND item is where a
     per-item check and a once-at-entry one differ (`m.str2`, `m.trap`).
  4. WHICH ERROR, AND IN WHAT ORDER? `Type mismatch` vs `Illegal function call`
     vs `FIELD overflow` vs `Syntax error` — the NAME is the reading, and the
     reference is not assumed to map them the way this tree does. `o.wt` and
     `o.chan` make two checks compete in one statement so the ORDER is measured
     rather than inferred from a source read.

🎯 THE READING IS `LEN(A$)` — THE FIELD'S OWN WIDTH — NOT `OK`. A width that is
ACCEPTED and a width that is REFUSED-with-the-right-message are the only two
outcomes an `[OK]` fixture can tell apart, and this slice's whole subject lives
between "accepted as 10" and "accepted as 0". So every accepting row reads the
width BACK out of the field table and every refusing row reads the error name
([[a-case-that-agrees-can-agree-for-the-wrong-reason]]).

🔴 EVERY ROW HERE HAS **ONE** REFERENCE. `FIELD`/`LSET` are Disk BASIC and a
diskless Philips VG-8020 answers `Syntax error` to the word — it cannot express
the question, and recording that as a reading would manufacture an agreement out
of an absent disk controller. Every `dsk` row rests on the National CF-3300
alone (the disposition basic_probe_fldary.py / basic_probe_lvsites.py carry).
`s.joinctl` is the one row that needs no disk and is measured on whatever
reference sides are requested.

🟢 EVERY GROUP CARRIES ITS OWN POSITIVE CONTROL ON THE SAME FIXTURE — the
working `FIELD#1,10 AS A$` form (`c.lit`), the two-item form (`c.two`), the
LSET read-back (`c.lset`), the in-domain running total (`d.sumok`), the
expression channel (`ch.expr`), `LSET`'s shipped ERR 13 (`t.numctl`) and the
join with FIELD taken out (`s.joinctl`). Without them a red row has two causes
([[row-with-two-candidate-causes]]).

🔴 A CONTROL FAILING ON A **REFERENCE** AND ON **ZEROBAS** ARE DIFFERENT EVENTS
([[classify-a-control-failure-by-which-side-failed-it]]): a reference miss means
the fixture is broken -> exit 2, score nothing; a zerobas miss is an ordinary
divergence, scored, and it SCOPES its own group.

⚠️ EACH ROW GETS A FRESH COPY OF THE TEST IMAGE — these rows OPEN a
random-access file and some of them write it, so a shared image would let one
row's record buffer decide another's reading ([[test-disk-mutation-gotcha]]).

⚠️ THE ERROR-NAME MATCH IS CASE-INSENSITIVE, AND THAT IS A SCOPE DECISION, NOT
AN ACCIDENT. zerobas prints `File not OPEN` where the reference prints `File not
open`; message WORDING is D-MSGEXACT's surface, not this slice's, and matching
case-sensitively here would score a known, separately-owned divergence inside
every row that happens to raise ERR 59. The canonical name is what is compared.

Clean-room: observed screen output only; the reference ROM is a black box.
"""
from __future__ import annotations

import argparse
import os
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

SIDES = {
    "vg8020": dict(machine="Philips_VG_8020", boot=8.0, step=2.5,
                   reset=("NEW",), diska=False),
    "cf3300": dict(machine="National_CF-3300", boot=14.0, step=4.5,
                   reset=("", "SCREEN 0", "NEW"), diska=True),
    "zb":     dict(machine=ZB_MACHINE, boot=8.0, step=2.5,
                   reset=("NEW",), diska=True),
}

OPEN = 'OPEN"TS.DAT"AS #1'

# (label, kind, [lines])   kind "dsk" needs a disk drive, "run" does not.
CASES = [
    # === 0. THE POSITIVE CONTROLS — the working forms, same fixtures ========
    # 🎯 The reading is the WIDTH, read back out of the field table. `[OK]`
    # cannot separate "accepted as 10" from "accepted as 0", which is the
    # distinction this whole battery is about.
    ("c.lit",     "dsk", [OPEN, 'FIELD#1,10 AS A$', 'PRINT"[";LEN(A$);"]"']),
    ("c.two",     "dsk", [OPEN, 'FIELD#1,5 AS A$,7 AS B$',
                          'PRINT"[";LEN(A$);LEN(B$);"]"']),
    ("c.lset",    "dsk", [OPEN, 'FIELD#1,5 AS A$', 'LSET A$="AB"',
                          'PRINT"[";A$;"]"']),
    # 🟢 THE "MUST NOT DISTURB" PAIR, and they exist because of a CARVE. A
    # LEADING space before the width is skipped by `exf_item`'s own
    # `call skip_spaces` -- which is DEAD, because `eval` reaches `ev_f` whose
    # very first instruction is `call ev_sp` (basic/expr.asm:461). Deleting it
    # pays for half the fix, so it needs rows that would go RED if that reading
    # were wrong: one at the FIRST item (fallthrough into exf_item) and one at
    # the SECOND (the `jr` from exf_comma, past the comma). Green BEFORE and
    # after ([[knife-that-reddens-nothing-is-the-finding]] -- a carve with no row
    # behind it is an unmeasured tidy-up).
    ("c.wsp",     "dsk", [OPEN, 'FIELD#1, 10 AS A$', 'PRINT"[";LEN(A$);"]"']),
    ("c.wsp2",    "dsk", [OPEN, 'FIELD#1,5 AS A$, 7 AS B$',
                          'PRINT"[";LEN(A$);LEN(B$);"]"']),

    # === 1. WHAT TYPES MAY A WIDTH BE — the NUMERIC family =================
    #        Every one of these must keep working. A "refuse what I do not
    #        recognise" fix passes s.* and breaks this whole group.
    ("n.pct",     "dsk", ['N%=10', OPEN, 'FIELD#1,N% AS A$',
                          'PRINT"[";LEN(A$);"]"']),
    ("n.bang",    "dsk", ['N!=10', OPEN, 'FIELD#1,N! AS A$',
                          'PRINT"[";LEN(A$);"]"']),
    ("n.hash",    "dsk", ['N#=10', OPEN, 'FIELD#1,N# AS A$',
                          'PRINT"[";LEN(A$);"]"']),
    # 🎯 THE UNSUFFIXED NAME, PARENTHESISED. `FIELD#1,N AS A$` is s.join (the
    # name scan crosses the space and forms `NA$`); the `)` terminates it, so
    # this row is the same VALUE reaching the width by a spelling the scan
    # cannot swallow. Without it "a double variable width" has no green row.
    ("n.paren",   "dsk", ['N=10', OPEN, 'FIELD#1,(N) AS A$',
                          'PRINT"[";LEN(A$);"]"']),
    ("n.expr",    "dsk", [OPEN, 'FIELD#1,4+6 AS A$', 'PRINT"[";LEN(A$);"]"']),
    ("n.mul",     "dsk", [OPEN, 'FIELD#1,2*5 AS A$', 'PRINT"[";LEN(A$);"]"']),
    # a numeric ARRAY element: the `(` terminates the name scan too.
    ("n.ary",     "dsk", ['DIM N(3)', 'N(1)=10', OPEN, 'FIELD#1,N(1) AS A$',
                          'PRINT"[";LEN(A$);"]"']),
    # FUNCTION results — a numeric function of a STRING, and of a string
    # LITERAL. Both are numeric at the point the width is read.
    ("n.fn",      "dsk", ['B$="ABCDEFGHIJ"', OPEN, 'FIELD#1,LEN(B$) AS A$',
                          'PRINT"[";LEN(A$);"]"']),
    ("n.val",     "dsk", [OPEN, 'FIELD#1,VAL("10") AS A$',
                          'PRINT"[";LEN(A$);"]"']),

    # === 2. THE STRING FAMILY — THE SUBJECT ================================
    #        Four ways to put a STRING where a width belongs. `s.var` is the
    #        residual's own `z.fldstr` in a cleaner spelling: NO SPACE IN IT.
    ("s.var",     "dsk", ['N$="X"', OPEN, 'FIELD#1,N$ AS A$',
                          'PRINT"[";LEN(A$);"]"']),
    ("s.lit",     "dsk", [OPEN, 'FIELD#1,"X" AS A$', 'PRINT"[";LEN(A$);"]"']),
    ("s.ary",     "dsk", ['DIM N$(3)', 'N$(1)="X"', OPEN,
                          'FIELD#1,N$(1) AS A$', 'PRINT"[";LEN(A$);"]"']),
    ("s.fn",      "dsk", [OPEN, 'FIELD#1,STR$(10) AS A$',
                          'PRINT"[";LEN(A$);"]"']),
    # ⇐ THE RESIDUAL'S OTHER ROW, VERBATIM (D-NAMSPC `z.fldvar`). An unsuffixed
    # name: the scan crosses the space, `N AS A$(1)` IS the string array element
    # `NA$(1)`, and the width is therefore a STRING by a second road.
    ("s.join",    "dsk", ['DIM A$(3)', 'N=10', OPEN, 'FIELD#1,N AS A$(1)',
                          'PRINT"[";LEN(A$(1));"]"']),
    # 🟢 ...and the CONTROL that says the join itself is exact, with FIELD taken
    # out of the picture entirely. Needs no disk (D-NAMSPC `z.join`).
    ("s.joinctl", "run", ['DIM A$(3)', 'N=10', 'X=N AS A$(1)', 'PRINT"[OK]"']),

    # === 3. THE DOMAIN =====================================================
    # 🔴 EVERY VALUE HERE LEAVES THE BOUND IT IS SUPPOSED TO LEAVE, checked
    # against that bound and not assumed ([[a-rule-can-claim-more-than-its-evidence]]):
    #   0/-1  leave 1..255      256/257 leave the BYTE `ex_field` keeps in E
    #   70000 leaves int16      200+100 leaves the 256-byte RANDOM record
    ("d.zero",    "dsk", [OPEN, 'FIELD#1,0 AS A$', 'PRINT"[";LEN(A$);"]"']),
    ("d.neg",     "dsk", [OPEN, 'FIELD#1,-1 AS A$', 'PRINT"[";LEN(A$);"]"']),
    ("d.256",     "dsk", [OPEN, 'FIELD#1,256 AS A$', 'PRINT"[";LEN(A$);"]"']),
    ("d.257",     "dsk", [OPEN, 'FIELD#1,257 AS A$', 'PRINT"[";LEN(A$);"]"']),
    ("d.big",     "dsk", [OPEN, 'FIELD#1,70000 AS A$',
                          'PRINT"[";LEN(A$);"]"']),
    # truncate or round? The reading separates them: 10 vs 11.
    ("d.frac",    "dsk", [OPEN, 'FIELD#1,10.7 AS A$', 'PRINT"[";LEN(A$);"]"']),
    ("d.sum",     "dsk", [OPEN, 'FIELD#1,200 AS A$,100 AS B$',
                          'PRINT"[";LEN(A$);LEN(B$);"]"']),
    # ...and the BOUNDARY, one byte either side of the 256-byte record: `d.sumok`
    # is the largest legal total and `d.sum1` the smallest illegal one. Both
    # per-item widths are inside 0..255, so NO per-item domain rule can reach
    # them -- which is what makes the record-length check a SEPARATE question.
    ("d.sum1",    "dsk", [OPEN, 'FIELD#1,200 AS A$,57 AS B$',
                          'PRINT"[";LEN(A$);LEN(B$);"]"']),
    # 🟢 the control for d.sum/d.sum1: the SAME two-item shape, total exactly 256.
    ("d.sumok",   "dsk", [OPEN, 'FIELD#1,200 AS A$,56 AS B$',
                          'PRINT"[";LEN(A$);LEN(B$);"]"']),
    # --- D-RECLEN: THE DENOMINATOR THE ERR-50 DECLINE SAID WAS NOT BUILT -------
    # Every `d.sum*` row above uses the DEFAULT 256-byte record, so not one of
    # them can separate "checked against the RECORD LENGTH" from "checked against
    # a CONSTANT 256". Both rules predict every reading in this file identically.
    # These rows open a NON-default record and put the boundary somewhere the two
    # rules disagree about (docs/spec-basic-fldwidth.md §6.5, TODO ERR-50 item).
    #
    # PREDICTIONS, WRITTEN BEFORE THE RUN:
    #   r.openctl  ` OK `  on both        -- LEN= parses at all (see 🔴 below)
    #   r.ok       ` 64 `  on both        -- total == record, legal either way
    #   r.over     CF-3300 FIELD overflow / zerobas ` 65 `
    #   r.mid      CF-3300 FIELD overflow / zerobas ` 200 `
    #   r.sum      CF-3300 FIELD overflow / zerobas ` 60  50 `
    # i.e. the RECORD-LENGTH rule. Under the CONSTANT-256 rule r.over/r.mid/r.sum
    # would read ` 65 ` / ` 200 ` / ` 60  50 ` on the CF-3300 TOO, and the whole
    # ERR-50 fix would be a 2-byte compare against an immediate instead of a
    # fetch of FCH_RECLENS[ch].
    #
    # 🔴 r.openctl IS LOAD-BEARING AND IS NOT A FORMALITY. If `LEN=` is a syntax
    # error on zerobas, every row below reads "error" on this side for a reason
    # that has NOTHING to do with ERR 50, and the battery would look like a
    # record-length finding while measuring an OPEN parse gap.
    ("r.openctl", "dsk", ['OPEN"TS.DAT"AS #1 LEN=64', 'PRINT"[";"OK";"]"']),
    ("r.ok",      "dsk", ['OPEN"TS.DAT"AS #1 LEN=64', 'FIELD#1,64 AS A$',
                          'PRINT"[";LEN(A$);"]"']),
    ("r.over",    "dsk", ['OPEN"TS.DAT"AS #1 LEN=64', 'FIELD#1,65 AS A$',
                          'PRINT"[";LEN(A$);"]"']),
    # the same question with a wide margin, still under the default 256 -- so a
    # constant-256 implementation cannot accidentally agree by rounding.
    ("r.mid",     "dsk", ['OPEN"TS.DAT"AS #1 LEN=64', 'FIELD#1,200 AS A$',
                          'PRINT"[";LEN(A$);"]"']),
    # and on the RUNNING TOTAL rather than one item, which is the shape d.sum
    # tests against the default record.
    ("r.sum",     "dsk", ['OPEN"TS.DAT"AS #1 LEN=100',
                          'FIELD#1,60 AS A$,50 AS B$',
                          'PRINT"[";LEN(A$);LEN(B$);"]"']),
    # 🔴 r.sum MISSED, AND THE MISS IS A SECOND DIVERGENCE, NOT A BAD ROW.
    # Predicted zb ` 60  50 `; measured `<Syntax error>`. `oo_parse_reclen`
    # (basic/files.asm:578) validates the record length to a POWER OF TWO in
    # 1..256 "so records tile the 512-byte sector with no straddle", and 100 is
    # not one. The CF-3300 got as far as raising FIELD overflow, so it ACCEPTED
    # LEN=100. These two rows separate the two questions r.sum ran together:
    #
    #   r.len100  the LEN= parse ALONE, no FIELD at all
    #             PREDICT: cf3300 ` OK `, zb `<Syntax error>`
    #   r.sum128  the running total against a record zerobas DOES accept
    #             PREDICT: cf3300 FIELD overflow, zb ` 100  50 `
    #
    # ⚠️ r.len100 IS THE FIRST READING OF A NON-TILING `LEN=` AGAINST THE
    # REFERENCE. disk/docs/diskbasic-option-surface.md says "non-tiling ->
    # Syntax error ... byte-identical to CF-3300", but the probe cited for it
    # (probes/disk/disk_probe_openlen.py) drives LEN=128 and nothing else -- a
    # power of two. The byte-identity claim covers a corpus that never contained
    # the case it is being read to cover.
    ("r.len100",  "dsk", ['OPEN"TS.DAT"AS #1 LEN=100', 'PRINT"[";"OK";"]"']),
    ("r.sum128",  "dsk", ['OPEN"TS.DAT"AS #1 LEN=128',
                          'FIELD#1,100 AS A$,50 AS B$',
                          'PRINT"[";LEN(A$);LEN(B$);"]"']),
    # 🎯 THE ROW THAT DECIDES WHICH POST-EVAL CHECK. A deferred FPERR (division
    # by zero) rides the same statement-boundary mechanism as TMISMATCH, and
    # `check_expr_errors` tests BOTH in one 3-byte call while an inline
    # TMISMATCH-only test costs 7. Whether that is the RIGHT answer is a
    # reading, not a byte count.
    ("d.div",     "dsk", [OPEN, 'FIELD#1,1/0 AS A$', 'PRINT"[";LEN(A$);"]"']),

    # === 4. IS IT THE WIDTH ONLY? — the CHANNEL is a second unchecked eval ==
    ("ch.str",    "dsk", ['N$="1"', OPEN, 'FIELD#N$,10 AS A$',
                          'PRINT"[";LEN(A$);"]"']),
    # 🟢 the control: a numeric EXPRESSION channel is legal and works.
    ("ch.expr",   "dsk", [OPEN, 'FIELD#0+1,10 AS A$', 'PRINT"[";LEN(A$);"]"']),

    # === 5. THE SECOND ITEM — where per-item and once-at-entry differ =======
    ("m.str2",    "dsk", ['N$="X"', OPEN, 'FIELD#1,5 AS A$,N$ AS B$',
                          'PRINT"[";LEN(A$);LEN(B$);"]"']),
    # 🎯 ...and whether the FIRST item survived the second one's refusal. The
    # handler reads ERR and the first field's width in one row.
    ("m.trap",    "dsk", ['ON ERROR GOTO 60', 'N$="X"', OPEN,
                          'FIELD#1,5 AS A$,N$ AS B$', 'END',
                          'PRINT"[";ERR;LEN(A$);"]"']),
    ("m.neg2",    "dsk", [OPEN, 'FIELD#1,5 AS A$,-1 AS B$',
                          'PRINT"[";LEN(A$);LEN(B$);"]"']),

    # === 6. THE TARGET's TYPE — the twin of D-LRVAR, one statement over =====
    # `ex_field` answers its `var_str_type` miss with `exf_syn` (ERR 2) where
    # `lrset_common` — the SAME test, in the same file, fixed by D-LRVAR after
    # measuring the CF-3300 — answers ERR 13. Whether the reference splits them
    # is a reading, not a deduction.
    ("t.num",     "dsk", [OPEN, 'FIELD#1,10 AS A', 'PRINT"[OK]"']),
    # 🟢 D-LRVAR's shipped row, unchanged, as this group's control.
    ("t.numctl",  "dsk", [OPEN, 'A=1', 'LSET A=2', 'PRINT"[OK]"']),
    # 🔴 NEGATIVE control: no `AS` at all must STAY refused, so a width fix that
    # accepted anything would have a row in its way.
    ("t.noas",    "dsk", [OPEN, 'FIELD#1,10 A$', 'PRINT"[OK]"']),
    # 🔴 ...and the SECOND negative control, which is the one that BOUNDS the
    # ERR-13 change. `ex_field` answers FOUR different faults with the same
    # `exf_syn`; only ONE of them (the target resolved to a non-STRING) is
    # supposed to become ERR 13. A target that is not a NAME AT ALL must STAY
    # ERR 2, or the fix has widened from "wrong type" to "anything I dislike".
    ("t.nonm",    "dsk", [OPEN, 'FIELD#1,10 AS 5', 'PRINT"[OK]"']),

    # === 7. ORDER — two checks competing inside one statement ===============
    # a STRING width AND a NUMERIC target: whichever error appears is the one
    # the reference reaches FIRST.
    ("o.wt",      "dsk", ['N$="X"', OPEN, 'FIELD#1,N$ AS A', 'PRINT"[OK]"']),
    # ⚠️ `o.wt` CANNOT ORDER THE TWO CHECKS — both faults raise ERR 13, so it
    # agrees whichever fires. `o.dt` is the one that can: a DOMAIN-bad width
    # (ERR 5) against a numeric target (ERR 13), two different codes.
    ("o.dt",      "dsk", [OPEN, 'FIELD#1,-1 AS A', 'PRINT"[OK]"']),
    # a channel that is not open (MAXFILES defaults to 1) AND a string width.
    ("o.chan",    "dsk", ['N$="X"', OPEN, 'FIELD#2,N$ AS A$', 'PRINT"[OK]"']),
]

NO_DISK_SIDES = ("vg8020",)

CONTROLS = ("c.lit", "c.two", "c.lset", "d.sumok", "ch.expr", "t.numctl",
            "s.joinctl")
CONTROL_WANT = {"c.lit": " 10 ", "c.two": " 5  7 ", "c.lset": "AB   ",
                "d.sumok": " 200  56 ", "ch.expr": " 10 ",
                "t.numctl": "<Type mismatch>", "s.joinctl": "<Type mismatch>"}
NEGATIVE = ("t.noas", "t.nonm")
LABEL_W = 10

# Each row is evidence about its own question only while its group's control is
# green on zerobas.
SITE_CONTROL = {
    "n.pct": "c.lit", "n.bang": "c.lit", "n.hash": "c.lit",
    "n.paren": "c.lit", "n.expr": "c.lit", "n.mul": "c.lit",
    "n.ary": "c.lit", "n.fn": "c.lit", "n.val": "c.lit",
    "s.var": "c.lit", "s.lit": "c.lit", "s.ary": "c.lit", "s.fn": "c.lit",
    "s.join": "c.lit",
    "d.zero": "c.lit", "d.neg": "c.lit", "d.256": "c.lit", "d.257": "c.lit",
    "d.big": "c.lit", "d.frac": "c.lit", "d.div": "c.lit",
    "d.sum": "d.sumok", "d.sum1": "d.sumok",
    "m.str2": "c.two", "m.trap": "c.two", "m.neg2": "c.two",
    "ch.str": "ch.expr",
    "t.num": "t.numctl", "t.noas": "c.lit", "t.nonm": "c.lit",
    "o.wt": "t.numctl", "o.dt": "t.numctl", "o.chan": "c.lit",
    "c.wsp": "c.lit", "c.wsp2": "c.two",
}

# --- DEFERRED: measured, printed, NEVER scored ------------------------------
# 🔴 THE RECORD-LENGTH RULE IS A DIFFERENT RULE, AND `d.sumok` IS THE CONTROL
# THAT SAYS THE BOUNDARY IS REAL. 200+56 = 256 is accepted on both sides;
# 200+57 = 257 is `FIELD overflow` (ERR 50) on the CF-3300 and ` 200  57 ` here.
# Both per-item widths are inside 0..255, so the two-stage BYTE rule this slice
# implements is blind to them by construction -- no row conflates the two.
# 💰 Priced at ~27 B against a 6 B page-1 wall and DECLINED WITH NUMBERS
# (docs/spec-basic-fldwidth.md §6.5): the check needs FCH_RECLENS[ch], whose
# only accessor `load_reclen` is SUB-ROM and not callable from ex_field, and
# GP_RECLEN is loaded at GET/PUT time so reading it here would read a stale
# cell. Its own denominator is also unbuilt: every row here uses the DEFAULT
# 256-byte record, so nothing separates "checked against the record length"
# from "checked against a constant 256" -- that needs `OPEN .. LEN=r` rows.
# Filed in TODO.md as its own residual; a deferred row that started AGREEING
# would itself be a finding.
DEFERRED: dict[str, str] = {
    # ✅ D-RECLEN SHIPPED (2026-08-19): `r.openctl`, `r.ok`, `r.over`, `r.mid`,
    # `r.sum128`, `d.sum` and `d.sum1` were ALL deferred here and are now SCORED.
    # The rule they were waiting on -- is the bound the RECORD LENGTH or a
    # constant 256? -- was settled by `r.mid` (a width of 200 into a LEN=64
    # record: 200 is UNDER 256, so a constant-256 test passes it and the CF-3300
    # does not), and ex_field now reads FCH_RECLENS[ch] inline.
    # 🔴 PROMOTING THEM IS THE STRICTER MOVE: a DEFERRED row is measured and
    # printed but never scored, so it cannot fail. These now can.
    # ✅ D-RECLENFIX SHIPPED (2026-09-06): `r.len100` AND `r.sum` ARE SCORED NOW.
    # Both were deferred on the power-of-two `LEN=` rule, and the gate is what
    # said so — the battery went RED with "🔴 FACE ROTTED: zb: pinned
    # '<Illegal function call>', now 'OK'" the moment the widening landed. That
    # is D-DEFERPIN working as designed: a deferred row that starts AGREEING is
    # itself a finding, and a pinned face makes it one instead of a silent pass
    # [[a-filed-face-rots-without-the-row-ceasing-to-diverge]].
    #   r.len100  a non-tiling `LEN=` — `OK` on both sides now. The three fixes
    #             behind it were D-MULREC (mul_reclen was a shift), D-STRADDLE
    #             (fat_rand_put/get span two sectors) and dropping the validator.
    #   r.sum     ran two questions together (a non-tiling LEN=100 AND the
    #             running total); it was kept as the record of a row whose MISS
    #             was the finding, and it now reads `<FIELD overflow>` on both.
    # 🔴 PROMOTING THEM IS THE STRICTER MOVE: a DEFERRED row is measured and
    # printed but never scored, so it cannot fail. These now can.
}


SENTINELS = ("<NO CAPTURE>", "<NO OUTPUT>", "<RUN SCROLLED OFF>",
             "<NO DISK ON THIS SIDE>")

# ⚠️ CANONICAL NAME -> the spellings any side may print for it. The match is
# case-insensitive on purpose: `File not OPEN` (zerobas) vs `File not open`
# (reference) is D-MSGEXACT's surface, not this slice's, and scoring it here
# would put a separately-owned divergence inside every ERR 59 row.
_ERRORS = ("Type mismatch", "Syntax error", "Illegal function call",
           "Overflow", "Division by zero", "FIELD overflow", "Internal error",
           "Bad file number", "File already open", "File not open",
           "Bad file mode", "Sequential I/O only", "Subscript out of range",
           "Redimensioned array", "Out of memory", "Out of string space",
           "String too long", "Missing operand", "Device I/O error",
           "NEXT without FOR", "Undefined line number", "Unprintable error",
           # 🔴 ADDED 2026-09-02 (D-PUT3CONSUME). `Input past end` was ABSENT,
           # and a `GET` past EOF on a freshly-created empty file raises exactly
           # that -- so three CF-3300 rows read `<NO OUTPUT>` and looked like the
           # REFERENCE failing, when the probe simply could not spell what it
           # said. An unreadable answer is indistinguishable from no answer, and
           # on the ORACLE side that reads as "the reference is broken", which is
           # the worst direction for this mistake to point.
           # The rest are the remaining `db "...",0` message strings in
           # sub/errmsg.asm + basic/, added at the same time so the next gap is
           # not found the same way. Re-derived, not hand-listed.
           "Input past end", "File not found", "File still open",
           "Bad file name", "Bad drive name", "Bad sector number", "Bad FAT",
           "Illegal direct", "Direct statement in file", "Can't CONTINUE",
           "No RESUME", "RESUME without error", "RETURN without GOSUB",
           "Out of DATA", "Undefined user function", "Line buffer overflow",
           "String formula too complex")
# 🔴 LONGEST NEEDLE FIRST, AND THIS IS A LANDED DEFECT, NOT TIDINESS. `Overflow`
# is a SUBSTRING of `FIELD overflow` — the first draft listed it earlier and
# scored a screen reading `FIELD overflow in 30` as `<Overflow>`, i.e. the one
# error name this whole battery exists to look for was invisible to its own
# reader ([[readout-blind-to-its-own-subject]]). Found by the FIRST full run,
# in the two rows (`d.sum`, `d.big`) that separate the DOMAIN faults from the
# RECORD-LENGTH one — exactly the rows it would have silently merged.
ERRORS = tuple(sorted(_ERRORS, key=len, reverse=True))


def bracket(raw: str | None) -> str:
    """The `[...]` span the RUN printed, or a canonical error name.

    🔴 THE TAIL AFTER `RUN`, NOT THE WHOLE SCREEN
    ([[readout-blind-to-its-own-subject]]) — the program text is on the screen
    too, and every fixture here contains the word `FIELD`."""
    if raw is None:
        return "<NO CAPTURE>"
    tail = omsx_repl.screen_tail(raw, "RUN")
    if tail is None:
        # NOT "no output": `RUN` off the top of a SCREEN 0 page means the
        # program printed MORE than a screenful, i.e. a runaway (D-NAMSPC §10.5(c)).
        return ("<RUN SCROLLED OFF>" if str(raw).strip() else "<NO CAPTURE>")
    txt = " ".join(str(tail).split("\n"))
    i = txt.find("[")
    j = txt.find("]", i + 1)
    if i >= 0 and j > i:
        return txt[i + 1:j]
    low = txt.lower()
    for e in ERRORS:
        if e.lower() in low:
            return f"<{e}>"
    # 🔴 THE SCREEN HAD TEXT AND THE ALPHABET COULD NOT NAME IT. That is a fault
    # in THIS PROBE, not a missing reading, and `<NO OUTPUT>` hides it -- worse
    # here than in most probes, because a blank on the CF-3300 side reads as
    # "the reference is broken". Carry the text instead. (D-PUT3CONSUME; the
    # same repair lrvar took in D-LSETTM.)
    if low.replace("ok", "").strip():
        return f"<UNREADABLE: {txt.strip()[:48]}>"
    return "<NO OUTPUT>"


def run_side(side: str, only: list[str]) -> dict:
    cfg = SIDES[side]
    out = {}
    for label, kind, lines in CASES:
        if only and label not in only:
            continue
        if kind == "dsk" and side in NO_DISK_SIDES:
            # NOT a reading. A diskless machine cannot express the question, and
            # recording its `Syntax error` would manufacture an agreement with
            # zerobas out of an absent disk controller.
            out[label] = "<NO DISK ON THIS SIDE>"
            continue
        kw = {}
        if cfg["diska"]:
            # ⚠️ A FRESH IMAGE PER ROW — these rows OPEN (and some write) a
            # random-access file ([[test-disk-mutation-gotcha]]).
            dsk = probe_tmp.tmp(f"zb_fldwidth_{side}_{label}.dsk")
            shutil.copy(TEST_DSK, dsk)
            kw["diska"] = dsk
        body = [f"{10 * (k + 1)} {ln}" for k, ln in enumerate(lines)]
        caps = omsx_repl.run_cases(
            cfg["machine"], [("direct", list(cfg["reset"]) + body + ["RUN"])],
            batch=False, reset=(), boot=cfg["boot"], step=cfg["step"], **kw)
        out[label] = bracket(caps[0])
    return out


def main() -> int:
    ap = argparse.ArgumentParser(
        description="D-FLDWIDTH: what a FIELD width may BE, and what FIELD "
                    "does when it isn't")
    ap.add_argument("--sides", default="cf3300,zb")
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

    print("D-FLDWIDTH — what a FIELD width may BE, and what FIELD does when "
          f"it isn't   sides: {', '.join(sides)}")
    print("=" * 78)

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
            if got != CONTROL_WANT[ctl]:
                bad.append((ctl, s, got, CONTROL_WANT[ctl]))
    if bad:
        for lab, s, got, exp in bad:
            print(probe_report.row("FAIL", lab, LABEL_W, {s: got},
                                   "   [POSITIVE CONTROL]"))
            print(f"        wanted {exp!r}")
        print("\n*** A POSITIVE CONTROL FAILED ON A REFERENCE, so nothing was "
              "measured.\n"
              "    Each control is the WORKING form of its own group's fixture "
              "-- the same\n"
              "    program with the offending width/target/channel put right. "
              "A REFERENCE\n"
              "    failing it means the fixture is broken (a disk that did not "
              "mount, a\n"
              "    channel that never opened), not that the rule is wrong. (A "
              "control failing\n"
              "    on `zb` is NOT this: that is an ordinary divergence and IS "
              "scored, because\n"
              "    only a reference is supposed to be right.) Check "
              "build/*.rom, `make\n"
              "    repack-machine` and `make latch-check`, THEN re-read the "
              "rows. Exit 2 (not\n"
              "    1) = the instrument was broken, NOT a regression.")
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
        return got != CONTROL_WANT[ctl]

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
            note = "   [NEGATIVE CONTROL — the reference REFUSES this]"
        own = SITE_CONTROL.get(lab)
        if own and own in present and ctl_red_on_zb(own):
            note += ("   [ITS OWN GROUP CONTROL IS RED ON zb — this row is NOT "
                     "evidence about the WIDTH]")
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
    print("🔴 ORACLE STRENGTH IS NOT UNIFORM: every `FIELD`/`LSET` row is Disk "
          "BASIC, which a diskless VG-8020 cannot express — they rest on the "
          "CF-3300 ALONE. Only `s.joinctl` can have two references.")
    print("DENOMINATOR: (WHAT TYPE the width expression has: an integer "
          "literal, a `%`/`!`/`#` scalar, a parenthesised unsuffixed name, a "
          "numeric array element, a `+`/`*` expression, a numeric FUNCTION of a "
          "string (LEN) and of a literal (VAL) -- against a string VARIABLE, a "
          "string LITERAL, a string ARRAY ELEMENT, a string FUNCTION, and the "
          "unsuffixed name that D-NAMSPC's name scan JOINS with the following "
          "`AS` into a string reference) x (WHAT DOMAIN: 0, negative, past the "
          "BYTE ex_field keeps (256/257), past int16 (70000), a non-integer "
          "(10.7 -- truncate or round), and a RUNNING TOTAL past the 256-byte "
          "record) x (WHICH SURFACE: the width, the CHANNEL's own unchecked "
          "eval, the TARGET's type test, and the SECOND item of a multi-item "
          "list, which is where a per-item check and a once-at-entry one "
          "differ) x (WHICH ERROR and IN WHAT ORDER: two competing faults in "
          "one statement, width-vs-target and channel-vs-width). Every group "
          "carries the WORKING form of its own fixture as its positive "
          "control, and every accepting row reads the WIDTH BACK rather than "
          "printing OK. NOT COVERED: `GET`/`PUT` record I-O through a bad "
          "field; a `LEN=` record length other than the 256-byte default; "
          "`FIELD` on a CAS: channel; and message WORDING (D-MSGEXACT's "
          "surface -- the error-name match here is case-insensitive).")
    if rotted:
        print("🔴 DEFERRED FACE(S) ROTTED — a deferral is a PIN, not a "
              "note (D-DEFERPIN). The row still may not be scored; what moved "
              "is the reading the deferral's REASON is written about:")
        for _lab, _why in rotted:
            print(f"    {_lab}  {_why}")
    if a.gate and (dis or rotted):
        sys.stderr.write(f"fldwidth: {dis} reading(s) diverge [+{len(rotted)} rotted deferred face(s)]\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
