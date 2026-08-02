#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Error-MESSAGE TEXT characterization -- the exact wording, on both references.

WHY THIS PROBE EXISTS
=====================
Until 2026-08-02 this tree had a POLICY of not comparing message text to the
reference. probes/basic/error_acceptance.py states it outright:

    "Wording stays house-style (we don't copy MSX's verbatim text -- so we DON'T
     compare the message string to the reference)"

So the corpus was STRUCTURALLY BLIND to message wording: every error class it
covers agrees NUMERICALLY (`PRINT ERR`) and the text was never an observable.
The policy has been reversed -- zerobas now wants the EXACT reference message
for every error -- and that reversal needs a denominator before it needs an
implementation. This probe is that denominator.

⚠️ IT MEASURES THE REFERENCES, NOT ZEROBAS'S CORRECTNESS. Its job is to answer
"what exactly does an MSX1 print for error n", per machine, verbatim. The default
walk captures the zb side too, but as the CURRENT-STATE column of a
characterization table, not as a pass/fail.

🔴 THIS PARAGRAPH USED TO END: "The acceptance gate that asserts zb == ref is a
separate, later artifact -- writing the gate and the denominator in one file is
how a readout ends up agreeing with itself." THE GATE THEN LANDED IN THIS FILE
ANYWAY (D-MSGEXACT `--gate`, widened by D-MSGSUB), so the warning now describes
the file it is written in. Recorded rather than deleted, because the hazard it
names is real and the reason it does NOT bite here is specific:

  the gate does not compare zb against a FRESH reference reading. It compares zb
  against REF_TEXT, an EMBEDDED LOCK -- and `--relock` re-measures both machines
  and DIFFS them against that lock. So the two halves cannot drift into agreeing
  with each other: the reference half is a constant that a separate mode has to
  keep reproducing, not a value the gate run itself produces.

Delete `--relock`, or stop running it, and the warning becomes true again.

THE INSTRUMENT: `ERROR n` IN DIRECT MODE
========================================
`ERROR n` raises code n through the same dispatcher every real site funnels
into, prints its message, and returns to the prompt. So a direct-mode walk over
n enumerates the WHOLE message table in one boot per machine -- no per-site
trigger to invent, and no trigger-specific behaviour to disentangle from the
wording. Codes are walked CONTIGUOUSLY (1..26), not sampled: the spec-level
question is "which codes exist and what do they say", and a gap in the walk is
exactly where a wrong answer hides ([[one-row-cannot-separate-two-rules]]).

26 is deliberate -- one PAST the documented last entry (25, `Line buffer
overflow`). It is the CONTROL that proves the walk can see the table's END:
if 26 reads the same as 25, the readout is not tracking the table at all.

THE DISK RANGE (50..64) IS A SECOND, SEPARATE WALK. The VG-8020 has no disk
ROM, so it is expected to answer `Unprintable error` across that whole span
while the CF-3300 answers with real disk wording. That DISAGREEMENT is the
point: it is what proves each machine is being read on its own terms rather
than one answer being echoed for both. A row where both refs agree in that
range would be the suspicious one.

⚠️ WHAT THIS PROBE CANNOT REACH, AND SAYS SO RATHER THAN GUESSING
=================================================================
Four messages are NOT `ERROR n`-reachable and are therefore NOT in this walk:

  `Break`             CTRL-STOP / the STOP statement, not an ERR code at all
  `?Redo from start`  INPUT re-prompt -- needs interactive data entry
  `?Extra ignored`    INPUT surplus -- same
  `Verify error`      cassette VERIFY -- needs a tape image

They are listed here so the denominator states its own hole instead of reading
as complete coverage. `STOP`/`INPUT` are cheap follow-ups (a stored program and
an injected data line); the tape one needs the CAS: harness. None of them is
guessed at from a published reference -- an unmeasured message stays UNMEASURED
in the output table, spelled `<not-measured>`.

READOUT
=======
`omsx_repl.screen_tail(raw, cmdline)` -- the rows between the echoed command and
the next prompt. That is the same readout D-LSTRNG introduced, and it is the
first in this tree to read an error MESSAGE rather than an error CODE.

⚠️ TWO DISTINCT EMPTY SENTINELS, ALWAYS ([[readout-blind-to-its-own-subject]]).
`None` = the echo row was never found, i.e. the machine never ran the case (a
wedge, a date prompt, a SCREEN-1 name table read through a SCREEN-0 scraper).
`""` = the case ran and printed NOTHING. Collapsing those two would report a
dead machine as "this code is silent", which is a fact about the emulator being
reported as a fact about MSX-BASIC. They print as `<none>` and `<empty>`.

SELF-CHECK: THE READOUT MUST BE ABLE TO DISAGREE
================================================
`--selfcheck` runs before the walk and fails the whole run if it does not hold.
Two codes with KNOWN-DIFFERENT wording (2 `Syntax error`, 11 `Division by zero`)
must read back DIFFERENT strings on the same machine. A readout that returns a
constant -- the screen scraper landing on the prompt row, say -- would otherwise
report perfect agreement across all 41 rows and look like a clean measurement.
This is the cheap version of "construct a case the machine definitely gets
wrong and check the readout returns something DIFFERENT from the correct case".
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(REPO, "probes", "disk"))   # bas_tokenise
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402
from bas_tokenise import make_multiline_program  # noqa: E402
from cas_encode import build_cas_basic  # noqa: E402
from omsx_run import _tcl_dquote  # noqa: E402

OMSX = (os.environ.get("OPENMSX") or shutil.which("openmsx")
        or "/opt/homebrew/bin/openmsx")

ZB_MACHINE = os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")
SRC_DSK = os.path.join(REPO, "disk", "test720.dsk")

# side -> how to drive it. Mirrors basic_probe_lnblank.py's SIDES verbatim: the
# CF-3300's leading "" is its BOOT DATE PROMPT (a bare CR accepts the default;
# at the BASIC prompt every later one is a no-op), and its 4.5 s cadence is
# measured, not guessed -- D-LOF caught it EATING keystrokes at shorter ones.
# `SCREEN 0` is explicit because the CF-3300 boots Disk BASIC in SCREEN 1, whose
# name table this scraper does not read.
SIDES = {
    "vg8020": dict(machine="Philips_VG_8020", boot=8.0, step=2.5,
                   reset=("NEW", "SCREEN 0", "CLS"), diska=None),
    "cf3300": dict(machine="National_CF-3300", boot=14.0, step=4.5,
                   reset=("", "NEW", "SCREEN 0", "CLS"), diska=SRC_DSK),
    "zb":     dict(machine=ZB_MACHINE, boot=8.0, step=2.5,
                   reset=("NEW", "SCREEN 0", "CLS"), diska=None),
}
REF_SIDES = ("vg8020", "cf3300")

# The two walks. `main` is the dense err_msgtab domain plus one past its end;
# `disk` is the sparse disk range.
#
# ⚠️ CORRECTION, 2026-08-02 -- THE DOCSTRING'S PREDICTION ABOUT THE DISK RANGE
# WAS WRONG, AND THE MEASUREMENT IS WHAT SAYS SO. It predicted the VG-8020 would
# answer `Unprintable error` across 50..64 for want of a disk ROM. It does not:
# it answers 50..59 verbatim (`FIELD overflow` ... `File not OPEN`) and only
# falls to `Unprintable error` at 60. So codes 50..59 live in MAIN BASIC on a
# diskless machine, and only 60..64 are the disk ROM's own. The two references
# therefore agree on 1..59 and differ ONLY on 60..64 -- which is still the
# per-machine-terms check that paragraph wanted, just at a boundary five codes
# further along than predicted. Kept as a written-down wrong prediction rather
# than quietly corrected: the boundary is the finding.
MAIN_CODES = list(range(1, 27))
DISK_CODES = list(range(50, 65))

# --- the battery `ERROR n` CANNOT REACH -------------------------------------
# Four reference messages are not ERR codes raised through the dispatcher, so a
# code walk is structurally blind to them. Each is (label, mode, lines, echo-key).
#
#   brk / brk-run   `STOP` -- prints `Break`, and in a RUN carries " in <line>".
#                   Not an ERR code at all (no err_msgtab entry, no ERR value).
#   redo / extra    INPUT's re-prompt and surplus-data notes. Driven in DIRECT
#                   mode with the data line injected as its own step: after RUN
#                   the machine is sitting at INPUT's `?` prompt, so the next
#                   injected line IS the answer. The echo key is the answer text
#                   -- INPUT echoes it as `? X`, and _echo_idx matches on
#                   endswith, so `X` finds that row.
#
# `Verify error` (ERR 20's wording, cassette VERIFY) is STILL NOT MEASURED here:
# it needs a tape image and the CAS: harness. It is `<not-measured>` in the
# denominator rather than taken from a published reference.
EXTRA = [
    ("brk",     "direct", ["STOP"],                        "STOP"),
    ("brk-run", "direct", ["10 STOP", "RUN"],              "RUN"),
    ("redo",    "direct", ["10 INPUT A", "RUN", "X"],      "X"),
    ("extra",   "direct", ["10 INPUT A", "RUN", "1,2"],    "1,2"),
]

# --- the D-MSGSUB battery: the ABORT-PATH shapes a direct-mode code walk -----
# cannot see (docs/spec-basic-msgsub.md §5).
#
# D-MSGSUB routes the 14 unimplemented codes' TEXT into a sub-ROM page-1 tenant
# that emits through BIOS `CHPUT`, while main keeps the CRLF / " in <line>" tail
# and the PRDEST discipline. Every row in the main walk above is DIRECT mode, so
# it exercises exactly one of the two arms of `fre_abort_low` and never the
# suffix. These rows exercise the other arm, each paired with a MAIN-RESIDENT
# control of the identical shape -- the control is what says the rig is sound
# when the subject row moves ([[apparatus-is-part-of-the-measurement]]).
#
#   hole-run / ifc-run    RUN mode: does the sub-emitted body get main's own
#                         " in <line>" suffix appended, the same as a resident
#                         message? (`ifc-run` is ERR 5, resident, same shape.)
#   prd-hole / prd-ifc    An error raised on the statement AFTER a `PRINT#` to
#                         an open DISK FILE: the message must still reach the
#                         screen, for a sub-hosted code and a resident one alike.
#   mid-ifc               An error raised *INSIDE* a `PRINT#` -- the only shape
#                         that actually has PRDEST != 0 at raise time. See below.
#                         ⚠️ The three disk rows need one: CF-3300 + zb only.
#
# 🔴 CORRECTION, AND IT IS THE POINT OF THIS COMMENT. The prd-* pair was ADDED
# believing it measured the PRDEST question -- "pchar honours PRDEST, CHPUT
# cannot, so does fre_abort_low's PRDEST zero make them agree?" IT DOES NOT
# MEASURE THAT, and knife K3 is what said so: deleting `ld (PRDEST),a` from
# fre_abort_low changed NEITHER row. The reason is that `PRINT#1,"[";` RESTORES
# PRDEST when the statement ends, so by the time the NEXT statement raises,
# PRDEST is already 0 and the row cannot tell the two builds apart. A green row
# that cannot go red is not a measurement ([[gate-can-be-green-while-measuring-
# nothing]]), and this pair was written into a spec and a characterization doc as
# "the reading that settles CHPUT" before the knife caught it.
#
# `mid-ifc` is the rig that DOES set PRDEST: the error is raised inside the
# PRINT# argument list (`ASC("")` -> ERR 5), while the channel is still the
# print destination. K3 measured BOTH directions on it -- with the PRDEST zero
# the message is on the screen, without it the screen is EMPTY and the message
# went into the file. So it holds down the mechanism the sub-ROM path depends on,
# and nothing in the corpus held it before.
#
# ⚠️ THERE IS NO mid-HOLE ROW, AND THAT IS A FACT ABOUT THE LANGUAGE, NOT A GAP.
# The fourteen sub-hosted codes are reachable only through the `ERROR n`
# STATEMENT, which cannot appear inside a `PRINT#` argument list -- so a
# sub-hosted message can never be raised with PRDEST set. The CHPUT-vs-pchar
# question is therefore BOUNDED AWAY for this path rather than measured, which is
# a weaker claim than the one this battery originally made and the honest one.
# prd-hole is kept because it still measures something real (the open-channel
# state does not divert a sub-hosted message either), just not that.
#
# Boot-per-case, for exactly EXTRA's reason: each row stores a program and most
# leave an open channel behind.
SUBX = [
    ("hole-run", ["10 ERROR 12", "RUN"],                      "RUN",  False),
    ("ifc-run",  ["10 ERROR 5",  "RUN"],                      "RUN",  False),
    ("prd-hole", ['10 OPEN"MSGP.TXT" FOR OUTPUT AS #1',
                  '20 PRINT#1,"[";', "30 ERROR 12", "RUN"],   "RUN",  True),
    ("prd-ifc",  ['10 OPEN"MSGQ.TXT" FOR OUTPUT AS #1',
                  '20 PRINT#1,"[";', "30 ERROR 5",  "RUN"],   "RUN",  True),
    ("mid-ifc",  ['10 OPEN"MSGR.TXT" FOR OUTPUT AS #1',
                  '20 PRINT#1,"[";ASC("")', "RUN"],           "RUN",  True),
    # 🎯 A SUB-HOSTED CODE MUST STILL **TRAP**, NOT PRINT -- the one behavioural
    # risk of D-MSGSUB that no other row covers. A trap prints NOTHING: the
    # message pointer is resolved before raise_error_hl decides trap-vs-abort and
    # is DISCARDED on the trap arm, so the CALSLT must never happen. If the
    # dispatch had been wired at resolve time instead of at print time, this row
    # would show `Illegal direct` where the reference shows only the handler's
    # own output -- and every other row in this battery would still be green,
    # because they all abort.
    ("hole-trap", ["10 ON ERROR GOTO 40", "20 ERROR 12", "30 END",
                   ' 40 PRINT"T";ERR', "RUN"],                "RUN",  False),
]
SUBX_DISK_SIDES = ("cf3300", "zb")   # rows flagged needs_disk run only on these

# MEASURED 2026-08-02, `--walk subx`, before the D-MSGSUB design was fixed. Both
# references agreed on the two rows both can run; the CF-3300 is the oracle for
# the two disk rows (the VG-8020 has no disk ROM, so it is SKIPPED, not guessed).
#
# ⚠️ `mid-ifc` locked 2026-08-02 in the same way, AFTER knife K3 showed the
# prd-* pair was not measuring PRDEST at all (see the SUBX comment above). It is
# the row that actually holds `fre_abort_low`'s PRDEST zero down: K3 measured it
# in BOTH directions -- with the zero, `Illegal function call in 20` on screen;
# without it, the screen is EMPTY and the message is in the file.
SUBX_TEXT = {
    "hole-run": "Illegal direct in 10",
    "ifc-run":  "Illegal function call in 10",
    "prd-hole": "Illegal direct in 30",
    "prd-ifc":  "Illegal function call in 30",
    "mid-ifc":  "Illegal function call in 20",
    # 🎯 THE ONLY ROW ASSERTED ON ITS **WHOLE** TAIL, NOT ITS HEAD -- and both
    # rows of it carry a claim. `T 12` says the handler ran and ERR is right, so
    # `ERROR 12` TRAPPED and the sub-ROM was never called (a printed
    # `Illegal direct` here would mean the dispatch had been wired at message-
    # RESOLVE time instead of at PRINT time). `No RESUME in 40` is the run
    # falling off the end still owing a RESUME -- which every side does
    # identically, so keeping it costs nothing and pins the whole shape.
    # Asserting only the head would have thrown away the second half.
    "hole-trap": "T 12|No RESUME in 40",
}

# --- the self-check pair: two codes whose wording is known to differ ----------
# If these read back EQUAL, the readout is not reading the message.
SELFCHECK = (2, 11)

# =============================================================================
# THE ORACLE LOCK (D-MSGEXACT §5)
# =============================================================================
# Measured 2026-08-02, docs/msgexact-msx1-characterization.md. Embedded rather
# than re-measured every run: booting both references costs ~4 minutes and these
# are ROM constants. `--relock` re-measures and DIFFS against this table, so the
# lock is falsifiable rather than merely asserted -- a captured constant nobody
# can re-derive is indistinguishable from a guess.
#
# 1..59 are values BOTH references gave. 60..64 are CF-3300 only: the VG-8020
# has no disk ROM and answers `Unprintable error` there, so the CF-3300 is the
# oracle for that span and the table says so per-code.
REF_TEXT = {
    1: "NEXT without FOR",        2: "Syntax error",
    3: "RETURN without GOSUB",    4: "Out of DATA",
    5: "Illegal function call",   6: "Overflow",
    7: "Out of memory",           8: "Undefined line number",
    9: "Subscript out of range",  10: "Redimensioned array",
    11: "Division by zero",       12: "Illegal direct",
    13: "Type mismatch",          14: "Out of string space",
    15: "String too long",        16: "String formula too complex",
    17: "Can't CONTINUE",         18: "Undefined user function",
    19: "Device I/O error",       20: "Verify error",
    21: "No RESUME",              22: "RESUME without error",
    23: "Unprintable error",      24: "Missing operand",
    25: "Line buffer overflow",   26: "Unprintable error",
    50: "FIELD overflow",         51: "Internal error",
    52: "Bad file number",        53: "File not found",
    54: "File already open",      55: "Input past end",
    56: "Bad file name",          57: "Direct statement in file",
    58: "Sequential I/O only",    59: "File not OPEN",
    60: "Bad FAT",                61: "Bad file mode",
    62: "Bad drive name",         63: "Bad sector number",
    64: "File still open",
}
CF_ONLY_CODES = frozenset(range(60, 65))

EXTRA_TEXT = {
    "brk": "Break", "brk-run": "Break in 10",
    "redo": "?Redo from start", "extra": "?Extra ignored",
}
VERIFY_TEXT = "Verify error"

# --- THE HOLES: codes zerobas never RAISES -----------------------------------
# Reachable only via `ERROR n`, so zerobas used to answer with its out-of-table
# string. NAMED, never silently skipped: a hole that starts agreeing with the
# reference is itself a finding (someone implemented the code, or the table grew
# an entry), and a silent skip would swallow that.
#
# 🎯 EMPTY SINCE D-MSGSUB (docs/spec-basic-msgsub.md), 2026-08-02. The fourteen
#    12 15 18 19 50 51 53 54 56 57 60 62 63 64
# are hosted in the sub-ROM page-1 tenant SUBROM_IDX_ERRMSG and now print the
# reference's own text, so every row in this walk is in scope and the gate has
# no expected-failure list at all.
#
# ⚠️ KEPT AS A NAMED EMPTY SET RATHER THAN DELETED, and the machinery with it.
# `HOLES = frozenset()` is a positive statement -- "there are none left" -- that
# a reader can check against the row count. Deleting the mechanism would make a
# FUTURE hole (a code someone adds to REF_TEXT but not to the tenant) fail as a
# bare red row with no name on it, and would delete the HOLE-SURPRISE report,
# which is the thing that says "this hole got filled" rather than "this row
# broke". The two are opposite findings and must not collapse into one.
HOLES: frozenset[int] = frozenset()

# What a hole is REQUIRED to print instead -- the exact-cased out-of-table text.
HOLE_TEXT = "Unprintable error"

# --- predicted sets, LOCKED BEFORE THE BUILD (spec §5.1 / §5.2) ---------------
# Written down so the gate cannot be retro-fitted to whatever the build produced.
#
# 🔴 THE FIRST PREDICTION WAS WRONG, AND THE BASELINE RUN IS WHAT SAID SO.
# Spec §5.1 predicted 25 red rows; the pre-edit gate returned FORTY. Both misses
# were in the same direction -- rows I had reasoned about as "not part of the
# wording change" that are:
#
#   the 14 HOLES  print `err_unprintable`, which is ITSELF one of the strings
#                 being case-flipped. A hole is not exempt from the change; it
#                 shares code 23's string. I had filed them mentally as "out of
#                 scope" (§4) and let that leak into the PREDICTION, which is a
#                 different question -- out-of-scope for NEW TEXT, in-scope for
#                 the case fix.
#   code 20       the err_msgtab[20] -> err_verify repoint IS part of this slice
#                 (§3.3, called a free fix) and I simply omitted the row.
#
# The GREEN prediction was exactly right (5/45, precisely PREDICT_GREEN), which
# is the half that guards the design. Recording the miss rather than quietly
# widening the set: a prediction corrected after seeing the answer is not a
# prediction, and the correction is the reading.
PREDICT_RED = (frozenset({1, 2, 3, 4, 6, 7, 8, 11, 13, 14, 17, 20, 21, 22, 23,
                          24, 26, 52, 55, 58, 59, 61})
               | HOLES | {"brk", "brk-run", "redo", "extra"})
# The five already-exact messages. 5 and 25 are LOAD-BEARING: 5 rides the string
# the merge keeps (err_illegal_fn_arr), 25 rides the string whose fall-through
# the slice breaks (err_linebuf_overflow). If either reddens, the design is wrong
# -- they are controls that can move their own subject, not decoration.
PREDICT_GREEN = frozenset({5, 9, 10, 16, 25})

# =============================================================================
# D-MSGSUB's OWN predicted sets (docs/spec-basic-msgsub.md §5.1), locked before
# the build. Recorded BESIDE D-MSGEXACT's rather than replacing them: a slice's
# prediction is a record of what it believed, and overwriting the previous
# slice's would erase the reading that its miss produced.
#
# ⚠️ DERIVED FROM THE EDIT LIST, NOT THE SCOPE LIST. That distinction is exactly
# what D-MSGEXACT got wrong (25 predicted, 40 measured), and the correction it
# filed is [[predicted-red-set-must-not-inherit-scope]]. The D-MSGSUB edit list
# is: one new escape byte in the decoder, a 1 B marker string, four err_msgtab
# entries, one `ld hl` operand in rerr_unprintable, and a new sub-ROM tenant.
# What that can move is the fourteen holes and the two SUBX hole rows -- and
# NOTHING else, because the escape byte is a value no existing message contains
# and both repoints have a target whose text equals the tenant's fallback.
MSGSUB_PREDICT_RED = frozenset(
    {12, 15, 18, 19, 50, 51, 53, 54, 56, 57, 60, 62, 63, 64}
    | {"hole-run", "prd-hole"})
# The rows that MUST NOT move. Five are load-bearing:
#   26           rides the NEW sparse routing (rerr_unprintable -> err_subhosted)
#                and is answered by the TENANT's own fallback. If the dispatch,
#                the tenant or the CALSLT is wrong, this reddens -- it is the
#                only green row in the walk that exercises the new mechanism.
#   23           the UNCHANGED main-resident `Unprintable error`. Pairs with 26
#                to separate "the tenant is broken" from "the string is broken".
#   52 59 55 58 61  matched by rerr_sparse / rerr_sparse2 BEFORE the fall-through.
#                If the new routing swallowed them they would redden.
# Plus D-MSGEXACT's own {5,9,10,16,25} and the four EXTRA rows, all untouched.
#
# ⚠️ `mid-ifc` IS NOT PART OF THE 33/49 BASELINE, and saying so matters. It was
# added AFTER that run, when knife K3 showed the prd-* pair could not see PRDEST
# and a row that could was needed. It was green before the edit and green after
# (it rides a resident message), so it changes no verdict -- but a row added
# mid-slice and then counted in a "before" figure would be a retro-fitted
# prediction. The baseline is 33/49; the post-edit gate is 50/50.
MSGSUB_PREDICT_GREEN = frozenset(
    set(REF_TEXT) - set(MSGSUB_PREDICT_RED)
) | {"brk", "brk-run", "redo", "extra", "ifc-run", "prd-ifc", "mid-ifc",
   "hole-trap"}


def in_scope(code: int) -> bool:
    """A code zerobas EMITS its own message for (so the gate asserts the text)."""
    return code in REF_TEXT and code not in HOLES


def expected(code: int) -> str:
    return HOLE_TEXT if code in HOLES else REF_TEXT[code]


def cases_for(codes: list[int]) -> list[tuple[str, list[str]]]:
    return [("direct", [f"ERROR {n}"]) for n in codes]


def measure(side: str, codes: list[int], *, omsx: str | None = None,
            boot_per_case: bool = False) -> dict[int, str | None]:
    """Drive one side over `codes`, returning code -> screen_tail (or None).

    ONE BOOT for the whole walk. Safe here because no row READS state a previous
    row left behind: every case raises its own code and prints its own message.
    (basic_probe_lnblank.py's `err` battery could NOT batch -- its control read
    the ERRCODE the previous row had just set. That trap does not apply to a
    walk whose only observable is the text printed by the case itself.)
    """
    cfg = dict(SIDES[side])
    machine = cfg.pop("machine")
    diska = cfg.pop("diska")
    reset = cfg.pop("reset")
    tmp = None
    if diska:
        # ⚠️ never hand openMSX the committed image -- a /tmp copy, always.
        tmp = tempfile.NamedTemporaryFile(suffix=".dsk", prefix=f"msgx_{side}_",
                                          delete=False).name
        shutil.copy(diska, tmp)
    try:
        cases = cases_for(codes)
        raws = omsx_repl.run_cases(machine, cases, batch=not boot_per_case,
                                   reset=reset, capture="screen",
                                   omsx=omsx, diska=tmp, **cfg)
    finally:
        if tmp and os.path.exists(tmp):
            os.unlink(tmp)
    out: dict[int, str | None] = {}
    for n, raw in zip(codes, raws):
        out[n] = omsx_repl.screen_tail(raw, f"ERROR {n}")
    return out


def measure_extra(side: str, *, omsx: str | None = None
                  ) -> dict[str, str | None]:
    """Drive the EXTRA battery (the messages `ERROR n` cannot reach).

    ⚠️ BOOT-PER-CASE, deliberately. `brk-run`/`redo`/`extra` each STORE a line
    and leave the machine mid-INPUT or stopped; batching them would let one
    case's stored program and pending prompt answer the next case's readout.
    Four cases is cheap enough that isolation is the obvious call. Because
    boot-per-case IGNORES `reset` (omsx_repl.run_cases), the reset lines are
    PREPENDED to each case body instead -- the CF-3300's boot date-prompt CR and
    the SCREEN 0 the scraper needs live there, and dropping them would leave it
    at a date prompt being read through a SCREEN-0 scraper (`<none>` on every
    row, which would report as "the CF-3300 declines to answer").
    """
    cfg = dict(SIDES[side])
    machine = cfg.pop("machine")
    diska = cfg.pop("diska")
    reset = cfg.pop("reset")
    tmp = None
    if diska:
        tmp = tempfile.NamedTemporaryFile(suffix=".dsk", prefix=f"msgx_{side}_",
                                          delete=False).name
        shutil.copy(diska, tmp)
    try:
        cases = [(mode, list(reset) + lines) for _, mode, lines, _ in EXTRA]
        raws = omsx_repl.run_cases(machine, cases, batch=False,
                                   capture="screen", omsx=omsx, diska=tmp, **cfg)
    finally:
        if tmp and os.path.exists(tmp):
            os.unlink(tmp)
    return {label: omsx_repl.screen_tail(raw, key)
            for (label, _, _, key), raw in zip(EXTRA, raws)}


def measure_subx(side: str, *, omsx: str | None = None
                 ) -> dict[str, str | None]:
    """Drive the D-MSGSUB abort-path battery (SUBX). Boot-per-case, as EXTRA.

    ⚠️ THE DISK ROWS FORCE A DISK ON **BOTH** SIDES, INCLUDING zb. SIDES['zb']
    carries `diska=None` because the code walk needs none -- but `prd-hole`
    OPENs a file, and on a machine with no disk mounted that OPEN raises its own
    error and the row would measure THAT instead of the abort path, while still
    printing a plausible message. Rows that need one are flagged in SUBX and the
    VG-8020 (no disk ROM at all) is skipped for them rather than fed a disk it
    cannot use -- a skipped row reads `<skipped>`, never `<none>`, so it can
    never be mistaken for "the machine declined to answer".
    """
    cfg = dict(SIDES[side])
    machine = cfg.pop("machine")
    diska = cfg.pop("diska")
    reset = cfg.pop("reset")
    rows = [r for r in SUBX if not r[3] or side in SUBX_DISK_SIDES]
    if not rows:
        return {}
    if any(r[3] for r in rows):
        diska = diska or SRC_DSK
    tmp = None
    if diska:
        tmp = tempfile.NamedTemporaryFile(suffix=".dsk", prefix=f"msgs_{side}_",
                                          delete=False).name
        shutil.copy(diska, tmp)
    try:
        cases = [("direct", list(reset) + lines) for _, lines, _, _ in rows]
        raws = omsx_repl.run_cases(machine, cases, batch=False,
                                   capture="screen", omsx=omsx, diska=tmp, **cfg)
    finally:
        if tmp and os.path.exists(tmp):
            os.unlink(tmp)
    return {label: omsx_repl.screen_tail(raw, key)
            for (label, _, key, _), raw in zip(rows, raws)}


# --- the `verify` battery: ERR 20's wording, via a REAL cassette mismatch -----
# `Verify error` is not `ERROR n`-reachable in a way that proves the wording of
# the string the tape path actually prints, and it is the last hole in the
# denominator. Rig: type a program that POKEs 0x98, mount a tape holding the
# 0x99 version, `CLOAD?` -> the compare fails -> the message.
#
# ⚠️ THIS CANNOT REUSE basic_probe_cas_verify.py. That probe hardcodes
# `-machine ZB_MACHINE` + `-cart`, so it can only ever read ZEROBAS -- and its
# assertion is `"verify error" in scr.lower()`, i.e. CASE-INSENSITIVE. It is
# structurally incapable of seeing the very thing measured here. (That is the
# corpus-wide blindness this whole slice is about, present in the one probe that
# already prints this message.)
#
# ⚠️ VG-8020 ONLY, AND THE REASON IS THE TAPE IMAGE, NOT LAZINESS. The tokenised
# CAS is built with absolute line links for TXTBASE $8001, which is the VG-8020's
# BASIC text base. The CF-3300 boots Disk BASIC with a HIGHER TXTTAB, so the same
# image does not describe its memory. Running it there would measure the tape
# format, not the message. Recorded as a single-reference reading rather than
# silently presented as a two-reference lock.
TXTBASE = 0x8001
WITNESS = 0xD0FF
VERIFY_MACHINE = "Philips_VG_8020"


def measure_verify(*, machine: str = VERIFY_MACHINE, omsx: str | None = None,
                   cap_time: float = 60.0, timeout: float = 140.0) -> str | None:
    """Drive one CLOAD? mismatch on `machine`; return the collapsed screen text.

    Returns None if the capture never landed (a wedge) -- distinct from "" for a
    screen that captured but printed nothing, same two-sentinel rule as the rest
    of this probe.
    """
    binary = omsx or OMSX
    tmp = tempfile.mkdtemp(prefix="msgx_verify_")
    cas = os.path.join(tmp, "v_diff.cas")
    # tape holds the 0x99 program; memory will hold 0x98 -> a one-byte mismatch
    with open(cas, "wb") as f:
        f.write(build_cas_basic("V", make_multiline_program(
            [(10, f"POKE&H{WITNESS:04X},&H99")], TXTBASE)))
    out = os.path.join(tmp, "cap.txt")
    # ⚠️ TIMINGS ARE THE VG-8020'S, NOT basic_probe_cas_verify.py's. That probe
    # types at 6.0 s on the REPACK machine; on the VG-8020 that is BEFORE the
    # prompt (omsx_repl.SIDES gives it boot=8.0), and the first measurement run
    # proved it -- the program line never appeared on screen at all and the
    # readout returned a boot banner. Everything is pushed past the real boot.
    typed = [(12.0, f"10 POKE&H{WITNESS:04X},&H98"), (15.0, "\r"),
             (18.0, "CLOAD?"), (20.0, "\r")]
    # ⚠️ `autoruncassettes` MUST BE OFF. openMSX types CLOAD+RUN by itself when a
    # cassette is mounted; the first run here captured `CLOAD Found:V Ok RUN Ok`
    # as boot output, which means the tape had ALREADY BEEN CONSUMED before the
    # probe's own CLOAD? ran -- so the readout would have measured a tape at its
    # end, not a verify mismatch. basic_probe_cas_verify.py does not hit this
    # because its rig differs; anything new driving a cassette does.
    lines = ["set throttle off",
             "set autoruncassettes off",
             "set renderer none; set sound_driver null"]
    for delay, text in typed:
        lines.append(f"after time {delay} {{ type {_tcl_dquote(text)} }}")
    lines += [
        "proc cap {} {",
        f"  set f [open {{{out}}} w]",
        "  binary scan [debug read_block {VRAM} 0x0000 960] H* h0; puts $f \"s0=$h0\"",
        "  close $f; exit }",
        f"after time {cap_time} {{ cap }}",
    ]
    tcl = out + ".tcl"
    with open(tcl, "w") as f:
        f.write("\n".join(lines) + "\n")
    # ⚠️ ORDER MATTERS. openMSX processes command-line options IN SEQUENCE, and
    # the auto-run fires when the cassette is INSERTED -- so the setting has to
    # be off BEFORE `-cassetteplayer`, not merely somewhere in the -script (which
    # runs too late; the first fix attempt put it there and the tape was still
    # consumed at boot).
    cmd = [binary, "-machine", machine,
           "-command", "set autoruncassettes off",
           "-cassetteplayer", cas, "-script", tcl]
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL, start_new_session=True)
    deadline = time.time() + timeout
    while proc.poll() is None and time.time() < deadline:
        time.sleep(0.1)
    if proc.poll() is None:
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
    scr = None
    if os.path.exists(out):
        scr = ""
        for ln in open(out):
            k, _, v = ln.strip().partition("=")
            if k == "s0":
                scr += "".join(chr(c) if 32 <= c < 127 else " "
                               for c in bytes.fromhex(v))
        scr = re.sub(r"\s+", " ", scr).strip()
    shutil.rmtree(tmp, ignore_errors=True)
    return scr


def show(v: str | None) -> str:
    """Two distinct empty sentinels, never collapsed."""
    if v is None:
        return "<none>"
    if v == "":
        return "<empty>"
    return v


def selfcheck(readings: dict[int, str | None], side: str) -> list[str]:
    a, b = SELFCHECK
    va, vb = readings.get(a), readings.get(b)
    problems = []
    if va is None or vb is None:
        problems.append(
            f"{side}: selfcheck codes {a}/{b} did not both read "
            f"({show(va)} / {show(vb)}) -- the walk never reached them")
    elif va == vb:
        problems.append(
            f"{side}: selfcheck FAILED -- ERROR {a} and ERROR {b} read the SAME "
            f"string {va!r}. The readout is not tracking the message; every "
            f"'agrees' below would be an artefact.")
    return problems


def head(v: str | None) -> str | None:
    """First screen row of a reading. `redo` trails INPUT's re-prompt and the
    function-key row, which differ between machines; the message is the head."""
    return None if v is None else v.split("|")[0].strip()


def run_gate(*, omsx: str | None = None, with_verify: bool = False) -> int:
    """Assert zerobas == the measured reference text, per row. Returns 0/1."""
    # ⚠️ GUARD THE INSTRUMENT BEFORE TRUSTING A ROW. A SUBX row added but not yet
    # measured on a reference sits at None; `have == None` is merely False, so the
    # row would read as an ordinary red -- "zerobas is wrong" -- when the truth is
    # "nobody has measured what right looks like". Those are opposite findings.
    unmeasured = [k for k, v in SUBX_TEXT.items() if v is None]
    if unmeasured:
        print(f"REFUSING TO GATE: SUBX rows {unmeasured} have no measured "
              f"reference value yet. Run `--walk subx --sides vg8020,cf3300,zb` "
              f"and lock them into SUBX_TEXT first.", file=sys.stderr)
        return 2
    codes = MAIN_CODES + DISK_CODES
    print(f"# gate: driving zb ({SIDES['zb']['machine']}) over {len(codes)} codes"
          f" + {len(EXTRA)} extras ...", file=sys.stderr, flush=True)
    got = measure("zb", codes, omsx=omsx)
    got_x = measure_extra("zb", omsx=omsx)
    got_s = measure_subx("zb", omsx=omsx)

    fails: list[str] = []
    hole_surprises: list[str] = []
    npass = 0
    for n in codes:
        want, have = expected(n), head(got.get(n))
        if have == want:
            npass += 1
            continue
        if n in HOLES:
            # A hole reading the REAL reference text is not a failure of this
            # slice -- it means the code got implemented. Report it loudly and
            # separately rather than as a red row or, worse, a silent skip.
            if have == REF_TEXT[n]:
                hole_surprises.append(
                    f"  code {n}: hole now prints the REFERENCE text "
                    f"{have!r} -- implemented? update HOLES.")
                continue
        fails.append(f"  code {n:3d}: want {want!r}, got {show(have)}")
    for label, _, _, _ in EXTRA:
        want, have = EXTRA_TEXT[label], head(got_x.get(label))
        if have == want:
            npass += 1
        else:
            fails.append(f"  {label:8s}: want {want!r}, got {show(have)}")
    # SUBX (D-MSGSUB §5.2): the RUN-mode arm and the PRDEST!=0 arm. Two subject
    # rows, each with a MAIN-RESIDENT control of the identical shape -- so a
    # green subject row that agrees for the wrong reason (a rig that prints the
    # same thing whatever it is asked) is caught by its control moving too.
    for label, _, _, _ in SUBX:
        want = SUBX_TEXT[label]
        # A `|` in the locked value means "assert every screen row", not just the
        # first -- `head()` is the default because most rows trail machine-
        # specific junk, but a row whose FULL tail agrees on all three sides
        # should be held to all of it.
        raw_s = got_s.get(label)
        have = (raw_s.strip() if ("|" in want and raw_s is not None)
                else head(raw_s))
        if have == want:
            npass += 1
        else:
            fails.append(f"  {label:8s}: want {want!r}, got {show(have)}")

    total = len(codes) + len(EXTRA) + len(SUBX)
    if with_verify:
        total += 1
        scr = measure_verify(omsx=omsx)
        if scr and VERIFY_TEXT in scr:
            npass += 1
        else:
            fails.append(f"  verify  : want {VERIFY_TEXT!r} on screen, "
                         f"got {show(scr)}")

    print()
    print(f"msgexact gate: {npass}/{total}")
    print(f"  in-scope rows "
          f"{sum(1 for n in codes if in_scope(n)) + len(EXTRA) + len(SUBX)}"
          f", named holes {len(HOLES)}"
          f"{' , verify row' if with_verify else ''}")
    if hole_surprises:
        print("\nHOLE SURPRISES (not failures -- but do not ignore):")
        for h in hole_surprises:
            print(h)
    if fails:
        print("\nFAIL:")
        for f in fails:
            print(f)
        # 🔴 THE PREDICTION IS CHECKED HERE, NOT IN A COMMENT. A predicted set
        # nobody diffs against the run is a wish. D-MSGSUB predicted 16 red rows
        # of 49; if the pre-edit baseline disagrees, THAT is the reading and the
        # prediction stays on record rather than being widened to fit.
        red = {int(f.split()[1].rstrip(':')) if f.strip().startswith("code")
               else f.split(':')[0].strip() for f in fails}
        extra_red = red - set(MSGSUB_PREDICT_RED)
        missing = set(MSGSUB_PREDICT_RED) - red
        print(f"\nvs D-MSGSUB PREDICT_RED ({len(MSGSUB_PREDICT_RED)} rows): "
              f"{len(red)} red")
        if extra_red:
            print(f"  UNPREDICTED red: {sorted(map(str, extra_red))}")
        if missing:
            print(f"  predicted red but GREEN: {sorted(map(str, missing))}")
        if not extra_red and not missing:
            print("  exact match")
        return 1
    print("\nALL PASS -- every message zerobas emits matches the reference "
          "verbatim, and there are no named holes left.")
    return 0


def run_relock(*, omsx: str | None = None) -> int:
    """Re-measure both references and DIFF against the embedded REF_TEXT.

    The lock has to be falsifiable. Without this, REF_TEXT is a constant nobody
    can re-derive -- indistinguishable from a guess that happened to be written
    down confidently.
    """
    codes = MAIN_CODES + DISK_CODES
    live = {s: measure(s, codes, omsx=omsx) for s in REF_SIDES}
    bad = []
    for n in codes:
        vg, cf = head(live["vg8020"].get(n)), head(live["cf3300"].get(n))
        want = REF_TEXT.get(n)
        oracle = cf if n in CF_ONLY_CODES else vg
        if n not in CF_ONLY_CODES and vg != cf:
            bad.append(f"  code {n}: references DISAGREE vg={show(vg)} cf={show(cf)}")
        elif oracle != want:
            bad.append(f"  code {n}: locked {want!r}, machine says {show(oracle)}")
    print()
    if bad:
        print("RELOCK MISMATCH:")
        for b in bad:
            print(b)
        return 1
    print(f"relock OK -- all {len(codes)} locked values reproduce on the machines")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__.split("\n")[0],
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sides", default="vg8020,cf3300",
                    help="comma-separated: vg8020,cf3300,zb (default both refs)")
    ap.add_argument("--walk", default="main,disk",
                    help="comma-separated: main (1..26), disk (50..64), "
                         "extra (the non-ERROR-n messages), subx (D-MSGSUB's "
                         "abort-path rows)")
    ap.add_argument("--omsx", default=None)
    ap.add_argument("--boot-per-case", action="store_true",
                    help="isolation escape hatch: one boot per code")
    ap.add_argument("--gate", action="store_true",
                    help="assert zb == the locked reference text (D-MSGEXACT)")
    ap.add_argument("--relock", action="store_true",
                    help="re-measure both references and diff against REF_TEXT")
    args = ap.parse_args()

    if args.gate:
        return run_gate(omsx=args.omsx, with_verify="verify" in args.walk.split(","))
    if args.relock:
        return run_relock(omsx=args.omsx)

    sides = [s for s in args.sides.split(",") if s]
    walks = [w for w in args.walk.split(",") if w]
    for s in sides:
        if s not in SIDES:
            print(f"unknown side {s!r}", file=sys.stderr)
            return 2

    codes: list[int] = []
    if "main" in walks:
        codes += MAIN_CODES
    if "disk" in walks:
        codes += DISK_CODES
    want_extra = "extra" in walks
    want_subx = "subx" in walks
    want_verify = "verify" in walks
    if want_verify:
        print(f"# measuring Verify error on {VERIFY_MACHINE} (cassette rig) ...",
              file=sys.stderr, flush=True)
        vscr = measure_verify(omsx=args.omsx)
        print()
        print(f"VERIFY ({VERIFY_MACHINE}, single-reference -- see module notes)")
        print("  screen: " + show(vscr))
        print()
        if not codes and not want_extra and not want_subx:
            return 0
    if not codes and not want_extra and not want_subx:
        print("no walk selected", file=sys.stderr)
        return 2

    readings: dict[str, dict[int, str | None]] = {}
    extras: dict[str, dict[str, str | None]] = {}
    subxs: dict[str, dict[str, str | None]] = {}
    for s in sides:
        if codes:
            print(f"# measuring {s} ({SIDES[s]['machine']}) over {len(codes)} codes ...",
                  file=sys.stderr, flush=True)
            readings[s] = measure(s, codes, omsx=args.omsx,
                                  boot_per_case=args.boot_per_case)
        else:
            readings[s] = {}
        if want_extra:
            print(f"# measuring {s} extra battery ({len(EXTRA)} cases, "
                  f"boot-per-case) ...", file=sys.stderr, flush=True)
            extras[s] = measure_extra(s, omsx=args.omsx)
        if want_subx:
            print(f"# measuring {s} SUBX battery (boot-per-case) ...",
                  file=sys.stderr, flush=True)
            subxs[s] = measure_subx(s, omsx=args.omsx)

    problems = []
    if "main" in walks:
        for s in sides:
            problems += selfcheck(readings[s], s)

    print()
    if codes:
        print("ERR | " + " | ".join(s.ljust(28) for s in sides))
        print("----+-" + "-+-".join("-" * 28 for _ in sides))
        for n in codes:
            cells = [show(readings[s].get(n)).ljust(28) for s in sides]
            print(f"{n:3d} | " + " | ".join(cells))
        print()
    if want_extra:
        print("EXTRA   | " + " | ".join(s.ljust(28) for s in sides))
        print("--------+-" + "-+-".join("-" * 28 for _ in sides))
        for label, _, _, _ in EXTRA:
            cells = [show(extras[s].get(label)).ljust(28) for s in sides]
            print(f"{label:7s} | " + " | ".join(cells))
        print(f"{'verify':7s} | " + " | ".join(
            "<not-measured>".ljust(28) for _ in sides))
        print()
    if want_subx:
        print("SUBX     | " + " | ".join(s.ljust(34) for s in sides))
        print("---------+-" + "-+-".join("-" * 34 for _ in sides))
        for label, _, _, needs_disk in SUBX:
            cells = []
            for s in sides:
                # ⚠️ THREE sentinels here, not two: a row this side never RAN
                # (no disk) must not read as `<none>` ("the machine declined").
                if needs_disk and s not in SUBX_DISK_SIDES:
                    cells.append("<skipped:no-disk>".ljust(34))
                else:
                    cells.append(show(subxs[s].get(label)).ljust(34))
            print(f"{label:8s} | " + " | ".join(cells))
        print()

    # Agreement summary across the two references only -- the whole point of a
    # two-reference lock is that a rule BOTH show is a property of MSX-BASIC.
    refs = [s for s in sides if s in REF_SIDES]
    if len(refs) == 2:
        a, b = refs
        same = [n for n in codes if readings[a].get(n) == readings[b].get(n)]
        diff = [n for n in codes if readings[a].get(n) != readings[b].get(n)]
        print(f"references agree on {len(same)}/{len(codes)} codes")
        if diff:
            print(f"references DIFFER on: {', '.join(str(n) for n in diff)}")

    if problems:
        print()
        for p in problems:
            print("!! " + p)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
