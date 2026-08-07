#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""D-LPTVERB — `LPRINT` / `LPOS` / `LFILES`, the rest of the printer surface.

Measurement `docs/lptverb-msx1-characterization.md`, spec
`docs/spec-basic-lptverb.md`. Predecessor: D-EDITVERB
(`docs/editverb-msx1-characterization.md`), whose apparatus this reuses -- the
`printerport logger` readout, `screen_printer` capture and boot-per-case
discipline all come from there.

Three batteries, three DIFFERENT readouts and three different side sets:

  `lpr-`  the PRINTER LOG. `LPRINT` is `PRINT` with the sink re-pointed, so the
          answer is the byte stream, framing included -- `X\\r\\n`, not `X`.
  `lps-`  the SCREEN. `LPOS(n)` returns a number, so the reading is what `PRINT`
          put on screen -- but its SUBJECT is accumulated printer state, which
          is why this battery boots per case (below).
  `lfl-`  the PRINTER LOG *and* the SCREEN (LFL_SCREEN says which per row), on
          **two sides only** (LFILES_SIDES), over **two disk fixtures**
          (LFL_EMPTY says which per row) -- the populated `test720.dsk` and the
          empty-directory `empty720.dsk` D-DSKMSG added
          (docs/spec-basic-dskmsg.md §3).

⚠️ EVERY BATTERY PLUGS A PRINTER, INCLUDING THE SCREEN ONE. With no printer
plugged the VG-8020's `LSTOUT` tight-polls port $90 forever and the machine
hangs; a `logger` pluggable reports READY unconditionally and changes no screen
output, so plugging it everywhere costs nothing and removes a whole class of
hang. D-EDITVERB learned this by hanging a screen-battery row on an `LLIST`.

🔴 THE `lps-` BATTERY BOOTS PER CASE, AND THAT IS THE LOAD-BEARING APPARATUS
CHOICE HERE. The printer column counter is machine state that SURVIVES a case:
batched, `lps-init` ("a fresh printer head is at column 0") would read whatever
column the PREVIOUS case's `LPRINT` left behind, and it would read it
identically on every repeat because openMSX is deterministic. That is exactly
the shape D-EDITVERB found on `AUTO` -- a batched case measuring the one before
it, producing a plausible reading of the wrong thing that `--repeat` cannot
catch. Accumulated state ⇒ boot-per-case, and it is not caution.

⚠️ AND `run_cases(batch=False)` IGNORES `reset` -- its own docstring says so --
so every boot-per-case battery carries the side's reset INSIDE the case. The
CF-3300's reset is not cosmetic: the leading "" answers its boot date prompt and
`SCREEN 0` puts it in the 40-column mode this scrape reads. Omit them and every
CF-3300 row reads `<NO ECHO>` while the other sides agree perfectly -- an
apparatus failure shaped exactly like one machine disagreeing.

🔴 THE CONTROLS ARE NOT DECORATION, BECAUSE ZEROBAS IS EXPECTED TO BE EMPTY HERE.
All three words lack a `kwtable.inc` entry at the baseline, so the zb column
reads `Syntax error` / `<nothing printed>` for the SUBJECT rows -- and an empty
printer log has two candidate causes on our side, no verb or no working printer
path. `lpr-ctl` drives the same sink through `OPEN"LPT:"`, which already ships,
so every other empty reading is attributable to the verb alone. `lfl-ctlf` does
the same job for the DISK: it proves the fixture is readable before any LFILES
row is believed.

⚠️ AND A CONTROL IS ABOUT THE IMAGE IT MOUNTS, NOT ABOUT "the disk". The
empty-directory rows read `File not found` / `<nothing>` on a fixture `lfl-ctlf`
never touches, so they carry their own control, `lfl-emptyctl`, which SAVEs to
the empty volume and lists the result. Its `CTL     .BAS` is the positive text
that separates "this directory is empty" from "this machine cannot mount or
write" -- the class that scores 8/8 on a dead disk ROM
([[gate-whose-answer-is-an-error-passes-a-dead-subject]]).

Clean-room: typed inputs and observed outputs only, no reference-ROM
disassembly. See CONTRIBUTING.md.
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

ZB_MACHINE = os.environ.get("ZEROBAS_BASIC_MACHINE",
                            "C-BIOS_MSX1_EU_REPACK_DISK")
TEST_DSK = os.environ.get("ZEROBAS_TEST_DSK", "disk/test720.dsk")
# The EMPTY-directory fixture (D-DSKMSG, docs/spec-basic-dskmsg.md §3):
# `python3 tools/make_test_dsk.py --empty`. Same geometry, no files.
EMPTY_DSK = os.environ.get("ZEROBAS_EMPTY_DSK", "disk/empty720.dsk")

SIDES = {
    "vg8020": dict(machine="Philips_VG_8020", boot=8.0, step=2.5,
                   reset=("NEW",)),
    "cf3300": dict(machine="National_CF-3300", boot=14.0, step=4.5,
                   reset=("", "SCREEN 0", "NEW")),
    "zb":     dict(machine=ZB_MACHINE, boot=8.0, step=2.5, reset=("NEW",)),
}
REF_SIDES = ("vg8020", "cf3300")

# 🔴 LFILES IS A DISK-BASIC WORD AND THE VG-8020 HAS NO DISK ROM, SO THAT SIDE
# CANNOT MEASURE IT -- it would measure the absence of a disk interface, not the
# absence of a language feature. This is the half of the filed reason D-EDITVERB
# did NOT refute: `basic_probe_kwsweep.py`'s `lfiles` row carries TWO reasons,
# `NEEDS-DISK` and printer-bound, and only the second one fell. The battery is
# therefore two-sided BY CONSTRUCTION and says so in the report rather than
# leaving a reader to infer it from a silent absence (no-silent-caps).
LFILES_SIDES = ("cf3300", "zb")

# --- the LPRINT battery: readout is the PRINTER LOG ---------------------------
# (label, typed lines)
LPR = [
    # 🔴 THE SINK CONTROL. Not about LPRINT at all: it proves the printer path
    # works on the side under test, so an empty log elsewhere is the VERB.
    ("lpr-ctl",     ['OPEN"LPT:" FOR OUTPUT AS #1', 'PRINT#1,"CTL"',
                     "CLOSE#1"]),
    ("lpr-str",     ['LPRINT"X"']),
    ("lpr-num",     ["LPRINT 5"]),
    ("lpr-neg",     ["LPRINT -5"]),
    ("lpr-semi",    ['LPRINT"A";"B"']),
    ("lpr-comma",   ['LPRINT"A","B"']),
    ("lpr-trsemi",  ['LPRINT"A";']),
    ("lpr-bare",    ["LPRINT"]),
    ("lpr-two",     ['LPRINT"A":LPRINT"B"']),
    # Does the statement END the line (LLIST does) or continue (PRINT does)?
    # The printer half: whether B reaches the printer.
    ("lpr-tail",    ['LPRINT"A":B=9']),
    # 🔴 R-?: is the SCREEN sink restored for the next statement? exec_stmt
    # resets PRDEST at the top of EVERY statement on zerobas, so this row is the
    # one that says whether the reference agrees.
    ("lpr-sink",    ['LPRINT"A":PRINT"SCR"']),
    ("lpr-using",   ['LPRINT USING"##";5']),
    ("lpr-tab",     ['LPRINT TAB(5);"A"']),
    ("lpr-spc",     ['LPRINT SPC(3);"A"']),
    # Does LPRINT accept a #channel like PRINT does?
    ("lpr-hash",    ['LPRINT#1,"A"']),
    ("lpr-inprog",  ['10 LPRINT"P"', "RUN"]),
]

# --- the LPOS battery: readout is the SCREEN ----------------------------------
#
# 🔴 EVERY ROW IS GUARDED WITH `L=7`, AND WITHOUT IT THIS BATTERY COULD AGREE FOR
# THE WRONG REASON. `POS` is a keyword (`basic/kwtable.inc`), so on a machine with
# no `LPOS` entry the character sequence `LPOS(0)` does not fail -- it crunches as
# the VARIABLE `L` followed by the FUNCTION `POS(0)`, and `PRINT LPOS(0)` quietly
# prints two numbers. Measured on zerobas at the baseline: `0  3`.
#
# The first of those numbers is `L`, which defaults to **0** -- exactly what the
# references print for `LPOS(0)` on a fresh printer head. So the unguarded
# `lps-init` row had a reference answer of `0` and an accidental-parse answer
# whose leading value was also `0`, and any normalisation that dropped the second
# number would have scored it AGREE on a machine with no LPOS at all. That is the
# TAB( mistake this project already documents in `kwsweep-msx1-coverage.md`, and
# [[kwsweep-msx1-denominator]]'s rule: a case that agrees can agree for the wrong
# reason.
#
# `L=7` makes the two parses disjoint by construction: the references still print
# `0` (L is not read by LPOS), the accidental parse prints `7  <screen column>`.
# It cannot coincide, whatever POS returns.
LPS = [
    # 🔴 THE INSTRUMENT CONTROL. POS(0) is the SCREEN analogue and already ships
    # on all three sides, so this row says the `PRINT <fn>(0)` readout itself
    # works -- without it a uniform `Syntax error` cannot be told from a broken
    # reading. It is NOT a claim about LPOS.
    ("lps-ctl",     ["PRINT POS(0)"]),
    ("lps-init",    ["L=7", "PRINT LPOS(0)"]),
    ("lps-after",   ["L=7", 'LPRINT"ABC";:PRINT LPOS(0)']),
    ("lps-crlf",    ["L=7", 'LPRINT"ABC":PRINT LPOS(0)']),
    ("lps-arg1",    ["L=7", "PRINT LPOS(1)"]),
    ("lps-argbig",  ["L=7", "PRINT LPOS(255)"]),
    ("lps-argneg",  ["L=7", "PRINT LPOS(-1)"]),
    # 🔴 THE ELEVENTH ROW, ADDED BY D-DSKMSG (docs/spec-basic-dskmsg.md §2),
    # AND IT EXISTS BECAUSE R-LS4 CLAIMED SOMETHING NO ROW MEASURED.
    # R-LS4 reads "there is no domain check -- not even for a negative or an
    # OUT-OF-BYTE value", and its evidence is `LPOS(1)`, `LPOS(255)`,
    # `LPOS(-1)`. **255 is IN byte range.** So the clause about an out-of-byte
    # value rested on a row that cannot separate it from a byte-legal one, and
    # `lps-argneg` alone cannot either -- a `ld a,d / or a` byte-domain check
    # reddens the negative and the 300 identically, which is precisely why the
    # two of them together are what knife K-LS4b cuts against. 300 is int16,
    # positive, and outside 0..255: the smallest case that separates "no domain
    # check at all" from "a byte-domain check that a negative also happens to
    # trip". Three sides -- LPOS is core MSX BASIC, not Disk BASIC.
    ("lps-argover", ["L=7", "PRINT LPOS(300)"]),
    ("lps-noparen", ["L=7", "PRINT LPOS"]),
    ("lps-tab",     ["L=7", 'LPRINT TAB(10);:PRINT LPOS(0)']),
    # 🔴 THIS ROW TOOK THREE TRIES AND THE SECOND ONE SILENTLY CHANGED SUBJECT.
    #  1. `LPRINT"<40 chars>";:PRINT LPOS(0)` as ONE line is 43 characters: the
    #     prompt echo WRAPS at 40 columns, the anchor is never found, and both
    #     references read `<NO ECHO>` -- the echo-wrap trap ([[clearpool-slice]]),
    #     visible only because that sentinel is kept distinct from `<nothing>`.
    #  2. Splitting it into SEPARATE COMMANDS fixed the wrap and broke the
    #     measurement: both references then read **0**, because a separate command
    #     means a return to command level, and R-LP16 flushes the partial printer
    #     line there. The row still looked fine -- a number, agreed on both
    #     references -- while measuring the FLUSH that `scr-lposflush` already
    #     measures, not the counter it is named for.
    #  3. One line, 14-character payload: 37 characters, nothing wraps, and the
    #     counter is read BEFORE any flush.
    # ⚠️ THE PRINTER'S OWN WIDTH WRAP IS STILL NOT MEASURED and is not claimed: a
    # payload long enough to reach a printer's right margin cannot be typed into a
    # 40-column echo readout at all. Filed in the characterization §7, not stated.
    ("lps-multi",   ["L=7", 'LPRINT"01234567890123";:PRINT LPOS(0)']),
]

# --- the SCREEN halves of the printer rules -----------------------------------
# 🔴 A PRINTER-LOG ROW IS STRUCTURALLY BLIND TO HALF OF ITS OWN RULE, and
# D-EDITVERB paid for learning it: knife K3 scored MISS against `llt-tail`
# because that row reads the log, which is byte-identical whether or not the verb
# ends the line. "Does the statement continue to the next one" and "did the error
# message appear" are SCREEN facts. Every printer row whose rule has a screen
# half gets its partner here, named for the row it completes.
SCR = [
    # The screen instrument itself, so a uniform `Syntax error` on the zb side
    # cannot be confused with a dead readout.
    ("scr-ctl",       ['PRINT"CTL"']),
    # Does LPRINT END the line (LLIST does) or continue (PRINT does)? The log
    # cannot say; B can.
    ("scr-lprtail",   ['LPRINT"A":B=9', "PRINT B"]),
    # The log shows SCR did not reach the printer. This shows it reached the
    # SCREEN -- without it, "both empty" is also consistent with PRINT breaking.
    ("scr-lprsink",   ['LPRINT"A":PRINT"SCR"']),
    # `lpr-hash` printed nothing. Nothing is consistent with a Syntax error AND
    # with a silent accept that wrote elsewhere. The message decides.
    ("scr-lprhash",   ['LPRINT#1,"A"']),
    # 🔴 THE ROW THAT RESOLVES AN APPARENT CONTRADICTION IN THE FIRST ROUND.
    # `lpr-trsemi` (`LPRINT"A";`) came back with a TRAILING CRLF in the log while
    # `lps-after` (`LPRINT"ABC";:PRINT LPOS(0)`) read 3 -- i.e. no CRLF had been
    # sent yet at that point in the same line. Both readings are real, so the
    # CRLF must arrive LATER than the statement. This row separates the two
    # candidate explanations by asking LPOS from a SEPARATE command: if BASIC
    # flushes a partial printer line on the return to command level, LPOS reads 0
    # here and 3 in `lps-after`; if it does not, both read 3 and the log's CRLF
    # is an artifact this probe would have to explain some other way.
    ("scr-lposflush", ['LPRINT"A";', "PRINT LPOS(0)"]),
]

# --- the LFILES battery: readout is the PRINTER LOG, two sides ----------------
LFL = [
    # 🔴 THREE CONTROLS, BECAUSE THIS BATTERY HAS THREE WAYS TO READ EMPTY —
    # no verb, no printer, and (since D-DSKMSG) no DISK. The third is
    # `lfl-emptyctl`, at the bottom, and it is not interchangeable with
    # `lfl-ctlf`: it mounts the OTHER fixture.
    # `lfl-ctlf`: the DISK fixture is readable at all (screen FILES).
    ("lfl-ctlf",    ["FILES"]),
    # `lfl-ctlp`: the PRINTER path works on this side.
    ("lfl-ctlp",    ['OPEN"LPT:" FOR OUTPUT AS #1', 'PRINT#1,"CTL"',
                     "CLOSE#1"]),
    ("lfl-all",     ["LFILES"]),
    ("lfl-wild",    ['LFILES"*.BAS"']),
    ("lfl-none",    ['LFILES"NOSUCH.XXX"']),
    # The screen half of `lfl-none`: an empty LOG says nothing about whether a
    # message was printed. Same blindness as `scr-lpr*` above.
    ("lfl-noneb",   ['LFILES"NOSUCH.XXX"']),
    ("lfl-sink",    ['LFILES:PRINT"SCR"']),
    # 🔴 THE EIGHTH ROW, ADDED BY D-LFILES (docs/spec-basic-lfiles.md §2.2), AND
    # IT IS ABOUT `FILES`, NOT `LFILES`. R-LF4 says LFILES's no-match prints
    # `File not found`; zerobas raises no message at all on a no-match, and the
    # cheapest place to fix that is the SHARED walk both verbs run. So the change
    # lands on `FILES` too -- and a change to a verb this battery does not measure
    # is a change made blind. This row measures it: it asks the SCREEN what the
    # reference's own `FILES` says when the pattern matches nothing.
    #
    # It is also the row that decides a DESIGN FORK. If the reference answers
    # `File not found` here, the message belongs in the shared walk; if it answers
    # nothing, it belongs behind the LFILES op alone and `FILES` must keep its
    # silence. Written down as a fork BEFORE the reading, so the implementation
    # cannot be what decides it ([[filed-justification-is-a-claim]]).
    ("lfl-nonef",   ['FILES"NOSUCH.XXX"']),

    # --- the EMPTY-DIRECTORY arm (D-DSKMSG, docs/spec-basic-dskmsg.md §3) ----
    # 🔴 "NO FILES AT ALL ON THE DISK" IS NOT "NO FILE MATCHES THE FILESPEC".
    # R-LF4/R-LF6 above were both taken WITH a pattern, and D-LFILES's §2.4 said
    # so and left the other arm alone; its knife K7 then predicted the miss
    # BEFORE the run -- an unexercised arm, written down, rather than an
    # undiscovered one. These three rows are that arm, and they mount a
    # DIFFERENT fixture (EMPTY_DSK) from every row above.
    #
    # 🔴 AND THE SUBJECT ROWS' EXPECTED ANSWER MAY BE *NOTHING*, WHICH IS ALSO
    # WHAT A DEAD DISK PRINTS. An unmounted drive, an all-$00 disk ROM and an
    # empty directory are indistinguishable by "the listing was empty"
    # ([[gate-whose-answer-is-an-error-passes-a-dead-subject]] -- 8/8 on a dead
    # disk ROM). `lfl-ctlf` does NOT close that: it mounts the OTHER image.
    # `lfl-emptyctl` is the positive control ON THIS IMAGE -- it SAVEs a program
    # to it and lists the result, so the row asserts POSITIVE TEXT (`CTL`) and a
    # silent build cannot satisfy it. It runs on its own /tmp copy for the
    # obvious reason: it writes.
    ("lfl-emptyctl", ["10 REM", 'SAVE"CTL.BAS"', "FILES"]),
    ("lfl-emptyf",  ["FILES"]),
    ("lfl-emptyp",  ["LFILES"]),
    # 🔴 THE SCREEN HALF OF `lfl-emptyp`, AND IT IS NOT OPTIONAL -- the same
    # blindness `lfl-none`/`lfl-noneb` exists for, one arm over. The CF-3300
    # answers an EMPTY listing on the printer (measured: `<nothing printed>`)
    # because R-LF4's message resolves through `raise_error` to the SCREEN, not
    # through the listing's sink. So the printer row alone cannot tell "LFILES
    # refused with a message" from "LFILES did nothing at all", and it is the
    # row a build with no empty-directory disposition would pass.
    ("lfl-emptypb", ["LFILES"]),
]

# Rows in the LFILES battery whose readout is the SCREEN, not the printer log.
# Named explicitly: deriving it from the label would make adding a row a guess.
LFL_SCREEN = {"lfl-ctlf", "lfl-noneb", "lfl-nonef",
              "lfl-emptyctl", "lfl-emptyf", "lfl-emptypb"}
# Rows that mount the EMPTY fixture instead of test720.dsk. Also named
# explicitly -- a battery whose rows disagree about which DISK they are looking
# at is one where a divergence has two candidate causes.
LFL_EMPTY = {"lfl-emptyctl", "lfl-emptyf", "lfl-emptyp", "lfl-emptypb"}
# Rows that WRITE to the image they mount. Each gets a private copy, because
# boot-per-case reboots the machine but keeps mounting the SAME file: a control
# that SAVEs would otherwise make the "empty" directory non-empty for every
# later row in its group, and for the whole of a `--repeat 2` second pass.
LFL_WRITES = {"lfl-emptyctl"}

PROMPTS = omsx_repl.PROMPTS


def screen_rows(raw):
    """The capture as 40-column rows, WITHOUT the function-key row, and with the
    machine's LEFT MARGIN stripped.

    Row 24 is the SCREEN-0 function-key display, which both references show and
    zerobas does not; left in, every row would diverge for a reason unrelated to
    the subject. And the margin differs by machine -- C-BIOS renders at column 1
    and the VG-8020 at column 2 ([[lean-retire-s2-switch]]) -- so rows are fully
    stripped. That discards the SIGN SPACE in a number like ` 0`, which is a real
    loss and the right trade: the sign space is gated by the print battery, and
    keeping it would make every row here diverge on the margin instead.

    ⚠️ SO `lps-` READS `0`, NOT ` 0 `. A rule about LPOS's own number FORMAT
    cannot be stated from this battery; only its VALUE can."""
    txt = raw or ""
    return [txt[i:i + 40].strip() for i in range(0, len(txt), 40)][:-1]


def strip_prompt(row):
    """Drop a leading machine prompt: the references open with `Ok` and zerobas
    with `ZB`. A row that STARTS with one is an echo; a row EQUAL to one is a
    bare prompt (omsx_repl.PROMPTS' own note)."""
    for p in PROMPTS:
        if row.startswith(p):
            return row[len(p):]
    return row


def anchor_for(lines):
    """The typed line the reading starts AFTER -- DERIVED, never hand-listed.

    The reading must span everything the SUBJECT printed, so the anchor is the
    line carrying the verb under test, not the last line typed. D-EDITVERB's
    first version anchored on a trailing `LIST` and thereby measured the listing
    only, so every message the verb emitted fell outside the window and a machine
    that printed nothing would have passed ([[readout-blind-to-its-own-subject]],
    which fails by AGREEING). Deriving it means a new row cannot quietly
    reintroduce a narrow window.

    For `lps-` the verb and the reading are on the SAME line, so the anchor is
    that line and the reading is what follows its echo."""
    for ln in lines:
        for verb in ("LPRINT", "LPOS", "LFILES", "FILES", "RUN", "PRINT"):
            if verb in ln:
                return ln
    return lines[-1] if lines else ""


def reading(raw, anchor):
    """Everything printed AFTER the anchor command's echo.

    Two DISTINCT empty sentinels, never one: `<NO ECHO>` says the apparatus lost
    the anchor and nothing was measured; `<nothing>` says the machine printed
    nothing, which for some rows IS the answer. Collapsing them would let an
    apparatus failure compare equal across sides and score as agreement."""
    rows = [strip_prompt(r) for r in screen_rows(raw)]
    idx = None
    for i, r in enumerate(rows):
        if r == anchor:
            idx = i
    if idx is None:
        return "<NO ECHO>"
    out = [r for r in rows[idx + 1:] if r and r not in PROMPTS]
    return " / ".join(out) if out else "<nothing>"


def prn_reading(raw):
    """The printer half of a `screen_printer` capture, with CR and LF VISIBLE.

    The framing is part of the answer -- `X\\r\\n` is the rule and `X` is not --
    so it may not be stripped."""
    if raw is None:
        return "<NO CAPTURE>"
    _, _, prn = raw.partition("7c")
    if not prn:
        return "<nothing printed>"
    try:
        b = bytes.fromhex(prn)
    except ValueError:
        return "<BAD CAPTURE>"
    return "".join({13: "\\r", 10: "\\n"}.get(c, chr(c) if 32 <= c < 127 else
                                              f"\\x{c:02x}") for c in b)


def run_side(side, only):
    """Every battery this side can measure -> {label: reading}."""
    cfg = SIDES[side]
    out = {}

    def sel(rows):
        return [r for r in rows
                if not only or any(r[0].startswith(o) for o in only)]

    log = os.path.join(tempfile.gettempdir(), f"zb_lptverb_{side}.log")
    plug = (f"set printerlogfilename {{{log}}}", "plug printerport logger")

    def prn_battery(rows, diska=None):
        """A printer-log battery: boot-per-case, reset carried into the case.

        openMSX truncates the log when the pluggable is plugged, i.e. once per
        boot. Batched, the log ACCUMULATES and each case's output is a delta --
        correct right up until one case gets re-run boot-per-case, at which point
        that capture is a whole log and every later delta is silently wrong in
        the direction of a plausible divergence. One boot per case makes every
        capture exactly that case's own output and deletes the class."""
        cases = [(("direct"), list(cfg["reset"]) + list(lines))
                 for _, lines in rows]
        caps = omsx_repl.run_cases(
            cfg["machine"], cases, batch=False, boot=cfg["boot"],
            step=cfg["step"], prologue=plug,
            capture=("screen_printer", log), diska=diska)
        for (label, _), raw in zip(rows, caps):
            out[label] = prn_reading(raw)

    lpr = sel(LPR)
    if lpr:
        prn_battery(lpr)

    lps = sel(LPS)
    if lps:
        # boot-per-case: the printer column is ACCUMULATED state (docstring).
        cases = [("direct", list(cfg["reset"]) + list(lines))
                 for _, lines in lps]
        caps = omsx_repl.run_cases(
            cfg["machine"], cases, batch=False, boot=cfg["boot"],
            step=cfg["step"], prologue=plug)
        for (label, lines), raw in zip(lps, caps):
            out[label] = reading(raw, anchor_for(lines))

    scr_rows = sel(SCR)
    if scr_rows:
        # Screen readout. Batched would be sound for these (no modal state and no
        # accumulated printer column is READ here), but they are cheap and the
        # printer IS written by three of them, so they boot per case for the same
        # reason `lps-` does -- a leftover printer column is exactly what
        # `scr-lposflush` is trying to measure, and inheriting one from the
        # previous case would answer its question for it.
        cases = [("direct", list(cfg["reset"]) + list(lines))
                 for _, lines in scr_rows]
        caps = omsx_repl.run_cases(
            cfg["machine"], cases, batch=False, boot=cfg["boot"],
            step=cfg["step"], prologue=plug)
        for (label, lines), raw in zip(scr_rows, caps):
            out[label] = reading(raw, anchor_for(lines))

    def scr_battery(rows, diska=None):
        """A screen-readout battery on a mounted image: boot-per-case."""
        cases = [("direct", list(cfg["reset"]) + list(lines))
                 for _, lines in rows]
        caps = omsx_repl.run_cases(
            cfg["machine"], cases, batch=False, boot=cfg["boot"],
            step=cfg["step"], prologue=plug, diska=diska)
        for (label, lines), raw in zip(rows, caps):
            out[label] = reading(raw, anchor_for(lines))

    lfl = sel(LFL)
    if lfl and side in LFILES_SIDES:
        # TWO fixtures, and which one a row mounts is data, not a guess.
        for src, rows in ((TEST_DSK, [r for r in lfl if r[0] not in LFL_EMPTY]),
                          (EMPTY_DSK, [r for r in lfl if r[0] in LFL_EMPTY])):
            if not rows:
                continue
            if not os.path.exists(src):
                # A DISTINCT sentinel, and it is not an agreement: the gate
                # treats any `<NO ...>` as a divergence, so a missing fixture
                # can never read as "both sides printed nothing".
                for label, _ in rows:
                    out[label] = "<NO DISK FIXTURE>"
                continue
            tag = os.path.basename(src).replace(".dsk", "")
            ro = [r for r in rows if r[0] not in LFL_WRITES]
            # Read-only rows share ONE working copy; the committed fixture is
            # never the file openMSX is handed.
            if ro:
                dsk = os.path.join(tempfile.gettempdir(),
                                   f"zb_lptverb_{side}_{tag}.dsk")
                shutil.copy(src, dsk)
                scr = [r for r in ro if r[0] in LFL_SCREEN]
                prn = [r for r in ro if r[0] not in LFL_SCREEN]
                if scr:
                    scr_battery(scr, diska=dsk)
                if prn:
                    prn_battery(prn, diska=dsk)
            # Every WRITING row gets a fresh copy of its own.
            for row in [r for r in rows if r[0] in LFL_WRITES]:
                dsk = os.path.join(tempfile.gettempdir(),
                                   f"zb_lptverb_{side}_{tag}_{row[0]}.dsk")
                shutil.copy(src, dsk)
                if row[0] in LFL_SCREEN:
                    scr_battery([row], diska=dsk)
                else:
                    prn_battery([row], diska=dsk)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sides", default="vg8020,cf3300,zb")
    ap.add_argument("--only", default="")
    ap.add_argument("--repeat", type=int, default=1)
    ap.add_argument("--gate", action="store_true",
                    help="exit 1 unless every row agrees across the sides that "
                         "can measure it")
    a = ap.parse_args()

    sides = [s for s in a.sides.split(",") if s]
    only = [o for o in a.only.split(",") if o]
    for s in sides:
        if s not in SIDES:
            sys.stderr.write(f"unknown side {s!r}\n")
            return 2

    results = {}
    for s in sides:
        for r in range(a.repeat):
            got = run_side(s, only)
            if r and got != results[s]:
                sys.stderr.write(
                    f"⚠️  {s}: repeat {r + 1} disagrees with repeat 1 -- the "
                    "reading is not stable, so no verdict is possible\n")
                for k in sorted(set(got) | set(results[s])):
                    if got.get(k) != results[s].get(k):
                        sys.stderr.write(
                            f"    {k}: {results[s].get(k)!r} vs {got.get(k)!r}\n")
                return 2
            results[s] = got

    labels = ([r[0] for r in LPR] + [r[0] for r in LPS]
              + [r[0] for r in SCR] + [r[0] for r in LFL])
    labels = [l for l in labels if any(l in results[s] for s in sides)]

    print(f"D-LPTVERB — LPRINT / LPOS / LFILES   sides: {', '.join(sides)}")
    print("=" * 78)
    # ⚠️ ONE SIDE IS A CHARACTERIZATION, NOT A COMPARISON. Scoring a single-side
    # run as agree/diff would print DIFF on every row of a perfectly good
    # measurement -- a verdict the run cannot support either way. Say so instead.
    if len(sides) < 2:
        for label in labels:
            for s in sides:
                if label in results[s]:
                    print(f"     {label:<12} {results[s][label]!r}")
        print("=" * 78)
        print(f"{len(labels)} row(s) measured on {sides[0]} — CHARACTERIZATION, "
              "no agreement verdict is possible from one side")
        if a.gate:
            sys.stderr.write("lptverb: --gate needs at least two sides\n")
            return 2
        return 0

    agree = dis = 0
    for label in labels:
        # A row is scored over the sides that CAN measure it. LFILES has no
        # VG-8020 answer by construction, and calling that a divergence would
        # make the gate red for a fact about the hardware.
        vals = {s: results[s][label] for s in sides if label in results[s]}
        ok = len(set(vals.values())) == 1 and len(vals) > 1
        if any(v.startswith("<NO ") or v.startswith("<BAD ")
               for v in vals.values()):
            ok = False          # an apparatus sentinel is NEVER an agreement
        note = ""
        if len(vals) < len([s for s in sides]):
            missing = [s for s in sides if label not in results[s]]
            note = f"   [not measurable on: {','.join(missing)}]"
        agree += ok
        dis += not ok
        print(f"{'ok ' if ok else 'DIFF'} {label:<12} "
              + ("  ".join(f"{s}={vals[s]!r}" for s in vals)
                 if not ok else repr(next(iter(vals.values()))))
              + note)
    print("=" * 78)
    print(f"{agree}/{agree + dis} rows agree")
    print(f"LFILES battery sides: {','.join(LFILES_SIDES)} — the VG-8020 has no "
          "disk ROM and CANNOT measure it (stated, not silently dropped)")
    # 🔴 NO SILENT CAPS. If a battery was not selected, say which and why, so a
    # green headline can never be mistaken for whole-surface coverage.
    #
    # ✅ THE `lfl-` HOLE IS CLOSED (D-LFILES, docs/spec-basic-lfiles.md). It read
    # "NOT IMPLEMENTED this slice — no kwtable entry, no stmt_table row; page 1
    # ended at 7 B", and the whole point of printing it rather than dropping the
    # battery silently was that the next slice would have to walk past it. It did.
    # The entry is REMOVED rather than reworded to "implemented", because a list of
    # exclusions that contains a non-exclusion stops being read as a list of holes.
    ran = {l for l in labels}
    for name, rows, why in (
            ("lfl- (LFILES)", LFL, "excluded by --only"),
            ("lpr- (LPRINT)", LPR, "excluded by --only"),
            ("lps- (LPOS)", LPS, "excluded by --only"),
            ("scr- (screen halves)", SCR, "excluded by --only")):
        if not any(r[0] in ran for r in rows):
            print(f"NOT GATED: {name} — {why}")
    if a.gate and dis:
        sys.stderr.write(f"lptverb: {dis} row(s) diverge\n")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
