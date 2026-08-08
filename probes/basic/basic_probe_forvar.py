#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""D-FORVAR — what a `FOR`/`NEXT` loop variable may BE.

`ex_for` (basic/program.asm) takes ONE `upcase`d char into `FOR_CUR` and stores
through `var_set`, exactly what `exr_lp` did before D-READVAR. The D-ARYLV scout
measured three rows of the consequence (`docs/arylv-msx1-scout.md`, both
references agreeing): `FOR AB=` and `FOR A%=` are `Syntax error` here and ` 4 `
there, and `FOR A(1)=` is `Syntax error` on all three sides.

🔴 THREE READINGS ARE NOT A RULE. They say the NAME parse diverges; they do not
say what the rule IS, and `FOR` differs from `READ` in the one way that matters:
**`NEXT` matches on the stored name**, so generalising the name moves the MATCH
too. Every question below is one a fix has to answer and none of the three
measured rows asks:

  1. NAME FORM. 1-char / 2-char / 3+-char (2 significant) / letter+digit. A
     parse that accepts `AB` need not accept `A1`, and `INDEX` vs `IN` decides
     whether the frame key is the same 2-significant-char key every other
     reference in this tree uses.
  2. TYPE SUFFIX. `%` `!` `#` are three more names for the same letter, and
     `$` is the ONE shape `ex_for` already guards (`Type mismatch`, not
     `Syntax error`). Whether the SUFFIX is part of the loop variable's
     identity is what decides whether the type belongs in the FOR frame at all.
  3. 🎯 WHETHER `NEXT` MATCHES ON THE TYPE. `FOR A%=… : NEXT A` is the row that
     separates "the frame stores a NAME" from "the frame stores a TYPED name".
     One row cannot answer it and no measured row asks it.
  4. `NEXT` FORM. bare / named-matching / named-MISmatching / multi-variable
     (`NEXT B,A`) / a `$` name. A one-char match answers `NEXT A` = `FOR AB`
     TRUE today; a two-char key answers FALSE. Both are implementations; only
     the reference says which is the rule.
  5. NESTING, incl. a named `NEXT` that closes an inner frame — the path that
     walks the stack comparing keys, i.e. the one the widened key changes.
  6. 🔴 DEPTH. A wider frame in a fixed-size stack is fewer frames unless the
     stack moves. `f.dep8` is the row that says whether a fix quietly bought
     its key with a nesting level.
  7. IDENTITY. Do `A`, `A%` and `A$` collide as loop variables?

🟢 THE THREE CONTROLS ARE LOAD-BEARING, NOT DECORATION.
  * `c.for`  — `FOR I=1 TO 3`, the single-letter shape `ex_for` DOES handle. It
    is what makes every red row below a statement about the NAME parse rather
    than about `FOR` being broken.
  * `c.next` — `NEXT I`, the NAMED single-letter match. `ex_next` has its own
    parse and its own compare; without this row a red `n.two` has two candidate
    causes ([[row-with-two-candidate-causes]]).
  * `c.let`  — `AB=7` / `PRINT AB`. The 2-char name STORE, reached through
    `var_name_key`, which is the machinery a fix reuses. If this is red, a red
    `f.two` is a missing store, not a missing parse.
  A control failure exits 2 (the instrument broke), never 1 (a regression).

🔴 `f.ary` IS A NEGATIVE CONTROL. `FOR A(1)=1 TO 3` is `Syntax error` on BOTH
references. Whatever generalises the NAME here, the array form must KEEP
failing — this is a name residual, not an array one, and a fix that folds it
into D-ARYLV's shape would score green for the wrong reason
([[gate-whose-answer-is-an-error-passes-a-dead-subject]]).

🔴 TWO ROWS ARE DEFERRED, AND ONE OF THEM IS WHY. `NEXT B,A` reads ` 3  3 ` on
both references and `Syntax error` here — but so does `n.multi1`, the identical
comma with the SINGLE-LETTER names `ex_for` already parses. That is a LIST rule,
not a NAME rule, and it is filed and measured rather than folded in.

⚠️ `x.numstr` / `x.strtop` ARE NOT `FOR` ROWS, and they are here because the
DESIGN forced them (spec §4.2): the cheapest way to make `NEXT A$` miss every
frame is to stop `var_name_key` reporting a `$` name's resolved type as DOUBLE,
and `ev_f_var` reads that same cell. A side effect that is measured is a
finding; one that is not is a regression.

THE READING is the `[...]` span printed BY THE RUN, taken from the screen tail
after `RUN` — never the whole screen. D-READVAR measured that trap: the echo of
`PRINT"[";A;"]"` contains a `[`, so a whole-screen scan turns "the machine
printed nothing" into an artifact shaped exactly like a reading, on every
divergent row at once ([[readout-blind-to-its-own-subject]]).

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

# (label, [program body lines]). The last body line prints the read-back inside
# `[...]`; only that span is compared. A row whose reference answer is an ERROR
# prints `[OK]` on the line AFTER the statement under test, so "the error fired"
# and "the statement was skipped" cannot read alike.
CASES = [
    # --- controls: each names a DIFFERENT thing that could break -------------
    ("c.for",    ['FOR I=1 TO 3', 'NEXT', 'PRINT"[";I;"]"']),
    ("c.next",   ['FOR I=1 TO 3', 'NEXT I', 'PRINT"[";I;"]"']),
    ("c.let",    ['AB=7', 'PRINT"[";AB;"]"']),
    # --- 1. NAME FORM -------------------------------------------------------
    ("f.two",    ['FOR AB=1 TO 3', 'NEXT', 'PRINT"[";AB;"]"']),
    ("f.long",   ['FOR INDEX=1 TO 3', 'NEXT', 'PRINT"[";INDEX;"]"']),
    ("f.dig",    ['FOR A1=1 TO 3', 'NEXT', 'PRINT"[";A1;"]"']),
    # 2 significant chars: ABC and AB are the SAME variable everywhere else in
    # this tree, and this row says whether a loop variable is keyed the same way.
    ("f.alias",  ['FOR ABC=1 TO 3', 'NEXT', 'PRINT"[";AB;"]"']),
    # --- 2. TYPE SUFFIX -----------------------------------------------------
    ("f.pct",    ['FOR A%=1 TO 3', 'NEXT', 'PRINT"[";A%;"]"']),
    ("f.bang",   ['FOR A!=1 TO 3', 'NEXT', 'PRINT"[";A!;"]"']),
    ("f.hash",   ['FOR A#=1 TO 3', 'NEXT', 'PRINT"[";A#;"]"']),
    ("f.twopct", ['FOR AB%=1 TO 3', 'NEXT', 'PRINT"[";AB%;"]"']),
    # the ONE lvalue shape ex_for already guards as a TYPE error, not a syntax
    # error — carried so a fix cannot quietly re-route it to `Syntax error`
    ("f.str",    ['FOR A$=1 TO 3', 'NEXT', 'PRINT"[OK]"']),
    # --- 3. does NEXT match on the TYPE? ------------------------------------
    ("n.xtype",  ['FOR A%=1 TO 3', 'NEXT A', 'PRINT"[";A%;"]"']),
    # --- 4. NEXT FORM -------------------------------------------------------
    ("n.two",    ['FOR AB=1 TO 3', 'NEXT AB', 'PRINT"[";AB;"]"']),
    ("n.pct",    ['FOR A%=1 TO 3', 'NEXT A%', 'PRINT"[";A%;"]"']),
    # 🎯 a ONE-CHAR match says `NEXT A` closes `FOR AB`; a two-char key says it
    # does not. The old shim answers the first, and nothing measured says which.
    ("n.prefix", ['FOR AB=1 TO 3', 'NEXT A', 'PRINT"[OK]"']),
    ("n.wrong",  ['FOR AB=1 TO 3', 'NEXT CD', 'PRINT"[OK]"']),
    ("n.strnx",  ['FOR A=1 TO 3', 'NEXT A$', 'PRINT"[OK]"']),
    ("n.multi",  ['FOR AB=1 TO 2', 'FOR CD=1 TO 2', 'NEXT CD,AB',
                  'PRINT"[";AB;CD;"]"']),
    # 🔴 THE ROW THAT SEPARATES TWO RULES. n.multi is red here for either of two
    # reasons -- the NAME or the COMMA -- and one row cannot say which
    # ([[one-row-cannot-separate-two-rules]]). This one holds the name FIXED at
    # the single letter ex_for already parses, so it reads the COMMA alone.
    ("n.multi1", ['FOR A=1 TO 2', 'FOR B=1 TO 2', 'NEXT B,A',
                  'PRINT"[";A;B;"]"']),
    # --- 8. the `$` name in a NUMERIC factor -- forced by §4.2's design ------
    # Not a FOR question, and here because the cheapest way to make `NEXT A$`
    # miss every frame is to stop `var_name_key` reporting a `$` name's resolved
    # type as DOUBLE. `ev_f_var` reads that cell through `check_vartype_num`, so
    # the design has to know what these two answer BEFORE it is chosen -- a side
    # effect that is measured is a finding, one that is not is a regression.
    ("x.numstr", ['A$="X"', 'B=1+A$', 'PRINT"[";B;"]"']),
    ("x.strtop", ['A$="X"', 'B=A$', 'PRINT"[";B;"]"']),
    # --- 5. NESTING ---------------------------------------------------------
    ("n.nest",   ['FOR AB=1 TO 2', 'FOR CD=1 TO 2', 'NEXT CD', 'NEXT AB',
                  'PRINT"[";AB;CD;"]"']),
    # a named NEXT that CLOSES the inner frame — the stack-walking compare
    ("n.close",  ['FOR AB=1 TO 2', 'FOR CD=1 TO 2', 'NEXT AB',
                  'PRINT"[";AB;CD;"]"']),
    # 🎯 A BARE `NEXT` THAT FOLLOWS A NAMED ONE. This row exists because a KNIFE
    # was drafted before the row set was frozen ([[draft-the-knives-before-
    # freezing-the-row-set]]): the bare-NEXT sentinel is 3 bytes of new code, and
    # against every OTHER row cutting it changes nothing — a lone bare `NEXT`
    # re-reads the key `ex_for` itself just wrote, which matches its own frame by
    # accident. Only a bare NEXT whose scratch holds a DIFFERENT loop's key can
    # see it.
    ("n.mixnx",  ['FOR AB=1 TO 2', 'FOR CD=1 TO 2', 'NEXT CD', 'NEXT',
                  'PRINT"[";AB;CD;"]"']),
    # --- 6. DEPTH — a wider frame is fewer frames unless the stack moves -----
    ("f.dep8",   ['FOR A=1 TO 1', 'FOR B=1 TO 1', 'FOR C=1 TO 1',
                  'FOR D=1 TO 1', 'FOR E=1 TO 1', 'FOR F=1 TO 1',
                  'FOR G=1 TO 1', 'FOR H=1 TO 1', 'NEXT H', 'NEXT G',
                  'NEXT F', 'NEXT E', 'NEXT D', 'NEXT C', 'NEXT B', 'NEXT A',
                  'PRINT"[OK]"']),
    # --- 7. IDENTITY --------------------------------------------------------
    ("f.coll",   ['A=9', 'FOR A%=1 TO 3', 'NEXT', 'PRINT"[";A;A%;"]"']),
    ("f.colls",  ['A$="X"', 'FOR A=1 TO 3', 'NEXT', 'PRINT"[";A;A$;"]"']),
    # --- the DEFtbl, which is what supplies the type when there is no suffix -
    ("f.defint", ['DEFINT A', 'FOR AB=1 TO 3', 'NEXT', 'PRINT"[";AB;"]"']),
    ("f.defstr", ['DEFSTR A', 'FOR AB=1 TO 3', 'NEXT', 'PRINT"[OK]"']),
    # --- STEP with a widened name, so the whole frame is exercised ----------
    ("f.step",   ['FOR AB=10 TO 1 STEP -3', 'NEXT', 'PRINT"[";AB;"]"']),
    # --- the NEGATIVE control ------------------------------------------------
    ("f.ary",    ['DIM A(3)', 'FOR A(1)=1 TO 3', 'NEXT', 'PRINT"[OK]"']),
]
CONTROLS = ("c.for", "c.next", "c.let")
CONTROL_WANT = {"c.for": " 4 ", "c.next": " 4 ", "c.let": " 7 "}
NEGATIVE = ("f.ary",)
LABEL_W = 9

# --- DEFERRED rows: measured, printed, NEVER scored -------------------------
# ⚠️ "A row that can only ever be red is doc debt, not a gate." A MULTI-VARIABLE
# `NEXT` is a LIST rule, not a NAME rule, and `n.multi1` is the row that proves
# it: it holds the name fixed at the single letter `ex_for` already parses and is
# STILL `Syntax error` here against ` 3  3 ` on both references. `ex_next` runs
# `jp exec_stmt` past a closed frame and the `,` lands in statement position.
# Folding it in would leave no row able to separate the two rules
# ([[one-row-cannot-separate-two-rules]]). Both stay MEASURED and PRINTED -- a
# deferral has to carry its evidence -- and are excluded from the tally in BOTH
# directions. Filed in TODO.md as its own residual.
DEFERRED = {
    "n.multi":  "DEFERRED — multi-variable NEXT is a LIST rule; see n.multi1",
    "n.multi1": "DEFERRED — the SAME comma with a single-letter name: the "
                "comma, not the name",
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
    for label, lines in CASES:
        if only and label not in only:
            continue
        body = [f"{10 * (k + 1)} {ln}" for k, ln in enumerate(lines)]
        caps = omsx_repl.run_cases(
            cfg["machine"],
            [("direct", list(cfg["reset"]) + body + ["RUN"])],
            batch=False, boot=cfg["boot"], step=cfg["step"], **kw)
        out[label] = bracket(caps[0])
    return out


def main() -> int:
    ap = argparse.ArgumentParser(
        description="D-FORVAR: what a FOR/NEXT loop variable may be")
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
    present = [lab for lab, _ in CASES if any(lab in results[s]
                                             for s in sides)]

    print("D-FORVAR — what a FOR/NEXT loop variable may BE   "
          f"sides: {', '.join(sides)}")
    print("=" * 78)

    # --- the POSITIVE controls, first and gating ----------------------------
    # ⚠️ A control failure is classified by WHICH SIDE failed it: red on a
    # REFERENCE means the fixture is broken (exit 2, nothing scored); red on
    # zerobas before the fix would be an ordinary divergence. All three shapes
    # here ship today, so either side going red is the instrument, not the rule
    # ([[classify-a-control-failure-by-which-side-failed-it]]).
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
              "    c.for  = `FOR I=1 TO 3`, the single-letter shape ex_for "
              "DOES handle.\n"
              "    c.next = `NEXT I`, the NAMED single-letter match -- "
              "ex_next has its own\n"
              "             parse and its own compare, so a red n.two "
              "without this row\n"
              "             has two candidate causes.\n"
              "    c.let  = `AB=7`, the 2-char name STORE a fix reuses. Red "
              "here means a\n"
              "             red f.two is a missing STORE, not a missing "
              "parse.\n"
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
        if lab in NEGATIVE:
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
          f"{len(NEGATIVE)} negative control, "
          f"{refsplit} row(s) with no oracle, "
          f"{len(DEFERRED)} DEFERRED row(s) measured but not scored)")
    print("SIDES: vg8020,cf3300,zb — FOR/NEXT is core BASIC, present on every "
          "MSX1, so BOTH references are legitimate oracles for every row here")
    print("DENOMINATOR: (NAME FORM: 1-char / 2-char / 3+-char / letter+digit) x "
          "(TYPE SUFFIX: none / % / ! / # / $) x (NEXT FORM: bare / named / "
          "mismatched / multi-variable), plus whether NEXT matches on the TYPE, "
          "plus nesting and a named NEXT that CLOSES an inner frame, plus the "
          "nesting DEPTH a wider frame could silently buy its key with, plus "
          "the A / A% / A$ identity, plus the DEFtbl that supplies the type "
          "when there is no suffix, plus the array form both references REFUSE")
    if a.gate and dis:
        sys.stderr.write(f"forvar: {dis} reading(s) diverge\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
