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
import rigfw  # the RP2040-Zero input rig (tools/rigfw) -- NEEDS-RIG: rows
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
# 🔴 D-KWRUNFILE: `step` WENT 5.0 -> 8.0, AND `open_c` IS WHY -- TWICE. A case
# SLOWER THAN `step` has its SUCCESSOR typed into a still-running program, and on
# the CF-3300 a row with two open/write/close cycles sits right at the 5 s edge:
# `open_c` read cleanly alone and came back with a BLANK REFERENCE SCREEN as the
# disk group grew, once when `bsave_b` joined it and again when the RUN/LOAD rows
# did. Shrinking the row fixed it the first time and did not the second -- the
# fix belongs to the GROUP, not to whichever row happens to be at the edge.
DISK_TIMING = dict(step=8.0, cap_gap=20.0, timeout=900.0)


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
# 🔴 `run_gap` IS THE RUN->CAPTURE BUDGET AND THE TAPE ROWS NEEDED ONE
# (D-CAPGAP, fixed 2026-09-23). `cap_gap` is the gap AFTER the capture and buys
# a slow case nothing; the budget was `step` (5 s), which does not cover a tape
# SEARCH -- a 16000-cycle leader alone is ~7 emulated seconds per file and
# `cload` has to skip ZQ to reach ZR.
# 🎯 WHAT IT WAS HIDING WAS A REAL DEFECT, AND A VACUOUS AGREEMENT WAS HIDING IT:
#     ref  'Skip :ZQ'            zb  'Skip :ZQ'            -> SUPPORTED
# Both machines were captured MID-SEARCH, so they agreed on the shared prefix.
# With a real budget the reference finishes and finds the file while we fail:
#     ref  'Skip :ZQ|Found:ZR'   zb  'Skip :ZQ|load error' -> MISSING
# That is this tree's own do-not-award shape: two machines agreeing about
# nothing [[a-case-that-agrees-can-agree-for-the-wrong-reason]], on one of its
# named DENOMINATORS -- exactly the hole the denominator exists to close.
# 🔴 AND IT IS HERE, ON THE TAPE ROWS, RATHER THAN ON THE SUITE. A blanket
# `run_gap` FIXES `cload` AND BREAKS FOUR OTHER ROWS: `stick_hold`,
# `strig_hold`, `onstrig` and `onstrig_b` are `NEEDS-HOLD:` rows, the hold is
# pressed at the capture slot MINUS `step`, and `run_gap` raises that slot --
# so a wide budget moves the PRESS past the program's own 120-tick sampling
# window and all four reference readings flip from held (1/-1) to idle (0).
# MEASURED at ZEROBAS_RUN_GAP=90: `[2d 1 ]`->`[2d 0 ]`, `[1w-1 ]`->`[1w 0 ]`,
# `[1x-1 ]`->`[1x 0 ]`, `[1y 1 ]`->`[1y 0 ]`. **Those four are the instrument
# breaking, not the truth emerging** -- the opposite direction from `cload`, in
# the same run. A per-SUITE budget cannot tell them apart; a per-RIG one can.
TAPE_TIMING = dict(step=5.0, cap_gap=90.0, run_gap=60.0, timeout=1200.0)
TAPE_MARK = "\x00TAPE\x00"
TAPE_NAME = "ZQ"
TAPE_PROGRAM = make_multiline_program([(10, 'PRINT"[Z9]"')], 0x8001)
# 🎯 D-KWTAPE4: A SECOND FILE, AND IT IS WHAT MAKES EITHER `CLOAD` FORM MEAN
# ANYTHING. With ONE file on the tape a named `CLOAD"ZQ"` and a bare `CLOAD` both
# read the same first file and print the same `Found:ZQ` -- two forms, one
# reading, and a CLOAD that ignored its name argument passed both. `ZR` sits
# SECOND, so the named row has to SEARCH PAST a non-matching file to reach it and
# the bare row takes `ZQ` because it is simply the NEXT one.
TAPE_NAME2 = "ZR"
TAPE_PROGRAM2 = make_multiline_program([(10, 'PRINT"[Z8]"')], 0x8001)


def _tape_fixture() -> str:
    """A PREPARED tape for a reading row: a clean-room `.cas` carrying one known
    program under a known name, fresh per machine like the disk images.

    🎯 The program prints a MARKER, so a row can do more than reach `Ok`: the
    reference announces `Found:ZQ` on the screen as it reads, which is the
    machine's own witness that the verb did something and not merely parsed."""
    fh = tempfile.NamedTemporaryFile(suffix=".cas", delete=False)
    # Two logical images back to back IS a two-file tape: each is
    # `sync+header+sync+data`, which is exactly how a multi-program .cas is laid
    # out. Nothing in the encoder needed changing.
    # 🔴 CSAVE-FAITHFUL, NO TRAILING PAD -- AND THIS FIXTURE WAS NOT, WHICH IS
    # WHAT THE `cload` ROW WAS ACTUALLY MEASURING (D-CLOADSKIP, 2026-09-23).
    # `cas_encode.build_cas_basic` appends 16 $00 bytes after the end-link for
    # SINGLE-file framing. On a MULTI-file tape those unread pad bytes leave a
    # SKIPPED tokenised file mid-block so the next TAPION cannot relock -- which
    # `cload.asm`'s `cas_skip_data` states as its own assumption ("assumes the
    # tokenised data block ENDS at the $0000 end-link ... cas_encode's
    # single-file 16-byte pad would leave slack"), and which
    # `basic_probe_cas_match.py:tok_file_nopad` had already built a helper to
    # avoid. This probe kept using the padded builder, so `CLOAD"ZR"` was being
    # asked to skip a file that a real CSAVE never writes.
    # ⚠️ Real CSAVE tapes have no such pad (save.asm: payload then TAPOOF), so
    # the unpadded form is the faithful one and the padded form was testing the
    # fixture rather than the verb.
    fh.write(cas_encode.build_cas_basic_nopad(TAPE_NAME, TAPE_PROGRAM)
             + cas_encode.build_cas_basic_nopad(TAPE_NAME2, TAPE_PROGRAM2))
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


def _tape_readback(path: str, subject: bool = False) -> str:
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
    # 🔴 D-KNIFENOREAD (2026-09-24): BUT ONLY ON THE REFERENCE. The knife cuts
    # CSAVE on the SUBJECT side and the subject then writes no tape -- which is
    # exactly the defect this row exists to see, and the blanket refusal turned
    # it into "nothing was measured" (and the knife scored that as proof). A
    # reference that records nothing IS a broken rig; a subject that records
    # nothing is a READING, and it can never agree with the reference's real
    # tape, so the two-missing-fixtures trap above stays shut.
    if not _os.path.exists(path) and subject:
        return "<no tape written>"
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
# 🟢 D-KWAUTO: `NEEDS-BOOT:` IS THE SEVENTH RIG AND THE SMALLEST -- it asks for
# NOTHING but a boot of its own. Every other rig that needs boot-per-case gets it
# as a SIDE EFFECT of the device it wants (the printer log is never truncated, a
# blank tape must be re-created), so a row whose only requirement is isolation had
# no way to say so and had to be LAST BY PLACEMENT instead. `AUTO` is why: it
# leaves the machine in LINE-ENTRY MODE, which ate 21 following rows once, and
# placement can only ever protect ONE such row.
_RIG_TAGS = {"NEEDS-DISK:": "disk", "NEEDS-PRINTER:": "printer",
             "NEEDS-LOG:": "log", "NEEDS-TAPE:": "tape",
             "NEEDS-BLANKTAPE:": "tapew", "NEEDS-BOOT:": "boot"}

# 🟢 D-KWHOLD: THE SIXTH RIG IS THE KEY MATRIX, AND IT IS THE ONLY ONE THAT TAKES
# AN ARGUMENT. `NEEDS-HOLD:<row>,<mask>` holds ONE matrix bit down for the whole
# of the case's RUN -- row 8 bit 0 is the SPACE bar, row 8 bits 4/5/6/7 are
# left/up/down/right, row 6 bit $20 is F1 (the published MSX work-area layout, and
# the same constants basic_probe_input_devices.py and basic_probe_key_trap.py
# already drive).
# 🔴 IT EXISTS BECAUSE KEYBUF INJECTION CANNOT REACH A MATRIX SCAN. Every other
# delivery here writes DECODED characters into the ROM's type-ahead buffer, which
# bypasses the matrix entirely -- so STICK/STRIG (GTSTCK/GTTRIG) and the ON KEY /
# ON STRIG traps read IDLE no matter what the driver "types", and idle is 0, which
# is exactly what a stub returns [[a-case-that-agrees-can-agree-for-the-wrong-reason]].
# `omsx_repl.run_cases` has carried the `holds=` seam since the input-devices arc;
# this only routes it per row.
# ⚠️ THE ARGUMENT IS PART OF THE GROUP KEY, so two rows holding DIFFERENT keys are
# captured in different batches -- one `holds` value per batch is all the timeline
# can express.
_HOLD_TAG = "NEEDS-HOLD:"

# 🟢 D-KWPLUG: THE SEVENTH RIG PLUGS A DEVICE INTO A JOYSTICK PORT.
# `NEEDS-PLUG:<port>,<device>` becomes openMSX's `plug joyport<port> <device>`,
# run ONCE before the timeline (the connectors exist at script start, so this
# needs no scheduling).
# 🔴 IT EXISTS BECAUSE A DEVICE THAT IS MERELY PLUGGED ALREADY CHANGES WHAT THE
# REFERENCE REPORTS, AND NOTHING ELSE HERE CAN DRIVE ONE. openMSX offers no host
# mouse or paddle to turn, so a PDL value cannot be DRIVEN -- but a plugged paddle
# reads **128** where an empty port idles at 255, and an arkanoidpad answers
# PAD(0) = -1 where an empty port reads 0. Those are the only teeth PDL and PAD
# have: their unplugged rows read the IDLE line, and 255 is as much a constant as
# 0 is [[a-case-that-agrees-can-agree-for-the-wrong-reason]].
# The values are `basic_probe_input_devices.py`'s own measured table (its PHASE D
# and PHASE E), not guesses.
_PLUG_TAG = "NEEDS-PLUG:"

# 🟢 D-RIGFW: THE EIGHTH RIG IS A REAL USB JOYSTICK. `NEEDS-RIG:<state>` puts the
# RP2040-Zero (tools/rigfw/rigfw.ino, driven by probes/lib/rigfw.py) into a
# state -- `upright`, `trig1`, `downleft+trig2` -- BEFORE each machine's boot and
# holds it for the whole group, then centres it. The prologue binds openMSX's
# `msxjoystick1` (port A) to that host stick.
# 🔴 IT EXISTS BECAUSE NOTHING ELSE CAN MOVE A JOYSTICK PORT. Every STICK/STRIG
# row before it read the KEYBOARD forms (n=0) or the idle 0 a stub returns;
# openMSX's Tcl cannot drive a joystick (D-RIGBLOCK), and the PSG-latch injection
# fakes a TRIGGER behind GTTRIG's back but never a direction. The board is a
# genuine HID device, so SDL enumerates it even headless (measured, D-RIGFW).
# ⚠️ THE STATE IS WRITTEN INTO THE PROLOGUE TEXT (`set ::zb_rig_state ...`) so
# that the reference cache keys on it: the board is set OUTSIDE run_cases, and
# two groups with different states would otherwise share one cached answer.
# ⚠️ NO BOARD, NO READING: without a board answering `id`, these rows run
# crunch-only and say so -- they are never scored, so a machine without the rig
# cannot award or refute the joystick forms.
_RIG_TAG = "NEEDS-RIG:"


def _rigstate_of(rigs: tuple[str, ...]) -> str | None:
    """The rigfw state a rig tuple asks for, or None."""
    for r in rigs:
        if r.startswith("rig:"):
            return r[len("rig:"):]
    return None


def _plug_of(rigs: tuple[str, ...]) -> tuple[str, ...]:
    """The openMSX `plug` prologue a rig tuple asks for, or ()."""
    out = []
    for r in rigs:
        if r.startswith("plug:"):
            port, dev = r[len("plug:"):].split(",")
            out.append(f"plug joyport{port} {dev}")
    return tuple(out)


def _hold_of(rigs: tuple[str, ...]):
    """What a rig tuple asks to hold down, or None.

    ONE `(row, mask)` for a single key, or a TUPLE of them for a combo --
    `run_cases` takes either. 🔴 D-KWSTOP: the combo exists because Ctrl-STOP is
    TWO keys on DIFFERENT MATRIX ROWS (CTRL row 6 bit $02 + STOP row 7 bit $10),
    which is the whole reason `ON STOP GOSUB` had no row while its five sibling
    trap composites got theirs. Written `NEEDS-HOLD:6,0x02+7,0x10`: the MODIFIER
    FIRST, because the keys go down in the order given and come up in reverse."""
    for r in rigs:
        if r.startswith("hold:"):
            spec = r[len("hold:"):].split("@")[0]
            keys = tuple(tuple(int(v, 0) for v in part.split(","))
                         for part in spec.split("+"))
            return keys[0] if len(keys) == 1 else keys
    return None


def _holdtime_of(rigs: tuple[str, ...]) -> tuple[float, float] | None:
    """The `@<lead>/<secs>` a hold tag carries, or None for the defaults.

    🔴 D-KWSTOP: CTRL-STOP NEEDED BOTH, AND THE DEFAULTS BLANK THE REFERENCE'S
    SCREEN. Measured on the VG-8020 with every combination separated one at a
    time (`scratchpad/ctrlstop_probe.py`):
      * the DURATION -- a 2 s Ctrl-STOP reads a clean `Break in 20`; 5 s and the
        12 s default leave the screen COMPLETELY BLANK. CTRL alone and STOP alone
        at 12 s both leave the program running to completion, so it is the COMBO
        and it is the DURATION, and it is the reference's own behaviour at
        command level rather than an injection fault.
      * the LEAD -- pressing at the default RUN+0.3 blanks it too, while
        RUN+step+0.5 (the program already looping) is clean.
    The stop-trap arc's own docstring says the same from the other side: the
    happy path appears with a brief TAP during a delay, never a hold.
    ⚠️ Both are per-CALL `run_cases` kwargs, and the whole tag is part of the
    capture GROUP KEY, so every row in a group shares them."""
    for r in rigs:
        if r.startswith("hold:") and "@" in r:
            lead, secs = r.split("@", 1)[1].split("/")
            return (float(lead), float(secs))
    return None


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

# 🎚️ `FORM:<name>` — WHICH SYNTACTIC FORM OF ITS KEYWORD THIS ROW EXERCISES, and
# the reason TIER 1 needs it (Joost, 2026-09-14: "connected + N forms + no open
# item, N depending on the complexity of each individual keyword"). Counting ROWS
# would let three rows of the SAME form satisfy N=3 -- and that is not a
# hypothetical: `psetkw` and `psetkw_b` both drive `PSET(x,y),c`, differing only in
# WHICH colour, so before this tag existed PSET looked like two independent pieces
# of evidence for one form. The name is free text; what the tier table counts is
# DISTINCT names per keyword, against the form list authored in tools/kwforms.py.
_FORM_TAG = "FORM:"


def row_form(note: str) -> str | None:
    """The form name a row declares, or None. `FORM:step-relative` -> that name.

    🔴 SCANS THE WHOLE NOTE, DELIBERATELY NOT THE PREFIX RUN. `NOECHO:` is matched
    with `startswith` and must be the note's FIRST token, so a form tag can never
    precede it on those rows; and widening `_row_prefix_tags` to step past NOECHO
    would change where `PROVES-T3:` is seen on every row that has both. A form name
    selects no apparatus and changes no capture -- it is metadata the tier table
    counts -- so it is parsed independently and cannot disturb rig or flag parsing."""
    for tok in note.split():
        if tok.startswith(_FORM_TAG) and len(tok) > len(_FORM_TAG):
            return tok[len(_FORM_TAG):]
    return None


# 🎚️ D-KWSUBJECT (2026-09-14). WHICH STATEMENT A ROW IS ABOUT CANNOT ALWAYS BE
# DERIVED. The tier table reads the subject off the crunch body -- first keyword,
# or a composite name when the body carries one -- and that is right for most
# rows and MEASURABLY WRONG for the rest:
#   * `using`'s crunch body is `using "##"` and NEVER MENTIONS PRINT. Derivation
#     scores it for USING, a token that is not even in `stmt_table`.
#   * `inputkw`'s body is about `INPUT #1`, but `#` is punctuation and invisible
#     to keyword matching, so it is indistinguishable from bare `INPUT`.
#   * an exec line cannot stand in: it is apparatus-dominated (`inputkw`'s opens
#     a file, reads it, closes it and prints a length).
# Joost ruled the parents tier independently of their composites ("bare print and
# print # and print using have a different function"), so the distinction has to
# survive into the pin. THE ROW DECLARES IT. `_` becomes a space, because a note
# token cannot contain one: `SUBJECT:PRINT_USING` -> `PRINT USING`.
# ⚠️ A DECLARED SUBJECT IS VALIDATED IN `tier_table.stmt_subject`, NOT HERE -- a
# typo that named nothing would otherwise delete the row from its real keyword's
# evidence while looking like a tag that worked.
# ⌨️ D-KWRESPOND (Joost, 2026-09-14: *"Build it"*). BARE CONSOLE `INPUT "x";A$`
# AND `LINE INPUT` HAD NEVER HAD A ROW, and the reason was the row format: the
# harness types the numbered lines and `RUN` and then nothing, so a program that
# blocks on the keyboard simply hangs there.
# 🔴 AND THE UNBLOCK I PROPOSED WAS UNNECESSARY. I offered to stuff KEYBUF ($FBF0)
# with GETPNT/PUTPNT from inside the stored program -- apparatus INSIDE the program
# under test, which is exactly where this session kept getting bitten. Reading
# `probes/basic/basic_probe_input.py` first showed it does nothing of the kind: it
# types the response as a TRAILING RAW LINE AFTER `RUN`, and the line editor
# consumes it in order, so by the time it is injected RUN is executing and the read
# is blocked -- the CR-terminated line lands in KEYBUF by itself and CHGET hands it
# to INPUT. No POKEs, and a mechanism `input-acceptance` has been proving for
# months.
# 🎯 SO A `RESPOND:` ROW IS BUILT AS A **DIRECT** CASE CARRYING ITS OWN NUMBERED
# LINES, `RUN`, AND THE RESPONSES -- exactly the shape `basic_probe_input.spec`
# returns -- because `run_cases` appends `RUN` itself in stored mode and has no
# hook for anything after it. Nothing in omsx_repl changes.
# ⚠️ `_` becomes a space and `|` separates responses, since a note token can hold
# neither.
_RESPOND_TAG = "RESPOND:"


def row_respond(note: str) -> list[str] | None:
    """The lines a row types AFTER `RUN`, or None. `RESPOND:42` -> ['42']."""
    for tok in note.split():
        if tok.startswith(_RESPOND_TAG) and len(tok) > len(_RESPOND_TAG):
            return [p.replace("_", " ")
                    for p in tok[len(_RESPOND_TAG):].split("|")]
    return None


_PROGRAM_TAG = "PROGRAM:"


def row_program(note: str) -> list[str] | None:
    """The COMPLETE numbered lines a row types BEFORE its exec line, or None.

    `PROGRAM:10_REM_Z1|20_REM_Z2` -> ['10 REM Z1', '20 REM Z2'] (`_` is a space,
    the same spelling RESPOND: uses). The line NUMBERS are part of the tag on
    purpose: `RENUM` bare is a no-op on a program that already runs 10/20/30, so
    a row must be able to state 5/7/9 and read the renumbering. A row carrying
    this types the lines, then its exec line, then any RESPOND: lines -- and
    never `RUN`, because these verbs are what a user types AT THE PROMPT."""
    for tok in note.split():
        if tok.startswith(_PROGRAM_TAG) and len(tok) > len(_PROGRAM_TAG):
            return [p.replace("_", " ")
                    for p in tok[len(_PROGRAM_TAG):].split("|")]
    return None


_SUBJECT_TAG = "SUBJECT:"


def row_subject(note: str) -> str | None:
    """The statement a row declares itself to be about, or None to derive it.

    Parsed exactly like `row_form` above, and for the same reasons: whole note,
    never the prefix run, no effect on rig or flag parsing."""
    for tok in note.split():
        if tok.startswith(_SUBJECT_TAG) and len(tok) > len(_SUBJECT_TAG):
            return tok[len(_SUBJECT_TAG):].replace("_", " ")
    return None


def _row_prefix_tags(note: str) -> tuple[str, ...]:
    """The prefix run of tags on a note, rig and flag tags in any order.

    🔴 THIS EXISTS BECAUSE `NOFURN:` WAS TESTED WITH `startswith` and the tape
    rows are the first to need a rig tag AND a flag: `NEEDS-TAPE: NOFURN: ...`
    silently lost the flag, and the row it lost it on diverged only in the
    reference's function-key line -- a furniture difference reported as a defect."""
    out = []
    for tok in note.split():
        if (tok in _RIG_TAGS or tok in _FLAG_TAGS
                or tok.startswith(_HOLD_TAG) or tok.startswith(_PLUG_TAG)
                or tok.startswith(_RIG_TAG)):
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
    def _one(t):
        if t in _RIG_TAGS:
            return _RIG_TAGS[t]
        if t.startswith(_HOLD_TAG):
            return "hold:" + t[len(_HOLD_TAG):]
        if t.startswith(_RIG_TAG):
            return "rig:" + t[len(_RIG_TAG):]
        return "plug:" + t[len(_PLUG_TAG):]
    return tuple(_one(t) for t in _row_prefix_tags(note)
                 if t in _RIG_TAGS or t.startswith(_HOLD_TAG)
                 or t.startswith(_PLUG_TAG) or t.startswith(_RIG_TAG))


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
    if "boot" in rigs:
        # 🎯 THE WHOLE RIG. A row that poisons the SESSION rather than the SCREEN
        # cannot be cleaned up by `reset` -- `NEW`/`CLS` are typed INTO whatever
        # mode the previous row left behind -- so the only fix is not to share a
        # boot with anyone.
        kw["batch"] = False
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
        # 🔴 D-KWTAPE4: BOOT-PER-CASE, THE MOMENT THERE WAS A SECOND ROW. The
        # capture waits `cap_gap` (90 s) but the NEXT case is typed after `step`
        # (5 s), and a tape read is still running then -- so case 2 would be typed
        # into a machine chewing through a leader. That is the same shape that
        # blanked `open_c`'s reference screen when a slow writer sat upstream of
        # it; here it is structural rather than marginal. A fresh boot also
        # REWINDS the tape, which the bare `CLOAD` row depends on.
        kw["batch"] = False
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
# 🔴 36, NOT 38 (D-BOOTWIDTH + D-ZBCRLF, 2026-09-24). 38 silently assumed
# zerobas's screen was 39 wide. zerobas now boots at the VG-8020's 37, and a
# line that exactly FILLS the row wraps the cursor: 37 - 1 = 36. Measured on the
# way there: while `ZB` still shared the typed line's row, 36-37-char rows went
# UNREADABLE (the echo split) and a 35-char one gained a stray row break; Joost
# then ruled the CR/LF after `ZB` (D-ZBCRLF), which gave the 2 columns back. The
# five rows moved to stored mode in between stay stored -- harmless either way.
MAX_DIRECT_ECHO = 36
DISK_ORACLE_WIDTH = 39      # the CF-3300's boot width (D-BOOTWIDTH, measured)

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
    ("abs",     "a=abs(-5)",          'PRINT"[";ABS(-5);"]"',            "direct", "FORM:magnitude control"),
    ("int",     "a=int(1.7)",         'PRINT"[";INT(1.7);"]"',           "direct", "FORM:floor control"),
    ("len",     'a=len("ab")',        'PRINT"[";LEN("ab");"]"',          "direct", "FORM:length control"),
    ("chr",     "a$=chr$(65)",        'PRINT"[";CHR$(65);"]"',           "direct", "FORM:code-to-char control"),
    ("mid",     'a$=mid$("hi",1,1)',  'PRINT"[";MID$("hi",2,1);"]"',     "direct", "FORM:substring-3arg control"),
    # 🌾 D-KWBATCH6: MID$ HAS THREE FORMS AND ONLY THE THREE-ARGUMENT READ HAD A ROW.
    # The two-argument read runs to the END of the string, which is a different
    # length computation, not a different input.
    ("mid_b",   'a$=mid$("hello",3)',
     'PRINT"[";MID$("hello",3);"]"',                  "direct",
     "FORM:substring-to-end the TWO-argument form, which runs to the end of the "
     "string -- `llo`. The three-argument row supplies the length, so it cannot "
     "see a handler that computes the default one wrongly."),
    # 🔴 AND MID$ IS ALSO A STATEMENT. `ex_mid_stmt` (basic/str-engine.asm:1359) is
    # a SEPARATE handler from the function selector, so no read row reaches it --
    # the same shape as VDP(n) and TIME.
    ("mid_c",   'mid$(a$,2,3)="xyz"',
     'A$="abcdef":MID$(A$,2,3)="XYZ":PRINT"[";A$;"]"',  "stored",
     "FORM:assign the ASSIGNMENT statement, which has its own handler. Reading the "
     "WHOLE string is the point: `aXYZef` shows the replaced span AND that the "
     "bytes either side are untouched, where a handler that rebuilt the string "
     "would pass a substring-only check."),
    ("instr",   'a=instr("ab","b")',  'PRINT"[";INSTR("ab","b");"]"',    "direct", "FORM:search control"),
    # 🌾 D-KWBREADTH batch 9: the row above uses the TWO-argument form, and the only
    # three-argument coverage is `instr_t3`, which passes an INVALID start of 0. The
    # VALID start form is untested: `INSTR(2,"ABA","A")` must skip the first "A" and
    # find the one at 3, where a start argument that is parsed and discarded says 1.
    ("instr_b", 'a=instr(2,"aba","a")', 'PRINT"[";INSTR(2,"ABA","A");"]"',  "direct",
     "D-KWDRAIN: the 3-argument START form -- 3, not 1. A start that parses and is "
     "FORM:search-from then ignored finds the FIRST A and reads 1."),
    ("hex",     "a$=hex$(255)",       'PRINT"[";HEX$(255);"]"',          "direct", "FORM:to-hex control"),
    ("sqr",     "a=sqr(9)",           'PRINT"[";SQR(9);"]"',             "direct", "FORM:square-root control"),
    ("peek",    "a=peek(0)",          'PRINT"[";PEEK(0)>=0;"]"',         "direct", "FORM:address-read control"),
    # D-KWBATCH7: `peek` reads `PEEK(0)>=0`, a BOOLEAN, which is the fourth
    # screening axis and PEEK's only evidence. The byte PEEK reads back is scored
    # by `pokekw` -- but that row's SUBJECT is POKE. This one's crunch body is
    # `a=peek(-8192)`, so the reading is scored for PEEK.
    ("peek_b",  'a=peek(-8192)',
     'POKE-8192,66:PRINT"[";PEEK(-8192);"]"',        "stored",
     "FORM:address-read the VALUE, not its non-negativity -- 66, the byte just "
     "POKEd. `peek` asks `PEEK(0)>=0`, which is true of every possible byte."),
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
     "FORM:variable cancels; A and B are created BEFORE the DIM so the array cannot move."),
    ("stick",   "a=stick(0)",         'PRINT"[";STICK(0);"]"',           "direct", "control"),
    # 🌾 D-KWPLUG: `stick` below reads the idle 0 a stub also returns. This one holds
    # the CURSOR-UP key (matrix row 8, bit $20) and reads the direction code.
    ("stick_hold", 'a=stick(0)',
     'S=0:T=TIME:W$="WWWWWWWWWWWWWWWWWW":IF STICK(0)THEN S=STICK(0):V$="VVVVVVV":IF S=0 AND TIME-T<120 THEN 20:PRINT"[2d";S;"]"',
     "stored",
     "NEEDS-HOLD:8,0x20 SUBJECT:STICK FORM:cursor-keys 1 = UP: `STICK(0)` reads the "
     "CURSOR KEYS off the matrix, and the direction CODE separates it from any "
     "non-zero constant"),
    ("erase",   "erase a",            'DIM Q(2):ERASE Q:PRINT"[ok]"',    "direct", "control"),
    # 🌾 D-KWBATCH5: `erase` prints a CONSTANT `[ok]` -- the third screening axis,
    # and an ERASE that parsed and did nothing prints it just as happily. The effect
    # is that the name becomes FREE TO DIM AGAIN: without the ERASE the second DIM
    # is `Redimensioned array`, and with it the array comes back fresh, so the
    # element that held 5 reads 0.
    ("erase_b", 'erase q',
     'DIM Q(2):Q(1)=5:ERASE Q:DIM Q(2):PRINT"[";Q(1);"]"',               "stored",
     "FORM:free-array the EFFECT: `[ 0 ]` -- the array was erased, re-dimmed and "
     "came back cleared. An ERASE that did nothing makes the second DIM a "
     "`Redimensioned array` error instead."),
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
    ("asc",     'a=asc("A")',         'PRINT"[";ASC("A");"]"',         "direct", "FORM:code-of D-KWDRAIN"),
    ("cint",    'a=cint(1.7)',        'PRINT"[";CINT(1.7);"]"',        "direct", "FORM:to-integer D-KWDRAIN"),
    ("cdbl",    'a=cdbl(1)',          'PRINT"[";CDBL(1)/3;"]"',        "direct", "FORM:to-double D-KWDRAIN"),
    ("csng",    'a=csng(1.5)',        'PRINT"[";CSNG(1.5);"]"',        "direct", "FORM:to-single D-KWDRAIN"),
    ("fix",     'a=fix(-1.7)',        'PRINT"[";FIX(-1.7);"]"',        "direct", "FORM:truncate D-KWDRAIN"),
    ("sgn",     'a=sgn(-3)',          'PRINT"[";SGN(-3);"]"',          "direct", "FORM:sign D-KWDRAIN"),
    ("sin",     'a=sin(0)',           'PRINT"[";SIN(0);"]"',           "direct", "D-KWDRAIN"),
    # 🔴 D-KWTRIGVAL: `SIN(0)` IS 0 AND SO IS A STUB. The row above reads the one
    # argument whose answer a do-nothing function also gives -- the same axis as
    # `PEEK(0)>=0` and `INP(&HA8)>0`. `COS(0)` is 1 and escapes it; SIN and TAN do
    # not. Scaled by 1000 and truncated so the reading is an INTEGER both machines
    # must agree on rather than a float rendering.
    ("sin_b",   'a=sin(1)',   'PRINT"[";INT(SIN(1)*1000);"]"',  "direct",
     "FORM:sine SIN at an argument where 0 is the WRONG answer -- 841."),
    ("cos",     'a=cos(0)',           'PRINT"[";COS(0);"]"',           "direct", "FORM:cosine D-KWDRAIN"),
    ("tan",     'a=tan(0)',           'PRINT"[";TAN(0);"]"',           "direct", "D-KWDRAIN"),
    ("tan_b",   'a=tan(1)',   'PRINT"[";INT(TAN(1)*1000);"]"',  "direct",
     "FORM:tangent TAN at an argument where 0 is the WRONG answer -- 1557. "
     "`TAN(0)` is 0, which a stub returns too."),
    ("atn",     'a=atn(1)',           'PRINT"[";INT(ATN(1)*1000);"]"', "direct", "FORM:arctangent D-KWDRAIN"),
    ("exp",     'a=exp(1)',           'PRINT"[";INT(EXP(1)*1000);"]"', "direct", "FORM:exponential D-KWDRAIN"),
    ("log",     'a=log(1)',           'PRINT"[";LOG(1);"]"',           "direct", "FORM:logarithm D-KWDRAIN"),
    ("mod",     'a=7 mod 3',          'PRINT"[";7 MOD 3;"]"',          "direct", "FORM:modulo D-KWDRAIN"),
    ("notop",   'a=not 0',            'PRINT"[";NOT 0;"]"',            "direct", "FORM:bitwise-not D-KWDRAIN"),
    ("andop",   'a=5 and 3',          'PRINT"[";5 AND 3;"]"',          "direct", "FORM:bitwise-and D-KWDRAIN"),
    ("orop",    'a=5 or 3',           'PRINT"[";5 OR 3;"]"',           "direct", "FORM:bitwise-or D-KWDRAIN"),
    ("xorop",   'a=5 xor 3',          'PRINT"[";5 XOR 3;"]"',          "direct", "FORM:bitwise-xor D-KWDRAIN"),
    ("oct",     'a$=oct$(8)',         'PRINT"[";OCT$(8);"]"',          "direct", "FORM:to-octal D-KWDRAIN"),
    # 🌾 D-KWBARS: `VAL` had NO kwsweep row at all -- not a thin one, none -- and no
    # authored bar. The bar comes from docs/spec-basic-val.md, which measured the
    # reference across 40 shapes and named the five things VAL does: a signed
    # INTEGER, a FRACTION, an EXPONENT, a RADIX PREFIX, and a PARTIAL PARSE that
    # stops at the first byte it cannot use. ⚠️ `VAL` NEVER RAISES ON JUNK -- it
    # returns 0 -- so a wrong answer here is SILENT, which is why each row reads a
    # value no other form produces rather than checking that it did not error.
    ("valkw",   'a=val("-12")',       'PRINT"[";VAL("-12");"]"',       "direct",
     "FORM:integer the signed integer path"),
    ("valkw_b", 'a=val("1.5")',       'PRINT"[";VAL("1.5");"]"',       "direct",
     "FORM:fraction 1.5, not 1: the DECIMAL POINT. Truncating to the integer path "
     "is what this row is for (docs/spec-basic-val.md \u00a72 measured exactly that)"),
    ("valkw_c", 'a=val("1e3")',       'PRINT"[";VAL("1E3");"]"',       "direct",
     "FORM:exponent 1000, not 1: the EXPONENT is consumed, not left as junk"),
    ("valkw_d", 'a=val("&hff")',      'PRINT"[";VAL("&HFF");"]"',      "direct",
     "FORM:radix-prefix 255: `&H` is a RADIX, and a scanner that only knows decimal "
     "reads 0 here -- the silent wrong answer, not an error"),
    ("valkw_e", 'a=val("12abc")',     'PRINT"[";VAL("12ABC");"]"',     "direct",
     "FORM:partial-parse 12: the scan STOPS at the first byte it cannot use and "
     "keeps what it had, where `VAL(\"ABC\")` is 0"),
    ("left",    'a$=left$("abc",2)',  'PRINT"[";LEFT$("abc",2);"]"',   "direct", "FORM:prefix D-KWDRAIN"),
    ("right",   'a$=right$("abc",2)', 'PRINT"[";RIGHT$("abc",2);"]"',  "direct", "FORM:suffix D-KWDRAIN"),
    ("str",     'a$=str$(5)',         'PRINT"[";STR$(5);"]"',          "direct", "FORM:number-to-string D-KWDRAIN"),
    ("stringf", 'a$=string$(3,"x")',  'PRINT"[";STRING$(3,"x");"]"',   "direct", "FORM:repeat D-KWDRAIN"),
    ("space",   'a$=space$(3)',       'PRINT"[";LEN(SPACE$(3));"]"',   "direct", "D-KWDRAIN"),
    # 🌾 D-KWBATCH5: A LENGTH CANNOT SEE CONTENT -- the second screening axis, and
    # `space` reads `LEN(SPACE$(3))`, which a SPACE$ returning "xxx" passes. This
    # reads the BYTES, first and last, so the padding has to actually be spaces and
    # the string has to be spaces all the way through rather than one space and two
    # of something else.
    # ⏱ D-KWTLONG (2026-09-24): SPLIT SO EVERY STATEMENT TYPES IN 38 COLUMNS --
    # kwtime types explicitly numbered lines and cannot deliver one longer, so
    # this row's keyword had no T2 reading. The READING is unchanged: `B$` holds
    # the same RIGHT$ the PRINT used to compute inline.
    ("space_b", 'a$=space$(3)',
     'A$=SPACE$(3):B$=RIGHT$(A$,1):PRINT"[";ASC(A$);ASC(B$);"]"',        "stored",
     "FORM:pad the CONTENT, not the length -- `[ 32  32 ]`, the first byte and the "
     "last, both the space character."),
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
    ("csrlind", 'a=csrlin',           'A=CSRLIN:PRINT:PRINT"[";CSRLIN-A;"]"', "stored",
     "FORM:row-read D-KWDRAIN"),
    ("let",     'let a=5',            'LET A=5:PRINT"[";A;"]"',        "direct", "FORM:assign D-KWDRAIN"),
    ("rem",     'rem x',              'PRINT"[";1;"]":REM z',          "direct", "FORM:comment D-KWDRAIN"),

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
    # 🔴 D-KWTRIGVAL: `rnd`'s `RND(1)<1` IS A BOOLEAN and a stub returning 0
    # satisfies it -- but `rnd_b` FURTHER DOWN ALREADY READS THE RESEEDED DRAW
    # (438 on both references), so RND needed a TAG, not a row. The duplicate-key
    # guard caught the row I was about to add, for the second time today.
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
     "FORM:reseeded-draw references and here, so the generator itself agrees."),
    ("cvi",      'a=cvi("ab")',        'PRINT"[";CVI(MKI$(7));"]"',              "direct",
     "NEEDS-DISK: " "absent => syntax error; real => 7. 🔴 TAGGED AFTER THE FACT: "
     "written untagged it came back EXTRA -- ref `Illegal function call` vs zb "
     "`[ 7 ]` -- which is EXACTLY the mis-attribution this file's header "
     "describes, a diskless VG-8020 measured against zerobas's disk-equipped "
     "build and the difference blamed on zerobas. The rest of the MK/CV family "
     "FORM:string-to-int was already tagged; this row simply had not been."),
    ("using",   'using "##"',         'PRINT USING"##";7',                    "direct",
     "SUBJECT:PRINT_USING FORM:integer-field D-KWDRAIN"),
    # 🌾 D-KWBREADTH batch 4: the `using` row covers ONE format string, and `##`
    # is the one that needs no fraction, no rounding and no sign. `#.##` needs all
    # three -- 3.146 must round to 3.15, not truncate to 3.14.
    ("using_b", 'using "#.##"',
     'PRINT"[";:PRINT USING"#.##";3.146;:PRINT"]"',                      "stored",
     "SUBJECT:PRINT_USING FORM:fraction-field D-KWDRAIN: the FRACTIONAL field, "
     "where `##` cannot reach -- placement of the point AND the rounding of the "
     "discarded digit"),
    # D-KWPARTIAL: the format string is a small language and its FIELD TYPES are the
    # forms. Two were covered; these are the other three.
    ("using_c", 'using "+##"',
     'PRINT"[";:PRINT USING"+##";7;:PRINT"]"',        "stored",
     "SUBJECT:PRINT_USING FORM:sign the explicit SIGN field, which a format "
     "handler that only counts digit positions drops."),
    ("using_d", 'using "!"',
     'PRINT"[";:PRINT USING"!";"ABC";:PRINT"]"',      "stored",
     "SUBJECT:PRINT_USING FORM:string-field `!` takes the FIRST character of the "
     "string argument, so `ABC` prints as `A` -- a numeric-only format handler "
     "cannot do it at all."),
    ("using_e", 'using "##.##^^^^"',
     'PRINT"[";:PRINT USING"##.##^^^^";123.4;:PRINT"]"',  "stored",
     "SUBJECT:PRINT_USING FORM:exponential the `^^^^` EXPONENTIAL field. The exact "
     "spacing is not predicted here; what makes it a reading is that both machines "
     "must produce the same one."),
    ("then",    'then a=1',           'IF 2>1 THEN PRINT"[3]"',               "direct", "D-KWDRAIN"),
    ("elsekw",  'else a=1',           'IF 0 THEN PRINT 1 ELSE PRINT"[8]"',    "direct", "D-KWDRAIN"),
    ("tokw",    'to 5',               'FOR I=1 TO 3:NEXT:PRINT"[";I;"]"',     "direct", "D-KWDRAIN"),
    ("stepkw",  'step 2',             'FOR I=1TO5STEP2:NEXT:PRINT"[";I;"]"',  "stored", "D-KWDRAIN"),
    ("offkw",   'off',                'INTERVAL OFF:PRINT"[9]"',              "direct", "D-KWDRAIN"),
    ("ifkw",    'if 1 then a=2',      'IF 3>2 THEN PRINT"[4]"',               "direct", "FORM:then D-KWDRAIN"),
    # 🌾 D-KWIF2: IF's other two forms. `ifkw` above takes the THEN branch, so it
    # cannot see an ELSE that was parsed and dropped, nor the `IF ... GOTO` form,
    # which is a different grammar and not a THEN with a GOTO after it.
    # 🔴 AND IT IS **STORED**, NOT DIRECT, THOUGH IT FITS. At exactly 38 chars it
    # clears the MAX_DIRECT guard and still came back `?noecho` on BOTH machines:
    # the ceiling is reachable but the ECHO is not usable there. Same shape as
    # `vpoke_b2`, whose note records the same lesson at 37. Stored with its own
    # marker instead.
    # ⏱ D-KWTLONG (2026-09-24): `?` for PRINT -- the same token, 12 columns
    # shorter, so kwtime can type the line (it was 41 with its `10 `).
    ("ifkw_b",   'if 0 then a=1 else a=2',
     'IF 0 THEN ?"[1i]" ELSE ?"[1h]"',                "stored",
     "NOECHO:[1h FORM:else the ELSE branch, taken because the condition is FALSE. "
     "`[1h]`; an "
     "ELSE that was parsed and dropped prints nothing at all, and one that fell "
     "through to the THEN prints `[1i]`."),
    # 🎯 `IF <expr> GOTO <line>` -- no THEN. The padding forces the PRINT onto line
    # 40 so the jump has a target; verified with omsx_repl.as_stored first, and it
    # is long ASSIGNMENTS rather than `REM`, which would swallow the rest of its
    # line the way onkw_b's first cut did.
    ("ifkw_c",   'if 3>2 goto 40',
     'A=0:IF 3>2 GOTO 40:A=7:Z$="XXXXXXXXXXXXXXXXXXXXXXXX":Y$="YYYYYYYYYYYYYYYYYYYYYYYY":PRINT"[1j";A;"]"',
     "stored",
     "NOECHO:[1j FORM:goto the THEN-less form. `A=7` sits AFTER the jump on line 10 "
     "and must be skipped, so `[1j 0 ]`; an IF that fell through reads `[1j 7 ]`."),
    # 🌾 D-KWBARS: `FOR` HAD NO ROW OF ITS OWN -- every FOR in this file is a
    # NEXT row's apparatus, and a loop that runs is not the same claim as a loop
    # whose TERMINATION was decided correctly. Three forms from the reference's
    # syntax `FOR <var>=<a> TO <b> [STEP <c>]`: the IMPLIED step of 1, an explicit
    # STEP, and a NEGATIVE step -- which is not a third operand but a REVERSED
    # terminating comparison, the one a `>=` written as `<=` gets wrong.
    ("forkw",   'for i=1 to 3',
     'S=0:FOR I=1 TO 3:S=S+I:NEXT:PRINT"[";S;"]"',            "stored",
     "FORM:ascending 6 = 1+2+3: every iteration ran and the loop STOPPED at 3"),
    ("forkw_b", 'for i=1 to 9 step 4',
     'S=0:FOR I=1 TO 9 STEP 4:S=S+I:NEXT:PRINT"[";S;"]"',     "stored",
     "FORM:step 15 = 1+5+9: the INCREMENT is the operand, not 1, and the last "
     "iteration is the one at 9 -- a STEP that was parsed and dropped reads 45"),
    ("forkw_c", 'for i=3 to 1 step -1',
     'S=0:FOR I=3 TO 1 STEP -1:S=S*10+I:NEXT:PRINT"[";S;"]"', "stored",
     "FORM:negative-step 321: the comparison REVERSES with the sign of the step. "
     "Run with the ascending test the body executes ONCE and reads 3"),
    ("nextkw",  'next i',             'FOR I=1 TO 2:NEXT:PRINT"[";I;"]"',     "direct", "FORM:bare D-KWDRAIN"),
    # D-KWBATCH7: NEXT has three forms and only the BARE one had a row.
    # `ex_next` parks 0 for a bare NEXT ("match the top frame") and `nx_comma`
    # parks 1 (basic/program.asm), so the named and comma-list forms take a
    # DIFFERENT path through the frame search.
    ("nextkw_b", 'next i',
     'FOR I=1 TO 2:NEXT I:PRINT"[";I;"]"',           "direct",
     "FORM:named the NAMED form, which must MATCH the frame rather than take the "
     "top one."),
    ("nextkw_c", 'next j,i',
     'FOR I=1 TO 2:FOR J=1 TO 2:NEXT J,I:PRINT"[";I;J;"]"',  "stored",
     "FORM:comma-list one NEXT closing TWO frames, innermost first. `[ 3  3 ]` -- "
     "both loops ran to completion, where a comma list that closed only the first "
     "leaves the outer loop open and I at 1."),
    ("clearkw", 'clear 100',          'CLEAR 100:PRINT"[5]"',                 "direct",
     "D-KWDRAIN: FORM:string-space"),
    # 🌾 D-KWBREADTH batch 5: `clearkw` prints a CONSTANT MARKER, so it scores that
    # the word RAN and nothing about what it DID. CLEAR's defining effect is that
    # it resets variables; `A=A+1` after it reads 1 only if A really went to 0.
    ("clear_b", 'clear',              'A=5:CLEAR:A=A+1:PRINT"[";A;"]"',        "direct",
     "D-KWDRAIN: FORM:bare CLEAR's EFFECT, not its existence -- `[ 1 ]` proves A was reset "
     "to 0; a CLEAR that did nothing leaves 6"),
    # 🎚️ D-KWTIER1: CLEAR's THIRD form, `CLEAR n,himem`, sets the top of memory
    # BASIC may use (`HIMEM`, $FC4A, declared in basic/sysvars.inc). MEASURED in
    # scratchpad/clearhimem_probe.py on all three machines BEFORE this row existed,
    # because it carries two hazards at once:
    #   * it lowers a GLOBAL ceiling, so every row after it would run with less
    #     memory unless the original is put back (the `AUTO` hazard, once 21 rows);
    #   * `CLEAR` WIPES VARIABLES, so the original cannot be held in one (the
    #     `MAXFILES` trap, where the restore destroyed the value it protected).
    # 🎯 SO THE ORIGINAL IS PARKED IN RAM at $E003/$E004 -- ABOVE the lowered
    # ceiling, where BASIC will not touch it ($E001 is runkw's, $E002
    # deleterange_probe's) -- and the restore runs AFTER the readout.
    # 🔬 AND THE READING IS THE **SET** VALUE, NOT THE RESTING ONE: at rest HIMEM is
    # 62336 on the VG-8020 and here but 56951 on the CF-3300 (its disk ROM steals
    # RAM), so a row reading the resting value would DIVERGE for a reason that is
    # not a defect. 53248 (=$D000) is what all three read once it is SET.
    # ⚠️ `CLEAR 100,B` rather than the 39-char expression: a single statement over
    # 34 chars fits NEITHER mode, and the split form was measured to still see B --
    # the argument is evaluated before the clear takes effect.
    ("clear_c",  'clear 100,&hd000',
     'POKE&HE003,PEEK(&HFC4A):POKE&HE004,PEEK(&HFC4B):CLEAR 100,&HD000:A=PEEK(&HFC4A)+256*PEEK(&HFC4B):PRINT"[";A;"]":B=PEEK(&HE003)+256*PEEK(&HE004):CLEAR 100,B',
     "stored",
     "D-KWDRAIN: FORM:himem the HIMEM form -- 53248, the ceiling it SET, measured "
     "on all three machines. The resting value differs between the references and "
     "is deliberately not what this reads."),
    ("dimkw",   'dim a(2)',           'DIM D(2):D(1)=5:PRINT"[";D(1);"]"',    "direct", "FORM:one-dimensional D-KWDRAIN"),
    # 🌾 D-KWBATCH6: the MULTI-dimensional form, where the subscripts have to be
    # combined into one offset. `dimkw` uses a single subscript, which cannot see
    # a stride computed the wrong way round.
    ("dimkw_b", 'dim e(2,3)',
     'DIM E(2,3):E(1,2)=7:PRINT"[";E(1,2);E(2,1);"]"',  "stored",
     "FORM:multi-dimensional `[ 7  0 ]` -- the cell written and the cell with the "
     "SUBSCRIPTS SWAPPED, which a row-major/column-major mix-up would light up "
     "instead."),

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
    # 🔴 D-PSGLATCH (2026-09-24): THE READ IS SYNCED TO THE INTERRUPT. In a
    # batch the VG-8020 read R0 = 191 ($BF, the idle value of R14, the joystick
    # port) against the 123 just written -- and 123 on BOTH run alone. The
    # reference's interrupt service SELECTS R14 to scan the joystick, so one
    # landing between `OUT&HA0,0` and `INP(&HA2)` reads the wrong register;
    # zerobas's leaves the latch alone. Moving this row ahead of the BEEP rows
    # was tried first, on a wrong diagnosis, and changed nothing -- the row
    # stays there harmlessly. Now line 20 waits for TIME to tick and line 30
    # selects and reads inside the next 20 ms; the REM pads line 20 so the OUT
    # cannot be packed onto the IF's line, where a false IF would skip it.
    ("sound_b", 'sound 0,123',
     'SOUND 0,123:T9=TIME:FOR J9=1 TO 2:J9=1-(TIME<>T9):NEXT:OUT&HA0,0:PRINT"[";INP(&HA2);"]"', "stored",
     "FORM:register-value D-KWDRAIN: SOUND's EFFECT, not its existence -- the byte "
     "is read back out of the PSG. A SOUND that parsed and wrote nothing reads "
     "something else."),
    ("beep",    'beep',               'BEEP:PRINT"[6]"',                      "direct",
     "FORM:no-argument D-KWDRAIN"),
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
     'SOUND 7,255:BEEP:T9=TIME:FOR J9=1 TO 2:J9=1-(TIME<>T9):NEXT:OUT&HA0,7:PRINT"[";INP(&HA2);"]"',                     "stored",
     "WEAK: " "D-KWBATCH5 DEMOTED THIS ROW: IT READS A TRANSIENT AND THE TWO "
     "MACHINES DIFFER IN SPEED. The mixer is restored when the beep FINISHES, so "
     "184 (sounding) vs 191 (finished) is a race between the beep and the OUT/INP "
     "two statements later. Measured 2026-09-14: ALONE both machines read 184; in "
     "the full sweep the reference reads 191 and zerobas 184, deterministically "
     "over two runs -- zerobas is 2.5-3.8x slower (the open on-par-speed item), so it is "
     "still sounding when the reference has stopped. The row was SUPPORTED for as "
     "long as batching happened to put the same neighbours before it. "
     "🎯 `beep_c` below reads a register BEEP does NOT put back, which has no such "
     "race. THE ORIGINAL NOTE'S CLAIM IS STILL TRUE, it just is not SCOREABLE."),
    ("beep_c",  'beep',
     'SOUND 0,0:BEEP:T9=TIME:FOR J9=1 TO 2:J9=1-(TIME<>T9):NEXT:OUT&HA0,0:PRINT"[";INP(&HA2);"]"',                     "stored",
     "FORM:no-argument BEEP's effect on a register it does not have to put back "
     "-- channel A's tone-period low byte, zeroed first."),
    ("sound",   'sound 7,255',        'SOUND 7,255:PRINT"[7]"',               "direct",
     "FORM:register-value D-KWDRAIN"),
    # 🌾 D-KWBREADTH batch 6: `sound` writes PSG register 7 and prints a CONSTANT
    # MARKER, so it scores that the word ran and nothing about what landed. The PSG
    # HAS a readback path -- `OUT &HA0,<reg>` selects, `INP(&HA2)` reads -- so the
    # effect is observable after all. Register 0 (channel A fine tune) is used
    # rather than 7 because it is a plain 8-bit cell and because the MIXER is left
    # exactly as it was: nothing is made audible by this row.

    # ---------------------------------------------------------- D-KWPLAY: `PLAY`
    # 🎯 PLAY WAS 0 OF ITS FORMS AND THE REASON WAS THE INSTRUMENT. `make
    # play-acceptance` observes music with `PLAY(n)`, which answers only WHICH
    # VOICE is sounding -- so it covers `multi-voice` and NOTHING else: pitch,
    # volume, envelope and duration are all invisible to it. These rows read the
    # PSG BACK instead, exactly as `sound_b` above does (`OUT&HA0,<reg>` selects,
    # `INP(&HA2)` reads), which works LIVE while the drain is sounding the note.
    # 🔴 THREE DEFECTS FELL OUT OF DESIGNING THEM, and two were fixed in the same
    # slice (2026-09-15, scratchpad/playpsg_probe.py, playmml_probe.py,
    # playnote_probe.py -- each measured on the VG-8020 AND the CF-3300):
    #   * `N n` was A SEMITONE FLAT. The reference indexes its period table AT n;
    #     the tenant did `dec a` first. Every N from 1 to 96 was wrong, and the
    #     host test agreed with it because both came from the same generator.
    #   * `>` and `<` WERE IMPLEMENTED HERE AND ARE NOT MSX1 MML. Both references
    #     answer Illegal function call to all three spellings tried. Removed --
    #     and tools/kwforms.py's PLAY bar went from ELEVEN forms to TEN with them.
    #   * `X<var>;` IS MSX1 MML AND IS NOT IMPLEMENTED HERE. Both references sound
    #     `A$="O7L1C":PLAY"XA$;"`; this tree raises ERR 5. THE ONE REMAINING GAP,
    #     so `substring-exec` has no row and PLAY stops at 9 of 10.
    # ⚠️ EVERY ROW SETS ITS OWN `O`/`L`/`T`/`V` INSIDE ITS OWN MML STRING. The
    # VCB state PERSISTS ACROSS `PLAY` STATEMENTS (tests/test_play_parse.py "state
    # persists"), which is DRAW's ANGLE/SCALE hazard wearing a different hat; a row
    # that relied on the defaults would read whatever its neighbour left behind.
    # ⚠️ `AND 15` IS NOT COSMETIC. The VG-8020 reads R8 back as $80|value and R13
    # as $D0|value -- STABLE, not noise (three reads in one run gave three equal
    # answers), but different from this machine's bare value. The low nibble is the
    # register; the high bits are the two emulated PSGs disagreeing, not BASIC.
    # 🔴 THE TWO DURATION ROWS GO LAST, AND THAT IS THE `save_b` RULE AGAIN: they
    # END WITH MUSIC STILL PLAYING (50 and 93 frames queued against a 40-frame
    # wait), so anything after them that read the PSG would read their leftovers.
    ("playkw",   'play"c"',
     'PLAY"O4L1T120V8C":FOR I=1 TO 200:NEXT:T9=TIME:FOR J9=1 TO 2:J9=1-(TIME<>T9):NEXT:OUT&HA0,0:A=INP(&HA2):PRINT"[3i";A;"]"',
     "stored",
     "FORM:notes 172 -- the LOW BYTE of channel A's tone period while C sounds "
     "(the full period is 428, the VG-8020-measured C4). A PLAY that queued "
     "nothing leaves the register GICINI set it to"),
    ("playkw_b", 'play"n40"',
     'PLAY"L1T120V8N40":FOR I=1 TO 200:NEXT:T9=TIME:FOR J9=1 TO 2:J9=1-(TIME<>T9):NEXT:OUT&HA0,0:A=INP(&HA2):PRINT"[3j";A;"]"',
     "stored",
     "FORM:note-number 83, where the letter form reads 172: `N40` names a note by "
     "NUMBER and lands a fourth above C4. 🔴 THIS ROW READ 104 UNTIL 2026-09-15 -- "
     "one semitone flat, for every n in 1..96"),
    ("playkw_c", 'play"r"',
     'PLAY"O4L1T120V8C","O4L1T120V8R":FOR I=1 TO 200:NEXT:T9=TIME:FOR J9=1 TO 2:J9=1-(TIME<>T9):NEXT:OUT&HA0,8:A=INP(&HA2)AND15:OUT&HA0,9:B=INP(&HA2)AND15:PRINT"[3k";A;B;"]"',
     "stored",
     "FORM:rest `8 0` -- voice 1 sounds a note at the default volume and voice 2 "
     "RESTS, so the two channel amplitudes differ. 🎯 THE 8 IS THIS ROW'S OWN "
     "CONTROL: give voice 2 a NOTE instead and it reads `8 8`, so the 0 is the "
     "rest and not an absence"),
    ("playkw_d", 'play"o7c"',
     'PLAY"O7L1T120V8C":FOR I=1 TO 200:NEXT:T9=TIME:FOR J9=1 TO 2:J9=1-(TIME<>T9):NEXT:OUT&HA0,0:A=INP(&HA2):PRINT"[3l";A;"]"',
     "stored",
     "FORM:octave 53 against the same note's 172 three octaves down -- `O n` moves "
     "the WHOLE note table, and the period halves per octave"),
    # 🌾 PLAY X (spec-basic-audio-play §7.12, Joost 2026-09-24 "Tenant walks the
    # chain"): the tenth FORM. The string is reached THROUGH the variable chain,
    # and A%/B!/C#/D$ are defined FIRST so the tenant's walk must stride over an
    # int, a single, a double and a string (6 B) before it finds E$ -- the row IS
    # the gate that its walk agrees with scv_find's layout. Without X this reads
    # ERR 5 and no tone; `PLAY"XA$"` (no `;`) would agree for the WRONG reason.
    ("playkw_x", 'play"xe$;"',
     'A%=1:B!=2:C#=3:D$="Q":E$="O7L1T120V8C":PLAY"XE$;":FOR I=1 TO 200:NEXT:T9=TIME:FOR J9=1 TO 2:J9=1-(TIME<>T9):NEXT:OUT&HA0,0:A=INP(&HA2):PRINT"[3x";A;"]"',
     "stored",
     "FORM:substring-exec 53 -- O7 C reached through `X E$;`, after the chain walk "
     "strides over A% B! C# D$; ERR 5 and no reading without X"),
    ("playkw_e", 'play"v3c"',
     'PLAY"O4L1T120V3C":FOR I=1 TO 200:NEXT:T9=TIME:FOR J9=1 TO 2:J9=1-(TIME<>T9):NEXT:OUT&HA0,8:A=INP(&HA2)AND15:PRINT"[3o";A;"]"',
     "stored",
     "FORM:volume 3 -- PSG R8 is channel A's amplitude and the DEFAULT is 8, so a "
     "`V` that parsed and did nothing reads 8 here"),
    ("playkw_f", 'play"s10m2000c"',
     'PLAY"O4L1T120S10M2000C":FOR I=1 TO 200:NEXT:T9=TIME:FOR J9=1 TO 2:J9=1-(TIME<>T9):NEXT:OUT&HA0,13:A=INP(&HA2)AND15:OUT&HA0,11:B=INP(&HA2):OUT&HA0,12:C=INP(&HA2):PRINT"[3p";A;B;C;"]"',
     "stored",
     "FORM:envelope `10 208 7` -- R13 is the envelope SHAPE (`S10`) and R11/R12 "
     "the 16-bit envelope PERIOD, 7*256+208 = 2000 (`M2000`). Three cells, two "
     "commands, and no default produces any of them"),
    ("playkw_g", 'play"","","c"',
     'PLAY"","","O4L2T120V8C":FOR I=1 TO 200:NEXT:A=PLAY(1):B=PLAY(2):C=PLAY(3):PRINT"[3q";A;B;C;"]"',
     "stored",
     "FORM:multi-voice `0 0 -1` -- the THIRD string sounds and the first two are "
     "the faithful empty-voice skip. An implementation with one voice, or one that "
     "took the last string as the first, cannot read this"),
    ("playkw_h", 'play"l64c"',
     'A=0:B=0:PLAY"O4T120V8L64C":T=TIME:W$="WWWWWWWWWWWW":IF TIME-T<40 THEN 30:U$="UUUUUUUUUUUUUU":A=PLAY(0):PLAY"O4T120V8L2C":T=TIME:V$="VVVVVVVVVVVV":IF TIME-T<40 THEN 70:X$="XXXXXXXXXXXXXX":B=PLAY(0):PRINT"[3m";A;B;"]"',
     "stored",
     "FORM:default-length `0 -1` -- the SAME note at `L64` has finished after 40 "
     "frames and at `L2` has not. ⚠️ THE WAIT IS FRAMES VIA `TIME`, NOT "
     "ITERATIONS: `L64` is 1 frame and `L2` is 50, and a `FOR` loop counts "
     "INTERPRETER SPEED -- the reference is ~3x faster, and a 200-iteration wait "
     "sat on the WRONG side of `L64` there and the right side here"),
    ("playkw_i", 'play"t32c"',
     'A=0:B=0:PLAY"O4L4V8T255C":T=TIME:W$="WWWWWWWWWWWW":IF TIME-T<40 THEN 30:U$="UUUUUUUUUUUUUU":A=PLAY(0):PLAY"O4L4V8T32C":T=TIME:V$="VVVVVVVVVVVV":IF TIME-T<40 THEN 70:X$="XXXXXXXXXXXXXX":B=PLAY(0):PRINT"[3n";A;B;"]"',
     "stored",
     "FORM:tempo `0 -1` with the LENGTH held fixed at `L4`, so only `T` explains "
     "it: 11 frames at `T255` against 93 at `T32`, either side of the same 40-frame "
     "wait"),
    ("vpeek",   'a=vpeek(0)',         'VPOKE 0,7:PRINT"[";VPEEK(0);"]"',      "direct",
     "FORM:address-read D-KWDRAIN"),
    ("vpoke",   'vpoke 0,1',          'VPOKE 0,9:PRINT"[";VPEEK(0);"]"',      "direct",
     "FORM:address-value D-KWDRAIN"),
    ("vdpkw",   'a=vdp(1)',           'PRINT"[";VDP(1)>0;"]"',                "direct",
     "FORM:read D-KWDRAIN"),
    # 🌾 D-KWBREADTH batch 8: a BOOLEAN reading scores only that a value falls in a
    # half-plane, never the VALUE. `VDP(1)>0` is -1 for anything non-zero, so every
    # wrong-but-non-zero register read passes it -- and the note beside the row
    # already says the number is 240 against a stub's 0, so the value was known and
    # simply not scored.
    ("vdp_b",   'a=vdp(1)',           'PRINT"[";VDP(1);"]"',                  "direct",
     "FORM:read D-KWDRAIN: the VDP register's VALUE, not its non-zero-ness -- 240. "
     "The `vdpkw` row's `>0` passes on any wrong non-zero read."),
    # 🌾 D-KWBATCH2: `VDP(n)` IS ALSO AN ASSIGNMENT TARGET, and every row above
    # reads. `ex_vdp_assign` (basic/interp.asm:747) is a SEPARATE handler from the
    # `$C8` selector in expr.asm, so the read rows cannot speak for it at all.
    # 🔴 WHAT THIS ROW CAN AND CANNOT PROVE, SAID PLAINLY: MSX VDP registers are
    # WRITE-ONLY at the chip, so no reader anywhere can see what the chip got.
    # `VDP(n)` reads the RGnSAV mirror. The row therefore scores the ASSIGNMENT
    # PATH -- parse, evaluate, store the value written -- and it uses TWO DIFFERENT
    # values so a handler that stored a constant, or ignored the assignment and
    # left the old value, fails on the second reading.
    ("vdp_c",   'vdp(7)=5',
     'VDP(7)=5:A=VDP(7):VDP(7)=4:B=VDP(7):PRINT"[0d";A;B;"]"',  "stored",
     "NOECHO:[0d FORM:write the ASSIGNMENT form `VDP(n)=v`, which has its own "
     "handler (ex_vdp_assign) and which no read row reaches. `[0d 5  4 ]` -- two "
     "different values, so a stored constant or an ignored assignment is visible. "
     "Register 7 is the backdrop colour, which does not disturb the text plane."),
    # 🌾 D-KWBATCH3, AND IT RETRACTS THE LIMIT THE ROW ABOVE STATES (Joost,
    # 2026-09-14: *"if you choose a clever write, you can see the effects in the
    # visual appearance of the screen"*). He is right that the effect is reachable;
    # it is not reachable through THIS capture, which scrapes VRAM $0000 directly
    # and therefore sees the NAME TABLE rather than the display -- a blanked
    # screen, a changed backdrop and even a moved name-table base all read the same
    # to it. So the row takes the same idea one step further and finds an effect a
    # PROGRAM can measure.
    # 🔴 VDP REGISTER 1 BIT 5 IS THE FRAME-INTERRUPT ENABLE. Clear it and the
    # 50/60 Hz interrupt stops, so JIFFY stops and TIME FREEZES. Nothing but the
    # real chip can produce that: a handler that stored the value in the RGnSAV
    # mirror and never reached the port leaves the interrupt running and TIME
    # advancing. This is the CHIP-side witness `vdp_c` cannot be.
    # ⚠️ SAVE AND RESTORE THE REAL VALUE (`V AND 223`, then `VDP(1)=V`) rather than
    # hardcoding $F0.
    # 🔴 AND **ONE** LOOP, NOT TWO -- THE GUARD I FIRST BUILT INTO THIS ROW TURNED
    # IT INTO A SPEED MEASUREMENT. A delay loop too short to tick would read A=0
    # for a reason that has nothing to do with the VDP, so the first cut re-ran the
    # same loop with the interrupt back on and required that TIME advanced. That
    # doubled the run, and zerobas is 2.5-3.8x slower than the reference (the open
    # on-par-speed item), so the pair outran the capture window: the reference answered
    # `[0l 0 -1 ]` and zerobas printed NOTHING AT ALL, and the row reported
    # INTERPRETER SPEED as a VDP divergence. Measured apart in
    # scratchpad/vdpie_probe.py, where the single-loop shape reads `[1 0 ]` on BOTH
    # machines -- the write does reach the chip on both.
    # 🎯 THE GUARD COMES FROM ANOTHER ROW INSTEAD: `timetick` runs the SAME 400
    # iterations with the interrupt ON and requires `TIME>T`, so "the loop is long
    # enough to tick" is established there and does not have to be paid for here.
    ("vdp_d",   'vdp(1)=208',
     'V=VDP(1):VDP(1)=V AND 223:T=TIME:FOR I=1 TO 400:NEXT:A=TIME-T:VDP(1)=V:PRINT"[0l";A;"]"',
     "stored",
     "NOECHO:[0l FORM:write the write reaching the CHIP, not the mirror: clearing "
     "VDP register 1 bit 5 stops the frame interrupt, so JIFFY stops and TIME "
     "FREEZES. `[0l 0 ]` -- a handler that stored the value in the RGnSAV mirror "
     "and never reached the port leaves the interrupt running and TIME advancing. "
     "`timetick` is what proves 400 iterations DO tick when the interrupt is on."),
    # 🔴 `>0`, NOT `>=0`, AND THAT IS A FIX TO MY OWN ROW. The first cut asked
    # `INP(&HA8)>=0`, which an ABSENT INP passes too: the word would parse as an
    # undefined array, `INP(&HA8)` would be element 0, and `0>=0` is TRUE.
    # Measured (scratchpad/kwdrain_boolcheck.py): INP(&HA8) reads 240, the stub
    # shape ZZQ(0)>=0 reads -1 -- identical to the real answer. `>0` separates
    # them, because the stub gives 0. The VALUE itself cannot be asserted: &HA8
    # is the primary slot register and its content is a machine-layout fact, so
    # zerobas and the VG-8020 may legitimately differ. `vdpkw` was checked the
    # same way and is sound as written: VDP(1) reads 240 against the stub's 0.
    ("inpkw",   'a=inp(168)',         'PRINT"[";INP(&HA8)>0 ;"]"',            "direct",
     "FORM:port-read D-KWDRAIN"),
    # 🌾 D-KWBATCH3: THE ROW ABOVE IS A BOOLEAN AND CANNOT SEE THE VALUE -- the
    # fourth screening axis, and INP had nothing else. `INP(&HA8)>0` passes on any
    # wrong non-zero read, exactly the way `vdpkw`'s `>0` did before `vdp_b`.
    # This drives a KNOWN byte out to the PSG and reads that byte back, so the
    # reading is the value and not its non-zero-ness.
    ("inp_b",   'a=inp(&ha2)',
     'T9=TIME:FOR J9=1 TO 2:J9=1-(TIME<>T9):NEXT:OUT&HA0,0:OUT&HA1,66:OUT&HA0,0:PRINT"[";INP(&HA2);"]"',                 "stored",
     "FORM:port-read the VALUE, not its non-zero-ness -- 66, the byte just written "
     "to PSG register 0. `out_b` drives the same path but its SUBJECT is OUT; this "
     "row's crunch body is `a=inp(&ha2)`, so the reading is scored for INP."),
    ("outkw",   'out 160,7',          'OUT &HA0,7:PRINT"[8]"',                "direct",
     "FORM:port-value D-KWDRAIN"),
    # 🌾 D-KWBREADTH batch 6: the row above writes the PSG ADDRESS latch and scores
    # a marker; this one drives the whole OUT -> INP round trip through the DATA
    # port, so the byte it wrote is the byte that is read.
    ("out_b",   'out 161,77',
     'T9=TIME:FOR J9=1 TO 2:J9=1-(TIME<>T9):NEXT:OUT&HA0,0:OUT&HA1,77:OUT&HA0,0:PRINT"[";INP(&HA2);"]"',                 "stored",
     "FORM:port-value D-KWDRAIN: the value OUT actually DELIVERED, via the PSG's "
     "own readback. The `outkw` row writes only the address latch and never reads "
     "it back."),
    # 🔴 `WAIT` HAS NO ROW HERE, AND THE FIRST ATTEMPT IS WHY. `WAIT port,mask
    # [,xor]` blocks until ((INP(port) XOR xor) AND mask) <> 0, so a mask of 0 can
    # NEVER be satisfied: the row `WAIT &HA9,0:PRINT"[9]"` -- written believing
    # mask 0 meant "already true" -- blocks for ever BY DEFINITION, and zerobas
    # returning no output was it behaving CORRECTLY. Attributing WAIT needs a port
    # whose condition is satisfiable without blocking, and the obvious candidate
    # (the VDP status port, whose bit 7 sets every frame) is read-to-clear and
    # would disturb the BIOS interrupt handler. Left unattributed on purpose --
    # "no known gap" is the honest state for it until a safe row exists.
    # 🏗️ D-CURLIN (Joost, 2026-09-24): zerobas now maintains the published
    # CURLIN ($F41C) -- the current line NUMBER, $FFFF in direct mode -- which it
    # never wrote before (its run loop keeps a POINTER, CURLINE $E038). Read from
    # a stored line 10 it must say 10 on both machines. (Before the change
    # nothing in zerobas wrote the cell -- docs/sysvar-msx1-coverage.md lists
    # CURLIN among the cold-boot cells zerobas left uninitialised; what the OLD
    # ROM read in a running program was not measured.) Measured on the new ROM
    # first: 10 / 300 after a GOTO / 65535 direct, on both machines.
    ("peek_curlin", 'a=peek(&hf41c)',
     'A=PEEK(&HF41C)+256*PEEK(&HF41D):PRINT"[6c";A;"]"', "stored",
     "the published current-line cell, read by the line it names: `[6c 10 ]`."),
    ("pokekw",  'poke 0,1',           'POKE-8192,7:PRINT"[";PEEK(-8192);"]"', "stored",
     "FORM:address-value D-KWDRAIN"),

    # ---------------------------------------------- D-KWDRAIN step 4a (2026-09-12)
    # 🔴 A CORRECTION TO WHAT BATCH 3 FILED. I wrote that the display verbs "cannot
    # take a kwsweep row at all" because they destroy the echo this sweep anchors
    # on. That was the ANCHOR's limit, not the words': `marker_tail` above captures
    # from a unique per-row marker instead, which is what the arrays and deffn
    # suites have always done with `CLS:PRINT"[";...`. So the words come back in
    # reach, and the claim is retracted where it was made.
    # ⏱ `WIDTH 36` FIRST (D-KWT5FORM, 2026-09-24): the row's WIDTH 37 must be a
    # CHANGE on both machines, or kwtime times a re-init on one side and a no-op
    # on the other (zerobas boots at 39, the VG-8020 at 37 -- D-BOOTWIDTH). The
    # reading is unchanged: LINLEN is 37 after it either way. STORED now: the
    # two statements put the line over the 38-column direct-mode limit.
    ("widthkw", 'width 37',    'WIDTH 36:WIDTH 37:PRINT"[W";PEEK(-3152);"]"',  "stored",
     "NOECHO:[W FORM:text-width TIMED:2 WIDTH reformats the screen and takes the echo with it; the row reads LINLEN ($F3B0 = -3152) back, so a WIDTH that parses and does nothing still fails. absent => syntax error => no marker at all."),
    # 🌾 D-KWBATCH1: WIDTH'S SECOND FORM IS A DIFFERENT CELL, NOT A DIFFERENT
    # NUMBER. MSX keeps the text width PER MODE -- LINL40 ($F3AE) for SCREEN 0 and
    # LINL32 ($F3AF) for SCREEN 1 (both DECLARED in basic/sysvars.inc) -- and
    # `WIDTH` writes whichever belongs to the CURRENT mode. A WIDTH that always
    # wrote LINL40 passes `widthkw` and fails here, which is the whole point of
    # counting this as a second form rather than a second sample of the first.
    # 🎯 BOTH CELLS ARE SET BY THE ROW ITSELF (`WIDTH 37` first), so the reading
    # cannot depend on a boot default -- the VG-8020 and this repack do not agree
    # about which mode they start in, and a row that read an untouched LINL40
    # would be measuring the BOOT and reporting it as WIDTH.
    ("widthkw_b", 'width 29',
     'WIDTH 37:SCREEN1:WIDTH 29:A=PEEK(&HF3AF):B=PEEK(&HF3AE):SCREEN0:PRINT"[0a";A;B;"]"',
     "stored",
     "NOECHO:[0a FORM:mode1-width TIMED:2 the SCREEN 1 width, which lives in LINL32 "
     "($F3AF) and not in the LINL40 ($F3AE) cell `widthkw` reads. `[0a 29  37 ]`: "
     "the cell WIDTH must change AND the one it must leave alone, so a handler "
     "that wrote the wrong cell, or both, is visible either way."),
    # 🔴 D-WIDTHKEEP (2026-09-24): A WIDTH TO THE WIDTH ALREADY IN FORCE DOES
    # NOTHING ON THE REFERENCE -- and zerobas re-initialised the screen. Found by
    # T5's keyword-alone timing (`WIDTH 37` cost 32.0 ms here, 0.71 ms on the
    # VG-8020), then measured as BEHAVIOUR: after `PRINT"KKKK":WIDTH 37` the
    # VG-8020 still holds the four K's and the cursor on row 1 (SCREEN 0 and 1
    # alike), zerobas held none and homed the cursor. `widthkw` could never see
    # it: it reads LINLEN, which both sides set to 37 either way -- a row that
    # agreed for the wrong reason. The rule compares against LINLEN, not the
    # per-mode cell: with LINLEN poked to 30 the reference DOES re-init, with only
    # LINL40 poked it does not, and leaves LINL40 at 30 -- it does nothing at all.
    # `WIDTH 37` FIRST so the row never depends on the width a neighbour left.
    ("widthkw_c", 'width 37',
     'WIDTH 37:CLS:PRINT"KKKK":WIDTH 37:B=CSRLIN:C=0:FOR I=0 TO 119:C=C-(VPEEK(I)=75):NEXT:PRINT"[4w";C;B;"]"',
     "stored",
     "NOECHO:[4w FORM:same-width TIMED:2 a WIDTH to the width already in force keeps the "
     "screen and the cursor: `[4w 4  1 ]` = the four K's still in VRAM and the "
     "cursor still on row 1. A handler that re-initialises the screen reads "
     "`[4w 0  0 ]`."),
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
     "NOECHO:[Q FORM:centre-radius rim pixel is 15, centre is 4 -- a filled or "
     "absent circle fails"),
    # 🌾 D-KWBREADTH batch 10: the row above draws a FULL circle; the START/END arc
    # arguments are untouched. This draws only the upper-right quadrant and reads
    # TWO pixels, which is what makes it discriminating: a full circle gives 15 15,
    # a correct arc gives 15 4, and an absent CIRCLE gives 4 4. Reading the OFF-arc
    # pixel alone would have been blank-on-both-sides -- mode 2 -- because a CIRCLE
    # that drew nothing leaves it blank too.
    ("circlekw_b", 'circle(50,50),10,15,0,1.57',
     'SCREEN2:CIRCLE(50,50),10,15,0,1.57:A=POINT(60,50):B=POINT(40,50):SCREEN0:PRINT"[F";A;B;"]"',
     "stored",
     "NOECHO:[F FORM:arc the ARC arguments -- start 0 (rightmost) to end 1.57 rad "
     "(top), so (60,50) is ON the arc and (40,50) is not. 15 4 for an arc, 15 15 if "
     "the start/end are parsed and discarded."),
    # 🌾 D-KWBATCH3: the remaining three of CIRCLE's five forms. Grammar
    # (basic/graphics.asm:564): `CIRCLE [STEP](x,y),r[,[c][,[start][,[end][,aspect]]]]`.
    # 🎯 EACH ROW READS A PIXEL IT MUST DRAW **AND** ONE IT MUST NOT, because a
    # single rim reading cannot tell "drawn in the right place" from "drawn at all".
    ("circlekw_c", 'circle step(20,20),10,15',
     'SCREEN2:PSET(30,30),15:CIRCLE STEP(20,20),10,15:A=POINT(60,50):B=POINT(30,20):SCREEN0:PRINT"[0h";A;B;"]"',
     "stored",
     "NOECHO:[0h FORM:step-relative STEP is relative to the LAST POINT, which the "
     "PSET puts at (30,30), so the centre is (50,50) and (60,50) is on the rim. "
     "`[0h 15  4 ]`: an ignored STEP centres on (20,20) instead, which draws "
     "through (30,20) and leaves (60,50) blank -- both readings move."),
    ("circlekw_d", 'circle(50,50),20,15,,,.5',
     'SCREEN2:CIRCLE(50,50),20,15,,,.5:A=POINT(70,50):B=POINT(50,70):SCREEN0:PRINT"[0i";A;B;"]"',
     "stored",
     "NOECHO:[0i FORM:aspect the ASPECT argument halves the VERTICAL radius, so "
     "the x rim stays at (70,50) and (50,70) -- exactly on the rim of the circle "
     "an ignored aspect would draw -- falls outside the ellipse. `[0i 15  4 ]`; a "
     "discarded aspect reads `15  15`. The first reading is what says a shape was "
     "drawn at all, so the second cannot pass by drawing nothing."),
    ("circlekw_e", 'circle(50,50),10',
     'SCREEN2:COLOR 11:CIRCLE(50,50),10:A=POINT(60,50):B=POINT(50,50):SCREEN0:PRINT"[0j";A;B;"]":COLOR 15',
     "stored",
     "NOECHO:[0j FORM:colour-default the OMITTED colour, which must come from "
     "FORCLR -- `COLOR 11` first, so `[0j 11  4 ]` proves the rim took the "
     "foreground colour and not a hardcoded 15. The centre reading keeps a FILLED "
     "circle from passing, the way the `circlekw` row does."),
    ("drawkw",    'draw"c15r5"',      
     'SCREEN2:PSET(10,10),15:DRAW"A0S4C15R5":A=POINT(14,10):SCREEN0:PRINT"[D";A;"]"', "stored",
     "NOECHO:[D FORM:movement reads 4 pixels right of the start: blank is 4, drawn is 15"),
    # 🌾 D-KWBREADTH batch 10: the row above drives ONE direction command (`R`). A
    # DRAW that implemented only R -- or that ignored the letter entirely and moved
    # right -- passes it. `D` moves DOWN, so the pixel read is BELOW the start.
    ("drawkw_b",  'draw"c15d5"',
     'SCREEN2:PSET(10,10),15:DRAW"A0S4C15D5":A=POINT(10,14):SCREEN0:PRINT"[E";A;"]"',
     "stored",
     "NOECHO:[E FORM:movement a DIFFERENT direction command -- `D` draws DOWN, so this reads a "
     "pixel below the start where the `R` row reads one to the right. 15 drawn, "
     "4 blank."),
    # 🌾 D-KWDRAW9: the other NINE forms of the command language, every one read
    # back with `POINT` the way the two rows above are. spec-basic-graphics-g6.md
    # §1 is the surface they come from. The background in SCREEN 2 is 4 and the
    # drawn colour 15 unless a row says otherwise, so 4 and 15 are the two answers
    # every reading below is built out of.
    ("drawkw_c", 'draw"m50,50"',
     'SCREEN2:PSET(10,10),15:DRAW"A0S4C15M50,50":A=POINT(30,30):SCREEN0:PRINT"[2y";A;"]"',
     "stored",
     "NOECHO:[2y FORM:move-absolute 15 at (30,30): `M` DRAWS a line to the absolute "
     "point, so the midpoint of (10,10)-(50,50) is set"),
    ("drawkw_d", 'draw"m+20,+0"',
     'SCREEN2:PSET(10,10),15:DRAW"A0S4C15M+20,+0":A=POINT(25,10):SCREEN0:PRINT"[2z";A;"]"',
     "stored",
     "NOECHO:[2z FORM:move-relative 15 at (25,10): the SIGNED operands are a "
     "DISPLACEMENT from (10,10), so the line ends at (30,10). Read as ABSOLUTE it "
     "would go to (20,0) and (25,10) stays 4"),
    ("drawkw_e", 'draw"bm50,50r5"',
     'SCREEN2:PSET(10,10),15:DRAW"A0S4C15BM50,50R5":A=POINT(30,30):B=POINT(52,50):SCREEN0:PRINT"[3a";A;B;"]"',
     "stored",
     "NOECHO:[3a FORM:blank-prefix the move drew NOTHING on the way (30,30) and the "
     "`R5` after it drew at the NEW place (52,50). Reading only the first would be "
     "satisfied by a DRAW that did nothing at all"),
    ("drawkw_f", 'draw"nr5d3"',
     'SCREEN2:PSET(10,10),15:DRAW"A0S4C15NR5D3":A=POINT(12,10):B=POINT(10,12):SCREEN0:PRINT"[3b";A;B;"]"',
     "stored",
     "NOECHO:[3b FORM:no-update-prefix the `R5` drew AND the cursor went back, so "
     "the `D3` after it starts from (10,10) again. Without `N` the D3 would start "
     "at (15,10) and (10,12) stays 4"),
    ("drawkw_g", 'draw"c7r5"',
     'SCREEN2:PSET(10,10),15:DRAW"A0S4C7R5":A=POINT(14,10):SCREEN0:PRINT"[3c";A;"]"',
     "stored",
     "NOECHO:[3c FORM:colour 7, and the two rows above pass `C15` which IS THE "
     "DEFAULT FOREGROUND -- they say nothing about `C` at all. 7 is neither the "
     "default nor the background"),
    ("drawkw_h", 'draw"s8r2"',
     'SCREEN2:PSET(10,10),15:DRAW"A0C15S8R2":A=POINT(13,10):SCREEN0:PRINT"[3d";A;"]"',
     "stored",
     "NOECHO:[3d FORM:scale `S` is in QUARTERS and the default is 4, so `S8R2` "
     "travels FOUR pixels where the default `R2` travels two and leaves (13,10) "
     "at 4"),
    ("drawkw_i", 'draw"a1r5"',
     'SCREEN2:PSET(10,50),15:DRAW"S4C15A1R5":A=POINT(10,47):B=POINT(13,50):SCREEN0:PRINT"[3e";A;B;"]"',
     "stored",
     "NOECHO:[3e FORM:angle the 90-degree rotation: `R` stops going RIGHT. Both "
     "points are read so the reading says WHICH way it turned rather than only "
     "that it did"),
    # 🟢 `X<var>;` AND `=<var>;` WORK, AND THE FIRST CUT OF THESE TWO ROWS WAS
    # POISONED BY ITS OWN NEIGHBOUR. They read `4` -- the background -- on BOTH
    # machines and were dropped as "a row agreeing on an absence". The isolated
    # probe (scratchpad/drawsubst_probe.py, eight cases with a control) says
    # otherwise: `XA$;` draws, `XAB$;` draws with a two-letter name, `R=L;` draws,
    # `C=A;R5` reads **7** -- the substitution supplying a COLOUR -- and both
    # spellings WITHOUT the `;` raise ERR 5 exactly as
    # spec-basic-graphics-g6.md §147 says.
    # 🔴 THE CAUSE IS A STATE LEAK BETWEEN BATCHED CASES, AND IT IS FAITHFUL MSX:
    # `DRAW`'s ANGLE and SCALE persist across programs. `drawkw_i` sets `A1`, and
    # every later row in the batch then drew ROTATED -- measured directly
    # (scratchpad/drawleak_probe.py: `A1R5`, then a plain `R5` reads 4, then the
    # same `R5` behind an `A0S4` reads 15). **Every DRAW row now opens with `A0S4` (and
    # `C15` unless it is testing the colour)**, which is why the two rows below
    # can exist at all -- and why `drawkw`/`drawkw_b` were only ever right because
    # nothing before them had set an angle.
    ("drawkw_j", 'draw"xa$;"',
     'SCREEN2:A$="R5":PSET(10,10),15:DRAW"A0S4C15XA$;":A=POINT(14,10):SCREEN0:PRINT"[3f";A;"]"',
     "stored",
     "NOECHO:[3f FORM:substring-exec 15: the commands came from a STRING VARIABLE, "
     "which needs a variable lookup from inside the command walk"),
    ("drawkw_k", 'draw"r=a;"',
     'SCREEN2:A=5:PSET(10,10),15:DRAW"A0S4C15R=A;":B=POINT(14,10):SCREEN0:PRINT"[3g";B;"]"',
     "stored",
     "NOECHO:[3g FORM:variable-substitution 15: the OPERAND came from a variable, "
     "the same lookup the `X` form needs and a different call site"),
    # 🔴 THE CRUNCH IS `sprite on`, NOT `sprite$(0)=...`, AND THE FIRST CUT TAUGHT
    # ME WHY. tier_table's WORD regex keeps a trailing `$` (so STR$ and MID$ match),
    # which makes `sprite$(0)="x"` tokenise to SPRITE$ -- and the kwtable keyword is
    # SPRITE. The row reported SUPPORTED and credited NOTHING: four rows went in and
    # the evidence count rose by three. `sprite on` names SPRITE first and is real
    # BASIC besides.
    ("spritekw",  'sprite on',
     'SCREEN2:SPRITE$(0)=STRING$(8,255):A=ASC(SPRITE$(0)):SCREEN0:PRINT"[Z";A;"]"',
     "stored",
     "NOECHO:[Z SUBJECT:SPRITE FORM:pattern-write writes the pattern to VRAM and "
     "reads it back: 255 round-trips, a stub reads 0 and SCREEN 0 raises Illegal "
     "function call"),
    # 🌾 D-KWOSK: `SPRITE`'s OTHER half -- the trap STATE. The rows above write a
    # PATTERN; these three decide whether a collision is DELIVERED, and the only
    # way to see that is the collision trap itself (the machinery D-KWHOLD built
    # for `ON SPRITE GOSUB`). Same measured HIT as those rows: one solid 8x8
    # pattern at (100,100) and (104,100).
    # 🔴 `SPRITE STOP` IS NOT A THIRD BEHAVIOUR -- docs/spec-traps-t4-sprite.md
    # \u00a71.3 `G_stop_latch` measured `SPRITE STOP` \u2261 `SPRITE OFF` with NO LATCH, so
    # the third row is the DISABLE form sampled twice. It is here anyway: a tree
    # that treated STOP as a no-op would leave the trap enabled, and no OFF row
    # could see that.
    ("sprite_on", 'sprite on',
     'SCREEN2:SPRITE$(0)=STRING$(8,255):C=0:ON SPRITE GOSUB 80:SPRITE ON:PUTSPRITE0,(100,100),15,0:PUTSPRITE1,(104,100),15,0:T=TIME:V$="VVVVVVVVVVVVVVVVVVVVVVVV":IF C=0 AND TIME-T<120 THEN 60:SCREEN0:PRINT"[2j";C>0;"]":END:W1=55:C=C+1:RETURN',
     "stored",
     "NOECHO:[2j SUBJECT:SPRITE FORM:enable -1: ARMING IS NOT ENABLING, and this is "
     "the half that enables -- the handler runs only because `SPRITE ON` did"),
    ("sprite_off", 'sprite off',
     'SCREEN2:SPRITE$(0)=STRING$(8,255):C=0:ON SPRITE GOSUB 80:SPRITE OFF:PUTSPRITE0,(100,100),15,0:PUTSPRITE1,(104,100),15,0:T=TIME:V$="VVVVVVVVVVVVVVVVVVVVVV":IF C=0 AND TIME-T<30 THEN 60:SCREEN0:PRINT"[2k";C;"]":END:W1=55:C=C+1:RETURN',
     "stored",
     "NOECHO:[2k SUBJECT:SPRITE FORM:disable 0 fires in 30 frames with the handler "
     "ARMED and the sprites COLLIDING -- the state byte is what stops it. "
     "\U0001f534 30 FRAMES AND NOT 120: the first cut waited 2.4 s and came back "
     "`?nomarker` ON BOTH MACHINES -- the program was STILL WAITING when the "
     "capture was taken. A trap that fires once per COLLIDING FRAME needs no long "
     "window; the ENABLE row exits early and so never showed it."),
    ("sprite_stop", 'sprite stop',
     'SCREEN2:SPRITE$(0)=STRING$(8,255):C=0:ON SPRITE GOSUB 80:SPRITE STOP:PUTSPRITE0,(100,100),15,0:PUTSPRITE1,(104,100),15,0:T=TIME:V$="VVVVVVVVVVVVVVVV":IF C=0 AND TIME-T<30 THEN 60:SCREEN0:PRINT"[2l";C;"]":END:W1=55:C=C+1:RETURN',
     "stored",
     "NOECHO:[2l SUBJECT:SPRITE FORM:disable the DISABLE form sampled a second way: "
     "`SPRITE STOP` reads 0 too, because it is `SPRITE OFF` and does not latch "
     "(docs/spec-traps-t4-sprite.md \u00a71.3 `G_stop_latch`). Same 30-frame window as "
     "the row above, for the same reason."),
    # 🌾 D-KWBREADTH batch 19 — AXIS (g): measured across the file, EVERY `SPRITE$`
    # and `PUT SPRITE` uses SPRITE 0, so the pattern-table INDEX is a constant in
    # all of them and an implementation that ignored it entirely would pass.
    # 🎯 THE WRITE ORDER IS THE DISCRIMINATOR: sprite 3 is written FIRST and sprite
    # 0 SECOND, then 3 is read back. Indexed correctly that returns 3's own byte;
    # if the index is discarded both writes land in the same place and the read
    # returns 0's. Writing 0 first would have made both answers identical.
    ("spritekw_b", 'sprite$(3)=string$(8,222)',
     'SCREEN2:SPRITE$(3)=STRING$(8,222):SPRITE$(0)=STRING$(8,111):A=ASC(SPRITE$(3)):SCREEN0:PRINT"[Y";A;"]"',
     "stored",
     "NOECHO:[Y the pattern-table INDEX, where every other sprite row uses 0: 222, "
     "sprite 3's OWN byte, MEASURED on both machines before this sentence was "
     "written. An index that were discarded would read 111, the byte sprite 0 was "
     "given afterwards."),
    ("basekw",    'a=base(2)',         'PRINT"[";BASE(2);"]"',               "direct", "FORM:read D-KWDRAIN"),
    # D-KWBATCH7: `BASE(n)` is an assignment TARGET too -- `ex_base_assign`
    # (basic/interp.asm:749) is a separate handler from the read selector, exactly
    # like VDP(n). Every existing row reads.
    # WARNING: index 5, not 2. BASE(2) is the SCREEN 0 name table and writing it
    # MOVES THE TEXT PLANE the capture scrapes. BASE(5) belongs to SCREEN 1, which
    # is not on screen here, so the write is observable and harmless. The original
    # value is put back either way.
    ("basekw_b", 'base(5)=6144',
     'V=BASE(5):BASE(5)=&H1800:A=BASE(5):BASE(5)=V:PRINT"[0r";A;"]"',  "stored",
     "NOECHO:[0r FORM:write the ASSIGNMENT form, which has its own handler. "
     "`[0r 6144 ]` -- the value written, read back. An assignment that parsed and "
     "dropped the value leaves the boot default here instead."),

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
    # 🌾 D-KWPLUG: the rows with TEETH. `pdlkw` and `padkw` above read the IDLE
    # line of an EMPTY port, and 255 is as much a constant as 0 -- a PDL that
    # answered 255 to everything passes `pdlkw`. With a PADDLE plugged the value is
    # 128, and with an ARKANOIDPAD the touch sense is -1 and the X coordinate 255,
    # all three from `basic_probe_input_devices.py`'s own measured table (PHASE D
    # and PHASE E). openMSX offers no host paddle to TURN, so the plugged value is
    # the most a differential can reach here, and it is enough: it separates a real
    # read from every constant the idle rows admit.
    ("pdl_plug",  'a=pdl(1)',    'PRINT"[";PDL(1);"]"',      "direct",
     "NEEDS-PLUG:a,paddle SUBJECT:PDL FORM:read 128 with a paddle in port A, where "
     "the same expression reads 255 with the port EMPTY"),
    ("pad_plug",  'a=pad(0)',    'PRINT"[";PAD(0);"]"',      "direct",
     "NEEDS-PLUG:a,arkanoidpad SUBJECT:PAD FORM:touch-status -1: the pad is being "
     "touched. An empty port reads 0, and so does a stub"),
    ("pad_plug_b",'a=pad(1)',    'PRINT"[";PAD(1);"]"',      "direct",
     "NEEDS-PLUG:a,arkanoidpad SUBJECT:PAD FORM:coordinate 255: index 1 is the X "
     "COORDINATE, a different quantity from index 0's sense bit"),
    # 🔬 D-KWHOLD: THE CONTROL FOR THE KEY-MATRIX RIG, AND IT COMES FIRST. Every
    # STICK/STRIG/PDL row in this file reads the IDLE value, which is 0 -- exactly
    # what a stub returns -- so none of them can separate. This row holds the SPACE
    # BAR (matrix row 8, bit 0) down for the whole of its RUN and waits up to 120
    # FRAMES for `STRIG(0)` to answer -1.
    # 🔴 IT IS THE CONTROL, NOT A KEYWORD ROW: it carries no `FORM:` tag and awards
    # nothing. If this ever reads `[1w 0 ]` the rig is not reaching the matrix and
    # NOTHING THAT DEPENDS ON IT MAY BE BELIEVED -- which is the whole reason it
    # was written and run before a single dependent row existed.
    # ⚠️ The wait counts FRAMES (`TIME`), never iterations, and the `IF` that reads
    # STRIG sits on its own line: a FALSE condition skips the REST OF THE LINE.
    ("strig_hold", 'a=strig(0)',
     'S=0:T=TIME:W$="WWWWWWWWWWWWWWWWWW":IF STRIG(0)THEN S=-1:V$="VVVVVVV":IF S=0 AND TIME-T<120 THEN 20:PRINT"[1w";S;"]"',
     "stored",
     "NEEDS-HOLD:8,0x01 SUBJECT:STRIG FORM:space-bar the SPACE BAR HELD DOWN: -1, "
     "where every other input-device row in this file reads the idle 0 a stub also "
     "returns. \U0001f534 IT IS ALSO THE RIG'S CONTROL, AND THAT IS NOT A CONFLICT: if it "
     "ever reads `[1w 0 ]` the matrix is not being reached and STRIG loses the form "
     "in the same breath -- one row, both jobs, and the failure is loud either way."),
    # 🕹️ D-RIGFW: THE JOYSTICK-PORT FORMS, WITH A REAL STICK. The RP2040-Zero is
    # held in the named state for the whole case (NEEDS-RIG:, see _RIG_TAG), and
    # each row polls for up to 120 FRAMES like the hold rows above. Every row
    # prints a SECOND reading that must stay idle -- STICK(0) with no key held, or
    # the OTHER trigger -- so a routine that ignored `n` and read one source for
    # all of them cannot pass.
    ("stick_rig", 'a=stick(1)',
     'S=0:T=TIME:W$="WWWWWWWWWWWWWWWWWW":IF STICK(1)THEN S=STICK(1):V$="VVVVVVV":IF S=0 AND TIME-T<120 THEN 20:PRINT"[3s";S;STICK(0);"]"',
     "stored",
     "NEEDS-RIG:upright SUBJECT:STICK FORM:joystick-port 2 = UP-RIGHT, off port A's "
     "direction LINES (the PSG), with STICK(0) -- the cursor keys, nothing held -- "
     "still 0 beside it. A direction CODE, not a flag: a stub or a keyboard read "
     "cannot produce `2 0`"),
    ("stick_rig_b", 'a=stick(1)',
     'S=0:T=TIME:W$="WWWWWWWWWWWWWWWWWW":IF STICK(1)THEN S=STICK(1):V$="VVVVVVV":IF S=0 AND TIME-T<120 THEN 20:PRINT"[3w";S;"]"',
     "stored",
     "NEEDS-RIG:downleft SUBJECT:STICK 6 = DOWN-LEFT: the other diagonal, two "
     "different lines, so `stick_rig`'s 2 is a decode and not a constant"),
    ("strig_rig", 'a=strig(1)',
     'S=0:T=TIME:W$="WWWWWWWWWWWWWWWWWW":IF STRIG(1)THEN S=-1:V$="VVVVVVV":IF S=0 AND TIME-T<120 THEN 20:PRINT"[3t";S;STRIG(3);STRIG(0);"]"',
     "stored",
     "NEEDS-RIG:trig1 SUBJECT:STRIG FORM:joystick-trigger -1: port A's trigger A "
     "is down, and beside it STRIG(3) (port A's trigger B) and STRIG(0) (the space "
     "bar) stay 0"),
    ("strig_rig_b", 'a=strig(3)',
     'S=0:T=TIME:W$="WWWWWWWWWWWWWWWWWW":IF STRIG(3)THEN S=-1:V$="VVVVVVV":IF S=0 AND TIME-T<120 THEN 20:PRINT"[3u";S;STRIG(1);"]"',
     "stored",
     "NEEDS-RIG:trig2 SUBJECT:STRIG -1 0: trigger B alone reads through n=3, and "
     "n=1 stays 0 -- the index picks the BUTTON, not just the port"),
    ("attrkw",    'a$=attr$',    'PRINT"[";ATTR$;"]"',      "direct",
     "FORM:refuse D-KWDRAIN: bare ATTR$ raises Illegal function call -- so the word IS a token here; an undefined string variable prints empty instead"),
    ("stopkw",    'stop',        'PRINT"[T1]":STOP',        "stored",
     "FORM:break D-KWDRAIN: prints then Break in 10 on both machines; without STOP there is no Break"),
    # 🌾 D-CONTROW (2026-09-24): `CONT` HAD NO ROW AT ALL -- the only level-0
    # keyword that was neither a particle, composite-only, the parked rig nor
    # waiting on Joost. It is a PROMPT verb, so the row is a RESPOND: row: the
    # program STOPs after [C1], and `CONT` typed at the prompt must resume at the
    # statement after the STOP. The reading is `[C2]` appearing at all: without a
    # working CONT the run ends at `Break in 10` (or `Can't CONTINUE`), and a
    # CONT that restarted the LINE would print [C1] and Break again.
    # 🔴 NOECHO, AND THE FIRST CUT SHOWED WHY: anchored on the `RUN` echo the
    # window ENDS at the prompt the STOP returns to, so both sides read
    # `[C1]|Break in 10` -- SUPPORTED, and blind to CONT entirely (a row that
    # agrees for the wrong reason). The marker is the LAST row carrying `[C2]`,
    # which only the resumed run prints; it is spelled `"[C"+"2]"` so the typed
    # SOURCE never contains it, and a missing [C2] reads ?nomarker -- a refusal.
    ("contkw",    'cont',        'PRINT"[C"+"1]":STOP:PRINT"[C"+"2]"', "stored",
     "NOECHO:[C2] RESPOND:CONT FORM:resume D-CONTROW: STOP breaks after [C1]; CONT typed at the prompt resumes at the next statement and prints [C2] once"),
    # 🔴 D-AKCM (2026-09-17): THIS ROW AGREES ON AN ERROR. `PRINT"[";MAX;"]"` is
    # ERR 2 on BOTH references and here -- the `[` prints, then the bare `MAX`
    # raises -- so its SUPPORTED verdict is two machines failing identically. It
    # is kept because the AGREEMENT is still worth pinning (the word tokenises
    # the same way on both), but `MAX` is NO_BARE_FORM and `tier_table` no longer
    # reads this as happy-path evidence.
    ("maxkw",     'max',               'PRINT"[";MAX;"]"',                     "direct",
     "D-KWDRAIN: bare MAX is a Syntax error on a real machine; a stub prints 0"),
    ("strigkw",   'a=strig(0)',        'PRINT"[";STRIG(5);"]"',                "direct",
     "D-KWDRAIN: 5 is out of STRIG's 0..4 range -> Illegal function call; an "
     "undefined array auto-dims and answers 0"),
    ("onkw",      'on error goto 20', 
     'ON ERROR GOTO 20:ERROR 7:END:PRINT"[R";ERR;ERL;"]":END',  "stored", "D-KWDRAIN: FORM:on-error ON in its ON ERROR form"),
    # D-KWPARTIAL: `ON ERROR GOTO 0` DISABLES trapping -- the form a program uses to
    # hand an error back to BASIC -- and only the INSTALL had a row.
    # WARNING: NO `NOECHO:` MARKER HERE, DELIBERATELY. When the disable WORKS the
    # error is untrapped and the program stops, so the marker never prints and a
    # marker-anchored capture would read ?nomarker -- a refusal, not a reading.
    # Echo-anchored, the capture holds the ERROR MESSAGE, and the failing case
    # holds `[0w1]` instead.
    # 🔴 AND THE PADDING IS `A=n`, NOT `REM`, BECAUSE **REM SWALLOWS THE REST OF
    # THE LINE**. The first cut padded with `REM ZZZ...:ERROR 7`, which commented
    # the ERROR out: no error was ever raised, execution fell through to the
    # handler line, and the row read `[0w1]` on BOTH machines -- SUPPORTED, and
    # proving nothing whatever. `troff_b` gets away with REM padding only because
    # its REMs are the LAST statement on their lines.
    ("onkw_b",   'on error goto 0',
     'ON ERROR GOTO 40:ON ERROR GOTO 0:ERROR 7:A=1:A=2:A=3:A=4:A=5:A=6:A=7:A=8:A=9:B=1:B=2:B=3:B=4:B=5:PRINT"[0w1]":END',
     "stored",
     "SUBJECT:ON_ERROR_GOTO FORM:disable the DISABLE. With it working `ERROR 7` is "
     "untrapped and the program stops with the message; with it ignored the "
     "handler on line 40 runs and prints `[0w1]`."),
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
     "NOECHO:[J FORM:index-goto the INDEX-SELECTED jump. `ON 2` must reach the SECOND target: "
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
     "NOECHO:[K FORM:index-gosub the INDEX-SELECTED subroutine call. `ON 2` must reach the SECOND "
     "target and RETURN: 99. An ON that ignores the index gives 77, one that never "
     "calls leaves A at 0."),
    # 🔴 `SUBJECT:ON_INTERVAL_GOSUB` IS MANDATORY AND `ON SPRITE GOSUB`'s IS NOT:
    # `INTERVAL` IS NOT A KEYWORD TABLE ENTRY. It is a compound reserved word
    # (`iv_seq` = INT + "ER" + VAL, basic/program.asm), so `stmt_subject` cannot
    # see it in the crunch body and derived `ON GOSUB` -- crediting the INTERVAL
    # trap's readings to a statement that already had its own row. Measured, not
    # feared: the first knife run recorded them under `ON GOSUB`.
    # 🌾 D-KWONTRAP: two of `ON`'s SIX trap composites get their first rows. Both
    # are reachable from BASIC alone -- an INTERVAL fires on a timer and a SPRITE
    # collision is caused by putting two sprites on top of each other -- where
    # `ON KEY`, `ON STOP` and `ON STRIG` all need a KEY OR A TRIGGER PRESSED and
    # wait on the injection rig.
    # 🔴 THE WAIT LOOPS ARE `IF C=0 THEN <own line>` AND `IF TIME-T<30`, NEVER A
    # `FOR`: the two machines differ in interpreter speed by 2.5-3.8x, so a
    # counted loop measures the INTERPRETER and a frame count measures the FRAME.
    # And nothing may follow the `IF` on its line -- a FALSE condition skips the
    # REST OF THE LINE, not just the THEN -- so each is padded out to its own.
    # ⚠️ `C>0` and not `C`, because the number of fires before the loop exits IS
    # speed-dependent; whether any fire happened is not.
    ("oninterval", 'on interval=10 gosub 40',
     'C=0:ON INTERVAL=10 GOSUB 40:INTERVAL ON:IF C=0 THEN 20:PRINT"[1q";C>0;"]":END:W$="WWWWWW":C=C+1:RETURN',
     "stored",
     "SUBJECT:ON_INTERVAL_GOSUB FORM:arm the trap FIRED: -1. Arming is not "
     "enabling, so `INTERVAL ON` is "
     "there too; the loop exits only when the handler has run"),
    # The bare form CLEARS THE HANDLER SLOT (docs/spec-traps-t5-interval.md §1.6,
    # `R_bare_disarms`: 6 fires before, 0 after) -- and it is not the same thing as
    # `INTERVAL OFF`, which is still ON here. 30 frames is THREE periods, so a
    # `ON INTERVAL=n GOSUB` that parsed and kept the handler reads 3, not 0.
    ("oninterval_b", 'on interval=10 gosub',
     'C=0:ON INTERVAL=10 GOSUB 60:INTERVAL ON:IF C=0 THEN 20:ON INTERVAL=10 GOSUB:C=0:T=TIME:IF TIME-T<30 THEN 40:PRINT"[1r";C;"]":END:W$="WWWWWWWW":C=C+1:RETURN',
     "stored",
     "SUBJECT:ON_INTERVAL_GOSUB FORM:disarm 0 fires in THREE periods after the "
     "bare form cleared the slot"),
    # The sprite pair is the sprite-trap probe's own measured collision: ONE solid
    # 8x8 pattern, two sprites four pixels apart at (100,100) and (104,100)
    # (probes/basic/basic_probe_sprite_trap.py HIT). SCREEN 2 has no 40-column
    # text to scrape, so both rows come back to SCREEN 0 before the PRINT and
    # carry NOECHO.
    ("onsprite", 'on sprite gosub 70',
     'SCREEN2:SPRITE$(0)=STRING$(8,255):C=0:ON SPRITE GOSUB 70:SPRITE ON:PUTSPRITE0,(100,100),15,0:PUTSPRITE1,(104,100),15,0:IF C=0 THEN 50:W$="WWWWWWWWWWWWWW":SCREEN0:PRINT"[1s";C>0;"]":END:C=C+1:RETURN',
     "stored",
     "NOECHO:[1s FORM:arm two overlapping sprites collide and the handler runs: -1"),
    ("onsprite_b", 'on sprite gosub',
     'SCREEN2:SPRITE$(0)=STRING$(8,255):C=0:ON SPRITE GOSUB 90:SPRITE ON:PUTSPRITE0,(100,100),15,0:PUTSPRITE1,(104,100),15,0:IF C=0 THEN 50:W$="WWWWWWWWWWWWWW":ON SPRITE GOSUB:C=0:T=TIME:IF TIME-T<30 THEN 70:V$="VVVVVVVV":SCREEN0:PRINT"[1t";C;"]":END:W1=55:C=C+1:RETURN',
     "stored",
     "NOECHO:[1t FORM:disarm the sprites are STILL COLLIDING and SPRITE is still "
     "ON -- 0 fires in 30 frames is the HANDLER SLOT being cleared "
     "(docs/spec-traps-t4-sprite.md §1.4 `R_bare_disarms`), which a trap that "
     "fires once per colliding frame makes unmissable: it would read ~30"),
    # 🌾 D-KWHOLD: the two trap composites that need a KEY HELD DOWN, now that the
    # matrix rig has a control that says it reaches GTTRIG (`strig_hold`). Trigger
    # 0 IS THE SPACE BAR, so every STRIG row here holds matrix row 8 bit 0; the KEY
    # rows hold F1 (row 6, $20) and F2 (row 6, $40).
    # 🎯 THE LIST ROWS ARE WHY ONE PRESS IS ENOUGH FOR THE POSITIONAL FORM: the
    # reference fires SLOT n for TRIGGER n / KEY n (spec-traps-t2-strig.md R5,
    # spec-traps-t3-key.md K8), so an implementation that armed the LAST entry, or
    # armed them all, reads the OTHER handler's value from the same single press.
    ("onstrig", 'on strig gosub 60',
     'C=0:ON STRIG GOSUB 60:STRIG(0) ON:T=TIME:V$="VVVVVVVVVVVVVVVVVVVVVVVV":IF C=0 AND TIME-T<120 THEN 40:PRINT"[1x";C>0;"]":END:W$="WWWWWWWWW":C=C+1:RETURN',
     "stored",
     "NEEDS-HOLD:8,0x01 FORM:arm the SPACE BAR held: the trap fires and the handler "
     "runs. Arming is not enabling, so `STRIG(0) ON` is there too"),
    ("onstrig_b", 'on strig gosub 60,80',
     'C=0:ON STRIG GOSUB 60,80:STRIG(0) ON:T=TIME:V$="VVVVVVVVVVVVVVVVVVVVVV":IF C=0 AND TIME-T<120 THEN 40:PRINT"[1y";C;"]":END:W$="WWWWWWWWWWW":C=1:RETURN:U$="UUUUUUUUUUUUUUUUUUUUUUUUUUU":C=2:RETURN',
     "stored",
     "NEEDS-HOLD:8,0x01 FORM:list-positional 1, not 2: TRIGGER 0 takes SLOT 0. A "
     "list that armed its last entry would read 2 from the same press"),
    ("onstrig_c", 'on strig gosub ,60',
     'C=0:ON STRIG GOSUB 60:ON STRIG GOSUB ,60:STRIG(0) ON:T=TIME:IF C=0 AND TIME-T<120 THEN 40:PRINT"[1z";C;"]":END:W$="WWWWWWWWW":C=C+1:RETURN',
     "stored",
     "NEEDS-HOLD:8,0x01 FORM:empty-slot-clears an EMPTY slot 0 clears the handler "
     "armed one statement earlier (spec-traps-t2-strig.md S3), so 0 fires in 120 "
     "frames with the space bar held down the whole time"),
    # 🕹️ D-RIGFW: THE TRAP FROM A REAL JOYSTICK TRIGGER. `onstrig_b`'s program with
    # `STRIG(1) ON` for `STRIG(0) ON` (same length, so lines 60 and 80 stay put):
    # trigger 1 is list SLOT 1, so the SECOND handler fires. The trigger is PULSED
    # (rigfw.Pulser): a trap needs a press inside its wait. Until the rig, triggers
    # 1..4 were reachable only by faking the PSG latch (spec-traps-t2-strig.md §7.3).
    ("onstrig_rig", 'on strig gosub 60,80',
     'C=0:ON STRIG GOSUB 60,80:STRIG(1) ON:T=TIME:V$="VVVVVVVVVVVVVVVVVVVVVV":IF C=0 AND TIME-T<120 THEN 40:PRINT"[3v";C;"]":END:W$="WWWWWWWWWWW":C=1:RETURN:U$="UUUUUUUUUUUUUUUUUUUUUUUUUUU":C=2:RETURN',
     "stored",
     "NEEDS-RIG:pulse+trig1 2: joystick trigger 1 takes list SLOT 1, the SECOND "
     "handler. A trap wired to the space bar only reads 0; one that took slot 0 "
     "reads 1. \U0001f534 PULSED, NOT HELD: the trap fires on a PRESS, and a trigger "
     "held since before boot read 0 on BOTH machines -- an agreeing stub value"),
    # 🔴 EVERY ON KEY ROW OPENS WITH `KEY n,""`, AND THE FIRST CUT WITHOUT IT WAS
    # `?noecho` ON THE REFERENCE AND A CLEAN READING ON ZEROBAS -- an apparatus
    # failure that reads exactly like a divergence. The hold lasts ~12 emulated
    # seconds and the program finishes in ~2.4, so the key AUTO-REPEATS at ~17 Hz
    # into the BASIC prompt for the rest of it; each repeat types the function
    # key's EXPANSION, and the reference is 2.5-3.8x faster so it gets far more of
    # them. `color ` x ~160 scrolled the marker off the screen on the reference
    # alone. An EMPTY expansion still fires the trap (spec-traps-t3-key.md \u00a71.1 R8/R9
    # -- the event is upstream of string expansion) and types nothing.
    # 🌾 D-KWSTOP: the SIXTH and last of `ON`'s trap composites, and the one that
    # needed the rig to learn a COMBO: Ctrl-STOP is CTRL row 6 bit $02 plus STOP
    # row 7 bit $10, two keys on DIFFERENT MATRIX ROWS. `@0.5/2.0` is a 2-SECOND
    # press starting after the program is already looping; the defaults blank the
    # reference's screen outright (see `_holdtime_of`, measured one variable at a
    # time in scratchpad/ctrlstop_probe.py).
    # 🔴 THE ARM ROW DOES NOT `STOP OFF` BEFORE IT PRINTS, AND THAT IS NOT TIDINESS
    # -- it is the one shape that DIVERGES. With `STOP OFF` executed while the key
    # is STILL DOWN the reference finishes normally and zerobas answers
    # `Break in 50`: the reference's break is EDGE-triggered and consumed by the
    # trap, zerobas re-breaks on the LEVEL. Filed rather than papered over, and it
    # is a TIER 3 item, not a TIER 1 one -- the happy path below is clean on both.
    ("onstop", 'on stop gosub 60',
     'C=0:ON STOP GOSUB 60:STOP ON:T=TIME:V$="VVVVVVVVVVVVVVVVVVVVVV":IF C=0 AND TIME-T<200 THEN 30:PRINT"[2q";C>0;"]":END:W$="WWWWWW":Y$="YYYYYYYYYYYYYYYYYYYYYYYY":C=C+1:RETURN',
     "stored",
     "NEEDS-HOLD:6,0x02+7,0x10@0.5/2.0 FORM:arm -1: Ctrl-STOP reached the HANDLER "
     "instead of breaking the program, which is what the statement is FOR. Without "
     "`STOP ON` the same program answers `Break in 30` -- arm is not enable"),
    # The bare form CLEARS the handler slot (docs/spec-traps-t4-sprite.md §1.5 says
    # T1 shipped ERR 2 here where the reference accepts it; this row is the
    # re-verification, and both machines accept it today). 🔴 AND UNLIKE SPRITE AND
    # KEY, A CLEARED SLOT WITH THE ENTRY STILL ON DOES **NOT** SWALLOW THE EVENT --
    # both machines BREAK. That is the reading: `Break in 30` where the armed row
    # reads `[2q-1 ]`, and a bare form REFUSED with ERR 2 would read
    # `Syntax error in 10` instead.
    ("onstop_b", 'on stop gosub',
     'C=0:ON STOP GOSUB 60:ON STOP GOSUB:STOP ON:T=TIME:IF C=0 AND TIME-T<200 THEN 30:PRINT"[2r";C;"]":END:W$="WWWWWWWW":Y$="YYYYYYYYYYYYYYYYYYYYYYYY":C=C+1:RETURN',
     "stored",
     "NEEDS-HOLD:6,0x02+7,0x10@0.5/2.0 FORM:disarm the handler slot is CLEARED, so "
     "the program breaks where the armed row services"),
    ("onkey", 'on key gosub 60',
     'KEY 1,"":C=0:ON KEY GOSUB 60:KEY(1) ON:T=TIME:V$="VVVVVVVVVVVVVVVVVVVVVVVV":IF C=0 AND TIME-T<120 THEN 40:PRINT"[2a";C>0;"]":END:W$="WWWWWWWWW":C=C+1:RETURN',
     "stored",
     "NEEDS-HOLD:6,0x20 FORM:arm F1 held: the trap fires. A trapped key is DIVERTED "
     "(spec-traps-t3-key.md \u00a71.2), so its expansion never reaches the screen"),
    ("onkey_b", 'on key gosub 60,80',
     'KEY 2,"":C=0:ON KEY GOSUB 60,80:KEY(2) ON:T=TIME:V$="VVVVVVVVVVVVVVVVVVVVVV":IF C=0 AND TIME-T<120 THEN 40:PRINT"[2b";C;"]":END:W$="WWWWWWWWWWW":C=1:RETURN:U$="UUUUUUUUUUUUUUUUUUUUUUUUUUU":C=2:RETURN',
     "stored",
     "NEEDS-HOLD:6,0x40 FORM:list-positional 2, not 1: F2 takes the SECOND slot "
     "(spec-traps-t3-key.md K8). Only `KEY(2)` is enabled, so the first slot cannot "
     "fire even if it were armed"),
    ("onkey_c", 'on key gosub ,60',
     'KEY 1,"":C=0:ON KEY GOSUB 60:ON KEY GOSUB ,60:KEY(1) ON:T=TIME:V$="VVVVVVVVVVVVVVVVVVVVVVVV":IF C=0 AND TIME-T<120 THEN 40:PRINT"[2c";C;"]":END:W$="WWWWWWWW":C=C+1:RETURN',
     "stored",
     "NEEDS-HOLD:6,0x20 FORM:empty-slot-clears 0 fires with F1 held: the empty slot "
     "cleared the handler. \u26a0\ufe0f the key is STILL SWALLOWED -- diversion follows "
     "the entry STATE, not the handler (spec-traps-t3-key.md T5) -- which is why "
     "no F1 expansion appears on the screen this row scrapes"),
    ("errorkw",   'error 7',          
     'ON ERROR GOTO 20:ERROR 7:END:PRINT"[R";ERR;ERL;"]":END',  "stored", "FORM:raise D-KWDRAIN: ERROR 7 is what raises it"),
    # 🌾 D-KWBREADTH batch 20 — AXIS (g): counted across the file, EVERY `ERROR`
    # raised is code 7, six times over, so every other code's own path is
    # unexercised and an implementation that ignored the operand and always raised
    # 7 would pass all six. 53 is `File not found`, unmistakably not 7.
    # The packing is the same shape as the row above (line 10 raises, line 20
    # handles) and was PRINTED before this row was written.
    # 🎯 BOTH `ERR` AND `ERL` ARE READ, so the row separates "the right error" from
    # "an error at the right line" -- either alone would agree for the wrong reason.
    ("errorkw_b", 'error 53',
     'ON ERROR GOTO 20:ERROR 53:END:PRINT"[I";ERR;ERL;"]":END',  "stored",
     "D-KWDRAIN: a DIFFERENT error code, where all six existing rows raise 7 -- "
     "`[I 53  10 ]`, MEASURED on both machines before this sentence was written. "
     "ERR returns 53 and not 7, so the OPERAND is honoured rather than a fixed "
     "FORM:raise code being raised; ERL pins it to line 10, the line that raised it."),
    ("errkw",     'a=err',            
     'ON ERROR GOTO 20:ERROR 7:END:PRINT"[R";ERR;ERL;"]":END',  "stored", "FORM:error-code D-KWDRAIN: ERR reads 7, the code raised"),
    ("erlkw",     'a=erl',            
     'ON ERROR GOTO 20:ERROR 7:END:PRINT"[R";ERR;ERL;"]":END',  "stored", "FORM:error-line D-KWDRAIN: ERL reads 10, the line that raised"),
    ("resumekw",  'resume next',      
     'ON ERROR GOTO 30:ERROR 7:PRINT"[U";A;"]":END:A=5:RESUME NEXT', "stored", "FORM:next D-KWDRAIN: the handler RESUMEs NEXT and control reaches the PRINT; without it nothing prints"),
    # 🌾 D-KWRETRES: RESUME's other two destinations. All three forms continue in a
    # DIFFERENT place, so each needs a reading no other form can produce, and both
    # rows below need EXACT NUMBERED LINES -- verified with `omsx_repl.as_stored`
    # first, padded with long assignments because `REM` swallows the rest of its line.
    #   bare: the handler REPAIRS the cause (B=9) and RESUME re-runs the statement
    #   that failed, so `SQR(B)` succeeds the second time and A is 3. RESUME NEXT
    #   would skip it and print 0 -- the value an unassigned A already has, which is
    #   exactly why the repaired value has to be a NON-ZERO one.
    ("resumekw_b", 'resume',
     'ON ERROR GOTO 40:B=-1:W$="WWWWWWW":A=SQR(B):Y$="YYYYYYYYYYYYYYYYYYYY":PRINT"[1n";A;"]":END:V$="VVVVVVVV":B=9:RESUME',
     "stored",
     "SUBJECT:RESUME FORM:bare 3 means SQR(9) RAN: the failing statement was re-entered, not skipped"),
    #   line: the handler names line 40, which is the PRINT. Line 30's `A=8` sits
    #   between the failure and that PRINT, so RESUME NEXT reads 8 and only an
    #   honoured LINE NUMBER reads the 7 assigned before the error.
    ("resumekw_c", 'resume 40',
     'ON ERROR GOTO 50:A=7:W$="WWWWWWWW":ERROR 7:Y$="YYYYYYYYYYYYYYYYYYYYY":A=8:U$="UUUUUUUUUUUUUUUUUUUUUUUUU":PRINT"[1o";A;"]":END:V$="VVVVVVVV":RESUME 40',
     "stored",
     "SUBJECT:RESUME FORM:line 7 not 8 -- control resumed AT line 40 and skipped the line in between"),
    ("defintkw",  'defint a',         
     'DEFINT A:A=1.7:PRINT"[";A;"]"',                           "direct", "FORM:single-letter D-KWDRAIN: 1, not 1.7 -- a DEFINT that parses and does nothing still prints 1.7"),
    # 🌾 D-KWBATCH6: `ex_deftype` (basic/usr.asm:210) parses a comma-list of
    # `letter` OR `letter-letter` RANGE items and rejects a reversed range, so the
    # range is a second behaviour and not a second input. Each of the four rows
    # below proves the range reached a letter the single-letter form never names.
    ("defint_b", 'defint a-c',
     'DEFINT A-C:C=1.7:PRINT"[";C;"]"',               "direct",
     "FORM:letter-range the RANGE form -- `C` is covered only if `A-C` was expanded, "
     "so `[ 1 ]` where an unexpanded range leaves C single-precision and prints 1.7."),

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
     "FORM:bare-list D-KWDRAIN: the LISTING itself is the discriminator -- a LIST that did nothing would leave only [A] on the screen"),
    # 🌾 D-KWLISTSEL: LIST's two SELECTING forms. The bare row prints everything,
    # so it cannot see a LIST that ignored a line number and printed the lot.
    ("listkw_b", 'list 20',
     'PRINT"[A]":Z$="XXXXXXXXXXXXXXXXXXXXXXXX":Y$="YYYYYYYYYYYYYYYYYYYY":LIST 20',
     "stored",
     "FORM:single-line ONE line only. The row's own program has several, so a "
     "LIST that ignored the argument prints them all and the compared text "
     "differs."),
    ("listkw_c", 'list 20-30',
     'PRINT"[A]":Z$="XXXXXXXXXXXXXXXXXXXXXXXX":Y$="YYYYYYYYYYYYYYYYYYYY":LIST 20-30',
     "stored",
     "FORM:range a RANGE, which the single-line form cannot exercise: the "
     "endpoints have to be read as a pair."),
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
    # 🟢 D-KWEDIT (2026-09-16): `DELETE` AND `RENUM` WERE CLOSED AS UNRATEABLE AND
    # THE REASON WAS THE MODE, NOT THE VERB. Measured from INSIDE a running
    # program, `DELETE 20` stops the run -- so every range form has the same
    # observable, nothing -- and `RENUM 100` breaks the execution pointer, so its
    # only reading is `Undefined line 100 in 20`, a TIER 5 reading wearing a TIER
    # 1 label. Both are DIRECT-MODE EDITOR COMMANDS. At the prompt there is no run
    # to stop and no pointer to break, and the PROGRAM TEXT AFTERWARDS separates
    # every form exactly. The readout is the printer log, not the screen: a
    # listing is not bounded by 40 columns there.
    # ⚠️ The `deletekw` row above stays -- it is the ERROR class (a line that does
    # not exist), a different question from which lines a range selects.
    ("del_line",  "delete 20",
     "DELETE 20",                                            "direct",
     "NEEDS-LOG: PROGRAM:10_REM_Z1|20_REM_Z2|30_REM_Z3 RESPOND:LLIST "
     "FORM:delete-line one line goes, its neighbours stay -- the listing reads Z1 Z3"),
    ("del_range", "delete 20-30",
     "DELETE 20-30",                                         "direct",
     "NEEDS-LOG: PROGRAM:10_REM_Z1|20_REM_Z2|30_REM_Z3 RESPOND:LLIST "
     "FORM:delete-range an inclusive span goes -- Z1 alone is left, which is what "
     "separates this from the single-line form"),
    ("del_head",  "delete -20",
     "DELETE -20",                                           "direct",
     "NEEDS-LOG: PROGRAM:10_REM_Z1|20_REM_Z2|30_REM_Z3 RESPOND:LLIST "
     "FORM:delete-to-line the open-ended LEFT form, everything up to and including "
     "20 -- Z3 alone is left. Whether the reference ACCEPTS this spelling is what "
     "the row measures; a refusal here is a reading, not a failure"),
    ("del_tail",  "delete 20-",
     "DELETE 20-",                                           "direct",
     "NEEDS-LOG: PROGRAM:10_REM_Z1|20_REM_Z2|30_REM_Z3 RESPOND:LLIST "
     "🔴 MEASURED 2026-09-16 AND IT IS NOT A FORM: the open-ended RIGHT spelling is "
     "REFUSED -- `Illegal function call` on both machines, where `DELETE -20` is "
     "accepted. So MSX1 DELETE takes `<line>`, `<from>-<to>` and `-<to>` and NOT "
     "`<from>-`. The row stays because the asymmetry is worth holding pinned, and it "
     "carries NO `FORM:` tag on purpose: its reading is the same `Illegal function "
     "call` the `deletekw` row already gets for a line that does not exist, and a "
     "second row agreeing on the SAME ERROR would inflate the bar without testing "
     "anything new."),
    ("newkw",     'new',
     'PRINT"[A]":NEW',                                       "stored",
     "D-KWDRAIN: the D-NEWSTMT shape -- [A] then a clean stop; before the fix "
     "FORM:erase-program this row would have carried `Syntax error in 10` on the zb side"),
    ("gosubkw",   'gosub 20',     
     'A=0:GOSUB 20:PRINT"[G";A;"]":END:A=7:RETURN',         "stored", "FORM:call D-KWDRAIN: the subroutine sets A=7; no GOSUB, no output"),
    ("returnkw",  'return',       
     'A=0:GOSUB 20:PRINT"[H";A;"]":END:A=7:RETURN',         "stored", "FORM:bare D-KWDRAIN: A is 7 only because RETURN came back to the PRINT"),
    ("endkw",     'end',          
     'A=0:GOSUB 20:PRINT"[J";A;"]":END:A=7:RETURN',         "stored", "FORM:terminate D-KWDRAIN: END keeps the subroutine from being fallen into"),
    # 🌾 D-KWBARS: `DATA` had no row either -- `readkw`/`restorekw` USE it, and
    # their subject is the statement that consumes it. Four forms, and three of
    # them are about where an ITEM ENDS: a numeric constant, a QUOTED string (whose
    # `,` and `:` do NOT terminate it -- docs/spec-basic-datacolon.md found the
    # missing quote state twice), an UNQUOTED string (which keeps internal spaces
    # and is trimmed at the edges), and an EMPTY item, which reads as 0.
    ("datakw",   'data 42',
     'DATA 42:READ A:PRINT"[";A;"]"',                         "stored",
     "FORM:numeric a numeric constant read back as a number. "
     "\U0001f534 THE `DATA` COMES FIRST, AND THAT IS THE CONNECTEDNESS: with it after "
     "the `END` the statement is NEVER EXECUTED -- READ finds the text by SCANNING "
     "the program -- so cutting DATA's stmt_table entry moved nothing and the knife "
     "read BLIND. Here the DATA statement is stepped over on the way to the READ, "
     "so its handler is on the path [[a-shared-tail-is-not-a-decision]]."),
    ("datakw_b", 'data "x,y"',
     'DATA "X,Y":READ A$:PRINT"[";A$;"]"',                    "stored",
     "FORM:quoted-string `[X,Y]`: the COMMA inside the quotes did not end the item. "
     "A body scan with no quote state reads `X`, and the `:` AFTER the closing quote "
     "still ends the statement"),
    ("datakw_c", 'data a b',
     'DATA A B:READ A$:PRINT"[";LEN(A$);A$;"]"',              "stored",
     "FORM:unquoted-string LEN 3: an unquoted item keeps its INTERNAL space and is "
     "trimmed only at the edges -- a scan that split on whitespace reads LEN 1, and "
     "one that ran past the `:` read the whole rest of the line, TOKENS and all"),
    ("datakw_d", 'data 1,,3',
     'DATA 1,,3:READ A,B,C:PRINT"[";A;B;C;"]"',               "stored",
     "FORM:empty-item the middle item is EMPTY and reads 0, and the THIRD still "
     "reads 3 -- a scan that skipped the empty slot would read 3 into B"),
    ("readkw",    'read q',       
     'READ Q:RESTORE:READ R:PRINT"[E";Q+R;"]":END:DATA 3',  "stored", "FORM:read-data D-KWDRAIN: reads 3 from the DATA on the second line"),
    ("restorekw", 'restore',      
     'READ Q:RESTORE:READ R:PRINT"[F";Q+R;"]":END:DATA 3',  "stored", "FORM:bare D-KWDRAIN: 6 needs the pointer RESET: without RESTORE the second READ runs out of DATA"),
    # 🌾 D-KWRETRES: the LINE forms of RESTORE and RETURN, each the second of two
    # authored forms. Both need EXACT NUMBERED LINE TARGETS, and `as_stored` packs
    # `:`-joined statements greedily into <=34-char bodies -- so the padding here is
    # not decoration, it is what puts `DATA 11` on line 50 and the PRINT on line 40.
    # Verified with `omsx_repl.as_stored` BEFORE the rows were written (the first cut
    # of both LIST rows listed nothing because the line they named did not exist).
    # Padding is long ASSIGNMENTS, never `REM`, which swallows the rest of its line.
    #   restore: READ Q takes the first DATA (7, line 30); `RESTORE 50` then makes the
    #   second READ take line 50's 11. A BARE RESTORE would read 7 again and no
    #   RESTORE at all would read 9 -- so 11 is reachable only by honouring the LINE.
    ("restorekw_b", 'restore 50',
     'READ Q:RESTORE 50:READ R:PRINT"[1k";Q;R;"]":END:W$="WWWWWW":Y$="YYYYYYYYYYYYYYYYYYYYYY":DATA 7:V$="VVVVVVVVVVVVVVVVVVVVVV":DATA 9:DATA 11',
     "stored",
     "SUBJECT:RESTORE FORM:line the DATA pointer moves to line 50, not to the start (7) and not onwards (9)"),
    #   return: GOSUB 50 lands on `A=5:RETURN 40`, and line 40 is the PRINT. A bare
    #   RETURN would resume after the GOSUB -- line 20's padding, then line 30's
    #   `A=A+1` -- and print 6. 5 is reachable only by honouring the LINE.
    ("returnkw_b", 'return 40',
     'A=0:GOSUB 50:Z$="XXXXXXXXXXXXXXXXXXXXXXXX":A=A+1:Y$="YYYYYYYYYYYYYYYYYYYYYYY":PRINT"[1l";A;"]":END:W$="WWWWWWWW":A=5:RETURN 40',
     "stored",
     "SUBJECT:RETURN FORM:line RETURN 40 skips the increment on line 30 that a bare RETURN would run"),
    ("psetkw",   'pset(1,1)',      
     'SCREEN2:PSET(1,1),15:A=POINT(1,1):SCREEN0:PRINT"[S";A;"]"',   "stored",
     "NOECHO:[S FORM:colour-explicit PSET draws, POINT reads it back: 4 blank vs 15 drawn"),
    # 🌾 D-KWBREADTH batch 11: the row above uses colour 15, the default foreground,
    # so a PSET that IGNORED its colour argument and drew in the current foreground
    # passes it. 7 is neither the foreground nor the blank 4, so this reads the
    # COLOUR ARGUMENT rather than "something was drawn".
    ("psetkw_b", 'pset(2,2),7',
     'SCREEN2:PSET(2,2),7:A=POINT(2,2):SCREEN0:PRINT"[H";A;"]"',    "stored",
     "NOECHO:[H FORM:colour-explicit a NON-DEFAULT colour -- 7. ⚠️ THE SAME FORM AS "
     "`psetkw`: both drive `PSET(x,y),c` and differ only in WHICH colour, which is "
     "precisely why the tier table counts DISTINCT FORMS and not rows. "
     "The `psetkw` row draws in 15, which is "
     "also what a PSET that discarded its colour argument would leave."),
    # 🌾 D-KWBREADTH batch 18 — AXIS (g): A READING THAT SAMPLES ONE POINT OF A
    # RANGE. Measured across the whole row set: the graphics rows use SCREEN 0, 1
    # and 2 and **never SCREEN 3**, so every pixel verb is scored in one bitmap mode
    # only. SCREEN 3 is MULTICOLOUR (64x48) with a different VRAM layout, which is
    # exactly where a mode-specific address calculation would go wrong.
    # 🔴 THE CRUNCH BODY, NOT THE ROW KEY, DECIDES WHICH KEYWORD A ROW IS ABOUT.
    # This was written as `'screen 3'` and `tier_table.stmt_keyword` therefore
    # credited it to SCREEN -- a row named `psetkw_c`, testing PSET, scored for a
    # different keyword entirely and was invisible when PSET's forms were counted.
    ("psetkw_c", 'pset(10,10),15',
     'SCREEN3:PSET(10,10),15:A=POINT(10,10):SCREEN0:PRINT"[X";A;"]"',  "stored",
     "NOECHO:[X FORM:mode-screen3 the SAME verb in a DIFFERENT screen mode -- SCREEN 3 is multicolour "
     "with its own VRAM layout, so the plot and the read-back both go through a "
     "different address calculation. 15 on BOTH machines, MEASURED before this "
     "sentence was written."),
    # 🎚️ D-KWTIER1 (2026-09-14, Joost's rule: connected + N forms + no open item,
    # N by the keyword's own complexity). PSET's form set is FOUR: an explicit
    # colour, the DEFAULT colour, a STEP-relative coordinate, and a second screen
    # mode. The two rows above cover explicit-colour TWICE and screen 3 once; these
    # two close the remaining forms.
    # `COLOR 11` first, so the default is read against a foreground that is NOT the
    # 15 the other rows use -- a PSET that hard-coded 15 would pass otherwise.
    # ⚠️ COLOR is restored AFTER the readout, not before it (the `MAXFILES` lesson:
    # a restore placed ahead of the PRINT destroys the value it was protecting).
    ("psetkw_d", 'pset(5,5)',
     'SCREEN2:COLOR 11:PSET(5,5):A=POINT(5,5):SCREEN0:PRINT"[A";A;"]":COLOR 15',
     "stored",
     "NOECHO:[A FORM:colour-default the colour argument OMITTED, so the CURRENT "
     "foreground must be used: 11, MEASURED on both machines before this sentence "
     "was written. A PSET that hard-coded 15 would read 15."),
    # STEP is RELATIVE to the last point plotted, so the pixel lands 5 right of
    # (10,10). A PSET that parsed STEP and then treated the pair as ABSOLUTE would
    # plot at (5,0) and leave (15,10) blank.
    ("psetkw_e", 'pset step(5,0),15',
     'SCREEN2:PSET(10,10),15:PSET STEP(5,0),15:A=POINT(15,10):SCREEN0:PRINT"[B";A;"]"',
     "stored",
     "NOECHO:[B FORM:step-relative the STEP form -- coordinates relative to the "
     "last point: the pixel lands at (15,10), five right of (10,10), and reads 15. "
     "MEASURED on both machines. An absolute reading would plot at (5,0) and "
     "leave (15,10) blank at 4."),
    ("presetkw", 'preset(1,1)',    
     'SCREEN2:PSET(1,1),15:PRESET(1,1):A=POINT(1,1):SCREEN0:PRINT"[R";A;"]"', "stored",
     "NOECHO:[R FORM:colour-default PRESET must UNDO the PSET: 15 if it does nothing, 4 if it works"),
    # 🌾 D-KWBREADTH batch 14: the row above gives PRESET NO colour, so it scores
    # only "PRESET erases". `PRESET(x,y),c` draws in colour c -- 9 is neither the
    # background 4 nor the foreground 15, so this reads the COLOUR ARGUMENT and a
    # PRESET that always erased would give 4.
    ("presetkw_b", 'preset(3,3),9',
     'SCREEN2:PRESET(3,3),9:A=POINT(3,3):SCREEN0:PRINT"[M";A;"]"',  "stored",
     "NOECHO:[M FORM:colour-explicit PRESET with an explicit COLOUR -- 9. The `presetkw` row omits it "
     "and can only see that PRESET erases."),
    # 🎚️ D-KWTIER1: PRESET's remaining two forms. Its syntax mirrors PSET's --
    # `PRESET [STEP](x,y)[,colour]` -- so N is 4: the two above plus STEP and a
    # second screen mode.
    # ⚠️ DIGIT MARKERS, because every single-letter NOECHO marker A-Z is taken and a
    # letter marker would be a PREFIX of any two-letter one (`marker_tail` matches
    # by SUBSTRING, so `[A` would find a row printing `[AA`).
    # 🎯 BOTH ROWS READ TWO PIXELS, one the verb must CHANGE and one it must LEAVE:
    # `4` alone cannot tell "PRESET erased it" from "PSET never drew it".
    ("presetkw_c", 'preset step(10,0)',
     'SCREEN2:PSET(20,10),15:PSET(10,10),15:PRESET STEP(10,0):A=POINT(20,10):B=POINT(10,10):SCREEN0:PRINT"[1";A;B;"]"',
     "stored",
     "NOECHO:[1 FORM:step-relative the STEP form -- the last point is (10,10), so "
     "`STEP(10,0)` must erase (20,10) and leave (10,10) alone: `[1 4  15 ]`, "
     "MEASURED on both machines before this sentence was written."),
    ("presetkw_d", 'preset(10,10)',
     'SCREEN3:PSET(10,10),15:PSET(12,10),15:PRESET(10,10):A=POINT(10,10):B=POINT(12,10):SCREEN0:PRINT"[2";A;B;"]"',
     "stored",
     "NOECHO:[2 FORM:mode-screen3 the same erase in SCREEN 3, whose multicolour "
     "VRAM layout takes a different address calculation: `[2 4  15 ]`, MEASURED "
     "on both machines before this sentence was written."),
    # 🌾 D-KWBREADTH batch 15 — AXIS (f): `PAINT` and `PUT SPRITE` had NO ROW AS
    # SUBJECT anywhere in the sweep. They appeared only inside other rows' setup
    # lines, so kwcover counted them EXERCISED, the tier table credited the other
    # keyword, and the knife could not reach them at all (it re-runs a keyword's OWN
    # row). These give each one a row it is the SUBJECT of.
    # PAINT: a box drawn with `LINE ,B` bounds the flood, and (15,15) is INTERIOR --
    # a pixel only a FILL sets. Blank is 4.
    ("paintkw",  'paint(15,15),15',
     'SCREEN2:LINE(10,10)-(20,20),15,B:PAINT(15,15),15:A=POINT(15,15):SCREEN0:PRINT"[U";A;"]"',
     "stored",
     "NOECHO:[U the FLOOD -- (15,15) is inside the box and is set by nothing but "
     "FORM:flood PAINT, so 15 filled against 4 blank."),
    # ✅ D-KWPAINT2 CLOSED 2026-09-24 -- PAINT's OTHER TWO FORMS, measured first
    # by an isolated probe with its OWN timing (scratchpad/paintforms_probe.py:
    # the program writes a completion mark and the capture waits for it). The
    # sweep's earlier `?nomarker` on BOTH machines was two different things:
    # ⚠️ in SCREEN 2 a border that differs from the fill is NOT a boundary at all
    # -- eight pixels share one colour pair, so painting 11 recolours the
    # 15-border's own blocks and the flood runs away on BOTH machines -- so the
    # BORDER form is measured in SCREEN 3 (multicolour, each 4x4 block its own
    # colour), where it stops the flood on both: `[5q 11 4]`.
    # ❌ A "HANG" THE ISOLATED PROBE SEEMED TO FIND WAS WITHDRAWN THE SAME DAY
    # (D-PAINTHANG): its captures passed `cap_gap`, which does not delay the
    # capture after RUN. Timed with marks, every flood is 1.73x, any shape.
    ("paintkw_b", 'paint(15,15),11',
     'SCREEN2:LINE(10,10)-(20,20),11,B:PAINT(15,15),11:A=POINT(15,15):B=POINT(5,5):SCREEN0:PRINT"[5p";A;B;"]"',
     "stored",
     "NOECHO:[5p FORM:fill-colour a fill colour other than the foreground: the "
     "box is drawn in 11, the border DEFAULTS to the fill colour, so the flood "
     "stops at it -- `[5p 11  4 ]`, inside filled, outside blank."),
    ("paintkw_c", 'paint(60,60),11,15',
     'SCREEN3:LINE(40,40)-(80,80),15,B:PAINT(60,60),11,15:A=POINT(60,60):B=POINT(20,20):SCREEN0:PRINT"[5q";A;B;"]"',
     "stored",
     "NOECHO:[5q FORM:border-colour a BORDER that differs from the fill, in SCREEN "
     "3 where that is a real boundary: the 15-box stops an 11-fill -- `[5q 11  4 ]`. "
     "A handler that ignored the border would flood past it."),
    # PUT SPRITE: the SCREEN 2 sprite ATTRIBUTE table is at $1B00 (6912) and its
    # first byte is the sprite's Y coordinate, so the write is read straight back
    # out of VRAM. `spritekw` only round-trips SPRITE$, which is the PATTERN table.
    ("putsprite", 'put sprite 0,(100,50),15,0',
     'SCREEN2:SPRITE$(0)=STRING$(8,255):PUT SPRITE 0,(100,50),15,0:A=VPEEK(6912):SCREEN0:PRINT"[V";A;"]"',
     "stored",
     "NOECHO:[V the ATTRIBUTE write -- VPEEK($1B00) is the sprite's Y. `spritekw` "
     "FORM:position round-trips SPRITE$, which is the PATTERN table and a different store."),
    # D-KWPARTIAL: the attribute entry is four bytes -- y, x, PATTERN, COLOUR --
    # and the row above reads only the first. These are DIFFERENT bytes of the same
    # entry, so a handler that wrote the position and dropped the rest passes there
    # and fails here.
    ("putsprite_b", 'put sprite 0,(100,50),13,1',
     'SCREEN2:SPRITE$(1)=STRING$(8,255):PUT SPRITE 0,(100,50),13,1:A=VPEEK(6914):B=VPEEK(6915):SCREEN0:PRINT"[0x";A;B;"]"',
     "stored",
     "NOECHO:[0x FORM:colour-and-pattern the PATTERN number and the COLOUR, bytes 2 "
     "and 3 of plane 0's attribute entry ($1B00 = 6912). `[0x 1  13 ]`."),
    ("pointkw",  'a=point(1,1)',   
     'SCREEN2:PSET(1,1),15:A=POINT(1,1):SCREEN0:PRINT"[T";A;"]"',   "stored",
     "NOECHO:[T FORM:pixel-read POINT as the subject: a stub parses as an array and "
     "reads 0, not 15"),
    # 🌾 D-KWBATCH4: THE ROW ABOVE READS ONLY A PIXEL THAT WAS SET, so a POINT that
    # answered 15 to everything passes it. The second reading is a pixel nothing
    # drew, which is the difference between "reads the plane" and "returns the
    # colour it was just given".
    ("pointkw_b", 'a=point(20,20)',
     'SCREEN2:PSET(1,1),15:A=POINT(1,1):B=POINT(20,20):SCREEN0:PRINT"[0m";A;B;"]"',
     "stored",
     "NOECHO:[0m FORM:pixel-read `[0m 15  4 ]` -- the pixel that WAS set and one "
     "that was not. A POINT returning a constant, or the last colour written, "
     "passes `pointkw` and fails here."),
    ("linekw",   'line(1,1)-(5,1)',
     'SCREEN2:LINE(1,1)-(5,1),15:A=POINT(3,1):SCREEN0:PRINT"[L";A;"]"', "stored",
     "NOECHO:[L FORM:segment reads a pixel in the MIDDLE of the span, so an "
     "endpoint-only LINE fails too"),
    # 🌾 D-KWBREADTH batch 9: the row above draws a plain segment; the `,B` BOX form
    # is untested. (9,1) is the box's TOP-RIGHT CORNER -- on the rectangle, and NOT
    # on the diagonal a `,B`-ignoring LINE would draw between the same two points.
    # So a LINE that parses `,B` and discards it reads 4 (blank) where a real box
    # reads 15.
    ("linekw_b", 'line(1,1)-(9,9),15,b',
     'SCREEN2:LINE(1,1)-(9,9),15,B:A=POINT(9,1):SCREEN0:PRINT"[P";A;"]"', "stored",
     "NOECHO:[P FORM:box the BOX form -- (9,1) is a corner of the rectangle but not "
     "a point on the diagonal, so a discarded `,B` reads 4 instead of 15"),
    # 🌾 D-KWBATCH4: the remaining FOUR of LINE's six forms. Grammar
    # (basic/graphics.asm:182): `LINE [[STEP](x1,y1)] - [STEP](x2,y2) [,[c][,B|BF]]`.
    # 🎯 EVERY ONE READS A PIXEL IT MUST DRAW **AND** ONE IT MUST NOT, and the second
    # reading is chosen to be where the WRONG interpretation would have drawn --
    # not merely somewhere blank, which only proves the screen is not all 15.
    # ⚠️ (7,3), NOT (5,5). The interior point has to be off the DIAGONAL as well as
    # inside the rectangle, or a plain segment reads 15 there too and the row
    # separates BF from `,B` but not from no box suffix at all.
    ("linekw_c", 'line(1,1)-(9,9),15,bf',
     'SCREEN2:LINE(1,1)-(9,9),15,BF:A=POINT(7,3):B=POINT(20,20):SCREEN0:PRINT"[0n";A;B;"]"',
     "stored",
     "NOECHO:[0n FORM:filled-box `BF` FILLS where `,B` draws the outline only. "
     "(7,3) is INSIDE the rectangle, off its edges AND off the diagonal: `[0n 15  4 ]` "
     "for a fill, 4 for a `,B` outline, and 4 for a bare segment -- so one reading "
     "separates BF from BOTH."),
    ("linekw_d", 'line step(0,0)-step(5,0),15',
     'SCREEN2:PSET(10,10),15:LINE STEP(0,0)-STEP(5,0),15:A=POINT(13,10):B=POINT(3,0):SCREEN0:PRINT"[0o";A;B;"]"',
     "stored",
     "NOECHO:[0o FORM:step-relative both coordinates RELATIVE -- the first to the "
     "last point (10,10), the second to the first. The span is (10,10)-(15,10), so "
     "(13,10) is on it. `[0o 15  4 ]`: an ignored STEP draws (0,0)-(5,0) instead, "
     "which puts 15 at (3,0) and leaves (13,10) blank -- BOTH readings move."),
    ("linekw_e", 'line -(20,10),15',
     'SCREEN2:PSET(10,10),15:LINE -(20,10),15:A=POINT(15,10):B=POINT(15,7):SCREEN0:PRINT"[0p";A;B;"]"',
     "stored",
     "NOECHO:[0p FORM:omitted-start the OMITTED first coordinate, which continues "
     "from the last point (GRPAC) -- here (10,10), so the span is horizontal and "
     "(15,10) is on it. `[0p 15  4 ]`: a start defaulting to (0,0) would draw the "
     "diagonal (0,0)-(20,10), which passes through (15,7) and misses (15,10)."),
    ("linekw_f", 'line(1,1)-(5,1)',
     'SCREEN2:COLOR 11:LINE(1,1)-(5,1):A=POINT(3,1):B=POINT(3,10):SCREEN0:PRINT"[0q";A;B;"]":COLOR 15',
     "stored",
     "NOECHO:[0q FORM:colour-default the OMITTED colour, which must come from "
     "FORCLR -- `COLOR 11` first, so `[0q 11  4 ]` proves the span took the "
     "foreground colour and not a hardcoded 15."),
    ("colorkw",  'color 7',    'COLOR 7:PRINT"[O";PEEK(-3095);"]"',              "direct",
     "NOECHO:[O FORM:foreground COLOR repaints the whole screen, echo included. Reads FORCLR "
     "($F3E9 = -3095) back, and uses 7 rather than the DEFAULT 15 on purpose: "
     "a COLOR that parsed and did nothing would leave 15 there and the row "
     "would pass on the default. absent => syntax error, no marker."),
    # 🎚️ D-KWTIER1: COLOR is `COLOR [fg][,bg][,border]`, so its three forms are the
    # three POSITIONS -- and the interesting part is the OMISSION: the parser has to
    # skip a position rather than shift the argument left. FORCLR/BAKCLR/BDRCLR are
    # all declared ($F3E9/$F3EA/$F3EB), so each lands somewhere readable.
    # 🎯 EACH ROW READS THE CELL IT MUST CHANGE **AND** FORCLR, WHICH IT MUST LEAVE:
    # a parser that shifted `COLOR ,5` into the foreground would write 5 where 7
    # must still stand, and reading only the changed cell could not see it.
    # ⚠️ Restored to the MSX default `COLOR 15,4,4` AFTER the readout.
    ("colorkw_b", 'color ,5',
     'COLOR 7:COLOR ,5:A=PEEK(&HF3EA):B=PEEK(&HF3E9):PRINT"[3";A;B;"]":COLOR 15,4,4',
     "stored",
     "NOECHO:[3 FORM:background the BACKGROUND with the foreground OMITTED: "
     "`[3 5  7 ]` -- background 5, and FORCLR still 7, so the omitted position was "
     "SKIPPED and not shifted. MEASURED on both machines before this was written."),
    ("colorkw_c", 'color ,,3',
     'COLOR 7:COLOR ,,3:A=PEEK(&HF3EB):B=PEEK(&HF3E9):PRINT"[4";A;B;"]":COLOR 15,4,4',
     "stored",
     "NOECHO:[4 FORM:border the BORDER with BOTH earlier positions omitted: "
     "`[4 3  7 ]` -- border 3, FORCLR still 7. MEASURED on both machines."),
    # ⚠️ `SCREEN` AND `KEY` ARE NOT HERE YET, each for a stated reason rather
    # than an oversight. SCREEN: the only value that discriminates is a mode
    # CHANGE, and `SCREEN 1` is 32 columns while this capture parses a 40-column
    # screen -- the row would break the reader it depends on. KEY: the natural
    # readback is the function-key buffer, whose address (FNKSTR) is NOT in
    # basic/sysvars.inc, and guessing the standard $F87F would be building on an
    # unverified constant. Both need a measurement first.
    ("clskw",    'cls',        'CLS:PRINT"[C";CSRLIN;"]"',            "direct",
     "NOECHO:[C FORM:no-argument CLS erases the echo by definition -- the exact row the old "
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
     "FORM:column absent => `LOCATE 10` is a bare word + juxtaposition => syntax "
     "error; real => `[X]` indented to column 10"),
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
    ("locate_b", "locate 0,5",   'CLS:LOCATE 0,5:PRINT"[N";CSRLIN;"]"',       "stored",
     "NOECHO:[N " "FORM:row the ROW argument, read back through CSRLIN -- `[N 5 ]`. The "
     "`locate` row sets only a COLUMN and scores the marker's indentation; CLS "
     "anchors the cursor so this reads the ROW and not the scroll history."),
    # 🌾 D-KWBATCH1: THE OMITTED POSITION, WHICH IS THE COLOR SHAPE AGAIN. An
    # omitted LOCATE axis KEEPS its current value (basic/missing.asm:97 records the
    # measurement), so `LOCATE ,7` after `LOCATE 9,3` must move the ROW to 7 and
    # LEAVE the column at 9. A parser that shifted the argument left would put 7 in
    # the COLUMN -- and neither `locate` nor `locate_b` could see that, because each
    # supplies its axis in the position the shift would read anyway.
    ("locate_c", "locate ,7",
     'CLS:LOCATE 9,3:LOCATE ,7:A=CSRLIN:B=POS(0):PRINT"[0b";A;B;"]"', "stored",
     "NOECHO:[0b FORM:omitted-column `[0b 7  9 ]` -- the ROW moved and the COLUMN "
     "did not. CLS anchors the cursor first, because LOCATE moves it and an "
     "unanchored row measures scroll history (the trap `locate_b`'s note records)."),
    # 🔪 D-LOCCSR: the FOURTH form, which basic/missing.asm's O-3 declined as
    # "a write nobody reads". That was a claim about THIS TREE; the reference
    # writes CSRSW ($FCA9) and a row can read it. The sentinel is the control --
    # a cell reading 0 after `LOCATE ,,0` proves nothing unless it held 99 first.
    # ⚠️ `,,2` IS IN THE ROW BECAUSE THE VALUE IS FOLDED: both references store 1
    # for it, where SCREEN's neighbouring switch stores its byte RAW (screenkw_d,
    # `,,2` -> 2). Two adjacent work-area switches, two different rules -- so this
    # row would pass on an implementation copied from that one, and does not.
    ("locate_d", "locate ,,1",
     'C=PEEK(&HFCA9):POKE&HFCA9,99:LOCATE,,0:A=PEEK(&HFCA9):LOCATE,,1:B=PEEK(&HFCA9):LOCATE,,2:D=PEEK(&HFCA9):POKE&HFCA9,C:PRINT"[0e";A;B;D;"]"',
     "stored",
     "NOECHO:[0e FORM:cursor-switch the CURSOR-SWITCH argument, read back through "
     "CSRSW ($FCA9) against a POKEd sentinel. `[0e 0  1  1 ]` -- the third value "
     "is what says the byte is FOLDED to 0/1 rather than stored raw. "
     "🔴 IT SAVES AND RESTORES CSRSW, AND THAT IS NOT TIDINESS: this row is the "
     "first thing in the tree that makes the cell LIVE, and leaving the cursor "
     "enabled changed what the harness typed and read -- 60 keywords went MISSING "
     "in the batch, every one of them printing its CORRECT value and then `Type "
     "mismatch` from the NEXT typed line. In isolation they all passed. A row that "
     "moves global machine state has to put it back, or it measures its "
     "successors."),
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
     "FORM:column-read absent => array POS(0) auto-dims to 0; real => the "
     "(non-zero) column"),

    # The two PRINT-item pseudo-functions. THE `TAB(` TRAP: with TAB absent,
    # `PRINT TAB(5);"X"` prints ` 0 X` (array element 0 then X) instead of
    # padding to column 5 — so compare the TEXT, and never a bare error code.
    ("tab",     'print tab(5);"x"',
     'PRINT"[";TAB(5);"X]"',                         "direct",
     "FORM:tab-item absent => array TAB(5)=0 prints ` 0 `; real => pad to column 5"),
    ("spc",     'print spc(5);"x"',
     'PRINT"[";SPC(5);"X]"',                         "direct",
     "FORM:spc-item absent => array SPC(5)=0 prints ` 0 `; real => 5 spaces"),
    # D-KWPARTIAL: BARE PRINT'S SEPARATORS HAD NO ROW. Its only two rows are the
    # PRINT ITEMS, and PRINT is the apparatus of almost every row in this sweep --
    # constantly exercised, almost never the SUBJECT. Being used is not being
    # measured. Each row below reads a POSITION back rather than looking at the
    # text, so the reading is a number both machines must agree on.
    ("printkw_b", 'print "a","b"',
     'CLS:PRINT"A","B";:A=POS(0):PRINT"[0t";A;"]"',   "stored",
     "NOECHO:[0t FORM:comma-zone the COMMA advances to the next 14-column zone, so "
     "the cursor lands at 15 after `A`,`B`. `[0t 15 ]` -- a comma treated as a "
     "plain separator leaves it at 2."),
    ("printkw_c", 'print "ab";"cd"',
     'CLS:PRINT"AB";"CD";:A=POS(0):PRINT"[0u";A;"]"', "stored",
     "NOECHO:[0u FORM:semicolon the SEMICOLON concatenates with no gap, so four "
     "characters put the cursor at 4. `[0u 4 ]` -- a semicolon that ended the line "
     "would leave 2."),
    ("printkw_d", 'print "ab";',
     'CLS:PRINT"AB";:A=CSRLIN:PRINT"[0v";A;"]"',      "stored",
     "NOECHO:[0v FORM:trailing-suppress a TRAILING separator suppresses the "
     "newline, so the cursor is still on row 0. `[0v 0 ]` -- without the "
     "suppression it has moved to row 1."),

    # Program / editor management.
    ("swap",    "swap a,b",
     'A=1:B=2:SWAP A,B:PRINT"[";A;B;"]"',            "direct",
     "FORM:exchange absent => syntax error; real => ` 2  1 `"),
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
     "FORM:free-ram the machine-dependent absolute free figure cancels."),
    # D-KWFRESTR: `FRE("")` REPORTS THE STRING POOL, A DIFFERENT POOL FROM
    # `FRE(0)`'s free RAM -- not a second input to one behaviour. The row measures
    # a DELTA across a 50-character allocation for the same reason `fre_b` does:
    # the absolute figure is machine-dependent and the delta is not.
    ("fre_c",    'a=fre("")',
     'A=FRE(""):B$=STRING$(50,"X"):C=FRE(""):PRINT"[";A-C;"]"',   "stored",
     "FORM:free-string-space the STRING pool, which `FRE(0)` does not report. A "
     "50-character allocation, read as a DELTA."),
    ("tron",    "tron",
     "TRON:TROFF:PRINT\"[ok]\"",                     "direct",
     "FORM:toggle absent => syntax error; real => accepted (trace toggled off "
     "again)"),
    ("troff",   "troff",
     'TROFF:PRINT"[ok]"',                            "direct",
     "FORM:toggle absent => syntax error"),
    # 🌾 D-KWBATCH3: BOTH ROWS ABOVE PRINT A CONSTANT `[ok]`, which is the THIRD
    # screening axis -- a constant marker cannot see the EFFECT. A TRON that
    # parsed and did nothing prints `[ok]` just as happily. The effect IS
    # scrapeable: MSX TRON prints each line number in brackets as it executes, the
    # way `listkw` scores the listing itself.
    # 🔴 AND THE FIRST CUT OF THIS ROW COULD NOT DISCRIMINATE, WHILE SCORING
    # SUPPORTED. Written as `TRON:A=1:B=2:PRINT"[0k]"` it packed onto ONE numbered
    # line, and TRON switches the trace on DURING line 10 -- whose number has
    # already been printed or not printed -- so with no line 20 there was nothing
    # left to trace. It read `[0k]`, which is exactly what a dead TRON reads, and
    # both machines agreed on it. 🎯 THE REM IS NOT PADDING FOR LENGTH, IT IS THE
    # SECOND LINE the trace has to reach.
    ("tron_b",  "tron",
     'TRON:A=1:REM ZZZZZZZZZZZZZZZZZZZZZZZZZ:B=2:PRINT"[0k]"',   "stored",
     "NOECHO:[0k FORM:toggle the TRACE ITSELF: with TRON live each line number is "
     "printed before that line runs, so the capture reads the traced numbers ahead "
     "of the marker where a TRON that parsed and did nothing reads `[0k]` alone. "
     "Line 10 is never traced -- TRON turns on inside it."),
    # 🎯 AND TROFF NEEDS A LINE **AFTER** THE TROFF, or the row cannot see it: the
    # trace prints the number BEFORE executing the line, so the line carrying TROFF
    # is traced either way. The REMs are padding that forces `as_stored` to split
    # the statements across numbered lines -- it packs greedily into <=34-char
    # bodies, so without them TROFF and the PRINT land on one line and there is
    # nothing left to leave untraced.
    ("troff_b", "troff",
     'TRON:A=1:REM ZZZZZZZZZZZZZZZZZZZZZZZZZ:TROFF:B=2:REM QQQQQQQQQQQQQQQQQQQQQQ:PRINT"[0g]"',
     "stored",
     "NOECHO:[0g FORM:toggle the trace STOPPING. MEASURED `[20][30][0g]`: line 10 "
     "is not traced because TRON turns on inside it, line 30 IS traced because the "
     "number is printed BEFORE the TROFF on it runs, and lines 40-50 are not -- "
     "where a TROFF that parsed and did nothing reads `[20][30][40][50][0g]`."),
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
    # 🟢 D-KWEDIT: `RENUM` in DIRECT MODE -- see the DELETE block above for why the
    # filed closure was about the mode and not the verb.
    # 🔴 THE PROGRAM STARTS AT 5/7/9 AND NOT 10/20/30 ON PURPOSE. Bare `RENUM`
    # renumbers from 10 by 10, so on a program that is ALREADY 10/20/30 it is a
    # no-op and the row would agree on a constant -- the reading has to be able to
    # tell a renumbering from nothing happening.
    ("ren_bare",  "renum",
     "RENUM",                                                "direct",
     "NEEDS-LOG: PROGRAM:5_REM_Z1|7_REM_Z2|9_REM_Z3 RESPOND:LLIST "
     "FORM:renumber-all 5/7/9 becomes 10/20/30 -- the defaults, start 10 step 10"),
    ("ren_start", "renum 100",
     "RENUM 100",                                            "direct",
     "NEEDS-LOG: PROGRAM:5_REM_Z1|7_REM_Z2|9_REM_Z3 RESPOND:LLIST "
     "FORM:renumber-from a new START, 100/110/120 -- the step stays 10"),
    ("ren_old",   "renum 100,7",
     "RENUM 100,7",                                          "direct",
     "NEEDS-LOG: PROGRAM:5_REM_Z1|7_REM_Z2|9_REM_Z3 RESPOND:LLIST "
     "FORM:renumber-partial renumber only from OLD line 7 on -- 5 stays 5 and 7/9 "
     "become 100/110, which no other form can produce"),
    ("ren_step",  "renum 100,,20",
     "RENUM 100,,20",                                        "direct",
     "NEEDS-LOG: PROGRAM:5_REM_Z1|7_REM_Z2|9_REM_Z3 RESPOND:LLIST "
     "FORM:renumber-increment the third argument, 100/120/140 -- the OMITTED middle "
     "argument is the part a parser can shift left"),

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
     'DEFSNG A:A=1.5:PRINT"[";A;"]"',                "direct", "FORM:single-letter control"),
    # ⚠️ DEFSNG's range row must make the default WRONG first: single precision is
    # already the default, so `DEFSNG A-C` alone proves nothing. DEFINT first.
    ("defsng_b", 'defsng a-c',
     'DEFINT A-C:DEFSNG A-C:C=1.5:PRINT"[";C;"]"',    "stored",
     "FORM:letter-range the RANGE form, measured against a DEFINT that made C an "
     "integer first: `[ 1.5 ]` where an unexpanded range leaves C integer and "
     "prints 1."),
    ("defdbl",  "defdbl a",
     'DEFDBL A:A=1.5:PRINT"[";A;"]"',                "direct", "FORM:single-letter control"),
    ("defdbl_b", 'defdbl a-c',
     'DEFDBL A-C:C=1/3:PRINT"[";C;"]"',               "direct",
     "FORM:letter-range the RANGE form. 1/3 is the discriminator, not 1.5: it "
     "prints with SINGLE precision's digits unless C really became double, and "
     "1.5 is exact in both."),
    ("defstr",  "defstr a",
     'DEFSTR A:A="x":PRINT"[";A;"]"',                "direct", "FORM:single-letter control"),
    ("defstr_b", 'defstr a-c',
     'DEFSTR A-C:C="x":PRINT"[";C;"]"',               "direct",
     "FORM:letter-range the RANGE form -- without it `C=\"x\"` is a Type mismatch, "
     "so the reading is `x` against an ERROR and not against another value."),

    # User-defined functions.
    # STORED, not direct: the reference answers `Illegal direct` to a direct-mode
    # DEF FN — measured, first run of this sweep. So the direct form tests the
    # direct-mode restriction, not the feature.
    ("deffn",   "def fna(x)=x+1",
     'DEF FNA(X)=X+1:PRINT"[";FNA(2);"]"',           "stored",
     "SUBJECT:DEF_FN FORM:numeric absent => syntax error; real => 3"),
    # D-KWPARTIAL: the RESULT TYPE is DEF FN's second form and not a detail -- a
    # string-valued FN needs a GC root the numeric one does not.
    # 🌾 D-KWBARS: `FN` is the CALL side and `DEF FN` is the definition side; the
    # two rows below the anchor define AND call, but their subject is the DEF FN
    # statement, so cutting the FN dispatch in the evaluator is a cut neither can
    # speak for. Two forms, mirroring DEF FN's own: a numeric function and a
    # string-valued one, which return through different paths.
    ("fnkw",   'a=fnb(5)',
     'DEF FNB(X)=X*X:PRINT"[";FNB(5);"]"',                    "stored",
     "SUBJECT:FN FORM:numeric 25: the ARGUMENT reached the body. A call that passed "
     "0 reads 0, and one that returned the argument reads 5. "
     "\U0001f534 STORED THOUGH IT FITS DIRECT, AND THE FIRST CUT PROVES WHY: `DEF FN` "
     "is ILLEGAL DIRECT, so the direct form scored SUPPORTED on `Illegal direct` "
     "from BOTH machines -- an agreement about nothing "
     "[[a-case-that-agrees-can-agree-for-the-wrong-reason]]."),
    ("fnkw_b", 'a$=fnt$("z")',
     'DEF FNT$(X$)=X$+"?":PRINT"[";FNT$("Z");"]"',            "stored",
     "SUBJECT:FN FORM:string-valued `Z?`: the string return path, which is a "
     "different one from the numeric"),
    ("deffn_b", 'def fns$(x$)=x$+"!"',
     'DEF FNS$(X$)=X$+"!":PRINT"[";FNS$("A");"]"',    "stored",
     "SUBJECT:DEF_FN FORM:string-valued the STRING-valued definition, whose result "
     "lives in the string pool where the numeric one is a float. `[A!]`."),

    # The two missing logical operators.
    ("eqv",     "a=5 eqv 3",
     'PRINT"[";5 EQV 3;"]"',                         "direct",
     "FORM:equivalence absent => juxtaposition syntax error; real => -7"),
    ("imp",     "a=5 imp 3",
     'PRINT"[";5 IMP 3;"]"',                         "direct",
     "FORM:implication absent => juxtaposition syntax error; real => -5"),

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
     "NEEDS-LOG: " "FORM:list-to-printer the listing itself, off the printer log -- the row's own "
     "stored program. Absent => Syntax error on the SCREEN and an empty log, which "
     "is why the CLASS comes from the screen and only the TEXT from the log."),

    # Cassette / misc statements.
    # 🌾 D-KWMOTOR: the cassette motor is READABLE, and this row used to print a
    # CONSTANT. `MOTOR OFF:PRINT"[ok]"` scored absence and nothing else -- a MOTOR
    # that parsed and did nothing passed it. Bit 4 of PPI port C is the motor line:
    # `INP(&HAA)AND16` is 16 with the motor OFF and 0 with it ON.
    # 🔴 THE MASK IS LOAD-BEARING, NOT TIDINESS. The WHOLE port reads 90/74 on the
    # VG-8020 and 87/71 on zerobas (scratchpad/mdr_probe.py, which also settled
    # that DELETE and RENUM have no happy-path reading in a sweep row at all):
    # the other bits differ between the machines and a raw `INP(&HAA)` row would
    # report a DIVERGENCE that is not one. Masked to bit 4 both machines agree
    # exactly, and the 16 -> 0 step is the motor line moving.
    ("motor",   "motor off",
     'MOTOR OFF:A=INP(&HAA)AND16:PRINT"[2n";A;"]"',   "stored",
     "FORM:off 16: the motor line is HIGH (idle)"),
    ("motor_b", "motor on",
     'MOTOR ON:A=INP(&HAA)AND16:MOTOR OFF:PRINT"[2m";A;"]"', "stored",
     "FORM:on 0: the motor line is PULLED DOWN -- the motor is running. The row "
     "puts it back before it prints, so the machine is left as it was found"),
    ("motor_c", "motor",
     'MOTOR OFF:MOTOR:A=INP(&HAA)AND16:MOTOR OFF:PRINT"[2o";A;"]"', "stored",
     "FORM:toggle the BARE form TOGGLES: started from OFF it reads 0, the same as "
     "`MOTOR ON` -- so the row proves the operand-less form is not a no-op"),
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
     "FORM:read THE discriminator: a real TIME advances across a delay loop; the "
     "variable `TI` does not. This is the row that catches the silent gap."),
    # 🌾 D-KWBATCH2: `TIME = <expr>` is the WRITE half (ex_time_assign,
    # basic/time.asm:43), a different handler from the `$CB` read selector.
    # 🎯 AND IT IS ALSO WHERE TIME'S **VALUE** GETS SCORED. `timetick` above can
    # only ask `TIME>T`, a BOOLEAN, and it has to: zerobas is 2.5-3.8x slower than
    # the reference (the open on-par-speed item), so a delay loop's TIME VALUE would
    # diverge on INTERPRETER SPEED and report it as a TIME defect. Writing a known
    # value and reading it back has no such dependence.
    # ⚠️ `INT(TIME/100)`, NOT `TIME`: the clock ticks at 50/60 Hz between the write
    # and the read, so the raw value is not reproducible. Divided by 100 it is
    # stable for ~100 ticks, and both readings sit exactly on a multiple.
    ("time_c",  "time=30000",
     'TIME=30000:A=INT(TIME/100):TIME=10000:B=INT(TIME/100):PRINT"[0e";A;B;"]"',
     "stored",
     "NOECHO:[0e FORM:write the ASSIGNMENT form. `[0e 300  100 ]` -- two different "
     "written values read back, so a TIME= that parsed and dropped the value shows "
     "up, and the reading is a VALUE rather than the boolean `timetick` is forced "
     "into by the interpreter-speed difference."),

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
    # 🌾 D-KWBATCH5: same axis. `mki` reads `LEN(MKI$(1))` = 2, which an MKI$
    # returning two arbitrary bytes passes. 258 is $0102, so the two bytes are
    # DIFFERENT and the row sees the VALUE **and the byte order**: little-endian is
    # `[ 2  1 ]` and a big-endian store reads `[ 1  2 ]`.
    # ⏱ D-KWTLONG (2026-09-24): SPLIT SO EVERY STATEMENT TYPES IN 38 COLUMNS --
    # kwtime types explicitly numbered lines and cannot deliver one longer, so
    # this row's keyword had no T2 reading. The READING is unchanged: `B$` holds
    # the same RIGHT$ the PRINT used to compute inline.
    ("mki_c",   'a$=mki$(258)',
     'A$=MKI$(258):B$=RIGHT$(A$,1):PRINT"[";ASC(A$);ASC(B$);"]"',        "stored",
     "NEEDS-DISK: " "FORM:int-to-string the BYTES and their ORDER -- 258 = $0102 "
     "stored low byte "
     "first, so `[ 2  1 ]`. `mki` reads only the LENGTH, which any two bytes pass, "
     "and `mki_b` further down reads only the FIRST byte, so neither can see the "
     "byte ORDER: a big-endian store reads `[ 1  2 ]` here and `[ 1 ]` there."),
    ("mks",     'a$=mks$(1)',   'PRINT"[";LEN(MKS$(1));"]"',  "direct",
     "NEEDS-DISK: " "FORM:single-to-string absent => syntax error; real => 4"),
    # D-KWBATCH7: same axis as `mki` -- a LENGTH cannot see CONTENT, and 4 is what
    # any four bytes read. The single-precision byte layout is not predicted here:
    # the row prints the length AND the first byte, and what makes it a reading is
    # that BOTH MACHINES MUST AGREE on the byte. A stub returning four zeros reads
    # a different first byte from the real encoder.
    ("mks_b",   'a=asc(mks$(1.5))', 'PRINT"[";ASC(MKS$(1.5));"]"', "direct",
     "NEEDS-DISK: " "SUBJECT:MKS$ FORM:single-to-string MKS$'s CONTENT, where its "
     "own row scores only LENGTH -- and "
     "`LEN(MKS$(1))=4` is passed by a stub returning four ZERO bytes. 1.5 packs "
     "as 65 21 0 0, MEASURED on the CF-3300 and equal to PEEK(VARPTR(A!)) for "
     "A!=1.5 (basic/str-engine.asm), so the exponent byte reads 65."),
    ("mkd",     'a$=mkd$(1)',   'PRINT"[";LEN(MKD$(1));"]"',  "direct",
     "NEEDS-DISK: " "FORM:double-to-string absent => syntax error; real => 8"),
    ("mkd_b",   'a=asc(mkd$(1.5))', 'PRINT"[";ASC(MKD$(1.5));"]"', "direct",
     "NEEDS-DISK: " "SUBJECT:MKD$ FORM:double-to-string the same content reading "
     "on the 8-byte DOUBLE pack, whose row likewise scores only LENGTH."),
    ("cvs",     'a=cvs("abcd")', 'PRINT"[";CVS(MKS$(1));"]"', "direct",
     "NEEDS-DISK: " "FORM:string-to-single absent => syntax error; real => 1"),
    ("cvd",     'a=cvd("abcdefgh")', 'PRINT"[";CVD(MKD$(1));"]"', "direct",
     "NEEDS-DISK: " "FORM:string-to-double absent => syntax error; real => 1"),

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
     "NEEDS-DISK: " "SUBJECT:MKI$ FORM:int-to-string MKI$'s CONTENT, NOT ITS "
     "LENGTH. The `mki` row scores "
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
     "FORM:default VALUE. $E000 is the cell `pokekw` already uses."),
    # 🌾 D-KWUSRN: MSX has TEN user-routine vectors and `USR<n>` selects which, so
    # the numbered form reaches a DIFFERENT ADDRESS -- not a second input to the
    # same behaviour. `DEFUSR1` must be set for it, which is the point: a USR that
    # ignored the digit would read vector 0 and answer whatever THAT holds.
    # 🌾 D-KWONTRAP: `DEF USR` is a STATEMENT and the two rows above are `USR`'s --
    # their subject is the function that READS the vector, so cutting `DEF`'s
    # stmt_table entry is a cut neither of them can speak for. These two carry the
    # same bodies under their own subject for exactly that reason: the reading is
    # the same 7, and what it proves here is that the DEF USR STATEMENT is what put
    # the address in the cell.
    ("defusr",   'def usr=-8192',
     'POKE-8192,&HC9:DEFUSR=-8192:A=USR(7):PRINT"[1u";A;"]"',   "stored",
     "FORM:default the DEFAULT vector: the POKEd byte is a RET, so USR(7) returns 7 "
     "only if DEF USR stored -8192 in vector 0"),
    ("defusr_b", 'def usr1=-8192',
     'POKE-8192,&HC9:DEFUSR1=-8192:A=USR1(7):PRINT"[1v";A;"]"', "stored",
     "FORM:numbered the NUMBERED vector -- a DIFFERENT CELL. A DEF USR that ignored "
     "the digit would write vector 0 and leave vector 1 undefined, which `USR1` "
     "cannot then call"),
    ("usrkw_b",  'a=usr1(7)',
     'POKE-8192,&HC9:DEFUSR1=-8192:A=USR1(7):PRINT"[";A;"]"',  "stored",
     "FORM:numbered the NUMBERED vector: `DEFUSR1` points at an `ret` and `USR1(7)` "
     "returns its argument, so `[ 7 ]`. A USR that ignored the digit reads vector "
     "0, which this row never sets."),
    ("screenkw", "screen 2",
     'SCREEN2:A=PEEK(&HFCAF):SCREEN0:PRINT"[G";A;"]"',          "stored",
     "NOECHO:[G SCRMOD ($FCAF, DECLARED in basic/sysvars.inc) reads 2 inside "
     "SCREEN 2 and 0 in text mode, on both machines -- so the row sees the MODE "
     "and not merely that the statement parsed, and it reads the mode BEFORE "
     "returning to SCREEN 0 because a graphics screen cannot be scraped as text. "
     "FORM:mode"),
    # 🌾 D-KWBATCH1: SCREEN'S SECOND ARGUMENT IS REAL HERE (G7_RESIDENT=1,
    # basic/sysvars.inc:489) and no row ever read it. RG1SAV ($F3E0, DECLARED) is
    # the VDP register 1 mirror whose bits 1..0 ARE the sprite size, so the row
    # prints the mirror at size 3 and again at size 0: the two readings must differ
    # by exactly 3 and agree in every other bit.
    # 🔴 AND THE HISTORY SAYS WHY THIS IS WORTH A ROW: `SCREEN 1,,99` once applied
    # 99 AS THE SPRITE SIZE (basic/screen.asm:121) and NO row could see it -- the
    # old `and $03` turned it into size 3, and a wrong sprite size does not show up
    # in SCRMOD, which is the only cell `screenkw` reads.
    ("screenkw_c", "screen 2,3",
     'SCREEN2,3:A=PEEK(&HF3E0):SCREEN2,0:B=PEEK(&HF3E0):SCREEN0:PRINT"[0c";A;B;"]"',
     "stored",
     "NOECHO:[0c FORM:sprite-size the SPRITE-SIZE argument, read back through "
     "RG1SAV ($F3E0). A and B must differ by exactly 3 (bits 1..0) and match "
     "everywhere else -- a handler that wrote the whole register, or the wrong "
     "one, moves the other bits too."),
    # 🔪 D-SCRCLICK: the THIRD form, which TODO.md filed as unmeasurable -- "the
    # key click has no cell any row here can read". CLIKSW $F3DB is a published
    # work-area cell and both references move it, so the claim was an INSTRUMENT
    # assumption rather than a fact about the machine.
    # 🎯 THE SENTINEL IS THE CONTROL. Reading 0 after `SCREEN ,,0` proves nothing
    # on its own -- the cell may have been 0 already, or always be 0. POKEing 99
    # first means a row that reads 0 has WATCHED SCREEN write it.
    # ⚠️ AND `,,2` IS IN THE ROW ON PURPOSE: both references store the byte RAW, so
    # an implementation that normalised to 0/1 would look right on the first two
    # values and be wrong on the first one anyone varies.
    ("screenkw_d", "screen ,,1",
     'POKE&HF3DB,99:SCREEN,,0:A=PEEK(&HF3DB):SCREEN,,1:B=PEEK(&HF3DB):SCREEN,,2:PRINT"[0d";A;B;PEEK(&HF3DB);"]"',
     "stored",
     "NOECHO:[0d FORM:key-click the KEY-CLICK argument, read back through CLIKSW "
     "($F3DB) against a POKEd sentinel. `[0d 0  1  2 ]` -- the third value is what "
     "says the byte is stored RAW rather than folded to 0/1."),
    ("keykw",    'key 1,"x"',
     'KEY 1,"ZZQ":KEY LIST',                                    "stored",
     "FORM:list D-KWRIG: `KEY LIST` prints all ten definitions and the row compares the "
     "WHOLE listing: the ten defaults are identical on both machines, so the only "
     "difference either side can show is `ZZQ` in slot 1 -- which is there only if "
     "the assignment happened. No FNKSTR constant is needed or guessed."),
    # 🔴 D-KEYRIG (2026-09-15): THE ROW ABOVE *PERFORMS* THE ASSIGNMENT AND
    # CANNOT SCORE IT. Its own note says the listing differs "only if the
    # assignment happened" -- but a row declares ONE `FORM:`, and that one is
    # `list`. So `assign` was uncovered by a row that exercises it.
    # 🎯 THIS ROW READS THE ASSIGNMENT AS THE BEHAVIOUR IT ACTUALLY IS: a
    # function-key MACRO TYPES ITS STRING into the keyboard buffer when the key is
    # pressed, and the key-matrix rig can press it (`NEEDS-HOLD:6,0x20` is F1, the
    # same hold the `onkey` rows use). `INKEY$` then reads back what the macro
    # typed -- an effect, not a listing.
    # 🔴 ITS CONTROL IS THE DEFAULT MACRO AND IT CAN FAIL: F1 defaults to
    # `color `, so holding F1 with NO assignment reads `co` on both machines
    # (scratchpad/keyassign_probe.py). If that ever read `ZQ`, or nothing, the rig
    # would not be reaching the key and this row would mean nothing. The DIFFERENCE
    # between `co` and `ZQ` is the assignment, and neither is a constant.
    # ⚠️ `KEY 1,""` BEFORE THE PRINT IS LOAD-BEARING. The macro AUTO-REPEATS for
    # as long as the key is held -- the same flood that made the `onkey` rows read
    # `?noecho` on the faster reference -- and the control's first cut, which did
    # not disarm, came back as an unparseable screen of `color color color...`.
    # It still proved the rig reached F1, but an unreadable cell is not a verdict.
    ("keykw_b",  'key 1,"x"',
     '''KEY 1,"ZQ":A$="":T=TIME:W$="WWWWWWWWWWWWWWWWWW":A$=A$+INKEY$:V$="VVVVVVVVVVVVVVVVVV":IF LEN(A$)<2 AND TIME-T<99 THEN 30:KEY 1,"":PRINT"[3r";LEFT$(A$,2);"]"''',
     "stored",
     "NEEDS-HOLD:6,0x20 FORM:assign `ZQ` typed BY THE MACRO with F1 held -- the "
     "assigned string coming back through `INKEY$`. Unassigned, the same hold "
     "reads `co` from F1's default `color `, so the reading is the assignment and "
     "not the rig"),
    # 🚫 D-KWOSK: `KEY ON` / `KEY OFF` HAVE NO ROW, AND THE REASON IS MEASURED.
    # The obvious instrument is the FUNCTION-KEY LINE in VRAM -- `KEY OFF` blanks
    # it -- but its layout is NOT the same on the two machines:
    # `PEEK(&HF3B0)` (LINLEN) reads **37 on the VG-8020 and 39 on zerobas**, and
    # the reference's assigned string lands at name-table offset 922 while a fixed
    # offset reads a space on the other side. The first cut of these rows scored
    # SUPPORTED on `32` from BOTH machines -- an agreement about a blank cell
    # [[a-case-that-agrees-can-agree-for-the-wrong-reason]] -- and the scan that
    # found the real offset (scratchpad/keyline_probe.py) is what
    # said why. The display forms stay UNCOVERED rather than measured wrongly.
    # 🟢 D-AKCM (2026-09-17): THEY HAVE AN INSTRUMENT NOW, AND IT IS NOT A VRAM
    # CELL. `KEY ON` reserves the bottom line for the function-key display, so the
    # TEXT WINDOW is one row shorter -- and a ROW INDEX is machine-independent
    # where a name-table offset is not. `LOCATE 0,23` then `CSRLIN` reads:
    #     KEY OFF   23 on the VG-8020 and 23 here      -- agree
    #     KEY ON    22 on the VG-8020 and 23 here      -- 🔴 DIVERGENT
    # 🔴 SO `KEY ON` DOES NOT RESERVE THE LINE HERE. That is a TIER 1 defect, not
    # an evidence gap, and it is filed as one; only the form that AGREES is
    # authored below. ⚠️ THE `display-on` ROW IS OWED, not written off: it belongs
    # with the fix, and the item says so
    # [[a-row-written-off-as-out-of-scope-leaves-the-bookkeeping]].
    # ⚠️ `CRTCNT` ($F3B1) IS NOT THE OBSERVABLE and was the obvious guess: it reads
    # **24 on both machines in BOTH states**, delta 0. A row on it would have
    # agreed on a constant -- the same mistake as the blank VRAM cell, in a new
    # cell (scratchpad/akcm_probe.py).
    # 🟢 D-FNKLINE + D-SCROLLBOUND (2026-09-17): THE ROW THAT WAS OWED. With the
    # line painted and the row RESERVED (`key_on` decrements `CRTCNT`), `KEY ON`
    # takes row 23 and `LOCATE 0,23` clamps to **22** -- which is what the
    # reference has always done and what this tree did not.
    # ⚠️ Same `CLS`-then-print shape as `keykw_off` below, and the same NOECHO:
    # anchor for the same reason: the CLS that normalises the scroll geometry
    # takes the echoed command with it.
    ("keykw_on",  'key on',
     'KEY ON:LOCATE 0,23:A=CSRLIN:CLS:PRINT"[K5";A;"]"',        "stored",
     "NOECHO:[K5 "
     "FORM:display-on with the function-key line shown, row 23 belongs to it and "
     "`LOCATE 0,23` clamps to 22. Its twin `keykw_off` reads 23 from the same "
     "spelling, so the PAIR is the reading and neither cell is a constant"),
    ("keykw_off", 'key off',
     'KEY OFF:LOCATE 0,23:A=CSRLIN:CLS:PRINT"[K4";A;"]"',        "stored",
     "NOECHO:[K4 "
     "FORM:display-off \u26a0\ufe0f THE `CLS` IS LOAD-BEARING: the first cut printed "
     "from wherever `LOCATE 0,23` left the cursor and scored DIVERGENT on the "
     "SCREEN FURNITURE -- 19 line separators against 20 -- while BOTH machines "
     "read 23. The value is the reading; the scroll geometry is not, and the two "
     "boot screens do not agree on it. Snapshot CSRLIN, clear, then print. "
     "\u26a0\ufe0f AND THE `CLS` TAKES THE ECHOED COMMAND WITH IT, so the row is "
     "anchored on its own `[K4` marker (NOECHO:) instead -- the second cut scored "
     "UNREADABLE on both sides for exactly that reason. "
     "With the function-key line given back, row 23 is inside the "
     "text window and CSRLIN reads 23 on both machines. Its twin `KEY ON` reads 22 "
     "there and 23 here, which is the filed TIER 1 divergence -- so this row is "
     "the half that agrees, and it is a ROW INDEX rather than a VRAM offset "
     "because the two machines' name tables do not line up"),
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
     "FORM:port-mask D-KWRIG: mask &HFF against a port measured at 240 on both machines"),
    # 🌾 D-KWRETRES: the THIRD operand, which INVERTS the sense of the test. The
    # same measured port carries it: INP(&HA8) is 240 on both machines, so its LOW
    # NIBBLE is zero -- `WAIT &HA8,&H0F` alone would spin FOR EVER, and
    # `WAIT &HA8,&H0F,&H0F` returns at once because the xor turns those four zero
    # bits into ones. That is the whole discrimination: a WAIT that PARSED the xor
    # and dropped it does not come back, so the `[1m]` is the xor being APPLIED and
    # not merely accepted. `ex_wait` (basic/vdpio.asm:72) does apply it, which is
    # why this row is safe to run at all -- the row above scores absence, this one
    # scores the operand.
    ("waitkw_b", "wait 0,1,1",
     'WAIT &HA8,&H0F,&H0F:PRINT"[1m]"',                         "stored",
     "FORM:port-mask-xor the low nibble of 240 is 0, so only the xor can satisfy the mask"),

    # --- the printer pair. They need a PLUGGED printer (NEEDS-PRINTER:), and that
    # tag is not decoration: with nothing on the port both rows produce NO OUTPUT
    # AT ALL on both machines -- the LSTOUT hang, measured
    # (scratchpad/kwdrain_lptchk.out).
    ("lposkw",   "a=lpos(0)",
     'LPRINT"ABC";:PRINT"[P";LPOS(0);"]"',                      "stored",
     "NEEDS-PRINTER: " "FORM:column-read the head COLUMN, which reaches the screen "
     "even though the "
     "printed text does not: 0 at rest, 3 after three bytes, 7 after seven, the "
     "same on both machines. 🔴 THE `LPRINT` IS THE ROW: batch 4g measured bare "
     "`LPOS(0)` as 0 against a stub's 0 and left the word unattributed for exactly "
     "that reason -- the readback had to be MOVED before it could be read."),
    ("lprintkw", 'lprint"x"',
     'LPRINT"ABC";:PRINT"[P";LPOS(0);"]"',                      "stored",
     "NEEDS-PRINTER: " "FORM:print-to-printer the same measurement from the other end, and deliberately "
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
     "NEEDS-DISK: " "FORM:free-space 707 free KB on the 720 KB fixture, against a stub's 0. This is "
     "the row the empty drive was hiding: DSKF is not a stub and never was."),
    ("files",   "files",
     'FILES"HI.TXT":PRINT"[8]"',                     "stored",
     "NEEDS-DISK: " "FORM:pattern the LISTING is the behaviour, and it is inside the compared "
     "text: the tail reads `HI      .TXT` then the marker, so a FILES that printed "
     "nothing, or named the wrong entry, fails on text even though the marker is "
     "there. Absent => syntax error => no marker at all."),
    # 🌾 D-KWFILESBARE: the BARE catalogue. The row above passes a PATTERN, so a
    # FILES that ignored its argument would pass it; this one has no argument to
    # ignore and the whole listing is the reading.
    ("files_b",  'files',
     'FILES:PRINT"[9]"',                              "stored",
     "NEEDS-DISK: " "FORM:bare the WHOLE catalogue, which is inside the compared "
     "text -- every entry on the fixture, then the marker."),
    ("lof",     "a=lof(1)",
     'OPEN"HI.TXT"FOR INPUT AS#1:A=LOF(1):CLOSE#1:PRINT"[";A;"]"', "stored",
     "NEEDS-DISK: " "26 — HI.TXT's exact length, which only a real directory walk "
     "FORM:length produces; a stub reads 0."),
    # 🌾 D-KWBREADTH batch 18 — AXIS (g) ON THE FILE SIDE: every one of the 17 file
    # rows opens channel #1 and nothing ever opens a second, so the channel NUMBER
    # is a constant across all of them. MSX defaults MAXFILES to 1, so a second
    # channel needs it raised -- which makes this the only row with TWO files open
    # at once. MAXFILES is put back, so the machine is left as it was found.
    # 🔴 AND IT BELONGS WITH THE **READERS**, WHICH THE FIRST PLACEMENT GOT WRONG.
    # It was filed after `fieldkw` with the writers by reflex -- but MAXFILES is
    # MACHINE state, not DISK state, and both opens are FOR INPUT, so the row
    # creates and changes nothing. Down there it ran AFTER `dsko` (which rewrites
    # the first byte of the ROOT DIRECTORY) and `kill`, and read `[ 0 ]` -- ZERO ON
    # BOTH SIDES, which is mode 2, because the fixture it was reading had already
    # been mutated. THE ORDERING RULE CUTS BOTH WAYS: a writer must go last, and a
    # READER MUST GO BEFORE THE WRITERS OR IT READS A FIXTURE THAT HAS MOVED.
    ("openkw_b", 'open"prog.bas"for input as#2',
     'MAXFILES=2:OPEN"HI.TXT"FOR INPUT AS#2:A$=INPUT$(2,#2):CLOSE#2:PRINT"[";A$;"]":MAXFILES=1',
     "stored",
     "NEEDS-DISK: " "FORM:input a SECOND CHANNEL, where every one of the other file rows uses "
     "#1 alone -- the channel NUMBER was a constant across all 17 of them. Reads "
     "[He], the first two bytes of HI.TXT, through #2. MEASURED on both machines "
     "before this sentence was written. "
     "🔴 THE `MAXFILES=1` RESTORE MUST COME AFTER THE `PRINT`, AND THAT COST FOUR "
     "SWEEPS TO SEE: assigning MAXFILES performs an implicit CLEAR, so restoring "
     "it before the readout WIPED A$ and the row read `[]` -- the tidy-up "
     "destroying the measurement it was protecting. "
     "🔬 AND TWO THINGS MEASURED ALONG THE WAY, both identical on both machines and "
     "so faithful rather than defects: with a second channel open `LOF(1)` reads 0 "
     "where the `lof` row reads 26 with one, and a read from #1 while #2 is open "
     "returns nothing -- which is why the observable here is #2 alone."),
    # 🌾 D-KWRETRES: `MAX FILES` had no row of its own -- openkw_b USES it, but that
    # row's subject is OPEN and its reading is OPEN's. This one is disk-free and
    # scores the part a parse-and-ignore MAXFILES cannot fake: assigning MAXFILES
    # RE-ALLOCATES the file-control blocks and performs an IMPLICIT CLEAR, so the 7
    # assigned one statement earlier is gone. A MAXFILES that parsed and did nothing
    # reads `[1p 7 ]`. The restore comes AFTER the PRINT for the same reason it does
    # in openkw_b: put it first and the tidy-up wipes the measurement.
    ("maxfiles", 'maxfiles=2',
     'A=7:MAXFILES=2:PRINT"[1p";A;"]":MAXFILES=1',              "stored",
     "SUBJECT:MAX_FILES FORM:set the implicit CLEAR: 0, not the 7 assigned just "
     "before it. \U0001f534 THE SUBJECT TAG IS LOAD-BEARING: the crunch word is "
     "`maxfiles=2`, ONE word, and `stmt_keyword` reads words -- so the row scored "
     "for NOBODY until the tag named the composite the tokeniser splits it into."),
    ("eof",     "a=eof(1)",
     'OPEN"HI.TXT"FOR INPUT AS#1:A$=INPUT$(26,#1):A=EOF(1):CLOSE#1:PRINT"[";A;"]"', "stored",
     "NEEDS-DISK: " "-1 AFTER the whole file is consumed. 🔴 THE READ IS THE ROW: "
     "measured, EOF(1) is 0 on the same channel before the INPUT$ and -1 after, so "
     "this moves with the channel rather than answering a constant. A stub reads 0 "
     "FORM:at-end — which is the BEFORE value, so the row had to be the after one."),
    ("bload",   'bload"x"',
     'POKE&HC000,7:BLOAD"PROG.BIN":A=PEEK(&HC000):PRINT"[";A;"]"', "stored",
     "NEEDS-DISK: " "PROG.BIN is a real BSAVE binary loading at $C000 whose first "
     "byte is $3E (62); the cell is poked to 7 first, so the row reads what the "
     "FORM:plain LOAD put there and not what was already in RAM."),
    # 🟢 D-KWTAPE2: THE LAST TWO WORDS OF THE DRAIN THAT HAD A MACHINE ANSWER.
    # Both waited on apparatus, and both blockers turned out to be real and then
    # to fall: `CLOAD` needed a tape mountable through the harness (`run_cases`
    # took `cassette=` only from D-CASORACLE on), and `CSAVE` needed the defect
    # that WAS its subject fixed first (D-CASTAIL2 -- until then a passing row
    # would have certified a tape no real MSX could load).
    # 🌾 D-KWTAPE4: THE NAMED FORM NOW REACHES THE **SECOND** FILE, AND THE OLD
    # ONE PROVED LESS THAN IT LOOKED. With one file on the tape `CLOAD"ZQ"` and a
    # bare `CLOAD` both read the first file and both printed `Found:ZQ` -- two
    # forms, one reading, and a CLOAD that IGNORED ITS NAME ARGUMENT passed both.
    # `ZR` sits second, so this row reads `Skip :ZQ`: the machine's own witness
    # that it PASSED OVER a non-matching file, which only a name can make it do.
    ("cload",   'cload"zr"', 'CLOAD"ZR"',                     "direct",
     "NEEDS-TAPE: " "NOFURN: FORM:load-named \U0001f3af THE MACHINE'S OWN `Skip :ZQ` IS "
     "THE WITNESS, printed as it searches: a hang and a silent no-op look "
     "identical at the `Ok` prompt, which is exactly how D-CASTAIL2 hid for four "
     "slices. A CLOAD that ignored the name would read `Found:ZQ` like the bare "
     "row below. Absent => syntax error."),
    ("cload_b", 'cload',     'CLOAD',                         "direct",
     "NEEDS-TAPE: " "NOFURN: FORM:load-next the BARE form takes the NEXT file, "
     "which from a rewound tape is `ZQ` -- no name is given and none is needed"),
    ("inkey",   'a$=inkey$',
     'POKE&HFBF0,65:POKE&HF3FA,&HF0:POKE&HF3FB,&HFB:POKE&HF3F8,&HF1:'
     'POKE&HF3F9,&HFB:A$=INKEY$:PRINT"[";A$;LEN(A$);"]"',  "stored",
     "FORM:poll-key absent => the buffer stays stuffed and INKEY$ reads nothing; real => [A 1 ]"),
    ("csave",   'csave"zq"',  'PRINT"[Z9]":CSAVE"ZQ"',  "stored",
     "NEEDS-BLANKTAPE: " "NOFURN: " "FORM:save-to-tape 🔴 THE ROW READS THE "
     "TAPE, NOT THE SCREEN, "
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
    # 🔴 D-KWGOTOROW: `GOTO` HAD NO HAPPY-PATH ROW AT ALL -- its only row was the
    # PROVES-T3 error case above. GOTO is the APPARATUS of dozens of rows and the
    # SUBJECT of none, the same hole bare PRINT had: being used is not being
    # measured.
    # ⚠️ THE PADDING IS TWO LONG ASSIGNMENTS, NOT `REM` (which would swallow the
    # rest of its line), and it is there to force the PRINT onto line 40 so the
    # `GOTO 40` has a target. Packing verified with omsx_repl.as_stored first:
    # 10 `A=0:GOTO 40:A=7` / 20,30 padding / 40 the PRINT.
    ("gotokw",   'goto 40',
     'A=0:GOTO 40:A=7:Z$="XXXXXXXXXXXXXXXXXXXXXXXX":Y$="YYYYYYYYYYYYYYYYYYYYYYYY":PRINT"[1e";A;"]"',
     "stored",
     "NOECHO:[1e FORM:jump the JUMP itself: `A=7` sits AFTER the GOTO on line 10 "
     "and must be skipped, so `[1e 0 ]`. A GOTO that parsed and fell through "
     "reads `[1e 7 ]`."),
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
     "FORM:address-value BREADTH: the LAST byte of an MSX1's 16 KB VRAM, where the "
     "existing row uses address 0 — an off-by-one in the address path shows here "
     "and nowhere else. ⚠️ SAME FORM AS `vpoke`, DELIBERATELY: `VPOKE a,v` has one "
     "behaviour and this is a second SAMPLE of it, not a second form."),
    ("vpoke_b2", 'vpoke 100,255', 'VPOKE 100,255:PRINT"[";VPEEK(100);"]"', "stored",
     "FORM:address-value BREADTH: the maximum byte VALUE, where the existing row "
     "writes 9. ⚠️ STORED "
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
     "FORM:channel reopened; a `reopen succeeds` row would have passed without the close."),
    # D-KWCLOSEBARE: bare `CLOSE` closes EVERY channel, which the `#n` form cannot
    # exercise. The row opens TWO channels and closes them with one bare CLOSE,
    # then reads a length back through a reopen -- so a CLOSE that shut only the
    # first leaves #2 open and the second OPEN fails.
    ("close_b",  'close',
     'OPEN"W4.TXT"FOR OUTPUT AS#1:PRINT#1,"AB":CLOSE:OPEN"W4.TXT"FOR INPUT AS#1:A=LOF(1):CLOSE#1:PRINT"[";A;"]"',
     "stored",
     "NEEDS-DISK: " "FORM:all bare CLOSE closes a channel it was NOT TOLD ABOUT, "
     "which is the behaviour `CLOSE #n` cannot exercise: the reopen only succeeds "
     "if the write was flushed and the channel freed, and the length proves the "
     "bytes reached the medium.\n"
     "     \U0001f534 TWO EARLIER CUTS OF THIS ROW MEASURED THE APPARATUS INSTEAD. "
     "With two channels it read `Bad file number in 20` -- the default MAXFILES "
     "is ONE. With `MAXFILES=2` prepended it went DIVERGENT: zerobas read `[ 5 ]` "
     "and the reference read a scrolled, empty screen, because MAXFILES performs "
     "an implicit CLEAR and the row was then measuring five things at once. ONE "
     "CHANNEL PROVES THE SAME POINT with none of that."),
    ("bsave",   'bsave"x",0,1',
     'POKE&HC800,99:BSAVE"O.BIN",&HC800,&HC800:POKE&HC800,7:BLOAD"O.BIN":A=PEEK(&HC800):PRINT"[";A;"]"', "stored",
     "NEEDS-DISK: " "a ROUND TRIP through the disk: save 99, overwrite the cell with "
     "FORM:range 7, load it back, read 99. A BSAVE that wrote nothing leaves 7."),
    ("save",    'save"x"',
     'A=1:SAVE"S.BAS":OPEN"S.BAS"FOR INPUT AS#1:A=LOF(1):CLOSE#1:PRINT"[";A;"]"', "stored",
     "NEEDS-DISK: " "FORM:tokenised the saved program's own length, read back through a channel: 68 "
     "on BOTH machines, which also says the tokenised on-disk form agrees byte for "
     "FORM:tokenised byte. A SAVE that wrote nothing leaves no file and the OPEN raises."),
    # 🔭 D-KWSAVEA: `SAVE ...,A` (ASCII) ALSO NEEDS AN ISOLATED PROBE. The row
    # read `[ 49 ]` on zerobas -- the first byte of the listing, exactly as
    # designed -- and NOTHING on the reference, which is a divergence about the
    # APPARATUS as easily as about SAVE: writing then reopening a file inside one
    # sweep row is the shape `openkw_b` needed six sweeps to get right. SAVE stays
    # at 1/2 until that is measured on its own.
    # 🔴 D-KWSAVE: `SAVE"x",A` ENDS THE RUN ON THE REFERENCE AND CONTINUES HERE,
    # AND THIS ROW IS PINNED DIVERGENT TO SAY SO. Both machines print `[2s]`; only
    # zerobas goes on to print `[2u]`.
    # 🔬 MEASURED WITH A CONTROL (scratchpad/saveascii_probe.py, four cases on the
    # CF-3300): the TOKENISED save continues normally (`< 72 >`, the control), and
    # after an ASCII one NEITHER a readback NOR a bare `PRINT` NOR a `FILES` is
    # reached. The mechanism is not a mystery: `ascii_save` drives the LIST walk,
    # and `LIST` inside a program ENDS THE RUN -- measured on BOTH machines, so
    # zerobas already gets LIST right and only ascii_save fails to inherit it
    # (`ex_list` finishes `jp end_line_end`; `ascii_save` finishes
    # `jp disk_write_end`).
    # 💰 NOT FIXED TONIGHT, AND THE NUMBER IS WHY: `basic/save.asm` is in the MAIN
    # image and `make basic-reloc` from a clean tree on 2026-09-15 reads **8 B free
    # in page 1** with the low region at 0. Turning that tail into
    # `call disk_write_end / jp end_line_end` is +3 B -- affordable, and more than
    # a third of what is left, which is exactly the kind of spend that gets
    # REPORTED rather than taken quietly.
    # ⛔ AND THERE IS NO ROW AT ALL, WHICH IS THE THIRD THING THIS COST TO LEARN.
    # The first cut read the file back and scored `ref [value] ''` -- an EMPTY
    # capture, one of the silent-failure modes and not a verdict. The second was a
    # two-PRINT shape that read cleanly on both sides -- and POISONED THE REST OF
    # ITS BATCH: `namekw` and `open_c`, both SUPPORTED minutes earlier, came back
    # with BLANK REFERENCE SCREENS, echo and all, because a run that ends mid-line
    # leaves the reference somewhere the next case cannot be typed into. A row that
    # can only be right by making its neighbours wrong does not belong in a batched
    # sweep; the measurement lives in the probe, which has a control and a machine
    # to itself.
    ("kill",    'kill"x"',
     'A=DSKF(1):KILL"PROG2.BAS":B=DSKF(1):PRINT"[";B-A;"]"', "stored",
     "NEEDS-DISK: " "the FREED SPACE is the behaviour — 1 KB back after the file "
     "goes, so a KILL that merely parsed reads 0. The victim is PROG2.BAS, which no "
     "FORM:delete-file other row in this sweep opens."),
    ("merge",   'merge"x"',
     'OPEN"N.BAS"FOR OUTPUT AS#1:PRINT#1,"100 END":CLOSE:PRINT"[M0]":MERGE"N.BAS":PRINT"[M1]"', "stored",
     "NEEDS-DISK: " "FORM:merge-file MERGE RETURNS TO COMMAND LEVEL, so the row reads `[M0]` and "
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
     "FORM:left-justify from each other and not merely from a stub."),
    ("rset",    'rset a$="x"',
     'OPEN"R.DAT"AS#1:FIELD#1,4 AS A$:RSET A$="B":A=ASC(A$):CLOSE#1:PRINT"[";A;"]"', "stored",
     "NEEDS-DISK: " "RIGHT justification: byte 1 is a SPACE (32), not the \"B\" that "
     "FORM:right-justify `lset` puts there."),
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
     "NEEDS-DISK: " "SUBJECT:INPUT_# FORM:string-read the FILE form: 24 = the "
     "fixture line's length, 0 without it"),
    ("input_b",  "input#1,a$",
     'OPEN"HI.TXT"FOR INPUT AS#1:INPUT#1,A$:CLOSE#1:PRINT"[";LEFT$(A$,5);"]"',
     "stored",
     "NEEDS-DISK: " "SUBJECT:INPUT_# FORM:string-read the BYTES, not the COUNT. "
     "`inputkw` scores LEN(A$)=24, which "
     "a read returning 24 BLANKS passes just as well as the real line; HI.TXT is "
     "\"Hello from zerobas-disk!\" (tools/make_test_dsk.py), so this reads Hello."),
    # ⌨️ D-KWRESPOND: THE CONTROL ROW, AND IT COMES FIRST ON PURPOSE. Apparatus
    # inside a measurement is where this session kept getting bitten, so before any
    # row DEPENDS on the response channel, one row proves the channel itself
    # delivers: `INKEY$` reads a single character straight out of the keyboard
    # buffer, so if the trailing line never arrives this reads the empty string and
    # the row says so instead of a later row failing for a reason nobody can see.
    # 🔴 AND THE FIRST CONTROL ROW WAS THE WRONG SHAPE, WHICH IS WHY IT RAN FIRST.
    # Written with `INKEY$` it read `[0y]` on the reference and `[0y]|ZBZ|Syntax
    # error` on zerobas: INKEY$ DOES NOT BLOCK, so the program finished before the
    # trailing line was typed and BASIC then tried to EXECUTE the response as a
    # command. The channel works only while a read is WAITING -- which is the whole
    # mechanism `basic_probe_input` relies on and the thing this row exists to pin.
    # 🎯 `INPUT$(1)` BLOCKS FOR EXACTLY ONE CHARACTER, so it holds the program open
    # until the response arrives. `INPUT$` is not in the keyword table, so this row
    # scores for NOBODY -- which is what a control row should do.
    # 🔴 AND ON ITS FIRST USE THE CHANNEL FOUND A MISSING FORM. `inputdol` above is
    # CRUNCH-ONLY -- exec `None`, note "BLOCKS waiting for a keypress" -- because
    # nothing could type a response, so `INPUT$(n)` had never been executed at all.
    # Executed, the reference reads `[0yZ]` and zerobas answers `Syntax error`:
    # `str_inputd` (basic/strvar.asm:415) requires `,#f` -- "file form requires
    # '#f'" -- and falls to `str_eval_no` without it, so the CONSOLE form of
    # `INPUT$` is not implemented here.
    # 🎯 THIS ROW DOUBLES AS THE CHANNEL'S CONTROL ON THE REFERENCE SIDE: `INPUT$`
    # is not `INPUT`, so `[0yZ]` proves the trailing line reaches a blocked read
    # INDEPENDENTLY of the statement the console-INPUT rows below are measuring.
    ("inputdol_b", 'a$=input$(1)',
     'A$=INPUT$(1):PRINT"[0y";A$;"]"',                 "stored",
     "NOECHO:[0y RESPOND:Z SUBJECT:INPUT$ FORM:console the CONSOLE form of "
     "`INPUT$`, measurable for the first time once a response could be typed. "
     "✅ SHIPPED 2026-09-16 (D-INPDCON): it was the LAST MISSING keyword in this "
     "sweep -- `str_inputd` required `,#f` and fell to str_eval_no without it, so "
     "`A$=INPUT$(1)` answered Syntax error where both references read a key. Both "
     "sides now read `[0yZ]`. One Z, from the PRINT: an ECHOING INPUT$ would put a "
     "second before the `[`, which is how `no echo` is a reading here and not an "
     "assumption."),
    # 🎯 THE CHANNEL FORM, WHICH HAD NO ROW OF ITS OWN. `INPUT$(n,#f)` was
    # exercised only INSIDE printhash below, where it is the INSTRUMENT that reads
    # PRINT #'s bytes back -- so it scored `PRINT_#` and INPUT$ got nothing for it.
    # A form measured only as another verb's instrument is a form with no row.
    ("inputdol_c", 'a$=input$(3,#1)',
     'OPEN"IDL.TXT"FOR OUTPUT AS#1:PRINT#1,"ABC":CLOSE#1:OPEN"IDL.TXT"FOR INPUT AS#1:A$=INPUT$(3,#1):CLOSE#1:PRINT"[";A$;"]"',
     "stored",
     "NEEDS-DISK: " "SUBJECT:INPUT$ FORM:channel the CHANNEL form -- n bytes out "
     "of an open file rather than off the keyboard. Written and read back in one "
     "program so the row cannot pass on a file some earlier case left behind: "
     "`[ABC]`."),
    # ⌨️ D-KWRESPOND: bare CONSOLE INPUT, which has NEVER had a row -- both of
    # INPUT's rows drive the FILE form and now belong to `INPUT #`.
    ("inputcon", 'input a$',
     'INPUT A$:PRINT"[0z";A$;"]"',                     "stored",
     "NOECHO:[0z RESPOND:HELLO SUBJECT:INPUT FORM:no-prompt the CONSOLE form, "
     "reading a string typed at the keyboard rather than out of a channel. "
     "`[0zHELLO]`."),
    ("inputcon_b", 'input "n";a',
     'INPUT "N";A:PRINT"[1a";A;"]"',                   "stored",
     "NOECHO:[1a RESPOND:42 SUBJECT:INPUT FORM:prompt the PROMPT form -- the "
     "literal is printed before the read, which the promptless form cannot "
     "exercise. `[1a 42 ]`."),
    ("inputcon_c", 'input a,b',
     'INPUT A,B:PRINT"[1b";A;B;"]"',                   "stored",
     "NOECHO:[1b RESPOND:3,4 SUBJECT:INPUT FORM:multi-variable ONE typed line "
     "split on the comma into TWO variables. `[1b 3  4 ]` -- a handler that read "
     "the whole line into the first leaves B at 0."),
    # ⌨️ D-KWRESPOND: `LINE INPUT` is a COMPOSITE and its whole point is that it
    # does NOT split: commas and leading spaces are kept.
    ("lineinput", 'line input a$',
     'LINE INPUT A$:PRINT"[1c";A$;"]"',                "stored",
     "NOECHO:[1c RESPOND:_A,B_C SUBJECT:LINE_INPUT FORM:whole-line the WHOLE line "
     "including its commas AND its leading space, where `INPUT` would have split "
     "at the comma and eaten the space. `[1c A,B C]`."),
    ("lineinput_b", 'line input "q";a$',
     'LINE INPUT "Q";A$:PRINT"[1d";A$;"]"',            "stored",
     "NOECHO:[1d RESPOND:_X,Y SUBJECT:LINE_INPUT FORM:prompt the PROMPT form, "
     "which prints the literal before the read. `[1d X,Y]` -- and the leading "
     "space is still kept, so the prompt did not eat it."),

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
     "NEEDS-DISK: " "SUBJECT:GET_# FORM:fielded-record a PUT/GET round trip "
     "through a FIELDed record: 90 then 66, "
     "where a GET that did nothing reads 90 then 90."),
    # D-KWSTMTDEN: `PUT #` IS ITS OWN STATEMENT AND `getkw` CANNOT SPEAK FOR IT.
    # That row does a PUT/GET round trip on record 1 only, so a PUT # that ignored
    # the record number entirely would pass it. This writes TWO records with
    # DIFFERENT values and reads BOTH back, so the record number is part of the
    # reading and not an assumption.
    ("puthash", 'put#1,2',
     'OPEN"Q.DAT"AS#1:FIELD#1,4 AS A$:LSET A$="K":PUT#1,1:LSET A$="Z":PUT#1,2:GET#1,1:A=ASC(A$):GET#1,2:B=ASC(A$):CLOSE#1:PRINT"[";A;B;"]"',
     "stored",
     "NEEDS-DISK: " "SUBJECT:PUT_# FORM:fielded-record `[ 75  90 ]` -- K in record "
     "1 and Z in record 2, each read back from the record it was written to. A "
     "PUT # that ignored the record number writes both to the same place and both "
     "readings become Z."),
    # D-KWSTMTDEN: `PRINT #` likewise -- Joost ruled bare PRINT, PRINT # and
    # PRINT USING three different functions, and only the last two had any row.
    ("printhash", 'print#1,"abc"',
     'OPEN"P.TXT"FOR OUTPUT AS#1:PRINT#1,"ABC":CLOSE#1:OPEN"P.TXT"FOR INPUT AS#1:A$=INPUT$(3,#1):CLOSE#1:PRINT"[";A$;"]"',
     "stored",
     "NEEDS-DISK: " "SUBJECT:PRINT_# FORM:channel-write the BYTES that reached the "
     "channel, read back through a second OPEN -- `[ABC]`. A PRINT # that wrote "
     "nothing leaves an empty file and the read fails instead."),
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
    # 🔴 D-AKCM (2026-09-17): SO DOES THIS ONE, AND IT IS WHY `CALL` IS NOW A
    # REFUSE-ON-SIGHT WORD. `CALL FOO`, the `_FOO` shorthand and a bare `CALL` are
    # ERR 2 on both references -- `CALL <name>` dispatches to an EXTENSION ROM and
    # a bare MSX1 has none. The word has no happy path on this machine.
    ("callkw",   "call zzq",  'CALL=1:PRINT"[C1]"',   "stored",
     "D-KWGET: reservedness only — Syntax error on all three machines where the "
     "stub shape assigns and prints. 🔴 DELIBERATELY CARRIES NO `FORM:` TAG: this "
     "row is about the word being RESERVED, and reservedness is on this tree's "
     "do-not-award list. `CALL`'s one form is the row below."),
    # 🎚️ D-TIER1REF (Joost, 2026-09-17): *"works correctly in the happy path,
    # unless there is no happy path in which case it works correctly in the normal
    # failing path"*. `CALL <name>` dispatches to an EXTENSION ROM and a bare MSX1
    # has none, so the refusal IS the normal path -- and the bar is that the error
    # MATCHES. It is ERR 2 here, not the ERR 5 the other four refuse-on-sight
    # words give, which is exactly why the bar cannot be written as "raises 5".
    # Measured on three spellings (`CALL FOO`, the `_FOO` shorthand, bare `CALL`),
    # all ERR 2 on both machines (scratchpad/akcm_probe.py); the shorthand is the
    # same behaviour by another spelling, so it is not a second form.
    ("callkw_b", "call foo",  'CALL FOO:PRINT"[C2]"',  "stored",
     "FORM:refuse `CALL FOO` is Syntax error on both references and here -- no "
     "extension ROM to dispatch to. The `PRINT` never runs, which is what "
     "separates a refusal from a CALL that silently did nothing"),

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
     "stored", "FORM:line D-KWDISK"),
    # 🌾 D-KWRUNBARE: the BARE form RESTARTS, and seeing that needs state that
    # SURVIVES a RUN. Variables do not -- RUN clears them, which is half of what
    # the statement IS -- but VRAM does, and `VPEEK(4096)` reads **0 on BOTH
    # machines at boot** (measured; 4096 is outside every table SCREEN 0 uses, and
    # 8192 reads 244 on both, so this is a real zero and not an unset read).
    # Pass 1 finds 0, writes 99 and RUNs; pass 2 finds 99 and prints.
    # 🎯 A `RUN` THAT DID NOTHING PRINTS NOTHING AT ALL -- the program would fall
    # off the end of line 30 on its first and only pass -- so the marker is the
    # RESTART itself and not merely that the word parsed.
    ("runkw_b", "run",
     'A=VPEEK(4096):IF A=99 THEN PRINT"[2x]":END:VPOKE 4096,99:RUN',
     "stored", "FORM:bare the RESTART: only a second pass can see the 99 the "
     "first one wrote"),

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
     "FORM:read-sector the same read WITHOUT the DSKI$ gives 254, so the row moves."),
    ("dsko",    "dsko$0,0",
     'A$=DSKI$(0,7):B=PEEK(&HF351)+256*PEEK(&HF352):POKE B,88:DSKO$0,7:A$=DSKI$(0,0):A$=DSKI$(0,7):A=PEEK(B):PRINT"[";A;"]"', "stored",
     "NEEDS-DISK: " "raw sector WRITE, and it is a ROUND TRIP: poke the buffer to "
     "\"X\", write sector 7, read a DIFFERENT sector to flush the buffer, read 7 "
     "back. 88 only if the bytes reached the disk. DESTRUCTIVE to the root "
     "FORM:write-sector directory, which is why it is the LAST reading row in this block."),
    ("copy",    'copy"a:x"to"a:y"',
     'COPY"HI.TXT" TO "H2.TXT":OPEN"H2.TXT"FOR INPUT AS#1:A=LOF(1):CLOSE#1:PRINT"[";A;"]"', "stored",
     "NEEDS-DISK: " "the COPY's own length read back through a channel: 26, HI.TXT's "
     "FORM:file-to-file size. A COPY that created an empty file reads 0."),
    ("set",     'set password',  "SET PASSWORD", "stored",
     "NEEDS-DISK: " "FORM:refuse ERR 5 on every machine with a disk ROM and on the diskless "
     "VG-8020 too (D-DONOTHING3) — the handler refuses ON SIGHT. That IS the "
     "differential: an absent SET parses `SET PASSWORD` as a variable and a name, "
     "which is a Syntax error, not an Illegal function call."),
    ("attr",    'a$=attr$(0)',   None, "direct", "NEEDS-DISK: " "MSX-DOS2-era; measured for the record"),
    ("ipl",     "ipl",           "IPL", "stored",
     "NEEDS-DISK: " "FORM:refuse MEASURED, not assumed to be destructive: `IPL` is Illegal "
     "function call on the CF-3300 as well as on zerobas — the boot-sector write "
     "the old note feared needs MSX-DOS2, and this machine refuses the word on "
     "sight. Same Syntax-error differential as `set`."),
    ("cmd",     'cmd"x"',        'CMD"X"',      "stored",
     "NEEDS-DISK: " "FORM:refuse the third refuse-on-sight word; ERR 5 on both references."),
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
     "NEEDS-DISK: " "NEEDS-PRINTER: " "FORM:catalogue-to-printer the printer head goes back to column 0 "
     "because every entry ended its own line -- 0 on both machines since D-DFEND, "
     "2 before it. A no-match LFILES must NOT zero it (both machines leave the "
     "head parked and let R-LP16 flush), which is why the store is conditional."),
    ("loc",     "a=loc(1)",
     'OPEN"HI.TXT"FOR INPUT AS#1:A$=INPUT$(10,#1):A=LOC(1):CLOSE#1:PRINT"[";A;"]"', "stored",
     "NEEDS-DISK: " "26 on BOTH machines — LOC answers in BYTES here, and it "
     "answers the same after 10 bytes as after none, so the row scores the "
     "FORM:position FUNCTION and not a position. An absent LOC auto-dims an array and reads 0."),
    # 🌾 D-KWBREADTH batch 16 — AXIS (f): `OPEN` had NO ROW AS SUBJECT. It carries
    # `inputkw`, `lof`, `save` and the row above as APPARATUS, so kwcover counted it
    # EXERCISED, the tier table credited the OTHER keyword, and the knife could not
    # reach it at all. Every existing use is `FOR INPUT`; this drives the untested
    # `FOR OUTPUT` form and reads the file back.
    # 🔴 PLACEMENT IS THE HARD PART, NOT THE ROW. This CREATES a file, and the
    # D-KWDISK rule is that every row which READS the fixture sits ahead of every
    # row that CHANGES it. `files` and `lfiles` LIST the directory and `dskf` reads
    # FREE SPACE, so a new file would move all three -- which is why this sits after
    # `loc`, the LAST disk row, and not beside the other writers
    # [[apparatus-is-part-of-the-measurement]].
    ("openkw",  'open"o.txt"for output as#1',
     'OPEN"O.TXT"FOR OUTPUT AS#1:PRINT#1,"AB":CLOSE#1:OPEN"O.TXT"FOR INPUT AS#1:A=LOF(1):CLOSE#1:PRINT"[";A;"]"',
     "stored",
     "NEEDS-DISK: " "FORM:output the FOR OUTPUT form, which every other use of OPEN in this "
     "file lacks: create, write \"AB\", close, reopen FOR INPUT and read LOF. "
     "🔴 THE READING IS 5, NOT THE 4 THIS NOTE FIRST CLAIMED -- \"AB\" plus CRLF "
     "is four bytes and the file measures five on BOTH machines. The fifth is "
     "consistent with the $1A EOF marker Disk BASIC appends on CLOSE, but that "
     "byte has NOT been read back, so it is named as the likely cause and not as "
     "a measured fact. What IS measured is 5, and an OPEN that created nothing "
     "cannot be reopened at all."),
    # 🌾 D-KWBREADTH batch 17 — AXIS (f), THE LAST OF THE FOUR: `FIELD` had no row
    # as subject either. RANDOM-access disk: `OPEN ... AS#1` with NO `FOR` clause,
    # `FIELD` binds a buffer slice to a string variable, `LSET` fills it, `PUT`
    # writes the record and `GET` reads it back. Placed here, after `loc` and
    # `openkw`, because it CREATES a file and `files`/`lfiles`/`dskf` must read the
    # fixture first.
    # 🌾 D-KWOSK: `OPEN`'s other two modes. `openkw` opens FOR OUTPUT and `openkw_b`
    # FOR INPUT; APPEND and the FOR-less RANDOM mode had no row of their own --
    # the random-access rows above USE it, but their subject is FIELD / GET # /
    # PUT #. Both of these WRITE, so they sit with the writers: a reader placed
    # after them reads a fixture that has moved.
    # 🌾 D-KWMOTOR: `NAME` had no row at all. One behaviour -- rename -- and the
    # reading is that the NEW name carries the OLD file's bytes: create NM.TXT with
    # `AB`, rename it, reopen under the new name and read LOF. A NAME that parsed
    # and did nothing leaves NM2.TXT absent and the reopen raises File not found.
    ("namekw",  'name"nm.txt" as "nm2.txt"',
     'OPEN"NM.TXT"FOR OUTPUT AS#1:PRINT#1,"AB":CLOSE#1:NAME"NM.TXT" AS "NM2.TXT":OPEN"NM2.TXT"FOR INPUT AS#1:A=LOF(1):CLOSE#1:PRINT"[2p";A;"]"',
     "stored",
     "NEEDS-DISK: " "FORM:rename 5 bytes under the NEW name: `AB`+CRLF plus the "
     "sequential end marker, the same count `open_c` measures"),
    ("open_c",  'open"oa.txt"for append as#1',
     'OPEN"OA.TXT"FOR OUTPUT AS#1:PRINT#1,"AB":CLOSE#1:OPEN"OA.TXT"FOR APPEND AS#1:A=LOF(1):PRINT#1,"CD":CLOSE#1:PRINT"[2f";A;"]"',
     "stored",
     "NEEDS-DISK: " "SUBJECT:OPEN FORM:append 5: `LOF` on the APPEND channel sees "
     "the `AB`+CRLF+$1A that is ALREADY there. An APPEND that TRUNCATED -- which is "
     "exactly what FOR OUTPUT does to an existing file -- reads 0. "
     "\U0001f534 TWO OPENS, NOT THREE, AND THAT IS NOT TIDINESS: the three-open cut read "
     "9 correctly on its own and came back with a BLANK REFERENCE SCREEN inside the "
     "full disk batch. A case slower than the batch's `step` has its SUCCESSOR "
     "typed into a still-running program, and the CF-3300 is slow enough on three "
     "open/close cycles to cross it."),
    ("open_d",  'open"or.dat"as#1',
     'OPEN"OR.DAT"AS#1:FIELD#1,4 AS A$:LSET A$="PQRS":PUT#1,1:GET#1,1:PRINT"[2e";A$;"]":CLOSE#1',
     "stored",
     "NEEDS-DISK: " "SUBJECT:OPEN FORM:random the FOR-LESS form, which is RANDOM "
     "access and not a defaulted INPUT: `PUT`/`GET` are legal on it and a "
     "sequential channel refuses them"),
    ("fieldkw", 'field#1,4 as a$',
     'OPEN"F.DAT"AS#1:FIELD#1,4 AS A$:LSET A$="WXYZ":PUT#1,1:GET#1,1:PRINT"[";A$;"]":CLOSE#1',
     "stored",
     "NEEDS-DISK: " "FORM:bind-buffer the random-access round trip -- FIELD binds, LSET fills, PUT "
     "writes record 1 and GET reads it back: [WXYZ], MEASURED on both machines "
     "before this sentence was written. A FIELD that bound nothing leaves A$ "
     "empty, and the four verbs are load-bearing TOGETHER -- the reading fails if "
     "any one of them does."),
    # 🔴 D-KWSAVE: LAST OF THE DISK ROWS, AND IT WAS NOT AT FIRST. Placed up
    # beside `bsave` it sat UPSTREAM of every reader, and `open_c` -- green on
    # its own and green in the batch before this row existed -- came back with a
    # BLANK REFERENCE SCREEN, echo and all. A writer goes LAST; that is the
    # ordering rule `openkw_b`'s note already carries, and this is the second
    # time it has been paid for.
    # 🌾 THE OPTIONAL ENTRY ADDRESS, read straight out of the file
    # HEADER rather than by running anything. A BSAVE image is
    # `$FE,start:2,end:2,entry:2` little-endian, so byte 7 is the entry's HIGH
    # byte. 🔴 THE ENTRY IS &HC900 AND THE RANGE IS &HC800, AND THAT GAP IS THE
    # WHOLE ROW: the three-argument form writes an entry too -- it DEFAULTS to the
    # start -- so an entry equal to &HC800 would read 200 either way and separate
    # nothing. 201 is reachable only by honouring the fourth argument.
    ("bsave_b", 'bsave"x",0,1,2',
     'POKE&HC800,99:BSAVE"O2.BIN",&HC800,&HC800,&HC900:OPEN"O2.BIN"FOR INPUT AS#1:B$=INPUT$(7,#1):CLOSE#1:PRINT"[2t";ASC(MID$(B$,7,1));"]"',
     "stored",
     "NEEDS-DISK: " "FORM:with-entry 201 = $C9, the ENTRY's high byte in the file "
     "header, where the three-argument form defaults it to the start and reads 200"),
    # 🌾 D-KWBLOADR: `BLOAD"x",R` LOADS **AND EXECUTES**, and the only way to see
    # the difference from a plain load is to make the loaded bytes DO something.
    # Six bytes of Z80 are POKEd, BSAVEd with `&HC800` as the entry, and the
    # landmark cell is cleared before the load: `3E 2A` = LD A,42, `32 06 C8` =
    # LD (&HC806),A, `C9` = RET -- so a plain `BLOAD` reads 0 and only the `,R`
    # form reads 42. The RET is what brings control back to BASIC.
    # ⚠️ LAST of the disk rows, beside `bsave_b`, because it WRITES: a writer
    # upstream of a reader blanked `open_c`'s reference screen once already.
    ("bload_b", 'bload"x",r',
     'POKE&HC800,&H3E:POKE&HC801,42:POKE&HC802,&H32:POKE&HC803,6:POKE&HC804,&HC8:POKE&HC805,&HC9:BSAVE"R.BIN",&HC800,&HC805,&HC800:POKE&HC806,0:BLOAD"R.BIN",R:A=PEEK(&HC806):PRINT"[2v";A;"]"',
     "stored",
     "NEEDS-DISK: " "FORM:run 42: the loaded bytes RAN. A plain BLOAD loads the "
     "same six bytes and reads 0, because nothing calls them"),
    # 🌾 D-KWBLOADR: and `,S` loads into **VRAM** instead of RAM. The file's own
    # header addresses are used as VRAM addresses, and &HC800 = 51200 wraps into a
    # 16 KB VRAM at 2048 -- which in SCREEN 0 is the start of the PATTERN
    # GENERATOR table, ordinary writable VRAM that nothing on screen is using.
    # The cell is cleared with VPOKE before the load, so 77 can only come from the
    # file.
    ("bload_c", 'bload"x",s',
     'POKE&HC800,77:BSAVE"V.BIN",&HC800,&HC800:VPOKE 2048,0:BLOAD"V.BIN",S:A=VPEEK(2048):PRINT"[2w";A;"]"',
     "stored",
     "NEEDS-DISK: " "FORM:vram 77 read back with VPEEK, not PEEK: the `,S` form "
     "puts the bytes in VIDEO memory, where a plain BLOAD would leave VRAM at 0"),
    # 🔴 D-KWSAVEEND: **THE LAST DISK ROW, AND THAT PLACEMENT IS THE ROW.** An
    # ASCII save ENDS THE RUN -- that is the whole form -- so the program stops
    # MID-LINE, and a case that ends mid-line leaves the machine somewhere the
    # NEXT case cannot be typed into. An earlier cut of this row read cleanly on
    # both sides and blanked `namekw` and `open_c` behind it. At the end of the
    # group there is no successor to poison.
    # 🎯 `[2s]` ALONE IS THE READING: both machines print it and NEITHER reaches
    # the `[2u]` after the SAVE. Before the fix this tree printed both.
    ("save_b",  'save"x",a',
     'PRINT"[2s]":SAVE"SA.BAS",A:PRINT"[2u]"',                "stored",
     "NEEDS-DISK: " "FORM:ascii the ASCII save ENDS THE RUN, so the statement after "
     "it is never reached -- the same shape `LIST` inside a program has, and the "
     "reason is the same: this path drives the LIST walk"),
    # 🌾 D-KWRUNFILE: the two rows the FIXTURE was blocking, not the machine.
    # `RUN"<file>"` and `LOAD"<f>",R` REPLACE the running program, so the row that
    # typed them has nothing left to print with -- the only witness is output from
    # the LOADED program, and `PROG.BAS`/`PROG2.BAS` both only POKE. `PROG3.BAS`
    # is `10 PRINT"[3h]"` (Joost ruled 2026-09-15: add a second `.BAS`, leave
    # `PROG.BAS` alone), appended LAST in the image so no earlier file moves.
    # ⚠️ BOTH ROWS END THE TYPED PROGRAM, so they sit at the very END of the disk
    # group beside `save_b` for the same reason it does: a case that leaves
    # nothing of itself running must have no successor to poison.
    ("runkw_c", 'run"prog3.bas"',
     'RUN"PROG3.BAS"',                                        "stored",
     "NEEDS-DISK: " "FORM:file `[3h]` comes from the LOADED program, which is the "
     "only thing that can speak once ours has been replaced"),
    ("loadkw",  'load"prog3.bas",r',
     'LOAD"PROG3.BAS",R',                                     "stored",
     "NEEDS-DISK: " "FORM:run the same witness through `LOAD`'s own execute "
     "option -- the loaded program speaks for itself"),
    # 🟢 D-LOADPLAIN (2026-09-23): THE PLAIN FORM, AND THE NOTE THAT SAID IT
    # COULD NOT HAVE ONE WAS STALE. This row's own predecessor read "the PLAIN
    # `LOAD` has NO row and cannot get one with this instrument: it replaces the
    # program and runs nothing, so the reading would be an ABSENCE both machines
    # produce". True when written, and answered four months later by machinery
    # this file already carries: `NEEDS-LOG:` + `RESPOND:LLIST` (D-KWLOG) puts a
    # LISTING in a host file, so the program does not have to run to be read.
    # Joost had already ruled the principle -- "just validate the program in ram
    # or llist it" -- and `DELETE`/`RENUM` were built on it; nobody came back to
    # `LOAD` [[a-justification-parenthesis-is-an-unrun-claim]].
    # 🎯 THE READOUT IS TWO-SIDED ON PURPOSE. `PROGRAM:` plants `10 REM ZQ9`
    # and `PROG3.BAS` is `10 PRINT"[3h]"`, so the log reads ONE or the OTHER: the
    # loaded text proves the load happened AND that it REPLACED, while a `LOAD`
    # that did nothing leaves `ZQ9` behind and is not an absence either side can
    # produce by accident. An empty log is a third, distinguishable outcome.
    # ⚠️ Two rigs, and they compose -- `lfiles` already carries
    # NEEDS-DISK + NEEDS-PRINTER, and `_rig_kwargs` unions them.
    ("load_b",  'load"prog3.bas"',
     'LOAD"PROG3.BAS"',                                       "direct",
     "NEEDS-DISK: " "NEEDS-LOG: PROGRAM:10_REM_ZQ9 RESPOND:LLIST "
     "FORM:plain load WITHOUT `,R` -- the listing afterwards is the witness, "
     "since the loaded program is never run"),
    ("bin",     "a$=bin$(5)",
     'PRINT"[";BIN$(5);"]"',                         "direct",
     "FORM:to-binary absent => syntax error; real => 101"),

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
     "NEEDS-BOOT: " "NOFURN: " "FORM:start the line-entry prompt `100` on both "
     "machines. 🟢 NO LONGER LAST BY PLACEMENT (D-KWAUTO): it still leaves the "
     "machine in line-entry mode, but `NEEDS-BOOT:` gives it a boot of its own, "
     "which is what lets the two rows below exist at all."),
    # 🟢 D-KWAUTO: THE OTHER TWO FORMS, NOW THAT MORE THAN ONE `AUTO` ROW CAN
    # COEXIST. ⚠️ The increment is invisible on the FIRST prompt -- `AUTO 100` and
    # `AUTO 100,5` both open at `100` -- so the step form has to ENTER A LINE and
    # read the SECOND prompt. `RESPOND:` already types lines after the run.
    ("auto_bare", "auto",         "AUTO",         "stored",
     "NEEDS-BOOT: " "NOFURN: " "FORM:bare the default start, prompt `10` -- which "
     "is what separates it from the `start` row's `100`"),
    ("auto_step", "auto 100,5",   "AUTO 100,5",   "stored",
     "NEEDS-BOOT: " "NOFURN: " "RESPOND:REM_Z "
     "FORM:start-increment enter one line at the `100` prompt and the NEXT prompt "
     "is `105`. The first prompt cannot tell this form from `start`; the second "
     "is the only place the increment is observable"),
]

# 🔴 A DUPLICATE ROW KEY IS SILENT AND DESTRUCTIVE, AND NOTHING CHECKED FOR ONE
# UNTIL D-KWBATCH5 (2026-09-14). A second `mki_b` was added beside an existing one
# and the sweep RAN BOTH: they printed as two rows with the same name, and the pin
# is a dict keyed by row, so whichever finished last SILENTLY REPLACED the other's
# verdict. The same shape as `GOSUB:ongosub` overwriting GOSUB's good reading --
# merged by key, with no witness that a merge happened.
# 🎯 It is one line to make impossible, and the cost of not having it was a row
# whose reading belonged to a different row entirely.
_dups = sorted({k for k in (r[0] for r in SWEEP)
                if [r[0] for r in SWEEP].count(k) > 1})
if _dups:
    raise AssertionError(
        "SWEEP has duplicate row key(s): %s -- the pin is keyed by row, so one "
        "verdict would silently replace the other" % " ".join(_dups))


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

    # D-RIGFW: find the board ONCE, and only if a selected row needs it. With no
    # board those rows lose their exec line -- crunch-only, listed with the
    # reason under NOT EXECUTED, and never scored.
    RIG = {"port": None}
    if any(_rigstate_of(_row_rigs(r[4])) for r in rows if r[2] is not None):
        RIG["port"] = rigfw.find()
        print(f"rig: {RIG['port'] or 'NO BOARD -- NEEDS-RIG: rows run crunch-only'}")
        if RIG["port"] is None:
            rows = [(k, c, None, m,
                     "NOT RUN -- NEEDS-RIG: no rigfw board answered `id` on "
                     "/dev/cu.usbmodem* (tools/rigfw). " + n)
                    if _rigstate_of(_row_rigs(n)) else (k, c, ex, m, n)
                    for k, c, ex, m, n in rows]

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
            # 📏 D-BOOTWIDTH (2026-09-24): THE DISK GROUP COMPARES AT ITS ORACLE'S
            # WIDTH. The references boot at DIFFERENT widths -- the VG-8020 at 37,
            # the CF-3300 (the disk rows' oracle) at 39 -- and zerobas now boots
            # at the VG's 37. Measured: `files_b` then compared FILES packed
            # 2-per-line against 3-per-line, the split and not a FILES defect.
            # zerobas's side of the disk group therefore starts at 39, as before
            # today; a per-row `WIDTH 39` could not do it, because the change
            # re-inits the screen on one side only and wipes the anchor echo.
            if "disk" in rig and mach == args.zb_machine:
                pre = pre + (f"WIDTH {DISK_ORACLE_WIDTH}",)
            if pre:
                mkw["reset"] = pre + tuple(kw.get("reset", ()))
            if mount:
                mkw.update(_rig_kwargs(rig))
                # 🔴 PER CASE, NOT PER CALL: `run_cases` takes one (row, mask) or
                # None per case, aligned with `cases`. Every row in this group
                # asked for the SAME key -- the argument is part of the group key
                # -- so the list is that one hold repeated. `mount=False` is the
                # crunch layer, which stores a line and never RUNs it, so there is
                # nothing for a held key to be read by.
                held = _hold_of(rig)
                if held is not None:
                    mkw["holds"] = [held] * len(idx)
                    ht = _holdtime_of(rig)
                    if ht is not None:
                        mkw["hold_lead"], mkw["hold_secs"] = ht
                # ⚠️ `prologue` is a WHOLE-CALL kwarg, so a plug and a printer log
                # would overwrite one another -- no row asks for both, and the
                # group key would separate them anyway.
                plugs = _plug_of(rig)
                if plugs:
                    assert "prologue" not in mkw, (
                        "a NEEDS-PLUG: row cannot also need the printer rig: "
                        "both own `prologue`")
                    mkw["prologue"] = plugs
                rstate = _rigstate_of(rig)
                if rstate is not None:
                    assert "prologue" not in mkw, (
                        "a NEEDS-RIG: row cannot also plug a device or a printer: "
                        "all three own `prologue`")
                    mkw["prologue"] = rigfw.prologue(rstate)
            else:
                rstate = None
            # a rig may force its own delivery mode (see _rig_kwargs: `log` needs
            # boot-per-case or every row reads its predecessors' printer output)
            tape_out = mkw.pop("_tape_path", None)
            if tape_out is not None:
                assert len(idx) == 1, (
                    "a NEEDS-BLANKTAPE: group holds ONE row: the rig re-creates "
                    "one tape per boot, so only the last case's recording survives")
            import contextlib
            pulser = contextlib.nullcontext()
            if rstate is not None:
                rigfw.set_state(RIG["port"], rstate)
                _d, _trigs, _pulse = rigfw.parse_state(rstate)
                if _pulse:
                    pulser = rigfw.Pulser(RIG["port"], _trigs)
            try:
                with pulser:
                    got = omsx_repl.run_cases(mach, [specs[i] for i in idx],
                                              batch=mkw.pop("batch", batch), **mkw)
            finally:
                if rstate is not None:
                    rigfw.set_state(RIG["port"], "centre")
            if tape_out is not None:
                # 🔴 A MARKER, NOT `screen_printer`'s `7c`: this rig takes the
                # DEFAULT capture, which comes back DECODED, while both halves of a
                # `screen_printer` capture are hex. Appending hex to decoded text
                # made `bytes.fromhex` fail and the row read `?noecho` on both
                # sides -- honest, but only because that guard exists. A NUL cannot
                # appear in a 40x24 screen scrape, so the split is unambiguous.
                got = [(g or "") + TAPE_MARK
                       + _tape_readback(tape_out, subject=mach == args.zb_machine)
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
            for _, _, line, mode, _rnote in ex_rows:
                _resp = row_respond(_rnote)
                _prog = row_program(_rnote)
                if _prog:
                    # D-KWEDIT: an EDITOR row. The program goes in, the exec line
                    # edits it, and a RESPOND: line reads the result back -- with
                    # NO `RUN` anywhere, which is the whole point: these verbs
                    # were closed as unrateable only because they had been
                    # measured from inside a running program.
                    if not _resp:
                        sys.exit("kwsweep: a PROGRAM: row with no RESPOND: types "
                                 "a program and never reads it back -- refusing "
                                 "rather than scoring an unread edit")
                    specs.append(("direct", _prog + [line] + _resp))
                elif _resp:
                    # D-KWRESPOND: numbered lines + RUN + the responses, as a
                    # DIRECT case, because run_cases appends RUN itself in stored
                    # mode and nothing can follow it there.
                    specs.append(("direct",
                                  [f"{10 * (i + 1)} {b}" for i, b in
                                   enumerate(omsx_repl.as_stored(line))]
                                  + ["RUN"] + _resp))
                else:
                    specs.append((mode,
                                  omsx_repl.as_stored(line) if mode == "stored"
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
    # 🔴 D-PINONLY (2026-09-24): an `--only` run writes NO pin. A one-row
    # `make kwsweep ONLY=widthkw` overwrote the full pin and tools/tier_table.py
    # drew SQR/PAINT/MOTOR as GAP from it; the reader now refuses a partial pin
    # too, but the writer must not produce one.
    if args.only:
        print("pin: NOT written -- an --only run measures a subset, and the pin "
              "is the whole sweep")
    elif fp_before == fp_after:
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
                              # which FORM of the keyword this row exercises
                              "form": row_form(notes[key]),
                              # the statement it is about, when derivation is wrong
                              "subject": row_subject(notes[key]),
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
