#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""D-STMTPEND — a fault that ALREADY HAPPENED outranks everything the statement
does afterwards, including finishing.

WHERE THIS CAME FROM. D-TMFP filed "defect 1": after a string-compare mismatch
the token cursor does not land on the closing `)`, so `str_fn_radix` bails
through `str_arg_empty`. D-PENDERR then fixed the OTHER defect and made the
symptom disappear -- `r.hex` and its family went green on three sides -- while
leaving defect 1 untouched. This probe is the denominator that was supposed to
show the cursor was unobservable. It shows the opposite.

🎯 THE CURSOR IS REAL AND IT IS MEASURED, but it is not the rule. Freezing
zerobas at `type_mismatch_set` and reading IX out of the token buffer puts the
cursor on the RHS OPERAND -- `Q$` and `<` consumed, `5` not -- and freezing at
`penderr_set` shows the first pending code written after `HEX$((Q$<5)+0*(1/0))`
is 4 (`str_arg_empty`), never 2 (`fp_div`). So the rest of the expression is not
merely fault-free after a deferred type fault: IT IS NEVER EVALUATED. That
answers the question `spec-basic-penderr.md` §3.2 explicitly declined to answer,
and the screen cannot answer it. See `docs/stmtpend-msx1-characterization.md` §3.

🔴 AND THE STRANDED CURSOR IS ONLY ONE ROUTE INTO A HOLE THAT NEEDS NO STRING AT
ALL. `SCREEN 0*(1/0)` and `DEFUSR=0*(1/0)` print NO ERROR on zerobas and
`Division by zero` on both references. `exec_stmt` clears the pending-error cell
unconditionally at the top of every statement, so a fault raised by a statement
whose driver never calls `check_expr_errors` is simply forgotten. A stranded
cursor gets you there by making the statement END early; a plain `1/0` gets you
there because nobody looked.

THE TWO MECHANISMS, WHICH THIS PROBE KEEPS APART BY NAME:

  s.*  THE STATEMENT-BOUNDARY DROP. The statement runs to completion (or to what
       its driver thinks is completion), `jp exec_stmt`, and the pending code is
       cleared before anyone reads it. Reported: nothing at all.
  e.*  THE EAGER SYNTAX ERROR. The statement's own delimiter check fails and
       jumps to `stmt_error`, which raises ERR 2 over the top of a live pending
       code. Reported: `Syntax error` where the reference reports the fault.
  c.*  THE CURSOR ROWS -- e.*/s.* reached specifically by a string compare
       stranding the cursor mid-expression. Same two mechanisms, string entry.
  g.*  THE MASKED CLASS: contexts whose driver DOES check, where the pending
       code already wins. These must not move; they are what D-PENDERR shipped.
  n.*  NEGATIVE CONTROLS, each agreeing for a reason INDEPENDENT of the claim:
       a genuine syntax error with NO fault pending (must stay ERR 2), a clean
       statement (must stay silent), a single fault at a reader that checks.
  u.*  THE UNTRAPPED FACE: message TEXT, its line, printed ONCE, and whether the
       following line ran.
  b.*  THE COLD-BOOT FACE. 🔴 ADDED 2026-08-21 (D-COLDROW) TO CLOSE A HOLE THIS
       PROBE HAD SINCE IT SHIPPED: every other row above resets through `CLS`,
       and `CLS` is a statement, so it runs `exec_stmt` -- which READS the
       pending-error cell. If the cold-boot `ld (FPERR),a` in basic/interp.asm
       were missing, power-on RAM ($FF on this machine, D-VALTYP) would raise
       ONE bogus `Unprintable error` out of the first statement executed, and
       the reset's own `CLS` would spend it before any scored row ran. These two
       rows run the SAME program off two resets that differ only in that `CLS`.

TWO READINGS, ONE GRAMMAR (D-ROWSHAPE): `s.*`/`e.*`/`c.*`/`g.*`/`n.*` are
TRAPPED and read `[ ERR ]` from inside the handler; `u.*` rows are UNTRAPPED and
read the clipped `screen_tail` of `RUN`.

⚠️ Every row is a STORED program driven by `RUN`. In direct mode an abort on one
line does not stop the next.

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

SIDES = {
    "vg8020": dict(machine="Philips_VG_8020", boot=8.0, step=2.5,
                   reset=("NEW", "CLS"), diska=False),
    "cf3300": dict(machine="National_CF-3300", boot=14.0, step=4.5,
                   reset=("", "SCREEN 0", "NEW", "CLS"), diska=True),
    "zb":     dict(machine=ZB_MACHINE, boot=8.0, step=2.5,
                   reset=("NEW", "CLS"), diska=True),
}

# 🔴 THE SEED LINE IS PART OF EVERY PROGRAM, TRAPPED OR NOT. `Q$` must hold a
# string for the comparison rows to be a TYPE fault rather than an empty-variable
# one, and the untrapped template needs it too -- which is why the fault is on
# line 30 there, not line 10, and every u.* expectation names line 30.
TRAP_PROG = [
    "10 ON ERROR GOTO 100",
    '20 Q$="A"',
    "30 {stmt}",
    "40 E=0",
    '50 PRINT"[";E;"]":END',
    "100 E=ERR:RESUME 50",
]
UNTRAP_PROG = [
    '10 Q$="A"',
    "20 {stmt}",
    '30 PRINT"[RANON]"',
]
# 🔴 THE COLD-BOOT TEMPLATE TAKES NO STATEMENT AT ALL. Its subject is not what a
# statement does; it is whether a machine that has executed NOTHING since power-on
# can run an ordinary program. Two PRINTs rather than one, so a machine that dies
# on the first statement and a machine that dies on the second read differently.
COLD_PROG = [
    '10 PRINT"[OK]"',
    '20 PRINT"[TWO]"',
]
TEMPLATES = {"t": TRAP_PROG, "u": UNTRAP_PROG, "b": COLD_PROG}

# THE FAULT SEEDS. Each contributes 0 to the expression it sits in and leaves a
# DISTINCT pending code, so the row says WHICH fault survived, not merely that
# one did.
#   DZ  division by zero      -> 11        S5  SQR of a negative ->  5
#   OV  a float overflow      ->  6        TM  string < number   -> 13
#   MT  number < string       -> 13   (the OTHER mismatch site, evr_mismatch)
DZ = "0*(1/0)"
S5 = "0*SQR(-1)"
OV = "0*(1E38*1E38)"
TM = "(Q$<5)"
MT = "(5<Q$)"

CLS = "CLS:"

# (label, kind, statement)   kind: "t" trapped / "u" untrapped
CASES = [
    # === s.* THE STATEMENT-BOUNDARY DROP — no string anywhere ===============
    # The statement PARSES cleanly and runs to `jp exec_stmt`; the pending code
    # is cleared there before any reader sees it. zerobas reports NOTHING.
    # 🔴 These are the rows that say the defect is not about strings.
    ("s.for.dz",   "t", CLS + f"FOR I={DZ} TO 3:NEXT"),
    ("s.for.ov",   "t", CLS + f"FOR I={OV} TO 3:NEXT"),
    ("s.for.5",    "t", CLS + f"FOR I={S5} TO 3:NEXT"),
    ("s.forlim",   "t", CLS + f"FOR I=1 TO {DZ}:NEXT"),
    ("s.scr.dz",   "t", CLS + f"SCREEN {DZ}"),
    ("s.usr.dz",   "t", CLS + f"DEFUSR={DZ}"),
    ("s.usr.ov",   "t", CLS + f"DEFUSR={OV}"),

    # === e.* THE EAGER SYNTAX ERROR over a live pending code ================
    # `stmt_error` raises ERR 2 without consulting the cell. Same statement, one
    # delimiter removed, so the ONLY difference from the s.* rows above is which
    # of the two mechanisms is reached.
    ("e.for.dz",   "t", CLS + f"FOR I={DZ} STEP 2:NEXT"),
    ("e.for.ov",   "t", CLS + f"FOR I={OV} STEP 2:NEXT"),
    ("e.for.5",    "t", CLS + f"FOR I={S5} STEP 2:NEXT"),

    # === c.* THE CURSOR ROWS — the same two holes, entered by a string =====
    # A string-compare mismatch strands the cursor on the RHS operand, so the
    # statement's next delimiter check reads a token that is not there yet.
    # BOTH mismatch sites: ers_rhs_mismatch (`Q$<5`) and evr_mismatch (`5<Q$`).
    ("c.for.tm",   "t", CLS + f"FOR I={TM} TO 3:NEXT"),
    ("c.for.mt",   "t", CLS + f"FOR I={MT} TO 3:NEXT"),
    ("c.forlim",   "t", CLS + f"FOR I=1 TO {TM} STEP 1:NEXT"),
    ("c.scr.tm",   "t", CLS + f"SCREEN {TM}"),
    ("c.usr.tm",   "t", CLS + f"DEFUSR={TM}"),
    ("c.usr.mt",   "t", CLS + f"DEFUSR={MT}"),
    ("c.poke.tm",  "t", CLS + f"POKE {TM},0"),
    ("c.line.tm",  "t", CLS + f"LINE (0,0)-({TM},1)"),

    # === g.* THE MASKED CLASS — drivers that DO check, and must not move ====
    # This is what D-PENDERR shipped. Every one of these already agrees; they
    # are here because the fix touches the statement boundary they all cross.
    ("g.hex",      "t", CLS + f"Q2$=HEX$({DZ}+{TM})"),
    ("g.hex.tm",   "t", CLS + f"Q2$=HEX$({TM}+{DZ})"),
    ("g.oct",      "t", CLS + f"Q2$=OCT$({DZ}+{TM})"),
    ("g.wid",      "t", CLS + f"WIDTH {TM}+{DZ}"),
    ("g.wid.dz",   "t", CLS + f"WIDTH {DZ}+{TM}"),
    ("g.loc",      "t", CLS + f"LOCATE {TM},3"),
    ("g.prt",      "t", CLS + f"PRINT {TM};1"),
    ("g.if",       "t", CLS + f"IF {TM} THEN 50"),
    ("g.dim",      "t", CLS + f"DIM Z({TM})"),
    ("g.ary",      "t", CLS + f"W({TM})=1"),
    ("g.let",      "t", CLS + f"V={TM}+{DZ}"),
    ("g.mid",      "t", CLS + f'Z$=MID$("ABC",{TM},1)'),
    ("g.strng",    "t", CLS + f"Z$=STRING$({TM},65)"),
    ("g.open",     "t", CLS + f'OPEN"X" AS #{TM}'),
    ("g.next",     "t", CLS + f"FOR I=1 TO 1:NEXT W({TM})"),
    ("g.snd",      "t", CLS + f"SOUND {TM},1"),
    ("g.on",       "t", CLS + f"ON {TM} GOTO 50"),
    ("g.poke.dz",  "t", CLS + f"POKE {DZ},0"),
    ("g.snd.dz",   "t", CLS + f"SOUND {DZ},1"),

    # === n.* NEGATIVE CONTROLS ==============================================
    # 🔴 A GENUINE SYNTAX ERROR WITH NOTHING PENDING MUST STAY ERR 2. These are
    # the rows a fix that simply stopped raising ERR 2 would redden, and they
    # agree today for a reason that has nothing to do with pending codes.
    ("n.syn.for",  "t", CLS + "FOR I=1 STEP 2:NEXT"),
    ("n.syn.zork", "t", CLS + "ZORK 1,2"),
    ("n.syn.swap", "t", CLS + "SWAP 1,V"),
    # ...and a clean statement must stay silent.
    ("n.ok.for",   "t", CLS + "FOR I=1 TO 3:NEXT"),
    ("n.ok.usr",   "t", CLS + "DEFUSR=&HC000"),
    ("n.ok.poke",  "t", CLS + "POKE &HC000,0"),
    ("n.ok.scr",   "t", CLS + "SCREEN 0"),
    ("n.ok.chain", "t", CLS + "V=1:W=2:V=V+W"),
    # ...and a single fault at a reader that already checks keeps its own code.
    ("n.dz.w",     "t", CLS + f"WIDTH {DZ}+1"),
    ("n.5.w",      "t", CLS + f"WIDTH {S5}+1"),
    ("n.ov.w",     "t", CLS + f"WIDTH {OV}+1"),
    ("n.tm.w",     "t", CLS + f"WIDTH {TM}"),
    ("n.tm.loc",   "t", CLS + 'LOCATE "5",3'),
    # ...and the TRAP itself must still work after a newly-raised error: every
    # s.*/e.* row above runs its handler and RESUMEs, which is only readable
    # because this row proves the handler/RESUME path is sound on its own.
    ("n.trap.res", "t", CLS + "V=1/0"),

    # === u.* THE UNTRAPPED FACE ============================================
    ("u.for.dz",   "u", f"FOR I={DZ} TO 3:NEXT"),
    ("u.for.tm",   "u", f"FOR I={TM} TO 3:NEXT"),
    ("u.scr.dz",   "u", f"SCREEN {DZ}"),
    ("u.usr.tm",   "u", f"DEFUSR={TM}"),
    ("u.syn.for",  "u", "FOR I=1 STEP 2:NEXT"),
    ("u.dz.w",     "u", f"WIDTH {DZ}+1"),
    ("u.tm.loc",   "u", 'LOCATE "5",3'),

    # === b.* THE COLD-BOOT FACE ============================================
    # Same program, same readout, two resets that differ ONLY in `CLS`.
    # `b.cold` is the subject: `NEW` alone, so nothing has run `exec_stmt`
    # before `RUN` does. `b.warm` is its GREEN CONTROL on the same apparatus --
    # it cannot fail because this row's claim is wrong, only because the
    # program, the template or the readout is broken.
    ("b.cold",     "b", ""),
    ("b.warm",     "b", ""),
]

# 🔴 THE ROW WHOSE SUBJECT IS THE ABSENCE OF A RESET LINE. `run_side` drops
# `CLS` from this side's reset for these labels and nothing else changes.
NO_CLS_RESET = {"b.cold"}

# 🟢 POSITIVE CONTROLS, two per reading. 🔴 EVERY ONE IS A ROW WHOSE ANSWER IS
# FIXED BY SOMETHING OTHER THAN THIS SLICE'S CLAIM: a genuine syntax error with
# no pending code, an ordinary single fault at a reader that already checked
# before this slice existed, and the same pair on the untrapped reading.
CONTROLS = ("n.syn.zork", "n.dz.w", "u.syn.for", "u.dz.w", "b.warm")

CONTROL_WANT = {
    "n.syn.zork": " 2 ",
    "n.dz.w":     " 11 ",
    "u.syn.for":  "Syntax error in 20",
    "u.dz.w":     "Division by zero in 20",
    # 🔴 A LITERAL, NOT A CROSS-SIDE AGREEMENT. `b.cold` and `b.warm` share a
    # template, a readout AND a reset builder, so a blindness in any of the three
    # would make the pair agree while measuring nothing -- and no differential can
    # see that, because there is no column in which those three differ
    # (D-FILESIDE). Measured on all three sides 2026-08-21 before it was pinned.
    "b.warm":     "[OK]|[TWO]",
}

NEGATIVE = {
    "n.syn.for":  "NEGATIVE CONTROL — a syntax error with NOTHING pending",
    "n.syn.zork": "NEGATIVE CONTROL — an unknown statement, nothing pending",
    "n.syn.swap": "NEGATIVE CONTROL — a malformed SWAP, nothing pending",
    "n.ok.for":   "NEGATIVE CONTROL — a clean loop must stay silent",
    "n.ok.usr":   "NEGATIVE CONTROL — a clean DEFUSR must stay silent",
    "n.ok.poke":  "NEGATIVE CONTROL — a clean POKE must stay silent",
    "n.ok.scr":   "NEGATIVE CONTROL — a clean SCREEN must stay silent",
    "n.ok.chain": "NEGATIVE CONTROL — ':'-chained statements still chain",
    "n.dz.w":     "NEGATIVE CONTROL — one numeric fault at a checking reader",
    "n.5.w":      "NEGATIVE CONTROL — the SQR code alone",
    "n.ov.w":     "NEGATIVE CONTROL — the overflow code alone",
    "n.tm.w":     "NEGATIVE CONTROL — a type fault alone is still 13",
    "n.tm.loc":   "NEGATIVE CONTROL — the trapped reading itself",
    "n.trap.res": "NEGATIVE CONTROL — the handler + RESUME path is sound",
}
LABEL_W = 11

DEFERRED: dict[str, str] = {
    # 🎯 THE DICT IS EMPTY. Both rows this probe deferred are now scored.
    #
    # 🎯 `c.line.tm` WAS DEFERRED HERE AND IS NOW SCORED. D-LINERR (2026-08-11,
    # docs/spec-basic-lineerr.md) closed it -- and the reason recorded here was
    # WRONG. This dict used to say "LINE raises its OWN Illegal function call
    # eagerly from inside its coordinate parse". There is no ERR 5 in
    # parse_coord: the refusal was `ex_line_gfx`'s own opening `cp 2`, three
    # instructions in, BEFORE any coordinate was looked at, and this row runs in
    # the boot default SCREEN 0. Reading the site was enough to refute the
    # filed diagnosis; the real rule is an ORDERING one, measured at five verbs
    # (spec-basic-lineerr.md §2) -- a graphics statement moves the work area to
    # the point its MANDATORY arguments resolve to and refuses a wrong SCREEN
    # mode immediately after that, so every coordinate fault outranks the mode
    # and no optional argument does.
    #
    # 🎯 `u.scr.dz` WAS DEFERRED HERE AND IS NOW SCORED. D-SCRERR (2026-08-10,
    # docs/spec-basic-screenerr.md) closed it: SCREEN's mode is a checked byte
    # and the check runs BEFORE CHGMOD, so the mode is never applied and the
    # `RUN` echo this reading anchors on survives. The statement boundary is
    # still by construction too late for a driver with a side effect -- what
    # changed is that ex_screen no longer relies on it.
}

SENTINELS = ("<NO CAPTURE>", "<NO ECHO>")


def clip_at_prompt(tail: str) -> str:
    """Drop everything from the first row that BEGINS with a prompt token.

    zerobas emits `ZB` with no trailing newline, so the prompt shares a row with
    the next echoed line and `omsx_repl.screen_tail`'s own prompt terminator
    never fires on zb (D-ONERR0, docs/onerr0-msx1-characterization.md §3.1)."""
    out = []
    for row in tail.split("|"):
        if any(row.startswith(p) for p in omsx_repl.PROMPTS):
            break
        out.append(row)
    return "|".join(out)


def program(kind: str, stmt: str) -> list[str]:
    tpl = TEMPLATES[kind]
    lines = [ln.format(stmt=stmt) for ln in tpl]
    # D-SNCAP: only the TRAPPED template has a terminal point every path reaches.
    # ⚠️ THE COLD-BOOT TEMPLATE ("b") IS NOT ONE. It has no `END` at all, and its
    # readout is `screen_tail` like the untrapped rows -- both disqualifying.
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
                               f"zb_stpd_{side}_{label}.dsk")
            shutil.copy(TEST_DSK, dsk)
            kw["diska"] = dsk
        reset = (tuple(r for r in cfg["reset"] if r != "CLS")
                 if label in NO_CLS_RESET else cfg["reset"])
        lines = list(reset) + program(kind, stmt) + ["RUN"]
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
    "(WHERE a pending error code can be LOST between the fault and a reader) x "
    "(WHICH statement is the loser). The tree has FIFTY-SIX `call`/`jp eval` / "
    "`ev_logic` sites; SEVEN of them reach `check_expr_errors`/"
    "`check_fperr_only` within eight lines and SIX reach `stmt_error` before "
    "any check, so a static scan alone cannot classify the remaining 43 -- "
    "every one of them ends at `jp exec_stmt`, whose unconditional "
    "`ld (FPERR),a` is the SINGLE point at which a live code is discarded, and "
    "`stmt_error` is the single point at which one is outranked. That is why "
    "this probe samples STATEMENTS rather than call sites: two writers to "
    "close, and a statement is the only thing that can tell you whether a "
    "given driver reaches them. Sampled: FOR (three argument positions), "
    "SCREEN, DEF USR, POKE, LINE (drivers with no check) x the four fault "
    "codes 11/6/5/13 x the two ways to arrive (the statement ENDS with a live "
    "code, or its own delimiter check fails over one) x the two string-compare "
    "mismatch SITES (ers_rhs_mismatch `Q$<5`, evr_mismatch `5<Q$`) x TRAPPED "
    "vs UNTRAPPED. The g.* rows re-measure the drivers that DO check, which is "
    "the population `make penderr-acceptance` (61) and `make tmfp-acceptance` "
    "(50) own; those two, plus `make width-acceptance` (94) and "
    "`make locarg-acceptance` (45), are this slice's green control set. NOT "
    "swept: the cursor POSITION itself, which no screen row can witness -- it "
    "is measured by freezing the machine and reading IX, "
    "docs/stmtpend-msx1-characterization.md §3."
)


def reset_selftest() -> list[str]:
    """🔴 A ROW WHOSE SUBJECT IS A MISSING RESET LINE GOES BLIND BY AGREEING.

    `NO_CLS_RESET` is consulted inside `run_side`, which BOTH columns run --
    so if the override ever stops firing (a renamed label, a side whose reset
    no longer says `CLS`, a `CLS` that creeps into the template) `b.cold`
    quietly becomes a second copy of `b.warm`, agrees on three sides, and
    measures nothing. A differential cannot catch that, because there is no
    column in which the override is different. So it is pinned STATICALLY,
    against LITERALS, in both senses -- the override must REMOVE a `CLS` from
    every side, and the un-overridden twin must still HAVE one
    (fileside-slice; negjudge's "a vector of each sense").

    Returns a list of complaints; empty means the instrument is sound."""
    bad: list[str] = []
    labels = {lab: kind for lab, kind, _ in CASES}
    for lab in sorted(NO_CLS_RESET):
        if lab not in labels:
            bad.append(f"NO_CLS_RESET names {lab!r}, which is not a case")
    twins = sorted(lab for lab, kind, _ in CASES
                   if kind == "b" and lab not in NO_CLS_RESET)
    if not twins:
        bad.append("no un-overridden b.* row is left to serve as the control")
    for side, cfg in SIDES.items():
        if "CLS" not in cfg["reset"]:
            bad.append(f"{side}: reset {cfg['reset']!r} has no 'CLS' for the "
                       f"override to remove -- b.cold no longer differs")
        for lab in sorted(NO_CLS_RESET):
            if lab not in labels:
                continue
            reset = tuple(r for r in cfg["reset"] if r != "CLS")
            lines = list(reset) + program(labels[lab], "") + ["RUN"]
            hit = [ln for ln in lines if "CLS" in ln]
            if hit:
                bad.append(f"{side}/{lab}: 'CLS' survives in {hit!r}")
        for lab in twins:
            lines = list(cfg["reset"]) + program(labels[lab], "") + ["RUN"]
            if not any("CLS" in ln for ln in lines):
                bad.append(f"{side}/{lab}: the CONTROL twin has no 'CLS' "
                           f"either -- the pair no longer differs")
    return bad


def main() -> int:
    ap = argparse.ArgumentParser(
        description="D-STMTPEND: a fault that already happened outranks the "
                    "rest of the statement")
    ap.add_argument("--sides", default="vg8020,cf3300,zb")
    ap.add_argument("--only", default="")
    ap.add_argument("--gate", action="store_true",
                    help="exit 1 unless every row agrees across sides")
    a = ap.parse_args()

    complaints = reset_selftest()
    if complaints:
        sys.stderr.write("stmtpend: the reset override is broken, so the "
                         "b.* rows would agree while measuring nothing:\n")
        for c in complaints:
            sys.stderr.write(f"  {c}\n")
        return 2

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

    print("D-STMTPEND — a fault that already happened outranks the rest of "
          f"the statement    sides: {', '.join(sides)}")
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
              "    n.syn.zork = a syntax error with NO pending code is still "
              "ERR 2.\n"
              "    n.dz.w     = an ordinary numeric fault reports its OWN code "
              "(11).\n"
              "    u.syn.for  = the UNTRAPPED reading -- ONE message, naming "
              "its line.\n"
              "    u.dz.w     = an untrapped numeric fault, the OTHER "
              "message.\n"
              "    b.warm     = the cold-boot template off the NORMAL reset, a "
              "LITERAL want\n"
              "                 (b.cold shares its template, readout and "
              "reset builder).\n"
              "    🔴 Neither pair can fail because this slice's claim is "
              "wrong: one has\n"
              "    nothing pending to outrank, the other has nothing to be "
              "outranked BY.\n"
              "    🔴 CLASSIFY BY WHICH SIDE FAILED: red on a REFERENCE is a "
              "broken fixture\n"
              "    (report it, score nothing); red on zb is an ordinary "
              "divergence that\n"
              "    belongs in the row set, not in the control set.\n"
              "    Check build/*.rom, `make repack-machine` and `make "
              "latch-check`, THEN\n"
              "    re-read the rows. Exit 2 (not 1) = the instrument was "
              "broken.")
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
    print("SIDES: vg8020,cf3300,zb — ON ERROR, ERR, RESUME, FOR/NEXT, SCREEN, "
          "DEF USR, POKE, LINE, WIDTH, LOCATE, PRINT, SOUND, ON..GOTO, DIM and "
          "HEX$/OCT$/STRING$/MID$ are core MSX-BASIC, present on every MSX1, so "
          "BOTH references are legitimate oracles for every row here")
    print("DENOMINATOR: " + DENOMINATOR)
    if a.gate and dis:
        sys.stderr.write(f"stmtpend: {dis} reading(s) diverge\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
