#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""D-CASTAIL — what a machine prints AFTER `RUN"CAS:x"` / `LOAD"CAS:x",R`.

The TAPE TWIN of `basic_probe_runtail.py`, and the residual that battery filed:
`docs/spec-basic-runtail.md` §9.

    `basic/cload.asm`'s `dl_cas_close` (LOAD"CAS:x",R) and `dr_is_cas`
    (RUN"CAS:x") end in the identical `jp run_prog` from a STATEMENT context, so
    D-RUNTAIL's defect A is structurally present there verbatim -- but that
    battery mounts a disk, not a `.cas`, so no row read them before OR after.

🔴 THE INSTRUMENT WAS ALREADY THERE. §9 says `omsx_repl.run_cases` "mounts a
disk, not a `.cas`", which is true of its SIGNATURE and false of the module: the
`prologue` seam (input-devices arc I2) runs raw Tcl before the timeline, and
`basic_probe_lnblank`'s `cld` rows already mount a tape with
`cassetteplayer insert`. No library change was needed for the mount; what this
battery adds is the `@WAIT` budget per row and the tape FIXTURE.

WHAT THE ROWS ASK, each one a whole-tail EXACT match (never a substring --
the subject IS an extra screen row):

  `cas-run-hit`        a program loaded from TAPE and run prints its OWN output
                       and nothing else
  `cas-run-hit-res`    ...even with a different program already resident
  `cas-loadr-hit`      `LOAD"CAS:x",R` is the same verb by another spelling
  `cas-run-brk`        a tape load ABORTED with Ctrl-STOP prints ONE message
  `cas-run-brk-res`    ...and does NOT then run the program already resident
  `cas-loadr-brk-res`  ...nor does the `LOAD",R` spelling of it
  `bare-run`           🟢 CONTROL: plain `RUN` is the path this slice does not
                       touch; it must keep printing exactly the program's output
  `cas-load-plain`     🟢 CONTROL: `LOAD"CAS:x"` without `,R` loads and does NOT
                       run -- its `:listing` half proves the tape arrived

D-CASSEARCH adds the rows that read the SEARCH itself, on a TWO-file tape
(docs/spec-basic-cassearch.md). Their subject is the progress line, so they read
their verb's line UNFILTERED:

  `cas2-load`          `LOAD"CAS:RT"` steps over `SK` and takes `RT`
  `cas2-merge`         ...so does `MERGE"CAS:"`, a DIFFERENT caller of the same
                       search engine
  `cas2-cload`         ...so does `CLOAD`, on the TOKENISED tape
  `cas2-bare`          `LOAD"CAS:"` with no name takes the FIRST file: a
                       separate arm of the match, reached without the compare
                       loop, and the only row that can HOLD when the skip arm is
                       knifed
  `cas2-open`          📌 `OPEN"CAS:" FOR INPUT` -- the fourth caller, and a
                       PINNED divergence for a reason that is NOT the progress
                       line (see below)

D-CASCUT adds a tokenised tape that ENDS INSIDE THE PROGRAM, read with CLOAD and
broken with Ctrl-STOP (knife-checked, one exit each):

  `cas-cut-link`       the tape ends after a link word's LOW byte -> the
                       loader's link-high failure exit (`ctp_link_err`)
  `cas-cut-body`       the tape ends inside a line's body -> its body-read
                       failure exit (`ctp_err_pop`)

🔴 THE `-res` ROWS EXIST BECAUSE AN EMPTY PROGRAM HIDES A WRONG RUN. Measured in
D-RUNTAIL under two separate knives ([[an-empty-program-hides-a-wrong-run]]):
`run-miss` -- a failed load with NOTHING resident -- held GREEN over a machine
that ran the store anyway, because running an EMPTY program is silent. "Refused
to run" and "ran an empty store" print the identical string. Every failure row
here therefore has `10 PRINT"ZQ1"` resident and asks whether `ZQ1` is ABSENT.

🔴 EVERY ROW IS SCORED BY CROSS-SIDE AGREEMENT, NOT AGAINST A HAND-WRITTEN WANT.
The references define the answer. The exception is CONTROLS below, which
additionally require POSITIVE TEXT in the agreed reading -- two DEAD machines
agree perfectly, and `<nothing>` is a legitimate answer for one row here
([[gate-whose-answer-is-an-error-passes-a-dead-subject]]).

⚠️ ONE STRING IS NORMALISED PER SIDE, AND ONLY ONE -- exactly as in
`basic_probe_runtail`. An aborted tape read answers `Device I/O error` on the
references and zerobas's own lowercase `load error`: the quarantined no-disk /
mount / I-O wording divergence (`basic/PROVENANCE.md`), deliberately NOT in
scope. A tail that is EXACTLY that one message reads `<load-failed>` on both
sides, so the rows are scored on SHAPE -- how many messages, and did the
resident program run -- without re-opening the wording. A tail that merely
CONTAINS it is not normalised: the extra row is the subject.

🔴 AND ONE CLASS OF ROW IS FILTERED OUT OF THE SIX SUBJECT ROWS, AND IT IS A
SUBJECT IN ITS OWN RIGHT -- SO IT GETS ITS OWN ROWS RATHER THAN A SILENT
NORMALISATION. Every machine here prints the BIOS tape-search progress line --
`Found:NAME` when the search takes a file, `Skip :NAME` when it steps over one.
It is about the SEARCH, not about what the verb does after the load, so scoring
it inside the D-CASTAIL rows would DIFF all six of them for a reason none is
asking about. `SEARCH_ROWS` therefore drops those EXACT strings from those
tails, and the `cas2-*` rows below read the search line UNFILTERED -- it is
their whole subject.

⚠️ THE FILTER USED TO FIRE ONLY ON A REFERENCE, WHICH IS WHY IT NEEDED A PIN.
Until D-CASSEARCH (docs/spec-basic-cassearch.md) zerobas printed NEITHER row, so
the filter was a normalisation that was a NO-OP on the side under test -- one
that blesses one machine's silence ([[readout-blind-to-its-own-subject]]) --
and `cas-load-plain:search` pinned all three sides verbatim so it could not.
zerobas now prints both rows, the pin is RE-MEASURED to `Found:RT` rather than
loosened, and the filter now fires on all three sides: it normalises an
AGREEMENT, which is the honest use of one. It is KEPT rather than deleted, and
the reason is `<load-failed>`: that normalisation fires only when the tail is
EXACTLY the side's own message, deliberately, so that an extra row is always the
subject. Unfiltered, every abort row's tail would be `Skip :RT` PLUS the
message, nothing would normalise, and all three abort rows would DIFF on the
quarantined WORDING divergence this battery exists to hold out of scope.

D-CASOPEN adds the rows that read the OPEN verb's NAME handling, and closes the
divergence the two `cas2-open` pins held (docs/spec-basic-casopen.md):

  `cas2-openbare`    `OPEN"CAS:"` with no name takes the NEXT file, exactly like
                     bare `LOAD"CAS:"` -- the arm that reaches the match WITHOUT
                     the compare loop, and the row that says a fix did not arm
                     matching unconditionally
  `cas2-opencase`    the compare is CASE-SENSITIVE: `OPEN"CAS:rt"` does NOT find
                     `RT`. Read FILTERED, deliberately -- see its comment
  `cas-openout`      🎯 `FOR OUTPUT` with a name, read off the TAPE THE MACHINE
  `cas-openoutbare`  WROTE (a `cassetteplayer new` recording, decoded by
                     probes/lib/cas_decode.py). The screen cannot answer this
                     one: OPEN"CAS:WX" FOR OUTPUT prints nothing whatever it
                     records

✅ ONE DIVERGENCE REMAINS PINNED HERE, AND IT IS THE PROGRESS LINE'S
(`cas-load-plain:search`). `OPEN"CAS:name" FOR INPUT` NAME-MATCHES on both
references -- it steps over a non-matching file and opens the named one -- and
zerobas deliberately did not (basic/files.asm `oo_dev_cas` wrote
`CAS_WANT_ON = 0`), so it opened the NEXT file and handed back the WRONG FILE'S
BYTES. `cas2-open` / `cas2-open:echo` pinned that per side until D-CASOPEN closed
it; they are now SCORED rows with a `ZQ9` control, which is the reclassification
that spec §4.1 argues for rather than a loosened pin.

🟢 AND UNLIKE THE DISK BATTERY, THE VG-8020 IS A LEGITIMATE SIDE. `RUN"A:name"`
needs a disk interface, which is why `basic_probe_runtail` refuses a vg8020 run;
`RUN"CAS:x"` needs a CASSETTE PORT, which every MSX1 has, and the Philips
VG-8020 answers these rows out of its own main ROM. It is a side here, and its
agreement with the CF-3300 is what says a reading is the MSX1 rule rather than a
property of one machine's Disk BASIC.

⚠️ THE `LOAD`/`RUN`/`MERGE`/`OPEN` FIXTURES ARE $EA ASCII, AND THAT IS FORCED BY
THE REFERENCE. `LOAD"CAS:"`/`RUN"CAS:"` on a real MSX search the tape for an
ASCII file and SKIP a tokenised ($D3) one -- past it, to the end of the tape,
where they wait forever (measured in docs/dotgaps-msx1-characterization.md §1.2;
zerobas accepts both, a divergence filed there, not re-opened here). A $D3
fixture would therefore HANG both references and gate nothing. `CLOAD` is the
exception and gets the `twot` tape: it searches for a TOKENISED file, so $D3 is
what the reference needs there and an ASCII tape would hang it instead.

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
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "disk"))
import omsx_repl                                                 # noqa: E402
import probe_report                                              # noqa: E402
import probe_tmp                                                 # noqa: E402
from basic_probe_cas_ascii import build_ascii_cas                # noqa: E402
from cas_encode import (CAS_SYNC, BASIC_ID, build_cas_basic,      # noqa: E402
                        build_cas_basic_csave)
from bas_tokenise import make_multiline_program                  # noqa: E402
import cas_decode                                                # noqa: E402

ZB_MACHINE = os.environ.get("ZEROBAS_BASIC_MACHINE",
                            "C-BIOS_MSX1_EU_REPACK_DISK")
TEST_DSK = os.environ.get("ZEROBAS_TEST_DSK", "disk/test720.dsk")

# `failmsg` is the ONE string normalised per side -- see the docstring.
SIDES = {
    "vg8020": dict(machine="Philips_VG_8020", boot=8.0, step=2.5,
                   reset=("NEW",), failmsg="Device I/O error", diska=False),
    "cf3300": dict(machine="National_CF-3300", boot=14.0, step=4.5,
                   reset=("", "SCREEN 0", "NEW"), failmsg="Device I/O error",
                   diska=True),
    "zb":     dict(machine=ZB_MACHINE, boot=8.0, step=2.5,
                   reset=("NEW",), failmsg="load error", diska=True),
}

FAILED = "<load-failed>"

# The BIOS tape-search progress rows, dropped from the D-CASTAIL tails (where
# they are not the subject) and read UNFILTERED by every `cas2-*` row (where they
# are). EXACT strings, never a prefix match: a rule wide enough to catch
# `Found:`-anything is wide enough to eat a program's output, and the whole point
# of this battery is that an extra row is the subject. Knife K-NAME
# (spec-basic-cassearch.md §5) is what proves the exactness is load-bearing --
# under it the emitted row becomes `Found:Skip :`, which a PREFIX rule would
# still have eaten, leaving six subject rows green over a search printing
# garbage. They red.
SEARCH_ROWS = ("Found:{n}", "Skip :{n}")

# The tape this battery writes and reads back. It PRINTS, and that is the whole
# design: `ZQ9` in the tail says the file arrived AND ran AND nothing followed
# it, in ONE string -- the disk battery's trick, for the same reason.
CAS_NAME = "RT"
CAS_PROG = ['10 PRINT"ZQ9"']
TXTBASE = 0x8001

# --- D-CASSEARCH: the SECOND and THIRD fixtures ------------------------------
# A TWO-file tape, so the SKIP arm of the search has something to step over. The
# one-file tape above can only ever produce a `Found:`; `Skip :` is a different
# arm of `com_miss` and nothing in this tree had ever read it on a reference.
# File 1 is `SK` (prints ZQ8), file 2 is `RT` (prints ZQ9) -- so every `:listing`
# / `:echo` half is a POSITIVE CONTROL that says the search stepped over the
# FIRST file and took the SECOND, not merely that a tape arrived.
SKIP_NAME = "SK"
SKIP_PROG = ['10 PRINT"ZQ8"']

# --- D-CASOPEN: the OUTPUT half, read off the tape the machine ACTUALLY WROTE -
# `OPEN"CAS:name" FOR OUTPUT` writes an $EA header carrying the 6-char name and
# then the text; nothing on the SCREEN says what went into that header. So the
# reading is taken from the RECORDING: the row runs on a `cassetteplayer new`
# tape and `probes/lib/cas_decode.py` turns the WAV back into bytes, exactly the
# write->read round-trip that module was built for. Signal edges only -- no
# reference disassembly, and the same decoder on all three sides.
REC_NAME = "WX"
REC_TEXT = "ZQ7"
ALIVE = "ZQ6"
ASCII_ID = 0xEA          # the $EA ASCII-file id, ten times, ahead of the name

# A tape read runs for ~10-30 EMULATED seconds while the harness keeps injecting
# on schedule, and each injection overwrites whatever is still pending, so the
# clock must be advanced past the operation before the next line is typed
# (omsx_repl.WAIT_PREFIX, and the D-DOTGAPS §1.4b measurement behind it).
W_LOAD = "@WAIT25"       # find + read the first file on the tape
W_SEEK = "@WAIT12"       # let the search run before breaking it
W_AFTER = "@WAIT8"       # let the abort report land
W_LOAD2 = "@WAIT45"      # SKIP the first file, then find + read the second
W_HDR = "@WAIT10"        # FOR OUTPUT writes the $EA header block's long leader
W_FLUSH = "@WAIT14"      # CLOSE flushes the 256-byte data block behind it

# Each row is (label, lines, subject_index, extra), `extra` = None or a tuple of
# (index, name, drop_search) triples naming FURTHER lines of the same case that
# are read as readings of their own. Subject indices are EXPLICIT rather than
# derived: several rows type a verb twice, and any "the line with the verb in it"
# rule picks the wrong one.
RUNCAS = f'RUN"CAS:{CAS_NAME}"'
LOADRCAS = f'LOAD"CAS:{CAS_NAME}",R'
MISSCAS = 'RUN"CAS:NOSUCH"'
MISSLOADR = 'LOAD"CAS:NOSUCH",R'

CASES = [
    ("cas-run-hit",       [RUNCAS, W_LOAD],                            0, None),
    ("cas-run-hit-res",   ['10 PRINT"ZQ1"', RUNCAS, W_LOAD],           1, None),
    ("cas-loadr-hit",     [LOADRCAS, W_LOAD],                          0, None),
    # --- the failure half: a tape read the operator ABORTS ----------------
    # 🔴 THERE IS NO OTHER TERMINATING TAPE FAILURE ON THE REFERENCE. A named
    # file that is not on the tape is not an error there: the machine searches
    # PAST the end of the tape and waits on silence forever. Ctrl-STOP is the
    # only failure a reference reports and returns from, which makes it the only
    # shape in which "did the resident program run afterwards?" is a question a
    # reference can answer at all.
    ("cas-run-brk",       [MISSCAS, W_SEEK, "@BREAK", W_AFTER],        0, None),
    ("cas-run-brk-res",   ['10 PRINT"ZQ1"', MISSCAS, W_SEEK, "@BREAK",
                           W_AFTER],                                   1, None),
    ("cas-loadr-brk-res", ['10 PRINT"ZQ1"', MISSLOADR, W_SEEK, "@BREAK",
                           W_AFTER],                                   1, None),
    # 🟢 THE TWO GREEN CONTROLS. `bare-run` is the REPL's own RUN command path
    # (basic/program.asm dl_run), which reaches run_prog at the depth its `ret`
    # returns to the prompt from -- the shape the tape paths are being corrected
    # TO. It must not move. `cas-load-plain` is LOAD"CAS:" without `,R`: it must
    # load the tape (the LIST half) and must NOT run it (the empty tail half).
    ("bare-run",          ['10 PRINT"ZQ1"', "RUN"],                    1, None),
    # `:listing` is the control's positive half (the tape ARRIVED); `:search` is
    # the SAME LOAD line read UNFILTERED, and it is the pinned divergence row --
    # see PINNED and the docstring.
    ("cas-load-plain",    ['10 PRINT"ZQ1"', f'LOAD"CAS:{CAS_NAME}"',
                           W_LOAD, "LIST"],                            1,
     ((3, "listing", True), (1, "search", False))),
]

# --- D-CASSEARCH: the TWO-file-tape rows, every subject read UNFILTERED -------
# 🔴 THESE ROWS ASK WHAT NOTHING IN THIS TREE HAD EVER ASKED. The battery above
# reads the search only through ONE pinned row on ONE verb with ONE file on the
# tape, so three separate questions were open, and each of them decides what a
# fix may print:
#
#   1. Does a `Skip :` row appear, once PER stepped-over file, carrying the
#      SKIPPED file's name -- or is the progress line a `Found:`-only affair?
#   2. Does `CLOAD` (the TOKENISED search) print the same rows as the ASCII
#      `LOAD"CAS:"` search?
#   3. 🔴 DO THE OTHER TWO CALLERS OF `cas_open_match` PRINT IT TOO? `MERGE"CAS:"`
#      (basic/files.asm merge_cas) and `OPEN"CAS:" FOR INPUT` (oo_dev_cas) share
#      the SAME search engine, so a print sited inside it prints for them as
#      well. If a reference is silent there, siting the fix in the shared engine
#      would CLOSE one divergence by OPENING two, and only a measurement can say.
#
# Every subject here is the SEARCH line read UNFILTERED (`UNFILTERED_SUBJECTS`);
# the `:listing` / `:echo` halves are the positive controls, and they are
# controls of the SKIP, not merely of the mount: the tape's first file prints
# ZQ8 and the second ZQ9, so a machine that took the wrong file reads ZQ8.
CASES_T2 = [
    ("cas2-load",  [f'LOAD"CAS:{CAS_NAME}"', W_LOAD2, "LIST"],         0,
     ((2, "listing", True),)),
    ("cas2-merge", ['20 PRINT"ZQ1"', f'MERGE"CAS:{CAS_NAME}"', W_LOAD2,
                    "LIST"],                                           1,
     ((3, "listing", True),)),
    ("cas2-open",  ["MAXFILES=1", f'OPEN"CAS:{CAS_NAME}" FOR INPUT AS #1',
                    W_LOAD2, "INPUT#1,A$", "CLOSE", "PRINT A$"],       1,
     ((5, "echo", True),)),
    # --- D-CASOPEN: the two INPUT readings the D-CASSEARCH residual named -----
    # `cas2-open` above asks whether OPEN name-matches AT ALL. These two ask what
    # a FIX has to know, and neither answer is derivable from that row:
    #
    #   `cas2-openbare`  Does bare `OPEN"CAS:"` take the NEXT file, the way bare
    #                    `LOAD"CAS:"` does (`cas2-bare`)? That is the arm which
    #                    reaches the match WITHOUT the compare loop, so a fix
    #                    that turns matching ON for OPEN must leave it alone --
    #                    and this is the only row that can say whether it did.
    #                    Its `:echo` control wants ZQ8, the FIRST file: on this
    #                    tape taking the wrong file means taking the SECOND.
    #   `cas2-opencase`  Is the compare CASE-SENSITIVE, as it is for LOAD/CLOAD
    #                    (`CAS_WANT` is byte-exact, CF-3300-confirmed,
    #                    docs/spec-cas-tier3-cload.md A.5)? The tape holds `RT`
    #                    and this row asks for `rt`.
    #
    # WARNING: `cas2-opencase` IS READ FILTERED, AND THAT IS WHY IT CAN BE SCORED
    # AT ALL. A case-SENSITIVE machine steps over BOTH files, runs off the end of
    # the tape, waits on silence, and is broken out of with Ctrl-STOP -- so its
    # tail is `Skip :SK / Skip :RT` PLUS the side's own aborted-load message.
    # Read UNFILTERED that tail is not EXACTLY the message, `<load-failed>` would
    # not fire, and the row would DIFF on the quarantined WORDING divergence
    # instead of on the question it asks. Filtered it is a clean two-valued
    # discriminator: `<load-failed>` = the name was compared and missed,
    # `<nothing>` = something was opened. Its `:alive` half is the positive
    # control -- a row whose answer is an error message is otherwise satisfied by
    # a machine that has stopped answering at all.
    ("cas2-openbare", ["MAXFILES=1", 'OPEN"CAS:" FOR INPUT AS #1', W_LOAD,
                       "INPUT#1,A$", "CLOSE", "PRINT A$"],            1,
     ((5, "echo", True),)),
    ("cas2-opencase", ["MAXFILES=1",
                       f'OPEN"CAS:{CAS_NAME.lower()}" FOR INPUT AS #1',
                       W_LOAD2, "@BREAK", W_AFTER, f'PRINT"{ALIVE}"'], 1,
     ((5, "alive", True),)),
    # The BARE form -- `LOAD"CAS:"` with no name -- takes the FIRST file on the
    # tape without comparing anything. It is a SEPARATE arm of the match (a
    # `CAS_WANT_ON = 0` shortcut straight to `com_match`, never through the
    # compare loop), so a fix sited at `com_match` serves it and no row above
    # reads it. Its reading must therefore be measured, not assumed to follow.
    ("cas2-bare",  ['LOAD"CAS:"', W_LOAD, "LIST"],                     0,
     ((2, "listing", True),)),
]

CASES_T2T = [
    ("cas2-cload", [f'CLOAD"{CAS_NAME}"', W_LOAD2, "LIST"],            0,
     ((2, "listing", True),)),
    # D-CASRELOCK: a SECOND `CLOAD` after a first takes the NEXT file. The first
    # read stops at the end-link, so the second TAPION starts on the seven $00
    # CSAVE wrote after it -- the same relock the skip above needs, reached by
    # a different verb sequence (no name, no skip). zerobas read `load error`
    # here and kept the FIRST program, which LIST exposes as ZQ8.
    ("cas2-cload2", ["CLOAD", W_LOAD, "CLOAD", W_LOAD, "LIST"],         0,
     ((4, "listing", True),)),
    # D-CLOADPROG: CLOAD run FROM A PROGRAM. The load replaces the program, and
    # the VG-8020 then stops at `Ok`; zerobas carried on at the stale cursor
    # and read `Syntax error in 3346` out of whatever sat under it
    # (scratchpad/cload_ta_probe7.out). The subject is RUN's tail -- the search
    # rows filtered as everywhere else, so it reads `<nothing>` on a machine
    # that stopped -- and the listing is the CONTROL that the load happened.
    ("cas2-cloadprog", ["7 POKE&HE000,201", f'10 CLOAD"{CAS_NAME}"',
                        "20 POKE&HE000,202", "RUN", W_LOAD2, "LIST"],   3,
     ((5, "listing", True),)),
]

# --- D-CASCUT (2026-09-27): a TOKENISED tape that ENDS INSIDE THE PROGRAM -----
# The D-DUPSPAN2 alias audit found CLOAD's two mid-program read-failure exits
# (`basic/cload.asm` `ctp_link_err`, `ctp_err_pop`) exercised by NO gate. A
# tape that stops inside the program reaches them: the device half BLOCKS on
# silence once a block's data runs out, so the read waits until Ctrl-STOP, and
# the TAPIN that was waiting returns CF:
#
#   `cas-cut-link`  the tape ends after line 20's link-LOW byte: the link-high
#                   read blocks -> `ctp_link_err`
#   `cas-cut-body`  the tape ends three bytes into line 10's body -> the next
#                   body read blocks -> `ctp_err_pop`
#
# 🔴 THE FIRST CUT OF `cas-cut-link` REACHED THE WRONG EXIT, AND ONLY A KNIFE
# SAID SO. It kept BOTH link bytes, on the premise that the last byte before the
# silence is never framed (the `twot` note above). On zerobas that byte IS read:
# a knife on `ctp_link_err` moved nothing, while a knife on `ctp_err_pop` moved
# BOTH rows -- the line-number read was the one blocking. Same answer on all
# three sides either way, which is exactly why the reading could not tell.
#
# Every side is expected to report its aborted-load message (`<load-failed>`)
# and return to a working prompt (`:alive`). Both rows are knife-checked
# against the zerobas exit they name.
CUT_PROG = [(10, 'PRINT"ZQ9"'), (20, 'PRINT"ZQ7"')]
CASES_CUTL = [
    ("cas-cut-link", ['10 PRINT"ZQ1"', f'CLOAD"{CAS_NAME}"', W_LOAD, "@BREAK",
                      W_AFTER, f'PRINT"{ALIVE}"'],                     1,
     ((5, "alive", True),)),
]
CASES_CUTB = [
    ("cas-cut-body", ['10 PRINT"ZQ1"', f'CLOAD"{CAS_NAME}"', W_LOAD, "@BREAK",
                      W_AFTER, f'PRINT"{ALIVE}"'],                     1,
     ((5, "alive", True),)),
]

# --- D-CASOPEN: the THIRD reading -- what `FOR OUTPUT` does with a name -------
# 🔴 THE SCREEN CANNOT ANSWER THIS ONE. `OPEN"CAS:WX" FOR OUTPUT` prints nothing
# on any of the three sides whether it records the name, records six spaces, or
# records garbage; the only witness is the TAPE. So these rows run on a RECORDING
# tape (`cassetteplayer new`) and the reading is taken off the recording:
# `probes/lib/cas_decode.py` turns the WAV back into bytes, and the six bytes
# after the ten-byte $EA run ARE the header name. Signal edges only, the same
# decoder on all three sides, no reference disassembly.
#
# Each row needs its OWN boot and its OWN recording (`cassetteplayer new`
# truncates the file at every boot), so unlike the groups above each gets its own
# `run_cases` call -- the shape `basic_probe_lnblank`'s `tape-save` rows use.
#
#   `cas-openout`      a NAMED output file: is the name in the header?
#   `cas-openoutbare`  the bare form: what name does an UNNAMED output file get?
#
# Four readings each: the OPEN line (must print nothing -- no error), `:alive`
# (the machine reached the next prompt and printed), `:tape` (the decoded 6-byte
# header name) and `:data` (the decoded text, up to the Ctrl-Z terminator). The
# last two are what says the tape was WRITTEN, not merely that nothing errored.
_REC_TAIL = [W_HDR, f'PRINT#1,"{REC_TEXT}"', "CLOSE", W_FLUSH,
             f'PRINT"{ALIVE}"']

CASES_REC = [
    ("cas-openout",     ["MAXFILES=1", f'OPEN"CAS:{REC_NAME}" FOR OUTPUT AS #1']
                        + _REC_TAIL,                                   1,
     ((6, "alive", True),)),
    ("cas-openoutbare", ["MAXFILES=1", 'OPEN"CAS:" FOR OUTPUT AS #1']
                        + _REC_TAIL,                                   1,
     ((6, "alive", True),)),
]

# The two readings each recording row takes off the HOST file rather than off the
# screen, in the order `run_rec_group` produces them.
REC_READINGS = ("tape", "data")

# Labels whose SUBJECT line is read with the `SEARCH_ROWS` filter OFF -- for
# these rows the progress line IS the subject, so filtering it would leave them
# measuring nothing at all ([[gate-can-be-green-while-measuring-nothing]]).
# `cas2-opencase` is deliberately NOT here -- see its comment above.
UNFILTERED_SUBJECTS = {"cas2-load", "cas2-merge", "cas2-open", "cas2-cload",
                       "cas2-bare", "cas2-openbare"}

ALL_CASES = CASES + CASES_T2 + CASES_T2T + CASES_CUTL + CASES_CUTB + CASES_REC

# 🔴 THE PINNED DIVERGENCE. Not an agreement row: the three sides are EXPECTED to
# differ, and each side's exact reading is written down so the day any of them
# moves the pin ROTS and this gate fails. This is what keeps `SEARCH_ROWS` from
# being a normalisation that quietly blesses zerobas's silence.
PINNED = {
    # D-CASSEARCH: this row was the pin that said zerobas printed NOTHING. It is
    # re-pinned to the reading the fix produces -- the pin did its job (it ROTS
    # the moment any side moves, which is exactly what closing the divergence
    # does), and re-pinning is a RE-MEASUREMENT, never a loosening: it is still a
    # per-side EXACT match, and it is now the only row in the battery that
    # asserts the search line by VALUE rather than by cross-side agreement.
    "cas-load-plain:search": {
        "vg8020": f"Found:{CAS_NAME}",
        "cf3300": f"Found:{CAS_NAME}",
        "zb":     f"Found:{CAS_NAME}",
    },
    # ✅ D-CASOPEN CLOSED THE SECOND DIVERGENCE, AND ITS TWO PINS ARE GONE FROM
    # HERE ON PURPOSE -- RECLASSIFIED, NOT LOOSENED. `cas2-open` and
    # `cas2-open:echo` pinned `zb='Found:SK'` / `zb='10 PRINT"ZQ8"'` against both
    # references' `Skip :SK / Found:RT` / `10 PRINT"ZQ9"`: OPEN"CAS:name" ignored
    # the name and handed back the WRONG FILE's bytes. basic/files.asm
    # `oo_dev_cas` now captures into CAS_WANT (docs/spec-basic-casopen.md), all
    # three sides read the same thing, and a pin whose three values are IDENTICAL
    # is a hand-written want -- which is the one thing this battery says it does
    # not score by ("the references define the answer"). Both rows therefore join
    # the SCORED set, where they are structurally identical to their three
    # siblings `cas2-load` / `cas2-merge` / `cas2-cload`.
    # 🟢 AND THE STRICTNESS IS REPLACED, NOT DROPPED. `cas2-open:echo` becomes a
    # CONTROL asserting `ZQ9` -- the SECOND file's text. A machine that takes the
    # wrong file reads ZQ8 and fails it; a dead one reads `<nothing>` and fails
    # it. That is the degenerate case a bare agreement row is open to, and it is
    # covered, so neither row is left without positive evidence.
}

# Rows whose agreed reading must additionally carry POSITIVE TEXT: proof that a
# program actually RAN (or, for `cas-load-plain`, that the tape actually
# arrived). Without these the battery is satisfied by machines that do nothing
# at all -- one row expects `<nothing>` and three expect an error message, and a
# dead subject produces both for free.
CONTROLS = {
    "cas-run-hit":            ("ZQ9",),
    "bare-run":               ("ZQ1",),
    "cas-load-plain:listing": ("ZQ9",),
    # 🟢 The two-file tape's four controls. Each is a control of the SKIP: the
    # tape's FIRST file prints ZQ8, so `ZQ9` in the reading says the search
    # stepped over one file and took the next. A machine whose search is broken
    # reads ZQ8, and a dead one reads nothing -- both caught here.
    "cas2-load:listing":      ("ZQ9",),
    "cas2-merge:listing":     ("ZQ9", "ZQ1"),
    "cas2-cload:listing":     ("ZQ9",),
    # D-CASRELOCK: the second of two CLOADs took the SECOND file. A relock that
    # fails keeps the first program (ZQ8); a dead machine reads nothing.
    "cas2-cload2:listing":    ("ZQ9",),
    # D-CLOADPROG: the program CLOAD was run from is GONE -- the tape's RT is
    # what LIST shows. A machine that never loaded lists line 7.
    "cas2-cloadprog:listing": ("ZQ9",),
    # ✅ D-CASOPEN: the fourth verb's control, and the row that used to be half of
    # a pinned divergence (see PINNED). ZQ9 is the SECOND file -- the whole claim
    # of `cas2-open` is that the search stepped over the first.
    "cas2-open:echo":         ("ZQ9",),
    # The bare form takes the FIRST file, so ZQ8 -- not ZQ9 -- is the proof.
    "cas2-bare:listing":      ("ZQ8",),
    # --- D-CASOPEN ---------------------------------------------------------
    # The bare OPEN takes the FIRST file too, so ZQ8 is its proof and ZQ9 would
    # be the failure. `cas2-opencase` answers with an ERROR MESSAGE, which a
    # machine that has stopped answering produces for free, so its liveness half
    # is what says the Ctrl-STOP returned to a working prompt.
    "cas2-openbare:echo":     ("ZQ8",),
    "cas2-opencase:alive":    (ALIVE,),
    # The recording rows. `:tape` and `:data` come off the DECODED tape, so they
    # are the rows that say something was actually WRITTEN -- the screen halves
    # of these two rows are `<nothing>` and would be produced by an OPEN that
    # silently did nothing at all.
    "cas-openout:alive":      (ALIVE,),
    "cas-openout:tape":       (REC_NAME,),
    "cas-openout:data":       (REC_TEXT,),
    "cas-openoutbare:alive":  (ALIVE,),
    # 🔴 NO CONTROL ON `cas-openoutbare:tape`, DELIBERATELY, AND THE REASON IS
    # THAT ITS EXPECTED VALUE CARRIES NO TEXT: an unnamed output file's header
    # name is SIX SPACES, and "the reading contains six spaces" is satisfied by
    # every blank and every failure. Its positive evidence is `:data` from the
    # SAME decode of the SAME recording -- if the WAV decoded to `ZQ7` then the
    # six bytes ahead of it are a real header field and not an absence.
    "cas-openoutbare:data":   (REC_TEXT,),
}

ROWS = 24
COLS = 40


def tail_after(raw, cmdline, failmsg, drop_search=True):
    """Everything `cmdline` printed: the rows between its echo and the NEXT
    prompt or echo. Not `omsx_repl.screen_tail`, for the reason
    `basic_probe_runtail` states: that window ends at a row EQUAL to a prompt,
    which is only correct when the subject is the last line typed -- and here it
    never is (every row carries a trailing `@WAIT`, and two carry a `LIST`).

    Two DISTINCT empty sentinels, never one: `<NO ECHO>` says the apparatus lost
    its anchor and nothing was measured, `<nothing>` says the machine printed
    nothing -- which for one row here IS the answer.
    """
    if raw is None:
        return "<NO CAPTURE>"
    # Row 23 is the SCREEN-0 function-key display, which both references show
    # and zerobas does not.
    rows = [raw[r * COLS:(r + 1) * COLS].strip() for r in range(ROWS)][:-1]
    key = cmdline.strip()
    idx = None
    for i, r in enumerate(rows):
        if r == key or r.endswith(key):
            idx = i                              # keep the LAST occurrence
    if idx is None:
        return "<NO ECHO>"
    # Both fixture names, not just the matched one: on the one-file tape the
    # ABORT rows step over `RT` itself (`RUN"CAS:NOSUCH"` matches nothing), and
    # on the two-file tape the skipped file is `SK`.
    search = [s.format(n=n) for s in SEARCH_ROWS
              for n in (CAS_NAME, SKIP_NAME)]
    out = []
    for r in rows[idx + 1:]:
        if any(r == p or r.startswith(p) for p in omsx_repl.PROMPTS):
            break                                # next prompt, echo or not
        if drop_search and r in search:
            continue        # the pinned search-progress divergence (see PINNED)
        if r:
            out.append(r)
    if not out:
        return "<nothing>"
    # The ONE normalisation, and only when the message is the WHOLE tail.
    return " / ".join(FAILED if r == failmsg else r for r in out)


_TAPE: dict[str, str] = {}


def _tok_file_nopad(name: str, program: bytes) -> bytes:
    """A tokenised .cas file whose data block ends EXACTLY at the program's
    $0000 end-link, with NO trailing in-block padding -- NOT what any CSAVE
    writes (all three machines write SEVEN $00 after the end-link, D-CASRELOCK
    2026-09-28); kept for the D-CASCUT tapes, which are cut on purpose.
    `cas_encode.build_cas_basic` appends 16 $00 pad bytes for
    single-file framing, and on a MULTI-file tape those unread pad bytes leave a
    skipped file mid-block so the next TAPION cannot relock
    (basic/casmatch-body.inc `csd_tok`). The same fixture shape
    `basic_probe_cas_match.tok_file_nopad` builds, for the same reason."""
    return (CAS_SYNC + bytes([BASIC_ID] * 10)
            + name[:6].ljust(6).encode("ascii") + CAS_SYNC + program)


def tape_path(kind: str = "one") -> str:
    """Build (and cache) a cassette fixture.

      `one`  -- the ONE $EA ASCII file every row of `CASES` mounts.
      `two`  -- $EA `SK` then $EA `RT`: the ASCII search has to SKIP one file.
      `twot` -- the tokenised ($D3) twin of `two`, for `CLOAD`.

    🔴 THE TWO TAPES ARE SEPARATE FIXTURES ON PURPOSE, not one tape for
    everything. Putting `SK` in front of `RT` on the shared tape would move all
    nine readings of `CASES` -- every subject row would grow a `Skip :SK` -- for
    a question none of them is asking. `run_cases`' `prologue` applies to a whole
    batch, so each fixture gets its own call (the documented shape).
    """
    if kind not in _TAPE:
        d = tempfile.mkdtemp(prefix=f"zb_castail_{kind}_")
        p = os.path.join(d, f"castail_{kind}.cas")
        if kind == "one":
            blob = build_ascii_cas(CAS_NAME, CAS_PROG)
        elif kind == "two":
            blob = (build_ascii_cas(SKIP_NAME, SKIP_PROG)
                    + build_ascii_cas(CAS_NAME, CAS_PROG))
        elif kind == "twot":
            # ⚠️ THE TWO FILES NEED DIFFERENT FRAMING, AND THE FIRST READING OF
            # THIS FIXTURE PROVED IT. The SKIPPED file must have NO trailing pad
            # (a skip walks the link chain and stops at the $0000 end-link, so
            # unread pad bytes leave the tape mid-block and the next TAPION
            # cannot relock); the MATCHED file must HAVE one, because the device
            # half blocks on silence once a block's data runs out and the loader
            # needs the pad to frame the final byte (cas_encode.build_cas_basic).
            # Built no-pad, BOTH references read the search rows correctly and
            # then never returned to the prompt -- `<NO ECHO>` on the LIST half.
            # 🔴 D-CASRELOCK (2026-09-28): AND THE TWO FRAMINGS WERE BOTH WRONG.
            # CSAVE writes the end-link then SEVEN $00 on every machine measured
            # (scratchpad/csavetail_probe.out) -- the "skipped file has no pad"
            # half was OUR save.asm's claim, never a reference's. On a tape of
            # that shape zerobas's skip left the seven bytes unread and TAPION
            # locked inside them (`load error`). Both files are now built
            # exactly as CSAVE writes them, which is what makes `cas2-cload`
            # and `cas2-cload2` rows about a REAL tape.
            blob = (build_cas_basic_csave(SKIP_NAME, make_multiline_program(
                        [(10, 'PRINT"ZQ8"')], TXTBASE))
                    + build_cas_basic_csave(CAS_NAME, make_multiline_program(
                        [(10, 'PRINT"ZQ9"')], TXTBASE)))
        elif kind in ("cutl", "cutb"):
            # D-CASCUT: the program image, cut. Line 10's length is its own
            # link word minus the text base.
            prog = make_multiline_program(CUT_PROG, TXTBASE)
            len1 = (prog[0] | prog[1] << 8) - TXTBASE
            keep = len1 + 1 if kind == "cutl" else 4 + 3
            blob = _tok_file_nopad(CAS_NAME, prog[:keep])
        else:
            raise ValueError(kind)
        with open(p, "wb") as f:
            f.write(blob)
        _TAPE[kind] = p
    return _TAPE[kind]


def tape_readback(wav):
    """(header name, text) actually WRITTEN, decoded from the recording.

    Two DISTINCT apparatus sentinels, and both start with `<NO ` / `<BAD ` so the
    scorer's own rule ("an apparatus sentinel is NEVER agreement") catches them:
    two sides that both fail to record must not read as a reading they share.
    """
    if not os.path.exists(wav) or os.path.getsize(wav) < 1024:
        return "<NO TAPE>", "<NO TAPE>"
    try:
        data, _info = cas_decode.decode_file(wav)
    except Exception as exc:                                # pragma: no cover
        return f"<BAD WAV {exc}>", "<BAD WAV>"
    blob = bytes(data)
    run = bytes([ASCII_ID] * 10)
    i = blob.find(run)
    if i < 0:
        return "<NO $EA HEADER>", "<NO $EA HEADER>"
    j = i + len(run)
    name = blob[j:j + 6].decode("latin-1")
    body = blob[j + 6:]
    k = body.find(b"\x1a")                    # Ctrl-Z ends the ASCII text
    text = (body[:k] if k >= 0 else body).decode("latin-1")
    return name, " / ".join(t for t in text.split("\r\n") if t) or "<nothing>"


# (fixture kind, the rows that mount it) -- one `run_cases` call each.
GROUPS = (("one", CASES), ("two", CASES_T2), ("twot", CASES_T2T),
          ("cutl", CASES_CUTL), ("cutb", CASES_CUTB))


def run_side(side, only):
    out = {}
    for kind, group in GROUPS:
        run_group(side, only, kind, group, out)
    for row in CASES_REC:
        run_rec_group(side, only, row, out)
    return out


def run_rec_group(side, only, row, out):
    """One recording row: its own boot, its own `cassetteplayer new` tape.

    🔴 ONE ROW PER CALL IS NOT TIDINESS. `cassetteplayer new` is a PROLOGUE, and
    a prologue applies to the whole `run_cases` batch -- and it TRUNCATES the
    file at every boot. Two recording rows sharing one call would leave one
    recording on disk and both rows would read it.
    """
    label, lines, subj, extra = row
    if only and not any(label.startswith(o) for o in only):
        return out
    cfg = SIDES[side]
    kw = {}
    if cfg["diska"]:
        if not os.path.exists(TEST_DSK):
            for name in [label] + [f"{label}:{n}" for _, n, _ in (extra or ())] \
                    + [f"{label}:{n}" for n in REC_READINGS]:
                out[name] = "<NO DISK FIXTURE>"
            return out
        dsk = probe_tmp.tmp(f"zb_castail_{side}_{label}.dsk")
        shutil.copy(TEST_DSK, dsk)
        kw["diska"] = dsk
    wav = os.path.join(tempfile.mkdtemp(prefix=f"zb_castail_rec_{side}_"),
                       f"{label}.wav")
    caps = omsx_repl.run_cases(
        cfg["machine"], [("direct", list(cfg["reset"]) + list(lines))],
        batch=False, reset=(),
                # 🔴 BOOT-PER-CASE IS LOAD-BEARING — MEASURED (D-BATCH2,
                # 2026-09-01). `scratchpad/batchcheck.py` ran it both ways and
                # the two modes DISAGREE ON PASS/FAIL (rc 2 batched vs 0
                # boot-per-case): the cassette tail state does not survive being
                # shared. Refused rather than converted.
                 boot=cfg["boot"], step=cfg["step"],
        prologue=(f"cassetteplayer new {{{wav}}}",), **kw)
    raw = caps[0]
    out[label] = tail_after(raw, lines[subj], cfg["failmsg"])
    for i, name, drop in (extra or ()):
        out[f"{label}:{name}"] = tail_after(raw, lines[i], cfg["failmsg"],
                                            drop_search=drop)
    tape, text = tape_readback(wav)
    out[f"{label}:tape"] = tape
    out[f"{label}:data"] = text
    return out


def run_group(side, only, kind, group, out):
    cfg = SIDES[side]
    rows = [c for c in group if not only or any(c[0].startswith(o)
                                                for o in only)]
    if not rows:
        return out
    kw = {}
    if cfg["diska"]:
        # ⚠️ A /tmp COPY, never the committed image. Nothing here writes to a
        # disk, but a probe that hands openMSX the repo's own .dsk is one bug
        # away from mutating a committed artifact. The CF-3300 and the repack
        # machine both boot into Disk BASIC with a drive attached; the tape
        # verbs under test are main-ROM verbs either way.
        if not os.path.exists(TEST_DSK):
            for label, *_ in rows:
                out[label] = "<NO DISK FIXTURE>"
            return out
        dsk = probe_tmp.tmp(f"zb_castail_{side}_{kind}.dsk")
        shutil.copy(TEST_DSK, dsk)
        kw["diska"] = dsk
    cases = [("direct", list(cfg["reset"]) + list(lines))
             for _, lines, _, _ in rows]
    caps = omsx_repl.run_cases(
        cfg["machine"], cases, batch=False, reset=(), boot=cfg["boot"], step=cfg["step"],
        prologue=(f"cassetteplayer insert {{{tape_path(kind)}}}",), **kw)
    for (label, lines, subj, extra), raw in zip(rows, caps):
        out[label] = tail_after(raw, lines[subj], cfg["failmsg"],
                                drop_search=label not in UNFILTERED_SUBJECTS)
        for i, name, drop in (extra or ()):
            out[f"{label}:{name}"] = tail_after(raw, lines[i], cfg["failmsg"],
                                                drop_search=drop)
    return out


def labels_of(row):
    label, _, _, extra = row
    names = [n for _, n, _ in (extra or ())]
    if any(row is r for r in CASES_REC):
        names += list(REC_READINGS)     # the two HOST-file readings
    return [label] + [f"{label}:{n}" for n in names]


# The label pad for every report row this probe prints, on every exit path.
# docs/spec-probe-rowshape.md: ONE grammar, so a knife runner's baseline taken on
# one path can be read against another.
LABEL_W = 22


# --- control_faults: ONLY A REFERENCE CAN SAY THE APPARATUS IS BROKEN --------
# 🔴 THIS USED TO SCAN EVERY SIDE, AND THAT MADE THE BATTERY UNABLE TO MEASURE ITS
# OWN KNIVES (D-FNRUN, 2026-08-21). K-FR3 cut exactly what it aimed at --
# `cas-run-hit` went `ZQ9` -> `<load-failed>` -- and because that row is a POSITIVE
# CONTROL the probe printed "33 printed, 0 scored -- NOT MEASURED" and exited 2. A
# knife is SUPPOSED to break things; a battery that reads any control failure as a
# broken instrument cannot score one.
#
# 🎯 `basic_probe_namspc.py`:1036 already had the right rule and is the precedent:
# a control that fails on `zb` is a FINDING and is scored like any other row, while
# a control that fails on a REFERENCE means the fixture, the ROMs or the cassette
# are wrong and nothing below it can be believed. The controls exist because a
# machine that runs no program at all produces `<nothing>` and an error message for
# free -- and that argument is about the REFERENCE side, which is what defines the
# answer here.
#
# ⚠️ A zb control failure is now SCORED, so it counts in the agree/diverge tally and
# the run exits non-zero through the ORDINARY path. Exit 2 keeps its meaning: the
# instrument was broken, not a regression.
def control_faults(results, sides, controls):
    """(lab, side, got, missing) for REFERENCE sides only. `zb` is never a fault."""
    out = []
    for lab, want in controls.items():
        for s in sides:
            if s == "zb":
                continue                          # a zerobas miss is a RESULT
            got = results[s].get(lab)
            if got is None:
                continue                          # excluded by --only
            miss = [w for w in want if w not in got]
            if miss:
                out.append((lab, s, got, miss))
    return out


def _selftest() -> int:
    """Plant control readings and check WHICH SIDE decides. No machine booted."""
    ctl = {"cas-run-hit": ["ZQ9"]}
    cases = [
        ("zb misses, reference fine -> a FINDING, scored below",
         {"cf3300": {"cas-run-hit": "ZQ9"}, "zb": {"cas-run-hit": "<load-failed>"}}, 0),
        ("reference misses -> the INSTRUMENT, exit 2",
         {"cf3300": {"cas-run-hit": "<load-failed>"}, "zb": {"cas-run-hit": "ZQ9"}}, 1),
        ("both miss -> still the instrument, only the reference listed",
         {"cf3300": {"cas-run-hit": "<x>"}, "zb": {"cas-run-hit": "<y>"}}, 1),
        ("both fine -> no fault",
         {"cf3300": {"cas-run-hit": "ZQ9"}, "zb": {"cas-run-hit": "ZQ9"}}, 0),
    ]
    rc = 0
    for name, results, want in cases:
        got = len(control_faults(results, ["cf3300", "zb"], ctl))
        good = got == want
        rc |= (not good)
        print(f"  {'ok ' if good else 'RED'} {name:56} faults={got} want={want}")
    print("castail selftest:", "PASS" if not rc else "FAIL")
    return rc


def main() -> int:
    ap = argparse.ArgumentParser(description="D-CASTAIL")
    ap.add_argument("--selftest", action="store_true",
                    help="check WHICH SIDE decides a control failure, on planted "
                         "readings -- no machine booted")
    ap.add_argument("--sides", default="cf3300,zb")
    ap.add_argument("--only", default="")
    ap.add_argument("--repeat", type=int, default=1)
    ap.add_argument("--gate", action="store_true",
                    help="exit 1 unless every row agrees across sides")
    a = ap.parse_args()
    if a.selftest:
        return _selftest()

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

    present = [lab for row in ALL_CASES for lab in labels_of(row)
               if any(lab in results[s] for s in sides)]
    scored = [lab for lab in present if lab not in PINNED]
    pins = [lab for lab in present if lab in PINNED]

    print("D-CASTAIL — what a machine prints after RUN\"CAS:x\" / "
          f"LOAD\"CAS:x\",R   sides: {', '.join(sides)}")
    print("=" * 78)

    # --- the POSITIVE controls, first and gating ---------------------------
    bad = control_faults(results, sides, CONTROLS)
    if bad:
        for lab, s, got, miss in bad:
            print(probe_report.row("FAIL", lab, LABEL_W, {s: got},
                                   "   [POSITIVE CONTROL]"))
            print(f"        wanted {miss} in the reading")
        print("\n*** A POSITIVE CONTROL FAILED ON A REFERENCE, so nothing below "
              "it was measured.\n"
              "    ONE row here expects `<nothing>` and THREE expect an error "
              "message, and a\n"
              "    machine that runs no program at all produces both for free "
              "-- `make\n"
              "    fat-error-acceptance` once scored 8/8 on an all-$00 "
              "build/disk.rom. These\n"
              "    controls are the positive text that says a program REACHED "
              "the screen.\n"
              "    Check build/*.rom, `make repack-machine` and the cassette "
              "fixture, THEN\n"
              "    re-read the rows. Exit 2 (not 1) = the instrument was "
              "broken, NOT a\n"
              "    regression.")
        for lab in present:
            vals = {s: results[s][lab] for s in sides if lab in results[s]}
            print(probe_report.row("....", lab, LABEL_W, vals, "   (not scored)"))
        print(probe_report.footer(len(bad) + len(present), 0,
                                  "NOT MEASURED (a positive control failed)"))
        return 2

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
        print(f"{len(scored)} row(s) measured on {sides[0]} — "
              "CHARACTERIZATION, no agreement verdict is possible from one side")
        if a.gate:
            sys.stderr.write("castail: --gate needs at least two sides\n")
            return 2
        return 0

    agree = dis = 0
    for lab in scored:
        vals = {s: results[s][lab] for s in sides if lab in results[s]}
        ok = len(set(vals.values())) == 1 and len(vals) > 1
        if any(v.startswith("<NO ") or v.startswith("<BAD ")
               for v in vals.values()):
            ok = False                # an apparatus sentinel is NEVER agreement
        agree += ok
        dis += not ok
        note = "   [CONTROL]" if lab in CONTROLS else ""
        print(probe_report.row("ok" if ok else "DIFF", lab, LABEL_W, vals, note))
    # --- the PINNED divergence rows: each side against its OWN written-down
    # reading, never against another side. A pin that still reads what it was
    # pinned at is not agreement -- it is a divergence that has not moved.
    rotted = []
    for lab in pins:
        want = PINNED[lab]
        vals = {s: results[s][lab] for s in sides if lab in results[s]}
        bad = {s: v for s, v in vals.items() if want.get(s) != v}
        rotted += [(lab, s, want.get(s), v) for s, v in bad.items()]
        print(probe_report.row("PIN" if not bad else "ROT", lab, LABEL_W, vals,
                               "   [PINNED DIVERGENCE]"))
    for lab, s, want, got in rotted:
        print(f"      ROTTED [{s}] pinned {want!r}, read {got!r}")

    print(probe_report.footer(len(scored) + len(pins), len(scored),
                              f"{agree} agree, {dis} diverge, "
                              f"{len(pins)} pinned"))
    print("=" * 78)
    print(f"{agree}/{agree + dis} scored readings agree "
          f"({len(ALL_CASES)} cases, {len(CONTROLS)} positive controls, "
          f"{len(pins)} pinned divergence row(s))")
    print(f"SIDES: {','.join(SIDES)} — every MSX1 has a CASSETTE PORT, so "
          "unlike the disk battery the VG-8020 is a legitimate reference here")
    print(f"NORMALISED: a tail that is EXACTLY the side's own aborted-load "
          f"message reads {FAILED!r} "
          f"({', '.join(f'{s}={SIDES[s]['failmsg']!r}' for s in SIDES)}) — "
          "the quarantined wording divergence, not re-opened here")
    print(f"PINNED: the tape-search progress rows "
          f"({', '.join(repr(s.format(n=CAS_NAME)) for s in SEARCH_ROWS)}, and "
          f"the same pair for {SKIP_NAME!r}) are dropped from the D-CASTAIL "
          "tails, where they are not the subject, and read UNFILTERED by every "
          "cas2-* row, where they are. All three sides print them since "
          "D-CASSEARCH, so the filter now normalises an AGREEMENT rather than "
          "blessing one machine's silence")
    if a.gate and (dis or rotted):
        if dis:
            sys.stderr.write(f"castail: {dis} reading(s) diverge\n")
        if rotted:
            sys.stderr.write(
                f"castail: {len(rotted)} pinned reading(s) ROTTED -- a "
                "divergence this battery deliberately does not score has "
                "MOVED, so the filter above is no longer describing the "
                "machines. Re-measure and re-pin.\n")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
