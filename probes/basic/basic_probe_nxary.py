#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""D-NXARY — a `NEXT` operand is a full variable REFERENCE, subscript and all.

D-NXLIST measured three rows and DECLINED the fix with a price
(`docs/spec-basic-nxlist.md` §3.1): `NEXT A(1)` is **NEXT without FOR** and
`NEXT A(99)` is **Subscript out of range** on both references, so the reference
EVALUATES the subscript before matching anything. The 8-byte "a `(` makes the
key unmatchable" fix answers the wrong error on the second row, which is why it
was refused.

🔴 THREE READINGS ARE NOT A RULE, AND THIS ONE IS THE MOST INVITING SHAPE THERE
IS: small, obvious and affordable. Every question below is one a fix has to
answer and none of the three measured rows asks:

  1. 🎯 WHICH ARRAY, AND IN WHICH NAMESPACE. `tgt_parse` takes a MODE (0 numeric
     / 1 string) and `for_name` returns a TYPE CODE (2/4/8, or DEFTBL_STR for a
     `$` name) — two namespaces sharing a cell ([[two-namespaces-sharing-a-value]]).
     `NEXT A$(1)` and `NEXT A%(1)` are what say whether the resolve must be
     told the mode, i.e. whether the fix is one call or a conversion first.
  2. 🎯 DOES THE RESOLVE AUTO-DIM? `ary_op0_resolve` op=0 auto-dims on first
     reference. If the reference does NOT, a fix built on it leaves an array
     behind that no reference program has — a side effect on a row that ERRORS,
     which no screen reading can see. `a.autodim` traps the error and then DIMs,
     so a created array reads `Redimensioned array` and an absent one `[OK]`.
  3. THE SUBSCRIPT SURFACE. Literal / variable / expression, 1-D / 2-D, the
     WRONG rank, in range and out of range, DIMmed and unDIMmed. A resolve that
     is reached at all has to get all of it right, because it is the same
     resolve every other lvalue site uses.
  4. THE ERROR NUMBER, not just its wording — `a.errno` reads `ERR` through
     `ON ERROR`, so "NEXT without FOR" is pinned as ERR 1 rather than as a
     string that happens to match.
  5. COMPOSITION with D-NXLIST: an array element as a LIST element.

🟢 THE THREE POSITIVE CONTROLS ARE LOAD-BEARING, NOT DECORATION.
  * `c.for`   — `FOR I=1 TO 3` / `NEXT`, the bare loop.
  * `c.aryrd` — `DIM A(3)` / `A(1)=7` / `PRINT A(1)`, the array machinery a fix
    REUSES. If this is red, a red `a.dim` is a broken resolve, not a broken NEXT.
  * `c.nofor` — `NEXT B` against a live `FOR A`, the error face the fix has to
    produce. Without it every `NEXT without FOR` row below has two causes
    ([[row-with-two-candidate-causes]]).
  A control failure exits 2 (the instrument broke), never 1 (a regression).

🔴 `f.ary` IS A NEGATIVE CONTROL. `FOR A(1)=1 TO 3` is `Syntax error` on BOTH
references and must STAY so. This slice teaches `ex_next` to resolve a
subscript; the danger is that the same reach lands in `ex_for`, where both
references REFUSE it ([[gate-whose-answer-is-an-error-passes-a-dead-subject]]).

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

# (label, [program body lines]) — numbered 10, 20, 30, ... in order, so any
# ON ERROR GOTO target below is 10 x its 1-based position in this list.
CASES = [
    # --- positive controls ---------------------------------------------------
    ("c.for",     ['FOR I=1 TO 3', 'NEXT', 'PRINT"[";I;"]"']),
    ("c.aryrd",   ['DIM A(3)', 'A(1)=7', 'PRINT"[";A(1);"]"']),
    ("c.nofor",   ['FOR A=1 TO 2', 'NEXT B', 'PRINT"[OK]"']),
    # --- 3. the SUBSCRIPT surface -------------------------------------------
    ("a.lit",     ['FOR A=1 TO 2', 'NEXT A(1)', 'PRINT"[OK]"']),
    ("a.oob",     ['FOR A=1 TO 2', 'NEXT A(99)', 'PRINT"[OK]"']),
    ("a.spc",     ['FOR A=1 TO 2', 'NEXT A (1)', 'PRINT"[OK]"']),
    ("a.dim",     ['DIM A(3)', 'FOR A=1 TO 2', 'NEXT A(1)', 'PRINT"[OK]"']),
    ("a.dimoob",  ['DIM A(3)', 'FOR A=1 TO 2', 'NEXT A(9)', 'PRINT"[OK]"']),
    ("a.var",     ['B=1', 'FOR A=1 TO 2', 'NEXT A(B)', 'PRINT"[OK]"']),
    ("a.expr",    ['FOR A=1 TO 2', 'NEXT A(1+1)', 'PRINT"[OK]"']),
    ("a.2d",      ['DIM A(3,3)', 'FOR A=1 TO 2', 'NEXT A(1,2)', 'PRINT"[OK]"']),
    # the WRONG rank — a resolve that ignores it answers the wrong error
    ("a.rank",    ['DIM A(3,3)', 'FOR A=1 TO 2', 'NEXT A(1)', 'PRINT"[OK]"']),
    # --- 1. 🎯 WHICH ARRAY, AND IN WHICH NAMESPACE --------------------------
    ("a.str",     ['FOR A=1 TO 2', 'NEXT A$(1)', 'PRINT"[OK]"']),
    # 🎯 a.str IS ALREADY GREEN, AND THIS ROW IS WHY THAT PROVES NOTHING.
    # zerobas answers it right for a reason that has nothing to do with arrays:
    # D-FORVAR made a `$` name resolve to DEFTBL_STR, a type no frame can hold,
    # so the key misses and ERR 1 falls out -- WITHOUT the subscript ever being
    # looked at. Put the subscript out of range and the two mechanisms separate.
    # A case that AGREES can agree for the WRONG REASON.
    ("a.stroob",  ['FOR A=1 TO 2', 'NEXT A$(99)', 'PRINT"[OK]"']),
    ("a.pct",     ['FOR A%=1 TO 2', 'NEXT A%(1)', 'PRINT"[OK]"']),
    ("a.pctoob",  ['FOR A%=1 TO 2', 'NEXT A%(99)', 'PRINT"[OK]"']),
    # 🔴 THE ROW A KNIFE DEMANDED. K-NA3 (force tgt_parse's MODE argument to 0,
    # so the resolve is told the TYPE CODE instead) reddened NOTHING: nothing in
    # the battery could tell `A$()` picked by mode 1 from `A$()` picked by type
    # code 3 -- the two namespaces coincide ([[two-namespaces-sharing-a-value]]),
    # and a cut with no row of its own is a missing row, not a bad cut.
    # Here BOTH arrays exist and only ONE of them makes 9 out of range, so the
    # answer names which array the resolve actually reached.
    ("a.strpick", ['DIM A(50)', 'DIM A$(3)', 'FOR A=1 TO 2', 'NEXT A$(9)',
                   'PRINT"[OK]"']),
    # --- 4. the ERROR NUMBER, not the wording -------------------------------
    # line 4 is `40`, which is where ON ERROR sends it.
    ("a.errno",   ['ON ERROR GOTO 40', 'FOR A=1 TO 2', 'NEXT A(1)',
                   'PRINT"[";ERR;"]"']),
    # --- 2. 🎯 DOES THE RESOLVE AUTO-DIM? -----------------------------------
    # A side effect on a row that ERRORS, which no direct reading can see: trap
    # the error, then DIM inside the handler. An array the NEXT created reads
    # `Redimensioned array`; one it did not reads `[OK]`. Line 4 is `40`.
    # 🔴 THE FIRST DRAFT OF THIS ROW MEASURED SOMETHING ELSE AND LOOKED FINE.
    # It disarmed with `ON ERROR GOTO 0` before the DIM -- and in MS-BASIC that
    # statement, executed INSIDE a handler, RE-RAISES the error that entered it.
    # So both references read `NEXT without FOR` and zerobas read `OK`: a clean
    # 3-side reading, a plausible divergence, and an answer to a question nobody
    # asked ([[readout-blind-to-its-own-subject]]). The re-raise divergence it
    # accidentally found is real and is filed separately -- it belongs to the
    # error-handling surface, not to this one.
    ("a.autodim", ['ON ERROR GOTO 40', 'FOR A=1 TO 2', 'NEXT A(1)',
                   'DIM A(3)', 'PRINT"[OK]"']),
    # --- 5. composition with D-NXLIST ---------------------------------------
    ("a.list",    ['FOR A=1 TO 2', 'FOR B=1 TO 2', 'NEXT B,A(1)',
                   'PRINT"[OK]"']),
    # --- 🔴 the CARVE's own row ---------------------------------------------
    # This slice is funded partly by rewriting `ex_for`'s "too many nested FORs"
    # bound test (spec §6.3) -- the SENSE of a comparison, which is exactly the
    # kind of edit that passes every row that never reaches it. 8 nested loops
    # is the deepest the frame stack holds, so this row fails the moment the
    # bound is one frame tight. Green before AND after; it can only catch a
    # carve, never a fix. (D-FORVAR's f.dep8 is the same program in the other
    # battery; the carve is in THIS slice, so the row has to be here too.)
    ("a.dep8",    ['FOR A=1 TO 1', 'FOR B=1 TO 1', 'FOR C=1 TO 1',
                   'FOR D=1 TO 1', 'FOR E=1 TO 1', 'FOR F=1 TO 1',
                   'FOR G=1 TO 1', 'FOR H=1 TO 1', 'NEXT H', 'NEXT G',
                   'NEXT F', 'NEXT E', 'NEXT D', 'NEXT C', 'NEXT B', 'NEXT A',
                   'PRINT"[OK]"']),
    # --- the NEGATIVE control ------------------------------------------------
    ("f.ary",     ['DIM A(3)', 'FOR A(1)=1 TO 3', 'NEXT', 'PRINT"[OK]"']),
]
CONTROLS = ("c.for", "c.aryrd", "c.nofor")
CONTROL_WANT = {"c.for": " 4 ", "c.aryrd": " 7 ",
                "c.nofor": "<NEXT without FOR>"}
NEGATIVE = ("f.ary",)
LABEL_W = 10

# --- DEFERRED: measured, printed, NEVER scored ------------------------------
# ✅ EMPTY SINCE 2026-08-08, AND THAT IS THE DEFERRAL BEING HONOURED RATHER THAN
# FORGOTTEN ([[a-deferral-honoured-is-worth-more-than-one-filed]]).
# 🔴 `a.spc` — `NEXT A (1)`, A SPACE BEFORE THE `(` — sat here because
# `tgt_parse` tested for the subscript with a bare `ld a,(hl)` right after
# `var_name_key`, so its `(` was LEXICALLY CONTIGUOUS: `A (1)` read as the scalar
# `A` and the ` (1)` then reached statement position as Syntax error.
# 💰 THE FIX WAS NEVER BLOCKED ON BYTES (it is +2 B and page 1 had 5). It was
# blocked on EVIDENCE: `tgt_parse` is the lvalue family's SHARED target parse, and
# the change decides what `READ A (1)`, `INPUT A (1)`, `LINE INPUT A$ (1)`,
# `MID$(A$ (1),1,2)=`, `INPUT#1,A$ (1)`, `FIELD..AS A$ (1)` and `LSET A$ (1)=`
# MEAN ([[a-shared-engine-fix-must-measure-its-other-callers]]).
# D-TGTSPC (docs/spec-basic-tgtspc.md) is that slice: 28 rows across all NINE
# statement surfaces on three sides, BOTH references agreeing on every one -- plus
# the row that reads the STORED LINE BYTES to prove the space survives the crunch
# at all, which is what says the fix belongs to the PARSER and not the tokeniser.
# `a.spc` is now an ordinary SCORED row and this battery goes 21/21 -> 22/22.
# 🔴 AND THE FILED CALL-SITE COUNT WAS WRONG. `tgt_parse` has EIGHT `call`
# sites from NINE statement surfaces, not seven: the hand list forgot to count
# `ex_next` itself ([[a-hand-listed-denominator-is-a-scope-claim]]).
DEFERRED = {}

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
    # 🔴 THE SCREEN HAD TEXT AND THE ALPHABET COULD NOT NAME IT (D-CARRYTEXT,
    # 2026-09-02). `ERRORS` is a hand-written list and the ROM can print 30
    # different messages; the sweep in TODO.md ("AN UNNAMED OUTCOME READS AS NO
    # OUTCOME") measured this tree's readouts at a MEDIAN of 5 of those 30, and
    # its thesis is that "add the next name" is provably unbounded. Carrying the
    # text is the BOUNDED fix: a reading nobody modelled stops being reported as
    # `<NO OUTPUT>`, which is a sentence about the MACHINE, and becomes one about
    # this probe. Note this is deliberately NOT a new alphabet entry -- it is the
    # thing that makes the alphabet's incompleteness visible instead of silent.
    # [[an-unnamed-outcome-reads-as-no-outcome]]
    if txt.replace("Ok", "").strip():
        return f"<UNREADABLE: {txt.strip()[:48]}>"
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
        description="D-NXARY: a NEXT operand is a full variable reference")
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

    print("D-NXARY — a NEXT operand is a full variable REFERENCE   "
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
              "    c.for   = `FOR I=1 TO 3` / `NEXT`, the bare loop.\n"
              "    c.aryrd = `DIM A(3)` / `A(1)=7` / `PRINT A(1)`, the array "
              "machinery a fix\n"
              "              REUSES -- red here means a red a.dim is a broken "
              "RESOLVE.\n"
              "    c.nofor = `NEXT B` against a live `FOR A`, the error FACE "
              "the fix must\n"
              "              produce -- without it every NEXT-without-FOR row "
              "has two causes.\n"
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
    print("SIDES: vg8020,cf3300,zb — FOR/NEXT and DIM are core BASIC, present "
          "on every MSX1, so BOTH references are legitimate oracles for every "
          "row here")
    print("DENOMINATOR: (SUBSCRIPT FORM: literal / variable / expression) x "
          "(RANK: 1-D / 2-D / the WRONG rank) x (RANGE: in / out) x (DIMmed / "
          "unDIMmed), plus the TYPE namespace the resolve must be told "
          "(unsuffixed / % / $), plus the ERROR NUMBER read through ON ERROR "
          "rather than its wording, plus whether the resolve AUTO-DIMS (a side "
          "effect on a row that errors, invisible to a direct reading), plus "
          "an array element as a LIST element, plus the `FOR A(1)=` form both "
          "references REFUSE")
    if a.gate and dis:
        sys.stderr.write(f"nxary: {dis} reading(s) diverge\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
