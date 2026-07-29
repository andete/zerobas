#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Error-handling acceptance — S2b trap/RESUME gate (docs/spec-basic-error-handling-
s2b-packet.md §10). Differential against the reference oracle Philips VG-8020,
driven through the typing-free KEYBUF-injection REPL driver (probes/lib/omsx_repl.py),
modelled on probes/basic/error_acceptance.py's family shapes.

Standing gate for the RESUME family (`make error-trap-acceptance`); the S2b arc landed
on main 2026-07-19. The resume_line case additionally gates the ERR-reset-on-RESUME
follow-up (ERR->0, ERL kept), landed 2026-07-19.

Cases (observable-variable design throughout, matching error_acceptance.py's own
robustness rule — screen-scrape only where the packet needs the message TEXT or its
structure, never as the sole signal for a numeric fact):

  * TRAP_ERL   — trap fires; ERR/ERL correct inside the handler ("TRAP 5 20").
  * RESUME_BARE / RESUME_ZERO — retry the erroring statement (both forms; a handler
    mutates state so the RETRY succeeds and the run continues past it).
  * RESUME_NEXT_SAMELINE — RESUME NEXT across a mid-':'-line error whose OWN
    statement contains a quoted ':' (PRINT "a:b";SQR(-1):PRINT"AFTER") — the
    scan_stmt_end quote-awareness case (packet §5.5/§10's explicit callout).
  * RESUME_NEXT_EOL — RESUME NEXT where the erroring statement is the LAST on its
    line (advances to the next LINE's first statement).
  * RESUME_LINE — RESUME <line> (an explicit target).
  * NESTED_FORCED_ABORT — an error INSIDE the handler with no intervening RESUME ->
    forced abort with the INNER message (not a re-trap).
  * ON_ERROR_GOTO_0 — disables the handler -> falls back to the S1 abort (" in N").
  * ON_ERROR_UNDEF — ON ERROR GOTO <undefined line> -> "Undefined line number" at
    definition time.
  * RESUME_NOERR — bare RESUME with no active trap -> ERR 22 ("resume without
    error").
  * ERROR_N_REGRESSION — ERROR 5 still prints the right message (S2a regression,
    matches error_acceptance.py's own C_ERROR5_DIRECT case).
  * MSGTAB_BOUND — `ERROR 23..26` message text: err_msgtab's last entry (25, "Line
    buffer overflow") is LIVE and 26 falls to "unprintable error". raise_error's
    `cp` bound and the table's length are one fact in two places; they drifted once
    (2026-07-29) and nothing noticed, because the sole raiser of 25 bypasses the
    table. Gates BOTH directions — 25 in, 26 out.
  * ONEFLG_* — the D-ONEFLG reset scope (docs/spec-basic-oneflg-reset-scope.md).
    `ONEFLG` ("inside a handler, no RESUME yet") used to survive the return to the
    REPL, so after a nested forced abort the NEXT error force-aborted instead of
    trapping. The reference clears it on ANY abort and on any RUN TERMINATION, but
    NOT on a STOP/Break — a suspended run must keep its handler context so CONT can
    resume inside it. Seven rows, each naming the site it holds down: three that
    require the clear (stale/end/falloff), TWO THAT REQUIRE ITS ABSENCE
    (keep/suspend_resume — these are what make the PLACEMENT load-bearing; a fix
    that just zeroes ONEFLG at the prompt passes the first three and fails these),
    plus the no-prior-error control and a direct-RESUME readout that reads the flag
    head-on ("RESUME without error" == ONEFLG is already 0).
  * ONELIN_* — the D-ONELIN reset scope (docs/spec-basic-onelin-reset-scope.md),
    i.e. §7's OTHER half. `ON ERROR` is disarmed exactly when the VARIABLE TABLE
    IS CLEARED: RUN, NEW, CLEAR (direct-mode and in-run, so MAXFILES too) and
    EVERY program EDIT — measured, 13 oracle-locked rows of which FIVE require the
    handler to SURVIVE, plus a fourteenth judged on the abort LINE NUMBER because
    a stale handler pointer branches wild rather than simply not firing.
  * RESET_SCOPE_RUN / RESET_SCOPE_NEW / RESET_SCOPE_CLEAR — the §7 pin as
    originally written: a handler armed via a DIRECT-MODE `ON ERROR GOTO` (so the
    PROGRAM ITSELF never re-arms it), then RUN/NEW/CLEAR, then an error in a fresh
    minimal program. Straight DIFFERENTIAL, no hardcoded expectation. ⚠️ KEPT, BUT
    CONFOUNDED FOR PLACEMENT and no longer the primary evidence: every one of the
    three types a program line BETWEEN the arm and the trigger, so it cannot tell
    an EDIT's disarm from RUN's or CLEAR's. All three read "no fire" on both
    machines both before and after D-ONELIN — for DIFFERENT reasons on each side
    before it. The ONELIN_* rows above are the unconfounded measurement.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from collections import namedtuple

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
import omsx_repl  # noqa: E402

REF_MACHINE = "Philips_VG_8020"
ZB_MACHINE = os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")

Case = namedtuple("Case", "label lines")


def read_R(raw):
    """The value(s) printed by `PRINT"R<";...;">"` -- the last `R<...>` marker on
    screen (observable-variable pattern, error_acceptance.py's read_A)."""
    if not raw:
        return None
    m = re.findall(r"R<([^<>]*)>", raw)
    return m[-1].strip() if m else None


def in_line_number(raw):
    """The <n> from an error message's ' in <n>' suffix, or None if absent
    (error_acceptance.py's own helper, same convention)."""
    if not raw:
        return None
    m = re.findall(r"\bin (\d+)\b", raw)
    return m[-1] if m else None


# --- Numeric-fact cases (observable-variable; differential vs the VG-8020) -----
NUM_CASES = [
    Case("trap_erl", [
        "10 X=-1", "20 ON ERROR GOTO 100", "30 B=SQR(X)",
        '100 PRINT"R<";ERR;",";ERL;">"',
        "RUN",
    ]),  # want "5,30"
    Case("resume_bare", [
        "10 X=-1", "20 ON ERROR GOTO 100", "30 B=SQR(X)",
        '40 PRINT"R<";B;">"',
        "100 X=4:RESUME",
        "RUN",
    ]),  # want "2" (retry succeeds once X:=4, SQR(4)=2, falls through to line 40)
    Case("resume_zero", [
        "10 X=-1", "20 ON ERROR GOTO 100", "30 B=SQR(X)",
        '40 PRINT"R<";B;">"',
        "100 X=4:RESUME 0",
        "RUN",
    ]),  # want "2" (RESUME 0 == RESUME)
    Case("resume_next_sameline", [
        "10 ON ERROR GOTO 100",
        '20 PRINT "a:b";SQR(-1):C=9',
        '30 PRINT"R<";C;">"',
        "100 RESUME NEXT",
        "RUN",
    ]),  # want "9" -- only reachable if scan_stmt_end skipped the QUOTED ':' in
         # "a:b" and landed on "C=9" (the true next statement), not mid-string
    Case("resume_next_eol", [
        "10 ON ERROR GOTO 100", "20 B=SQR(-1)",
        '30 PRINT"R<";99;">"',
        "100 RESUME NEXT",
        "RUN",
    ]),  # want "99" -- erroring stmt is the LAST on line 20; RESUME NEXT must
         # roll over to line 30, not line 20's (nonexistent) next statement
    Case("resume_line", [
        "10 ON ERROR GOTO 100", "20 B=SQR(-1)",
        '30 PRINT"R<";1;">"',
        '40 PRINT"R<";ERR;"/";ERL;">"',
        "100 RESUME 40",
        "RUN",
    ]),  # RESUME 40 branches to 40 + SKIPS line 30's "R<1...>". Line 40 then prints
         # ERR/ERL: after ANY RESUME the reference RESETS ERR to 0 but KEEPS ERL
         # (empirically pinned VG-8020, all four forms -> "0/20"). Both are gated
         # below (the ERR-reset was S2b-deferred, landed 2026-07-19).
    Case("on_error_goto_0", [
        "10 ON ERROR GOTO 100", "20 ON ERROR GOTO 0", "30 B=SQR(-1)",
        '100 PRINT"R<";7;">"',
        "RUN",
    ]),  # want NO "R<7>" on screen (handler disabled -> S1 abort instead);
         # checked via absence below, not read_R
    Case("error_n_regression", ["ERROR 5"]),  # zerobas-only text check, below
]

# --- Trap-CLASS cases: a statement-level syntax error must TRAP, not abort -----
# Measured on the VG-8020 (2026-07-22, the G8-trapclass follow-up): every
# malformed statement raises a TRAPPABLE ERR 2 into an armed handler -- a bad FOR
# lvalue, a bad NEXT, an unknown statement, a dangling GOTO -- with exactly one
# exception, `FOR A$=`, which is ERR 13. zerobas used to route all of them
# through stmt_error, which PRINTS AND ABORTS, so an ON ERROR program could never
# see them; the abort also made these cases invisible to any probe that reads a
# printed tag, which is how the gap survived this long.
TRAPCLASS_CASES = [
    Case("tc_for_num",   ["10 ON ERROR GOTO 100", "20 FOR 1=0 TO 1:NEXT",
                          '100 PRINT"R<";ERR;">"', "RUN"]),          # 2
    Case("tc_for_str",   ["10 ON ERROR GOTO 100", "20 FOR A$=0 TO 1:NEXT",
                          '100 PRINT"R<";ERR;">"', "RUN"]),          # 13
    Case("tc_for_paren", ["10 ON ERROR GOTO 100", "20 FOR (I)=0 TO 1:NEXT",
                          '100 PRINT"R<";ERR;">"', "RUN"]),          # 2
    Case("tc_for_kw",    ["10 ON ERROR GOTO 100", "20 FOR PRINT=0 TO 1:NEXT",
                          '100 PRINT"R<";ERR;">"', "RUN"]),          # 2
    Case("tc_for_bare",  ["10 ON ERROR GOTO 100", "20 FOR",
                          '100 PRINT"R<";ERR;">"', "RUN"]),          # 2
    Case("tc_for_noeq",  ["10 ON ERROR GOTO 100", "20 FOR I 0 TO 1",
                          '100 PRINT"R<";ERR;">"', "RUN"]),          # 2
    Case("tc_for_noto",  ["10 ON ERROR GOTO 100", "20 FOR I=0 1",
                          '100 PRINT"R<";ERR;">"', "RUN"]),          # 2
    Case("tc_next_junk", ["10 ON ERROR GOTO 100", "20 NEXT 1",
                          '100 PRINT"R<";ERR;">"', "RUN"]),          # 2 (NOT 1)
    Case("tc_next_nofor",["10 ON ERROR GOTO 100", "20 NEXT",
                          '100 PRINT"R<";ERR;">"', "RUN"]),          # 1 -- a BARE
                                                                     # next still is
                                                                     # "next without for"
    Case("tc_swap",      ["10 ON ERROR GOTO 100", "20 SWAP 1,A",
                          '100 PRINT"R<";ERR;">"', "RUN"]),          # 2
    Case("tc_unknown",   ["10 ON ERROR GOTO 100", "20 FOO 1,A",
                          '100 PRINT"R<";ERR;">"', "RUN"]),          # 2
    Case("tc_bareword",  ["10 ON ERROR GOTO 100", "20 ZORK",
                          '100 PRINT"R<";ERR;">"', "RUN"]),          # 2
    Case("tc_juxt",      ["10 ON ERROR GOTO 100", "20 A 1",
                          '100 PRINT"R<";ERR;">"', "RUN"]),          # 2
    Case("tc_dangling",  ["10 ON ERROR GOTO 100", "20 PRINT:GOTO",
                          '100 PRINT"R<";ERR;">"', "RUN"]),          # 2
    # ...and the loop that is FINE must stay fine (a too-eager lvalue check would
    # break every FOR in the corpus, and this is the case that would catch it).
    Case("tc_for_ok",    ["10 ON ERROR GOTO 100", "20 FOR I=0 TO 1:NEXT",
                          '30 PRINT"R<";42;">":END',
                          '100 PRINT"R<";ERR;">"', "RUN"]),          # 42 -- END, or
                                                                     # line 30 falls
                                                                     # THROUGH into the
                                                                     # handler and the
                                                                     # last marker is a
                                                                     # stale ERR
    Case("tc_resume_next", ["10 ON ERROR GOTO 100", "20 FOO 1,A", "30 A=5",
                            '40 PRINT"R<";A;">"',
                            "100 RESUME NEXT", "RUN"]),              # 5 -- the trap
                                                                     # is resumable
]

# --- Structural / message-text cases (screen-scrape; zerobas + differential) ---
NESTED_ABORT = Case("nested_forced_abort", [
    "10 ON ERROR GOTO 100", "20 B=SQR(-1)",
    '100 PRINT"INHANDLER":C=1/0',
    "RUN",
])  # want "INHANDLER" printed, then a forced abort with "division by zero"
    # (the INNER error's message, not a re-trap into line 100) and " in 100"

ON_ERROR_UNDEF = Case("on_error_undef", ["10 ON ERROR GOTO 999", "RUN"])
# want "Undefined line number"-class report at definition time (ex_goto_undef's
# landmark), matching plain GOTO's own undefined-line report (house-style D-8,
# not oracle-verbatim text -- see basic/interp.asm ex_goto_undef)

RESUME_NOERR = Case("resume_noerr", ["RESUME"])
# want "resume without error" (zerobas house-style D-2 wording, ERR 22) --
# zerobas-only text check (not diffed: house style, same policy as error_
# acceptance.py's family B/C message-text cases)

# --- D-ONEFLG: the stale in-handler flag (spec-basic-oneflg-reset-scope.md) ----
# Every row re-enters with `GOTO 200` into a program tail that RE-ARMS its own
# handler at 200, so ONELIN is fresh and the ONLY thing that can decide
# trap-vs-force-abort is ONEFLG. Marker printed -> trapped; `illegal function
# call in 210` -> force-aborted.
#
# ⚠️ THE MARKER IS `PRINT"R<";1;">"`, NOT `PRINT"R<TRAP>"`, AND THAT IS THE
# MEASUREMENT. Round 1 of the characterization used the literal form -- whose own
# SOURCE ECHO contains `R<TRAP>` -- so a force-aborted case scraped the marker off
# the TYPED LINE and scored as a trap. The numeric form's echo yields the artifact
# '";1;"' and its output yields '1'; the two can never collide. Same class as
# clearpool-slice's wrapping echo: the readout is part of the measurement.
ONEFLG_TAIL = ["200 ON ERROR GOTO 300", "210 B=SQR(-1)",
               '300 PRINT"R<";1;">":END']
ONEFLG_CASES = [
    # the filed defect: a nested forced abort left ONEFLG=1 behind
    Case("oneflg_stale", ["10 ON ERROR GOTO 100", "20 B=SQR(-1)", "30 END",
                          "100 C=1/0"] + ONEFLG_TAIL + ["RUN", "GOTO 200"]),
    # two-sided control: identical shape, line 20 does NOT error, so nothing ever
    # set ONEFLG -- both machines must trap here whether the fix exists or not
    Case("oneflg_ctl", ["10 ON ERROR GOTO 100", "20 B=1", "30 END",
                        "100 C=1/0"] + ONEFLG_TAIL + ["RUN", "GOTO 200"]),
    # site B: the handler ENDs the run -- no abort anywhere, so site A alone
    # leaves this red
    Case("oneflg_end", ["10 ON ERROR GOTO 100", "20 B=SQR(-1)", "30 END",
                        "100 END"] + ONEFLG_TAIL + ["RUN", "GOTO 200"]),
    # OVER-CLEAR GUARD: a STOP SUSPENDS the run, it does not end it. The handler
    # context must SURVIVE to the prompt, so this re-entry force-aborts on BOTH
    # machines. Any placement that clears at the prompt / at the run-loop exit
    # (shared by END and STOP) turns this row red.
    Case("oneflg_keep", ["10 ON ERROR GOTO 100", "20 B=SQR(-1)", "30 END",
                         "100 STOP"] + ONEFLG_TAIL + ["RUN", "GOTO 200"]),
    # OVER-CLEAR GUARD from the CONT side: after CONT the handler's own RESUME
    # still has to work, which needs ONEFLG intact across the whole suspension.
    Case("oneflg_suspend_resume",
         ["10 ON ERROR GOTO 100", "20 B=SQR(-1)", "30 END", "100 STOP",
          "110 RESUME 120", '120 PRINT"R<";1;">":END', "RUN", "CONT"]),
]
ONEFLG_TRAPS = {"oneflg_stale": True, "oneflg_ctl": True, "oneflg_end": True,
                "oneflg_keep": False, "oneflg_suspend_resume": True}

# Direct `RESUME` readouts -- these read ONEFLG head-on rather than through a
# trap decision: with ONEFLG==0 the RESUME family reports ERR 22 "without error".
ONEFLG_RESUME_DIFF = Case("oneflg_direct_resume", [
    "10 ON ERROR GOTO 100", "20 B=SQR(-1)", "30 END", "100 C=1/0",
    "RUN", "RESUME",
])  # both machines: "RESUME without error". Pre-fix zerobas instead RESUMED into
    # line 20 with the stale flag and re-raised ("division by zero in 100" twice).
ONEFLG_RESUME_ZB = Case("oneflg_falloff", [
    "10 ON ERROR GOTO 100", "20 B=SQR(-1)", "30 END", "100 A=1",
    "RUN", "RESUME",
])  # site C: the handler runs off the END OF THE PROGRAM. zerobas-ONLY on
    # purpose -- the reference does not end silently here at all, it raises ERR 21
    # "No RESUME in 100" first (a raiser zerobas lacks, filed separately in
    # docs/spec-basic-oneflg-reset-scope.md §7). So the row gates the RESUME
    # RESPONSE, which is the ONEFLG fact, and not the text before it.

# --- D-ONELIN: WHAT DISARMS `ON ERROR` (spec-basic-onelin-reset-scope.md) ------
# The §7 reset-scope cases below are CONFOUNDED FOR PLACEMENT: each of them types
# a program line BETWEEN the direct-mode arm and the trigger, so "the EDIT
# disarmed it" and "RUN/CLEAR disarmed it" are indistinguishable there -- which is
# how the packet's `ONELIN` half stayed open for a whole arc while all three rows
# read green. These rows type the WHOLE program FIRST and arm LAST, so every
# trigger is measured ALONE.
#
# MEASURED RULE (VG-8020, 2026-07-29): `ON ERROR` is disarmed exactly when the
# VARIABLE TABLE IS CLEARED -- RUN, NEW, CLEAR (direct-mode and in-run, so
# MAXFILES too) and EVERY program EDIT. Nothing else disarms it.
#
# ⚠️ The `edit_append` row is the one that falsified the filed "ONELIN holds a
# resolved link address, invalidated when what it points into MOVES" reading:
# appending line 200 moves nothing at all and the reference disarms anyway.
# Same marker discipline as ONEFLG above -- `PRINT"R<";1;">"`, never a literal.
ONELIN_H = '100 PRINT"R<";1;">"'      # the handler line
ONELIN_E = "10 B=SQR(-1)"             # the erroring line
ONELIN_CASES = [
    # -- direct-mode triggers, NO edit between the arm and the trigger ---------
    Case("onelin_ctl_goto", [ONELIN_H, ONELIN_E, "ON ERROR GOTO 100", "GOTO 10"]),
    Case("onelin_run_arm", [ONELIN_H, ONELIN_E, "ON ERROR GOTO 100", "RUN"]),
    Case("onelin_clear_direct",
         [ONELIN_H, ONELIN_E, "ON ERROR GOTO 100", "CLEAR", "GOTO 10"]),
    Case("onelin_print_direct",
         [ONELIN_H, ONELIN_E, "ON ERROR GOTO 100", "PRINT 0", "GOTO 10"]),
    # -- program EDITS, arm already in place -----------------------------------
    Case("onelin_edit_retype",
         [ONELIN_H, ONELIN_E, "ON ERROR GOTO 100", ONELIN_E, "GOTO 10"]),
    Case("onelin_edit_append",
         [ONELIN_H, ONELIN_E, "ON ERROR GOTO 100", "200 REM", "GOTO 10"]),
    # -- in-run triggers -------------------------------------------------------
    Case("onelin_inrun_clear", ["10 ON ERROR GOTO 100", "20 CLEAR",
                                "30 B=SQR(-1)", "40 END", ONELIN_H, "RUN"]),
    Case("onelin_inrun_ctl", ["10 ON ERROR GOTO 100", "20 REM CLEAR",
                              "30 B=SQR(-1)", "40 END", ONELIN_H, "RUN"]),
    Case("onelin_inrun_rearm", ["10 ON ERROR GOTO 100", "20 CLEAR",
                                "25 ON ERROR GOTO 100", "30 B=SQR(-1)",
                                "40 END", ONELIN_H, "RUN"]),
    Case("onelin_inrun_dim", ["10 ON ERROR GOTO 100", "20 DIM Q(50)",
                              "30 B=SQR(-1)", "40 END", ONELIN_H, "RUN"]),
    Case("onelin_inrun_str", ["10 ON ERROR GOTO 100", '20 A$="X"+"Y"',
                              "30 B=SQR(-1)", "40 END", ONELIN_H, "RUN"]),
    Case("onelin_stop_cont", ["10 ON ERROR GOTO 100", "20 STOP",
                              "30 B=SQR(-1)", "40 END", ONELIN_H, "RUN", "CONT"]),
    Case("onelin_clear_before_arm", ["10 ON ERROR GOTO 100", "20 B=SQR(-1)",
                                     "30 END", ONELIN_H, "CLEAR", "RUN"]),
]
# The reference's own recorded answers -- oracle-locked, so a row that starts
# reading differently trips the gate instead of quietly redefining the target.
# False = the handler was DISARMED. FOUR rows require the disarm and FIVE require
# its ABSENCE: the "must NOT" half is what makes the PLACEMENT load-bearing (the
# D-ONEFLG lesson -- its cheap-but-wrong placement passed every "must" row).
ONELIN_FIRES = {
    "onelin_ctl_goto": True,            # control: the shape itself works
    "onelin_run_arm": False,            # RUN disarms -- MEASURED, not assumed
    "onelin_clear_direct": False,       # must disarm
    "onelin_print_direct": True,        # must NOT
    "onelin_edit_retype": False,        # must disarm
    "onelin_edit_append": False,        # must disarm (and kills the "it MOVED" theory)
    "onelin_inrun_clear": False,        # must disarm -- the filed defect
    "onelin_inrun_ctl": True,           # must NOT (REMmed-out control)
    "onelin_inrun_rearm": True,         # must NOT: a re-arm restores the trap, so
                                        # the CLEAR zeroed the ARM, not a "mode"
    "onelin_inrun_dim": True,           # must NOT: keeps the zero out of ary_reset
    "onelin_inrun_str": True,           # must NOT: ...and out of heap_reset
    "onelin_stop_cont": True,           # must NOT: a suspension is not a reset
    "onelin_clear_before_arm": True,    # must NOT: a CLEAR before the arm
}
# ⚠️ ONE ROW CANNOT BE JUDGED ON THE MARKER AT ALL. Inserting a line BEFORE the
# erroring line MOVES the handler line, and pre-fix zerobas followed its stale
# ONELIN link into the moved text: it neither fired the handler nor aborted
# cleanly -- it branched WILD and reported `syntax error in 4850`, a line that
# does not exist. Marker-wise that is "did not fire", i.e. it AGREED with the
# reference while doing something far worse. So this row is judged on the ABORT
# LINE NUMBER: both machines must report the error at line 10.
ONELIN_INSERT = Case("onelin_edit_insert",
                     [ONELIN_H, ONELIN_E, "ON ERROR GOTO 100", "5 REM", "GOTO 10"])

# --- §7 reset-scope cases (packet §7 -- ANSWERED; see D-ONELIN above) ---------
# A handler armed via DIRECT MODE (never touched by the program body), then a
# reset hook, then a FRESH minimal erroring program. Straight differential --
# NO hardcoded expectation (the working hypothesis is unverified; this probe
# exists to PIN it, not assume it).
RESET_SCOPE_CASES = [
    Case("reset_scope_run", [
        ONELIN_H,
        "ON ERROR GOTO 100",
        "10 B=SQR(-1)",
        "RUN",
    ]),
    Case("reset_scope_new", [
        ONELIN_H,
        "ON ERROR GOTO 100",
        "NEW",
        "10 B=SQR(-1)",
        "RUN",
    ]),
    Case("reset_scope_clear", [
        ONELIN_H,
        "ON ERROR GOTO 100",
        "10 B=SQR(-1)",
        "CLEAR",
        "RUN",
    ]),
]
# The reference's recorded answers -- ADDED 2026-07-29 (D-ONELIN §2.1). These
# three used to be judged on `"R<LEAKED>" in raw` with a LITERAL marker line
# `100 PRINT"R<LEAKED>"`, whose OWN SOURCE ECHO contains that exact string: the
# test was TRUE on every machine, every build, forever. Vacuous since the day it
# landed -- and not harmlessly so, because the "reference DOES fire the handler
# on reset_scope_clear" claim in spec-basic-filechan-alloc.md §5d.5 was read off
# it, and that false claim is what steered the filed defect away from the
# variable-clear rule for a whole arc. Now on the numeric marker, like every
# other row in this file, and oracle-locked so it can never go quiet again.
RESET_SCOPE_FIRES = {"reset_scope_run": False, "reset_scope_new": False,
                     "reset_scope_clear": False}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--machine", default=REF_MACHINE, help="reference oracle machine")
    ap.add_argument("--zb-machine", dest="zb_machine", default=ZB_MACHINE,
                    help="zerobas repack machine")
    ap.add_argument("--only", help="run only cases whose label contains this substring")
    ap.add_argument("--ref-only", action="store_true", help="oracle-lock only")
    ap.add_argument("--boot-per-case", dest="boot_per_case", action="store_true")
    args = ap.parse_args()
    batch = not args.boot_per_case
    ok = True

    def sel(cases):
        return [c for c in cases if not args.only or args.only in c.label]

    # ---------------- numeric-fact cases: differential vs the VG-8020 ----------
    want_num = {
        # PRINT renders ";"-separated numerics with sign-spaces: `PRINT ERR;",";ERL`
        # -> " 5 , 30 " (read_R strips only the outer edges).
        "trap_erl": "5 , 30", "resume_bare": "2", "resume_zero": "2",
        "resume_next_sameline": "9", "resume_next_eol": "99",
        # trap-class (a statement-level syntax error TRAPS, ERR 2 -- ERR 13 for
        # the one string-lvalue shape, ERR 1 only for a genuine bare NEXT)
        "tc_for_num": "2", "tc_for_str": "13", "tc_for_paren": "2",
        "tc_for_kw": "2", "tc_for_bare": "2", "tc_for_noeq": "2",
        "tc_for_noto": "2", "tc_next_junk": "2", "tc_next_nofor": "1",
        "tc_swap": "2", "tc_unknown": "2", "tc_bareword": "2", "tc_juxt": "2",
        "tc_dangling": "2", "tc_for_ok": "42", "tc_resume_next": "5",
    }
    ncases = [c for c in sel(NUM_CASES + TRAPCLASS_CASES) if c.label in want_num]
    if ncases:
        specs = [("direct", c.lines) for c in ncases]
        ref = omsx_repl.run_cases(args.machine, specs, batch=batch, reset=("NEW", "CLS"))
        print(f"--- numeric-fact oracle-lock ({args.machine}) ---")
        ref_val = {}
        for c, r in zip(ncases, ref):
            got = read_R(r)
            ref_val[c.label] = got
            want = want_num[c.label]
            good = got == want
            ok = ok and good
            print(f"{'PASS' if good else 'FAIL':5} {c.label:24} ref={got!r} (want {want!r})")
        if not args.ref_only:
            zb = omsx_repl.run_cases(args.zb_machine, specs, batch=batch, reset=("NEW", "CLS"))
            print(f"\n--- numeric-fact: zerobas == reference ({args.zb_machine}) ---")
            for c, r in zip(ncases, zb):
                got = read_R(r)
                want = ref_val.get(c.label)
                good = got is not None and got == want
                ok = ok and good
                print(f"{'PASS' if good else 'FAIL':5} {c.label:24} zb={got!r} ref={want!r}")

    # ---------------- resume_line: RESUME <line> branches + skips intervening ---
    # RESUME <line> must branch to <line> (line 40) and SKIP the intervening
    # statement (line 30's "R< 1 ...>"). Line 40 then prints "R< ERR / ERL >": after
    # ANY RESUME the reference RESETS ERR to 0 but KEEPS ERL (empirically pinned on
    # the VG-8020, all four RESUME forms -> "0 / 20"). The ERR-reset was S2b-deferred
    # (the reference "0" vs zerobas's then-last-code) and LANDED 2026-07-19 (a 4 B
    # `xor a`/`ld (ERRCODE),a` at ex_resume's trap-active head, funded by three
    # provably-redundant `xor a` reclaims). Now GATED on BOTH machines: line-30
    # skipped, ERR reset to 0, ERL kept at 20.
    if not args.only or "resume_line" in (args.only or ""):
        rl = next(c for c in NUM_CASES if c.label == "resume_line")
        print(f"\n--- resume_line: RESUME <line> -> 40, skip 30, ERR->0, ERL kept ---")
        for machine, tag in ([(args.machine, "ref")] +
                             ([(args.zb_machine, "zb")] if not args.ref_only else [])):
            raw = omsx_repl.run_case(machine, "direct", rl.lines)
            markers = [m.strip() for m in re.findall(r"R<([^<>]*)>", raw or "")]
            skipped = not any(m.startswith("1") for m in markers)  # "R< 1 >" must NOT appear
            errerl = markers[-1] if markers else None               # "0 / 20"
            parts = [p.strip() for p in (errerl or "").split("/")]
            err_reset = len(parts) == 2 and parts[0] == "0"         # ERR reset to 0
            erl_kept = len(parts) == 2 and parts[1] == "20"         # ERL kept at 20
            good = skipped and err_reset and erl_kept
            ok = ok and good
            print(f"{'PASS' if good else 'FAIL':5} [{tag}] resume_line line-30-skipped="
                  f"{skipped} (want True); ERR/ERL-after-RESUME={errerl!r} "
                  f"(want '0 / 20': ERR reset, ERL kept)")

    # ---------------- on_error_goto_0: handler disabled ------------------------
    if not args.only or "on_error_goto_0" in (args.only or ""):
        oe0 = next(c for c in NUM_CASES if c.label == "on_error_goto_0")
        print(f"\n--- on_error_goto_0: GOTO 0 disables -> S1 abort, handler skipped ---")
        for machine, tag in ([(args.machine, "ref")] +
                             ([(args.zb_machine, "zb")] if not args.ref_only else [])):
            raw = omsx_repl.run_case(machine, "direct", oe0.lines)
            handled = "R<7>" in (raw or "")
            aborted_at_30 = in_line_number(raw) == "30"
            good = (not handled) and aborted_at_30
            ok = ok and good
            print(f"{'PASS' if good else 'FAIL':5} [{tag}] on_error_goto_0 "
                  f"handled={handled} (want False) in-line={in_line_number(raw)!r} "
                  f"(want '30')")

    # ---------------- nested forced abort: inner message -----------------------
    if not args.only or "nested" in (args.only or ""):
        print(f"\n--- nested_forced_abort: error inside handler -> forced abort, INNER msg ---")
        for machine, tag in ([(args.machine, "ref")] +
                             ([(args.zb_machine, "zb")] if not args.ref_only else [])):
            raw = omsx_repl.run_case(machine, "direct", NESTED_ABORT.lines)
            entered = "INHANDLER" in (raw or "")
            good = entered
            ok = ok and good
            print(f"{'PASS' if good else 'FAIL':5} [{tag}] nested_forced_abort "
                  f"entered-handler={entered} (want True)")
        # message text is house-style on zerobas (not diffed) -- check separately
        if not args.ref_only:
            raw = omsx_repl.run_case(args.zb_machine, "direct", NESTED_ABORT.lines)
            has_msg = "division by zero" in (raw or "").lower()
            in100 = in_line_number(raw) == "100"
            good = has_msg and in100
            ok = ok and good
            print(f"{'PASS' if good else 'FAIL':5} [zb]  nested_forced_abort "
                  f"message contains 'division by zero'={has_msg}, in-line={in_line_number(raw)!r} "
                  f"(want '100')")

    # ---------------- ON ERROR GOTO <undefined> ---------------------------------
    if not args.only or "on_error_undef" in (args.only or ""):
        print(f"\n--- on_error_undef: ON ERROR GOTO <undefined line> ---")
        for machine, tag in ([(args.machine, "ref")] +
                             ([(args.zb_machine, "zb")] if not args.ref_only else [])):
            raw = omsx_repl.run_case(machine, "direct", ON_ERROR_UNDEF.lines)
            undef = "undefined line" in (raw or "").lower()
            ok = ok and undef
            print(f"{'PASS' if undef else 'FAIL':5} [{tag}] on_error_undef "
                  f"'undefined line' present={undef} (want True)")

    # ---------------- RESUME without error (ERR 22), zerobas-only text ---------
    if not args.only or "resume_noerr" in (args.only or ""):
        print(f"\n--- resume_noerr: bare RESUME with no active trap -> ERR 22 ---")
        raw = omsx_repl.run_case(args.zb_machine, "direct", RESUME_NOERR.lines)
        has_msg = "resume without error" in (raw or "").lower()
        ok = ok and has_msg
        print(f"{'PASS' if has_msg else 'FAIL':5} [zb] resume_noerr "
              f"message contains 'resume without error'={has_msg}")

    # ---------------- ERROR n regression (S2a) ----------------------------------
    if not args.only or "error_n_regression" in (args.only or ""):
        print(f"\n--- error_n_regression: ERROR 5 still reports correctly (S2a) ---")
        raw = omsx_repl.run_case(args.zb_machine, "direct", ["ERROR 5"])
        has_msg = "illegal function call" in (raw or "").lower()
        no_inline = in_line_number(raw) is None
        good = has_msg and no_inline
        ok = ok and good
        print(f"{'PASS' if good else 'FAIL':5} [zb] error_n_regression "
              f"message={has_msg} in-line={in_line_number(raw)!r} (want None, direct mode)")

    # ---------------- ERROR n argument validation (S2a-deferred, landed 2026-07-19)
    # The faithful ERROR <n> domain is 1..255 (empirically pinned VG-8020): 0, 256,
    # and any value out of range within int16 raise ERR 5 (illegal function call),
    # while 1..255 raise that code verbatim. Straight ERR-value differential (via a
    # handler). NOTE: |n| that OVERFLOWS int16 (e.g. 32768 -> ref ERR 6 Overflow, zb
    # ERR 5) is the SEPARATE pre-existing D-F2-2 int-arg-coercion seam, out of scope
    # here (zerobas does not overflow-check int-arg coercion for any statement).
    if not args.only or "error_arg" in (args.only or ""):
        print(f"\n--- error_arg: ERROR <n> domain 1..255 else ERR 5 (int16 range) ---")
        arg_cases = ["0", "256", "-1", "1000", "32767", "-32768",  # -> 5
                     "1", "5", "200", "255"]                       # -> verbatim
        for n in arg_cases:
            prog = ["10 ON ERROR GOTO 100", f"20 ERROR {n}",
                    '100 PRINT"A<";ERR;">"', "RUN"]
            ref = omsx_repl.run_case(args.machine, "direct", prog)
            rv = (re.findall(r"A<([^<>]*)>", ref or "") or [None])[-1]
            rv = rv.strip() if rv else None
            if args.ref_only:
                print(f"  [ref] ERROR {n:>6} -> ERR {rv!r}")
                continue
            zbc = omsx_repl.run_case(args.zb_machine, "direct", prog)
            zv = (re.findall(r"A<([^<>]*)>", zbc or "") or [None])[-1]
            zv = zv.strip() if zv else None
            good = zv == rv
            ok = ok and good
            print(f"{'PASS' if good else 'FAIL':5} ERROR {n:>6} -> zb ERR {zv!r} "
                  f"ref ERR {rv!r}")

    # ---------------- err_msgtab BOUND: the last in-table code, and the first out
    # `raise_error`'s range test and the table's length are ONE FACT IN TWO PLACES,
    # and they DRIFTED: the ERR 25 entry landed with D-LINEMAX while the test stayed
    # `cp 24`, so the entry was two bytes of dead table and `ERROR 25` printed
    # `unprintable error` for the whole arc. Nothing caught it, because the only
    # raiser of 25 (program.asm dl_overflow) deliberately BYPASSES the table -- so
    # linemax-acceptance stayed 60/60 while the table was wrong. Fixed 2026-07-29;
    # THIS is the row that keeps the two places in step, and it must gate BOTH
    # directions: 25 in-table AND 26 out of it (a test that only checked 25 would
    # pass just as happily on `cp 99`).
    #
    # Message TEXT differential, compared case-insensitively -- zerobas's messages
    # are deliberately house-style lowercase (D-2), so only the WORDING is the
    # claim, never the capitalisation. (ERR 25 is the one exception: its text is the
    # reference's verbatim, see basic/missing.asm's header.) Both sides must READ
    # something: a row where both scrape None would otherwise score PASS while
    # measuring nothing.
    #
    # NOT gated here: the disk codes 50..69 (`ERROR 52` -> ref `Bad file number`,
    # zb `unprintable error`). Measured divergent 2026-07-29 and UNCHANGED by this
    # fix -- it is S-FCH-2's open item (the raisers cost 26 B over a full page 1),
    # not a bound problem.
    if not args.only or "msgtab_bound" in (args.only or ""):
        print(f"\n--- msgtab_bound: ERROR 23..26 message text (the table's last entry) ---")
        bound_cases = ["ERROR 23", "ERROR 24", "ERROR 25", "ERROR 26"]
        specs = [("direct", [c]) for c in bound_cases]
        ref = omsx_repl.run_cases(args.machine, specs, batch=batch, reset=("NEW", "CLS"))
        if args.ref_only:
            for c, r in zip(bound_cases, ref):
                print(f"  [ref] {c:<9} -> {omsx_repl.screen_tail(r, c)!r}")
        else:
            zb = omsx_repl.run_cases(args.zb_machine, specs, batch=batch,
                                     reset=("NEW", "CLS"))
            for c, r, z in zip(bound_cases, ref, zb):
                rt = omsx_repl.screen_tail(r, c)
                zt = omsx_repl.screen_tail(z, c)
                read = rt is not None and zt is not None   # neither side may be blind
                good = read and rt.lower() == zt.lower()
                ok = ok and good
                print(f"{'PASS' if good else 'FAIL':5} {c:<9} zb {zt!r} ref {rt!r}"
                      f"{'' if read else '  <- UNREADABLE on one side, not a measurement'}")

    # ---------------- D-ONEFLG: the stale in-handler flag ----------------------
    # Oracle-lock against the MEASURED want (spec §2's table) AND a differential,
    # the same shape the numeric-fact family uses. `oneflg_keep` /
    # `oneflg_suspend_resume` want the OPPOSITE of the others: they fail if the
    # clear is placed anywhere that also catches a STOP.
    ofcases = sel(ONEFLG_CASES)
    if ofcases:
        print(f"\n--- D-ONEFLG reset scope: abort/END clear it, a STOP must NOT ---")
        specs = [("direct", c.lines) for c in ofcases]
        ref = omsx_repl.run_cases(args.machine, specs, batch=batch, reset=("NEW", "CLS"))
        ref_trap = {}
        for c, r in zip(ofcases, ref):
            got = read_R(r) == "1"            # "1" only from the PRINTed marker
            ref_trap[c.label] = got
            want = ONEFLG_TRAPS[c.label]
            good = got == want
            ok = ok and good
            print(f"{'PASS' if good else 'FAIL':5} [ref] {c.label:22} trapped={got} "
                  f"(want {want})")
        if not args.ref_only:
            zb = omsx_repl.run_cases(args.zb_machine, specs, batch=batch,
                                     reset=("NEW", "CLS"))
            for c, r in zip(ofcases, zb):
                got = read_R(r) == "1"
                good = got == ref_trap[c.label] and got == ONEFLG_TRAPS[c.label]
                ok = ok and good
                print(f"{'PASS' if good else 'FAIL':5} [zb]  {c.label:22} trapped={got} "
                      f"(ref={ref_trap[c.label]}, want {ONEFLG_TRAPS[c.label]})")

    # ---------------- D-ONEFLG: the direct-RESUME readouts ---------------------
    if not args.only or "oneflg" in (args.only or ""):
        print(f"\n--- D-ONEFLG direct RESUME: ERR 22 == the flag is already 0 ---")
        # differential: after a nested forced abort BOTH machines must answer a
        # typed RESUME with "resume without error" (class, not wording -- zerobas
        # is house-style lowercase, D-2). Both sides must READ something: a row
        # where both scrape nothing would otherwise score PASS while measuring
        # nothing.
        for machine, tag in ([(args.machine, "ref")] +
                             ([(args.zb_machine, "zb")] if not args.ref_only else [])):
            raw = omsx_repl.run_case(machine, "direct", ONEFLG_RESUME_DIFF.lines)
            said = "resume without error" in (raw or "").lower()
            ok = ok and said
            print(f"{'PASS' if said else 'FAIL':5} [{tag}] oneflg_direct_resume "
                  f"'resume without error'={said} (want True)")
        # site C, zerobas-only (see ONEFLG_RESUME_ZB's note: the reference reports
        # the ERR 21 "No RESUME" that zerobas does not raise, so the text before
        # the RESUME differs for a SECOND reason and is deliberately not compared)
        if not args.ref_only:
            raw = omsx_repl.run_case(args.zb_machine, "direct", ONEFLG_RESUME_ZB.lines)
            said = "resume without error" in (raw or "").lower()
            ok = ok and said
            print(f"{'PASS' if said else 'FAIL':5} [zb]  oneflg_falloff "
                  f"'resume without error'={said} (want True -- running off the end "
                  f"of the program ends the run, so the handler context dies)")

    # ---------------- D-ONELIN: what disarms ON ERROR --------------------------
    olcases = sel(ONELIN_CASES)
    if olcases:
        print(f"\n--- D-ONELIN: the variable-clear disarm (spec §3, oracle-locked) ---")
        specs = [("direct", c.lines) for c in olcases]
        # ⚠️ run_differential, NOT two run_cases calls: `onelin_stop_cont` FLAKED
        # exactly once in a shared boot (zb scored "did not fire"; boot-per-case it
        # fires on both machines, as does the whole matrix). A row whose case
        # SUSPENDS a run and resumes it from the prompt has two extra REPL round
        # trips to be raced on a batched timeline. The self-heal re-runs any row
        # that misses the oracle-lock boot-per-case, so the verdicts equal a full
        # boot-per-case run and a flake costs one pair of boots, not a red gate.
        def ol_ok(i, r, z):
            want = ONELIN_FIRES[olcases[i].label]
            return (read_R(r) == "1") == want and (read_R(z) == "1") == want
        if args.ref_only:                       # oracle-lock only
            ref = omsx_repl.run_cases(args.machine, specs, batch=batch,
                                      reset=("NEW", "CLS"))
            zb, verdicts = [None] * len(ref), [
                (read_R(r) == "1") == ONELIN_FIRES[c.label]
                for c, r in zip(olcases, ref)]
        else:
            verdicts, ref, zb = omsx_repl.run_differential(
                args.machine, args.zb_machine, specs, ol_ok,
                batch=batch, reset=("NEW", "CLS"))
        for c, r, z, v in zip(olcases, ref, zb, verdicts):
            want = ONELIN_FIRES[c.label]
            ok = ok and v
            zbs = "n/a" if args.ref_only else str(read_R(z) == "1")
            print(f"{'PASS' if v else 'FAIL':5} {c.label:26} "
                  f"ref={read_R(r) == '1'} zb={zbs} (want {want})")

    # ---------------- D-ONELIN: the stale-pointer row, judged on the LINE ------
    if not args.only or "onelin" in (args.only or ""):
        print(f"\n--- D-ONELIN edit_insert: judged on the ABORT LINE, not the marker ---")
        for machine, tag in ([(args.machine, "ref")] +
                             ([(args.zb_machine, "zb")] if not args.ref_only else [])):
            raw = omsx_repl.run_case(machine, "direct", ONELIN_INSERT.lines)
            fired = read_R(raw) == "1"
            line = in_line_number(raw)
            good = (not fired) and line == "10"
            ok = ok and good
            print(f"{'PASS' if good else 'FAIL':5} [{tag}] onelin_edit_insert "
                  f"fired={fired} (want False) abort-line={line!r} (want '10' -- a "
                  f"stale ONELIN branches WILD into the moved text and reports a "
                  f"line that does not exist)")

    # ---------------- §7 reset-scope: RAW differential, no hardcoded want ------
    rscases = sel(RESET_SCOPE_CASES)
    if rscases:
        print(f"\n--- §7 reset-scope (ANSWERED by D-ONELIN; oracle-locked) ---")
        specs = [("direct", c.lines) for c in rscases]
        ref = omsx_repl.run_cases(args.machine, specs, batch=batch, reset=("NEW", "CLS"))
        for c, r in zip(rscases, ref):
            got = read_R(r) == "1"
            want = RESET_SCOPE_FIRES[c.label]
            good = got == want
            ok = ok and good
            print(f"{'PASS' if good else 'FAIL':5} [ref] {c.label:20} "
                  f"handler-fired={got} (want {want})")
        if not args.ref_only:
            zb = omsx_repl.run_cases(args.zb_machine, specs, batch=batch, reset=("NEW", "CLS"))
            for c, r, rr in zip(rscases, zb, ref):
                got = read_R(r) == "1"
                want = RESET_SCOPE_FIRES[c.label]
                good = got == (read_R(rr) == "1") and got == want
                ok = ok and good
                print(f"{'PASS' if good else 'FAIL':5} [zb]  {c.label:20} "
                      f"handler-fired={got} (ref={read_R(rr) == '1'}, want {want})")

    print("\nALL PASS" if ok else "\nSOME FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
