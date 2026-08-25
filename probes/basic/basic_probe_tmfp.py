#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""D-TMFP — when a type fault and a numeric fault are BOTH pending, the one
that happened FIRST is reported.

D-LOCARG filed `t.tmfp` (`LOCATE STR$(1/0),3` -> ERR 11 on both references,
ERR 13 here) as "a pending numeric fault outranks TMISMATCH too", and priced
the fix as a REORDER of `check_expr_errors` -- test FPERR ahead of TMISMATCH.

🔴 THAT RULE IS REFUTED BY A ROW THAT ALREADY SHIPS GREEN. D-EVALCHK §5.1 froze
the opposite constraint on `dfe-tmfp` (`WIDTH (A$<5)+0*(1/0)` -> ERR 13 on both
references), which ALSO has both flags live. Two rows, both flags, opposite
answers. No STATIC test order can satisfy both, so the reorder does not fix a
bug -- it trades one for another.

🎯 THE AXIS THAT SEPARATES THEM IS TIME, AND THIS PROBE IS BUILT ON IT. The two
rows differ only in WHICH FAULT OCCURS FIRST during evaluation:

    WIDTH (A$<5)+0*(1/0)     type fault first     -> 13
    WIDTH 0*(1/0)+(A$<5)     numeric fault first  -> 11     [measured here]
    WIDTH 0*SQR(-1)+(A$<5)   numeric fault first  ->  5     [a DIFFERENT code]
    LOCATE STR$(1/0),3       numeric fault first  -> 11

The references raise EAGERLY -- there is no ranking rule on the reference at
all, because the first fault aborts on the spot and the second never happens.
zerobas emulates eager errors with two STICKY FLAGS plus a static test order,
and a static order can only ever approximate a rule that is about time. The
`SQR(-1)` pair is what makes this a rule about ORDER and not about division:
the winning code changes with the operand, not with the operator.

WHAT THIS COSTS TO GET RIGHT IS ONE SITE, WHICH IS WHY THE REORDER'S DENOMINATOR
WAS THE WRONG ONE TO WORRY ABOUT. `TMISMATCH` has exactly ONE writer
(`type_mismatch_set`, basic/str-engine.asm) and both flags are cleared together
at `exec_stmt` (basic/interp.asm), so "did the numeric fault come first?" is
readable at the moment the type fault is marked: FPERR is already non-zero.
The type fault then simply does not arm, and EVERY reader of TMISMATCH -- not
just `check_expr_errors` -- reports the numeric fault that really did come
first.

⚠️ AND THAT IS THE REAL DENOMINATOR, WHICH IS NOT THE ONE THE FILED ITEM NAMED.
The filed item counted "four other callers of `check_expr_errors`". The tree has
TWELVE `check_expr_errors` sites, a SECOND hand-rolled copy of the same ordering
in `check_expr_errors_popbc`, a THIRD in `ex_let_arr` (basic/arrays.asm), and
FOUR further readers of `TMISMATCH` that never consult FPERR at all:

    basic/files.asm    fch_check      the string-channel test for all 12 file verbs
    basic/expr.asm     ev_ff_ckpdl    PDL's domain check defers to a type fault
    basic/expr.asm     ev_mc_arg_checked   "Z iff FPERR==0 AND TMISMATCH==0"
    basic/str-engine.asm  sfr_argok   HEX$/OCT$'s argument check

A fix that changes WHEN the flag is set moves all of them, so all of them are
measured here -- both flags pending AND each flag alone, the second being the
negative control that must not move.

TWO READINGS, ONE GRAMMAR.

  * `o.*` / `n.*` / `r.*` rows are TRAPPED and read `[ ERR ]` from inside the
    handler, before anything prints. Every program does a runtime `CLS` first,
    so the only `[` on the screen is the one it printed.
  * `u.*` rows are UNTRAPPED and read the clipped `screen_tail` of `RUN` -- the
    message TEXT, its line number, whether it printed ONCE, and whether the
    next line ran. A code-only reading is structurally blind to all four
    ([[readout-blind-to-its-own-subject]]).

⚠️ Every row is a STORED program driven by `RUN`. In direct mode an abort on one
line does not stop the next, so a tail anchored on a closing `PRINT` reads a
value where a reference stopped (`docs/todo-staleness-sweep-2026-08.md` §2.1).

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
import probe_signal                                              # noqa: E402

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

# The TRAPPED program. `stmt` runs at line 20; the handler captures ERR BEFORE
# anything is printed and RESUMEs at the printer.
# ⚠️ Line 30 exists so the NO-ERROR path reaches the same printer at the same
# point; E=0 there is distinguishable from every real error code.
# ⚠️ Only E is used by the scaffold. Row statements use V / Q$ / W(), so a row
# can never collide with the handler's own capture.
TRAP_PROG = [
    "10 ON ERROR GOTO 100",
    "20 {stmt}",
    "30 E=0",
    '40 PRINT"[";E;"]":END',
    "100 E=ERR:RESUME 40",
]
# The UNTRAPPED program. Line 20 is the run-on detector: an abort at line 10
# must not reach it.
UNTRAP_PROG = [
    "10 {stmt}",
    '20 PRINT"[RANON]"',
]

# 🎯 THE TWO FAULT SEEDS, and the whole probe is built out of them.
#   FP  a NUMERIC fault that does not abort on its own here: `0*(1/0)` sets
#       FPERR (code 11) and contributes 0 to the expression.
#   FP5 the same shape with a DIFFERENT code: `0*SQR(-1)` sets FPERR (code 5).
#       Two codes, one shape -- which is what makes the result a rule about
#       ORDER and not a statement about division by zero.
#   TM  a TYPE fault that does not abort on its own: `(Q$<5)` compares a string
#       to a number, sets TMISMATCH and yields 0 (basic/str-engine.asm's
#       type_mismatch_set).
# Concatenating them in either order puts BOTH flags up with a known winner.
FP = "0*(1/0)"
FP5 = "0*SQR(-1)"
TM = "(Q$<5)"

CLS = "CLS:"

# (label, kind, statement)   kind: "t" trapped / "u" untrapped
CASES = [
    # === o.* THE ORDER AXIS, at every caller that can hold BOTH flags =======
    # Each pair is the SAME two faults in the two possible orders. A tree that
    # ranks by flag identity answers the pair identically; the references do
    # not.
    # -- eval_int16_checked (interp.asm), reached by WIDTH -------------------
    ("o.w.fp",    "t", CLS + f"WIDTH {FP}+{TM}"),
    ("o.w.tm",    "t", CLS + f"WIDTH {TM}+{FP}"),
    ("o.w.fp5",   "t", CLS + f"WIDTH {FP5}+{TM}"),
    ("o.w.tm5",   "t", CLS + f"WIDTH {TM}+{FP5}"),
    # -- ...and CLEAR, the other int16 tenant of the same leaf ---------------
    ("o.cl.fp",   "t", CLS + f"CLEAR {FP}+{TM}"),
    ("o.cl.tm",   "t", CLS + f"CLEAR {TM}+{FP}"),
    # -- LOCATE, the filed row's own verb, at its first argument -------------
    # 🔴 `o.loc.str` IS THE FILED ROW `t.tmfp` (make locarg-acceptance),
    # restated: STR$ makes the numeric fault happen strictly before the type
    # fault the string then causes.
    ("o.loc.str", "t", CLS + "LOCATE STR$(1/0),3"),
    ("o.loc.fp",  "t", CLS + f"LOCATE {FP}+{TM},3"),
    ("o.loc.tm",  "t", CLS + f"LOCATE {TM}+{FP},3"),
    # -- ex_if (interp.asm) --------------------------------------------------
    ("o.if.fp",   "t", CLS + f"IF {FP}+{TM} THEN 30"),
    ("o.if.tm",   "t", CLS + f"IF {TM}+{FP} THEN 30"),
    # -- exp_num (print.asm) -------------------------------------------------
    ("o.pr.fp",   "t", CLS + f"PRINT {FP}+{TM}"),
    ("o.pr.tm",   "t", CLS + f"PRINT {TM}+{FP}"),
    # -- exps_notrel (print.asm): the type fault is marked ON THE SPOT here,
    #    not deferred out of the expression, so it is the one site where the
    #    two faults are raised by different mechanisms.
    ("o.imp.fp",  "t", CLS + "PRINT STR$(1/0) IMP 1"),
    ("o.imp.tm",  "t", CLS + 'PRINT "A" IMP 1'),
    # -- ex_let via check_expr_errors_popbc (interp.asm): a SECOND hand-rolled
    #    copy of the ordering, with the caller's saved key on the stack. The
    #    abort must still leave SP clean.
    ("o.let.fp",  "t", CLS + f"V={FP}+{TM}"),
    ("o.let.tm",  "t", CLS + f"V={TM}+{FP}"),
    # -- ex_let_arr (arrays.asm): a THIRD copy, with [OFFSET] and [TYPE]
    #    pushed. Neither the filed item nor §5.1 names this site.
    ("o.ary.fp",  "t", CLS + f"W(0)={FP}+{TM}"),
    ("o.ary.tm",  "t", CLS + f"W(0)={TM}+{FP}"),
    # -- els_tc_common (missing.asm): `A$=<numeric>` re-evaluates the RHS -----
    ("o.els.fp",  "t", CLS + f"Q2$={FP}+{TM}"),
    ("o.els.tm",  "t", CLS + f"Q2$={TM}+{FP}"),
    # -- eval_chan (float-arith.asm): the one caller whose ordering was already
    #    CHANGED on a measurement (D-BADFNUM §6), and the filed item's predicted
    #    refuter. A TMISMATCH channel SKIPS the coercion, so a fix that stops
    #    arming TMISMATCH lets the coercion run -- and the coercion can write
    #    FPERR=1 over the pending code. That is the risk this pair prices.
    ("o.chan.fp", "t", CLS + f'PRINT #{FP}+{TM},"X"'),
    ("o.chan.tm", "t", CLS + f'PRINT #{TM}+{FP},"X"'),

    # === n.* NEGATIVE CONTROLS: each flag ALONE, at every reader ============
    # These are the rows that must NOT move. A fix that changes when TMISMATCH
    # is armed is only correct if a type fault with NO numeric fault pending
    # still reports exactly as it does today.
    ("n.tm.w",    "t", CLS + f"WIDTH {TM}"),
    ("n.fp.w",    "t", CLS + f"WIDTH {FP}+1"),
    ("n.fp5.w",   "t", CLS + f"WIDTH {FP5}+1"),
    ("n.tm.loc",  "t", CLS + 'LOCATE "5",3'),
    ("n.tm.if",   "t", CLS + f"IF {TM} THEN 30"),
    ("n.tm.let",  "t", CLS + f"V={TM}"),
    ("n.tm.ary",  "t", CLS + f"W(0)={TM}"),
    ("n.fp.ary",  "t", CLS + f"W(0)={FP}"),
    # D-BADFNUM §6's own row: a string channel is Type mismatch, measured on
    # the CF-3300. This is the constraint the filed item mis-attributed to
    # §5.1, and it is a TM-ALONE row -- it cannot discriminate order at all.
    ("n.tm.chan", "t", CLS + 'PRINT #Q$,"X"'),
    ("n.fp.chan", "t", CLS + f'PRINT #1+{FP},"X"'),
    # The four TMISMATCH readers that never consult FPERR.
    ("n.tm.pdl",  "t", CLS + "V=PDL(Q$)"),          # expr.asm ev_ff_ckpdl
    ("n.tm.rnd",  "t", CLS + "V=RND(Q$)"),          # expr.asm ev_mc_arg_checked
    ("n.tm.hex",  "t", CLS + 'PRINT HEX$("A")'),    # str-engine.asm sfr_argok
    ("n.tm.lof",  "t", CLS + "V=LOF(Q$)"),          # files.asm fch_check

    # === r.* THE AT-RISK READERS: both flags, at a TM-ONLY reader ===========
    # 🔴 These are the rows that decide whether the one-site fix is SAFE. Each
    # reader below tests TMISMATCH without ever testing FPERR, so disarming
    # TMISMATCH changes what it does. Measured BEFORE the fix so the "after"
    # column has something to be compared against that is not a prediction.
    ("r.pdl",     "t", CLS + f"V=PDL({FP}+{TM})"),
    ("r.rnd",     "t", CLS + f"V=RND({FP}+{TM})"),
    ("r.hex",     "t", CLS + f"Q2$=HEX$({FP}+{TM})"),
    ("r.lof",     "t", CLS + f"V=LOF({FP}+{TM})"),

    # === u.* THE UNTRAPPED FACE: the TEXT, the line, and printed ONCE =======
    ("u.fp.w",    "u", f"WIDTH {FP}+1"),
    ("u.w.fp",    "u", f"WIDTH {FP}+{TM}"),
    ("u.w.tm",    "u", f"WIDTH {TM}+{FP}"),
    ("u.w.fp5",   "u", f"WIDTH {FP5}+{TM}"),
    ("u.loc.str", "u", "LOCATE STR$(1/0),3"),
    ("u.let.fp",  "u", f"V={FP}+{TM}"),
    ("u.ary.fp",  "u", f"W(0)={FP}+{TM}"),
    ("u.chan.fp", "u", f'PRINT #{FP}+{TM},"X"'),
    ("u.tm.loc",  "u", 'LOCATE "5",3'),
]

# 🟢 THE POSITIVE CONTROLS. Two per reading, because the two readings can fail
# independently and a battery that has gone blind looks exactly like a battery
# that agrees.
#   n.tm.loc   the trapped reading works AND an ordinary type fault reports 13
#   n.fp.w     an ordinary numeric fault traps and reports its own code 11
#   u.tm.loc   the untrapped reading works: ONE message, naming its line
#   u.fp.w     an untrapped numeric fault names its own DIFFERENT message
#
# 🔴 THE FIRST DRAFT OF THIS SET NAMED `u.w.fp5` AS THE FOURTH CONTROL AND THAT
# WAS A DEFECT IN THE APPARATUS, CAUGHT ON THE FIRST SMOKE RUN. `u.w.fp5` is
# `WIDTH 0*SQR(-1)+(Q$<5)` -- a BOTH-FLAGS row, i.e. one of the rows under test.
# A subject row cannot also be the control that licenses reading the subject:
# it read `Type mismatch in 10` on zb, which is exactly the divergence this
# slice exists to measure, and it would have exited 2 ("the instrument broke")
# on a run where the instrument was fine. Replaced with `u.fp.w`
# (`WIDTH 0*(1/0)+1`), a numeric fault with NO type fault pending.
# Recorded in docs/tmfp-msx1-characterization.md §3.
# A control failure exits 2 (the instrument broke), never 1 (a regression).
CONTROLS = ("n.tm.loc", "n.fp.w", "u.tm.loc", "u.fp.w")

# 🔴 PREDICTIONS, WRITTEN BEFORE THE FIRST RUN and not back-filled from the
# result column ([[a-prediction-copied-into-the-result-column]]). Misses are
# recorded in docs/tmfp-msx1-characterization.md §3, not absorbed.
CONTROL_WANT = {
    "n.tm.loc": " 13 ",
    "n.fp.w":   " 11 ",
    "u.tm.loc": "Type mismatch in 10",
    "u.fp.w":   "Division by zero in 10",
}

# Rows the fix must NOT move: a type fault with no numeric fault pending still
# reports exactly as it does today, at every reader.
NEGATIVE = {
    "n.tm.w":    "NEGATIVE CONTROL — a type fault ALONE is still 13",
    "n.tm.chan": "NEGATIVE CONTROL — D-BADFNUM §6's row; TM-alone, cannot "
                 "discriminate order",
    "n.tm.pdl":  "NEGATIVE CONTROL — PDL defers to a TM-alone fault",
    "n.tm.rnd":  "NEGATIVE CONTROL — ev_mc_arg_checked's TM-alone half",
    "n.tm.hex":  "NEGATIVE CONTROL — HEX$'s TM-alone promotion",
    "n.tm.lof":  "NEGATIVE CONTROL — fch_check's string-channel test",
    "n.fp.ary":  "NEGATIVE CONTROL — a numeric fault ALONE at the third "
                 "hand-rolled copy",
}
LABEL_W = 10

# --- DEFERRED: measured, printed, NEVER scored ------------------------------
# 🔴 `r.hex` IS THE ONE ROW OF FIFTY THIS SLICE DID NOT CLOSE, AND IT IS THE ONE
# THAT EXPOSED A SECOND DEFECT RATHER THAN FIXING THE FIRST.
# `Q2$=HEX$(0*(1/0)+(Q$<5))` reads ` 11 ` on both references. It read ` 13 `
# before D-TMFP and reads ` 2 ` after -- wrong before, wrong differently now.
# Say that plainly: the fix moved this row from one wrong answer to another.
#
# 🎯 WHAT IT EXPOSED, AND WHY THAT IS WORTH MORE THAN THE ROW. Localized on zb
# (docs/tmfp-msx1-characterization.md §5): it is NOT specific to HEX$ -- STR$ and
# OCT$ do it too -- and NOT to the assignment driver, since `PRINT` shows it as
# well. It needs BOTH faults INSIDE a string function's parentheses; either fault
# alone reads correctly (` 13 ` / ` 11 `). The mechanism is two PRE-EXISTING
# defects that TMISMATCH was masking, neither caused by this slice:
#   1. after a string-compare mismatch the cursor does not land on the closing
#      `)`, so `str_fn_radix`'s `cp ')'` fails and takes the str_arg_empty exit;
#   2. `str_arg_empty` (basic/str-engine.asm) then does `ld a,4 : ld (FPERR),a`
#      -- OVERWRITING the pending Division-by-zero 11 with the deferred
#      syntax-error 4. That is a first-error-wins violation of exactly the kind
#      this slice is about, three hundred lines from the routine it fixed, and
#      `sfr_argok`'s own comment fifteen lines away already states the rule it
#      breaks ("an inner error keeps its own (more specific) message").
# Before D-TMFP both were invisible: TMISMATCH was armed, so check_expr_errors
# reported 13 and the clobbered code never surfaced.
#
# 💰 PRICED AND DEFERRED. Guarding the clobber is +6 B
# (`ld a,(FPERR)` / `or a` / `jr nz` around the two stores) and the main LOW
# region has exactly 6 B free after this slice -- the whole remaining budget, for
# a guard that fixes defect 2 and leaves defect 1 (the cursor) unmeasured and
# unexplained. A row that needs its own cursor characterisation is its own slice
# with its own denominator, not a rider on this one. Filed in TODO.md.
#
# ✅ CLOSED BY D-PENDERR (docs/spec-basic-penderr.md §8), AND FOR LESS THAN THE
# PRICE ABOVE. Merging TMISMATCH into the pending-error cell required making the
# cell set-if-empty at EVERY writer, which is one shared 14 B routine
# (`penderr_set`) and a byte-neutral `call` at each of the twenty-four stores --
# so defect 2's guard cost ZERO marginal bytes instead of the +6 B priced here.
# `r.hex` reads ` 11 ` on all three sides and is SCORED again: 49 scored + 1
# deferred -> 50 scored, 50 agree.
#
# 🔴 AND DEFECT 1 IS STILL THERE. The cursor still does not land on the closing
# `)`, `str_fn_radix` still takes the `str_arg_empty` exit, and HEX$ still does
# not compute. What changed is that the exit no longer REWRITES the pending code,
# so the Division-by-zero that happened first survives to the statement boundary
# and is what gets reported. The row is green with the defect present: closing
# defect 2 made defect 1 unobservable THROUGH THE ERROR CODE, which is not the
# same as fixing it. It stays filed in TODO.md as a cursor question, and this
# note is here so nobody reads a green row as evidence that it is gone.
DEFERRED: dict[str, str] = {}

SENTINELS = ("<NO CAPTURE>", "<NO ECHO>")


def clip_at_prompt(tail: str) -> str:
    """Drop everything from the first row that BEGINS with a prompt token.

    🔴 THE READING IS NOT MACHINE-AGNOSTIC WITHOUT THIS, AND ONLY THE SIDE UNDER
    TEST CAN SEE IT. `omsx_repl.screen_tail` ends its span at a row that IS a
    prompt (`PROMPTS = ("Ok", "ZB")`) — true on both references, where `Ok` sits
    alone on its line. zerobas emits `ZB` with no trailing newline, so the
    prompt and the NEXT echoed line share one row, no row ever equals a prompt,
    and the span runs to the bottom of the screen (measured 2026-08-09,
    D-ONERR0, docs/onerr0-msx1-characterization.md §3.1). Clipped HERE and not
    in `omsx_repl`: 24 gated probes read that helper, and widening the shared
    span rule is its own slice with its own denominator."""
    out = []
    for row in tail.split("|"):
        if any(row.startswith(p) for p in omsx_repl.PROMPTS):
            break
        out.append(row)
    return "|".join(out)


def program(kind: str, stmt: str) -> list[str]:
    tpl = TRAP_PROG if kind == "t" else UNTRAP_PROG
    lines = [ln.format(stmt=stmt) for ln in tpl]
    # D-SNCAP: only the TRAPPED template has a terminal point every path reaches.
    return probe_signal.mark_ends(lines) if kind == "t" else lines


# --- D-SNCAP: capture-on-signal (probes/lib/probe_signal.py) -----------------
# Every case here is its OWN BOOT (`batch=False`), so the scheduled RUN..capture
# budget is a guess at how long the case takes. The TRAPPED template ends at a
# single `:END` that BOTH paths reach -- the handler `RESUME`s onto the printing
# line -- so the case can announce completion itself and the budget becomes a
# pure FAILURE detector, firing only when a row never signalled at all.
#
# 🔴 THE UNTRAPPED ROWS ARE OUT OF SCOPE, FOR TWO INDEPENDENT REASONS, and
# either alone is enough. (1) They are BUILT to abort -- the statement raises and
# the next line is the run-on detector -- so control never reaches a POKE and
# they would fall back every time. (2) Their readout is `screen_tail`, which
# TERMINATES AT THE `Ok`/`ZB` PROMPT -- exactly the 2 characters a signal-time
# capture has not printed yet -- so converting them would change what they mean.
# They pass no sentinel at all, rather than being converted and then counted as
# fallbacks.
#
# 🟢 HOW THE TRAPPED ROWS DISCHARGE THE PROMPT BURDEN. They read through
# `omsx_repl.result_span` -- the text between the LAST `[` and the following
# `]`. Neither prompt is a bracket, so the reading is prompt-independent BY
# CONSTRUCTION. That argument is not what this rests on: the whole report was
# diffed row-by-row against a run taken BEFORE the conversion, and every row was
# identical (scratchpad/sncap/rowdiff.py).
SIG = probe_signal.Tally()


def read_case(kind: str, raw: str | None) -> str:
    """Trapped rows read the printed `[ERR]` cell; untrapped rows read the
    clipped screen tail of `RUN`.

    🔴 The trapped programs CLS at runtime, which is what makes `result_span`'s
    "last `[` on the screen" unambiguous: the echoed program text (which
    contains the printer's own `[`) is gone by the time anything prints."""
    if raw is None:
        return "<NO CAPTURE>"
    if kind == "t":
        v = omsx_repl.result_span(raw)
        return "<NO CAPTURE>" if v is None else v
    t = omsx_repl.screen_tail(raw, "RUN")
    return "<NO ECHO>" if t is None else clip_at_prompt(t)


def run_side(side: str, only: list[str]) -> dict:
    cfg = SIDES[side]
    out = {}
    for label, kind, stmt in CASES:
        if only and label not in only:
            continue
        kw = {}
        if cfg["diska"]:
            dsk = os.path.join(tempfile.gettempdir(),
                               f"zb_tmfp_{side}_{label}.dsk")
            shutil.copy(TEST_DSK, dsk)
            kw["diska"] = dsk
        lines = list(cfg["reset"]) + program(kind, stmt) + ["RUN"]
        # 🔴 A FRESH `so` PER CALL. Each case is its own boot and every boot
        # indexes from 0, so one dict reused across the loop would hold a single
        # entry and the tally would silently under-count.
        so: dict = {}
        sn = probe_signal.kwargs(so) if kind == "t" else {}
        caps = omsx_repl.run_cases(
            cfg["machine"], [("direct", lines)],
            batch=False, boot=cfg["boot"], step=cfg["step"], **kw, **sn)
        SIG.add(so, label=f"{side}:{label}")
        out[label] = read_case(kind, caps[0])
    return out


DENOMINATOR = (
    "(WHICH READER of the two deferred flags: the twelve check_expr_errors "
    "sites, reached here via WIDTH / CLEAR / LOCATE (eval_int16_checked), IF, "
    "PRINT (exp_num), PRINT's string-operand path (exps_notrel), PRINT # "
    "(eval_chan) and A$=<numeric> (els_tc_common); PLUS the two SEPARATE "
    "hand-rolled copies of the same ordering that a fix to check_expr_errors "
    "would not move at all -- check_expr_errors_popbc (ex_let) and ex_let_arr "
    "(arrays.asm); PLUS the four readers that test TMISMATCH and never test "
    "FPERR -- fch_check (files.asm, the string-channel test shared by all 12 "
    "file verbs), ev_ff_ckpdl and ev_mc_arg_checked (expr.asm), sfr_argok "
    "(str-engine.asm)) x (BOTH faults pending vs EACH ALONE, the second being "
    "the negative control that must not move) x (the ORDER the two faults "
    "occur in, which is the axis the filed item did not have: the SAME two "
    "faults concatenated both ways) x (WHICH numeric code: 11 from 1/0 vs 5 "
    "from SQR(-1), so the rule is about RANK and not about division) x "
    "(whether the caller's own stack cleanup survives the abort -- "
    "check_expr_errors_popbc pops a saved key, ex_let_arr pops [OFFSET] and "
    "[TYPE], exps_notrel balances an operand-start push) x (TRAPPED vs "
    "UNTRAPPED, the second reading the message TEXT, its line number, and "
    "whether it printed ONCE). The LOCATE argument-position, clamp and cursor "
    "axes are NOT re-measured here: they are `make locarg-acceptance` and "
    "`make missing-acceptance`, which are this slice's green control set."
)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="D-TMFP: of two pending faults, the FIRST one is reported")
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
    print(SIG.line())
    present = [lab for lab, _, _ in CASES
               if any(lab in results[s] for s in sides)]

    print("D-TMFP — of two pending faults, the one that happened FIRST wins   "
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
              "    n.tm.loc = the TRAPPED reading itself, on an ordinary type "
              "fault (13).\n"
              "               Red here and every t-row has two causes.\n"
              "    n.fp.w   = an ordinary numeric fault reports its OWN code "
              "(11). Red here\n"
              "               and the divergence is NOT about fault order.\n"
              "    u.tm.loc = the UNTRAPPED reading -- ONE message, naming its "
              "line.\n"
              "    u.w.fp5  = an untrapped numeric fault with the OTHER code "
              "and message.\n"
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
          f"{len(NEGATIVE)} negative controls, "
          f"{refsplit} row(s) with no oracle, "
          f"{len(DEFERRED)} DEFERRED row(s) measured but not scored)")
    print("SIDES: vg8020,cf3300,zb — ON ERROR, ERR, WIDTH, CLEAR, LOCATE, IF, "
          "PRINT, PDL, RND and HEX$ are core MSX-BASIC, present on every MSX1, "
          "so BOTH references are legitimate oracles for those rows; the LOF "
          "rows depend on a file system and are expected to be measured, not "
          "necessarily oracled, on a cassette-only reference")
    print("DENOMINATOR: " + DENOMINATOR)
    if a.gate and dis:
        sys.stderr.write(f"tmfp: {dis} reading(s) diverge\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
