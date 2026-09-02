#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""D-NXLIST — `NEXT` takes a LIST of loop variables, not one.

D-FORVAR measured `NEXT B,A` on both references (` 3  3 `) against `Syntax
error` here and DEFERRED it, with `n.multi1` as the proof that it is a
DIFFERENT rule: the identical comma with the SINGLE-LETTER names `ex_for` has
always parsed is still `Syntax error`, so no NAME fix can reach it
([[one-row-cannot-separate-two-rules]]). `nx_end` runs `jp exec_stmt` once its
frame is closed and the `,` arrives in statement position.

🔴 TWO READINGS ARE NOT A RULE. They say a comma diverges; they do not say what
the LIST is. Every question below is one a fix has to answer and neither
measured row asks:

  1. 🎯 THE CONTINUES PATH. `NEXT B,A` is only `NEXT B : NEXT A` if the comma is
     NOT consumed while B's loop is still running -- `nx_again` jumps back to
     the body and never reaches the terminator. `m.count` counts the inner body
     executions, so a fix that consumes the comma early is a WRONG NUMBER here
     rather than an invisible one. This is the path a fix is most likely to
     break and no row existed for it.
  2. LIST LENGTH. Two, and three -- a rule stated from one comma is a rule
     about one comma.
  3. THE ELEMENTS. Does an element of the list obey `NEXT`'s own matching rule
     (name AND type, D-FORVAR `n.xtype`/`n.wrong`), or does a list relax it?
  4. THE DEGENERATE FORMS. A trailing comma (`NEXT B,`) with and without an
     outer frame; a leading comma (`NEXT ,B`); spaces around the comma.
  5. TERMINATION. A `:`-separated statement after the list, and the `:`
     separator itself in place of the comma -- which is what says the rule is
     about a COMMA and not about "any separator re-enters NEXT".
  6. `NEXT A(1)` -- unmeasured anywhere, and it inherits this statement's shape
     rather than having an answer of its own (spec-basic-forvar.md §3).

🟢 THE THREE POSITIVE CONTROLS ARE LOAD-BEARING, NOT DECORATION.
  * `c.for`   — `FOR I=1 TO 3` / `NEXT`, the bare loop. If this is red the
    machine is broken and nothing below it means anything.
  * `c.next`  — `NEXT I`, the NAMED match. Every subject row here is a named
    `NEXT` with something after it, so a red `m.two` without this row has two
    candidate causes ([[row-with-two-candidate-causes]]).
  * 🎯 `c.nest` — `NEXT B` / `NEXT A` as TWO STATEMENTS, the exact semantics the
    list is claimed to abbreviate. This is what makes a red `m.two` a statement
    about the COMMA rather than about nesting.
  A control failure exits 2 (the instrument broke), never 1 (a regression).

🔴 `n.num` IS A NEGATIVE CONTROL. `NEXT 1` is `Syntax error` on both references
and must STAY so: a comma test bolted onto `nx_end` is one edit away from
"anything after a closed frame re-enters NEXT", and a rule that accepts more
than the reference is not a fix ([[gate-whose-answer-is-an-error-passes-a-dead-
subject]]).

🔴 `n.nofor` / `n.barenofor` ARE THE CARVE'S OWN ROWS. The bytes that pay for
this slice come from merging `nx_find`'s empty-FOR-stack test with `nx_miss`'s
ran-out-of-frames test (spec §6.3). NO ROW IN THE FORVAR BATTERY ENTERS THROUGH
`nx_find`'s test: every mismatching row there has one frame, so it reaches
`nx_nofor` through `nx_miss`. A `NEXT` with no `FOR` at all is the only program
that takes the other entry, and the carve is unguarded without it.

THE READING is the `[...]` span printed BY THE RUN, taken from the screen tail
after `RUN` — never the whole screen ([[readout-blind-to-its-own-subject]]).

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
    # --- positive controls: each names a DIFFERENT thing that could break ----
    ("c.for",    ['FOR I=1 TO 3', 'NEXT', 'PRINT"[";I;"]"']),
    ("c.next",   ['FOR I=1 TO 3', 'NEXT I', 'PRINT"[";I;"]"']),
    # 🎯 the semantics the list is claimed to abbreviate, spelled out as two
    # statements. Green here + red on m.two = the comma, and nothing else.
    ("c.nest",   ['FOR A=1 TO 2', 'FOR B=1 TO 2', 'NEXT B', 'NEXT A',
                  'PRINT"[";A;B;"]"']),
    # --- 2. LIST LENGTH -----------------------------------------------------
    ("m.two",    ['FOR A=1 TO 2', 'FOR B=1 TO 2', 'NEXT B,A',
                  'PRINT"[";A;B;"]"']),
    ("m.name",   ['FOR AB=1 TO 2', 'FOR CD=1 TO 2', 'NEXT CD,AB',
                  'PRINT"[";AB;CD;"]"']),
    ("m.three",  ['FOR A=1 TO 2', 'FOR B=1 TO 2', 'FOR C=1 TO 2',
                  'NEXT C,B,A', 'PRINT"[";A;B;C;"]"']),
    # --- 1. 🎯 THE CONTINUES PATH -------------------------------------------
    # `NEXT B,A` is `NEXT B : NEXT A` ONLY if the comma is invisible while B is
    # still running. m.inner reads the two counters after asymmetric bounds;
    # m.count reads the number of INNER BODY executions, which is 3x2 iff the
    # comma was never consumed on a continue.
    ("m.inner",  ['FOR A=1 TO 3', 'FOR B=1 TO 2', 'NEXT B,A',
                  'PRINT"[";A;B;"]"']),
    ("m.count",  ['N=0', 'FOR A=1 TO 3', 'FOR B=1 TO 2', 'N=N+1', 'NEXT B,A',
                  'PRINT"[";N;"]"']),
    # --- 3. THE ELEMENTS obey NEXT's own matching rule (or do not) -----------
    ("m.type",   ['FOR A%=1 TO 2', 'FOR B=1 TO 2', 'NEXT B,A%',
                  'PRINT"[";A%;B;"]"']),
    # D-FORVAR n.xtype INSIDE a list: `FOR A%` is not closed by `NEXT ...,A`
    ("m.typex",  ['FOR A%=1 TO 2', 'FOR B=1 TO 2', 'NEXT B,A',
                  'PRINT"[OK]"']),
    ("m.wrong",  ['FOR A=1 TO 2', 'FOR B=1 TO 2', 'NEXT B,C',
                  'PRINT"[OK]"']),
    # a list whose FIRST element closes an inner frame on the way -- the
    # stack-walking compare (nx_miss) reached from INSIDE a list
    ("m.deep",   ['FOR A=1 TO 2', 'FOR B=1 TO 2', 'FOR C=1 TO 2', 'NEXT B,A',
                  'PRINT"[";A;B;C;"]"']),
    # a NEGATIVE step inside a list. The funding carve (spec §6.3) merges the
    # two limit comparisons `nx_have` and `nx_neg` used to hold separately, so
    # the step SIGN needs a row in this battery and not only in forvar's.
    ("m.step",   ['FOR A=3 TO 1 STEP -1', 'FOR B=1 TO 2', 'NEXT B,A',
                  'PRINT"[";A;B;"]"']),
    # --- 4. THE DEGENERATE FORMS --------------------------------------------
    ("m.trail",  ['FOR A=1 TO 2', 'FOR B=1 TO 2', 'NEXT B,',
                  'PRINT"[";A;B;"]"']),
    ("m.trail1", ['FOR B=1 TO 2', 'NEXT B,', 'PRINT"[OK]"']),
    # 🔴 ROUND 2. m.trail REFUTED "a trailing comma is a bare NEXT": with an
    # OUTER frame standing, a bare NEXT would have closed it and the program
    # would have finished, and both references answer NEXT without FOR instead.
    # So a comma DEMANDS a variable -- and these three say what "demands" means,
    # which is a byte: ERR 1 (the element matched nothing) or ERR 2 (the parse
    # refused). `NEXT 1` alone is ERR 2 (n.num), so the two faces are BOTH live
    # here and the asymmetry is exactly what a design has to know.
    ("m.trailnum", ['FOR A=1 TO 2', 'FOR B=1 TO 2', 'NEXT B,1',
                    'PRINT"[OK]"']),
    ("m.trailc", ['FOR A=1 TO 2', 'FOR B=1 TO 2', 'NEXT B,:PRINT"[OK]"']),
    ("m.trail2", ['FOR A=1 TO 2', 'FOR B=1 TO 2', 'NEXT B,A,',
                  'PRINT"[OK]"']),
    ("m.lead",   ['FOR B=1 TO 2', 'NEXT ,B', 'PRINT"[OK]"']),
    ("m.space",  ['FOR A=1 TO 2', 'FOR B=1 TO 2', 'NEXT B , A',
                  'PRINT"[";A;B;"]"']),
    # --- 5. TERMINATION -----------------------------------------------------
    ("m.after",  ['FOR A=1 TO 2', 'FOR B=1 TO 2', 'NEXT B,A:PRINT"[";A;B;"]"']),
    # 🎯 the SAME nesting closed by a `:` instead of a `,`. Green before AND
    # after, and the only row that can tell "the comma re-enters NEXT" from
    # "any separator re-enters NEXT" -- a distinction two cuts would otherwise
    # redden identically ([[draft-the-knives-before-freezing-the-row-set]]).
    ("m.colon",  ['FOR A=1 TO 2', 'FOR B=1 TO 2', 'NEXT B:NEXT A',
                  'PRINT"[";A;B;"]"']),
    # --- 6. NEXT A(1) — unmeasured anywhere -------------------------------
    ("m.ary",    ['FOR A=1 TO 2', 'NEXT A(1)', 'PRINT"[OK]"']),
    # 🎯 DOES THE REFERENCE EVALUATE THE SUBSCRIPT? The cheap fix for m.ary is
    # "a `(` after the name makes the key unmatchable", which raises ERR 1
    # WITHOUT evaluating anything. 99 is outside an auto-DIMmed 0..10, so a
    # reference that runs a full variable-reference parse answers `Subscript out
    # of range` here and the cheap fix would trade one red row for another.
    # This row is what decides whether m.ary is in scope at all.
    ("m.ary9",   ['FOR A=1 TO 2', 'NEXT A(99)', 'PRINT"[OK]"']),
    ("m.aryspc", ['FOR A=1 TO 2', 'NEXT A (1)', 'PRINT"[OK]"']),
    # --- 🔴 the CARVE's own rows: nx_find's empty-stack entry ----------------
    ("n.nofor",  ['NEXT A', 'PRINT"[OK]"']),
    ("n.barenofor", ['NEXT', 'PRINT"[OK]"']),
    # --- the NEGATIVE control -----------------------------------------------
    ("n.num",    ['FOR A=1 TO 2', 'NEXT 1', 'PRINT"[OK]"']),
]
CONTROLS = ("c.for", "c.next", "c.nest")
CONTROL_WANT = {"c.for": " 4 ", "c.next": " 4 ", "c.nest": " 3  3 "}
NEGATIVE = ("n.num",)
LABEL_W = 12

# --- DEFERRED rows: measured, printed, NEVER scored -------------------------
# 🔴 `NEXT A(1)` IS A DIFFERENT RULE, AND `m.ary9` IS THE ROW THAT PRICED THE
# DECLINE. m.ary alone looks like a free ride on this slice: an array element is
# a different variable from the scalar `A`, so it matches no frame, and the
# cheapest way to say that is to make the parsed key unmatchable when a `(`
# follows -- 8 bytes, D-FORVAR's own `n.strnx` trick. `NEXT A(99)` reads
# **Subscript out of range** on both references, so the reference parses a
# COMPLETE variable reference and EVALUATES the subscript before matching
# anything: the cheap fix would trade one red row for another
# ([[a-priced-decline-is-a-claim-about-a-design]]). m.aryspc adds that the `(`
# is not even lexically contiguous.
# The faithful fix is an array-element reference parse in `ex_next` -- the
# D-ARYLV / lvalue family, not the LIST family. Filed in TODO.md with all three
# readings. All three stay MEASURED and PRINTED -- a deferral has to carry its
# evidence -- and are excluded from the tally in BOTH directions, because a
# deferred row that started agreeing would itself be a finding.
DEFERRED = {
    "m.ary":    "DEFERRED — a NEXT operand is a full variable REFERENCE; see "
                "m.ary9",
    "m.ary9":   "DEFERRED — the reference EVALUATES the subscript, so the "
                "8-byte unmatchable-key fix answers the WRONG error",
    "m.aryspc": "DEFERRED — and the `(` is not lexically contiguous either",
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
    # BATCHED (D-BATCH9); `scratchpad/batchcheck.py` found every row identical
    # both ways. Each case's own `cfg["reset"]` is prepended to its lines, and
    # the disk was already shared (TEST_DSK), so nothing about isolation changes
    # except the boot count.
    group = [(l, ln) for l, ln in CASES if not only or l in only]
    if not group:
        return out
    specs = [("direct", list(cfg["reset"])
              + [f"{10 * (k + 1)} {x}" for k, x in enumerate(lines)] + ["RUN"])
             for _l, lines in group]
    caps = omsx_repl.run_cases(
        cfg["machine"], specs,
        batch=True, reset=(), boot=cfg["boot"], step=cfg["step"], **kw)
    for (label, _lines), cap in zip(group, caps):
        out[label] = bracket(cap)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(
        description="D-NXLIST: NEXT takes a LIST of loop variables")
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

    print("D-NXLIST — NEXT takes a LIST of loop variables     "
          f"sides: {', '.join(sides)}")
    print("=" * 78)

    # --- the POSITIVE controls, first and gating ----------------------------
    # ⚠️ A control failure is classified by WHICH SIDE failed it: red on a
    # REFERENCE means the fixture is broken (exit 2, nothing scored); red on
    # zerobas would be an ordinary divergence. All three shapes ship today, so
    # either side going red is the instrument, not the rule
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
              "    c.for  = `FOR I=1 TO 3` / `NEXT`, the bare loop.\n"
              "    c.next = `NEXT I`, the NAMED match -- every subject row is "
              "a named\n"
              "             NEXT, so a red m.two without this row has two "
              "candidate causes.\n"
              "    c.nest = `NEXT B` / `NEXT A` as TWO STATEMENTS, the exact "
              "semantics\n"
              "             the list abbreviates. Red here means a red m.two "
              "is about\n"
              "             NESTING, not about the comma.\n"
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
    print("DENOMINATOR: (LIST LENGTH: 1 / 2 / 3) x (ELEMENT: matching name / "
          "mismatching name / mismatching TYPE / two-char name) x "
          "(DEGENERATE: trailing comma with an outer frame / with none / after "
          "a full list / before a `:` / leading comma / a non-name after the "
          "comma / spaces around the comma), plus the CONTINUES path measured "
          "as an inner-body COUNT, plus a list element that closes inner "
          "frames on its way, plus a NEGATIVE step inside a list, plus "
          "termination by `:` after the list and by a `:` used INSTEAD of the "
          "comma, plus a NEXT with no FOR at all through BOTH of nx_find's and "
          "nx_miss's entries, plus the numeric form both references REFUSE. "
          "NOT covered: `NEXT A(1)` and its subscript evaluation (3 DEFERRED "
          "rows, declined with a price); a `$` element inside a list; a list "
          "spanning a line boundary; a list longer than three")
    if a.gate and dis:
        sys.stderr.write(f"nxlist: {dis} reading(s) diverge\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
