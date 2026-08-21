#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""D-STRPAREN — `(A$)` is refused in EVERY string context, and this is the
denominator that says so.

🔴 THE CLAIM CAME WITH TWO DATA POINTS. D-FNEXPR (docs/spec-basic-fnexpr.md §4)
found `f.paren` -- `OPEN(A$)AS #1` -- was the ONE row of fourteen its filename
fix did not close, correctly refused to charge it to the filename gate, and filed
it as *"`(A$)` is refused in EVERY string context"* on the strength of `B$=(A$)`
and `PRINT (A$)`, measured ad hoc and never committed as rows. That is a rule
claiming more than its evidence [[a-rule-can-claim-more-than-its-evidence]].
This file is the evidence: **eleven contexts, three controls, TWO references** --
and since 2026-08-21 it is also the gate that holds the fix, **14/14 scored, the
DEFERRED dict EMPTY**. What follows described the state it measured; the ✅ notes
say what closed it.

🎯 AND THE ROWS SAY IT IS NOT WHAT THE RESIDUAL NAMED IT. The filing says
"`str_eval_one` has no parenthesised-subexpression case", which is TRUE and is
not the whole mechanism:

  * `p.let`, `p.cat1`, `p.nest`, `p.inner`, `p.lit` reach `str_eval` and would
    close with a `(` case there;
  * `p.print` never reaches it at all -- basic/print.asm's item loop dispatches
    on `"`, on the string-function tokens and on a `$`-suffixed letter, and a
    leading `(` falls through to `exp_num`, i.e. to the NUMERIC evaluator;
  * `p.if` is the same story through `ev_rel`;
  * 🔴 `p.left` answers a DIFFERENT FACE -- `Syntax error`, where all ten others
    answer `Type mismatch` -- so LEFT$'s argument parser refuses the `(` at its
    own site. One rule, at least two mechanisms; the same shape D-FNARG2 found
    when one filename rule turned out to have three.

So this is a SPLIT-EVALUATOR question, not a missing `case` label: zerobas has a
numeric `eval` and a string `str_eval` and decides between them by PEEKING, while
the reference has one type-polymorphic evaluator that returns whatever it found.
A leading `(` is the one operand shape a peek cannot classify.

✅ **FIXED 2026-08-21 in that shape**: `str_eval_paren` (basic/strvar.asm, 23 B)
is written to be TRIED and to leave no trace when it declines -- it restores HL
and returns CF clear on a non-string inside -- and `basic/print.asm`'s item loop
offers it a `(` for 5 B, falling back through the `exps_fallback` it already had.
🔴 **AND §3.4's "one rule, at least TWO mechanisms" WAS REFUTED BY THAT FIX**:
`p.left` closed in the same run as the other nine. Its different FACE came from
what its caller does with a `CF clear` return, not from where the refusal
happens. A face is a claim about the LAST routine to run, not the first to
refuse.

🟢 THREE CONTROLS, AND THEY ARE WHAT MAKE THE ELEVEN A READING. `p.ctl` is the
unparenthesised twin (`B$=A$`), `p.numctl` and `p.numprint` are the NUMERIC
parenthesised forms in the two dispatchers under test. Without them "parentheses
are unsupported" and "strings are unsupported" read the eleven rows just as well,
and those are the two readings this project keeps confusing
([[spokeline-slice]], [[gateblind-slice]]).

⚠️ NO DISK ANYWHERE, so a diskless Philips VG-8020 is a full second reference
here -- unlike the filename battery this grew out of, which rests on the CF-3300
alone. Every row below has TWO references and they agree on all fourteen.

THE READING is the `[...]` span printed BY THE RUN, taken from the screen tail
after `RUN` -- error first, because every divergent row's subject is a FAILURE
and a `[` printed later would otherwise be found first
([[readout-blind-to-its-own-subject]]).

Clean-room: observed screen output only; both reference ROMs are black boxes.
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from probes.lib import omsx_repl, probe_report          # noqa: E402

ZB_MACHINE = "C-BIOS_MSX1_EU_REPACK_DISK"

SIDES = {
    "vg8020": dict(machine="Philips_VG_8020", boot=8.0, step=2.5,
                   reset=("NEW",)),
    "cf3300": dict(machine="National_CF-3300", boot=14.0, step=4.5,
                   reset=("", "SCREEN 0", "NEW")),
    "zb":     dict(machine=ZB_MACHINE, boot=8.0, step=2.5, reset=("NEW",)),
}

# Every case runs on top of this, so `A$` and `A` exist and the ONLY variable
# between a row and its control is the parenthesis.
SETUP = ['A$="Q"', 'A=5']

CASES = [
    # --- reached through str_eval: a `(` case in str_eval_one would close these
    ("p.let",      ['B$=(A$)', 'PRINT"[";B$;"]"']),
    ("p.cat1",     ['B$=(A$)+"Z"', 'PRINT"[";B$;"]"']),
    ("p.cat2",     ['B$="Z"+(A$)', 'PRINT"[";B$;"]"']),
    ("p.nest",     ['B$=((A$))', 'PRINT"[";B$;"]"']),
    ("p.inner",    ['B$=(A$+"Z")', 'PRINT"[";B$;"]"']),
    # 🔴 `p.lit` is the row that says this is not about VARIABLES at all: a
    # parenthesised LITERAL is refused too, so the `(` is the whole subject.
    ("p.lit",      ['B$=("Z")', 'PRINT"[";B$;"]"']),
    # --- reached through a DISPATCHER that peeks, and never sees str_eval
    ("p.print",    ['PRINT"[";(A$);"]"']),
    ("p.if",       ['IF (A$)="Q" THEN PRINT"[Y]" ELSE PRINT"[N]"']),
    # --- reached through a string FUNCTION's own argument parse
    ("p.len",      ['PRINT"[";LEN((A$));"]"']),
    ("p.mid",      ['B$=MID$((A$),1,1)', 'PRINT"[";B$;"]"']),
    # 🔴 THE ONE WITH A DIFFERENT FACE. Keep it next to p.mid: same shape, same
    # kind of function, and they do NOT answer the same thing here.
    ("p.left",     ['PRINT"[";LEFT$((A$),1);"]"']),
    # 🔴 THE ROW THAT PINS THE DECLINE PATH. `str_eval_paren` must RESTORE HL and
    # return CF clear when the inside is not a string, so the caller's numeric
    # fallback sees the cursor it would have had. `p.numprint` exercises that
    # through basic/print.asm, which guards its own cursor and would survive a
    # broken restore; this one goes through `ex_let_str` -> `els_tc_common`,
    # which RE-EVALUATES FROM HL and therefore cannot. Without it the `pop hl`
    # in `sep_decline` is a guard no row can see
    # [[a-shadowed-guard-has-no-knife]].
    ("p.numlet",   ['B$=(A+1)', 'PRINT"[";B$;"]"']),
    # 🔴 ...AND `p.numlet` TURNED OUT NOT TO PIN IT EITHER -- K-SP2 (`pop hl` ->
    # `pop de`) reddened NOTHING with it in the set. It agrees for the WRONG
    # REASON: `els_tc_common` raises `type_mismatch_error` unconditionally once
    # `eval` returns, so a wrong cursor produces the SAME FACE. A row that scores
    # only the face cannot see a cursor.
    # 🎯 THIS ONE SCORES A VALUE INSTEAD. `IF (A+1)=6` must evaluate to TRUE, so
    # the numeric fallback has to re-read the operand from the `(` -- get the
    # cursor wrong and the comparison changes, which the `[Y]`/`[N]` arms show
    # directly rather than through an error.
    ("p.numif",    ['IF (A+1)=6 THEN PRINT"[Y]" ELSE PRINT"[N]"']),

    # --- 🟢 controls
    ("p.ctl",      ['B$=A$', 'PRINT"[";B$;"]"']),
    ("p.numctl",   ['B=(A)', 'PRINT"[";B;"]"']),
    ("p.numprint", ['PRINT"[";(A+1);"]"']),
]

CONTROLS = ("p.ctl", "p.numctl", "p.numprint")
CONTROL_WANT = {"p.ctl": "Q", "p.numctl": " 5 ", "p.numprint": " 6 "}
LABEL_W = 10

SENTINELS = ("<NO CAPTURE>", "<NO OUTPUT>", "<RUN SCROLLED OFF>")

ERRORS = ("Syntax error", "Type mismatch", "Illegal function call",
          "Overflow", "Division by zero", "Out of string space",
          "String too long", "Out of memory", "Missing operand",
          "Subscript out of range", "Redimensioned array", "Out of DATA",
          "NEXT without FOR", "Undefined line number")

# --- DEFERRED: measured, printed, NEVER scored ------------------------------
# ✅ EMPTY, AND EMPTIED BY FIXING THE ROWS RATHER THAN BY RESCORING THEM
# (D-STRPAREN's fix commit, 2026-08-21 -- docs/spec-basic-strparen.md).
# All eleven divergent rows here were DEFERRED for exactly one gate run: a known
# divergence that gates turns a battery red forever instead of measuring
# anything, and the three CONTROLS were gated throughout, which is what made the
# eleven a reading rather than an anecdote. They are ordinary scored rows now
# [[a-deferral-honoured-is-worth-more-than-one-filed]].
DEFERRED: dict[str, str] = {}


def face(raw: str | None) -> str:
    """The ERROR the RUN produced, or the `[...]` span if there was none."""
    if raw is None:
        return "<NO CAPTURE>"
    tail = omsx_repl.screen_tail(raw, "RUN")
    if tail is None:
        return "<RUN SCROLLED OFF>" if str(raw).strip() else "<NO CAPTURE>"
    txt = " ".join(str(tail).split("\n"))
    for e in ERRORS:
        if e in txt:
            return f"<{e}>"
    i, j = txt.find("["), txt.find("]", txt.find("[") + 1)
    if i >= 0 and j > i:
        return txt[i + 1:j]
    return "<NO OUTPUT>"


def run_side(side: str, only: list[str]) -> dict:
    cfg = SIDES[side]
    out = {}
    for label, lines in CASES:
        if only and label not in only:
            continue
        body = [f"{10 * (k + 1)} {ln}" for k, ln in enumerate(SETUP + lines)]
        caps = omsx_repl.run_cases(
            cfg["machine"], [("direct", list(cfg["reset"]) + body + ["RUN"])],
            batch=False, boot=cfg["boot"], step=cfg["step"])
        out[label] = face(caps[0])
    return out


def main() -> int:
    ap = argparse.ArgumentParser(
        description="D-STRPAREN: `(A$)` across every string context")
    ap.add_argument("--sides", default="vg8020,cf3300,zb")
    ap.add_argument("--only", default="")
    ap.add_argument("--gate", action="store_true",
                    help="exit 1 unless every scored row matches its reference")
    a = ap.parse_args()

    sides = [s for s in a.sides.split(",") if s]
    only = [o for o in a.only.split(",") if o]
    for s in sides:
        if s not in SIDES:
            sys.stderr.write(f"unknown side {s!r}\n")
            return 2

    results = {s: run_side(s, only) for s in sides}
    present = [lab for lab, _ in CASES if any(lab in results[s] for s in sides)]

    print("D-STRPAREN — `(A$)` in every string context   "
          f"sides: {', '.join(sides)}")
    print("=" * 78)

    # 🔴 ONLY A REFERENCE CAN SAY THE APPARATUS IS BROKEN. A control that fails
    # on `zb` is a FINDING and is scored below like any other row -- the rule
    # basic_probe_namspc.py carries and castail-acceptance does not
    # ([[classify-a-control-failure-by-which-side-failed-it]]).
    bad = []
    for ctl in CONTROLS:
        if ctl not in present:
            continue
        for s in sides:
            if s == "zb":
                continue
            got = results[s].get(ctl)
            if got is not None and got != CONTROL_WANT[ctl]:
                bad.append((ctl, s, got, CONTROL_WANT[ctl]))
    if bad:
        for lab, s, got, exp in bad:
            print(probe_report.row("FAIL", lab, LABEL_W, {s: got},
                                   "   [POSITIVE CONTROL]"))
            print(f"        wanted {exp!r}")
        print("\n*** A POSITIVE CONTROL FAILED ON A REFERENCE, so nothing was "
              "measured.\n"
              "    Each control is the UNPARENTHESISED (or NUMERIC) form of the "
              "rows beside\n"
              "    it -- the same program with the parenthesis taken out, or "
              "with a number\n"
              "    inside it. A REFERENCE failing that means the fixture is "
              "broken, not that\n"
              "    the rule is wrong. (A control failing on `zb` is NOT this: "
              "that is an\n"
              "    ordinary divergence and IS scored.) Check build/*.rom, `make "
              "repack-machine`\n"
              "    and `make latch-check`, THEN re-read the rows. Exit 2 (not "
              "1) = the\n"
              "    instrument was broken, NOT a regression.")
        for lab in present:
            vals = {s: results[s][lab] for s in sides if lab in results[s]}
            print(probe_report.row("....", lab, LABEL_W, vals, "   (not scored)"))
        print(probe_report.footer(len(bad) + len(present), 0,
                                  "NOT MEASURED (a positive control failed)"))
        return 2

    agree = dis = noref = deferred = 0
    for lab in present:
        vals = {s: results[s][lab] for s in sides if lab in results[s]}
        refs = {s: v for s, v in vals.items()
                if s in ("vg8020", "cf3300") and v not in SENTINELS}
        if lab in DEFERRED:
            deferred += 1
            print(probe_report.row("....", lab, LABEL_W, vals,
                                   f"   [{DEFERRED[lab]}]"))
            continue
        note = "   [POSITIVE CONTROL]" if lab in CONTROLS else ""
        if not refs or "zb" not in vals:
            noref += 1
            print(probe_report.row("....", lab, LABEL_W, vals,
                                   "   [no reference]"))
        elif len(set(refs.values())) > 1:
            dis += 1
            print(probe_report.row("DIFF", lab, LABEL_W, vals,
                                   "   [THE REFERENCES DISAGREE]"))
        elif vals["zb"] == list(refs.values())[0]:
            agree += 1
            print(probe_report.row("ok", lab, LABEL_W, vals, note))
        else:
            dis += 1
            print(probe_report.row("DIFF", lab, LABEL_W, vals, note))

    scored = len(present) - noref - deferred
    print(probe_report.footer(len(present), scored,
                              f"{agree} agree, {dis} diverge, "
                              f"{noref} without a reference, "
                              f"{deferred} deferred (not scored)"))
    print("=" * 78)
    print(f"{agree}/{scored} readings match their reference "
          f"({len(present)} cases, {len(CONTROLS)} positive controls, "
          f"{deferred} DEFERRED row(s) measured but not scored)")
    print("DENOMINATOR: (the CONTEXT the parenthesised string operand stands in: "
          "a LET to a `$` target, a `+` concat on either side, NESTED parens, a "
          "parenthesised EXPRESSION, a parenthesised LITERAL, a PRINT item, an "
          "IF comparison, and the argument of LEN / MID$ / LEFT$) x (what the "
          "context DISPATCHES on: str_eval directly, a peek that never reaches "
          "it, or a function's own argument parse). Every row carries the "
          "unparenthesised or NUMERIC form of its own dispatcher as a control. "
          "NOT COVERED: parenthesised strings in RSET/LSET/FIELD, in a DATA "
          "body, as a filename (that is `f.paren` in basic_probe_namspc.py, the "
          "row this battery grew out of), or nested more than two deep.")
    if a.gate and dis:
        sys.stderr.write(f"strparen: {dis} reading(s) diverge\n")
        return 1
    return 0


sys.exit(main())
