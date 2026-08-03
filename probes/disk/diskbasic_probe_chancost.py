#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Characterize -- and now GATE -- what ONE FILE CHANNEL COSTS on an MSX1.

Originally the question was: zerobas spends 562 B per channel and caps at
FCH_CEIL=2; what does the reference actually spend, and what is its ceiling?
Answer: 267 B/channel, dynamically, ceiling exactly 15. D-FCH then made zerobas
use the SAME MECHANISM -- carved out of the FRE(0) pool at MAXFILES time,
ceiling 15 -- at its own honest 50 B/channel (a zerobas block IS 50 B; its
sector staging is the shared FSECTOR_BUF write-back cache, so it charges what it
uses rather than padding to match a number).

So this is now an ACCEPTANCE GATE. It returns non-zero on oracle drift, on any
divergence not in the explicit KNOWN_DIVERGE allowlist (each entry naming the
item that owns it), and on the mechanism assertions: per-channel, LINEAR, with a
ceiling of 15, on BOTH machines.

⚠️ WHY THIS PROBE EXISTS RATHER THAN AN `omsx_repl` BATTERY. The earlier attempt
read `<none>` on every row and was mis-read as "the CF-3300 won't answer". It is
an APPARATUS failure: `omsx_repl` scrapes the SCREEN 0 name table at VRAM $0000
at 40 columns (probes/lib/omsx_repl.py SCR_ADDR/COLS, whose comment already
flags this), but **CF-3300 Disk BASIC boots to SCREEN 1** — measured here, not
assumed: `scrmod=$01`, `linlen=$1d` (29), name table **$1800 at 32 columns**.
This probe reads the geometry out of RAM and picks the name table from it, so it
works on both machines.

⚠️ EVERY ROW IS ECHO-GUARDED (`echo_missing`, ported from
diskbasic_probe_lof.py). A typed line that is not on screen returns MANGLED,
which is fatal and which SUPPRESSES the derived slope/ceiling/headline. This
probe types at the very 4.5 s cadence at which D-LOF measured the CF-3300
dropping whole chunks of a line and zerobas doubling its first character, and a
mangled line earns a COMPLETELY REAL error message — so without the guard it
would read as an `FRE(0)` finding, an oracle drift or a divergence, never as an
apparatus failure. Stability across many sessions is not attribution.

⚠️ `FRE(0)` IS IMPURE — it counts down to the STACK POINTER, and every extra
expression-nesting level costs 6 bytes (docs/binfre-vg8020-characterization.md
§3.1). Every reading below is therefore the byte-identical expression
`PRINT FRE(0)` at identical depth. Do not "simplify" one row's expression.

CONTROLS (a ladder this clean is exactly when to try hardest to falsify it):
  * `ctl_syntax` types a misspelled keyword and MUST show `Syntax error` — if it
    comes back clean the harness is not typing and every number here is worthless.
    ⚠️ BUT IT FAILS TOWARD "PASS", WHICH IS WHY THE ECHO GUARD IS NOT OPTIONAL:
    a MANGLED line also earns a `Syntax error`, so a `ctl_syntax` row that never
    received its line still reads SYNTAX, still matches its oracle, still
    compares equal across the machines and still prints `agree`. The control that
    proves the harness is typing cannot notice the harness NOT typing. Only
    `echo_missing` can, and it runs before this value is read;
  * `ctl_noop` types `REM MAXFILES=8`: echoed, parsed, and MUST NOT move FRE(0)
    — so the ladder's movement is attributable to the statement, not the typing;
  * note `MAXFILES=1` reads the SAME as an untouched boot because 1 IS the Disk
    BASIC default — that row CANNOT distinguish "the statement ran" from "the
    line was never typed", and is not load-bearing. The rows that carry the
    result are 0/2/3/4/8/15, which all move.

CLEAN-ROOM: black-box only — typed BASIC in, screen + documented sysvars out.
No reference ROM is read or disassembled.

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
import subprocess
import tempfile
import time
# --- zerobas: the openMSX preflight guard (probes/lib) ---
import os as _zbo, sys as _zbs  # noqa: E402
_zbs.path.insert(0, _zbo.path.join(_zbo.path.dirname(
    _zbo.path.dirname(_zbo.path.abspath(__file__))), "lib"))
import omsx_preflight  # noqa: E402

OMSX = shutil.which("openmsx") or "/Applications/openMSX.app/Contents/MacOS/openmsx"
SRC_DSK = os.path.join(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))), "disk", "test720.dsk")

# side -> (machine, has-date-prompt, boot instant in emulated seconds, prompt).
# ⚠️ The PROMPT is what the echo guard anchors on, and it must be exact: the
# reference echoes a typed line at the start of its own row (after the SCREEN 1
# left margin, which the guard squeezes away), while zerobas prints "ZB" and
# echoes on the same row. Anchoring on it is what makes an INSERTED character
# visible -- a plain substring test passes `ZBPPRINT FRE(0)` because the correct
# text is still in there. If a prompt ever changes, every row fails loudly, which
# is the right direction for a guard to break in.
MACHINES = {
    "ref": ("National_CF-3300", True, 12.0, ""),
    "zb":  (os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK"),
            False, 8.0, "ZB"),
}

# label -> typed lines. Keep <= 6 lines: the 24-row screen scrolls.
CASES = [
    ("ctl_syntax", ["MAXFILEZ=2", "PRINT FRE(0)"]),
    ("ctl_noop",   ["REM MAXFILES=8", "PRINT FRE(0)"]),
    ("boot",  ["PRINT FRE(0)"]),
    ("mf0",   ["MAXFILES=0", "PRINT FRE(0)"]),
    ("mf1",   ["MAXFILES=1", "PRINT FRE(0)"]),
    ("mf2",   ["MAXFILES=2", "PRINT FRE(0)"]),
    ("mf3",   ["MAXFILES=3", "PRINT FRE(0)"]),
    ("mf4",   ["MAXFILES=4", "PRINT FRE(0)"]),
    ("mf8",   ["MAXFILES=8", "PRINT FRE(0)"]),
    ("mf15",  ["MAXFILES=15", "PRINT FRE(0)"]),
    ("mf16",  ["MAXFILES=16", "PRINT FRE(0)"]),
    ("mf255", ["MAXFILES=255", "PRINT FRE(0)"]),
    # is the buffer charged when the channel is DECLARED or when it is OPENED?
    ("open_after", ["MAXFILES=2", 'OPEN "ZQ.DAT" FOR OUTPUT AS #1', "PRINT FRE(0)"]),
    # which pool pays? (FRE("") is the string pool -- a separate allocator)
    ("str0",  ["MAXFILES=0", 'PRINT FRE("")']),
    ("str8",  ["MAXFILES=8", 'PRINT FRE("")']),
    # incidental, kept because the cost pass found it: LOF on a fresh OUTPUT
    # channel. `lof_existing` is its two-sided control -- it MUST agree (26).
    ("lof_new",      ['OPEN "ZQ.DAT" FOR OUTPUT AS #1', "PRINT LOF(1)"]),
    ("lof_existing", ['OPEN "HI.TXT" FOR INPUT AS #1', "PRINT LOF(1)"]),

    # --- SEMANTICS battery: what MAXFILES must DO, for the dynamic-allocation
    # spec. Reallocating the channel table moves the top of the pool, so these
    # ask what the reference does to everything living under it. Measured, not
    # assumed -- the spec's behaviour section is written from these rows.
    ("sem_var",     ["A=5", "MAXFILES=2", "PRINT A"]),            # vars survive?
    ("sem_var_ctl", ["A=5", "REM MAXFILES=2", "PRINT A"]),        # ...control
    # ⚠️ `PRINT A$` was the original form and it is UNMEASURABLE: a cleared A$
    # prints an empty line, which this probe's readout scores as `<none>` -- and
    # `<none>` on BOTH sides compares EQUAL and reports PASS whether or not
    # either machine ran the statement (the clearpool-slice trap). LEN(A$) puts
    # a NUMBER on the screen, so the row can actually fail.
    ("sem_str",     ['A$="XY"', "MAXFILES=2", "PRINT LEN(A$)"]),  # strings survive?
    ("sem_str_ctl", ['A$="XY"', "REM MAXFILES=2", "PRINT LEN(A$)"]),  # ...control
    ("sem_same",    ["A=5", "MAXFILES=1", "PRINT A"]),            # no-change reallocs?
    ("sem_reopen",  ["MAXFILES=2", 'OPEN "HI.TXT" FOR INPUT AS #1',
                     "MAXFILES=2", "PRINT LOF(1)"]),              # open chan survives?
    ("sem_zero",    ["MAXFILES=0", 'OPEN "HI.TXT" FOR INPUT AS #1']),   # 0 = no I/O?
    ("sem_hinum",   ["MAXFILES=1", 'OPEN "HI.TXT" FOR INPUT AS #2']),   # #n > MAXFILES
    ("sem_clear",   ["CLEAR 500", "MAXFILES=2", 'PRINT FRE("")']),      # pool kept?

    # --- RESERVATION battery (D-FCH §3.2). ⚠️ THE LADDER ABOVE CAN BE GREEN
    # WHILE MEASURING NOTHING: it reads FRE(0), which is what the interpreter
    # SAYS is left, and a build that subtracted the channel table from the
    # REPORT but not from the ALLOCATOR'S CEILING would produce a perfect
    # 50 B/channel slope while reserving nothing at all — the arrays would grow
    # straight through the table and be shredded by the next channel switch.
    # These two rows close that hole, and they are TWO-SIDED on purpose:
    #   dim_fits — ask for FRE(0) MINUS 800 B: must succeed on both machines.
    #              (Guards the other direction: a build that reported the floor
    #              while allocating against the lower ceiling would OOM here.)
    #   dim_over — ask for FRE(0) PLUS 400 B: must raise Out of memory.
    # The overshoot is chosen against the FAILURE it must catch, not for round
    # numbers: at MAXFILES=15 an unreserved zerobas table is 750 B of slack, so
    # 400 B of overshoot lands INSIDE it and would silently succeed. Both rows
    # size themselves from the machine's OWN FRE(0), so they are a real
    # differential rather than a zerobas-only constant.
    ("dim_fits", ["10 MAXFILES=15", "20 N=INT(FRE(0)/2)-400", "30 DIM A%(N)",
                  "40 PRINT 7777", "RUN"]),
    ("dim_over", ["10 MAXFILES=15", "20 N=INT(FRE(0)/2)+200", "30 DIM A%(N)",
                  "40 PRINT 7777", "RUN"]),

    # --- ERR CODES. The spec needs the NUMBERS, and they are disk-range codes
    # well above zerobas's err_msgtab (which stops at 25). Trapped with
    # ON ERROR/ERR so the code is read, not inferred from the message wording.
    ("err_over",    ["10 ON ERROR GOTO 100", "20 MAXFILES=16", "30 END",
                     "100 PRINT ERR", "RUN"]),
    ("err_badchan", ["10 ON ERROR GOTO 100", "20 MAXFILES=1",
                     '30 OPEN "HI.TXT" FOR INPUT AS #2', "40 END",
                     "100 PRINT ERR", "RUN"]),
    ("err_notopen", ["10 ON ERROR GOTO 100", "20 PRINT LOF(1)", "30 END",
                     "100 PRINT ERR", "RUN"]),

    # --- S-FCH-2 ERR 52/59, UNCONFOUNDED. ⚠️ `err_badchan` above was read by
    # spec §5c as "ERR 52 is not trappable" and a forced-abort raiser (ONEFLG:=1,
    # left set) was specced on that reading. IT IS A CONFOUND: the row types
    # `MAXFILES=1` BETWEEN the ON ERROR and the failing OPEN, and MAXFILES --
    # like a plain CLEAR -- DISARMS the handler on the reference (mf_disarm /
    # clr_disarm below, each with a two-sided control). With nothing in between,
    # ERR 52 traps like any other code. These rows raise 52 two ways that touch
    # no MAXFILES at all, and 59 likewise, so what they measure is the CODE.
    ("bfn_trap",  ["10 ON ERROR GOTO 100", '20 OPEN "HI.TXT" FOR INPUT AS #2',
                   "30 END", "100 PRINT 7000+ERR", "RUN"]),   # #2 > default MAXFILES=1
    ("bfn_zero",  ["10 ON ERROR GOTO 100", '20 OPEN "HI.TXT" FOR INPUT AS #0',
                   "30 END", "100 PRINT 7000+ERR", "RUN"]),   # #0 is out of range always
    ("fno_eof",   ["10 ON ERROR GOTO 100", "20 B=EOF(1)",
                   "30 END", "100 PRINT 7000+ERR", "RUN"]),   # EOF, not just LOF
    # ...and the two-sided control that makes those three mean anything: the SAME
    # shape with a known-trappable code must read 7005 on both machines. Without
    # it, a build where NO handler ever fires would score all three "agree" on
    # the abort text. (gate-can-be-green-while-measuring-nothing)
    ("bfn_ctl",   ["10 ON ERROR GOTO 100", "20 B=SQR(-1)",
                   "30 END", "100 PRINT 7000+ERR", "RUN"]),

    # --- the DISARM finding itself, filed as a gate row so it cannot be lost.
    # Reference: MAXFILES (and CLEAR) disarm an armed ON ERROR handler; zerobas
    # does not. Each has its own two-sided control with the statement REMmed out,
    # which must trap on both machines -- otherwise the disarm row is measuring
    # "this program never traps at all".
    ("mf_disarm", ["10 ON ERROR GOTO 100", "20 MAXFILES=1", "30 B=SQR(-1)",
                   "40 END", "100 PRINT 7777", "RUN"]),
    ("mf_ctl",    ["10 ON ERROR GOTO 100", "20 REM MAXFILES=1", "30 B=SQR(-1)",
                   "40 END", "100 PRINT 7777", "RUN"]),
    ("clr_disarm", ["10 ON ERROR GOTO 100", "20 CLEAR", "30 B=SQR(-1)",
                    "40 END", "100 PRINT 7777", "RUN"]),
    ("clr_ctl",    ["10 ON ERROR GOTO 100", "20 REM CLEAR", "30 B=SQR(-1)",
                    "40 END", "100 PRINT 7777", "RUN"]),

    # --- D-MFDOM: the MAXFILES ARGUMENT DOMAIN (docs/spec-basic-maxfiles-domain.md).
    # ⚠️ `mf16`/`mf255` are the ONLY reject rows above, and BOTH have a zero high
    # byte -- so both land on the SAME arm of ex_maxfiles (basic/files.asm):
    #
    #       ld a,d / or a  / jp nz,gb_illegal   <-- arm A: NEVER EXECUTED by any
    #       ld a,e / cp 16 / jp nc,gb_illegal   <-- arm B: what 16 and 255 hit
    #                                                test, on either machine
    #
    # and ex_maxfiles reaches its argument through `eval` (expr.asm), NOT through
    # get_byte_arg. get_byte_arg is the reference-faithful path -- int16 check
    # first (ERR 6 Overflow), then the 0..255 test (ERR 5). `eval`'s own header
    # says "unsigned 16-bit, low-word on overflow" and has no int16 stage at all,
    # so 65536 could WRAP TO 0 and be SILENTLY ACCEPTED. Measured, not argued.
    #
    # Every accept-side row asks `PRINT FRE(0)` so an accepted value is read off
    # the SAME ladder as mf0..mf15 -- the row then distinguishes WHICH value was
    # accepted instead of merely reporting "no error". 1.5 truncating to 1 and
    # 1.5 rounding to 2 are different numbers; a row that could not tell them
    # apart would agree for either reason.
    ("mfd_300",   ["MAXFILES=300", "PRINT FRE(0)"]),      # arm A, first row ever
    ("mfd_65536", ["MAXFILES=65536", "PRINT FRE(0)"]),    # the wrap: accept or raise?
    ("mfd_70000", ["MAXFILES=70000", "PRINT FRE(0)"]),    # >int16, not a power of 2
    ("mfd_neg",   ["MAXFILES=-1", "PRINT FRE(0)"]),       # negative
    ("mfd_neg16", ["MAXFILES=-16", "PRINT FRE(0)"]),      # negative, in-range magnitude
    # --- the FRACTIONAL rows: truncate or round? Two corrections are baked in.
    #
    # ⚠️ 2.5, NOT 1.5. `MAXFILES=1.5` was typed first and read 23430 on the
    # reference -- which is mf1, and 1 IS THE BOOT DEFAULT, so that cell cannot
    # separate "1.5 truncated to 1" from "the statement did nothing at all". It
    # is the same hole this probe's header already flags for the `mf1` row.
    #
    # ⚠️ AND THE READOUT IS NOT FRE(0). Absolute FRE(0) is not comparable between
    # machines (different RAM maps -- that is why the ladder rows are COMPARE
    # "absfre", i.e. informational), so a fractional row read off FRE(0) would
    # gate NOTHING on zerobas: it would print "informational" and the truncation
    # rule -- the entire point of the row -- would go unmeasured on the very
    # machine under test. Both rows therefore read out through the CHANNEL-NUMBER
    # range instead, which is a CLASS on both machines:
    #   mfd_frac   -- 2.5 truncates to 2 => #3 is Bad file number;
    #                 2.5 rounds   to 3 => #3 opens and 7777 prints.
    #   mfd_frac15 -- 15.9 truncates to 15 => accepted, 7777 prints;
    #                 15.9 rounds   to 16 => over the ceiling, IFC.
    ("mfd_frac",  ["MAXFILES=2.5", 'OPEN "HI.TXT" FOR INPUT AS #3',
                   "PRINT 7777"]),
    # ...and its GREEN CONTROL: the identical shape with an INTEGER 3. It must
    # read 7777 on both machines, or mfd_frac's BFN is measuring "#3 cannot be
    # opened here" rather than "2.5 truncated".
    ("mfd_frac_ctl", ["MAXFILES=3", 'OPEN "HI.TXT" FOR INPUT AS #3',
                      "PRINT 7777"]),
    ("mfd_frac15", ["MAXFILES=15.9", "PRINT 7777"]),      # fractional AT the boundary
    # over-ceiling reached by an EXPRESSION rather than a literal -- paired with
    # mf16 as its control: if 8+8 reads differently from 16, the divergence is in
    # the hand-off from eval, not in the domain test.
    ("mfd_expr",  ["MAXFILES=8+8", "PRINT FRE(0)"]),
    # the SYNTAX arm, and the green control for the whole battery: it proves the
    # IFC readings above are a DOMAIN verdict and not the machine erroring at
    # everything typed at it.
    ("mfd_noeq",  ["MAXFILES 2", "PRINT FRE(0)"]),

    # --- the int16 BOUNDARY, both sides of it, both signs. These pin the
    # DENOMINATOR OF THE FIX rather than of the defect: mfd_65536/mfd_70000 show
    # THAT out-of-int16 is mishandled, these four show WHERE the line is, so a
    # fix cannot land one off and still score green on the two rows that found it.
    # get_byte_arg's own header records the reference rule as the RANGE
    # -32768..32767 (not the magnitude |x| <= 32767), verified on the VG-8020 at
    # CHR$(-32768) vs CHR$(-32769). These rows ask whether MAXFILES sits on that
    # same boundary on the CF-3300 -- measured, not inherited from another verb.
    ("mfd_32767",  ["MAXFILES=32767", "PRINT FRE(0)"]),   # in int16, >15  -> IFC?
    ("mfd_32768",  ["MAXFILES=32768", "PRINT FRE(0)"]),   # just OUT       -> OVF?
    ("mfd_n32768", ["MAXFILES=-32768", "PRINT FRE(0)"]),  # in int16 (range) -> IFC?
    ("mfd_n32769", ["MAXFILES=-32769", "PRINT FRE(0)"]),  # just OUT       -> OVF?
]

# The reference's own recorded answers. Re-checking that the oracle still
# reproduces these is what makes it an oracle (memory: validate-oracle-artifacts).
# value = the last integer printed, or an error string seen on screen.
REF_EXPECT = {
    "ctl_syntax": "SYNTAX",
    "ctl_noop":   23430,
    "boot":       23430,
    "mf0":        23697,
    "mf1":        23430,
    "mf2":        23163,
    "mf3":        22896,
    "mf4":        22629,
    "mf8":        21561,
    "mf15":       19692,
    "mf16":       "IFC",
    "mf255":      "IFC",
    "open_after": 23163,
    "str0":       200,
    "str8":       200,
    "lof_new":    0,
    "lof_existing": 26,
    # semantics battery (§9 of the characterization)
    "sem_var":     0,        # MAXFILES CLEARS variables
    "sem_var_ctl": 5,        # ...and the control proves the statement did it
    "sem_same":    0,        # ...even when the value does not change
    "sem_str":     0,        # ...strings too (LEN, not PRINT A$ -- see the case)
    "sem_str_ctl": 2,        # ...and its two-sided control keeps "XY"
    "sem_reopen":  "FNO",    # ...and CLOSES open channels
    "sem_zero":    "BFN",    # MAXFILES=0 -> OPEN is Bad file number
    "sem_hinum":   "BFN",    # #n above MAXFILES -> Bad file number
    "sem_clear":   500,      # ...but the CLEAR-set string pool size SURVIVES
    # reservation battery (D-FCH §3.2) -- FRE(0) is HONEST about the allocator
    "dim_fits":    7777,     # FRE(0)-800 B of array fits
    "dim_over":    "OOM",    # FRE(0)+400 B of array does not
    # error CODES, trapped via ON ERROR/ERR (§10 of the characterization)
    "err_over":    5,        # MAXFILES=16 -> ERR 5 Illegal function call
    "err_badchan": "BFN",    # ...prints `Bad file number in 30` PAST the handler --
                             # because line 20's MAXFILES DISARMED it (mf_disarm),
                             # NOT because ERR 52 is untrappable (bfn_trap)
    "err_notopen": 59,       # LOF on a closed channel -> ERR 59 File not OPEN
    # S-FCH-2 unconfounded (recorded 2026-07-29): ERR 52 and ERR 59 both TRAP.
    "bfn_trap":    7052,
    "bfn_zero":    7052,
    "fno_eof":     7059,
    "bfn_ctl":     7005,     # the two-sided control: a known-trappable code
    # the disarm finding: MAXFILES and CLEAR both disarm; the controls both trap.
    "mf_disarm":   "IFC",    # handler did NOT run -> the S1 abort text instead
    "mf_ctl":      7777,     # ...and with MAXFILES REMmed out it DOES run
    "clr_disarm":  "IFC",
    "clr_ctl":     7777,
    # --- D-MFDOM: the argument domain, MEASURED on the CF-3300 2026-07-31 and
    # written down BEFORE zerobas was run on a single one of these rows, so the
    # oracle cannot have been back-fitted to whatever zerobas happens to do.
    # (memory: validate-oracle-artifacts / vacuous-gate-row-steers-not-just-misses)
    # The three rules these nine readings pin:
    #   1. out of int16          -> ERR 6  Overflow      (65536, 70000)
    #   2. in int16, out of 0..15-> ERR 5  Illegal fn    (300, -1, -16, 8+8)
    #   3. fractional            -> TRUNCATES, then rule 1/2 on the integer
    "mfd_300":     "IFC",
    "mfd_65536":   "OVF",    # ⚠️ NOT IFC -- the reference distinguishes the two
    "mfd_70000":   "OVF",
    "mfd_neg":     "IFC",
    "mfd_neg16":   "IFC",
    "mfd_frac":    "BFN",    # 2.5 -> 2, so #3 is out of range
    "mfd_frac_ctl": 7777,    # ...and an integer 3 DOES open #3
    "mfd_frac15":  7777,     # 15.9 -> 15, accepted (rounding would be IFC)
    "mfd_expr":    "IFC",
    "mfd_noeq":    "SYNTAX",
    # the int16 boundary, measured on the CF-3300 2026-07-31 (again, BEFORE
    # zerobas was run on them). It is the RANGE -32768..32767, NOT the magnitude
    # |x| <= 32767 -- the same asymmetric boundary get_byte_arg's header records
    # for CHR$ on the VG-8020, now confirmed for MAXFILES on the CF-3300 rather
    # than assumed to carry over from another verb.
    "mfd_32767":   "IFC",
    "mfd_32768":   "OVF",
    "mfd_n32768":  "IFC",
    "mfd_n32769":  "OVF",
}

# Error CLASSES, not wordings. zerobas prints its OWN lowercase messages by
# deliberate provenance policy (basic/PROVENANCE.md §851: own wording, never the
# reference's verbatim strings), so `Syntax error` vs `syntax error` is the
# firewall working as designed -- NOT a divergence. Comparing the raw text would
# emit a false divergence on every error row and bury the real findings.
ERR_CLASSES = {
    "SYNTAX": ("syntax error",),
    "IFC":    ("illegal function call",),
    "FNF":    ("file not found",),
    "BFN":    ("bad file number",),
    "FNO":    ("file not open",),
    "OOM":    ("out of memory",),
    # D-MFDOM: the argument-domain rows can legitimately land on either of these
    # and NEITHER was classifiable before. An unclassified error line reads as
    # "no number on screen" -- see NOREAD below for why that is fatal.
    "OVF":    ("overflow",),          # ERR 6 -- what an out-of-int16 arg raises
    "TM":     ("type mismatch",),     # ERR 13 -- a non-numeric argument
}

# How each case is compared between the two machines:
#   "class"  — compare the error class / integer verbatim (a real differential)
#   "absfre" — INFORMATIONAL ONLY. Absolute FRE(0) differs between machines by
#              design (different RAM maps); only the SLOPE across the ladder is
#              meaningful, and that is derived separately below.
COMPARE = {
    "boot": "absfre", "ctl_noop": "absfre", "open_after": "absfre",
    "mf0": "absfre", "mf1": "absfre", "mf2": "absfre", "mf3": "absfre",
    "mf4": "absfre", "mf8": "absfre", "mf15": "absfre",
}

# --- GATE: divergences that are FILED AND EXPECTED, with the item that owns
# each. Everything NOT listed here is a regression and fails the run. The list
# is the honest statement of what D-FCH has not built yet; it shrinks as those
# items land, and it must never grow silently. ⚠️ A row is allowlisted with the
# value it is EXPECTED to diverge to, so a row that starts failing DIFFERENTLY
# still trips the gate.
KNOWN_DIVERGE = {
    # ✅ S-FCH-2 ALL-RESIDENT LANDED 2026-07-29 (docs/spec-basic-filechan-alloc.md
    # §5d): ERR 52 `bad file number` and ERR 59 `file not open` are raised and
    # printed by the resident ROM, as ORDINARY TRAPPABLE codes through a sparse
    # arm off raise_error's out-of-table branch. That closed FOUR rows that used
    # to live on this list -- sem_zero, sem_hinum, sem_reopen and err_notopen --
    # and is why they are gone rather than updated.
    #
    # ✅ D-ONELIN LANDED 2026-07-29 (docs/spec-basic-onelin-reset-scope.md):
    # THREE MORE rows left this list the same day -- err_badchan, mf_disarm and
    # clr_disarm. `MAXFILES`/`CLEAR` now DISARM an armed `ON ERROR` handler, as
    # the reference does, because the disarm moved to `vars_reset` -- the one
    # routine RUN, NEW, CLEAR/MAXFILES and every program EDIT all funnel through.
    # err_badchan was never an ERR 52 fact at all: line 20's `MAXFILES=1`
    # suppressed its handler on the reference and not on zerobas, so the
    # reference reported past the handler while zerobas trapped and printed 52.
    #
    # ✅ D-LOF LANDED 2026-07-31 (docs/spec-basic-lof-size-field.md): the LAST
    # entry, `lof_new`, is gone -- `LOF` on a freshly-created OUTPUT channel now
    # reads 0 on both machines. It was never an allocation fact either: the
    # per-channel size field simply had no writer on any CREATE path, so `LOF`
    # returned whatever the previous tenant of the FCH_STATE0 span left (measured
    # at 26 and 2048 -- the -1 was only the cold-boot content of the cell). Three
    # sites, not one; the full battery lives in `diskbasic_probe_lof.py`.
    #
    # ⚠️ THE LIST IS EMPTY, AND AN EMPTY ALLOWLIST IS THE POINT: an allowlist that
    # must keep MATCHING is a control, one that only suppresses is rot. Every row
    # in this probe must now agree, and any entry added here has to name the item
    # that owns it.
}


def err_class(text: str):
    """Map a screen line to an error class, or None if it is not an error."""
    low = text.lower()
    for cls, needles in ERR_CLASSES.items():
        for n in needles:
            if n in low:
                return cls
    return None


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
              step: float = 4.5) -> str:
    L = ["set throttle off",
         f"set __f [open {{{out_path}}} w]",
         "proc __hex {a l} { binary scan [debug read_block memory $a $l] H* h; return $h }",
         "proc __hex_v {a l} { binary scan [debug read_block VRAM $a $l] H* h; return $h }",
         "proc __dump {} {",
         "  global __f",
         '  puts $__f "meta scrmod=[__hex 0xFCAF 1] linlen=[__hex 0xF3B0 1]'
         ' himem=[__hex 0xFC4A 2] txttab=[__hex 0xF676 2]"',
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
        # ⚠️ 4.5 s is this probe's MEASURED-STABLE cadence, and it is the cadence
        # at which D-LOF measured the CF-3300 EATING keystrokes on lines that
        # touched the DISK (`PRINT LOF(1)` -> `PRO)`, answered with a completely
        # real `Syntax error`). This probe's rows are FRE(0) reads, which is why
        # it has been safe here -- but "has been stable" is not attribution, and
        # a delay makes mangling RARE, it cannot make it VISIBLE. The ECHO GUARD
        # (echo_missing) is what makes it loud; the delay and the guard are not
        # substitutes for one another.
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

    THE APPARATUS GUARD, ported wholesale from diskbasic_probe_lof.py (its §0 in
    docs/lof-cf3300-characterization.md is the record of the THREE wrong versions
    below -- do not re-derive them). A dropped keystroke turns `PRINT FRE(0)` into
    something shorter, and the machine answers THAT with a completely real
    `Syntax error` -- which reads as a finding about MAXFILES. Concatenating the
    rows reproduces the screen as one string, so a WRAPPED echo is contiguous in
    it and both wrapped and unwrapped lines are covered by one test.

    ⚠️ MATCH WITH ALL WHITESPACE REMOVED, from both sides. Two separate screen
    geometries conspire against a naive comparison, and the guard's first two
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
    drops this catches swallow whole chunks, and BASIC ignores spacing anyway.

    ⚠️ AND THE MATCH IS ANCHORED ON THE PROMPT AND EXACT, not a substring test:
    with whitespace squeezed out `ZBPPRINT FRE(0)` CONTAINS `PRINTFRE(0)`, so a
    plain `in` test passes a DOUBLED-character screen. A guard against DROPPED
    text is not a guard against INSERTED text.

    ⚠️ Assumes the case is short enough that nothing scrolls off the 24-row
    screen. That is the one assumption this probe strains and lof does not: ten
    cases here type a five-line program and then RUN it. A scrolled-off echo
    reports MANGLED on a PERFECT screen; `-v` tells the two apart at a glance
    (scrolled-off = the echo is simply absent and everything after it is clean).
    """
    squeeze = lambda s: "".join(s.split())
    # every row, and every run of 2 or 3 consecutive rows, as one squeezed string
    # (a wrapped echo spans rows; nothing here wraps past three).
    cand = set()
    for i in range(len(raw_rows)):
        for n in (1, 2, 3):
            cand.add(squeeze("".join(raw_rows[i:i + n])))
    return [ln for ln in lines if prompt + squeeze(ln) not in cand]


def run_case(side: str, label: str, lines, step: float = 4.5):
    machine, date_prompt, boot_t, prompt = MACHINES[side]
    dsk = tempfile.NamedTemporaryFile(suffix=".dsk", prefix=f"cc_{side}_{label}_",
                                      delete=False).name
    shutil.copy(SRC_DSK, dsk)              # /tmp copy -- never the committed image
    out = f"/tmp/chancost_{side}_{label}.txt"
    tcl = out + ".tcl"
    with open(tcl, "w") as fh:
        fh.write(build_tcl(out, lines, date_prompt, boot_t, step))
    if os.path.exists(out):
        os.unlink(out)
    proc = subprocess.Popen(
        omsx_preflight.guarded([OMSX, "-machine", machine, "-diska", dsk,
         "-command", "set renderer none; set sound_driver null", "-script", tcl]),
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    deadline = time.time() + 200
    while proc.poll() is None and time.time() < deadline:
        time.sleep(0.1)
    if proc.poll() is None:
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        os.unlink(dsk)
        # ⚠️ A DISTINCT MARKER, not None. `None` is also what a clean screen with
        # no number on it reads as, and these two paths return BEFORE the echo
        # guard runs -- so a run that never finished would arrive at the verdict
        # column wearing the same face as a reading. It is then reported as
        # ORACLE DRIFT, i.e. blamed on the CF-3300. MEASURED, not hypothetical:
        # `lof_new` came back None on one full run and read a clean 0 on re-run.
        # (memory: a sentinel that also means "no reading" is not a measurement)
        return side, label, "TIMEOUT", ["TIMEOUT"], ""
    os.unlink(dsk)
    if not os.path.exists(out):
        return (side, label, "NOCAPTURE",
                ["NO CAPTURE (machine/ROMs missing?)"], "")
    s0, s1, r0, r1, meta, scrmod = [], [], [], [], "", 0
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
    # geometry MEASURED, not assumed
    rows = [r for r in (s1 if scrmod == 1 else s0) if r]
    # the apparatus guard runs BEFORE any answer is read off the screen.
    missing = echo_missing(r1 if scrmod == 1 else r0, lines, prompt)
    if missing:
        return (side, label, "MANGLED", rows + [f"NOT ECHOED: {missing!r}"], meta)
    return side, label, read_value(rows), rows, meta


def read_value(rows):
    """Screen lines -> the row's reading: an error CLASS, an int, or NOREAD.

    Split out of run_case so the NOREAD guard can be falsified on synthetic
    screens without booting a machine (the same way the echo guard's K2 battery
    is run). Nothing else about the derivation changed.
    """
    value = None
    for r in rows:                                   # an error outranks a number
        cls = err_class(r)
        if cls:
            value = cls
    if value is None:
        nums = [int(r) for r in rows if re.fullmatch(r"-?\d+", r)]
        # ⚠️ NOREAD, not None. EVERY case in this probe is expected to put either
        # a number or a KNOWN error class on screen -- that is what its REF_EXPECT
        # entry is. A screen carrying neither is a screen this probe cannot read,
        # and the overwhelmingly likely cause is an error message that is not in
        # ERR_CLASSES (before D-MFDOM, `Overflow` and `Type mismatch` were both
        # unclassified, and the domain rows below can raise either).
        #
        # Returning None for that is the SAME failure the TIMEOUT/NOCAPTURE paths
        # above were fixed for, one layer further in: None is not distinguishable
        # from "a clean screen with no number on it", so an unreadable ROW on BOTH
        # machines compares EQUAL and prints `agree` -- a row that measured
        # nothing, reported as a pass. (memory: a sentinel that also means "no
        # reading" is not a measurement; gate-can-be-green-while-measuring-nothing)
        value = nums[-1] if nums else "NOREAD"
    return value


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="comma-separated case labels")
    ap.add_argument("--side", choices=("ref", "zb", "both"), default="both")
    ap.add_argument("--line-delay", type=float, default=4.5,
                    help="emulated seconds per typed line (default 4.5, this "
                         "probe's measured-stable cadence). Settable mainly so "
                         "the echo guard can be shown to CUT: at a short delay "
                         "the machines drop or double keystrokes.")
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
    jobs = [(s, lbl, lines, args.line_delay)
            for lbl, lines in cases for s in sides]
    with cf.ThreadPoolExecutor(max_workers=4) as ex:
        results = list(ex.map(lambda j: run_case(*j), jobs))
    by = {(s, l): (v, rows, meta) for s, l, v, rows, meta in results}

    print(f"{'case':<14} {'reference':>14} {'zerobas':>14}   verdict")
    print("-" * 70)
    oracle_bad, diverge, mangled = [], [], []
    for label, _ in cases:
        rv = by.get(("ref", label), (None, [], ""))[0] if "ref" in sides else "-"
        zv = by.get(("zb", label), (None, [], ""))[0] if "zb" in sides else "-"
        mode = COMPARE.get(label, "class")
        note = ""
        # ⚠️ CHECKED FIRST, and never folded into anything below. Two reasons,
        # each on its own sufficient: two MANGLED sides compare EQUAL and would
        # print `agree` (gate-can-be-green-while-measuring-nothing), and a
        # mangled REFERENCE row would otherwise be reported as ORACLE DRIFT --
        # loud, but blaming the CF-3300 for the typing. Attribution is the point.
        if {rv, zv} & {"MANGLED", "TIMEOUT", "NOCAPTURE", "NOREAD"}:
            why = ("MANGLED" if "MANGLED" in (rv, zv) else
                   "UNREADABLE SCREEN" if "NOREAD" in (rv, zv) else "RUN FAILED")
            note = f"{why} (the machine did not answer THIS line -- NOT a reading)"
            mangled.append(label)
        elif "ref" in sides and label in REF_EXPECT and rv != REF_EXPECT[label]:
            note = f"ORACLE DRIFT (recorded {REF_EXPECT[label]!r})"
            oracle_bad.append(label)
        elif args.side == "both":
            if mode == "absfre":
                # absolute pool sizes are not comparable between machines --
                # only the ladder's SLOPE is, and that is derived below.
                note = "informational (slope below)"
            elif rv == zv:
                note = "agree"
            elif KNOWN_DIVERGE.get(label) == (rv, zv):
                note = "diverges (FILED — ON ERROR disarm / LOF, TODO)"
            else:
                note = "DIVERGES"
                diverge.append((label, rv, zv))
        print(f"{label:<14} {str(rv):>14} {str(zv):>14}   {note}")
        if args.verbose:
            for s in sides:
                for r in by.get((s, label), (None, [], ""))[1]:
                    print(f"      {s} | {r}")

    print()
    if "ref" in sides:
        print("meta(ref):", by.get(("ref", cases[0][0]), (None, [], ""))[2])
    if "zb" in sides:
        print("meta(zb) :", by.get(("zb", cases[0][0]), (None, [], ""))[2])

    # --- MANGLED: fatal, and it SUPPRESSES the derivation rather than letting it
    # print. The slope, the ceiling and the HEADLINE are all computed from the
    # `mf*` ladder; derived from a mangled ladder they are numbers this run never
    # measured, and printing "the reference charges 267 B per channel" off a
    # screen that never received `MAXFILES=8` is exactly the failure this guard
    # exists to close. Print the table, name the rows, stop.
    if mangled:
        print(f"\n{len(mangled)} NON-READING row(s): {mangled}")
        print("  Either a typed line was not echoed on screen (the machine "
              "answered a line other\n  than the one this probe meant to type, and "
              "a mangled line earns a COMPLETELY\n  REAL error message), or the run "
              "itself did not finish (TIMEOUT / NO CAPTURE),\n  or the screen carried "
              "neither a number nor a KNOWN error class (NOREAD --\n  most likely an "
              "error message missing from ERR_CLASSES; ADD IT, do not\n  widen the "
              "row).  All are APPARATUS failures, not readings: re-run, and if a\n  "
              "MANGLED row reproduces raise --line-delay. Every derived number is "
              "suppressed below.")
        return 3        # ALWAYS fatal: it is not a measurement.

    # --- THE DERIVED ANSWER: per-channel slope + ceiling, both machines ---
    ladder = [("mf0", 0), ("mf1", 1), ("mf2", 2), ("mf3", 3),
              ("mf4", 4), ("mf8", 8), ("mf15", 15)]
    print()
    summary = {}
    for s in sides:
        pts = [(n, by[(s, l)][0]) for l, n in ladder
               if (s, l) in by and isinstance(by[(s, l)][0], int)]
        slopes = {(pts[i - 1][1] - pts[i][1]) / (pts[i][0] - pts[i - 1][0])
                  for i in range(1, len(pts))} if len(pts) >= 2 else set()
        # The ceiling is only a CEILING if the rows above it actually ran and
        # were rejected. On a subsetted run the largest surviving n is just the
        # largest n we asked about -- reporting that as "the ceiling" would be a
        # number the run never measured.
        ran = {l for l, _ in cases}
        full_ladder = all(l in ran for l, _ in ladder) and {"mf16"} <= ran
        ceiling = max((n for n, _ in pts), default=None)
        summary[s] = (sorted(slopes), ceiling if full_ladder else None)
        shape = ("statically reserved (MAXFILES does not move FRE(0))"
                 if slopes == {0.0} else
                 f"{sorted(slopes)[0]:g} B/channel, charged from the FRE(0) pool"
                 if len(slopes) == 1 else "NOT LINEAR — investigate")
        ceil_txt = (f"highest accepted MAXFILES = {ceiling}" if full_ladder
                    else f"ceiling NOT MEASURED (partial ladder; largest tried {ceiling})")
        print(f"{s:>4}: per-channel = {shape}; {ceil_txt}")

    if oracle_bad:
        print(f"\nORACLE DRIFT on {oracle_bad} — the reference no longer reproduces "
              f"its own recorded answers; fix the apparatus before trusting anything.")
        return 1
    full_run = args.side == "both" and len(cases) == len(CASES)
    if full_run:
        rs, rc = summary.get("ref", ([], None))
        zs, zc = summary.get("zb", ([], None))
        print()
        print("HEADLINE:")
        print(f"  reference charges {rs[0]:g} B per channel, dynamically, up to {rc};")
        print(f"  zerobas   charges {zs[0]:g} B per channel, dynamically, up to {zc}.")
        print("  (D-FCH §3.2: both MECHANISMS are now the same -- carved out of the")
        print("   FRE(0) pool at MAXFILES time, ceiling 15. The per-channel CONSTANTS")
        print("   differ because a zerobas block IS 50 B: its sector staging is the")
        print("   shared FSECTOR_BUF cache, so it charges what it uses.)")

    if oracle_bad:
        print(f"\nORACLE DRIFT on {oracle_bad} — the reference no longer reproduces "
              f"its own recorded answers; fix the apparatus before trusting anything.")
        return 1
    if diverge:
        print(f"\n{len(diverge)} UNFILED divergence(s) vs the reference:")
        for label, rv, zv in diverge:
            print(f"  {label}: reference {rv!r}, zerobas {zv!r}")
        return 1
    # --- the GATE proper: the mechanism assertions, only on a full run --------
    if full_run:
        bad = []
        for s in ("ref", "zb"):
            slopes, ceiling = summary.get(s, ([], None))
            if slopes == [0.0]:
                bad.append(f"{s}: MAXFILES does not move FRE(0) (statically reserved)")
            elif len(slopes) != 1:
                bad.append(f"{s}: per-channel charge is NOT LINEAR: {slopes}")
            if ceiling != 15:
                bad.append(f"{s}: highest accepted MAXFILES is {ceiling}, want 15")
        if bad:
            print("\nGATE FAILED:")
            for b in bad:
                print(f"  {b}")
            return 1
        print("\nGATE: both machines charge per-channel, linearly, ceiling 15 — "
              f"{len(cases)} cases, {len(KNOWN_DIVERGE)} filed divergences.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
