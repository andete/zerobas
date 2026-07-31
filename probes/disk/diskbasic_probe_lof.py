#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""What does `LOF(#n)` report, for EVERY way a channel can be opened?

TODO.md filed ONE row: `OPEN "ZQ.DAT" FOR OUTPUT AS #1 : PRINT LOF(1)` reads 0 on
the CF-3300 and -1 on zerobas. That row alone cannot say WHY, and it walks only
one of the five paths that make a channel's size field live. This battery exists
to answer three questions the filed row cannot:

  1. IS THE -1 A STALE VALUE?  `stale_prev`/`stale_big` open a KNOWN-SIZE file
     first, close it, then create a new one. If the diagnosis "the size field is
     never initialised on the create path" is right, zerobas must print the
     PREVIOUS file's size (26 / 2048), not -1. If it prints -1 there too, the
     diagnosis is WRONG and something actively stores $FFFF. This is the row that
     can refute the fix before it is written.

  2. WHICH RULE DOES THE REFERENCE FOLLOW?  "0 on a new OUTPUT channel" is
     reproduced equally well by "the size field is zeroed at OPEN" and by "LOF
     reads the directory entry, which is 0 for a just-created file". They are
     SEPARATED by a SECOND INSTRUMENT: every case's /tmp disk image is parsed
     after the run and the on-disk directory size is reported beside the LOF
     reading (`dir` column). `exist_out` opens an EXISTING 26-byte file FOR
     OUTPUT and asks both -- if LOF says 0 while the directory still says 26, LOF
     is NOT reading the directory.
     ⚠️ That column was measured, printed and NEVER COMPARED until D-APPMISS
     (2026-07-31): the verdict came from the LOF value alone, so a row could only
     ever go red on one of the two instruments. Both are in the verdict now, each
     with its own oracle lock (REF_EXPECT / DIR_EXPECT) and its own filed-
     divergence list (KNOWN_DIVERGE / DIR_DIVERGE).

  3. WHAT IS THE DENOMINATOR?  A channel's size field is made live by five
     paths, not one: INPUT (fat_io_open), OUTPUT (fat_io_create), APPEND on an
     existing file, APPEND on a missing file (falls into create), RANDOM on an
     existing file, and RANDOM on a missing file (fat_rand_open's fro_create).
     `append_*`/`rand_*` walk the ones the filed row does not, so the fix is
     aimed at the class rather than at the one row that was noticed.

APPARATUS -- inherited wholesale from diskbasic_probe_chancost.py, for the reason
documented there: `omsx_repl` scrapes the SCREEN 0 name table at $0000/40 columns
and CF-3300 Disk BASIC BOOTS TO SCREEN 1 ($1800/32 columns). This probe measures
`scrmod` out of RAM and picks the name table from it, so it reads both machines.
⚠️ The reference's SCREEN 1 name table is 32 cells wide but Disk BASIC boots it at
`linlen=$1d` = **29 COLUMNS**, indented by a LEFT MARGIN OF 2, so any typed line
over 29 characters wraps mid-echo. That is harmless for the reading itself and it
is why `echo_missing` matches with whitespace removed rather than slicing rows to
any assumed width (memory: read-the-screen-when-a-probe-fails).

CONTROLS -- rows that MUST agree on both machines, so that a red row somewhere
else is attributable to the subject rather than to the harness:
  * `ctl_syntax`  types a misspelled keyword and MUST show `Syntax error`. If it
    comes back clean the harness is not typing and every reading here is worthless.
  * `lof_input`   `OPEN "HI.TXT" FOR INPUT` -> 26 on both (the filed control).
  * `lof_bin`     `OPEN "TEST.BIN" FOR INPUT` -> 2048 on both. A SECOND known
    size, so the control is not a single point that could agree by accident.
  * `lof_closed`  `LOF(1)` with nothing open -> ERR 59 on both.
  * `trap_lof_closed`  the same LOF(1) under an armed `ON ERROR GOTO`, handler
    prints ERR -> 59 on both. GREEN BEFORE D-NOTOPEN AS WELL AS AFTER, which is
    what makes it a control: without it, a red `trap_print_closed` could not tell
    "the fix does not trap" from "this probe cannot read a trap at all". Note the
    handler prints the CODE, so `0` reads as "no error was raised" and the three
    outcomes stay distinguishable.
  * `roundtrip`   write, CLOSE, re-open FOR INPUT -> the real size on both. This
    is the row that catches a "fix" which zeroes the size field and then lets the
    zero reach the directory at CLOSE.

CLEAN-ROOM: black-box only -- typed BASIC in, screen + documented sysvars out,
plus the FAT12 directory of the machine's OWN scratch disk image. No reference
ROM is read or disassembled.

DISK SAFETY: every case runs on a /tmp COPY of the test image; the committed
.dsk is never mounted (OPEN FOR OUTPUT would mutate it).
"""
from __future__ import annotations

import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, _os.path.join(
    _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "lib"))

import argparse
import concurrent.futures as cf
import os
import re
import shutil
import signal
import struct
import subprocess
import tempfile
import time

OMSX = shutil.which("openmsx") or "/Applications/openMSX.app/Contents/MacOS/openmsx"
SRC_DSK = os.path.join(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))), "disk", "test720.dsk")

# side -> (machine, has-date-prompt, boot instant in emulated seconds, prompt).
# ⚠️ The PROMPT is what the echo guard anchors on, and it must be exact: the
# reference echoes a typed line at the start of its own row (after the SCREEN 1
# left margin, which the guard squeezes away), while zerobas prints "ZB" and
# echoes on the same row. Anchoring on it is what makes an INSERTED character
# visible -- a plain substring test passes `ZBPPRINT LOF(1)` because the correct
# text is still in there. If a prompt ever changes, every row fails loudly, which
# is the right direction for a guard to break in.
MACHINES = {
    "ref": ("National_CF-3300", True, 12.0, ""),
    "zb":  (os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK"),
            False, 8.0, "ZB"),
}

# The committed test image's directory, for reference:
#   TEST.BIN 2048 | HI.TXT 26 | PROG.BIN 57 | PROG.BAS 16 | PROG2.BAS 17
# ZQ.DAT does not exist on it -- that is what makes it the "freshly created" name.

# label -> (typed lines, directory name to report in the `dir` column or None).
# ⚠️ <= 6 lines (the 24-row screen scrolls) and <= 32 chars per line (SCREEN 1).
CASES = [
    # --- harness control: if this row comes back clean, nothing below is real.
    ("ctl_syntax",   (["OPEM \"HI.TXT\" FOR INPUT AS #1"], None)),

    # --- the FILED defect, and its "still 0 after a write" half.
    ("new_out",      (['OPEN "ZQ.DAT" FOR OUTPUT AS #1',
                       "PRINT LOF(1)"], "ZQ      DAT")),
    ("new_out_wr",   (['OPEN "ZQ.DAT" FOR OUTPUT AS #1',
                       'PRINT #1,"ABCDE"',
                       "PRINT LOF(1)"], "ZQ      DAT")),

    # --- IS IT STALE? the row that can refute the diagnosis before the fix.
    # Open a KNOWN-SIZE file, close it, then create a new one on the same
    # channel. "never initialised" predicts the PREVIOUS size; a -1 here would
    # mean something actively stores $FFFF and the whole diagnosis is wrong.
    ("stale_prev",   (['OPEN "HI.TXT" FOR INPUT AS #1',
                       "CLOSE",
                       'OPEN "ZQ.DAT" FOR OUTPUT AS #1',
                       "PRINT LOF(1)"], None)),
    # ...and a SECOND, different previous size, so a match cannot be coincidence.
    ("stale_big",    (['OPEN "TEST.BIN" FOR INPUT AS #1',
                       "CLOSE",
                       'OPEN "ZQ.DAT" FOR OUTPUT AS #1',
                       "PRINT LOF(1)"], None)),

    # --- WHICH RULE? an EXISTING 26-byte file opened FOR OUTPUT (truncate).
    # "zeroed at OPEN" -> 0. "LOF reads the directory" -> 26 until the entry is
    # rewritten. The `dir` column reports what the directory ACTUALLY holds at
    # dump time, so the two rules are separated rather than merely consistent.
    ("exist_out",    (['OPEN "HI.TXT" FOR OUTPUT AS #1',
                       "PRINT LOF(1)"], "HI      TXT")),
    ("exist_out_wr", (['OPEN "HI.TXT" FOR OUTPUT AS #1',
                       'PRINT #1,"ABCDE"',
                       "PRINT LOF(1)"], "HI      TXT")),

    # --- the DENOMINATOR: the other paths that make a size field live.
    ("append_new",   (['OPEN "ZQ.DAT" FOR APPEND AS #1',
                       "PRINT LOF(1)"], "ZQ      DAT")),
    # ...and the row that SEPARATES "the channel was never opened" from "the
    # channel WAS opened and LOF is broken". `append_new` cannot: its value is the
    # LAST error on screen, and `File not open` from the trailing `PRINT LOF(1)`
    # is what it reads whatever OPEN did. This row drops LOF entirely and pokes
    # the channel with a DIFFERENT VERB, so its value IS the PRINT# rejection --
    # an error here means the write was refused, attributable to the channel
    # state rather than to LOF. (D-APPMISS F3: RED on the pre-fix build, where
    # OPEN silently created the file and this row raised nothing at all.)
    ("append_new_wr", (['OPEN "ZQ.DAT" FOR APPEND AS #1',
                       'PRINT #1,"X"'], "ZQ      DAT")),
    ("append_exist", (['OPEN "HI.TXT" FOR APPEND AS #1',
                       "PRINT LOF(1)"], "HI      TXT")),
    ("rand_new",     (['OPEN "ZQ.DAT" AS #1',
                       "PRINT LOF(1)"], "ZQ      DAT")),
    ("rand_exist",   (['OPEN "HI.TXT" AS #1',
                       "PRINT LOF(1)"], "HI      TXT")),
    # does a RANDOM write move LOF while the channel is still open?
    ("rand_put",     (['OPEN "ZQ.DAT" AS #1',
                       "FIELD #1,10 AS A$",
                       'LSET A$="X"',
                       "PUT #1,1",
                       "PRINT LOF(1)"], "ZQ      DAT")),

    # --- CONTROLS: must agree on both machines.
    ("lof_input",    (['OPEN "HI.TXT" FOR INPUT AS #1',
                       "PRINT LOF(1)"], "HI      TXT")),
    ("lof_bin",      (['OPEN "TEST.BIN" FOR INPUT AS #1',
                       "PRINT LOF(1)"], "TEST    BIN")),
    ("lof_closed",   (["PRINT LOF(1)"], None)),
    # ATTRIBUTION CONTROL for `append_new_wr` (D-APPMISS). Same PRINT# into an
    # unopened channel, with NO OPEN typed at all -- so whatever it reports is a
    # property of PRINT#-on-a-closed-channel and has nothing to do with APPEND.
    # If this row and `append_new_wr` diverge the SAME way, `append_new_wr`'s
    # divergence is that pre-existing class and not something this slice did;
    # without it, "it was already like that" would be an assertion.
    ("ctl_prwr_closed", (['PRINT #1,"X"'], None)),

    # --- D-NOTOPEN (docs/spec-basic-chan-notopen-err59.md) -------------------
    # The closed-channel DENOMINATOR. `ctl_prwr_closed` above covers PRINT#;
    # INPUT# and LINE INPUT# are named by the same item and had NO ROW AT ALL
    # until this slice -- the fix would have landed with two thirds of its own
    # claim ungated. All three raise ERR 59 on the CF-3300, MEASURED.
    ("closed_input",   (["INPUT #1,A$"], None)),
    ("closed_lineinp", (["LINE INPUT #1,A$"], None)),

    # TRAPPABILITY -- the half that makes this a semantics fix and not a wording
    # fix. zerobas's `load_error` is a ret-based print path: it prints and the
    # program CONTINUES, so an armed ON ERROR GOTO never sees it. The handler
    # prints ERR, so the reading is the CODE -- and `0` means NO ERROR WAS RAISED
    # AT ALL, which is what keeps "trapped", "not trapped" and "nothing happened"
    # three distinguishable values rather than two (appmiss-slice: a sentinel
    # that also means "no reading" is not a measurement).
    ("trap_print_closed", (["10 ON ERROR GOTO 100", '20 PRINT #1,"X"',
                            "100 PRINT ERR", "RUN"], None)),
    ("trap_input_closed", (["10 ON ERROR GOTO 100", "20 INPUT #1,A$",
                            "100 PRINT ERR", "RUN"], None)),
    # ...and its GREEN CONTROL, which passed BEFORE D-NOTOPEN as well as after:
    # LOF on the same never-opened channel already raised 59 and already trapped.
    # Without it, a red trap row above could not tell "the fix does not trap"
    # from "this probe cannot read a trap".
    ("trap_lof_closed",   (["10 ON ERROR GOTO 100", "20 A=LOF(1)",
                            "100 PRINT ERR", "RUN"], None)),

    # The sites D-NOTOPEN DELIBERATELY LEFT, measured and allowlisted below. They
    # are here so KNOWN_DIVERGE stays a CONTROL THAT MUST KEEP MATCHING rather
    # than an empty box (memory: deadcode-gate) -- and so that a later slice which
    # sweeps them, or one which sweeps them BY ACCIDENT, moves a row instead of
    # landing silently. `closed_ch2` is the ERR 52 class, which is a DIFFERENT
    # class reached one check earlier (fch_valid), not this item.
    ("closed_get",     (["GET #1,1"], None)),
    ("closed_field",   (['FIELD #1,10 AS A$'], None)),
    ("closed_ch2",     (['PRINT #2,"X"'], None)),

    # write -> CLOSE -> re-open: catches a fix that lets its zero reach the dir.
    ("roundtrip",    (['OPEN "ZQ.DAT" FOR OUTPUT AS #1',
                       'PRINT #1,"ABCDE"',
                       "CLOSE",
                       'OPEN "ZQ.DAT" FOR INPUT AS #1',
                       "PRINT LOF(1)"], "ZQ      DAT")),
]

# --- ORACLE LOCK -------------------------------------------------------------
# The reference's measured answer per row, recorded 2026-07-31. A change here is
# ORACLE DRIFT (a different machine/ROM/disk), not a zerobas result, and fails the
# run on its own. `None` = not yet recorded; fill in from the first measured run.
REF_EXPECT: dict = {
    "ctl_syntax":   "SYNTAX",
    "new_out":      0,       # a created file is 0 bytes...
    "new_out_wr":   0,       # ...and a SEQUENTIAL write does not move it
    "stale_prev":   0,       # ...whatever was open on the channel before
    "stale_big":    0,
    "exist_out":    0,       # ...even when the file existed and is truncated
    "exist_out_wr": 0,
    "append_new":   "FNO",   # APPEND of a MISSING file: `File not found`, no
                             # channel opened, no directory entry made -- so the
                             # following LOF reports ERR 59. See §4 of the
                             # characterization; owned by its own TODO item.
    "append_new_wr": "FNO",  # ...and the PRINT# into that unopened channel is
                             # REFUSED with ERR 59 too (measured 2026-07-31, not
                             # assumed: it could have been ERR 52 `bad file
                             # number`). No LOF is typed in this row, so this is
                             # the channel-state reading that does not go through
                             # LOF at all.
    "append_exist": 26,      # APPEND of an existing file: its current size
    "rand_new":     0,
    "rand_exist":   26,
    "rand_put":     256,     # a RANDOM PUT moves the field LIVE (recno*reclen)
    "lof_input":    26,
    "lof_bin":      2048,
    "lof_closed":   "FNO",
    "ctl_prwr_closed": "FNO",   # PRINT# into an unopened channel: ERR 59 as well
                                # (measured 2026-07-31 -- the attribution control
                                # for append_new_wr)
    # --- D-NOTOPEN, all MEASURED 2026-07-31 on the CF-3300, never guessed.
    "closed_input":   "FNO",    # INPUT# on a never-opened channel: ERR 59
    "closed_lineinp": "FNO",    # ...and LINE INPUT#, which shares the same arm
    "trap_print_closed": 59,    # the handler RAN and printed 59 -- so the
    "trap_input_closed": 59,    # reference's ERR 59 here is trappable, and a `0`
    "trap_lof_closed":   59,    # would have meant no error was raised at all
    "closed_get":     "FNO",    # GET on a never-opened channel: ERR 59 too...
    "closed_field":   "FNO",    # ...and FIELD. Both LEFT by D-NOTOPEN (its §7.1):
                                # zerobas answers `Syntax error` from a DIFFERENT
                                # disposition at DIFFERENT sites (field.asm's
                                # stmt_error), and what the reference answers for
                                # GET on a channel open FOR INPUT is NOT measured
                                # -- sweeping an unmeasured neighbour is the trap.
    "closed_ch2":     "BFN",    # #2 > MAXFILES=1 -> ERR 52 `bad file number`, a
                                # DIFFERENT class from 59, rejected one check
                                # earlier (fch_valid). ⚠️ And it does NOT
                                # generalise: `PRINT #0,"X"` measures **FNO** on
                                # the reference, not BFN -- channel 0 is a legal
                                # channel number that is merely not open. So the
                                # ERR 52 item cannot be "route fch_valid's
                                # rejects to 52". D-NOTOPEN §7.2.
    "roundtrip":    8,       # "ABCDE" + CRLF + Ctrl-Z
}

# The DIRECTORY oracle -- the SECOND INSTRUMENT's own lock, one entry per case
# that names a directory. Recorded 2026-07-31 alongside REF_EXPECT.
#
# ⚠️ UNTIL D-APPMISS (2026-07-31) THIS COLUMN WAS MEASURED, PRINTED AND NEVER
# COMPARED. `run_case` returned it and `main` printed it, but the verdict was
# computed from the LOF value alone -- so the claim it exists to hold ("the
# reference makes NO directory entry") could not fail the gate. A second
# instrument that cannot make a row red is decoration. It is part of the verdict
# now: a row agrees only if BOTH columns agree.
DIR_EXPECT: dict = {
    "new_out":      0,
    "new_out_wr":   0,       # a SEQUENTIAL write does not reach the directory
    "exist_out":    0,       # OPEN FOR OUTPUT truncates the entry at open
    "exist_out_wr": 0,
    "append_new":   "absent",   # the whole point: NO entry is made
    "append_new_wr": "absent",
    "append_exist": 26,
    "rand_new":     0,
    "rand_exist":   26,
    "rand_put":     0,       # ...while LOF already reads 256 (characterization §3)
    "lof_input":    26,
    "lof_bin":      2048,
    "roundtrip":    8,
}

# --- GATE: divergences that are FILED AND EXPECTED, with the item that owns
# each. Everything NOT listed here must MATCH the reference, and a row that
# starts diverging DIFFERENTLY still trips the gate (the value is part of the
# key). The list is the honest statement of what is not built yet; it shrinks as
# those items land, and it must never grow silently.
#
# ✅ D-APPMISS LANDED 2026-07-31 (docs/spec-basic-append-missing-refuse.md): the
# entry that used to live here, `append_new`, is GONE rather than updated.
# `OPEN … FOR APPEND` on a missing file now REFUSES on both machines -- one
# instruction, `basic/fat.asm`'s `jp c,fat_io_create` -> `ret c`. The comment
# above it had stated the create as settled CF-3300 parity, citing
# disk_probe_append.py, which creates its file with OUTPUT first and only ever
# appends to an EXISTING one -- a true claim about the Ctrl-Z resume rule that
# never reached this case.
# ⚠️ The list did not end up empty: the row added to PROVE the channel was
# refused (`append_new_wr`) surfaced a DIFFERENT, pre-existing defect one layer
# down. It grew LOUDLY, with its own filed item and its own attribution control,
# which is the only way this list is allowed to grow.
#
# ✅ D-NOTOPEN LANDED 2026-07-31 (docs/spec-basic-chan-notopen-err59.md): the two
# entries that defect put here, `append_new_wr` and `ctl_prwr_closed`, are GONE
# rather than updated -- PRINT#/INPUT#/LINE INPUT# on a not-open channel now raise
# the same trappable ERR 59 the CF-3300 does, by CALLING the classifier LOF was
# already reaching (`fch_mode_class`, basic/expr.asm) instead of hand-inlining its
# array read and omitting its `or a`. Both sites got 4 bytes of page 1 back.
KNOWN_DIVERGE: dict = {
    # What D-NOTOPEN MEASURED AND DELIBERATELY LEFT (its §7), each with the row
    # that pins it. These are not "known bad, ignore" -- they are a CONTROL THAT
    # MUST KEEP MATCHING: if a later slice sweeps them, or sweeps them by
    # accident, the value moves and this gate trips.
    #
    # §7.1 -- GET/PUT/FIELD/INPUT$ on a not-open channel answer `Syntax error`
    # where the reference answers ERR 59. A DIFFERENT disposition (stmt_error /
    # str_eval_no, not load_error) at DIFFERENT sites (basic/field.asm,
    # basic/strvar.asm). FIELD's would be a 0-byte change, but GET's site
    # conflates "not open" with "open but not RANDOM" and what the reference
    # answers for GET on a channel open FOR INPUT is NOT MEASURED.
    "closed_get":   ("FNO", "SYNTAX"),
    "closed_field": ("FNO", "SYNTAX"),
    # §7.2 -- the ERR 52 class, reached one check EARLIER (fch_valid), so
    # D-NOTOPEN's change cannot and does not move it. ⚠️ It does not generalise:
    # `PRINT #0,"X"` measures FNO on the reference, not BFN.
    "closed_ch2":   ("BFN", "LOADERR"),
}

# The same, for the directory column.
DIR_DIVERGE: dict = {
    # ⚠️ NOT an append defect, and NOT new behaviour -- newly VISIBLE, because
    # D-APPMISS made this column part of the verdict. A RANDOM `PUT` stamps the
    # on-disk directory size on zerobas immediately (256 = recno * reclen) while
    # the reference leaves the entry at 0 and carries the size in RAM only
    # (characterization §3: ref LOF = 256 with ref dir = 0 -- the row that proved
    # LOF does not read the directory). Filed in TODO.md as its own item.
    # It is also this gate's own falsification: a row where the LOF columns AGREE
    # and only `dir` separates the machines, so a dir comparison that stayed
    # green here would be measuring nothing.
    "rand_put":  (0, 256),
}

ERR_CLASSES = {
    "SYNTAX": ("syntax error",),
    "IFC":    ("illegal function call",),
    "FNF":    ("file not found",),
    "BFN":    ("bad file number",),
    "FNO":    ("file not open",),
    "OOM":    ("out of memory",),
    "DIO":    ("disk i/o error", "disk offline"),
    # zerobas's OWN lowercase catch-all for the file/channel family (bload.asm
    # `load_error`). The reference never prints it, so a LOADERR here is always a
    # zerobas-side reading and can never be mistaken for an oracle value.
    #
    # ⚠️ ADDED 2026-07-31 (D-APPMISS) BECAUSE ITS ABSENCE MADE A ROW UNABLE TO
    # FAIL. Without it `load error` classifies as None -- and None is also what a
    # row reads when NOTHING WENT WRONG. On `append_new_wr` those are the two
    # opposite outcomes the row exists to separate: pre-fix it read None because
    # the write was SILENTLY ACCEPTED, post-fix it read None because the write
    # was REFUSED. A value that means both is not a measurement, and a regression
    # back to silent acceptance would not have moved it.
    "LOADERR": ("load error",),
}


def err_class(text: str):
    """Map a screen line to an error class, or None if it is not an error."""
    low = text.lower()
    for cls, needles in ERR_CLASSES.items():
        for n in needles:
            if n in low:
                return cls
    return None


def dir_size(dsk_path: str, name11: str):
    """The FAT12 root-directory size field for an 11-byte 8.3 name, or None.

    THE SECOND INSTRUMENT. Read straight out of the machine's own scratch image
    after it exits, so `LOF` can be compared against what the DIRECTORY holds at
    that instant instead of against another reading of the same cell.
    """
    try:
        with open(dsk_path, "rb") as fh:
            d = fh.read()
    except OSError:
        return None
    if len(d) < 512:
        return None
    bps = struct.unpack("<H", d[11:13])[0]
    res = struct.unpack("<H", d[14:16])[0]
    nfat = d[16]
    nroot = struct.unpack("<H", d[17:19])[0]
    spf = struct.unpack("<H", d[22:24])[0]
    if bps != 512:
        return None
    root = (res + nfat * spf) * bps
    want = name11.encode("ascii")
    for i in range(nroot):
        e = d[root + i * 32: root + i * 32 + 32]
        if len(e) < 32 or e[0] == 0:
            break
        if e[0] == 0xE5 or (e[11] & 0x18):
            continue
        if e[:11] == want:
            return struct.unpack("<I", e[28:32])[0]
    return "absent"


def tcl_quote(s: str) -> str:
    # CR must be the ESCAPE \r; a raw 0x0d breaks Tcl's line parsing and the
    # Enter event is silently dropped.
    out = []
    for ch in s:
        if ch == "\r":
            out.append("\\r")
        elif ch in '"\\[]$':
            out.append("\\" + ch)
        else:
            out.append(ch)
    return '"' + "".join(out) + '"'


def build_tcl(out_path: str, lines, date_prompt: bool, boot_t: float,
              step: float = 14.0) -> str:
    L = ["set throttle off",
         f"set __f [open {{{out_path}}} w]",
         "proc __hex {a l} { binary scan [debug read_block memory $a $l] H* h; return $h }",
         "proc __hex_v {a l} { binary scan [debug read_block VRAM $a $l] H* h; return $h }",
         "proc __dump {} {",
         "  global __f",
         '  puts $__f "meta scrmod=[__hex 0xFCAF 1] linlen=[__hex 0xF3B0 1]"',
         '  puts $__f "scr0=[__hex_v 0x0000 960]"',
         '  puts $__f "scr1=[__hex_v 0x1800 768]"',
         "  flush $__f",
         "}"]
    t = boot_t
    if date_prompt:
        L.append(f'after time {t} {{ type "\\r" }}')   # clear "Enter date"
        t += 4.0
    for ln in lines:
        # openMSX drops a CR that shares a burst with text under `throttle off`,
        # so each Enter is its own event ~3s after its command.
        #
        # ⚠️ 14.0 s, not chancost's 4.5. MEASURED, not padded for luck: at 4.5 the
        # CF-3300 ate whole CHUNKS of the line AFTER any line that touched the
        # disk -- `PRINT LOF(1)` arrived as `PRO)` and `OPEN "ZQ.DAT" FOR INPUT
        # AS #1` as `OZQ R INPUT AS #1`, both of which the machine answered with
        # a perfectly real `Syntax error`. Disk BASIC is not polling the keyboard
        # while the FDC is busy, and `type` keeps injecting regardless; chancost's
        # cadence is safe only because its rows are FRE(0) reads.
        # At 9.0 the drops stopped but zerobas started DUPLICATING the first
        # character of the line after a create (`PRINT LOF(1)` -> `PPRINT LOF(1)`),
        # reproducibly, on both `stale_*` rows -- the same busy-FDC window, landing
        # as an inserted character instead of a dropped one. 14.0 clears both, on
        # both machines, across the whole battery.
        # ⚠️ A mangled line is indistinguishable from a semantic failure by its
        # ANSWER -- `PRO)` earns a completely real `Syntax error`. The delay makes
        # the mangling rare; the ECHO GUARD (echo_missing) is what makes it LOUD,
        # and the guard is the load-bearing half. Neither replaces the other.
        L.append(f"after time {t} {{ type {tcl_quote(ln)} }}")
        L.append(f'after time {t + 3.0} {{ type "\\r" }}')
        t += step
    L.append(f"after time {t + 2.0} {{ __dump }}")
    L.append(f"after time {t + 4.0} {{ close $__f; exit }}")
    return "\n".join(L) + "\n"


def decode_raw(hexv: str, cols: int):
    """The name table as a list of UNSTRIPPED rows, one string per screen row."""
    data = bytes.fromhex(hexv)
    return ["".join(chr(c) if 32 <= c < 127 else " "
                    for c in data[r * cols:(r + 1) * cols])
            for r in range(len(data) // cols)]


def decode(hexv: str, cols: int):
    return [r.strip() for r in decode_raw(hexv, cols)]


def echo_missing(raw_rows, lines, prompt: str):
    """Which typed lines are NOT echoed on screen -- i.e. arrived mangled.

    THE APPARATUS GUARD. A dropped keystroke turns `PRINT LOF(1)` into `PRO)`,
    and the machine answers that with a completely real `Syntax error` -- which
    reads as a finding about LOF. Concatenating the rows reproduces the screen as
    one string, and a WRAPPED echo is contiguous in it, so a plain substring test
    covers both wrapped and unwrapped lines.

    ⚠️ MATCH WITH ALL WHITESPACE REMOVED, from both sides. Two separate screen
    geometries conspire against a naive substring test, and the guard's first two
    versions were each wrong in exactly the way the guard exists to catch:
      * the name table is 32 cells wide but CF-3300 Disk BASIC boots SCREEN 1 at
        `linlen=$1d` = 29 columns, so a 30-character line WRAPS and the unused
        cells land between the two halves of the echo -- comparing against full
        32-wide rows flagged 10 of 16 rows, several with perfect screens;
      * slicing to `linlen` instead was ALSO wrong, because the reference indents
        SCREEN 1 by a LEFT MARGIN of 2 (measured; C-BIOS uses 1 -- memory
        lean-retire-s2-switch), so `r[:29]` cuts the last two characters off any
        full-width line and re-flagged the same rows.
    Stripping whitespace on both sides is independent of margin, of `linlen` and
    of the wrap point, so it needs no per-machine constant to be right. The cost
    is that a dropped SPACE no longer trips the guard -- acceptable, because the
    drops this catches swallow whole chunks (`PRINT LOF(1)` -> `PRO)`), and BASIC
    ignores spacing anyway.
    ⚠️ Assumes the case is short enough that nothing scrolls off -- keep every
    case at <= 5 typed lines.
    """
    squeeze = lambda s: "".join(s.split())
    # every row, and every run of 2 or 3 consecutive rows, as one squeezed string
    # (a wrapped echo spans rows; nothing here wraps past three).
    cand = set()
    for i in range(len(raw_rows)):
        for n in (1, 2, 3):
            cand.add(squeeze("".join(raw_rows[i:i + n])))
    return [ln for ln in lines if prompt + squeeze(ln) not in cand]


def run_case(side: str, label: str, lines, dirname, step: float = 14.0):
    machine, date_prompt, boot_t, prompt = MACHINES[side]
    dsk = tempfile.NamedTemporaryFile(suffix=".dsk", prefix=f"lof_{side}_{label}_",
                                      delete=False).name
    shutil.copy(SRC_DSK, dsk)              # /tmp copy -- never the committed image
    out = f"/tmp/lof_{side}_{label}.txt"
    tcl = out + ".tcl"
    with open(tcl, "w") as fh:
        fh.write(build_tcl(out, lines, date_prompt, boot_t, step))
    if os.path.exists(out):
        os.unlink(out)
    proc = subprocess.Popen(
        [OMSX, "-machine", machine, "-diska", dsk,
         "-command", "set renderer none; set sound_driver null", "-script", tcl],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    deadline = time.time() + 240
    while proc.poll() is None and time.time() < deadline:
        time.sleep(0.1)
    if proc.poll() is None:
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        os.unlink(dsk)
        return side, label, None, ["TIMEOUT"], "", None
    # the SECOND instrument: read the directory the machine left behind.
    dsz = dir_size(dsk, dirname) if dirname else None
    os.unlink(dsk)
    if not os.path.exists(out):
        return side, label, None, ["NO CAPTURE (machine/ROMs missing?)"], "", dsz
    s0, s1, r0, r1, meta, scrmod, linlen = [], [], [], [], "", 0, 0
    for line in open(out):
        line = line.rstrip("\n")
        if line.startswith("scr0="):
            r0 = decode_raw(line.partition("=")[2], 40)
            s0 = [r.strip() for r in r0]
        elif line.startswith("scr1="):
            r1 = decode_raw(line.partition("=")[2], 32)
            s1 = [r.strip() for r in r1]
        else:
            meta = line
            for tok in line.split():
                if tok.startswith("scrmod="):
                    scrmod = int(tok.split("=")[1], 16)
                elif tok.startswith("linlen="):
                    linlen = int(tok.split("=")[1], 16)
    # geometry MEASURED, not assumed
    rows = [r for r in (s1 if scrmod == 1 else s0) if r]
    # the apparatus guard runs BEFORE any answer is read off the screen.
    missing = echo_missing(r1 if scrmod == 1 else r0, lines, prompt)
    if missing:
        return (side, label, "MANGLED", rows + [f"NOT ECHOED: {missing!r}"],
                meta, dsz)
    value = None
    for r in rows:                                   # an error outranks a number
        cls = err_class(r)
        if cls:
            value = cls
    if value is None:
        nums = [int(r) for r in rows if re.fullmatch(r"-?\d+", r)]
        value = nums[-1] if nums else None
    return side, label, value, rows, meta, dsz


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="comma-separated case labels")
    ap.add_argument("--side", choices=("ref", "zb", "both"), default="both")
    ap.add_argument("--gate", action="store_true",
                    help="fail on oracle drift or on any unfiled divergence")
    ap.add_argument("-j", "--jobs", type=int, default=4)
    ap.add_argument("--line-delay", type=float, default=14.0,
                    help="emulated seconds per typed line (default 14.0, the "
                         "measured-safe value). Settable mainly so the echo "
                         "guard can be shown to CUT: at 4.5 the CF-3300 drops "
                         "keystrokes on disk-busy lines and zerobas doubles them.")
    ap.add_argument("-v", "--verbose", action="store_true", help="print screens")
    args = ap.parse_args()
    if not os.path.isfile(SRC_DSK):
        print(f"missing test image: {SRC_DSK}")
        return 2
    cases = CASES
    if args.only:
        want = {s.strip() for s in args.only.split(",") if s.strip()}
        cases = [c for c in CASES if c[0] in want]
        if not cases:
            print(f"--only matched no cases: {sorted(want)}")
            return 2
    sides = ("ref", "zb") if args.side == "both" else (args.side,)
    jobs = [(s, lbl, lines, dn, args.line_delay)
            for lbl, (lines, dn) in cases for s in sides]
    with cf.ThreadPoolExecutor(max_workers=args.jobs) as ex:
        results = list(ex.map(lambda j: run_case(*j), jobs))
    by = {(s, l): (v, rows, meta, dsz) for s, l, v, rows, meta, dsz in results}

    print(f"{'case':<14} {'ref LOF':>9} {'ref dir':>9} "
          f"{'zb LOF':>9} {'zb dir':>9}   verdict")
    print("-" * 78)
    oracle_bad, diverge, mangled = [], [], []
    for label, _ in cases:
        rv, rd = (by.get(("ref", label), (None, [], "", None))[0],
                  by.get(("ref", label), (None, [], "", None))[3])
        zv, zd = (by.get(("zb", label), (None, [], "", None))[0],
                  by.get(("zb", label), (None, [], "", None))[3])
        note = ""
        # ⚠️ CHECKED FIRST, and never folded into the comparison: two MANGLED
        # sides compare EQUAL and would print "agree" -- a row that measured
        # nothing reading as a row that passed.
        if "MANGLED" in (rv, zv):
            note = "MANGLED (a typed line was not echoed -- NOT a reading)"
            mangled.append(label)
        elif "ref" in sides and label in REF_EXPECT and rv != REF_EXPECT[label]:
            note = f"ORACLE DRIFT (recorded {REF_EXPECT[label]!r})"
            oracle_bad.append(label)
        elif ("ref" in sides and label in DIR_EXPECT
                and rd != DIR_EXPECT[label]):
            note = f"DIR ORACLE DRIFT (recorded {DIR_EXPECT[label]!r})"
            oracle_bad.append(label)
        elif args.side == "both":
            # BOTH columns, and each one names itself in the verdict. The LOF
            # reading and the directory reading are two INDEPENDENT instruments
            # (§5b of docs/spec-basic-append-missing-refuse.md); a row where only
            # one of them separates the machines is exactly the row a
            # single-column verdict would have called `agree`.
            vok = rv == zv
            dok = rd == zd
            vfiled = KNOWN_DIVERGE.get(label) == (rv, zv)
            dfiled = DIR_DIVERGE.get(label) == (rd, zd)
            bad = []
            if not (vok or vfiled):
                bad.append("LOF")
            if not (dok or dfiled):
                bad.append("dir")
            if bad:
                note = "DIVERGES (" + "+".join(bad) + ")"
                diverge.append((label, (rv, rd), (zv, zd)))
            elif vfiled or dfiled:
                note = "diverges (FILED: " + "+".join(
                    (["LOF"] if vfiled else []) + (["dir"] if dfiled else [])) + ")"
            else:
                note = "agree"
        print(f"{label:<14} {str(rv):>9} {str(rd):>9} "
              f"{str(zv):>9} {str(zd):>9}   {note}")
        if args.verbose:
            for s in sides:
                for r in by.get((s, label), (None, [], "", None))[1]:
                    print(f"      {s} | {r}")

    print()
    if "ref" in sides:
        print("meta(ref):", by.get(("ref", cases[0][0]), (None, [], "", None))[2])
    if "zb" in sides:
        print("meta(zb) :", by.get(("zb", cases[0][0]), (None, [], "", None))[2])

    # --- the harness control has to have BITTEN, or nothing above is a reading.
    ctl = [by.get((s, "ctl_syntax"), (None, [], "", None))[0] for s in sides
           if ("ctl_syntax") in {c[0] for c in cases}]
    if ctl and any(c != "SYNTAX" for c in ctl):
        print("\n*** HARNESS CONTROL FAILED: ctl_syntax did not report a syntax "
              f"error ({ctl}). Every reading above is worthless.")
        return 3

    # --- the ORACLE-COMPLETENESS control. A row with no recorded oracle is not
    # locked, and an UNLOCKED row is the quiet way a battery stops measuring: it
    # can only ever report "agree", never "the reference moved". Adding a case
    # and forgetting to record its answer must be LOUD, so it is a gate failure,
    # not a comment in the docstring.
    unlocked = [lbl for lbl, (_, dn) in cases
                if lbl not in REF_EXPECT
                or (dn is not None and lbl not in DIR_EXPECT)]
    if unlocked and "ref" in sides:
        print(f"\n*** ORACLE NOT RECORDED for {unlocked} -- add the measured "
              f"answer to REF_EXPECT (and DIR_EXPECT if the case names a "
              f"directory). Until then those rows are unlocked.")

    print(f"\n{len(cases)} cases, {len(diverge)} unfiled divergence(s), "
          f"{len(oracle_bad)} oracle drift(s), {len(mangled)} mangled")
    for label, rv, zv in diverge:
        print(f"  DIVERGES {label}: ref=(LOF,dir){rv!r} zb=(LOF,dir){zv!r}")
    if mangled:
        print(f"  MANGLED (re-run; raise the per-line delay): {mangled}")
        return 3        # ALWAYS fatal, gate or not: it is not a measurement.
    if args.gate and (diverge or oracle_bad or (unlocked and "ref" in sides)):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
