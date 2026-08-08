#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""D-ARYLV carve scout — how WIDE is the array-lvalue target surface?

`docs/inputary-msx1-characterization.md` established the CLASS: six divergent
rows across `READ` and `INPUT`, every one of them the literal form `A(1)`, all
caused by `var_name_key` (basic/vars.asm) walking a name and a type suffix and
never a subscript. That answers *does it diverge*. It does not answer *how much
of the surface a fix has to cover*, and a fix scoped to the rows that happened to
be measured is a fix scoped to a hand-picked denominator
([[a-hand-listed-denominator-is-a-scope-claim]]).

THIS PROBE IS THE SCOUT'S DENOMINATOR, and it asks the four things the six rows
do NOT ask, plus one the whole class never asked at all:

  1. SUBSCRIPT FORM. Every measured row uses a literal `1`. A target parse that
     accepts `A(1)` need not accept `A(I)` or `A(1+1)`, because those go through
     the array engine's subscript EVALUATOR rather than a constant. If the
     references take them, the fix cannot special-case a literal.
  2. RANK. Every measured row is one-dimensional. `A(1,2)` is a second index
     through the same parse.
  3. THE ERROR FACE. `A(9)` against `DIM A(3)` is the one row here whose
     reference answer is expected to be an ERROR — and a fix that answers
     `Syntax error` to it would score "agrees with the reference" for entirely
     the wrong reason if the row were left out
     ([[gate-whose-answer-is-an-error-passes-a-dead-subject]]).
  4. POSITION IN THE LIST. `READ A(1),B` and `READ B,A(1)` are different: the
     first tests the array target as the list's HEAD, the second as a
     CONTINUATION reached through the comma loop. One row cannot separate them.
  5. 🔴 `FOR`. `ex_for` (basic/program.asm) still parses its loop variable with
     the SINGLE-LETTER shim `ex_read` stopped using at D-READVAR — one `upcase`d
     char into `FOR_CUR`, then `var_set`. So `FOR A(1)=` cannot parse here, and
     neither can `FOR AB=` or `FOR A%=`. Whether that DIVERGES is unmeasured, and
     it decides whether the array work has FOUR parse sites or FIVE — and whether
     `FOR` is an array residual at all or a re-run of D-READVAR's own class in a
     verb nobody re-checked. Reading the code cannot answer it; only the
     references can.

🟢 THE THREE CONTROLS ARE LOAD-BEARING, NOT DECORATION.
  * `c.read` — a SCALAR `READ` target, the shape D-READVAR landed. If it is red,
    the tree is broken somewhere this probe is not measuring.
  * `c.let`  — `A(1)=7`, the array lvalue via `LET`. This is the row that says
    the element-address machinery (`ary_op0_resolve` / `ary_store_write`) is
    PRESENT and working, so every red row below is a missing *parse*, not a
    missing store. Without it, "zerobas refuses `READ A(1)`" has two candidate
    causes and no way to choose ([[row-with-two-candidate-causes]]).
  * `c.for`  — `FOR A=1 TO 3`, the single-letter shape `ex_for` does handle. It
    is what makes a red `f.two` / `f.pct` a statement about the NAME parse rather
    than about `FOR` being broken.
  A control failure exits 2 (the instrument broke), never 1 (the tree regressed).

⚠️ THE READ-BACK USES A LITERAL SUBSCRIPT EVEN WHEN THE TARGET DOES NOT.
`r.aryvar` writes through `A(I)` and reads back through `A(1)`. Printing through
the same form under test would make a red row unattributable: a blank screen
could be the target parse OR the rvalue parse, and the row could not say which.
The one exception is `r.ary2d` / `i.ary2d`, where there is no 1-D read-back for a
2-D element — noted rather than worked around.

THE READING is the `[...]` span printed BY THE RUN, taken from the screen tail
after `RUN` — never the whole screen. D-READVAR measured that trap: the echo of
`PRINT"[";A;"]"` contains a `[`, so a whole-screen scan turns "the machine printed
nothing" into an artifact shaped exactly like a reading, on every divergent row at
once ([[readout-blind-to-its-own-subject]]).

Clean-room: observed screen output only; both reference ROMs are black boxes.
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lib"))
import omsx_repl                                                 # noqa: E402
import probe_report                                              # noqa: E402

ZB_MACHINE = os.environ.get("ZEROBAS_BASIC_MACHINE",
                            "C-BIOS_MSX1_EU_REPACK_DISK")
REPO = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
TEST_DSK = os.path.join(REPO, "disk", "test720.dsk")

SIDES = {
    "vg8020": dict(machine="Philips_VG_8020", boot=8.0, step=2.5,
                   reset=("NEW",), diska=False),
    "cf3300": dict(machine="National_CF-3300", boot=14.0, step=4.5,
                   reset=("", "SCREEN 0", "NEW"), diska=True),
    "zb":     dict(machine=ZB_MACHINE, boot=8.0, step=2.5,
                   reset=("NEW",), diska=True),
}

# (label, [program body lines], [responses injected AFTER `RUN`]). The last body
# line prints the read-back inside `[...]`; only that span is compared.
CASES = [
    # --- controls: each names a DIFFERENT thing that could break -------------
    ("c.read",    ['DATA 7', 'READ A', 'PRINT"[";A;"]"'], []),
    ("c.let",     ['DIM A(3)', 'A(1)=7', 'PRINT"[";A(1);"]"'], []),
    ("c.for",     ['FOR A=1 TO 3', 'NEXT', 'PRINT"[";A;"]"'], []),
    # --- READ: subscript FORM (the six measured rows are all literal `1`) ----
    ("r.aryvar",  ['DATA 7', 'DIM A(3)', 'I=1', 'READ A(I)',
                   'PRINT"[";A(1);"]"'], []),
    ("r.aryexpr", ['DATA 7', 'DIM A(3)', 'READ A(1+1)',
                   'PRINT"[";A(2);"]"'], []),
    # --- READ: a TYPED array whose subscript is a VARIABLE. The ONE row that
    # separates ARY_TYPE from VARTYPE: evaluating the subscript `I` re-runs
    # var_name_key, which overwrites (VARTYPE) with I's type -- so a store that
    # reads VARTYPE instead of ARY_TYPE writes an int16 element as a double.
    # With an untyped `A(I)` both are the DEFtbl double and the substitution is
    # INVISIBLE; `A%(I)` is what makes it a reading rather than a coincidence.
    ("r.arypct",  ['DATA 7', 'DIM A%(3)', 'I=1', 'READ A%(I)',
                   'PRINT"[";A%(1);"]"'], []),
    # --- ...and the string sibling, which reaches the OTHER store arm --------
    ("r.arystrv", ['DATA HI', 'DIM A$(3)', 'I=1', 'READ A$(I)',
                   'PRINT"[";A$(1);"]"'], []),
    # --- READ: RANK ---------------------------------------------------------
    ("r.ary2d",   ['DATA 7', 'DIM A(3,3)', 'READ A(1,2)',
                   'PRINT"[";A(1,2);"]"'], []),
    # --- READ: the ERROR face -- the one row whose oracle should NOT be a value
    ("r.aryoor",  ['DATA 7', 'DIM A(3)', 'READ A(9)',
                   'PRINT"[";A(1);"]"'], []),
    # --- READ: POSITION in the variable list ---------------------------------
    ("r.mix",     ['DATA 7,8', 'DIM A(3)', 'READ A(1),B',
                   'PRINT"[";A(1);B;"]"'], []),
    ("r.mixrev",  ['DATA 7,8', 'DIM A(3)', 'READ B,A(1)',
                   'PRINT"[";B;A(1);"]"'], []),
    # --- INPUT: the same three questions on the other verb -------------------
    ("i.aryvar",  ['DIM A(3)', 'I=1', 'INPUT A(I)',
                   'PRINT"[";A(1);"]"'], ["7"]),
    ("i.ary2d",   ['DIM A(3,3)', 'INPUT A(1,2)',
                   'PRINT"[";A(1,2);"]"'], ["7"]),
    ("i.aryoor",  ['DIM A(3)', 'INPUT A(9)', 'PRINT"[";A(1);"]"'], ["7"]),
    ("i.mix",     ['DIM A(3)', 'INPUT A(1),B',
                   'PRINT"[";A(1);B;"]"'], ["7,8"]),
    # --- FOR: is there a FIFTH parse site, and is it array-shaped at all? ----
    ("f.ary",     ['DIM A(3)', 'FOR A(1)=1 TO 3', 'NEXT',
                   'PRINT"[";A(1);"]"'], []),
    ("f.two",     ['FOR AB=1 TO 3', 'NEXT', 'PRINT"[";AB;"]"'], []),
    ("f.pct",     ['FOR A%=1 TO 3', 'NEXT', 'PRINT"[";A%;"]"'], []),
]
CONTROLS = ("c.read", "c.let", "c.for")
CONTROL_WANT = {"c.read": " 7 ", "c.let": " 7 ", "c.for": " 4 "}
LABEL_W = 10

# --- DEFERRED rows: measured, printed, NEVER scored -------------------------
# ⚠️ "A row that can only ever be red is doc debt, not a gate." These two belong
# to a DIFFERENT residual: `ex_for` still parses its loop variable with the
# single-letter shim `ex_read` stopped using at D-READVAR, so `FOR AB=` and
# `FOR A%=` are Syntax error here and ` 4 ` on both references. That is a NAME
# rule, not an array one, and folding it into D-ARYLV would leave no row able to
# separate the two ([[one-row-cannot-separate-two-rules]]). They stay MEASURED
# and PRINTED -- a deferral has to carry its evidence -- and are excluded from
# the tally in both directions. Filed in TODO.md as its own item.
#
# 🔴 `f.ary` IS NOT HERE, AND THAT IS THE POINT. `FOR A(1)=1 TO 3` is Syntax
# error on BOTH references, so it is SCORED, as a NEGATIVE control: this slice
# must not make it work, and neither may the ex_for slice that clears the two
# rows below.
DEFERRED = {
    "f.two": "DEFERRED — ex_for's single-letter NAME shim, not an array target",
    "f.pct": "DEFERRED — ex_for's single-letter NAME shim, not an array target",
}

# A row that answers one of these is NEVER agreement, however many sides answer
# it -- two machines that both failed to print agree perfectly about nothing.
SENTINELS = ("<NO CAPTURE>", "<NO OUTPUT>")

ERRORS = ("Syntax error", "Type mismatch", "Subscript out of range",
          "Redimensioned array", "Illegal function call", "Out of memory",
          "Overflow", "Out of DATA", "Bad file number", "NEXT without FOR")


def bracket(raw: str | None) -> str:
    """The `[...]` span the RUN printed, or a sentinel naming what came instead.

    🔴 THE TAIL AFTER `RUN`, NOT THE WHOLE SCREEN -- see the module docstring."""
    if raw is None:
        return "<NO CAPTURE>"
    txt = " ".join(str(omsx_repl.screen_tail(raw, "RUN") or "").split("\n"))
    i = txt.find("[")
    j = txt.find("]", i + 1)
    if i >= 0 and j > i:
        return txt[i + 1:j]
    for e in ERRORS:
        if e in txt:
            return f"<{e}>"
    return "<NO OUTPUT>"


def run_side(side: str, only: list[str]) -> dict:
    cfg = SIDES[side]
    kw = {}
    if cfg["diska"]:
        kw["diska"] = TEST_DSK
    out = {}
    for label, lines, responses in CASES:
        if only and label not in only:
            continue
        body = [f"{10 * (k + 1)} {ln}" for k, ln in enumerate(lines)]
        caps = omsx_repl.run_cases(
            cfg["machine"],
            [("direct", list(cfg["reset"]) + body + ["RUN"] + list(responses))],
            batch=False, boot=cfg["boot"], step=cfg["step"], **kw)
        out[label] = bracket(caps[0])
    return out


def main() -> int:
    ap = argparse.ArgumentParser(
        description="D-ARYLV scout: how wide is the array-lvalue surface?")
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
    present = [lab for lab, _, _ in CASES if any(lab in results[s]
                                                 for s in sides)]

    print("D-ARYLV scout — the array-lvalue target surface beyond `A(1)`   "
          f"sides: {', '.join(sides)}")
    print("=" * 78)

    # --- the POSITIVE controls, first and gating ----------------------------
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
              "    c.read = a SCALAR READ target (D-READVAR's own shape).\n"
              "    c.let  = `A(1)=7`, the array lvalue MACHINERY -- if this is "
              "red, a red\n"
              "             row below is not a missing parse, it is a missing "
              "STORE, and\n"
              "             the whole scout is measuring the wrong thing.\n"
              "    c.for  = `FOR A=1 TO 3`, the single-letter shape ex_for DOES "
              "handle.\n"
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

    agree = dis = 0
    refsplit = deferred = 0
    for lab in present:
        vals = {s: results[s][lab] for s in sides if lab in results[s]}
        ok = len(set(vals.values())) == 1 and len(vals) > 1
        if any(v in SENTINELS for v in vals.values()):
            ok = False              # an apparatus sentinel is NEVER agreement
        refs = {vals[s] for s in ("vg8020", "cf3300") if s in vals}
        if lab in DEFERRED:
            # Printed, not scored — in EITHER direction. A deferred row that
            # started agreeing would be a finding, so it still shows its reading.
            deferred += 1
            print(probe_report.row("....", lab, LABEL_W, vals,
                                   f"   [{DEFERRED[lab]}]"))
            continue
        agree += ok
        dis += not ok
        note = "   [POSITIVE CONTROL]" if lab in CONTROLS else ""
        if lab == "f.ary":
            note = "   [NEGATIVE CONTROL — both references REFUSE this]"
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
          f"1 negative control, {refsplit} row(s) with no oracle, "
          f"{len(DEFERRED)} DEFERRED row(s) measured but not scored)")
    print("SIDES: vg8020,cf3300,zb — READ/INPUT/FOR and DIM are core BASIC, "
          "present on every MSX1, so both references are legitimate oracles here")
    print("DENOMINATOR: (subscript FORM: literal / variable / expression) x "
          "(RANK: 1-D / 2-D) x (POSITION: list head / continuation), plus the "
          "one row whose reference answer is an ERROR (a subscript out of "
          "range), plus FOR — which uses the SINGLE-LETTER shim ex_read "
          "stopped using, so it is a candidate FIFTH parse site AND a candidate "
          "re-run of D-READVAR's own name class")
    if a.gate and dis:
        sys.stderr.write(f"arylv: {dis} reading(s) diverge\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
