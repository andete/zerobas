#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""D-ONERR0 — `ON ERROR GOTO 0` executed INSIDE an active handler RE-RAISES.

D-NXARY (2026-08-08) filed the rule from ONE row that was measuring something
else (`docs/nxary-msx1-characterization.md` §3): its first `a.autodim` disarmed
with `ON ERROR GOTO 0` before a `DIM`, both references answered `NEXT without
FOR` and zerobas ran on. A clean 3-side divergence, and an answer to a question
nobody asked ([[readout-blind-to-its-own-subject]]).

🔴 ONE ROW IS NOT A RULE, AND THAT ROW HAS SINCE ROTTED WITHOUT THE RULE
MOVING. Re-measured 2026-08-09 (`docs/todo-staleness-sweep-2026-08.md` §4.6) it
reads `Redimensioned array in 60` on zerobas, not `[OK]` — because D-NXARY's own
auto-DIM now creates `A(0..10)` at the `NEXT`, so the `DIM A(3)` two lines later
is a redimension. The swallow is intact; the row that reported it is not. **So
every program below is array-free**: the error is raised by `ERROR n`, which no
later slice of the arrays arc can reach.

THE DENOMINATOR — each bullet is a question a fix has to answer, and the filed
row asks exactly none of them:

  1. 🎯 WHICH ERROR IS RE-RAISED — the ORIGINAL, or a fresh one? `r.code` swaps
     the payload code, so a fix that re-raises a CONSTANT reads differently from
     one that re-raises `ERRFLG`.
  2. 🎯 WHICH LINE DOES IT REPORT? `r.line` puts the handler BEFORE the erroring
     line, so `in <erroring line>` and `in <handler line>` are different numbers
     and the message says which. zerobas' abort prints CURLINE, and at the
     `ON ERROR GOTO 0` CURLINE is the HANDLER — so this row is the one that
     decides whether the fix has to restore a saved context or merely raise.
  3. WHEN does it fire — immediately, or at the end of the statement/line?
     `r.mid` puts a `PRINT` after the colon.
  4. 🎯 IS DISARMING SPECIAL, OR DOES ANY `ON ERROR` INSIDE A HANDLER RE-RAISE?
     `r.rearm` arms a DIFFERENT line from inside the handler. This is the whole
     discriminator between "the rule is about `GOTO 0`" and "the rule is about
     `ON ERROR`", and no filed row touches it.
  5. DEPTH. `r.depth` disarms inside a `GOSUB` called BY the handler.
  6. WHAT ENDS THE HANDLER STATE. `r.afterres` disarms AFTER a `RESUME NEXT`
     has already left the handler — it must be a plain disarm, which is what
     says the rule is keyed on the IN-HANDLER state and not on "an error
     happened". `c.disarm`/`c.never` are the same claim from outside.
  7. `ERR`/`ERL` AFTER THE FACT (`e.*`, a direct `PRINT ERR;ERL` typed at the
     prompt the abort returns to). 🎯 `e.trap` is the one that answers the
     brief's open question — falling off the END of a handler reports
     `No RESUME in <line>`, and whether that is a REPORT or a trappable ERROR is
     readable only as `ERR` = the original code vs 21.
  8. DIRECT MODE. `d.plain` (no handler, must stay a no-op) and `d.instop` (the
     handler is SUSPENDED by a `STOP`, so the in-handler state is live at the
     prompt — the only way to type `ON ERROR GOTO 0` from inside a handler).

🟢 THE POSITIVE CONTROLS ARE LOAD-BEARING, NOT DECORATION.
  * `c.untrap` — `ERROR 7` with no handler at all: the untrapped-abort FACE the
    re-raise has to produce. Without it every `r.*` row has two causes
    ([[row-with-two-candidate-causes]]).
  * `c.trap`   — the trap itself, and the fall-off-the-end report. The brief's
    load-bearing control: it fires identically on all three sides, so any
    divergence below belongs to `ON ERROR GOTO 0` and to nothing else.
  * `c.resume` — the handler machinery a fix reuses (`RESUME NEXT`).
  * `c.disarm` — `ON ERROR GOTO 0` OUTSIDE a handler: the plain-disarm arm that
    must NOT move.
  * `c.never`  — `ON ERROR GOTO 0` with no handler ever armed: a no-op.
  A control failure exits 2 (the instrument broke), never 1 (a regression).

🔴 `r.nested` IS THE NEGATIVE CONTROL. A SECOND error raised inside a handler is
already a forced abort with the INNER message on all three sides. The danger of
this slice is a fix that re-raises the OUTER error there too, or that reaches
any statement other than `ON ERROR GOTO 0`. It must stay `Subscript out of
range in <handler line>`.

THE READING is `screen_tail` — every row between the echoed command and the
closing prompt, `|`-joined. NOT `result_span`: the subject of this slice IS the
error message and its line number, so a reading that keeps only a `[...]` value
is structurally blind to it ([[readout-blind-to-its-own-subject]]).

⚠️ Every erroring row is a STORED program driven by `RUN`. In direct mode an
abort on one line does not stop the next, so a tail anchored on a closing
`PRINT` reads a value where a reference stopped — two false verdicts during the
staleness sweep (`docs/todo-staleness-sweep-2026-08.md` §2.1).

Clean-room: observed screen output only; both reference ROMs are black boxes.
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
import probe_report                                              # noqa: E402

ZB_MACHINE = os.environ.get("ZEROBAS_BASIC_MACHINE",
                            "C-BIOS_MSX1_EU_REPACK_DISK")
REPO = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
TEST_DSK = os.path.join(REPO, "disk", "test720.dsk")

# ⚠️ `diska` is a /tmp COPY, never the committed image: nothing here writes to a
# disk, but a reference ROM that decided to would corrupt a tracked file.
SIDES = {
    "vg8020": dict(machine="Philips_VG_8020", boot=8.0, step=2.5,
                   reset=("NEW", "CLS"), diska=False),
    "cf3300": dict(machine="National_CF-3300", boot=14.0, step=4.5,
                   reset=("", "SCREEN 0", "NEW", "CLS"), diska=True),
    "zb":     dict(machine=ZB_MACHINE, boot=8.0, step=2.5,
                   reset=("NEW", "CLS"), diska=True),
}

ERRERL = 'PRINT"[";ERR;",";ERL;"]"'

# (label, [stored body lines], [extra DIRECT lines after RUN])
# Body lines are numbered 10, 20, 30, ... by position, so every line number
# named inside a program is 10 x its 1-based position in that list.
# The reading is the screen_tail of `RUN` (when there is a body) followed by the
# screen_tail of each extra direct line, joined with ' >> '.
CASES = [
    # --- 🟢 positive controls -----------------------------------------------
    # the untrapped-abort FACE, with no handler in the picture at all
    ("c.untrap",  ['ERROR 7',
                   'PRINT"[NO]"'], []),
    # 🎯 THE BRIEF'S LOAD-BEARING CONTROL: the trap fires identically on all
    # three sides, so the divergence below belongs to ON ERROR GOTO 0 alone.
    ("c.trap",    ['ON ERROR GOTO 40',
                   'ERROR 7',
                   'PRINT"[NO]"',
                   'PRINT"[TRAPPED]"'], []),
    # the handler machinery a fix REUSES
    # 🔴 THE FIRST DRAFT HAD NO `END` AND FAILED AS A CONTROL ON ALL THREE
    # SIDES, reading `[RESUMED]|RESUME without error in 40`: `RESUME NEXT`
    # lands on line 30, which then FALLS INTO the handler, where a second
    # RESUME with no error active is ERR 22. Identical on all three sides, so
    # it was the FIXTURE and not a divergence -- classify a control failure by
    # WHICH SIDE failed it ([[classify-a-control-failure-by-which-side-failed-
    # it]]). It is the same two-sufficient-causes trap D-DOTLINE's `clp-trap`
    # fell into, in the same file, over the same idiom.
    ("c.resume",  ['ON ERROR GOTO 50',
                   'ERROR 7',
                   'PRINT"[RESUMED]"',
                   'END',
                   'RESUME NEXT'], []),
    # 🔴 THE ROW A KNIFE DEMANDED, AND THE ONLY ONE THAT GUARDS `res_ctx`.
    # This slice re-extracts `res_ctx` (basic/interp.asm) so the re-raise can
    # share RESUME's leave-the-handler restore. K-O3 breaks that restore and
    # predicted `c.resume` would fail -- and it reddened NOTHING, twice.
    # 🎯 BECAUSE `RESUME NEXT` DOES NOT USE `res_ctx`. `res_next` marshals to a
    # sub-ROM tenant that does the identical prep sub-side, so `c.resume` was
    # never a control for the routine this slice touched, and the shared engine
    # was being refactored with NO row over its other caller
    # ([[a-shared-engine-fix-must-measure-its-other-callers]]).
    # Bare `RESUME` re-executes the FAILING statement, so the handler has to fix
    # the condition first or it loops forever: `A$` starts empty, `ASC(A$)` is
    # ERR 5, the handler sets `A$="Z"` and resumes, and line 20 then succeeds.
    ("c.resume0", ['ON ERROR GOTO 50',
                   'B=ASC(A$)',
                   'PRINT"[DONE]"',
                   'END',
                   'A$="Z":RESUME'], []),
    # ON ERROR GOTO 0 OUTSIDE a handler -- a plain disarm, and it must stay one
    ("c.disarm",  ['ON ERROR GOTO 50',
                   'ON ERROR GOTO 0',
                   'ERROR 7',
                   'PRINT"[NO]"',
                   'PRINT"[TRAPPED]"'], []),
    # ON ERROR GOTO 0 with no handler EVER armed -- a no-op
    ("c.never",   ['ON ERROR GOTO 0',
                   'PRINT"[OK]"'], []),
    # --- 1. WHICH ERROR IS RE-RAISED ----------------------------------------
    # 🎯 THE HEADLINE ROW, RE-PAYLOADED. The filed version used `NEXT A(1)` and
    # a `DIM`, and D-NXARY's auto-DIM rotted it four hours later. Nothing here
    # touches an array.
    ("r.reraise", ['ON ERROR GOTO 40',
                   'ERROR 7',
                   'PRINT"[NO]"',
                   'ON ERROR GOTO 0',
                   'PRINT"[RANON]"'], []),
    # the SAME program with a different payload code: a fix that re-raises a
    # constant reads identically on r.reraise and differently here
    ("r.code",    ['ON ERROR GOTO 40',
                   'ERROR 9',
                   'PRINT"[NO]"',
                   'ON ERROR GOTO 0',
                   'PRINT"[RANON]"'], []),
    # --- 2. 🎯 WHICH LINE DOES IT REPORT ------------------------------------
    # The handler is at 30, the error at 50. `in 50` and `in 30` are different
    # numbers, so the message itself says whether the re-raise reports the
    # ERRORING line or the line the re-raise is IN. zerobas' abort prints
    # CURLINE, which at the ON ERROR GOTO 0 is the HANDLER -- so this row is
    # what decides whether a fix must restore a saved context.
    ("r.line",    ['ON ERROR GOTO 30',
                   'GOTO 50',
                   'ON ERROR GOTO 0',
                   'PRINT"[RANON]"',
                   'ERROR 7',
                   'PRINT"[NO]"'], []),
    # --- 3. WHEN does it fire ------------------------------------------------
    ("r.mid",     ['ON ERROR GOTO 40',
                   'ERROR 7',
                   'PRINT"[NO]"',
                   'ON ERROR GOTO 0:PRINT"[AFTER]"'], []),
    # --- 4. 🎯 IS DISARMING SPECIAL, OR DOES ANY `ON ERROR` RE-RAISE? -------
    # re-arm to 70 from inside the handler. If ON ERROR *re-arms*, 50 prints
    # [REARM] and 60 resumes to 80 -> [DONE]. If any ON ERROR inside a handler
    # RE-RAISES, the raise meets the freshly-armed 70 -> [RETRAP], or aborts.
    # Three outcomes, three different readings, and no filed row asks.
    ("r.rearm",   ['ON ERROR GOTO 40',
                   'ERROR 7',
                   'PRINT"[NO]"',
                   'ON ERROR GOTO 70',
                   'PRINT"[REARM]"',
                   'RESUME 80',
                   'PRINT"[RETRAP]"',
                   'PRINT"[DONE]"'], []),
    # --- 5. DEPTH ------------------------------------------------------------
    ("r.depth",   ['ON ERROR GOTO 40',
                   'ERROR 7',
                   'PRINT"[NO]"',
                   'GOSUB 70',
                   'PRINT"[RANON]"',
                   'END',
                   'ON ERROR GOTO 0',
                   'RETURN'], []),
    # --- 6. WHAT ENDS THE HANDLER STATE -------------------------------------
    # RESUME NEXT leaves the handler and lands on 30, which disarms. If the rule
    # were "an error happened" rather than "we are inside a handler", this would
    # re-raise too. It must read [OK].
    ("r.afterres", ['ON ERROR GOTO 60',
                    'ERROR 7',
                    'ON ERROR GOTO 0',
                    'PRINT"[OK]"',
                    'END',
                    'RESUME NEXT'], []),
    # --- 🔴 the NEGATIVE control --------------------------------------------
    # a SECOND error inside the handler is a forced abort with the INNER
    # message. A fix that re-raises the OUTER error here has over-reached.
    ("r.nested",  ['ON ERROR GOTO 40',
                   'ERROR 7',
                   'PRINT"[NO]"',
                   'ERROR 9',
                   'PRINT"[NO2]"'], []),
    # --- 7. `ERR` / `ERL` AFTER THE FACT ------------------------------------
    # the untrapped baseline: what ERR/ERL look like after an ordinary abort
    ("e.untrap",  ['ERROR 7',
                   'PRINT"[NO]"'], [ERRERL]),
    # 🎯 IS `No RESUME` A REPORT OR A TRAPPABLE ERROR? Falling off the end of
    # the handler prints `No RESUME in <line>`; ERR = 7 says the report left the
    # original error standing, ERR = 21 says it raised one of its own.
    ("e.trap",    ['ON ERROR GOTO 40',
                   'ERROR 7',
                   'PRINT"[NO]"',
                   'PRINT"[TRAPPED]"'], [ERRERL]),
    # after the re-raise: does the re-raised error keep the original code/line?
    ("e.reraise", ['ON ERROR GOTO 40',
                   'ERROR 7',
                   'PRINT"[NO]"',
                   'ON ERROR GOTO 0',
                   'PRINT"[RANON]"'], [ERRERL]),
    # and after a plain disarm, for the difference to mean something
    ("e.disarm",  ['ON ERROR GOTO 50',
                   'ON ERROR GOTO 0',
                   'ERROR 7',
                   'PRINT"[NO]"',
                   'PRINT"[TRAPPED]"'], [ERRERL]),
    # --- 🎯 THE ROW THAT DECIDES BETWEEN TWO DESIGNS -------------------------
    # Two mechanisms produce every other reading in this battery and they are
    # NOT the same mechanism:
    #   (a) RESTORE-AND-ABORT  — put CURLINE/SAVTXT back from ERRRESUME and
    #       jump into raise_error past record_errline;
    #   (b) DISARM-AND-RESUME  — hand the erroring statement back to the run
    #       loop with the handler now disarmed, so it RAISES AGAIN by itself.
    # (b) RE-EXECUTES the failing statement, so any output that statement
    # emitted BEFORE erroring is emitted TWICE. `PRINT"[X]";ASC("")` is one
    # statement that prints and then fails, so `[X][X]` says (b) and `[X]` says
    # (a). Nothing else in this battery can tell them apart -- both designs
    # answer every other row identically ([[a-priced-decline-is-a-claim-about-
    # a-design]]).
    ("r.reexec",  ['ON ERROR GOTO 40',
                   'PRINT"[X]";ASC("")',
                   'PRINT"[NO]"',
                   'ON ERROR GOTO 0',
                   'PRINT"[RANON]"'], []),
    # --- 🔴 the CONT question the fix's own SHAPE raises ---------------------
    # An untrapped abort RECORDS a CONT resume point (D-CONTR: `ra_abort` hands
    # `cont_record` the FAILING statement's own SAVTXT). A re-raise therefore
    # has TWO context cells to think about, not one: CURLINE decides the line
    # the message names, SAVTXT decides where a later CONT lands. This row is
    # what says whether the second one is load-bearing or free to skip -- i.e.
    # whether the fix costs 6 more bytes than the message alone needs.
    ("k.cont",    ['ON ERROR GOTO 40',
                   'ERROR 7',
                   'PRINT"[NO]"',
                   'ON ERROR GOTO 0',
                   'PRINT"[RANON]"'], ['CONT']),
    # --- 8. DIRECT MODE ------------------------------------------------------
    # no handler, typed at the prompt: a no-op
    ("d.plain",   [], ['ON ERROR GOTO 0', 'PRINT"[OK]"']),
    # a handler armed by a RUN that has ENDed, then an error typed at the
    # prompt: does a DIRECT-mode error trap at all? This is the precondition
    # for the question d.instop asks.
    ("d.direrr",  ['ON ERROR GOTO 30',
                   'END',
                   'PRINT"[TRAPPED]"'], ['ERROR 7', 'PRINT"[AFTER]"']),
    # 🎯 THE ONLY WAY TO TYPE `ON ERROR GOTO 0` FROM INSIDE A HANDLER. The
    # handler STOPs, which SUSPENDS the run with the in-handler state live
    # (zerobas keeps it deliberately so CONT can resume inside a handler --
    # basic/sysvars.inc ONEFLG). Then the disarm is typed at the prompt.
    ("d.instop",  ['ON ERROR GOTO 40',
                   'ERROR 7',
                   'PRINT"[NO]"',
                   'STOP'], ['ON ERROR GOTO 0', 'PRINT"[OK]"']),
    # 🎯 THE DEGENERATE CONTEXT, and it is a PRICE question. Here the ERRORING
    # statement is itself the typed one, so the context a re-raise restores is
    # the DIRECT line -- whose lineno field is never initialised in this build
    # (basic/program.asm print_in_lineno). If the reference names no line here,
    # a fix may not simply force run mode: it has to DERIVE the mode from the
    # restored CURLINE the way rp_exec does, which is 11 B rather than 4.
    ("d.dirtrap", ['ON ERROR GOTO 30',
                   'END',
                   'ON ERROR GOTO 0',
                   'PRINT"[RANON]"'], ['ERROR 7', 'PRINT"[AFTER]"']),
]

CONTROLS = ("c.untrap", "c.trap", "c.resume", "c.resume0", "c.disarm",
            "c.never")

# 🔴 THESE ARE PREDICTIONS THAT WERE WRITTEN DOWN BEFORE THE FIRST RUN and then
# CORRECTED where they missed -- see docs/onerr0-msx1-characterization.md §2,
# which records every miss. A control's expectation is not allowed to be
# back-filled silently from the result column
# ([[a-prediction-copied-into-the-result-column]]).
CONTROL_WANT = {
    "c.untrap":  "Out of memory in 10",
    # 🔴 PREDICTED 'TRAPPED|No RESUME in 40' AND MISSED, on the READING and not
    # on the behaviour: `PRINT"[TRAPPED]"` emits the brackets, and this probe's
    # reading is the screen tail, not a result_span that strips them. Corrected
    # from the measurement, and the miss is recorded rather than absorbed.
    "c.trap":    "[TRAPPED]|No RESUME in 40",
    # 🔴 PREDICTED '[RESUMED]' AND MISSED ON THE PROGRAM: see c.resume's own
    # note. Corrected by adding the `END`, not by widening the expectation.
    "c.resume":  "[RESUMED]",
    "c.resume0": "[DONE]",
    "c.disarm":  "Out of memory in 30",
    "c.never":   "[OK]",
}

# Rows the fix must NOT move. Each is a shape adjacent to the rule, already
# agreeing on all three sides, that an over-reaching fix would redden.
NEGATIVE = {
    "r.nested": "NEGATIVE CONTROL — the INNER message, and it must stay",
    # 🎯 MEASURED GREEN ON ALL THREE SIDES 2026-08-09, and that reading is what
    # SCOPES the whole slice: `ON ERROR GOTO <n>` inside a handler RE-ARMS and
    # runs on. DISARMING IS SPECIAL. A fix keyed on `ON ERROR` rather than on
    # `GOTO 0` reddens this row.
    "r.rearm":  "NEGATIVE CONTROL — re-arming is NOT re-raising",
}
LABEL_W = 11

# --- DEFERRED: measured, printed, NEVER scored ------------------------------
# ✅ EMPTY SINCE D-LOCARG (2026-08-09) — and emptied by FIXING the two rows, not
# by rescoring them. `d.instop` and `d.dirtrap` were the same missing piece,
# `DIRECTF`: the re-raise restores the erroring statement's CURLINE and SAVTXT
# and aborts through `rerr_msg`, which never passes `rp_exec` — and `rp_exec`
# was the ONLY place that DERIVED `DIRECTF` from `CURLINE`'s high byte. So the
# mode cell kept whatever the RE-RAISING statement had:
#   d.instop   the disarm is TYPED (DIRECTF=1) but the error was a STORED line,
#              so the suffix was suppressed:  `Out of memory`  vs  `... in 20`.
#   d.dirtrap  the disarm is in a STORED handler (DIRECTF=0) but the error was
#              TYPED, so a suffix was printed from the direct line's own lineno
#              field:  `Out of memory in 0`  vs a bare `Out of memory`.
# 🎯 THEY FAILED IN OPPOSITE DIRECTIONS, which is what said the answer was a
# DERIVE and not a constant: forcing DIRECTF:=0 fixed d.instop and broke
# d.dirtrap, and forcing 1 did the reverse. `derive_directf` (basic/program.asm)
# is that derive, extracted and called from both places; the constant is
# falsified live by knife K-LA3 (docs/spec-basic-locarg.md §8).
# 💰 THE PRICE WAS PREDICTED AT +7 B AND LANDED AT +7 B, funded by the -29 B
# `loc_next` carve in the same slice (docs/spec-basic-locarg.md §6).
# An EMPTY dict is a CLAIM — "nothing here is measured-but-unscored" — and the
# footer states it on every run, so it cannot lapse quietly.
DEFERRED: dict[str, str] = {}

SENTINELS = ("<NO CAPTURE>", "<NO ECHO>")


def clip_at_prompt(tail: str) -> str:
    """Drop everything from the first row that BEGINS with a prompt token.

    🔴 THE READING WAS NOT MACHINE-AGNOSTIC AND ONLY THE SIDE UNDER TEST COULD
    SEE IT. `omsx_repl.screen_tail` ends its span at a row that IS a prompt
    (`PROMPTS = ("Ok", "ZB")`) — true on both references, where `Ok` sits alone
    on its line. zerobas emits `ZB` with no trailing newline, so the prompt and
    the NEXT echoed line share one row (`ZBPRINT"[OK]"`), no row ever equals a
    prompt, and the span ran to the bottom of the screen. Measured 2026-08-09:
    every zb reading carried its own later echoes, so all three sides diverged
    on rows where the machines agree — a readout failing on the shape of the
    side it exists to measure. Clipped HERE and not in `omsx_repl`: 24 gated
    probes read that helper, and widening the shared span rule is its own
    slice with its own denominator."""
    out = []
    for row in tail.split("|"):
        if any(row.startswith(p) for p in omsx_repl.PROMPTS):
            break
        out.append(row)
    return "|".join(out)


def read_case(raw: str | None, anchors: list[str]) -> str:
    """The clipped screen_tail of each anchor, joined with ' >> '.

    🔴 screen_tail, NOT result_span: the SUBJECT here is the error message and
    its line number, and a `[...]`-only reading cannot see either."""
    if raw is None:
        return "<NO CAPTURE>"
    parts = []
    for a in anchors:
        t = omsx_repl.screen_tail(raw, a)
        parts.append("<NO ECHO>" if t is None else clip_at_prompt(t))
    return " >> ".join(parts)


def run_side(side: str, only: list[str]) -> dict:
    cfg = SIDES[side]
    out = {}
    for label, body, tails in CASES:
        if only and label not in only:
            continue
        kw = {}
        if cfg["diska"]:
            dsk = os.path.join(tempfile.gettempdir(),
                               f"zb_onerr0_{side}_{label}.dsk")
            shutil.copy(TEST_DSK, dsk)
            kw["diska"] = dsk
        prog = [f"{10 * (k + 1)} {ln}" for k, ln in enumerate(body)]
        lines = list(cfg["reset"]) + prog + (["RUN"] if prog else []) + tails
        anchors = (["RUN"] if prog else []) + list(tails)
        caps = omsx_repl.run_cases(
            cfg["machine"], [("direct", lines)],
            batch=False, boot=cfg["boot"], step=cfg["step"], **kw)
        out[label] = read_case(caps[0], anchors)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(
        description="D-ONERR0: ON ERROR GOTO 0 inside a handler re-raises")
    ap.add_argument("--sides", default="vg8020,cf3300,zb")
    ap.add_argument("--only", default="")
    ap.add_argument("--gate", action="store_true",
                    help="exit 1 unless every row agrees across sides")
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

    print("D-ONERR0 — ON ERROR GOTO 0 inside a handler RE-RAISES   "
          f"sides: {', '.join(sides)}")
    print("=" * 78)

    bad = []
    for ctl in CONTROLS:
        if ctl not in present:
            continue
        for s in sides:
            got = results[s].get(ctl)
            if got != CONTROL_WANT[ctl]:
                bad.append((ctl, s, got))
    if bad:
        for lab, s, got in bad:
            print(probe_report.row("FAIL", lab, LABEL_W, {s: got},
                                   "   [POSITIVE CONTROL]"))
            print(f"        wanted {CONTROL_WANT[lab]!r}")
        print("\n*** A POSITIVE CONTROL FAILED, so nothing below it was "
              "measured.\n"
              "    c.untrap = `ERROR 7`, no handler -- the untrapped-abort "
              "FACE the re-raise\n"
              "               must produce. Red here and every r.* row has two "
              "causes.\n"
              "    c.trap   = the trap + the fall-off-the-end report. Red here "
              "and the\n"
              "               divergence is NOT about ON ERROR GOTO 0.\n"
              "    c.resume = RESUME NEXT, the handler machinery a fix reuses.\n"
              "    c.disarm = ON ERROR GOTO 0 OUTSIDE a handler -- the plain "
              "disarm.\n"
              "    c.never  = ON ERROR GOTO 0 with no handler ever armed.\n"
              "    🔴 CLASSIFY BY WHICH SIDE FAILED: red on a REFERENCE is a "
              "broken fixture\n"
              "    (report it, score nothing); red on zb is an ordinary "
              "divergence that\n"
              "    belongs in the row set, not in the control set.\n"
              "    Check build/*.rom, `make repack-machine` and the injector "
              "(`make\n"
              "    latch-check`), THEN re-read the rows. Exit 2 (not 1) = the "
              "instrument\n"
              "    was broken, NOT a regression.")
        for lab in present:
            vals = {s: results[s][lab] for s in sides if lab in results[s]}
            print(probe_report.row("....", lab, LABEL_W, vals,
                                   "   (not scored)"))
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
        print(f"{n} row(s) on {sides[0]} — no agreement verdict from one side")
        return 0

    agree = dis = refsplit = deferred = 0
    for lab in present:
        vals = {s: results[s][lab] for s in sides if lab in results[s]}
        ok = len(set(vals.values())) == 1 and len(vals) > 1
        if any(v in SENTINELS for v in vals.values()):
            ok = False
        refs = {vals[s] for s in ("vg8020", "cf3300") if s in vals}
        if lab in DEFERRED:
            deferred += 1
            print(probe_report.row("....", lab, LABEL_W, vals,
                                   f"   [{DEFERRED[lab]}]"))
            continue
        agree += ok
        dis += not ok
        note = "   [POSITIVE CONTROL]" if lab in CONTROLS else ""
        if lab in NEGATIVE:
            note = f"   [{NEGATIVE[lab]}]"
        if len(refs) > 1:
            refsplit += 1
            note += "   [REFERENCES DISAGREE — no oracle for this row]"
        print(probe_report.row("ok" if ok else "DIFF", lab, LABEL_W, vals, note))

    print(probe_report.footer(len(present), len(present) - deferred,
                              f"{agree} agree, {dis} diverge, "
                              f"{deferred} deferred (not scored)"))
    print("=" * 78)
    print(f"{agree}/{agree + dis} readings agree "
          f"({len(CASES)} cases, {len(CONTROLS)} positive controls, "
          f"{len(NEGATIVE)} negative control, "
          f"{refsplit} row(s) with no oracle, "
          f"{len(DEFERRED)} DEFERRED row(s) measured but not scored)")
    print("SIDES: vg8020,cf3300,zb — ON ERROR / RESUME / ERROR n / ERR / ERL "
          "are core MSX-BASIC, present on every MSX1, so BOTH references are "
          "legitimate oracles for every row here")
    print("DENOMINATOR: (WHICH error is re-raised: code 7 vs code 9) x (WHICH "
          "line it reports: handler-before-error vs handler-after-error) x "
          "(WHEN: immediately vs end of statement) x (WHICH `ON ERROR`: GOTO 0 "
          "vs GOTO n, the disarm-is-special discriminator) x (DEPTH: handler "
          "top level vs inside a GOSUB it called) x (HANDLER STATE: entered / "
          "left by RESUME / never entered / suspended by STOP) x (MODE: stored "
          "vs direct), plus ERR/ERL read at the prompt after four different "
          "endings — which is also what says whether `No RESUME` is a REPORT "
          "or an ERROR — plus the SECOND-error-inside-a-handler rule that must "
          "not move")
    if a.gate and dis:
        sys.stderr.write(f"onerr0: {dis} reading(s) diverge\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
