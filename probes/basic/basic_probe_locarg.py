#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""D-LOCARG — LOCATE's three arguments are CHECKED COERCIONS, and a DEFERRED
expression error outranks the coercion's own overflow at every one of them.

D-EVALCHK (docs/spec-basic-evalchk.md §6.6) measured FOUR rows against LOCATE
and then DECLINED the -29 B carve that would fold `loc_next`'s hand-inlined
two-stage domain check into `eval_byte_checked`, on the grounds that four rows
are not a denominator and that the carve deletes a defensive apparatus (the
`LOC_RET` parked frame) on the strength of a refuted comment.

🔴 THE "MISSING DENOMINATOR" WAS HALF-BUILT ALREADY, AND §6.6 DID NOT KNOW IT.
`make missing-acceptance` (probes/basic/basic_probe_missing.py, batteries
`locate` / `locerr` / `locrow` / `xchk`) is 214 recorded rows and it already
covers every axis §6.6 listed as absent: row/column, the omitted arguments,
the `CON_LASTROW` / `LINLEN` clamps, and the CSRLIN/POS read-back. That gate is
this slice's GREEN control set and is deliberately NOT duplicated here.

What it does NOT cover is the class the carve actually moves, so THAT is what
this probe measures:

  1. 🎯 THE DEFERRED-ERROR RANK, at each of the three argument positions and
     through an OMITTED one. `70000+0*(1/0)` both faults (ERR 11) and overflows
     int16 (ERR 6); `70000+0*SQR(-1)` faults with a DIFFERENT code (ERR 5) and
     overflows the same way. Two codes, one shape -- which is what makes this a
     RULE about rank and not "division by zero is special".
  2. THE RANK'S OTHER HALF, which is already green and says so: `1/0` and
     `SQR(-1)` alone (no overflow) and `256+0*(1/0)` (a fault plus the ERR 5
     BYTE stage, not the ERR 6 int16 one). A carve that reports these correctly
     for a NEW reason must keep reporting them.
  3. WHICH ARGUMENT x PRESENT / OMITTED x {in range, >255, negative, >int16,
     string, missing, a 4th}. `loc_next` is called from three sites and the
     carve edits the routine, so every site is a caller of the cut.
  4. 🎯 THE CURSOR SIDE EFFECT ON EVERY ROW. A domain error must leave the
     cursor exactly where it was (batch-then-apply), and a FOURTH argument must
     apply the first three and only then reject. Reading the error code alone
     cannot see either, and both are what the `LOC_RET` apparatus is FOR.
  5. 🎯 THE UNTRAPPED FACE, which is the apparatus test proper. The comment the
     carve deletes records what a wrongly-framed abort looked like -- `LOCATE
     "5",3` printing `type mismatch` AND THEN `missing operand`, i.e. the
     handler carrying on parsing after the abort had already printed. Battery
     `u.*` runs every abort class untrapped and reads the whole screen tail, so
     a second message, or a `[RANON]` that should never print, is visible.

TWO READINGS, ONE GRAMMAR.

  * `t.*` rows are TRAPPED and read `[ ERR  CSRLIN  POS(0) ]` -- the code AND
    the cursor, from inside the handler, before anything prints. Every `t.*`
    program does a runtime `CLS` first, so the only `[` on the screen is the
    one it printed.
  * `u.*` rows are UNTRAPPED and read the clipped `screen_tail` of `RUN` -- the
    message text, its line number, whether it printed ONCE, and whether the
    next line ran. A `[...]`-only reading is structurally blind to all four
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

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lib"))
import omsx_repl                                                 # noqa: E402
import probe_report                                              # noqa: E402
import probe_tmp                                                 # noqa: E402

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

# The TRAPPED program. `stmt` runs at line 20; the handler captures ERR and the
# cursor BEFORE anything is printed and RESUMEs at the printer.
# ⚠️ Line 30 exists so the NO-ERROR path reads the same two cells at the same
# point; the handler must not RESUME into a re-read of them.
TRAP_PROG = [
    "10 ON ERROR GOTO 100",
    "20 {stmt}",
    "30 E=0:Y=CSRLIN:X=POS(0)",
    '40 PRINT"[";E;Y;X;"]":END',
    "100 E=ERR:Y=CSRLIN:X=POS(0):RESUME 40",
]
# The UNTRAPPED program. Line 20 is the run-on detector: an abort at line 10
# must not reach it.
UNTRAP_PROG = [
    "10 {stmt}",
    '20 PRINT"[RANON]"',
]

# Every `t.*` statement seeds the cursor with `LOCATE 7,4` after the CLS, so an
# UNCHANGED cursor reads ` 4  7 ` and is distinguishable from the CLS home
# position ` 0  0 ` -- a seed of 0,0 would make "did not move" and "moved to
# home" the same reading.
# 🔴 WITH ONE EXCEPTION, AND KNIFE K-LA5 FOUND IT (docs/spec-basic-locarg.md
# §8.3): the seed is itself a `LOCATE`, so a cut that breaks LOCATE's accept path
# breaks the SEED too, and `t.zero` -- whose target IS home -- then reads
# ` 0  0  0 ` either way. Sound in the shipped tree, blind under that cut. The
# row stays as it is: `LOCATE 0` being a VALUE and not an omission is what it is
# for, and narrowing the claim is cheaper than losing the row (TODO.md).
SEED = "CLS:LOCATE 7,4:"

# (label, kind, statement)   kind: "t" trapped / "u" untrapped
CASES = [
    # --- in-range: the reading itself, and the omitted-argument grid ---------
    ("t.ok",       "t", "CLS:LOCATE 5,3"),
    ("t.ok3",      "t", "CLS:LOCATE 5,3,1"),
    ("t.zero",     "t", SEED + "LOCATE 0,0"),
    ("t.omitc",    "t", SEED + "LOCATE ,2"),
    ("t.omitr",    "t", SEED + "LOCATE 3"),
    ("t.omitr2",   "t", SEED + "LOCATE 3,,1"),
    ("t.omitb",    "t", SEED + "LOCATE ,,1"),
    # --- the domain grid: WHICH argument x WHICH fault ----------------------
    # `loc_next` is one routine called from three sites, so each site is a
    # caller of the cut and each is asked the same four questions.
    ("t.c.256",    "t", SEED + "LOCATE 256,3"),
    ("t.c.neg",    "t", SEED + "LOCATE -1,3"),
    ("t.c.ov",     "t", SEED + "LOCATE 70000,3"),
    ("t.c.str",    "t", SEED + 'LOCATE "5",3'),
    ("t.r.256",    "t", SEED + "LOCATE 5,256"),
    ("t.r.neg",    "t", SEED + "LOCATE 5,-1"),
    ("t.r.ov",     "t", SEED + "LOCATE 5,70000"),
    ("t.r.str",    "t", SEED + 'LOCATE 5,"3"'),
    ("t.u.256",    "t", SEED + "LOCATE 5,3,256"),
    ("t.u.ov",     "t", SEED + "LOCATE 5,3,70000"),
    ("t.u.str",    "t", SEED + 'LOCATE 5,3,"1"'),
    # ...and through an OMITTED position, which is the only way to reach the
    # second and third sites without a first argument having been accepted.
    ("t.om.r256",  "t", SEED + "LOCATE ,256"),
    ("t.om.u256",  "t", SEED + "LOCATE ,,256"),
    # --- the grammar faults: Missing operand is a DISTINCT error -------------
    ("t.bare",     "t", SEED + "LOCATE"),
    ("t.trailc",   "t", SEED + "LOCATE 5,"),
    ("t.trailu",   "t", SEED + "LOCATE 5,3,"),
    ("t.colon",    "t", SEED + "LOCATE 5,3,:"),
    # 🎯 APPLY-THEN-REJECT: a fourth argument must find the first three ALREADY
    # applied. The only row here whose cursor is expected to MOVE on an error.
    ("t.four",     "t", SEED + "LOCATE 1,1,1,1"),
    # --- 🔴 THE SUBJECT: a DEFERRED expression error, at each site -----------
    # Already green (the fault does not overflow, so nothing overwrites FPERR):
    ("t.c.div",    "t", SEED + "LOCATE 1/0,3"),
    ("t.c.sqr",    "t", SEED + "LOCATE SQR(-1),3"),
    ("t.c.b5div",  "t", SEED + "LOCATE 256+0*(1/0),3"),
    # 🔴 The divergence: the fault ALSO overflows int16, so the coercion's own
    # ERR 6 overwrote it. Two different fault codes, one shape.
    ("t.c.ovdiv",  "t", SEED + "LOCATE 70000+0*(1/0),3"),
    ("t.c.ovsqr",  "t", SEED + "LOCATE 70000+0*SQR(-1),3"),
    ("t.r.ovdiv",  "t", SEED + "LOCATE 5,70000+0*(1/0)"),
    ("t.u.ovdiv",  "t", SEED + "LOCATE 5,3,70000+0*(1/0)"),
    ("t.om.ovdiv", "t", SEED + "LOCATE ,70000+0*(1/0)"),
    # Does a TYPE fault outrank a pending numeric one? The two tests sit in one
    # routine in this tree and their ORDER is a claim.
    ("t.tmfp",     "t", SEED + "LOCATE STR$(1/0),3"),
    # --- the UNTRAPPED face: one message, at the right line, and STOP --------
    ("u.ok",       "u", "LOCATE ,,1"),
    ("u.bare",     "u", "LOCATE"),
    ("u.str",      "u", 'LOCATE "5",3'),
    ("u.256",      "u", "LOCATE 256,3"),
    ("u.neg",      "u", "LOCATE -1,3"),
    ("u.ov",       "u", "LOCATE 70000,3"),
    ("u.trail",    "u", "LOCATE 5,"),
    ("u.r256",     "u", "LOCATE 5,256"),
    ("u.u256",     "u", "LOCATE 5,3,256"),
    ("u.div",      "u", "LOCATE 1/0,3"),
    ("u.ovdiv",    "u", "LOCATE 70000+0*(1/0),3"),
]

# 🟢 THE POSITIVE CONTROLS. Two per reading, because the two readings can fail
# independently and a `t.*` battery that has gone blind looks exactly like a
# `t.*` battery that agrees.
#   t.ok      the trapped reading works AND an accepted LOCATE took effect
#   t.c.256   an ORDINARY domain error traps, reports 5, and moved nothing
#   u.ok      the untrapped reading works and an accepted LOCATE runs on
#   u.bare    an ORDINARY LOCATE abort prints ONE message, naming its line
# A control failure exits 2 (the instrument broke), never 1 (a regression).
CONTROLS = ("t.ok", "t.c.256", "u.ok", "u.bare")

# 🔴 PREDICTIONS, WRITTEN BEFORE THE FIRST RUN. A control's expectation is not
# allowed to be back-filled silently from the result column
# ([[a-prediction-copied-into-the-result-column]]). Misses are recorded in
# docs/locarg-msx1-characterization.md §3, not absorbed.
CONTROL_WANT = {
    "t.ok":    " 0  3  5 ",
    "t.c.256": " 5  4  7 ",
    "u.ok":    "[RANON]",
    "u.bare":  "Missing operand in 10",
}

# Rows the carve must NOT move. Each is a shape adjacent to the rule, already
# agreeing on all three sides, that an over-reaching carve reddens.
NEGATIVE = {
    "t.c.str":  "NEGATIVE CONTROL — the TYPE test must stay AHEAD of the "
                "coercion",
    "t.bare":   "NEGATIVE CONTROL — Missing operand (24), NOT Syntax error",
    "t.four":   "NEGATIVE CONTROL — apply-then-reject: the cursor DID move",
    "t.c.b5div": "NEGATIVE CONTROL — a fault that does NOT overflow was "
                 "already right",
}
LABEL_W = 11

# --- DEFERRED: measured, printed, NEVER scored ------------------------------
# 🔴 `t.tmfp` IS A ROW THIS SLICE FOUND AND DID NOT FIX, AND IT IS THE ONE THE
# CARVE DOES NOT MOVE. `LOCATE STR$(1/0),3` leaves BOTH deferred flags live: a
# numeric fault (FPERR = 11, from the `1/0` inside `STR$`) and a type fault
# (TMISMATCH, from the string that came back). Both references report 11;
# zerobas reports 13, before AND after the carve, because the test order is the
# same either way -- `loc_next`'s own inline `ld a,(TMISMATCH)` before, and
# `check_expr_errors`' TMISMATCH-then-FPERR after.
# 🎯 IT IS `t.c.str` THAT MAKES THIS READABLE AS A RULE AND NOT A GLITCH: a type
# fault with NO pending numeric one is 13 on all three sides. So the claim is
# narrow and testable -- a pending numeric fault outranks the type test too --
# and it is the SAME rank rule the rest of this gate measures, one level up.
# 💰 PRICED AND DECLINED. `check_expr_errors` is a two-entry-point routine whose
# second entry (`check_fperr_only`) is a FALL-IN, which is what makes the pair
# cost 0 extra bytes; testing FPERR first breaks that fall-in and needs the
# FPERR test written twice, +7..+9 B. That is affordable -- and it is NOT the
# reason. The reason is the DENOMINATOR: `check_expr_errors` has four other
# callers (`ex_if`, `exp_num` via print.asm, `ex_let`, and `eval_chan` since
# D-BADFNUM, whose own header records that its ordering was CHANGED on a
# measurement), and the order may not move until each of them has a
# both-flags-pending row of its own. D-EVALCHK §5.1 froze this order as a
# forced constraint on the strength of `PRINT #A$,"X"` -- a row with a type
# fault and NO pending numeric one, which cannot discriminate. Filed in TODO.md.
# ✅ CLOSED 2026-08-09 BY D-TMFP (docs/spec-basic-tmfp.md). `t.tmfp` is now
# SCORED and agrees on all three sides. The dict is deliberately kept, empty,
# rather than deleted: the machinery that prints a measured-but-unscored row is
# what makes the next deferral cheap to file.
# 🔴 THE FILED RULE WAS WRONG AND SO WAS ITS DENOMINATOR. It is not that a
# numeric fault OUTRANKS a type fault -- it is that whichever fault happened
# FIRST is reported, because the reference raises eagerly. `WIDTH (A$<5)+0*(1/0)`
# has both flags pending and reads 13 on both references, and D-EVALCHK §5.1
# froze the opposite order on it; no static test order satisfies both rows. The
# fix is not in check_expr_errors at all (nor in its "four other callers" -- the
# tree has twelve, plus two further hand-rolled copies of the ordering and four
# readers that never test FPERR): it is one guard at type_mismatch_set,
# TMISMATCH's only writer, for +5 B.
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
    return [ln.format(stmt=stmt) for ln in tpl]


def read_case(kind: str, raw: str | None) -> str:
    """Trapped rows read the printed `[ERR CSRLIN POS]` triple; untrapped rows
    read the clipped screen tail of `RUN`.

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
            dsk = probe_tmp.tmp(f"zb_locarg_{side}_{label}.dsk")
            shutil.copy(TEST_DSK, dsk)
            kw["diska"] = dsk
        lines = list(cfg["reset"]) + program(kind, stmt) + ["RUN"]
        caps = omsx_repl.run_cases(
            cfg["machine"], [("direct", lines)],
            batch=False, reset=(), boot=cfg["boot"], step=cfg["step"], **kw)
        out[label] = read_case(kind, caps[0])
    return out


DENOMINATOR = (
    "(WHICH argument: column / row / cursor, and each of them reached "
    "DIRECTLY or through an OMITTED earlier one) x (WHICH fault: in range, "
    ">255, negative, >int16, string, missing operand, a 4th argument, and a "
    "DEFERRED expression error) x (whether the deferred fault ALSO overflows "
    "int16 -- the discriminator between 'reported for the right reason' and "
    "'reported because nothing overwrote it') x (WHICH deferred code: 11 from "
    "1/0 vs 5 from SQR(-1), so the rule is about RANK and not about division) "
    "x (the CURSOR side effect on every row: unchanged on a domain error, "
    "applied before a 4th-argument rejection) x (TRAPPED vs UNTRAPPED, the "
    "second reading the message text, its line number, and whether it printed "
    "ONCE). The POSITION/clamp/omitted-argument axes are NOT re-measured here: "
    "they are `make missing-acceptance`, 214 recorded rows, which is this "
    "slice's green control set."
)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="D-LOCARG: LOCATE's arguments are checked coercions")
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

    print("D-LOCARG — LOCATE's arguments are CHECKED COERCIONS   "
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
              "    t.ok    = the TRAPPED reading itself -- ERR, CSRLIN and "
              "POS(0) captured\n"
              "              inside the handler. Red here and every t.* row "
              "has two causes.\n"
              "    t.c.256 = an ORDINARY domain error: code 5, cursor "
              "unmoved. Red here and\n"
              "              the divergence is NOT about deferred errors.\n"
              "    u.ok    = the UNTRAPPED reading -- an accepted LOCATE and "
              "the run-on line.\n"
              "    u.bare  = an ordinary LOCATE abort prints ONE message "
              "naming its line.\n"
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
    print("SIDES: vg8020,cf3300,zb — LOCATE, ON ERROR, ERR, CSRLIN and POS are "
          "core MSX-BASIC, present on every MSX1, so BOTH references are "
          "legitimate oracles for every row here")
    print("DENOMINATOR: " + DENOMINATOR)
    if a.gate and dis:
        sys.stderr.write(f"locarg: {dis} reading(s) diverge\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
