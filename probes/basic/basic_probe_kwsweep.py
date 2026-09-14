#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Keyword-completeness SWEEP — the MSX1 BASIC reserved-word denominator.

WHY THIS EXISTS
===============
zerobas has twice discovered a missing keyword *by accident*, and both had the
same silent shape — the word parses as an ordinary VARIABLE, so nothing errors
and the program just computes the wrong answer:

  * `TIME`  — found as collateral during the T3 KEY slice (20e04b4). `TIME`
    parses as the variable `TI`, reads 0 forever, and `IF TIME-T<400 GOTO`
    becomes an infinite loop.
  * `TAB(`  — found 2026-07-26 while auditing coverage. Worse: it was recorded
    as "already faithful (NO work)" in docs/spec-basic-df2-2-intarg-coercion.md
    §1.2 because `PRINT TAB(99999)` raises ERR 6 on BOTH sides. It does so for
    the WRONG REASON — zerobas has no `TAB(`, so `TAB` is an ARRAY and the
    subscript bound-check produces the same error code. The probe agreed; the
    feature is absent.

This probe closes that discovery channel by measuring the WHOLE reserved-word
set at once, so "complete MSX1 BASIC" finally has an honest denominator.

TWO LAYERS, BECAUSE ONE IS NOT ENOUGH
=====================================
The `INTERVAL` retraction (60e0ab6) is the standing lesson: a crunch probe
answers a TOKENISATION question, not a SUPPORT question. `INTERVAL` is absent
from every MSX1 keyword table — it is not a keyword at all, it is the
reserved-word compound `INT`+"ER"+`VAL` — and it works perfectly on the
VG-8020. "Absent from the keyword table" != "absent from the language."

The `TAB(` case is the mirror-image trap: identical OBSERVED BEHAVIOUR on one
probe, for structurally different reasons.

So every word is measured twice, and the two layers are reported separately:

  Layer 1 CRUNCH  — store `1 <body>` (tokenised into the program area, never
                    executed) and diff the token bytes ref vs zerobas. Reuses
                    basic_probe_crunch's stored-line capture wholesale.
  Layer 2 SUPPORT — EXECUTE a usage chosen so that "parses as a variable/array"
                    yields a VISIBLY DIFFERENT answer than real support, then
                    compare the OUTCOME CLASS (value vs which error) rather than
                    raw text — zerobas's error wording is lowercase by design
                    (a documented divergence), so a raw text diff would flag
                    every case and classify nothing.

Layer 2 is the load-bearing one. Layer 1 alone would have mis-called both
`INTERVAL` (absent token, works) and `TAB(` (present-looking, absent feature).

READING THE VERDICT
===================
  SUPPORTED    both sides produce the same outcome class and the same text
  DIVERGENT    both sides run it, but the answers differ  <- a faithfulness bug
  MISSING      the reference runs it, zerobas errors       <- a coverage gap
  SILENT-GAP   BOTH sides "succeed" but zerobas's answer betrays a
               variable/array parse (the TIME / TAB( shape)  <- the worst kind
  EXTRA        zerobas runs it, the reference errors
  SKIPPED      not safely executable in a batch (see SKIP_EXEC) — crunch only

Clean-room: this only *compares observed outputs*. No disassembly; the reference
ROM is a black box. The candidate word list is a generator only — every verdict
comes from measurement. See the clean-room firewall (CONTRIBUTING.md).

USAGE
    python3 probes/basic/basic_probe_kwsweep.py --zb-machine C-BIOS_MSX1_EU_REPACK_DISK
    ... --only tab,spc,locate      # a subset, by word key
    ... --layer crunch|support     # one layer only
    ... --boot-per-case            # isolation escape hatch
"""
from __future__ import annotations

# --- zerobas probes: locate shared infra (probes/lib) + sibling probes ---
import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))  # sibling probes
_sys.path.insert(0, _os.path.join(
    _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "lib"))  # shared infra

import argparse
import atexit
import hashlib
import shutil
import subprocess
import tempfile

_sys.path.insert(0, _os.path.join(
    _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "disk"))  # bas_tokenise

import cas_decode  # reads the recording back -- the NEEDS-BLANKTAPE: capture
import cas_encode  # the clean-room .cas encoder -- the NEEDS-TAPE: fixture
from bas_tokenise import make_multiline_program
import omsx_repl  # typing-free KEYBUF-injection REPL driver
import probe_report  # 🔴 D-KWFOOT: I3 -- every exit path that prints
                      # rows ends with a POSITIVE statement of what it measured

MACHINE = "Philips_VG_8020"
# A DISK-EQUIPPED reference, for the rows whose verbs live in Disk BASIC.
#
# This exists because the first full run tripped its own control group: `mki`
# (MKI$, which zerobas implements correctly) came back as the reference raising
# `Illegal function call` while zerobas printed the right answer. The language was
# never the asymmetry — the MACHINES were. The default reference is a DISKLESS
# VG-8020, while the zerobas side is C-BIOS_MSX1_EU_REPACK_**DISK**, so every
# MK$/CV/Disk-BASIC row was comparing "no disk ROM" against "disk ROM" and
# attributing the difference to zerobas. Rows tagged NEEDS-DISK: get their
# reference capture from this machine instead.
#
# 🟢 STATUS 2026-09-12 (D-KWDISK): THE ORACLE READS, AND THE NOTE THAT SAID IT
# DOES NOT IS RETRACTED HERE. The 2026-07-26 filing — "does NOT yet yield a
# readable SCREEN-0 capture ... reports NO-ORACLE rather than a verdict" — was
# already falsified by D-KWORACLE's `MACH_BOOT` / `MACH_RESET_PRE` fix below (a
# 14 s boot and a `SCREEN 0`), which is what `mki` `mks` `mkd` `cvs` `cvd` `cvi`
# now return real verdicts through. The sentence survived the fix that killed it
# [[a-fix-falsifies-the-justification-beside-it]]; NO-ORACLE is still the answer
# when the capture really is unreadable, but that is now an exception, not the
# expected state.
DISK_MACHINE = "National_CF-3300"

# 🔴 AND THE SECOND HALF OF THE SAME BLOCKER: A DISK-EQUIPPED MACHINE WITH NO
# DISK IN IT. Until 2026-09-12 this file named neither `diska` nor an image, so
# every Disk-BASIC row was measured on two machines with an EMPTY drive — which
# is why `DSKF(0)` read 0 and got filed as "reads 0, exactly what a stub reads".
# It reads 707 with the image in. The fixture was never missing: `disk/test720.dsk`
# (`make test-dsk`, tools/make_test_dsk.py) carries TEST.BIN, HI.TXT, PROG.BIN,
# PROG.BAS and PROG2.BAS with known contents, and `ramfree-acceptance` has mounted
# it for months [[a-justification-parenthesis-is-an-unrun-claim]].
# ⚠️ A PRIVATE COPY PER RUN, NEVER THE ORIGINAL: `kill` deletes a file, `copy`,
# `save`, `bsave` and `close` add one, and `dsko` rewrites the first byte of the
# root directory. The image is generated, so `make kwsweep` must declare
# `$(DISK_TEST_DSK)` — `diskdep-check` refuses a target that names it without.
DISK_TEST_DSK = _os.path.join(
    _os.path.dirname(_os.path.dirname(_os.path.dirname(
        _os.path.abspath(__file__)))), "disk", "test720.dsk")

# 🔴 THE DISK ROWS NEED TIME, AND THE FAILURE LOOKS EXACTLY LIKE A REFUSAL.
# At the shared default (`cap_gap` 2.5) every WRITING row came back BLANK on the
# CF-3300 — no marker, no error, no prompt — which reads as "the reference
# declines this verb" and would have published five divergences that are pure
# apparatus. The capture was simply firing before a real FAT write finished.
# Measured: at `cap_gap` 8 the reference still blanks on all five; at 12/3.5 both
# machines answer; 20/5 is the proven setting and the cost is EMULATED time, not
# wall time. Applied to the NEEDS-DISK group only [[apparatus-is-part-of-the-measurement]].
DISK_TIMING = dict(step=5.0, cap_gap=20.0, timeout=900.0)


def _disk_image() -> str:
    """A writable private copy of the test image, mounted for ONE machine's run.

    Each side gets its own, so a row that writes on zerobas cannot change what
    the reference reads two rows later -- the two runs must see the same disk
    evolve the same way, which they only do if neither can touch the other's."""
    fh = tempfile.NamedTemporaryFile(suffix=".dsk", delete=False)
    fh.close()
    shutil.copy(DISK_TEST_DSK, fh.name)
    if not _DISK_TEMPS:
        atexit.register(_drop_disk_images)
    _DISK_TEMPS.append(fh.name)
    return fh.name


# Tape rows are the slowest in the sweep; see _rig_kwargs for why these figures
# and not the disk ones [[apparatus-is-part-of-the-measurement]].
TAPE_TIMING = dict(step=5.0, cap_gap=90.0, timeout=1200.0)
TAPE_MARK = "\x00TAPE\x00"
TAPE_NAME = "ZQ"
TAPE_PROGRAM = make_multiline_program([(10, 'PRINT"[Z9]"')], 0x8001)


def _tape_fixture() -> str:
    """A PREPARED tape for a reading row: a clean-room `.cas` carrying one known
    program under a known name, fresh per machine like the disk images.

    🎯 The program prints a MARKER, so a row can do more than reach `Ok`: the
    reference announces `Found:ZQ` on the screen as it reads, which is the
    machine's own witness that the verb did something and not merely parsed."""
    fh = tempfile.NamedTemporaryFile(suffix=".cas", delete=False)
    fh.write(cas_encode.build_cas_basic(TAPE_NAME, TAPE_PROGRAM))
    fh.close()
    if not _TAPE_TEMPS:
        atexit.register(_drop_tape_temps)
    _TAPE_TEMPS.append(fh.name)
    return fh.name


def _tape_blank() -> str:
    """A path for a BLANK recording tape. openMSX's `cassetteplayer new` creates
    the file itself, so this hands back a name that does NOT exist yet -- for this
    rig the fixture IS the absence."""
    fh = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    fh.close()
    _os.unlink(fh.name)
    if not _TAPE_TEMPS:
        atexit.register(_drop_tape_temps)
    _TAPE_TEMPS.append(fh.name)
    return fh.name


def _tape_readback(path: str) -> str:
    """The BYTES on the recorded tape, as one hex string -- this rig's reading.

    🔴 IT IS DECODED IN PYTHON, NOT HEXED THROUGH Tcl like the printer log: a
    recording is ~580 KB, and the `screen_printer` capture would push more than a
    megabyte of hex per case through the control socket. The probe created the
    file, so it can simply read it."""
    # 🔴 AN ABSENT TAPE IS AN APPARATUS FAILURE, NOT A READING, and it must not be
    # allowed to look like one: the first cut RETURNED "<no tape written>" and the
    # row scored SUPPORTED because both sides returned it -- two missing fixtures
    # agreeing with each other. (The cause was this rig recovering the path by
    # slicing its own Tcl string at the wrong offset.)
    if not _os.path.exists(path):
        raise SystemExit(
            "kwsweep: APPARATUS FAILURE -- the NEEDS-BLANKTAPE: rig recorded no "
            f"tape at {path}. `cassetteplayer new` did not create it, so nothing "
            "was measured; do not read the row's verdict.")
    data, _info = cas_decode.decode_file(path, stop_bits=1)
    if not data:
        return "<tape unreadable>"
    return " ".join("%02X" % c for c in data)


def _drop_tape_temps() -> None:
    """Same `atexit` reasoning as the disk images and the printer logs."""
    while _TAPE_TEMPS:
        try:
            _os.unlink(_TAPE_TEMPS.pop())
        except OSError:
            pass


_TAPE_TEMPS: list[str] = []


# 🔴 THE PRINTER IS A RIG TOO, AND ITS ABSENCE IS A HANG, NOT A BLANK.
# Measured (scratchpad/kwdrain_lptchk.py): with a printer PLUGGED, `LPOS(0)`
# reads 0 at rest, 3 after `LPRINT"ABC";` and 7 after seven bytes, IDENTICALLY on
# zerobas and the VG-8020. With NOTHING on the port the same rows produce no
# output at all -- the LSTOUT hazard the TODO warned about is real, and it is why
# the plug is load-bearing rather than decoration.
# 🎯 AND THE LOG IS NOT NEEDED FOR THESE TWO. `LPOS` is the head's COLUMN and it
# reaches the SCREEN, so the filed blocker ("a reader for the PRINTER LOG -- the
# output never reaches the screen") is true of the printed TEXT and not of these
# rows. `LLIST` and `LFILES` DO need the log (their subject is the text), and the
# slice that adds a `screen_printer` capture group is the one to take them.
def _printer_log() -> str:
    """A private printer log file for one machine's run."""
    fh = tempfile.NamedTemporaryFile(suffix=".prn", delete=False)
    fh.close()
    if not _RIG_TEMPS:
        atexit.register(_drop_rig_temps)
    _RIG_TEMPS.append(fh.name)
    return fh.name


def _printer_plug(path: str) -> tuple[str, ...]:
    """The openMSX prologue that puts a logging printer on the port. For a
    `NEEDS-PRINTER:` row the log is never READ -- only its existence keeps the
    port ready, so `LPRINT` cannot block. A `NEEDS-LOG:` row reads it."""
    return (f"set printerlogfilename {{{path}}}", "plug printerport logger")


# 🟢 D-KWLOG (2026-09-13): `NEEDS-LOG:` IS THE THIRD RIG, and it is a CAPTURE
# rather than a device -- it implies the printer plug and then READS the log
# instead of merely keeping the port ready. `LLIST` is why: measured, the program
# STOPS at it on both machines so nothing reaches the screen, direct mode has no
# program to list, and its printed bytes are IDENTICAL on both. The verb is fine;
# what it lacked was a path from the verb to a reading
# (scratchpad/kwdrain_llistchk.out).
# 🟢 D-KWTAPE2: `NEEDS-TAPE:` mounts a PREPARED tape carrying a known program.
# A WRITING row would need the opposite fixture -- a blank tape openMSX creates --
# and no row needs one yet, because CSAVE turns out to have no screen-observable
# consequence at all (see the item): that rig arrives with the row that uses it.
_RIG_TAGS = {"NEEDS-DISK:": "disk", "NEEDS-PRINTER:": "printer",
             "NEEDS-LOG:": "log", "NEEDS-TAPE:": "tape",
             "NEEDS-BLANKTAPE:": "tapew"}


# A flag tag is a prefix tag that selects no apparatus -- it changes how the
# SCREEN is read, not what is plugged in.
# 🟢 D-KWT3 (2026-09-13, Joost: "add more tests for each keyword proving the
# tier"): `PROVES-T3:` is a row DECLARING WHAT IT PROVES, not what it needs.
# tier_table's own source says the reached column "becomes a measurement only when
# gate rows declare their keyword" -- this is that declaration, made by a row we
# WROTE rather than inferred from a suite we hope is load-bearing.
# 🎚️ TIER 3 is "handles the most common error situations", and the legend's own
# test is the filter: *would a 1985 magazine listing plausibly hit this?* -- Type
# mismatch, Illegal function call on a bad argument, Subscript out of range,
# Division by zero, Out of DATA, File not found. Not nesting depth 11; that is
# TIER 5 and does not belong on one of these rows.
_FLAG_TAGS = ("NOFURN:", "PROVES-T3:")


def _row_prefix_tags(note: str) -> tuple[str, ...]:
    """The prefix run of tags on a note, rig and flag tags in any order.

    🔴 THIS EXISTS BECAUSE `NOFURN:` WAS TESTED WITH `startswith` and the tape
    rows are the first to need a rig tag AND a flag: `NEEDS-TAPE: NOFURN: ...`
    silently lost the flag, and the row it lost it on diverged only in the
    reference's function-key line -- a furniture difference reported as a defect."""
    out = []
    for tok in note.split():
        if tok in _RIG_TAGS or tok in _FLAG_TAGS:
            out.append(tok)
        else:
            break
    return tuple(out)


def _row_rigs(note: str) -> tuple[str, ...]:
    """Every rig a row needs, as a stable tuple (the capture group key).

    🟢 GENERALISED BY THE ROW THAT NEEDED IT, not ahead of it: `lfiles` walks a
    DISK and prints to a PRINTER, and the single-tag form could not express it.
    The tags are a PREFIX RUN of the note -- the first token that is not a known
    tag is where the prose starts -- so a note reads
    `"NEEDS-DISK: " "NEEDS-PRINTER: " "why this row..."`."""
    return tuple(_RIG_TAGS[t] for t in _row_prefix_tags(note) if t in _RIG_TAGS)


def _rig_kwargs(rigs: tuple[str, ...]) -> dict:
    """The run_cases kwargs those rigs need -- a FRESH image and a FRESH log per
    call, so two machines never share one.

    🔴 `log` FORCES BOOT-PER-CASE, and that is not a preference. openMSX holds the
    log open and never truncates it, so BATCHED every case captures the whole log
    and each row would read its predecessors' output as its own -- D-BATCH2
    measured exactly that on `basic_probe_lptverb.py` and both modes still exited
    0, so no exit status can catch it. `batch` is returned here as a kwarg and
    popped by `capture()`."""
    kw: dict = {}
    if "disk" in rigs:
        kw.update(DISK_TIMING)
        kw["diska"] = _disk_image()
    if "printer" in rigs or "log" in rigs:
        path = _printer_log()
        kw["prologue"] = _printer_plug(path)
        if "log" in rigs:
            kw["capture"] = ("screen_printer", path)
            kw["batch"] = False
    if "tapew" in rigs:
        # 🔴 CSAVE'S OUTPUT NEVER REACHES THE SCREEN -- it reaches the TAPE, which
        # is the same shape `LLIST` had and the same answer: read the artefact,
        # not the display. Boot-per-case for the same reason the printer log needs
        # it, and with a bonus this rig gets for free: `cassetteplayer new`
        # re-creates the file each boot, so every case records onto a FRESH tape
        # instead of appending to its predecessors'.
        kw.update(TAPE_TIMING)
        path = _tape_blank()
        kw["prologue"] = (f"cassetteplayer new {{{path}}}",)
        kw["batch"] = False
        kw["_tape_path"] = path
    if "tape" in rigs:
        # Both tape rigs are SLOW by construction: a 16000-cycle leader is ~7 s of
        # emulated time before a single byte moves, and a search reads the whole
        # tape. The disk timings are nowhere near enough, and at the default
        # cap_gap both rows come back BLANK -- which reads as a refusal.
        kw.update(TAPE_TIMING)
        kw["cassette"] = _tape_fixture()
    return kw


def _drop_rig_temps() -> None:
    """Remove every private printer log, on the same `atexit` reasoning as the
    disk images."""
    while _RIG_TEMPS:
        try:
            _os.unlink(_RIG_TEMPS.pop())
        except OSError:
            pass


_RIG_TEMPS: list[str] = []


def _drop_disk_images() -> None:
    """Remove every private copy. `atexit`, not a `finally`: a run that dies
    inside the emulator must not leave 720 KB images behind, and this file has
    several early `return`s between the first mount and the report."""
    while _DISK_TEMPS:
        try:
            _os.unlink(_DISK_TEMPS.pop())
        except OSError:
            pass


_DISK_TEMPS: list[str] = []
TXTTAB = 0xF676   # sysvar: 2-byte LE pointer to the BASIC text base (both machines)

# Widest direct-mode exec line whose prompt echo still fits ONE SCREEN-0 row, so
# omsx_repl.screen_tail can find it. Anything wider must use mode="stored" (whose
# echoed command is the short "RUN"). Enforced at startup — see main().
MAX_DIRECT_ECHO = 38

# The MSX1 BASIC reserved-word set. CANDIDATE GENERATOR ONLY — this list decides
# what gets measured, never what the answer is. Sourced from the published
# keyword/token tables (MSX Technical Data Book; MSX2 Technical Handbook Table
# 2.20 — both allowed-sources.md tier B), which is the same provenance the
# existing kwtable.inc token locks already cite.
#
# Each row: (key, crunch_body, exec_line, exec_mode, note)
#   crunch_body — stored as `1 <body>`; never executed
#   exec_line   — the Layer-2 usage; None => crunch-only (also list in SKIP_EXEC)
#   exec_mode   — "direct" (typed at the prompt) or "stored" (numbered + RUN)
#
# The exec_line for a SUSPECTED-MISSING word is designed against the failure mode
# in this file's header: it must distinguish real support from a variable/array
# parse. `PRINT TAB(99999)` is the counter-example of how NOT to write one.

SWEEP: list[tuple[str, str, str | None, str, str]] = [

    # ---------------------------------------------------------------- controls
    # Known-shipped words. They are the CONTROL GROUP: if one of these comes back
    # anything but SUPPORTED, the apparatus is lying and no other row is
    # trustworthy. (The T3 KEY lesson: distrust a baseline that cannot produce a
    # non-zero answer.)
    ("abs",     "a=abs(-5)",          'PRINT"[";ABS(-5);"]"',            "direct", "control"),
    ("int",     "a=int(1.7)",         'PRINT"[";INT(1.7);"]"',           "direct", "control"),
    ("len",     'a=len("ab")',        'PRINT"[";LEN("ab");"]"',          "direct", "control"),
    ("chr",     "a$=chr$(65)",        'PRINT"[";CHR$(65);"]"',           "direct", "control"),
    ("mid",     'a$=mid$("hi",1,1)',  'PRINT"[";MID$("hi",2,1);"]"',     "direct", "control"),
    ("instr",   'a=instr("ab","b")',  'PRINT"[";INSTR("ab","b");"]"',    "direct", "control"),
    # 🌾 D-KWBREADTH batch 9: the row above uses the TWO-argument form, and the only
    # three-argument coverage is `instr_t3`, which passes an INVALID start of 0. The
    # VALID start form is untested: `INSTR(2,"ABA","A")` must skip the first "A" and
    # find the one at 3, where a start argument that is parsed and discarded says 1.
    ("instr_b", 'a=instr(2,"aba","a")', 'PRINT"[";INSTR(2,"ABA","A");"]"',  "direct",
     "D-KWDRAIN: the 3-argument START form -- 3, not 1. A start that parses and is "
     "then ignored finds the FIRST A and reads 1."),
    ("hex",     "a$=hex$(255)",       'PRINT"[";HEX$(255);"]"',          "direct", "control"),
    ("sqr",     "a=sqr(9)",           'PRINT"[";SQR(9);"]"',             "direct", "control"),
    ("peek",    "a=peek(0)",          'PRINT"[";PEEK(0)>=0;"]"',         "direct", "control"),
    ("varptr",  "a=varptr(b)",        'B=1:PRINT"[";VARPTR(B)>0;"]"',    "direct", "control"),
    # 🌾 D-KWBREADTH batch 8: `VARPTR(B)>0` is a half-plane. The ABSOLUTE address is
    # machine-dependent (RAM layouts differ), but a DELTA cancels the base: the
    # element STRIDE of a numeric array is 8 on all three machines (MSX defaults to
    # DOUBLE), measured in scratchpad/boolaxis_probe.py before this row was written.
    # 🔴 AND `A=0:B=0` FIRST IS LOAD-BEARING, WHICH THE FIRST VERSION LEARNED THE
    # HARD WAY. MSX stores SIMPLE variables BEFORE arrays, so creating B after
    # taking A=VARPTR(Z(1)) MOVES THE ARRAY between the two reads: the row read
    # `[-3 ]` instead of `[ 8 ]`, agreed on both machines, and was scored SUPPORTED
    # with a note claiming a stride of 8 that its own reading contradicted. The
    # SPLIT was mine -- forced by the 34-char body limit -- so the apparatus changed
    # the thing it measured [[apparatus-is-part-of-the-measurement]]. Declaring both
    # variables up front pins the array in place.
    ("varptr_b", 'a=varptr(z(1))',
     'A=0:B=0:DIM Z(4):A=VARPTR(Z(1)):B=VARPTR(Z(0)):PRINT"[";A-B;"]"',       "stored",
     "D-KWDRAIN: VARPTR's arithmetic, not its non-zero-ness -- the array element "
     "stride, 8 (MSX defaults to DOUBLE). A delta, so the machine-dependent base "
     "cancels; A and B are created BEFORE the DIM so the array cannot move."),
    ("stick",   "a=stick(0)",         'PRINT"[";STICK(0);"]"',           "direct", "control"),
    ("erase",   "erase a",            'DIM Q(2):ERASE Q:PRINT"[ok]"',    "direct", "control"),
    ("swapctl", "a=1",                'A=1:PRINT"[";A;"]"',              "direct", "control (bare assign)"),

    # ------------------------------------------------- D-KWDRAIN coverage rows
    # 🎯 JOOST'S STANDING ORDER (2026-09-11): *"get rid of the 'no known gap'
    # items in the table, so we have more known tier-ed work."* A "no known gap"
    # keyword is NOT one that is fine -- it is one nobody has attributed evidence
    # to, and with TIER 2 and TIER 3 empty the binding constraint stopped being
    # "fix the next defect" and became "find out what is actually broken".
    # These rows carry the CHEAPEST-CONTEXT verbs: pure functions and operators,
    # one differential each, no device and no file state. Each exec line prints a
    # value the reference must match, so the row SCORES rather than merely
    # exercising [[exercised-is-not-verified]].
    # 🔴 NOT "control": a control that comes back unsupported means the APPARATUS
    # is lying and voids the run. These are the words under test, so an
    # unsupported one here has to read as a FINDING instead.
    # ⚠️ Fractional rows (ATN, EXP, CDBL(1)/3) are deliberate -- formatting and
    # precision are exactly where a clean-room mathpack diverges, and a row that
    # only ever prints 0 or 1 cannot see it.
    ("asc",     'a=asc("A")',         'PRINT"[";ASC("A");"]"',         "direct", "D-KWDRAIN"),
    ("cint",    'a=cint(1.7)',        'PRINT"[";CINT(1.7);"]"',        "direct", "D-KWDRAIN"),
    ("cdbl",    'a=cdbl(1)',          'PRINT"[";CDBL(1)/3;"]"',        "direct", "D-KWDRAIN"),
    ("csng",    'a=csng(1.5)',        'PRINT"[";CSNG(1.5);"]"',        "direct", "D-KWDRAIN"),
    ("fix",     'a=fix(-1.7)',        'PRINT"[";FIX(-1.7);"]"',        "direct", "D-KWDRAIN"),
    ("sgn",     'a=sgn(-3)',          'PRINT"[";SGN(-3);"]"',          "direct", "D-KWDRAIN"),
    ("sin",     'a=sin(0)',           'PRINT"[";SIN(0);"]"',           "direct", "D-KWDRAIN"),
    ("cos",     'a=cos(0)',           'PRINT"[";COS(0);"]"',           "direct", "D-KWDRAIN"),
    ("tan",     'a=tan(0)',           'PRINT"[";TAN(0);"]"',           "direct", "D-KWDRAIN"),
    ("atn",     'a=atn(1)',           'PRINT"[";INT(ATN(1)*1000);"]"', "direct", "D-KWDRAIN"),
    ("exp",     'a=exp(1)',           'PRINT"[";INT(EXP(1)*1000);"]"', "direct", "D-KWDRAIN"),
    ("log",     'a=log(1)',           'PRINT"[";LOG(1);"]"',           "direct", "D-KWDRAIN"),
    ("mod",     'a=7 mod 3',          'PRINT"[";7 MOD 3;"]"',          "direct", "D-KWDRAIN"),
    ("notop",   'a=not 0',            'PRINT"[";NOT 0;"]"',            "direct", "D-KWDRAIN"),
    ("andop",   'a=5 and 3',          'PRINT"[";5 AND 3;"]"',          "direct", "D-KWDRAIN"),
    ("orop",    'a=5 or 3',           'PRINT"[";5 OR 3;"]"',           "direct", "D-KWDRAIN"),
    ("xorop",   'a=5 xor 3',          'PRINT"[";5 XOR 3;"]"',          "direct", "D-KWDRAIN"),
    ("oct",     'a$=oct$(8)',         'PRINT"[";OCT$(8);"]"',          "direct", "D-KWDRAIN"),
    ("left",    'a$=left$("abc",2)',  'PRINT"[";LEFT$("abc",2);"]"',   "direct", "D-KWDRAIN"),
    ("right",   'a$=right$("abc",2)', 'PRINT"[";RIGHT$("abc",2);"]"',  "direct", "D-KWDRAIN"),
    ("str",     'a$=str$(5)',         'PRINT"[";STR$(5);"]"',          "direct", "D-KWDRAIN"),
    ("stringf", 'a$=string$(3,"x")',  'PRINT"[";STRING$(3,"x");"]"',   "direct", "D-KWDRAIN"),
    ("space",   'a$=space$(3)',       'PRINT"[";LEN(SPACE$(3));"]"',   "direct", "D-KWDRAIN"),
    # 🔴 CSRLIN GETS A SECOND ROW, AND THE FIRST ONE IS WHY. The original
    # `csrlin` row is scored WEAK, and `tools/tier_table.py` EXCLUDES weak rows
    # from evidence -- so CSRLIN's DIVERGENT verdict (ref `[ 4 ]` vs zb `[ 3 ]`)
    # counts as nothing and the keyword reads as "no known gap", i.e. a measured
    # divergence that the attribution table cannot see
    # [[an-unnamed-outcome-reads-as-no-outcome]]. That divergence is an ARTIFACT
    # of absolute cursor geometry against the echoed prompt, not a defect: the
    # weak row's own note records CSRLIN measured CORRECT on 2026-09-07
    # (D-WAITGAP -- LOCATE 0,5 -> 5, 0,10 -> 10) and all three sides answering 2
    # to CLS:PRINT:PRINT. So this row reads the DELTA across two PRINTs, which is
    # what the three machines agree on, and which a stub still fails: an absent
    # CSRLIN parses as a variable and gives 0-0 = 0, not 2.
    ("csrlind", 'a=csrlin',           'A=CSRLIN:PRINT:PRINT"[";CSRLIN-A;"]"', "direct", "D-KWDRAIN"),
    ("let",     'let a=5',            'LET A=5:PRINT"[";A;"]"',        "direct", "D-KWDRAIN"),
    ("rem",     'rem x',              'PRINT"[";1;"]":REM z',          "direct", "D-KWDRAIN"),

    # ------------------------------------------------ D-KWDRAIN batch 2 (2026-09-12)
    # 🔴 THE SYNTAX PARTICLES NEEDED A TRICK, AND IT IS LEGITIMATE. `tier_table.py`
    # credits a row to the FIRST keyword token in its CRUNCH body, and THEN / ELSE /
    # TO / STEP / OFF / USING can never be first in valid BASIC -- so on the obvious
    # spelling they could never be attributed at all, however well they work. The
    # crunch body is CRUNCHED AND NEVER EXECUTED (see the header contract), so these
    # rows put the particle first in the crunch -- which is exactly what Layer 1 is
    # for, checking that the word tokenises -- while the exec line drives it in real
    # syntax. `then a=1` crunches; `IF 2>1 THEN PRINT"[3]"` is what runs.
    # ⚠️ RND IS SCORED FOR EXISTENCE AND RANGE, NOT FOR ITS SEQUENCE. `RND(1)<1` is
    # true on any conforming implementation and false on a stub (an absent RND parses
    # as a variable, making `RND(1)` a subscript). Whether zerobas's PRNG SEQUENCE
    # matches the reference's is a separate question this row does not ask, and
    # filing it as answered here would be the "agrees for the wrong reason" trap.
    ("rnd",     'a=rnd(1)',           'PRINT"[";RND(1)<1;"]"',                "direct", "D-KWDRAIN"),
    # 🌾 D-KWBREADTH batch 8, AND IT ANSWERS THE QUESTION THE ROW ABOVE DECLINES.
    # That note says whether zerobas's PRNG SEQUENCE matches the reference's is "a
    # separate question this row does not ask". It is now MEASURED: `RND(negative)`
    # reseeds deterministically (A=RND(-1):B=RND(-1) gives A=B on all three) and the
    # value after the reseed is the SAME on all three -- INT(RND(-1)*10000) = 438 on
    # the VG-8020, the CF-3300 and zerobas (scratchpad/boolaxis_probe.py).
    ("rnd_b",   'a=rnd(-1)',
     'A=RND(-1):PRINT"[";INT(A*10000);"]"',                                   "stored",
     "D-KWDRAIN: the SEQUENCE, not the range -- `RND(1)<1` is true on any "
     "conforming implementation. After a negative reseed the value is 438 on both "
     "references and here, so the generator itself agrees."),
    ("cvi",      'a=cvi("ab")',        'PRINT"[";CVI(MKI$(7));"]"',              "direct",
     "NEEDS-DISK: " "absent => syntax error; real => 7. 🔴 TAGGED AFTER THE FACT: "
     "written untagged it came back EXTRA -- ref `Illegal function call` vs zb "
     "`[ 7 ]` -- which is EXACTLY the mis-attribution this file's header "
     "describes, a diskless VG-8020 measured against zerobas's disk-equipped "
     "build and the difference blamed on zerobas. The rest of the MK/CV family "
     "was already tagged; this row simply had not been."),
    ("using",   'using "##"',         'PRINT USING"##";7',                    "direct", "D-KWDRAIN"),
    # 🌾 D-KWBREADTH batch 4: the `using` row covers ONE format string, and `##`
    # is the one that needs no fraction, no rounding and no sign. `#.##` needs all
    # three -- 3.146 must round to 3.15, not truncate to 3.14.
    ("using_b", 'using "#.##"',
     'PRINT"[";:PRINT USING"#.##";3.146;:PRINT"]"',                      "stored",
     "D-KWDRAIN: the FRACTIONAL field, where `##` cannot reach -- placement of "
     "the point AND the rounding of the discarded digit"),
    ("then",    'then a=1',           'IF 2>1 THEN PRINT"[3]"',               "direct", "D-KWDRAIN"),
    ("elsekw",  'else a=1',           'IF 0 THEN PRINT 1 ELSE PRINT"[8]"',    "direct", "D-KWDRAIN"),
    ("tokw",    'to 5',               'FOR I=1 TO 3:NEXT:PRINT"[";I;"]"',     "direct", "D-KWDRAIN"),
    ("stepkw",  'step 2',             'FOR I=1TO5STEP2:NEXT:PRINT"[";I;"]"',  "direct", "D-KWDRAIN"),
    ("offkw",   'off',                'INTERVAL OFF:PRINT"[9]"',              "direct", "D-KWDRAIN"),
    ("ifkw",    'if 1 then a=2',      'IF 3>2 THEN PRINT"[4]"',               "direct", "D-KWDRAIN"),
    ("nextkw",  'next i',             'FOR I=1 TO 2:NEXT:PRINT"[";I;"]"',     "direct", "D-KWDRAIN"),
    ("clearkw", 'clear 100',          'CLEAR 100:PRINT"[5]"',                 "direct", "D-KWDRAIN"),
    # 🌾 D-KWBREADTH batch 5: `clearkw` prints a CONSTANT MARKER, so it scores that
    # the word RAN and nothing about what it DID. CLEAR's defining effect is that
    # it resets variables; `A=A+1` after it reads 1 only if A really went to 0.
    ("clear_b", 'clear',              'A=5:CLEAR:A=A+1:PRINT"[";A;"]"',        "direct",
     "D-KWDRAIN: CLEAR's EFFECT, not its existence -- `[ 1 ]` proves A was reset "
     "to 0; a CLEAR that did nothing leaves 6"),
    ("dimkw",   'dim a(2)',           'DIM D(2):D(1)=5:PRINT"[";D(1);"]"',    "direct", "D-KWDRAIN"),

    # ------------------------------------------------ D-KWDRAIN batch 3 (2026-09-12)
    # The raw-I/O and sound words. Every exec here is chosen to leave the SCREEN
    # ALONE: this sweep anchors its capture on the echoed command, and the `locate`
    # row above is the standing proof that a feature which moves or clears the
    # display destroys the probe's own anchor. So no CLS, no SCREEN, no COLOR and no
    # WIDTH in this batch -- those need their own handling, not a hopeful row.
    # ⚠️ THE WRITES ARE DELIBERATELY AIMED AT HARMLESS TARGETS: VRAM 0 is the glyph
    # for character 0, `OUT &HA0` selects a PSG register without writing one,
    # `SOUND 7,255` is the mixer with every channel OFF, `WAIT &HA9,0` masks to zero
    # so the condition is true immediately and cannot hang, and the POKE goes to
    # -8192 ($E000), inside zerobas's own RAM rather than the work area.
    # 🎯 EACH ONE READS BACK WHAT IT WROTE where it can (VPOKE/VPEEK, POKE/PEEK), so
    # a stub that silently accepts the statement still fails the row.
    ("beep",    'beep',               'BEEP:PRINT"[6]"',                      "direct", "D-KWDRAIN"),
    # 🌾 D-KWBREADTH batch 7: `beep` prints a CONSTANT MARKER, and BEEP's effect
    # turns out to be observable through the PSG after all (scratchpad/
    # beepobs_probe.py, all three machines): the MIXER at rest reads 184, a
    # `SOUND 7,255` leaves 191 ($BF, the write masked), and a BEEP after it puts
    # the mixer back to 184. So 184-here-vs-191-there is BEEP's own doing.
    # 🔴 THE FIRST RUN OF THAT PROBE COULD NOT SEE IT, because its control read
    # register 8 while the change was in register 7 -- A CONTROL AIMED AT THE WRONG
    # CELL EXCLUDES NOTHING, and 184 would have been read as "nothing happened".
    # ⚠️ And the row leaves the machine AS IT FOUND IT: 184 IS the at-rest value.
    ("beep_b",  'beep',
     'SOUND 7,255:BEEP:OUT&HA0,7:PRINT"[";INP(&HA2);"]"',                     "stored",
     "D-KWDRAIN: BEEP's EFFECT, not its existence -- it restores the PSG mixer, "
     "so this reads 184 where the same program without the BEEP reads 191"),
    ("sound",   'sound 7,255',        'SOUND 7,255:PRINT"[7]"',               "direct", "D-KWDRAIN"),
    # 🌾 D-KWBREADTH batch 6: `sound` writes PSG register 7 and prints a CONSTANT
    # MARKER, so it scores that the word ran and nothing about what landed. The PSG
    # HAS a readback path -- `OUT &HA0,<reg>` selects, `INP(&HA2)` reads -- so the
    # effect is observable after all. Register 0 (channel A fine tune) is used
    # rather than 7 because it is a plain 8-bit cell and because the MIXER is left
    # exactly as it was: nothing is made audible by this row.
    ("sound_b", 'sound 0,123',
     'SOUND 0,123:OUT&HA0,0:PRINT"[";INP(&HA2);"]"',                          "stored",
     "D-KWDRAIN: SOUND's EFFECT, not its existence -- the byte is read back out "
     "of the PSG. A SOUND that parsed and wrote nothing reads something else."),
    ("vpeek",   'a=vpeek(0)',         'VPOKE 0,7:PRINT"[";VPEEK(0);"]"',      "direct", "D-KWDRAIN"),
    ("vpoke",   'vpoke 0,1',          'VPOKE 0,9:PRINT"[";VPEEK(0);"]"',      "direct", "D-KWDRAIN"),
    ("vdpkw",   'a=vdp(1)',           'PRINT"[";VDP(1)>0;"]"',                "direct", "D-KWDRAIN"),
    # 🌾 D-KWBREADTH batch 8: a BOOLEAN reading scores only that a value falls in a
    # half-plane, never the VALUE. `VDP(1)>0` is -1 for anything non-zero, so every
    # wrong-but-non-zero register read passes it -- and the note beside the row
    # already says the number is 240 against a stub's 0, so the value was known and
    # simply not scored.
    ("vdp_b",   'a=vdp(1)',           'PRINT"[";VDP(1);"]"',                  "direct",
     "D-KWDRAIN: the VDP register's VALUE, not its non-zero-ness -- 240. The "
     "`vdpkw` row's `>0` passes on any wrong non-zero read."),
    # 🔴 `>0`, NOT `>=0`, AND THAT IS A FIX TO MY OWN ROW. The first cut asked
    # `INP(&HA8)>=0`, which an ABSENT INP passes too: the word would parse as an
    # undefined array, `INP(&HA8)` would be element 0, and `0>=0` is TRUE.
    # Measured (scratchpad/kwdrain_boolcheck.py): INP(&HA8) reads 240, the stub
    # shape ZZQ(0)>=0 reads -1 -- identical to the real answer. `>0` separates
    # them, because the stub gives 0. The VALUE itself cannot be asserted: &HA8
    # is the primary slot register and its content is a machine-layout fact, so
    # zerobas and the VG-8020 may legitimately differ. `vdpkw` was checked the
    # same way and is sound as written: VDP(1) reads 240 against the stub's 0.
    ("inpkw",   'a=inp(168)',         'PRINT"[";INP(&HA8)>0 ;"]"',            "direct", "D-KWDRAIN"),
    ("outkw",   'out 160,7',          'OUT &HA0,7:PRINT"[8]"',                "direct", "D-KWDRAIN"),
    # 🌾 D-KWBREADTH batch 6: the row above writes the PSG ADDRESS latch and scores
    # a marker; this one drives the whole OUT -> INP round trip through the DATA
    # port, so the byte it wrote is the byte that is read.
    ("out_b",   'out 161,77',
     'OUT&HA0,0:OUT&HA1,77:OUT&HA0,0:PRINT"[";INP(&HA2);"]"',                 "stored",
     "D-KWDRAIN: the value OUT actually DELIVERED, via the PSG's own readback. "
     "The `outkw` row writes only the address latch and never reads it back."),
    # 🔴 `WAIT` HAS NO ROW HERE, AND THE FIRST ATTEMPT IS WHY. `WAIT port,mask
    # [,xor]` blocks until ((INP(port) XOR xor) AND mask) <> 0, so a mask of 0 can
    # NEVER be satisfied: the row `WAIT &HA9,0:PRINT"[9]"` -- written believing
    # mask 0 meant "already true" -- blocks for ever BY DEFINITION, and zerobas
    # returning no output was it behaving CORRECTLY. Attributing WAIT needs a port
    # whose condition is satisfiable without blocking, and the obvious candidate
    # (the VDP status port, whose bit 7 sets every frame) is read-to-clear and
    # would disturb the BIOS interrupt handler. Left unattributed on purpose --
    # "no known gap" is the honest state for it until a safe row exists.
    ("pokekw",  'poke 0,1',           'POKE-8192,7:PRINT"[";PEEK(-8192);"]"', "direct", "D-KWDRAIN"),

    # ---------------------------------------------- D-KWDRAIN step 4a (2026-09-12)
    # 🔴 A CORRECTION TO WHAT BATCH 3 FILED. I wrote that the display verbs "cannot
    # take a kwsweep row at all" because they destroy the echo this sweep anchors
    # on. That was the ANCHOR's limit, not the words': `marker_tail` above captures
    # from a unique per-row marker instead, which is what the arrays and deffn
    # suites have always done with `CLS:PRINT"[";...`. So the words come back in
    # reach, and the claim is retracted where it was made.
    ("widthkw", 'width 37',    'WIDTH 37:PRINT"[W";PEEK(-3152);"]"',  "direct",
     "NOECHO:[W WIDTH reformats the screen and takes the echo with it; the row reads LINLEN ($F3B0 = -3152) back, so a WIDTH that parses and does nothing still fails. absent => syntax error => no marker at all."),
    # 🔴 `KEY` HAS NO ROW, AND THE ATTEMPT THAT PASSED IS WHY. A `keykw` row
    # reading CRTCNT ($F3B1) after `KEY OFF` came back SUPPORTED / match on both
    # machines -- and it was BLIND. Measured directly
    # (scratchpad/kwdrain_keyblind.py): CRTCNT reads 24 with KEY OFF and 24
    # WITHOUT it, on zerobas AND on the VG-8020, so a KEY that parsed and did
    # nothing would have passed the row identically. A green verdict is not
    # evidence that the readback MOVES [[a-case-that-agrees-can-agree-for-the-wrong-reason]].
    # The honest readback is the function-key buffer, but FNKSTR is not declared
    # in basic/sysvars.inc and the standard $F87F would be an unverified
    # constant. KEY stays unattributed until one of those is settled.

    # ---------------------------------------------- D-KWDRAIN step 4c (2026-09-12)
    # The graphics verbs, reachable at last. Two things had to combine: the
    # echo-free capture above (SCREEN 0/2 destroys the echo), and doing the READBACK
    # BEFORE returning to text mode -- a SCREEN 2 screen cannot be read as 40-column
    # text at all, so the row draws, reads POINT into a variable, goes back to
    # SCREEN 0 and only then prints its marker.
    # 🎯 THE READBACK IS MEASURED FIRST, as the standard now requires
    # (scratchpad/kwdrain_gfxcheck.py, both machines agreeing): POINT reads 4 on a
    # blank SCREEN 2, 15 after `PSET ,15`, and 4 again after PRESET. So each row
    # below moves when its own verb stops working, rather than passing on a value
    # that was already there.
    # ⚠️ PSET AND POINT ARE COUPLED and the rows say so: POINT can only read what
    # something drew, so `pointkw` moves if EITHER breaks. It is still worth a row --
    # a POINT that parses as an array reads 0, which neither 4 nor 15 can be.
    # ---------------------------------------------- D-KWDRAIN step 4d (2026-09-12)
    # 🎯 EVERY READBACK BELOW WAS MEASURED BEFORE THE ROW WAS WRITTEN
    # (scratchpad/kwdrain_gfx2.py, both machines agreeing), and the measurement
    # changed two of them:
    #   CIRCLE  rim POINT(60,50) = 15 while the CENTRE reads 4 -- so the row sees a
    #           real circle and not a filled blob.
    #   DRAW    POINT(14,10) = 15 after `C15R5` from (10,10); blank is 4.
    #   BASE    BASE(2) = 2048 and BASE(10) = 6144 -- but 🔴 BASE(0) IS 0, which is
    #           exactly what a stub returns, so the obvious argument would have made
    #           a BLIND row. The row uses BASE(2).
    # 🟢 SPRITE'S NO-OUTPUT WAS DIAGNOSED, NOT GUESSED AT
    # (scratchpad/kwdrain_spritechk.py): `SPRITE$(0)=...` raises ILLEGAL FUNCTION
    # CALL in SCREEN 0 -- sprites need a graphics screen -- which is why the first
    # form printed nothing at all. In SCREEN 2 the round-trip works: ASC reads back
    # 255 and LEN reads 8. The row below therefore writes the pattern to VRAM and
    # reads it back through SPRITE$, so it moves if either half stops working.
    ("circlekw",  'circle(50,50),10', 
     'SCREEN2:CIRCLE(50,50),10,15:A=POINT(60,50):SCREEN0:PRINT"[Q";A;"]"', "stored",
     "NOECHO:[Q rim pixel is 15, centre is 4 -- a filled or absent circle fails"),
    # 🌾 D-KWBREADTH batch 10: the row above draws a FULL circle; the START/END arc
    # arguments are untouched. This draws only the upper-right quadrant and reads
    # TWO pixels, which is what makes it discriminating: a full circle gives 15 15,
    # a correct arc gives 15 4, and an absent CIRCLE gives 4 4. Reading the OFF-arc
    # pixel alone would have been blank-on-both-sides -- mode 2 -- because a CIRCLE
    # that drew nothing leaves it blank too.
    ("circlekw_b", 'circle(50,50),10,15,0,1.57',
     'SCREEN2:CIRCLE(50,50),10,15,0,1.57:A=POINT(60,50):B=POINT(40,50):SCREEN0:PRINT"[F";A;B;"]"',
     "stored",
     "NOECHO:[F the ARC arguments -- start 0 (rightmost) to end 1.57 rad (top), so "
     "(60,50) is ON the arc and (40,50) is not. 15 4 for an arc, 15 15 if the "
     "start/end are parsed and discarded."),
    ("drawkw",    'draw"c15r5"',      
     'SCREEN2:PSET(10,10),15:DRAW"C15R5":A=POINT(14,10):SCREEN0:PRINT"[D";A;"]"', "stored",
     "NOECHO:[D reads 4 pixels right of the start: blank is 4, drawn is 15"),
    # 🌾 D-KWBREADTH batch 10: the row above drives ONE direction command (`R`). A
    # DRAW that implemented only R -- or that ignored the letter entirely and moved
    # right -- passes it. `D` moves DOWN, so the pixel read is BELOW the start.
    ("drawkw_b",  'draw"c15d5"',
     'SCREEN2:PSET(10,10),15:DRAW"C15D5":A=POINT(10,14):SCREEN0:PRINT"[E";A;"]"',
     "stored",
     "NOECHO:[E a DIFFERENT direction command -- `D` draws DOWN, so this reads a "
     "pixel below the start where the `R` row reads one to the right. 15 drawn, "
     "4 blank."),
    # 🔴 THE CRUNCH IS `sprite on`, NOT `sprite$(0)=...`, AND THE FIRST CUT TAUGHT
    # ME WHY. tier_table's WORD regex keeps a trailing `$` (so STR$ and MID$ match),
    # which makes `sprite$(0)="x"` tokenise to SPRITE$ -- and the kwtable keyword is
    # SPRITE. The row reported SUPPORTED and credited NOTHING: four rows went in and
    # the evidence count rose by three. `sprite on` names SPRITE first and is real
    # BASIC besides.
    ("spritekw",  'sprite on',
     'SCREEN2:SPRITE$(0)=STRING$(8,255):A=ASC(SPRITE$(0)):SCREEN0:PRINT"[Z";A;"]"',
     "stored",
     "NOECHO:[Z writes the pattern to VRAM and reads it back: 255 round-trips, "
     "a stub reads 0 and SCREEN 0 raises Illegal function call"),
    ("basekw",    'a=base(2)',         'PRINT"[";BASE(2);"]"',               "direct", "D-KWDRAIN"),

    # ---------------------------------------------- D-KWDRAIN step 4e (2026-09-12)
    # 🎯 THE MULTI-LINE WORDS, AND THEY WERE NEVER BLOCKED EITHER. `as_stored`
    # SPLITS a `:`-joined line into numbered lines 10/20/... , packing statements
    # greedily into <=34-char bodies -- so a "one-line" exec is already a
    # multi-line program, and GOSUB/RETURN/READ/RESTORE only needed the line
    # numbers to be worked out rather than guessed. Verified by printing the
    # packing before writing a row, and by running it (scratchpad/
    # kwdrain_multiline.py, both machines): `A=0:GOSUB 20:...:END:A=7:RETURN`
    # packs to `10 A=0:GOSUB 20:PRINT...:END` / `20 A=7:RETURN` and answers 7.
    # 🔴 THE CONTROL IS WHAT MAKES THE RESTORE ROW MEAN ANYTHING: a single
    # `READ Q` answers 3, and the row answers 6 -- so the second READ really did
    # re-read the same DATA, which is only true if RESTORE reset the pointer.
    # ⚠️ `ON` IS NOT HERE: its two-target form packs badly -- the greedy packer
    # swallows both subroutines into line 20 -- and padding statements to force a
    # boundary would make the row about the packer instead of the keyword.

    # ---------------------------------------------- D-KWDRAIN step 4f (2026-09-12)
    # The error-handling cluster, four keywords off ONE program: line 10 arms the
    # handler and raises, line 20 reports. Measured on both machines before the rows
    # were written (scratchpad/kwdrain_errhand.py): ERR reads 7 and ERL reads 10, so
    # the row carries the CODE and the LINE, not just "something was trapped".
    # 🎯 RESUME NEEDED ITS OWN PROGRAM, and the packer decided its shape: the greedy
    # split puts the handler alone on line 30 as `RESUME NEXT`, which resumes at the
    # statement after the one that raised -- the PRINT on line 20. So the row prints
    # at all ONLY because RESUME returned control; drop RESUME and the program ends
    # in the handler with nothing on screen.
    # ⚠️ DEFINT's row asserts 1, NOT 1.7: a DEFINT that parses and does nothing would
    # still print 1.7, so the row sees the COERCION rather than the parse.

    # ---------------------------------------------- D-KWDRAIN step 4g (2026-09-12)
    # 🎯 TWO WORDS THAT SEPARATE THROUGH AN ERROR, WHICH IS STILL A DIFFERENTIAL.
    # Measured on both machines first (scratchpad/kwdrain_misc1.py):
    #   MAX bare      -> Syntax error on a real machine, `0` on a stub (an unknown
    #                    word is just a variable), so the row proves MAX is TOKENISED
    #                    rather than parsed as a name.
    #   STRIG(5)      -> Illegal function call (the valid range is 0..4), while an
    #                    undefined array STRIG(5) auto-dims and answers 0.
    # ⚠️ AND THREE THAT DO NOT SEPARATE, left unattributed rather than papered over:
    #   LPOS(0) reads 0 and a stub reads 0; LPRINT produced NO OUTPUT AT ALL on both
    #   machines (no printer attached), so neither can be scored from here; and
    #   LEN(INKEY$) is 0 with no key pressed, which is exactly what a stub returns.
    #   INKEY$ needs injected keystrokes, not a cleverer expression.

    # ---------------------------------------------- D-KWDRAIN step 4h (2026-09-12)
    # More words that separate through an ERROR, each measured on both machines
    # first (scratchpad/kwdrain_misc2.py). ATTR$ is the interesting one: bare use
    # raises ILLEGAL FUNCTION CALL rather than a Syntax error, which settles the
    # open question of whether it is an MSX1 BASIC token at all -- it is.
    # 🔴 `NEW` GOT NO ROW BECAUSE IT GOT AN ITEM: `10 NEW` + RUN is
    # `Syntax error in 10` here and `Ok` on the VG-8020, with `CLEAR` in the same
    # position accepted on both. That is filed as a TIER 1 defect in TODO.md, which
    # attributes the keyword far better than a permanently-divergent row would.
    # ⚠️ PDL IS STILL OUT: PDL(13) raises Illegal function call, but the STUB shape
    # also errors there (subscript out of range), so the two separate only by error
    # PHRASE. PDL(0) should separate cleanly -- measure it before writing the row.
    # 🎯 PDL USES THE VALUE, NOT THE ERROR. `PDL(0)` is out of range and raises
    # Illegal function call while a stub answers 0, which WOULD separate -- but
    # `PDL(1)` reads 255 on BOTH machines against a stub's 0, and a value
    # differential says more than an error one (scratchpad/kwdrain_pdlchk.py).
    ("pdlkw",     'a=pdl(1)',    'PRINT"[";PDL(1);"]"',       "direct",
     "D-KWDRAIN: 255 on both; an absent PDL parses as an array and reads 0"),
    ("padkw",     'a=pad(0)',    'PRINT"[";PAD(9);"]"',     "direct",
     "D-KWDRAIN: 9 is outside PAD's range -> Illegal function call; an undefined array auto-dims to 10 and answers 0"),
    ("attrkw",    'a$=attr$',    'PRINT"[";ATTR$;"]"',      "direct",
     "D-KWDRAIN: bare ATTR$ raises Illegal function call -- so the word IS a token here; an undefined string variable prints empty instead"),
    ("stopkw",    'stop',        'PRINT"[T1]":STOP',        "stored",
     "D-KWDRAIN: prints then Break in 10 on both machines; without STOP there is no Break"),
    ("maxkw",     'max',               'PRINT"[";MAX;"]"',                     "direct",
     "D-KWDRAIN: bare MAX is a Syntax error on a real machine; a stub prints 0"),
    ("strigkw",   'a=strig(0)',        'PRINT"[";STRIG(5);"]"',                "direct",
     "D-KWDRAIN: 5 is out of STRIG's 0..4 range -> Illegal function call; an "
     "undefined array auto-dims and answers 0"),
    ("onkw",      'on error goto 20', 
     'ON ERROR GOTO 20:ERROR 7:END:PRINT"[R";ERR;ERL;"]":END',  "stored", "D-KWDRAIN: ON in its ON ERROR form"),
    # 🌾 D-KWBREADTH batch 12: `ON` HAS THREE FORMS AND THE ROW ABOVE COVERS ONLY
    # `ON ERROR GOTO`. The INDEX-SELECTED jump -- the form a 1985 listing actually
    # uses -- had no row at all. It needs SEPARATE numbered lines as targets, and
    # `as_stored` packs statements GREEDILY into <=34-char bodies, so THE PACKING WAS
    # PRINTED BEFORE THE ROW WAS WRITTEN, exactly as `runkw`'s note prescribes:
    #     10 ON 2 GOTO 20,30:PRINT"[J00]":END
    #     20 REM ZQ:PRINT"[J77]":END
    #     30 PRINT"[J99]":END
    # 🎯 THREE DISTINCT READINGS, WHICH IS WHAT MAKES IT DISCRIMINATING: `[J99]` if
    # the INDEX is honoured, `[J77]` if the ON jumps to the FIRST target whatever
    # the index, and `[J00]` if it falls through without jumping at all.
    # ⚠️ The `REM ZQ` is load-bearing PACKING, not decoration: without it the two
    # handlers merge into one body and line 30 does not exist.
    ("ongoto",   'on 2 goto 20,30',
     'ON 2 GOTO 20,30:PRINT"[J00]":END:REM ZQ:PRINT"[J77]":END:PRINT"[J99]":END',
     "stored",
     "NOECHO:[J the INDEX-SELECTED jump. `ON 2` must reach the SECOND target: "
     "[J99]. An ON that ignores the index gives [J77], one that never jumps [J00]."),
    # 🌾 D-KWBREADTH batch 13: the GOSUB sibling. `RETURN` lands back on line 10's
    # PRINT, so the handler's value is what gets read. THE PACKING WAS SEARCHED FOR,
    # not guessed -- the greedy packer merges handlers unless the padding before
    # each one fills its body to the 34-char limit, and no padding below 22 chars
    # does it:
    #     10 ON 2 GOSUB 30,40:PRINT"[K";A;"]"
    #     20 END:REM ZZZZZZZZZZZZZZZZZZZZZZ
    #     30 A=77:RETURN:REM QQQQQQQQQQQQQQ
    #     40 A=99:RETURN
    # ⚠️ The two REM runs are LOAD-BEARING PACKING. The targets were re-written from
    # the search's 20,30 to 30,40 only because both are FIVE characters, so the
    # packing is bit-for-bit unchanged -- verified, not assumed.
    ("ongosub",  'on 2 gosub 30,40',
     'ON 2 GOSUB 30,40:PRINT"[K";A;"]":END:REM ZZZZZZZZZZZZZZZZZZZZZZ:A=77:RETURN:REM QQQQQQQQQQQQQQ:A=99:RETURN',
     "stored",
     "NOECHO:[K the INDEX-SELECTED subroutine call. `ON 2` must reach the SECOND "
     "target and RETURN: 99. An ON that ignores the index gives 77, one that never "
     "calls leaves A at 0."),
    ("errorkw",   'error 7',          
     'ON ERROR GOTO 20:ERROR 7:END:PRINT"[R";ERR;ERL;"]":END',  "stored", "D-KWDRAIN: ERROR 7 is what raises it"),
    ("errkw",     'a=err',            
     'ON ERROR GOTO 20:ERROR 7:END:PRINT"[R";ERR;ERL;"]":END',  "stored", "D-KWDRAIN: ERR reads 7, the code raised"),
    ("erlkw",     'a=erl',            
     'ON ERROR GOTO 20:ERROR 7:END:PRINT"[R";ERR;ERL;"]":END',  "stored", "D-KWDRAIN: ERL reads 10, the line that raised"),
    ("resumekw",  'resume next',      
     'ON ERROR GOTO 30:ERROR 7:PRINT"[U";A;"]":END:A=5:RESUME NEXT', "stored", "D-KWDRAIN: the handler RESUMEs NEXT and control reaches the PRINT; without it nothing prints"),
    ("defintkw",  'defint a',         
     'DEFINT A:A=1.7:PRINT"[";A;"]"',                           "direct", "D-KWDRAIN: 1, not 1.7 -- a DEFINT that parses and does nothing still prints 1.7"),

    # ---------------------------------------------- D-KWDRAIN step 4i (2026-09-12)
    # 🔴 NEW GETS A ROW *BECAUSE ITS DEFECT WAS FIXED*, which is not as odd as it
    # sounds. Attribution comes from OPEN items, so the moment D-NEWSTMT closed, the
    # keyword fell straight back into "no known gap" -- the table cannot tell
    # "investigated and now correct" from "nobody ever looked". A row is what holds
    # the ground a fix won.
    # The exec is the defect's own shape: before the fix it printed [A] and then
    # `Syntax error in 10`; now it prints [A] and stops, like the reference.

    # ---------------------------------------------- D-KWDRAIN step 4j (2026-09-12)
    # The program verbs, written from shapes ALREADY MEASURED on both machines in
    # the D-NEWSTMT sweep (scratchpad/kwdrain_progverbs.py) rather than guessed.
    # ⚠️ AND TWO OF THAT SWEEP'S VERBS GET NO ROW, because agreeing with the
    # reference is not the same as being SEEN by a row:
    #   LLIST -- both machines print only [A] (the printer output goes to the log,
    #            not the screen), so an LLIST that did nothing would pass too.
    #   RENUM -- both print [A] then Ok, and in a ONE-LINE program renumbering 10
    #            to 10 changes nothing observable. It needs a two-line program and
    #            a LIST read-back; measure that before writing the row.
    ("listkw",    'list',       
     'PRINT"[A]":LIST',                                     "stored",
     "D-KWDRAIN: the LISTING itself is the discriminator -- a LIST that did nothing would leave only [A] on the screen"),
    ("deletekw",  'delete 99',  
     'PRINT"[A]":DELETE 99',                                "stored",
     "D-KWDRAIN: Illegal function call in 10 on both (line 99 does not exist); an absent DELETE is a Syntax error, a different class"),
    # 🔴 `AUTO` HAS NO ROW, AND THE ATTEMPT DAMAGED EVERY ROW AFTER IT. A row
    # `PRINT"[A]":AUTO` scored the verb correctly -- both machines print [A] then
    # the `10*` line-entry prompt -- but AUTO LEAVES THE MACHINE IN LINE-ENTRY
    # MODE, so it swallowed the input of the cases that followed: the sweep went
    # from 0 divergent to DIVERGENT=22 + UNREADABLE=1, twenty-one of them
    # collateral. A row is not free of the session it runs in
    # [[the-apparatus-is-part-of-the-measurement]]. Attributing AUTO needs a form
    # that exits line-entry mode, or a case of its own at the END of the sweep.
    ("newkw",     'new',
     'PRINT"[A]":NEW',                                       "stored",
     "D-KWDRAIN: the D-NEWSTMT shape -- [A] then a clean stop; before the fix "
     "this row would have carried `Syntax error in 10` on the zb side"),
    ("gosubkw",   'gosub 20',     
     'A=0:GOSUB 20:PRINT"[G";A;"]":END:A=7:RETURN',         "stored", "D-KWDRAIN: the subroutine sets A=7; no GOSUB, no output"),
    ("returnkw",  'return',       
     'A=0:GOSUB 20:PRINT"[H";A;"]":END:A=7:RETURN',         "stored", "D-KWDRAIN: A is 7 only because RETURN came back to the PRINT"),
    ("endkw",     'end',          
     'A=0:GOSUB 20:PRINT"[J";A;"]":END:A=7:RETURN',         "stored", "D-KWDRAIN: END keeps the subroutine from being fallen into"),
    ("readkw",    'read q',       
     'READ Q:RESTORE:READ R:PRINT"[E";Q+R;"]":END:DATA 3',  "stored", "D-KWDRAIN: reads 3 from the DATA on the second line"),
    ("restorekw", 'restore',      
     'READ Q:RESTORE:READ R:PRINT"[F";Q+R;"]":END:DATA 3',  "stored", "D-KWDRAIN: 6 needs the pointer RESET: without RESTORE the second READ runs out of DATA"),
    ("psetkw",   'pset(1,1)',      
     'SCREEN2:PSET(1,1),15:A=POINT(1,1):SCREEN0:PRINT"[S";A;"]"',   "stored",
     "NOECHO:[S PSET draws, POINT reads it back: 4 blank vs 15 drawn"),
    # 🌾 D-KWBREADTH batch 11: the row above uses colour 15, the default foreground,
    # so a PSET that IGNORED its colour argument and drew in the current foreground
    # passes it. 7 is neither the foreground nor the blank 4, so this reads the
    # COLOUR ARGUMENT rather than "something was drawn".
    ("psetkw_b", 'pset(2,2),7',
     'SCREEN2:PSET(2,2),7:A=POINT(2,2):SCREEN0:PRINT"[H";A;"]"',    "stored",
     "NOECHO:[H a NON-DEFAULT colour -- 7. The `psetkw` row draws in 15, which is "
     "also what a PSET that discarded its colour argument would leave."),
    ("presetkw", 'preset(1,1)',    
     'SCREEN2:PSET(1,1),15:PRESET(1,1):A=POINT(1,1):SCREEN0:PRINT"[R";A;"]"', "stored",
     "NOECHO:[R PRESET must UNDO the PSET: 15 if it does nothing, 4 if it works"),
    ("pointkw",  'a=point(1,1)',   
     'SCREEN2:PSET(1,1),15:A=POINT(1,1):SCREEN0:PRINT"[T";A;"]"',   "stored",
     "NOECHO:[T POINT as the subject: a stub parses as an array and reads 0, not 15"),
    ("linekw",   'line(1,1)-(5,1)',
     'SCREEN2:LINE(1,1)-(5,1),15:A=POINT(3,1):SCREEN0:PRINT"[L";A;"]"', "stored",
     "NOECHO:[L reads a pixel in the MIDDLE of the span, so an endpoint-only LINE fails too"),
    # 🌾 D-KWBREADTH batch 9: the row above draws a plain segment; the `,B` BOX form
    # is untested. (9,1) is the box's TOP-RIGHT CORNER -- on the rectangle, and NOT
    # on the diagonal a `,B`-ignoring LINE would draw between the same two points.
    # So a LINE that parses `,B` and discards it reads 4 (blank) where a real box
    # reads 15.
    ("linekw_b", 'line(1,1)-(9,9),15,b',
     'SCREEN2:LINE(1,1)-(9,9),15,B:A=POINT(9,1):SCREEN0:PRINT"[P";A;"]"', "stored",
     "NOECHO:[P the BOX form -- (9,1) is a corner of the rectangle but not a point "
     "on the diagonal, so a discarded `,B` reads 4 instead of 15"),
    ("colorkw",  'color 7',    'COLOR 7:PRINT"[O";PEEK(-3095);"]"',              "direct",
     "NOECHO:[O COLOR repaints the whole screen, echo included. Reads FORCLR "
     "($F3E9 = -3095) back, and uses 7 rather than the DEFAULT 15 on purpose: "
     "a COLOR that parsed and did nothing would leave 15 there and the row "
     "would pass on the default. absent => syntax error, no marker."),
    # ⚠️ `SCREEN` AND `KEY` ARE NOT HERE YET, each for a stated reason rather
    # than an oversight. SCREEN: the only value that discriminates is a mode
    # CHANGE, and `SCREEN 1` is 32 columns while this capture parses a 40-column
    # screen -- the row would break the reader it depends on. KEY: the natural
    # readback is the function-key buffer, whose address (FNKSTR) is NOT in
    # basic/sysvars.inc, and guessing the standard $F87F would be building on an
    # unverified constant. Both need a measurement first.
    ("clskw",    'cls',        'CLS:PRINT"[C";CSRLIN;"]"',            "direct",
     "NOECHO:[C CLS erases the echo by definition -- the exact row the old "
     "echo-anchored capture could never hold. 🔴 AND IT READS CSRLIN BACK ON "
     "PURPOSE: the first cut printed a bare [C1], which a CLS that PARSED AND "
     "DID NOTHING would have printed just as happily -- scoring the parse and "
     "calling it the behaviour. After a real CLS the cursor is home, so the "
     "row reads 0; leave the screen alone and it reads wherever the echo left "
     "it. absent => syntax error, no marker at all."),

    # -------------------------------------------------- suspected MISSING words
    # Console / cursor. All three fail the same way if absent: the word parses as
    # a numeric variable (0) or an array, so the probe must make 0 the WRONG
    # answer rather than a plausible one.
    # COLUMN ONLY, not `LOCATE 10,0`. The first design used row 0 — and on the
    # reference the feature under test then MOVED THE CURSOR ONTO THE ECHOED
    # COMMAND and overprinted it, so screen_tail could not find the echo and the
    # reference row came back ?noecho/UNREADABLE. The probe was destroying its own
    # anchor. `LOCATE 10` keeps output on the current row, just indented.
    ("locate",  "locate 10,0",
     'LOCATE 10:PRINT"[X]"',                         "direct",
     "absent => `LOCATE 10` is a bare word + juxtaposition => syntax error; "
     "real => `[X]` indented to column 10"),
    # 🌾 D-KWBREADTH batch 5: the row above uses the ONE-argument form and reads the
    # marker's INDENTATION. The ROW argument is untouched, and CSRLIN reads it back
    # EXPLICITLY rather than by column-counting -- the form already recorded as
    # decisive beside the `csrlin` row, because a SET row admits no scroll history.
    # 🔴 AND IT MUST BE ANCHORED WITH `CLS`, WHICH THE `csrlin` ROW BELOW ALREADY
    # SAYS IN SO MANY WORDS. Written without it this row came back DIVERGENT on its
    # FIRST sweep -- and the VALUES AGREED: ref `|||[ 5 ]` vs zb `||||[ 5 ]`, three
    # wrap pipes against four. `LOCATE` MOVES THE CURSOR, so the blank lines ahead
    # of the output depend on ambient screen state and the row measures SCREEN
    # GEOMETRY rather than the keyword. `csrlin`'s note carries both the diagnosis
    # ("the VALUE is ambient scroll state") and the remedy ("Anchored with CLS all
    # three agree everywhere") -- a warning sitting two rows away that this row
    # walked straight into.
    # ⚠️ AND THE `CLS` THEN COSTS THE ECHO, WHICH IS THE NEXT TRAP IN THE SAME
    # CORNER: anchored but untagged, the row came back UNREADABLE `?noecho` on BOTH
    # sides, because CLS erases the echoed command the capture keys on. `NOECHO:`
    # exists for exactly that and the row is captured by its own unique marker.
    ("locate_b", "locate 0,5",   'CLS:LOCATE 0,5:PRINT"[N";CSRLIN;"]"',       "direct",
     "NOECHO:[N " "the ROW argument, read back through CSRLIN -- `[N 5 ]`. The "
     "`locate` row sets only a COLUMN and scores the marker's indentation; CLS "
     "anchors the cursor so this reads the ROW and not the scroll history."),
    ("csrlin",  "a=csrlin",
     # ⚠️ THIS ROW'S "DIVERGENT" IS A PROBE ARTIFACT, NOT A FAITHFULNESS BUG,
     # and it cannot be pinned here. CSRLIN is a POSITION, so with no leading
     # CLS the row reports wherever the boot banner and the batch's own
     # scrolling left the cursor. Measured: unpinned it reads ref 4 vs zb 3 in
     # this batch and ref 9 vs zb 7 in a differently scrolled one -- the
     # REFERENCE disagreeing with itself is the proof that the row is reading
     # ambient state. Prefix `CLS:` and both machines answer 2, with or without
     # a WIDTH pin.
     #
     # But CLS cannot be used HERE: this probe's readout anchors on the typed
     # ECHO, and CLS erases it -- the row then reads '' on both sides and
     # classifies UNREADABLE, which is strictly worse than a divergence you can
     # explain (tried, 2026-07-27). The two requirements are incompatible for
     # this one row, so it stays unpinned and stays explained.
     #
     # CSRLIN itself is CORRECT and properly gated elsewhere: cursor-acceptance
     # 67/67 covers it at a pinned WIDTH 40 + CLS across six cases
     # (docs/cursor-vg8020-characterization.md §2). Treat this row as evidence
     # that CSRLIN is PRESENT, never as evidence about its value.
     #
     # 🟢 SO IT IS NOW SCORED **WEAK**, WHICH IS WHAT THE PARAGRAPH ABOVE HAS
     # BEEN ARGUING FOR WITHOUT USING THE WORD (D-WAITGAP, 2026-09-07). A row
     # that is evidence of PRESENCE and never of VALUE is this probe's own
     # definition of WEAK, and `time` already uses it. The cost of leaving it
     # DIVERGENT was not cosmetic: the sweep read `DIVERGENT=1` permanently, so
     # the headline could not move if CSRLIN ever really broke, and a count that
     # is always 1 teaches its readers to skip it.
     'PRINT:PRINT:PRINT"[";CSRLIN;"]"',              "direct",
     "WEAK: absent => variable CSRLIN reads 0; real => the (non-zero) cursor "
     "row -- but the VALUE is ambient scroll state, so only the non-zero-ness "
     "is a reading. Scored WEAK for the reason the block above gives, and "
     "measured 2026-09-07 (D-WAITGAP, scratchpad/csrlin_probe.py): on THIS row "
     "the two REFERENCES disagree with EACH OTHER -- vg8020 11, cf3300 8, zb 10 "
     "-- in one batch, so it cannot score anything by construction. Anchored "
     "with CLS all three agree everywhere (CLS 0/0/0, CLS:PRINT 1/1/1, "
     "CLS:PRINT:PRINT 2/2/2) and CSRLIN is correct: LOCATE 0,5 -> 5, 0,10 -> 10, "
     "0,0 -> 0 on all three, which is the decisive form because a set row admits "
     "no scroll history."),
    ("pos",     "a=pos(0)",
     'PRINT"    ";:PRINT"[";POS(0);"]"',             "direct",
     "absent => array POS(0) auto-dims to 0; real => the (non-zero) column"),

    # The two PRINT-item pseudo-functions. THE `TAB(` TRAP: with TAB absent,
    # `PRINT TAB(5);"X"` prints ` 0 X` (array element 0 then X) instead of
    # padding to column 5 — so compare the TEXT, and never a bare error code.
    ("tab",     'print tab(5);"x"',
     'PRINT"[";TAB(5);"X]"',                         "direct",
     "absent => array TAB(5)=0 prints ` 0 `; real => pad to column 5"),
    ("spc",     'print spc(5);"x"',
     'PRINT"[";SPC(5);"X]"',                         "direct",
     "absent => array SPC(5)=0 prints ` 0 `; real => 5 spaces"),

    # Program / editor management.
    ("swap",    "swap a,b",
     'A=1:B=2:SWAP A,B:PRINT"[";A;B;"]"',            "direct",
     "absent => syntax error; real => ` 2  1 `"),
    ("fre",     "a=fre(0)",
     'PRINT"[";FRE(0)>1000;"]"',                     "direct",
     "absent => array FRE(0)=0 => `0` (false); real => -1 (true)"),
    # 🌾 D-KWBREADTH batch 8: `FRE(0)>1000` is a half-plane, and the ABSOLUTE figure
    # legitimately differs (the CF-3300's disk ROM steals RAM the diskless VG-8020
    # keeps). The COST of an allocation is a delta and agrees on all three: 99 bytes
    # for a 10-element array. Measured before the row was written.
    ("fre_b",   'a=fre(0)',
     'A=FRE(0):DIM Z(9):B=FRE(0):PRINT"[";A-B;"]"',                           "stored",
     "D-KWDRAIN: FRE tracking an ALLOCATION -- 99 bytes for DIM Z(9). A delta, so "
     "the machine-dependent absolute free figure cancels."),
    ("tron",    "tron",
     "TRON:TROFF:PRINT\"[ok]\"",                     "direct",
     "absent => syntax error; real => accepted (trace toggled off again)"),
    ("troff",   "troff",
     'TROFF:PRINT"[ok]"',                            "direct",
     "absent => syntax error"),
    # 🔴 D-KWFOOT2 (2026-09-13): FOUR CRUNCH-ONLY ROWS WERE REMOVED FROM THIS FILE,
    # AND THE REASON IS THE FOOTER THEY DISTORTED. `lprint` `lpos` `delete` `wait`
    # each gained an EXECUTED twin (`lprintkw` `lposkw` `deletekw` `waitkw`) as the
    # D-KWDRAIN batches went in, and the crunch-only originals stayed beside them.
    # Layer 1 lost nothing: `lprint` and `lpos` had crunch bodies BYTE-IDENTICAL to
    # their twins', and `delete 10` / `wait 0,0` differ from `delete 99` / `wait 0,1`
    # only in a numeric literal, which tokenises to the same keyword byte.
    # ⚠️ WHAT THEY COST WAS THE PROBE'S OWN HONESTY. The footer counts crunch-only
    # ROWS, and a reader reads that as "keywords with no support evidence". Those
    # are different numbers -- only `tier_table --keywords` computes the second --
    # and the gap between them grew by one every time a batch added a twin without
    # retiring its original [[readout-blind-to-its-own-subject]].
    # 🎯 WHAT IS LEFT HERE IS GENUINELY UNEXECUTED, each for a measured reason.
    # 🟢 D-KWINP (2026-09-13): `RENUM` EXECUTES. Its filed reason — "renumbers the
    # stored program; harmless but needs a program to be visible" — was true and
    # not the only route: `RENUM 100` on a one-line program answers
    # `Undefined line 100 in 10` on zerobas AND the CF-3300, byte for byte, while
    # an ABSENT `RENUM` parses `RENUM 100` as a name followed by a number and
    # answers `Syntax error` (scratchpad/kwdrain_inputauto2.out).
    # ⚠️ WHAT THE ROW CANNOT SEE, said out loud: it does NOT prove the renumbering
    # itself. It proves the verb parsed its argument and went LOOKING for a line —
    # which a do-nothing RENUM would not do — and no more. A positive read-back
    # needs a `LIST` after it, and RENUM stops the program, so nothing after it
    # runs in the same case.
    ("renum",   "renum 100",   'RENUM 100:PRINT"[R1]"',   "stored",
     "D-KWINP: `Undefined line 100 in 10` on both machines; absent => Syntax error"),

    # D-DEFTYPETOK (2026-08-19): DEFSNG/DEFDBL/DEFSTR now have whole-word
    # kwtable.inc rows and single-byte tokens of their own ($AD/$AE/$AB, beside
    # DEFINT's $AC from D-DEFINTTOK), so they TOKENISE and reach ex_deftype
    # (basic/usr.asm) as one byte each. The DEF_TOKEN + literal ASCII mechanism
    # they used to arrive by is gone, and so is ex_def_type (merged into
    # ex_deftype). Until then they were the one family where "absent from the
    # keyword table" was expected AND support was expected — the INTERVAL
    # shape, in-tree, flagged by this probe's own coverage audit as a blind spot.
    # They are ordinary tokenising rows now; the three cases below are kept
    # because they gate the BEHAVIOUR, which is what they always gated.
    ("defsng",  "defsng a",
     'DEFSNG A:A=1.5:PRINT"[";A;"]"',                "direct", "control"),
    ("defdbl",  "defdbl a",
     'DEFDBL A:A=1.5:PRINT"[";A;"]"',                "direct", "control"),
    ("defstr",  "defstr a",
     'DEFSTR A:A="x":PRINT"[";A;"]"',                "direct", "control"),

    # User-defined functions.
    # STORED, not direct: the reference answers `Illegal direct` to a direct-mode
    # DEF FN — measured, first run of this sweep. So the direct form tests the
    # direct-mode restriction, not the feature.
    ("deffn",   "def fna(x)=x+1",
     'DEF FNA(X)=X+1:PRINT"[";FNA(2);"]"',           "stored",
     "absent => syntax error; real => 3"),

    # The two missing logical operators.
    ("eqv",     "a=5 eqv 3",
     'PRINT"[";5 EQV 3;"]"',                         "direct",
     "absent => juxtaposition syntax error; real => -7"),
    ("imp",     "a=5 imp 3",
     'PRINT"[";5 IMP 3;"]"',                         "direct",
     "absent => juxtaposition syntax error; real => -5"),

    # Printer surface. The LPTOUT device layer ships (zerobas-tape page-0 patch),
    # so a divergence here is statement-surface only. Printer is UNPLUGGED in the
    # harness by default and LSTOUT is NOT hang-safe unplugged (openmsx-printer-
    # pluggable), so these are crunch-only — executing LPRINT could wedge the run.
    # 🟢 D-KWLOG (2026-09-13): `LLIST` EXECUTES AT LAST, and the blocker was a
    # CAPTURE rather than a hazard. The LSTOUT hazard is real and is what the plug
    # answers; what kept the verb unscored is that its ONLY output is the printer,
    # and the program STOPS at it on both machines so nothing reaches the screen
    # (direct mode has no program to list at all -- an empty log, for the opposite
    # reason). Measured on both: the log reads `10 LLIST:REM ZQ8\r\n`, byte for
    # byte (scratchpad/kwdrain_llistchk.out).
    # 🎯 THE PROGRAM BEING LISTED IS THE ROW'S OWN, which is what makes the
    # expected text something chosen rather than hoped for -- and `:REM ZQ8` is in
    # it on purpose: a listing that printed only the line number, or mangled the
    # token spacing, fails a row that asserted the verb's own name alone.
    # 🔴 THE BLIND SHAPE WAS MEASURED: the same program WITHOUT the `LLIST`
    # (`10 REM ZQ8`) leaves the log EMPTY on both machines, so the reading exists
    # only because the verb ran.
    ("llist",   "llist",       "LLIST:REM ZQ8",  "stored",
     "NEEDS-LOG: " "the listing itself, off the printer log -- the row's own "
     "stored program. Absent => Syntax error on the SCREEN and an empty log, which "
     "is why the CLASS comes from the screen and only the TEXT from the log."),

    # Cassette / misc statements.
    ("motor",   "motor on",
     'MOTOR OFF:PRINT"[ok]"',                        "direct",
     "absent => syntax error; MOTOR OFF is the safe direction"),
    # KEPT DELIBERATELY, AND KEPT WEAK. This row is the TAB( mistake reproduced
    # on purpose: `TIME>=T` is `0>=0` on a machine with no TIME at all, so BOTH
    # sides answer -1 and the row reports SUPPORTED for a feature that does not
    # exist. It is the in-tree demonstration that a passing differential case
    # proves nothing unless the absent-feature parse gives a DIFFERENT answer.
    # WEAK: rows are excluded from the tally and flagged in the report.
    ("time",    "time=0",
     'T=TIME:PRINT"[";TIME>=T;"]"',                  "direct",
     "WEAK: absent => variable TI, always 0, and `0>=0` is STILL true, so this "
     "row passes on a machine with no TIME. The `timetick` row is the real test."),
    # STORED mode, not direct: the line is 46 chars, so its prompt echo wraps
    # across two 40-column rows and screen_tail's echo match fails -> ?noecho ->
    # UNREADABLE. In stored mode the echoed command is just "RUN". (Caught by the
    # MAX_DIRECT_ECHO guard below, which exists so this cannot recur silently.)
    ("timetick", "a=time",
     'T=TIME:FOR I=1 TO 400:NEXT:PRINT"[";TIME>T;"]"', "stored",
     "THE discriminator: a real TIME advances across a delay loop; the variable "
     "`TI` does not. This is the row that catches the silent gap."),

    # INTERVAL — the retraction case. It is NOT a keyword on either side (it is
    # INT+"ER"+VAL), so CRUNCH is expected to MATCH while SUPPORT is expected to
    # differ. Any probe design that reports this row as "fine" is broken.
    ("interval", "interval on",
     None,                                           "direct",
     "needs a stored ON INTERVAL=n GOSUB program + a timed window; covered by "
     "probes/basic/basic_probe_interval_trap.py (T5 slice), not duplicated here"),

    # Random-access float conversions (the MKI$/CVI integer pair ships).
    # MKI$ is the FAMILY CONTROL: the first run had the reference answering
    # `Illegal function call` to `LEN(MKS$(1))`, which could mean either "MKS$
    # needs Disk BASIC on this diskless VG-8020" or "my expression is wrong".
    # MKI$ is implemented on BOTH sides, so it separates those two readings.
    ("mki",     'a$=mki$(1)',   'PRINT"[";LEN(MKI$(1));"]"',  "direct",
     "NEEDS-DISK: " "control for the MK/CV family — MKI$ ships in zerobas"),
    ("mks",     'a$=mks$(1)',   'PRINT"[";LEN(MKS$(1));"]"',  "direct",
     "NEEDS-DISK: " "absent => syntax error; real => 4"),
    ("mks_b",   'a=asc(mks$(1.5))', 'PRINT"[";ASC(MKS$(1.5));"]"', "direct",
     "NEEDS-DISK: " "MKS$'s CONTENT, where its own row scores only LENGTH -- and "
     "`LEN(MKS$(1))=4` is passed by a stub returning four ZERO bytes. 1.5 packs "
     "as 65 21 0 0, MEASURED on the CF-3300 and equal to PEEK(VARPTR(A!)) for "
     "A!=1.5 (basic/str-engine.asm), so the exponent byte reads 65."),
    ("mkd",     'a$=mkd$(1)',   'PRINT"[";LEN(MKD$(1));"]"',  "direct",
     "NEEDS-DISK: " "absent => syntax error; real => 8"),
    ("mkd_b",   'a=asc(mkd$(1.5))', 'PRINT"[";ASC(MKD$(1.5));"]"', "direct",
     "NEEDS-DISK: " "the same content reading on the 8-byte DOUBLE pack, whose "
     "row likewise scores only LENGTH."),
    ("cvs",     'a=cvs("abcd")', 'PRINT"[";CVS(MKS$(1));"]"', "direct",
     "NEEDS-DISK: " "absent => syntax error; real => 1"),
    ("cvd",     'a=cvd("abcdefgh")', 'PRINT"[";CVD(MKD$(1));"]"', "direct",
     "NEEDS-DISK: " "absent => syntax error; real => 1"),

    # 🌱 D-KWBREADTH batch 2 (2026-09-13) — THE MK/CV FAMILY IS THE THINNEST
    # COVERAGE IN THE TREE, AND THAT IS MEASURED, NOT GUESSED. `make kwcover`
    # over a full 83-suite / 46 969-line capture reports CVD at 2 suites and
    # MKI$/MKS$/MKD$/CVS at 3 — and the only non-kwsweep suite that types any of
    # them is `lnblank-acceptance`, which types them as TOKENISER subjects
    # (`20 CALL X`, `20 CALLX5`) and never EXECUTES one. So each of these words
    # has exactly ONE scoring row, and these rows add the forms it cannot reach.
    ("cvi_b",   'a=cvi(mki$(-1))',
     'A=CVI(MKI$(-1)):B=CVI(MKI$(32767)):PRINT"[";A;B;"]"', "stored",
     "NEEDS-DISK: " "THE SIGN AND THE 16-BIT EXTREME. The `cvi` row round-trips "
     "7, whose high byte is 0 and whose sign bit is clear — neither a byte swap "
     "nor a sign error can show there. -1 and 32767 separate both. STORED "
     "because the direct form is 43 columns, and 37 was already too many."),
    ("cvs_b",   'a=cvs(mks$(1.5))',
     'PRINT"[";CVS(MKS$(1.5));"]"', "direct",
     "NEEDS-DISK: " "A FRACTION. The `cvs` row round-trips 1, which survives "
     "almost any mantissa packing; 1.5 needs a real one."),
    ("cvd_b",   'a=cvd(mkd$(.1))',
     'PRINT"[";CVD(MKD$(.1));"]"', "direct",
     "NEEDS-DISK: " "a fraction with NO exact binary form, on the DOUBLE path — "
     "the 8-byte pack, not the 4-byte one."),
    ("mki_b",   'a=asc(mki$(258))',
     'PRINT"[";ASC(MKI$(258));"]"', "direct",
     "NEEDS-DISK: " "MKI$'s CONTENT, NOT ITS LENGTH. The `mki` row scores "
     "LEN(MKI$(1))=2 — which a stub returning two zero bytes passes. 258 is "
     "$0102, so both of its bytes are non-zero and ASC reads whichever end the "
     "pack puts first; a disagreement here is a real finding, not a blind row."),

    # -------------------------------------------- D-KWRIG (2026-09-12)
    # FOUR WORDS WHOSE FILED BLOCKER WAS A CONSTANT OR A MODE, and all four were
    # stale. Re-verified before being believed, which is now five sessions running
    # (scratchpad/kwdrain_misc3.py, both machines).
    # 🔴 `SCREEN` was filed as *"its only discriminating value is a MODE CHANGE,
    # and SCREEN 1 is 32 columns while this capture parses a 40-column screen --
    # the row would break the reader it depends on."* True, and beside the point:
    # nothing makes the row STAY in the mode. `SCRMOD` ($FCAF) IS declared in
    # basic/sysvars.inc, so the row switches, reads, comes back and prints from
    # SCREEN 0 -- the shape the graphics rows have used since step 4c.
    # 🔴 `KEY` was filed as blocked because FNKSTR is NOT in basic/sysvars.inc and
    # guessing $F87F would build on an unverified constant. That reasoning stands;
    # what it missed is that `KEY LIST` puts the definitions ON THE SCREEN, which
    # needs no constant at all. Measured: the ten defaults agree on both machines,
    # so the only difference the row can see is the one it makes.
    # 🔴 `USR` was filed as needing "machine code to call". One POKEd $C9 is
    # machine code: a bare RET leaves DAC alone, so USR returns its argument.
    ("usrkw",    "a=usr(0)",
     'POKE-8192,&HC9:DEFUSR=-8192:A=USR(7):PRINT"[U";A;"]"',   "stored",
     "D-KWRIG: the POKEd byte is a RET, so USR(7) returns 7 -- and the stub shape "
     "measures 0 (an undefined array subscripted by 7), so the row separates on a "
     "VALUE. $E000 is the cell `pokekw` already uses."),
    ("screenkw", "screen 2",
     'SCREEN2:A=PEEK(&HFCAF):SCREEN0:PRINT"[G";A;"]"',          "stored",
     "NOECHO:[G SCRMOD ($FCAF, DECLARED in basic/sysvars.inc) reads 2 inside "
     "SCREEN 2 and 0 in text mode, on both machines -- so the row sees the MODE "
     "and not merely that the statement parsed, and it reads the mode BEFORE "
     "returning to SCREEN 0 because a graphics screen cannot be scraped as text."),
    ("keykw",    'key 1,"x"',
     'KEY 1,"ZZQ":KEY LIST',                                    "stored",
     "D-KWRIG: `KEY LIST` prints all ten definitions and the row compares the "
     "WHOLE listing: the ten defaults are identical on both machines, so the only "
     "difference either side can show is `ZZQ` in slot 1 -- which is there only if "
     "the assignment happened. No FNKSTR constant is needed or guessed."),
    # 🔴 `WAIT` IS BACK, AND THE ROW THAT BLOCKED FOR EVER IS WHY IT LOOKS LIKE
    # THIS. Batch 3 wrote `WAIT &HA9,0`, read mask 0 as "already true", and the
    # row never returned. `WAIT p,m` returns when `INP(p) AND m` is non-zero, so
    # the mask has to be chosen from a MEASURED port: INP(&HA8) reads 240 on
    # zerobas AND on the VG-8020 (scratchpad/kwdrain_misc3.out), and &HFF is
    # satisfied by any non-zero read. PROVED TO RETURN before this row existed
    # (scratchpad/kwdrain_waitchk.py), with batch 3's own mask-0 form as the
    # control -- it still returns NOTHING, which is what says the machine really
    # blocks and this WAIT is not a no-op.
    # ⚠️ WHAT THE ROW CANNOT SEE, said out loud: a WAIT that parsed and returned
    # immediately passes it. WAIT has no observable but blocking, so the row scores
    # ABSENCE (a missing WAIT makes `WAIT &HA8,&HFF` a Syntax error) and the
    # blocking itself is scored by that control, which can never be a sweep row
    # because it does not come back [[a-case-that-agrees-can-agree-for-the-wrong-reason]].
    ("waitkw",   "wait 0,1",
     'WAIT &HA8,&HFF:PRINT"[Y1]"',                              "stored",
     "D-KWRIG: mask &HFF against a port measured at 240 on both machines"),

    # --- the printer pair. They need a PLUGGED printer (NEEDS-PRINTER:), and that
    # tag is not decoration: with nothing on the port both rows produce NO OUTPUT
    # AT ALL on both machines -- the LSTOUT hang, measured
    # (scratchpad/kwdrain_lptchk.out).
    ("lposkw",   "a=lpos(0)",
     'LPRINT"ABC";:PRINT"[P";LPOS(0);"]"',                      "stored",
     "NEEDS-PRINTER: " "the head COLUMN, which reaches the screen even though the "
     "printed text does not: 0 at rest, 3 after three bytes, 7 after seven, the "
     "same on both machines. 🔴 THE `LPRINT` IS THE ROW: batch 4g measured bare "
     "`LPOS(0)` as 0 against a stub's 0 and left the word unattributed for exactly "
     "that reason -- the readback had to be MOVED before it could be read."),
    ("lprintkw", 'lprint"x"',
     'LPRINT"ABC";:PRINT"[P";LPOS(0);"]"',                      "stored",
     "NEEDS-PRINTER: " "the same measurement from the other end, and deliberately "
     "the SAME exec line: `LPOS` is the only readback either word has from the "
     "screen, so the pair is coupled exactly as `pset`/`point` are. It moves if "
     "EITHER breaks, and 3 is a byte COUNT -- an LPRINT that emitted nothing "
     "leaves the head at 0. `LLIST` and `LFILES` are NOT here: their subject is "
     "the printed TEXT, which needs the log capture."),

    # ------------------------------------------------ D-KWDISK (2026-09-12)
    # The file-and-channel verbs, which had no row for one reason only: nothing
    # was in the drive. `DSKF(0)` reading 0 was filed as "exactly what a stub
    # reads"; with the image mounted it reads 707, and the coincidence that hid
    # the verb is gone [[a-case-that-agrees-can-agree-for-the-wrong-reason]].
    # 🎯 EVERY READBACK WAS MEASURED BEFORE THE ROW WAS WRITTEN, on BOTH machines
    # (scratchpad/kwdrain_diskfinal.py, scratchpad/kwdrain_diskslow.py), and two
    # candidate rows were thrown away for being blind: a `CLOSE` row that reopened
    # channel 1 passed WITHOUT the close (zerobas lets #1 be reopened), and a
    # `FILES` row reading CSRLIN read 1 on zerobas and 0 on the CF-3300 because
    # the CF-3300 shows the function-key line and its screen is a row shorter —
    # the MACHINES, not the verb [[readout-blind-to-its-own-subject]].
    ("dskf",    "a=dskf(0)",
     'PRINT"[";DSKF(1);"]"',                         "stored",
     "NEEDS-DISK: " "707 free KB on the 720 KB fixture, against a stub's 0. This is "
     "the row the empty drive was hiding: DSKF is not a stub and never was."),
    ("files",   "files",
     'FILES"HI.TXT":PRINT"[8]"',                     "stored",
     "NEEDS-DISK: " "the LISTING is the behaviour, and it is inside the compared "
     "text: the tail reads `HI      .TXT` then the marker, so a FILES that printed "
     "nothing, or named the wrong entry, fails on text even though the marker is "
     "there. Absent => syntax error => no marker at all."),
    ("lof",     "a=lof(1)",
     'OPEN"HI.TXT"FOR INPUT AS#1:A=LOF(1):CLOSE#1:PRINT"[";A;"]"', "stored",
     "NEEDS-DISK: " "26 — HI.TXT's exact length, which only a real directory walk "
     "produces; a stub reads 0."),
    ("eof",     "a=eof(1)",
     'OPEN"HI.TXT"FOR INPUT AS#1:A$=INPUT$(26,#1):A=EOF(1):CLOSE#1:PRINT"[";A;"]"', "stored",
     "NEEDS-DISK: " "-1 AFTER the whole file is consumed. 🔴 THE READ IS THE ROW: "
     "measured, EOF(1) is 0 on the same channel before the INPUT$ and -1 after, so "
     "this moves with the channel rather than answering a constant. A stub reads 0 "
     "— which is the BEFORE value, so the row had to be the after one."),
    ("bload",   'bload"x"',
     'POKE&HC000,7:BLOAD"PROG.BIN":A=PEEK(&HC000):PRINT"[";A;"]"', "stored",
     "NEEDS-DISK: " "PROG.BIN is a real BSAVE binary loading at $C000 whose first "
     "byte is $3E (62); the cell is poked to 7 first, so the row reads what the "
     "LOAD put there and not what was already in RAM."),
    # 🟢 D-KWTAPE2: THE LAST TWO WORDS OF THE DRAIN THAT HAD A MACHINE ANSWER.
    # Both waited on apparatus, and both blockers turned out to be real and then
    # to fall: `CLOAD` needed a tape mountable through the harness (`run_cases`
    # took `cassette=` only from D-CASORACLE on), and `CSAVE` needed the defect
    # that WAS its subject fixed first (D-CASTAIL2 -- until then a passing row
    # would have certified a tape no real MSX could load).
    ("cload",   'cload"zq"',  'CLOAD"ZQ"',  "direct",
     "NEEDS-TAPE: " "NOFURN: " "🎯 THE MACHINE'S OWN `Found:ZQ` IS THE WITNESS, "
     "printed as it reads: a hang and a silent no-op look identical at the `Ok` "
     "prompt, which is exactly how D-CASTAIL2 hid for four slices. Absent => "
     "syntax error."),
    # 🟢 D-KWINKEY: THE LAST WORD ON THE DRAIN, and its filed blocker was wrong.
    # `INKEY$` was held back as needing a HARNESS change — a key had to arrive
    # after the machine consumed `RUN` and before the statement read it, a moment
    # computed inside run_cases from `boot` + per-line `step` that a row cannot
    # see, with the D-LATCH/D-LATCH2 races as what such a change must not reopen.
    # 🎯 BUT A KEY DOES NOT HAVE TO BE TYPED TO BE WAITING. The BIOS type-ahead
    # buffer is ordinary MSX work area (KEYBUF $FBF0, the GETPNT/PUTPNT cursors,
    # empty when equal) and BASIC can POKE it: the program stuffs one character,
    # sets the cursors one apart, and reads a REAL keystroke with no injector
    # timing anywhere. Measured `[A 1 ]` on both machines
    # (scratchpad/kwdrain_inkeypoke.py) — and the value separates from a stub,
    # which answers `[ 0 ]` exactly as an unstuffed buffer does.
    # ⚠️ STORED, AND THAT IS LOAD-BEARING: in direct mode the harness delivers the
    # NEXT line through this very buffer, which would overwrite the stuffed
    # character. Nothing competes for it during RUN.
    ("inkey",   'a$=inkey$',
     'POKE&HFBF0,65:POKE&HF3FA,&HF0:POKE&HF3FB,&HFB:POKE&HF3F8,&HF1:'
     'POKE&HF3F9,&HFB:A$=INKEY$:PRINT"[";A$;LEN(A$);"]"',  "stored",
     "absent => the buffer stays stuffed and INKEY$ reads nothing; real => [A 1 ]"),
    ("csave",   'csave"zq"',  'PRINT"[Z9]":CSAVE"ZQ"',  "stored",
     "NEEDS-BLANKTAPE: " "NOFURN: " "🔴 THE ROW READS THE TAPE, NOT THE SCREEN, "
     "and that is measured: every screen form of this row scored SUPPORTED on an "
     "EMPTY capture (D-KWTAPE2) because CSAVE prints nothing and ends the program. "
     "The reading is the recording DECODED BACK TO BYTES -- header id, name and "
     "the program image with its 7-byte terminator, the very thing D-CASTAIL2 "
     "fixed. `[Z9]` on the screen half additionally says the program ran at all."),
    # 🎚️ D-KWT3 BATCH 1 — the TIER 3 rung: each row is a SECOND row for a keyword
    # that already has a happy-path one, scoring the error a 1985 magazine listing
    # would plausibly hit. The legend's own test picked them, one per error class.
    ("sqr_t3",  'a=sqr(-1)',   'PRINT SQR(-1)',        "direct",
     "PROVES-T3: " "Illegal function call on a bad ARGUMENT — the domain error, "
     "not a syntax one"),
    ("asc_t3",  'a=asc("")',   'PRINT ASC("")',        "direct",
     "PROVES-T3: " "Illegal function call on the EMPTY string, the classic "
     "off-by-one when a listing walks a string to its end"),
    ("left_t3", 'a$=left$(5,1)', 'PRINT LEFT$(5,1)',   "direct",
     "PROVES-T3: " "Type mismatch — a NUMBER where the string argument goes"),
    ("dim_t3",  'dim zz(2)',   'DIM ZZ(2):ZZ(9)=1',    "direct",
     "PROVES-T3: " "Subscript out of range, the commonest array fault of all"),
    ("read_t3", 'read zv',     'READ ZV',              "direct",
     "PROVES-T3: " "Out of DATA — a READ with no DATA statement anywhere"),
    # 🎚️ D-KWT3 BATCH 2 — same filter: the error a 1985 listing would plausibly
    # hit. Batch 1's READ row found a TIER 1 defect, so these are written to
    # DISAGREE if they can, not to confirm.
    ("chr_t3",  'a$=chr$(256)', 'PRINT CHR$(256)',      "direct",
     "PROVES-T3: " "Illegal function call past the byte range — the classic "
     "off-by-one on a character loop"),
    ("mid_t3",  'a$=mid$("ab",0)', 'PRINT MID$("AB",0)', "direct",
     "PROVES-T3: " "Illegal function call on a ZERO start position, where BASIC "
     "counts from 1"),
    ("log_t3",  'a=log(0)',    'PRINT LOG(0)',          "direct",
     "PROVES-T3: " "Illegal function call on the domain edge, not a maths result"),
    ("str_t3",  'a$=string$(300,"a")', 'PRINT STRING$(300,"A")', "direct",
     "PROVES-T3: " "past the 255-character string limit"),
    ("goto_t3", 'goto 9999',   'GOTO 9999',             "direct",
     "PROVES-T3: " "Undefined line number — the commonest fault in a mistyped "
     "listing"),
    ("next_t3", 'next',        'NEXT',                  "direct",
     "PROVES-T3: " "NEXT without FOR"),
    ("ret_t3",  'return',      'RETURN',                "direct",
     "PROVES-T3: " "RETURN without GOSUB"),
    # 🎚️ D-KWT3 BATCH 3. The display verbs (SCREEN/COLOR/WIDTH/LOCATE) are held
    # back deliberately: their happy rows already need NOFURN/NOECHO because they
    # destroy the echo anchor, and an error row on top of that is two apparatus
    # questions at once. CLEAR is held back for the other reason — a row that
    # resets the variable world can eat the cases after it (mode 5).
    ("instr_t3", 'a=instr(0,"ab","a")', 'PRINT INSTR(0,"AB","A")', "direct",
     "PROVES-T3: " "Illegal function call on a ZERO start position"),
    ("poke_t3", 'poke 70000,0', 'POKE 70000,0',        "direct",
     "PROVES-T3: " "past the 16-bit address space"),
    ("peek_t3", 'a=peek(70000)', 'PRINT PEEK(70000)',  "direct",
     "PROVES-T3: " "the same overflow on the reading side"),
    ("sgn_t3",  'a=sgn("a")',  'PRINT SGN("A")',       "direct",
     "PROVES-T3: " "Type mismatch — a STRING where the number goes"),
    ("abs_t3",  'a=abs("a")',  'PRINT ABS("A")',       "direct",
     "PROVES-T3: " "Type mismatch on the commonest numeric function of all"),
    ("rest_t3", 'restore 9999', 'RESTORE 9999',        "direct",
     "PROVES-T3: " "Undefined line number — RESTORE to a line that is not there"),
    ("erase_t3", 'erase zq9',  'ERASE ZQ9',            "direct",
     "PROVES-T3: " "erasing an array that was never DIMmed"),
    ("swap_t3", 'swap zq9,zq8$', 'SWAP ZQ9,ZQ8$',      "direct",
     "PROVES-T3: " "Type mismatch — swapping a number with a string"),
    ("space_t3", 'a$=space$(300)', 'PRINT SPACE$(300)', "direct",
     "PROVES-T3: " "past the 255-character string limit"),
    # 🎚️ D-KWT3 BATCH 4. Non-disk rows only, so the batch stays fast enough to
    # read every value; the disk-rig error rows are a batch of their own.
    ("len_t3",  'a=len(5)',    'PRINT LEN(5)',         "direct",
     "PROVES-T3: " "Type mismatch — a NUMBER where the string goes"),
    ("hex_t3",  'a$=hex$("a")', 'PRINT HEX$("A")',     "direct",
     "PROVES-T3: " "Type mismatch on the conversion functions"),
    ("oct_t3",  'a$=oct$("a")', 'PRINT OCT$("A")',     "direct",
     "PROVES-T3: " "the same, and its sibling is the control"),
    ("int_t3",  'a=int("a")',  'PRINT INT("A")',       "direct",
     "PROVES-T3: " "Type mismatch on the commonest rounding function"),
    ("exp_t3",  'a=exp(1000)', 'PRINT EXP(1000)',      "direct",
     "PROVES-T3: " "Overflow — the domain edge a compound-interest listing hits"),
    ("vpoke_t3", 'vpoke 20000,0', 'VPOKE 20000,0',     "direct",
     "PROVES-T3: " "past the 16 KB VRAM of an MSX1"),
    ("sound_t3", 'sound 20,0', 'SOUND 20,0',           "direct",
     "PROVES-T3: " "past the PSG's 14 registers"),
    ("fn_t3",   'a=fnzz(1)',   'PRINT FNZZ(1)',        "direct",
     "PROVES-T3: " "calling a function no DEF FN ever defined"),
    # 🎚️ D-KWT3 BATCH 5 — the DISK error rows, kept to four because the rig's
    # timings make them the slowest in the sweep. The bad-file-number class is
    # deliberately absent: badfnum-acceptance already owns it, and a row that
    # duplicates a suite adds cost without adding evidence.
    ("kill_t3", 'kill"nosuch.bas"', 'KILL"NOSUCH.BAS"', "direct",
     "NEEDS-DISK: " "PROVES-T3: " "File not found — the error a listing hits when "
     "the data disk is not the one in the drive"),
    ("cvi_t3",  'a=cvi("a")',  'PRINT CVI("A")',       "direct",
     "NEEDS-DISK: " "PROVES-T3: " "CVI wants two bytes and got one"),
    ("mki_t3",  'a$=mki$("a")', 'PRINT MKI$("A")',     "direct",
     "NEEDS-DISK: " "PROVES-T3: " "Type mismatch — MKI$ converts a NUMBER"),
    ("dskf_t3", 'a=dskf(9)',   'PRINT DSKF(9)',        "direct",
     "NEEDS-DISK: " "PROVES-T3: " "a drive letter that does not exist"),
    # 🎚️ D-KWBREADTH BATCH 1 — the OTHER half of establishing a tier. A keyword
    # with one agreeing row has one agreement point; these cover a verb's FORMS.
    # ⚠️ Every reading here is a VALUE, not an error (silent-failure mode 6, learned
    # from PAD: a row reading an ERROR cannot tell a working feature from a
    # differently-failing one), and no reading is 0 on both sides, which would
    # merely trade mode 6 for mode 2.
    ("sgn_b",   'a=sgn(-5)',   'PRINT"[";SGN(-5);SGN(0);SGN(5);"]"',   "direct",
     "BREADTH: all THREE branches of the sign test in one reading — a row that "
     "took only SGN(5) would pass on an implementation that never returns -1"),
    ("fix_b",   'a=fix(-2.7)', 'PRINT"[";FIX(-2.7);FIX(2.7);"]"',      "direct",
     "BREADTH: truncation toward zero on BOTH signs — the half a single positive "
     "argument cannot see, and where FIX and INT differ"),
    ("cos_b",   'a=cos(0)',    'PRINT"[";COS(0);"]"',                  "direct",
     "BREADTH: the exact point of the cosine, 1 — a value reading, and not 0"),
    ("vpoke_b", 'vpoke 16383,7', 'VPOKE 16383,7:PRINT"[";VPEEK(16383);"]"', "stored",
     "BREADTH: the LAST byte of an MSX1's 16 KB VRAM, where the existing row uses "
     "address 0 — an off-by-one in the address path shows here and nowhere else"),
    ("vpoke_b2", 'vpoke 100,255', 'VPOKE 100,255:PRINT"[";VPEEK(100);"]"', "stored",
     "BREADTH: the maximum byte VALUE, where the existing row writes 9. ⚠️ STORED "
     "BECAUSE IT PASSED ALONE AND FAILED IN COMPANY: at 37 chars it clears the "
     "38-column guard, yet the reference's capture wraps (`|[ 255 ]`) and zerobas "
     "lost its echo anchor entirely once other rows had run before it. The guard "
     "measures the TYPED line; what wraps is the line plus whatever the screen "
     "already holds."),
    ("close",   "close",
     'OPEN"W.TXT"FOR OUTPUT AS#1:PRINT#1,"ABC":CLOSE#1:OPEN"W.TXT"FOR INPUT AS#1:A=LOF(1):CLOSE#1:PRINT"[";A;"]"', "stored",
     "NEEDS-DISK: " "the FLUSH is the readback: 6 bytes are on the disk only because "
     "the channel was closed. 🔴 THE BLIND SHAPE WAS MEASURED — the same row with "
     "the CLOSE removed reads 0, not an error, because zerobas allows #1 to be "
     "reopened; a `reopen succeeds` row would have passed without the close."),
    ("bsave",   'bsave"x",0,1',
     'POKE&HC800,99:BSAVE"O.BIN",&HC800,&HC800:POKE&HC800,7:BLOAD"O.BIN":A=PEEK(&HC800):PRINT"[";A;"]"', "stored",
     "NEEDS-DISK: " "a ROUND TRIP through the disk: save 99, overwrite the cell with "
     "7, load it back, read 99. A BSAVE that wrote nothing leaves 7."),
    ("save",    'save"x"',
     'A=1:SAVE"S.BAS":OPEN"S.BAS"FOR INPUT AS#1:A=LOF(1):CLOSE#1:PRINT"[";A;"]"', "stored",
     "NEEDS-DISK: " "the saved program's own length, read back through a channel: 68 "
     "on BOTH machines, which also says the tokenised on-disk form agrees byte for "
     "byte. A SAVE that wrote nothing leaves no file and the OPEN raises."),
    ("kill",    'kill"x"',
     'A=DSKF(1):KILL"PROG2.BAS":B=DSKF(1):PRINT"[";B-A;"]"', "stored",
     "NEEDS-DISK: " "the FREED SPACE is the behaviour — 1 KB back after the file "
     "goes, so a KILL that merely parsed reads 0. The victim is PROG2.BAS, which no "
     "other row in this sweep opens."),
    ("merge",   'merge"x"',
     'OPEN"N.BAS"FOR OUTPUT AS#1:PRINT#1,"100 END":CLOSE:PRINT"[M0]":MERGE"N.BAS":PRINT"[M1]"', "stored",
     "NEEDS-DISK: " "MERGE RETURNS TO COMMAND LEVEL, so the row reads `[M0]` and "
     "NOT `[M1]`: the marker before it proves the statement stream got there, the "
     "absent one after it is the behaviour. 🔴 THE `[M0]` IS WHY THIS IS NOT AN "
     "EMPTY-TAIL ROW. Until D-MERGERET it read DIVERGENT with `[M1]` on the zb side; "
     "green at `` on both would have been agreement with nothing named, and a "
     "regression would print `[M0]|[M1]` here [[an-unnamed-outcome-reads-as-no-outcome]]. "
     "What the row still cannot see is that the merge LANDED — that is unobservable "
     "inside one case precisely because the statement after it never runs, and "
     "scratchpad/kwdrain_mergechk.out reads `LIST 100` on both machines instead."),
    ("lset",    'lset a$="x"',
     'OPEN"R.DAT"AS#1:FIELD#1,4 AS A$:LSET A$="B":A=ASC(A$):CLOSE#1:PRINT"[";A;"]"', "stored",
     "NEEDS-DISK: " "LEFT justification inside a FIELDed buffer: 66 = ASC(\"B\") in "
     "byte 1. Its pair `rset` reads 32 in the same byte, so the two rows separate "
     "from each other and not merely from a stub."),
    ("rset",    'rset a$="x"',
     'OPEN"R.DAT"AS#1:FIELD#1,4 AS A$:RSET A$="B":A=ASC(A$):CLOSE#1:PRINT"[";A;"]"', "stored",
     "NEEDS-DISK: " "RIGHT justification: byte 1 is a SPACE (32), not the \"B\" that "
     "`lset` puts there."),
    # ------------------------------------------------ D-KWINP (2026-09-13)
    # 🟢 `INPUT` IS THE SECOND WORD IN THIS LIST FOR ITS NAME RATHER THAN A GAP,
    # after `GET`. It sat with `INKEY$` as though it shared the keyboard blocker;
    # `INPUT #n, var` reads a FILE and needs no keystroke at all. The fixture's own
    # `HI.TXT` holds `Hello from zerobas-disk!` + CRLF, so the length is 24 on both
    # machines and the same row with the `INPUT#` removed reads 0
    # (scratchpad/kwdrain_inputauto2.out).
    # ⚠️ THE KEYBOARD FORM IS STILL UNSCORED and this row does not pretend
    # otherwise — `INPUT "prompt";A$` blocks, and that is the injector-timing
    # group's problem, shared with `INKEY$`.
    ("inputkw",  "input#1,a$",
     'OPEN"HI.TXT"FOR INPUT AS#1:INPUT#1,A$:CLOSE#1:PRINT"[I";LEN(A$);"]"',
     "stored",
     "NEEDS-DISK: " "the FILE form: 24 = the fixture line's length, 0 without it"),
    ("input_b",  "input#1,a$",
     'OPEN"HI.TXT"FOR INPUT AS#1:INPUT#1,A$:CLOSE#1:PRINT"[";LEFT$(A$,5);"]"',
     "stored",
     "NEEDS-DISK: " "the BYTES, not the COUNT. `inputkw` scores LEN(A$)=24, which "
     "a read returning 24 BLANKS passes just as well as the real line; HI.TXT is "
     "\"Hello from zerobas-disk!\" (tools/make_test_dsk.py), so this reads Hello."),

    # ------------------------------------------------ D-KWGET (2026-09-13)
    # 🟢 `GET` IS NOT A KEYBOARD VERB, and the name is the whole reason it sat
    # unattributed: MSX1's `GET` is the RANDOM-FILE record read (`GET #n[,record]`).
    # `PUT` already ships and the disk rig is mounted, so the round trip fits one
    # row — and the BLIND SHAPE is inside the same reading rather than beside it.
    # 🔴 THE BUFFER IS OVERWRITTEN BETWEEN THE PUT AND THE GET, and BOTH values are
    # printed: 90 is the "Z" that overwrote it, 66 is the "B" the GET brought back
    # off the disk. A `GET` that parsed and did nothing reads `90 90` — measured,
    # that is exactly what the same row without the GET gives on both machines
    # (scratchpad/kwdrain_getcall.out).
    ("getkw",    "get#1,1",
     'OPEN"R.DAT"AS#1:FIELD#1,4 AS A$:LSET A$="B":PUT#1,1:LSET A$="Z":A=ASC(A$):GET#1,1:B=ASC(A$):CLOSE#1:PRINT"[G";A;B;"]"',
     "stored",
     "NEEDS-DISK: " "a PUT/GET round trip through a FIELDed record: 90 then 66, "
     "where a GET that did nothing reads 90 then 90."),
    # 🔴 `CALL` SCORES RESERVEDNESS AND NOTHING MORE, and that limit is the row.
    # The obvious form is blind: `CALL ZZQ`, bare `CALL` and the ABSENT-keyword
    # shape `ZZQQ ZZQ` ALL answer `Syntax error` on zerobas, the CF-3300 and the
    # VG-8020 alike, so an unknown extension cannot separate a machine that has
    # the verb from one that does not. What separates them is D-DONOTHING3's
    # trick: a RESERVED word cannot be a variable. `CALL=1` is a Syntax error on
    # all three machines while the stub shape `ZZQQ=1` assigns and prints
    # (scratchpad/kwdrain_callres.out).
    # ⚠️ SO THE ROW CANNOT SEE WHETHER ANY EXTENSION WORKS. The two that exist on
    # this hardware are `CALL SYSTEM` and `CALL FORMAT` — one exits to DOS and one
    # formats the disk — so neither is invokable from a sweep, and saying that is
    # better than a row that passes for the wrong reason
    # [[a-case-that-agrees-can-agree-for-the-wrong-reason]].
    # 🎯 NOT A DISK ROW: `CALL` is reserved on the diskless VG-8020 too, which is
    # what makes the VG-8020 its proper oracle.
    ("callkw",   "call zzq",  'CALL=1:PRINT"[C1]"',   "stored",
     "D-KWGET: reservedness only — Syntax error on all three machines where the "
     "stub shape assigns and prints"),

    # 🎯 `runkw` IS NOT A DISK ROW and is deliberately not tagged: `RUN` is plain
    # MSX BASIC and the VG-8020 is its proper oracle. It sat in "no known gap"
    # because RUN CLEARS VARIABLES, so no expression can carry a count across the
    # restart — the flag has to live in RAM, and $E001 is the cell next to the one
    # `pokekw` already writes. Pass 1 increments 0 -> 1 and takes the branch; pass 2
    # increments to 2 and prints it. A RUN that did nothing prints 1.
    # ⚠️ `RUN 20` NAMES A LINE `as_stored` CHOSE. The packing was printed before the
    # row was written (10 POKE 0 / 20 increment / 30 IF..THEN RUN 20 / 40 PRINT),
    # and it is the same dependence the `gosub` and `resume` rows already carry.
    ("runkw",   "run 20",
     'POKE&HE001,0:POKE&HE001,PEEK(&HE001)+1:IF PEEK(&HE001)<2 THEN RUN 20:PRINT"[";PEEK(&HE001);"]"',
     "stored", "D-KWDISK"),

    # --------------------------------- D-KWDISK, the pre-existing rows (2026-09-12)
    # Disk-BASIC surface, EXECUTED at last. Every "needs a disk fixture" note
    # below was true of the probe, not of the tree: the fixture has existed and
    # been mounted by other gates for months, and this file simply never named
    # it. The rows now run against a private copy of disk/test720.dsk on BOTH
    # sides (see DISK_TEST_DSK), so the reference and zerobas hold the SAME disk.
    # 🎯 ORDER IS PART OF THE ROW SET, not presentation: `dsko` rewrites the first
    # byte of the root directory and `kill` deletes a file, so every row that
    # READS the fixture is placed ahead of every row that changes it, and the two
    # sides walk the identical sequence [[apparatus-is-part-of-the-measurement]].
    # 🔴 STORED MODE THROUGHOUT, and not for width: a DIRECT-mode `BLOAD` eats the
    # rest of its line (measured — `BLOAD"PROG.BIN":A=PEEK(&HC000):PRINT…` printed
    # nothing at all), so the readback has to be on a LATER numbered line. The
    # packing is `as_stored`'s, checked before each row was written.
    ("dski",    'a$=dski$(0,0)',
     'A$=DSKI$(0,7):B=PEEK(&HF351)+256*PEEK(&HF352):A=PEEK(B):PRINT"[";A;"]"', "stored",
     "NEEDS-DISK: " "raw sector READ: sector 7 is the root directory, whose first "
     "entry is TEST.BIN, so the buffer's first byte is ASC(\"T\") = 84. The buffer "
     "ADDRESS is read through $F351 rather than pinned — it is $EB95 on the "
     "CF-3300 and $E5C0 on zerobas BY DESIGN (docs/spec-basic-dskio.md). Control: "
     "the same read WITHOUT the DSKI$ gives 254, so the row moves."),
    ("dsko",    "dsko$0,0",
     'A$=DSKI$(0,7):B=PEEK(&HF351)+256*PEEK(&HF352):POKE B,88:DSKO$0,7:A$=DSKI$(0,0):A$=DSKI$(0,7):A=PEEK(B):PRINT"[";A;"]"', "stored",
     "NEEDS-DISK: " "raw sector WRITE, and it is a ROUND TRIP: poke the buffer to "
     "\"X\", write sector 7, read a DIFFERENT sector to flush the buffer, read 7 "
     "back. 88 only if the bytes reached the disk. DESTRUCTIVE to the root "
     "directory, which is why it is the LAST reading row in this block."),
    ("copy",    'copy"a:x"to"a:y"',
     'COPY"HI.TXT" TO "H2.TXT":OPEN"H2.TXT"FOR INPUT AS#1:A=LOF(1):CLOSE#1:PRINT"[";A;"]"', "stored",
     "NEEDS-DISK: " "the COPY's own length read back through a channel: 26, HI.TXT's "
     "size. A COPY that created an empty file reads 0."),
    ("set",     'set password',  "SET PASSWORD", "stored",
     "NEEDS-DISK: " "ERR 5 on every machine with a disk ROM and on the diskless "
     "VG-8020 too (D-DONOTHING3) — the handler refuses ON SIGHT. That IS the "
     "differential: an absent SET parses `SET PASSWORD` as a variable and a name, "
     "which is a Syntax error, not an Illegal function call."),
    ("attr",    'a$=attr$(0)',   None, "direct", "NEEDS-DISK: " "MSX-DOS2-era; measured for the record"),
    ("ipl",     "ipl",           "IPL", "stored",
     "NEEDS-DISK: " "MEASURED, not assumed to be destructive: `IPL` is Illegal "
     "function call on the CF-3300 as well as on zerobas — the boot-sector write "
     "the old note feared needs MSX-DOS2, and this machine refuses the word on "
     "sight. Same Syntax-error differential as `set`."),
    ("cmd",     'cmd"x"',        'CMD"X"',      "stored",
     "NEEDS-DISK: " "the third refuse-on-sight word; ERR 5 on both references."),
    # 🟢 THE FIRST TWO-TAG ROW, and D-DFEND is what earned it: `LFILES` walks a
    # DISK and prints to a PRINTER, which is why `_row_rigs` returns a tuple.
    # 🎯 AND IT HOLDS THE GROUND A FIX WON. `LFILES` did not zero LPTPOS, so with
    # the head PARKED mid-line this read 2 where the CF-3300 read 0 (and R-LP16
    # then put two extra bytes on the printer). Closing that item would hand the
    # keyword straight back to the unattributed pile -- attribution comes from OPEN
    # items -- so the row carries the defect's own shape
    # [[a-row-written-off-as-out-of-scope-leaves-the-bookkeeping]].
    # ⚠️ THE `LPRINT` IS NOT DECORATION: with the head already at 0, LPOS reads 0
    # whether or not LFILES touches it, which is the blind row this replaced.
    ("lfiles",  "lfiles",
     'LPRINT"AB";:LFILES:PRINT"[P";LPOS(0);"]"',     "stored",
     "NEEDS-DISK: " "NEEDS-PRINTER: " "the printer head goes back to column 0 "
     "because every entry ended its own line -- 0 on both machines since D-DFEND, "
     "2 before it. A no-match LFILES must NOT zero it (both machines leave the "
     "head parked and let R-LP16 flush), which is why the store is conditional."),
    ("loc",     "a=loc(1)",
     'OPEN"HI.TXT"FOR INPUT AS#1:A$=INPUT$(10,#1):A=LOC(1):CLOSE#1:PRINT"[";A;"]"', "stored",
     "NEEDS-DISK: " "26 on BOTH machines — LOC answers in BYTES here, and it "
     "answers the same after 10 bytes as after none, so the row scores the "
     "FUNCTION and not a position. An absent LOC auto-dims an array and reads 0."),
    ("bin",     "a$=bin$(5)",
     'PRINT"[";BIN$(5);"]"',                         "direct",
     "absent => syntax error; real => 101"),

    # Keyboard INPUT$(n) — blocks for n keypresses. Crunch-only; the channel form
    # INPUT$(n,#f) already ships.
    ("inputdol", 'a$=input$(1)', None, "direct", "BLOCKS waiting for a keypress"),

    # ========================================================================
    # 🔴 `auto` IS LAST IN THIS LIST AND MUST STAY LAST. IT IS NOT SORTED HERE,
    # IT IS PLACED HERE. `AUTO` leaves the machine in LINE-ENTRY MODE, which
    # swallows whatever is typed next: when it sat mid-list it scored ITSELF
    # correctly and took TWENTY-ONE unrelated rows down with it (D-KWDRAIN step
    # 4j, DIVERGENT=22 + UNREADABLE=1, all but one pure collateral). Anything
    # appended after this line inherits that [[apparatus-is-part-of-the-measurement]].
    # 🟢 AND THE FILED BLOCKER WAS THE POISONING, WHICH POSITION SOLVES. What
    # actually stood in the way is that line-entry mode prints NO CLOSING PROMPT,
    # so the ordinary tail runs to the bottom of the screen and collects the
    # CF-3300's function-key display — hence `NOFURN:` and `screen_tail_nofurn`.
    # 🎯 THE READING IS THE LINE-ENTRY PROMPT ITSELF: both machines answer `100`,
    # the number AUTO was asked to start at. An absent `AUTO` parses `AUTO 100` as
    # a name followed by a number and answers `Syntax error`; an `AUTO` that
    # parsed and did nothing prints no prompt at all.
    # ========================================================================
    ("auto",    "auto 100",     "AUTO 100",     "stored",
     "NOFURN: " "the line-entry prompt `100` on both machines. LAST ROW BY "
     "PLACEMENT: it leaves the machine in line-entry mode, which eats whatever "
     "follows."),
]

# Rows deliberately not executed, with the reason surfaced in the report. Named
# explicitly so a reader can audit the exclusions instead of inferring them from
# a silent absence (no-silent-caps).
SKIP_EXEC = {k for k, _, ex, _, _ in SWEEP if ex is None}

# --------------------------------------------------------------------------
# --- CRUNCH_DIFF_PINNED: the keywords zerobas does not tokenise ------------
# 🔴 UNTIL 2026-09-07 THE CRUNCH LAYER SCORED NOTHING AT ALL. `main()`
# returned 0 unless the ROMs moved mid-run or the CONTROL GROUP failed, so this
# file — collected by `make gates`, green in the 114/114 battery of that morning
# — printed EIGHT words the reference tokenises and zerobas does not, and exited
# 0. Layer 1's states are SAME/DIFF; `MISSING` is a LAYER 2 state, and all eight
# are crunch-only rows that Layer 2 never runs. **A word absent from
# `kwtable.inc` that is also crunch-only was structurally incapable of being
# scored** [[a-coverage-row-whose-geometry-cannot-reach-the-case]].
#
# 🎯 AND THE "NO-ORACLE" REASONING DOES NOT REACH THIS LAYER. The rows are
# tagged NEEDS-DISK because their SUPPORT oracle is a disk-equipped reference;
# the probe declines to attribute a support difference to zerobas. Tokenising
# needs no disk. The reference's bytes are right there, the difference is
# unambiguous (a single token vs the raw ASCII of a variable name), and it IS
# attributable.
#
# The values are ORACLE-SOURCED — read out of the reference's own program area by
# this probe's Layer 1, the same provenance as every token in kwtable.inc.
# 🟢 ATTR$ ($E9) LEFT THIS SET on 2026-09-08 too (D-ATTRFN) — the same class, but
# a FUNCTION, so its handler is an `ev_f` arm and not a stmt_table row. Measured on
# four sides: `PRINT ATTR$` / `A$=ATTR$` / `A$=ATTR$(0)` are ERR 5 and `ATTR$="Z"`
# is ERR 2, both references agreeing, and zerobas now matches all four.
# 🟢 SET ($D2), IPL ($D5) and CMD ($D7) LEFT THIS SET on 2026-09-08 (D-DONOTHING3):
# zerobas now crunches all three and dispatches them to `gb_illegal`, so they read
# SAME. A pinned row that stops diverging is a STALE PIN and this probe returns 5
# on one, which is what removing them here answers.
# 🔴 AND THEY WERE NEVER DISK-BASIC WORDS. This block sat under a Disk-BASIC
# heading and the fix was filed as needing a disk-equipped oracle; measured, the
# DISKLESS VG-8020 answers ERR 5 to `SET`, `IPL`, `CMD` AND to `SET=1` -- so all
# three are reserved in plain MSX BASIC and the VG-8020 is a perfectly good oracle
# for them (scratchpad/donothing_probe.py, four sides).
CRUNCH_DIFF_PINNED = {
}
# 🎯 `LFILES` IS THE CONTROL THAT MAKES THIS A LIST AND NOT A CLASS: it is
# a Disk-BASIC word too, it IS in kwtable.inc, and it crunches SAME. So "zerobas
# omits Disk BASIC's keywords" is not the finding — these eight specific words
# are.


# 🔴 EVERY ENTRY MUST STAY LOWERCASE. `classify` below does `low = tail.lower()`
# and then `phrase in low`, so a capitalised entry can NEVER match -- it does not
# fail loudly, it silently reclassifies that row from `error:<phrase>` to
# `value`, which reads as "the keyword ran and printed something".
# ⚠️ D-MSGEXACT nearly broke exactly this. A tree-wide sweep that capitalised
# message literals hit seven of these, because they LOOK like the message
# expectations it was updating. They are not: this is a CLASSIFIER vocabulary,
# not an assertion, and it is deliberately case-insensitive.
# The original reason for lowercasing -- zerobas's own lowercase wording being a
# documented divergence -- is GONE (D-MSGEXACT made every message the
# reference's verbatim text). The lowercasing stays anyway: the CLASS is the
# comparable thing here, and a classifier that is insensitive to case cannot be
# broken by a future wording change.
ERROR_WORDS = (
    "syntax error", "type mismatch", "overflow", "illegal function call",
    "out of memory", "undefined line", "subscript out of range",
    "division by zero", "redimensioned array", "missing operand",
    "illegal direct", "nexus", "bad file", "file not found", "disk offline",
    "device i/o error", "not found", "error",   # bare "error" LAST: catch-all
)


def tokens(raw: str | None) -> bytes | None:
    """Body tokens from a stored_line capture — the bytes after the 4-byte
    header (link + line number). None when the line was never stored (a crunch
    that errored on entry leaves the program empty)."""
    if not raw:
        return None
    b = bytes.fromhex(raw)
    return b[4:] if len(b) >= 5 else None


def marker_tail(raw: str | None, marker: str) -> str | None:
    """Rows from the one carrying `marker` to the closing prompt, '|'-joined.

    🔴 THE ECHO-FREE CAPTURE, AND WHY IT HAS TO EXIST (D-KWDRAIN step 4a).
    `screen_tail` anchors on the ECHOED COMMAND, which is why every row in this
    sweep had to leave the display alone: `CLS`, `SCREEN`, `WIDTH` and `COLOR`
    erase or move the echo, so the capture reported ?noecho and the word could
    never be attributed at all. I filed that as "these words cannot take a
    kwsweep row" -- WRONG: it was this probe's choice of anchor, not a limit.
    Other suites (arrays, deffn) have always run `CLS:PRINT"[";...` and read the
    bracketed marker straight off the screen.
    ⚠️ THE MARKER MUST BE UNIQUE PER ROW. Without the echo there is nothing to
    prove the text came from THIS case rather than surviving from the last one,
    so each NOECHO row prints its own tag and this function matches that tag --
    a stale screen then reads as ?nomarker, which is a refusal, not a pass.
    """
    if raw is None:
        return None
    rows = [raw[r * omsx_repl.COLS:(r + 1) * omsx_repl.COLS].strip()
            for r in range(omsx_repl.ROWS)]
    # 🔴 THE **LAST** MATCHING ROW, NOT THE FIRST, AND THAT COST A ROW TO LEARN.
    # The exec line prints the marker, so the marker text is also inside the
    # ECHOED COMMAND. On a machine whose echo SURVIVES the row's own feature
    # (`WIDTH 37` reformats but does not clear on the reference) a first-match
    # anchored on the echo and captured the command plus the answer, while the
    # side whose echo was gone captured the answer alone -- and the row came back
    # DIVERGENT with BOTH sides having printed `[W 37 ]`. The output always
    # follows the echo, so the last match is the answer on both.
    idx = next((i for i in range(len(rows) - 1, -1, -1) if marker in rows[i]), None)
    if idx is None:
        return None
    out: list[str] = []
    for r in rows[idx:]:
        if r in omsx_repl.PROMPTS:
            break
        out.append(r)
    while out and out[-1] == "":
        out.pop()
    return "|".join(out)


def screen_tail_nofurn(raw: str | None, cmdline: str) -> str | None:
    """`screen_tail` with the LAST screen row discarded.

    🔴 THE LAST ROW IS MACHINE FURNITURE, NOT OUTPUT, and only one row has ever
    needed to say so: `AUTO` leaves the machine in LINE-ENTRY MODE, which never
    prints a closing prompt — so the ordinary tail runs to the bottom of the
    screen and collects the CF-3300's FUNCTION-KEY DISPLAY, which zerobas does not
    show. The row then reads DIVERGENT for a machine-configuration reason, exactly
    like the `FILES`/`CSRLIN` row this sweep already threw away
    [[readout-blind-to-its-own-subject]].
    🎯 `basic_probe_lptverb.screen_rows` DOES THE SAME `[:-1]` FOR THE SAME
    REASON, in its own words: "Row 24 is the SCREEN-0 function-key display, which
    both references show and zerobas does not; left in, every row would diverge for
    a reason unrelated to the subject."
    ⚠️ POSITION, NEVER CONTENT. The obvious rule — drop a row that reads
    `color auto goto list run` — is wrong here: this sweep's own `keykw` row
    REWRITES that line to `ZZQ auto goto list run`.
    ⚠️ AND IT IS KWSWEEP-LOCAL ON PURPOSE. `omsx_repl.screen_tail` is a shared
    leaf; one row does not justify changing what every other probe reads. The echo
    anchor is still the harness's own `_echo_idx`, so the two differ in the row set
    and in nothing else."""
    if raw is None:
        return None
    rows = [raw[r * omsx_repl.COLS:(r + 1) * omsx_repl.COLS].strip()
            for r in range(omsx_repl.ROWS)][:-1]
    idx = omsx_repl._echo_idx(rows, cmdline)
    if idx is None:
        return None
    out: list[str] = []
    for r in rows[idx + 1:]:
        if r in omsx_repl.PROMPTS:
            break
        out.append(r)
    while out and out[-1] == "":
        out.pop()
    return "|".join(out)


def printer_text(raw: str | None) -> str:
    """The PRINTER half of a `screen_printer` capture, with CR and LF VISIBLE.

    The framing is part of the answer -- `X\\r\\n` is the rule and `X` is not --
    so it may not be stripped. Same decode as `basic_probe_lptverb.prn_reading`.
    ⚠️ THE SEPARATOR IS THE FIRST `7c` (a literal `|` byte), so a SCREEN that
    contains the two characters `7c` would split in the wrong place. No row here
    types them, and the lptverb suite has relied on the same rule since D-EDITVERB."""
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


def classify(raw: str | None, cmdline: str,
             marker: str | None = None,
             log: bool | str = False, nofurn: bool = False) -> tuple[str, str]:
    """(outcome_class, text) for one executed case.

    class is "value" (ran, printed something), "error:<phrase>", or "?<reason>".
    Comparing the CLASS first is what makes the sweep readable across zerobas's
    lowercase error wording.

    `marker` selects the echo-free capture for rows whose own feature destroys
    the echo -- see marker_tail.

    🔴 `log` IS THE ROW SAYING WHICH HALF IT SCORES, and a `screen_printer`
    capture has two. The CLASS still comes from the SCREEN -- a keyword the
    machine does not have answers `Syntax error` there and prints nothing at all,
    which is the differential -- while the TEXT compared becomes the printer log.
    Scoring the screen half of a log row would compare two blank screens and call
    it agreement [[an-unnamed-outcome-reads-as-no-outcome]]."""
    if log == "tape":
        # The screen says the program RAN (its class), the tape says what CSAVE
        # actually wrote (the text compared) -- the same division of labour as a
        # printer-log row, minus the hex, because this capture is not hex.
        screen, _, tape = (raw or "").partition(TAPE_MARK)
        cls, _ = classify(screen, cmdline, marker, log=False, nofurn=nofurn)
        if cls.startswith("?"):
            return (cls, "")
        return (cls, tape or "<no tape reading>")
    if log:
        # 🔴 BOTH HALVES OF A `screen_printer` CAPTURE ARE HEX, including the
        # screen one -- `__hex_v` does not come back decoded the way a plain
        # "screen" capture does. The first cut passed the raw half straight to
        # screen_tail and every row read `?noecho` on BOTH sides, which is
        # UNREADABLE and therefore honest, but only because the guard existed:
        # with the echo anchor gone there is nothing to compare and two blank
        # readings would otherwise have agreed [[an-unnamed-outcome-reads-as-no-outcome]].
        # (`basic_probe_lptverb.py` never hits this: its screen batteries take the
        # DEFAULT capture and only its printer battery takes this one.)
        half, _, _ = raw.partition("7c") if raw is not None else ("", "", "")
        try:
            screen = bytes.fromhex(half).decode("latin-1") if half else ""
        except ValueError:
            screen = ""
        cls, txt = classify(screen or None, cmdline, marker)
        if cls.startswith("?") or cls.startswith("error"):
            return (cls, txt)
        return ("value", printer_text(raw))
    if marker is not None:
        tail = marker_tail(raw, marker)
        if tail is None:
            return ("?nomarker", "")
    else:
        tail = (screen_tail_nofurn if nofurn else omsx_repl.screen_tail)(raw, cmdline)
        if tail is None:
            return ("?noecho", "")
    low = tail.lower()
    for phrase in ERROR_WORDS:
        if phrase in low:
            return (f"error:{phrase}", tail)
    return ("value", tail)


def verdict(ref_cls: str, ref_txt: str, zb_cls: str, zb_txt: str,
            crunch_state: str | None) -> str:
    """The six-way call described in the module header.

    `crunch_state` ("SAME"/"DIFF"/None) is what separates SILENT-GAP from a
    plain DIVERGENT: when NEITHER side errors, the answers still differ, AND
    zerobas failed to tokenise the word, the word is being parsed as an ordinary
    variable/array — the TIME / TAB( shape, the failure mode this whole probe
    exists to catch. That inference needs BOTH layers, which is why the support
    pass runs after the crunch pass rather than standalone."""
    if ref_cls.startswith("?") or zb_cls.startswith("?"):
        return "UNREADABLE"
    ref_err = ref_cls.startswith("error")
    zb_err = zb_cls.startswith("error")
    # A DIFF crunch is a DEFINITIVE fact: zerobas did not tokenise the word, so
    # whatever it did instead was a variable/array parse. When it then declines to
    # error, that is a silent wrong answer NO MATTER what the reference did —
    # including when the reference itself refused the case (MKS$/MKD$ on a
    # diskless VG-8020). Checking this before the ref-vs-zb comparison stops such
    # rows being labelled "EXTRA", which would read as zerobas having a feature it
    # provably lacks.
    # AGREEMENT WINS FIRST. An earlier revision tested the DIFF-crunch rule before
    # comparing the outputs, and promptly called DEFSNG/DEFDBL/DEFSTR "SILENT-GAP"
    # while printing two IDENTICAL answers — at the time those three had no
    # kwtable entry by design (they reached the then-ex_def_type as DEF_TOKEN +
    # literal ASCII) and worked fine. A no-entry word that produces the right
    # answer is the INTERVAL shape, not a gap, so identical observable behaviour
    # must be decided before tokenisation is allowed to weigh in at all.
    # ⚠️ THE ORDERING RULE OUTLIVED ITS EXAMPLE: those three got rows and
    # tokens of their own in D-DEFTYPETOK (2026-08-19) and no longer exercise this
    # path. INTERVAL still does, and the rule is kept for the CLASS, not the
    # instance — any word supported without a kwtable entry lands here.
    if not ref_err and not zb_err and ref_txt.strip() == zb_txt.strip():
        return "SUPPORTED"
    if crunch_state == "DIFF" and not zb_err:
        return "SILENT-GAP"
    if not ref_err and zb_err:
        return "MISSING"
    if ref_err and not zb_err:
        return "EXTRA"
    if ref_err and zb_err:
        # both refuse it — same class = faithful refusal, different = divergent
        return "SUPPORTED" if ref_cls == zb_cls else "DIVERGENT"
    return "SILENT-GAP" if crunch_state == "DIFF" else "DIVERGENT"


def _rom_fingerprint() -> str:
    """Hash the ROMs the repack machine actually loads, so a report can never be
    silently attributed to a different build. The machine XML points straight at
    build/*.rom in the project tree, so a concurrent `make` in another session
    changes the measurement target mid-flight — this is the tripwire for that."""
    root = _os.path.dirname(_os.path.dirname(_os.path.dirname(
        _os.path.abspath(__file__))))
    parts = []
    for name in ("zerobas-main-eu.rom", "sub.rom", "disk.rom"):
        p = _os.path.join(root, "build", name)
        try:
            with open(p, "rb") as fh:
                parts.append(f"{name}={hashlib.sha256(fh.read()).hexdigest()[:12]}")
        except OSError:
            parts.append(f"{name}=<missing>")
    try:
        rev = subprocess.run(["git", "-C", root, "rev-parse", "--short", "HEAD"],
                             capture_output=True, text=True, timeout=10).stdout.strip()
    except Exception:
        rev = "?"
    return f"git={rev} " + " ".join(parts)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--machine", default=MACHINE,
                    help="reference machine (built-in BASIC oracle; default VG-8020)")
    ap.add_argument("--disk-machine", dest="disk_machine", default=DISK_MACHINE,
                    help="disk-equipped reference for NEEDS-DISK rows (default "
                         f"{DISK_MACHINE}); the default VG-8020 has no disk ROM, "
                         "so Disk-BASIC verbs would compare machines, not languages")
    ap.add_argument("--zb-machine", dest="zb_machine", required=True,
                    help="repack machine with BASIC baked into slot 0")
    ap.add_argument("--only", help="comma-separated word keys to run")
    ap.add_argument("--layer", choices=("crunch", "support", "both"), default="both")
    ap.add_argument("--boot-per-case", dest="boot_per_case", action="store_true",
                    help="isolate each case in its own boot (rule out leakage)")
    args = ap.parse_args()

    # A direct-mode line wider than one SCREEN-0 row wraps, so screen_tail can
    # never match its echo and the case silently reports ?noecho -> UNREADABLE.
    # That is a probe defect masquerading as a measurement, so fail loudly at
    # startup rather than emitting an unreadable row (the T3 KEY lesson: the
    # apparatus is part of the measurement).
    too_long = [(k, len(ex)) for k, _, ex, mode, _ in SWEEP
                if ex is not None and mode == "direct" and len(ex) > MAX_DIRECT_ECHO]
    if too_long:
        print("probe defect — direct-mode exec lines exceed one screen row "
              f"({MAX_DIRECT_ECHO} cols); use mode='stored' for these:")
        for k, n in too_long:
            print(f"    {k:9} {n} chars")
        # 🔴 D-KWFOOT: THIS EXIT PRINTS A DIFFERENT TABLE ENTIRELY, and without a
        # footer a runner holding a kwsweep baseline sees ZERO rows and cannot
        # tell "the probe measured nothing" from "I failed to parse it". The
        # abort is CORRECT; what was missing is it SAYING SO.
        print(probe_report.footer(
            len(too_long), 0,
            "probe defect, nothing measured: the listed words' direct-mode exec "
            "lines exceed one screen row, so their echo can never match"))
        return 2

    rows = SWEEP
    if args.only:
        want = {s.strip() for s in args.only.split(",")}
        rows = [r for r in rows if r[0] in want]
        missing = want - {r[0] for r in rows}
        if missing:
            print(f"unknown word keys: {', '.join(sorted(missing))}")
            print(probe_report.footer(
                0, 0, "nothing measured: --only named word keys this sweep does "
                      "not have"))
            return 2
    batch = not args.boot_per_case

    fp_before = _rom_fingerprint()
    print(f"build under measurement: {fp_before}\n")

    results: dict[str, dict] = {k: {} for k, *_ in rows}

    # Route each row's REFERENCE capture to a machine that can actually run it.
    # A Disk-BASIC verb on a diskless reference measures the absence of a disk
    # ROM, not the absence of a language feature — see DISK_MACHINE.
    def ref_machine_for(note: str) -> str:
        return args.disk_machine if "disk" in _row_rigs(note) else args.machine

    # 🔴 D-KWORACLE (2026-09-03): THE SECOND REFERENCE WAS NEVER BOOTED IN TIME,
    # AND ALL FIVE OF ITS WITH-ORACLE ROWS CAME BACK EMPTY. `run_cases` defaults
    # to `boot=8.0`, which is right for the VG-8020 and ~6 s SHORT for the
    # CF-3300; and the CF-3300 boots into a screen mode the scrape cannot read
    # until a `SCREEN 0`. So every NEEDS-DISK row was typed into an unbooted
    # machine: layer 2 got `ref ''` -> NO-ORACLE, and layer 1 read TXTTAB before
    # the line was there -> `<not stored>` -> ABSENT, which called even `MKI$`
    # absent from the reference's own keyword table.
    #
    # 🎯 THE FAMILY CONTROL IS WHAT MADE IT VISIBLE. `mki` is in the row set
    # precisely because MKI$/CVI ship on BOTH sides; when the control reports no
    # oracle, nothing else in the family can be believed. It did, and the summary
    # line -- `NO-ORACLE=5`, with no MISSING count -- reads like a clean bill of
    # health if you do not look at which five.
    #
    # The values here are the SAME ones basic_probe_deffn.SIDES already carries
    # for these machines; the two tables disagreeing is what let this sit.
    MACH_BOOT = {"National_CF-3300": 14.0}
    MACH_RESET_PRE = {"National_CF-3300": ("", "SCREEN 0")}

    def capture(machine_for, specs, sel_rows, mount: bool = True, **kw):
        """Capture `specs`, split by (machine, RIG) and re-interleaved in row
        order. ONE function for both sides on purpose: the subject side needs the
        same disk and the same printer as the reference, and two near-copies is
        how the sweep came to compare a reference holding a disk against a
        zerobas holding none.

        `mount=False` is the crunch layer, which stores a line and never runs it,
        so no row there can reach a disk or a printer."""
        out: list[str | None] = [None] * len(specs)
        keys: list[tuple[str, str]] = []
        for r in sel_rows:
            k = (machine_for(r[4]), _row_rigs(r[4]))
            if k not in keys:
                keys.append(k)
        for mach, rig in keys:
            idx = [i for i, r in enumerate(sel_rows)
                   if (machine_for(r[4]), _row_rigs(r[4])) == (mach, rig)]
            mkw = dict(kw)
            mkw["boot"] = MACH_BOOT.get(mach, 8.0)
            pre = MACH_RESET_PRE.get(mach, ())
            if pre:
                mkw["reset"] = pre + tuple(kw.get("reset", ()))
            if mount:
                mkw.update(_rig_kwargs(rig))
            # a rig may force its own delivery mode (see _rig_kwargs: `log` needs
            # boot-per-case or every row reads its predecessors' printer output)
            tape_out = mkw.pop("_tape_path", None)
            if tape_out is not None:
                assert len(idx) == 1, (
                    "a NEEDS-BLANKTAPE: group holds ONE row: the rig re-creates "
                    "one tape per boot, so only the last case's recording survives")
            got = omsx_repl.run_cases(mach, [specs[i] for i in idx],
                                      batch=mkw.pop("batch", batch), **mkw)
            if tape_out is not None:
                # 🔴 A MARKER, NOT `screen_printer`'s `7c`: this rig takes the
                # DEFAULT capture, which comes back DECODED, while both halves of a
                # `screen_printer` capture are hex. Appending hex to decoded text
                # made `bytes.fromhex` fail and the row read `?noecho` on both
                # sides -- honest, but only because that guard exists. A NUL cannot
                # appear in a 40x24 screen scrape, so the split is unambiguous.
                got = [(g or "") + TAPE_MARK + _tape_readback(tape_out)
                       for g in got]
            for i, g in zip(idx, got):
                out[i] = g
        return out

    def ref_capture(specs, sel_rows, **kw):
        return capture(ref_machine_for, specs, sel_rows, **kw)

    def zb_capture(specs, sel_rows, **kw):
        return capture(lambda note: args.zb_machine, specs, sel_rows, **kw)

    # ---- Layer 1: CRUNCH ---------------------------------------------------
    if args.layer in ("crunch", "both"):
        specs = [("direct", [f"1 {body}"]) for _, body, _, _, _ in rows]
        ref_raws = ref_capture(specs, rows, mount=False, reset=("NEW",),
                               capture=("stored_line", TXTTAB))
        zb_raws = omsx_repl.run_cases(args.zb_machine, specs, batch=batch,
                                      reset=("NEW",),
                                      capture=("stored_line", TXTTAB))
        for (key, body, _, _, _), rr, zr in zip(rows, ref_raws, zb_raws):
            ref, zb = tokens(rr), tokens(zr)
            results[key]["crunch"] = (
                "SAME" if (ref is not None and ref == zb) else "DIFF",
                " ".join(f"{b:02X}" for b in ref) if ref else "<not stored>",
                " ".join(f"{b:02X}" for b in zb) if zb else "<not stored>",
                body,
            )

    # ---- Layer 2: SUPPORT --------------------------------------------------
    if args.layer in ("support", "both"):
        ex_rows = [r for r in rows if r[2] is not None]
        if ex_rows:
            specs = []
            for _, _, line, mode, _ in ex_rows:
                specs.append((mode, omsx_repl.as_stored(line) if mode == "stored"
                              else [line]))
            ref_raws = ref_capture(specs, ex_rows,
                                   reset=("NEW", "CLS"), capture="screen")
            zb_raws = zb_capture(specs, ex_rows,
                                 reset=("NEW", "CLS"), capture="screen")
            for (key, _, line, mode, rnote), rr, zr in zip(ex_rows, ref_raws, zb_raws):
                cmd = "RUN" if mode == "stored" else line
                # NOECHO:<tag> -- this row's own feature erases or moves the
                # echoed command, so it is captured by its unique marker instead
                # (see marker_tail). Everything else keeps the echo anchor.
                mk = (rnote.split(":", 2)[1].split()[0]
                      if rnote.startswith("NOECHO:") else None)
                rrigs = _row_rigs(rnote)
                # `tapew` reads its artefact through the same two-half split as the
                # printer log, for the same reason: the verb's output is not on the
                # screen. The second half is the reading; the screen half only says
                # the program ran.
                islog = ("tape" if "tapew" in rrigs
                         else ("log" in rrigs))
                nofurn = "NOFURN:" in _row_prefix_tags(rnote)
                rc, rt = classify(rr, cmd, mk, log=islog, nofurn=nofurn)
                zc, zt = classify(zr, cmd, mk, log=islog, nofurn=nofurn)
                cs = results[key].get("crunch", (None,))[0]
                note = next(n for k, _, _, _, n in rows if k == key)
                if "disk" in _row_rigs(note) and rc.startswith("?"):
                    # The oracle for this row is the disk-equipped reference, and
                    # it produced nothing readable. Refuse to compare rather than
                    # silently fall back to the diskless default and call the
                    # resulting machine difference a language difference.
                    v = "NO-ORACLE"
                else:
                    v = verdict(rc, rt, zc, zt, cs)
                results[key]["support"] = (v, rc, rt, zc, zt, line)

    fp_after = _rom_fingerprint()

    # ---- report ------------------------------------------------------------
    print("=" * 78)
    print("LAYER 1 — CRUNCH (tokenisation only; NOT a support answer)")
    print("=" * 78)
    for key, *_ in rows:
        c = results[key].get("crunch")
        if not c:
            continue
        state, ref, zb, body = c
        print(f"{state:5}  {key:9} {body}")
        if state == "DIFF":
            print(f"           ref: {ref}")
            print(f"           zb : {zb}")

    print()
    print("=" * 78)
    print("LAYER 2 — SUPPORT (the load-bearing layer)")
    print("=" * 78)
    order = {"SILENT-GAP": 0, "MISSING": 1, "DIVERGENT": 2, "EXTRA": 3,
             "UNREADABLE": 4, "NO-ORACLE": 5, "SUPPORTED": 6}
    executed = [(key, results[key]["support"]) for key, *_ in rows
                if "support" in results[key]]
    notes = {k: n for k, _, _, _, n in rows}
    for key, s in sorted(executed, key=lambda kv: order.get(kv[1][0], 9)):
        v, rc, rt, zc, zt, line = s
        weak = notes[key].startswith("WEAK:")
        print(f"{v:10}{'  ! WEAK' if weak else '  '}  {key:9} {line}")
        print(f"            ref  [{rc}] {rt!r}")
        if v != "SUPPORTED" or weak:
            print(f"            zb   [{zc}] {zt!r}")
        if weak:
            print(f"            {notes[key]}")

    # ---- the combined view: absence (layer 1) + consequence (layer 2) --------
    # Neither layer is readable alone. Layer 1 says whether zerobas TOKENISES the
    # word; layer 2 says what a program actually observes. INTERVAL is why: SAME
    # crunch, no support. TAB( is why: value on both sides, no support.
    if args.layer == "both":
        print()
        print("=" * 78)
        print("COMBINED — tokenised? x observable consequence")
        print("=" * 78)
        print(f"{'word':10} {'crunch':7} {'support':11} consequence")
        print("-" * 78)
        for key, *_ in rows:
            c = results[key].get("crunch")
            s = results[key].get("support")
            cs = c[0] if c else "-"
            tok = {"SAME": "present", "DIFF": "ABSENT", "-": "-"}[cs]
            if s:
                sv = s[0]
                cons = f"ref {s[2]!r} vs zb {s[4]!r}" if sv != "SUPPORTED" else "match"
            else:
                sv, cons = "not-run", "crunch-only — support UNKNOWN"
            print(f"{key:10} {tok:7} {sv:11} {cons}")

    skipped = [(k, n) for k, _, ex, _, n in rows if ex is None]
    if skipped:
        print()
        print("=" * 78)
        print(f"NOT EXECUTED — {len(skipped)} words, crunch-only. Reasons below; these "
              "are\nCOVERAGE HOLES IN THIS PROBE, not evidence of support.")
        print("=" * 78)
        for k, n in skipped:
            print(f"  {k:9} {n}")

    # ---- summary + the apparatus tripwire ----------------------------------
    # WEAK rows are excluded from the tally: counting a known-false SUPPORTED
    # would overstate coverage, which is the exact error this probe was built to
    # stop making.
    tally: dict[str, int] = {}
    for key, s in executed:
        tally["WEAK(excluded)" if notes[key].startswith("WEAK:") else s[0]] = \
            tally.get("WEAK(excluded)" if notes[key].startswith("WEAK:") else s[0], 0) + 1
    print()
    print("=" * 78)
    print("SUMMARY  " + "  ".join(f"{k}={v}" for k, v in
                                  sorted(tally.items(), key=lambda kv: order.get(kv[0], 9))))
    print(f"         executed {len(executed)} / {len(rows)} words; "
          f"{len(skipped)} crunch-only")
    print("=" * 78)
    print(probe_report.footer(
        len(rows), len(executed),
        f"{len(skipped)} crunch-only word(s) carry no support reading and are "
        f"printed but not scored"))

    # ---- D-TIERS (2026-09-10): a machine-readable pin for `make tiers` --------
    # Every row here IS a keyword, so this run is the first per-keyword
    # evidence the tier table can read without running an emulator. Written
    # to build/ (regenerated, never tracked) and ONLY when the ROMs held still
    # for the whole run -- a discarded report must not leave a pin behind.
    if fp_before == fp_after:
        import json
        import time as _time
        stmt = {key: st for key, st, *_ in rows}
        pin = {"written": _time.strftime("%Y-%m-%d %H:%M:%S"),
               "rom_fingerprint": fp_after,
               "rows": {key: {"verdict": s[0],
                              "weak": notes[key].startswith("WEAK:"),
                              # what the row CLAIMS to prove; absent = TIER 1 only
                              "proves": ("T3" if "PROVES-T3:" in
                                         _row_prefix_tags(notes[key]) else None),
                              "stmt": stmt[key]}
                        for key, s in executed}}
        _root = _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
        pin_path = _os.path.join(_root, "build", "kwsweep-verdicts.json")
        try:
            _os.makedirs(_os.path.dirname(pin_path), exist_ok=True)
            with open(pin_path, "w", encoding="utf-8") as fh:
                json.dump(pin, fh, indent=1, sort_keys=True)
            print(f"pin: {len(pin['rows'])} row verdict(s) -> {pin_path}")
        except OSError as e:
            print(f"pin: NOT written ({e}) -- `make tiers` will show no kwsweep evidence")

    if fp_before != fp_after:
        print("\n*** APPARATUS WARNING — the ROMs changed DURING this run:")
        print(f"      before: {fp_before}")
        print(f"      after : {fp_after}")
        print("    Another session rebuilt the tree. DISCARD this report and re-run.")
        print(probe_report.footer(
            len(executed), 0,
            "DISCARDED: the ROMs changed during the run, so every row above was "
            "taken from more than one machine"))
        return 3

    # NEEDS-DISK rows cannot be controls: their oracle is the disk-equipped
    # reference, which is not yet readable (see DISK_MACHINE).
    controls = [k for k, _, ex, _, n in rows
                if ex is not None and n.startswith("control")]
    bad = [k for k in controls
           if results[k].get("support", ("?",))[0] != "SUPPORTED"]
    if bad:
        print(f"\n*** CONTROL GROUP FAILED: {', '.join(bad)}")
        print("    The apparatus is not measuring what it claims. Every other row "
              "in this\n    report is untrustworthy until this is explained.")
        print(probe_report.footer(
            len(executed), 0,
            f"NOT SCORED: the control group failed ({', '.join(bad)}), so the "
            f"apparatus is not measuring what it claims"))
        return 4

    # --- the crunch pin: a MISSING keyword has no other way to be scored ----
    if args.layer in ("crunch", "both"):
        diffs = {k for k in results
                 if results[k].get("crunch", (None,))[0] == "DIFF"}
        new_d = sorted(diffs - set(CRUNCH_DIFF_PINNED))
        gone = sorted(set(CRUNCH_DIFF_PINNED) - diffs)
        print("\n=== CRUNCH PIN — words the reference tokenises and zerobas "
              "does not ===")
        for k in sorted(CRUNCH_DIFF_PINNED):
            mark = "still DIFF" if k in diffs else "\U0001f7e2 NO LONGER DIFF"
            print(f"    {k:9s} {CRUNCH_DIFF_PINNED[k]:44s} {mark}")
        if new_d:
            print(f"\n*** \U0001f534 {len(new_d)} UNPINNED CRUNCH DIFF(S): "
                  f"{', '.join(new_d)}")
            print("    The reference tokenises these and zerobas does not, so "
                  "zerobas is\n    MISSING the keyword and parses it as an "
                  "ordinary VARIABLE -- the silent\n    shape this whole probe "
                  "exists to catch (TIME, TAB(). Implement it, or\n    pin it in "
                  "CRUNCH_DIFF_PINNED with its oracle-measured token and a why.")
            return 5
        if gone:
            print(f"\n*** \U0001f534 {len(gone)} PIN(S) NO LONGER DIVERGE: "
                  f"{', '.join(gone)}")
            print("    Good news, and it must be BOOKED: drop them from "
                  "CRUNCH_DIFF_PINNED,\n    or a stale pin hides the next real "
                  "one.")
            return 5

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
