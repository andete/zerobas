#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""D-READVAR follow-up — does `INPUT` take an ARRAY ELEMENT target?

`TODO.md` §"Open — standing residuals" carries D-READVAR's two DEFERRED rows,
`READ A(1)` / `READ A$(1)`, and the item says in as many words that the price
depends on an UNMEASURED question: *does `INPUT A(1)` diverge too?* If it does,
the array-lvalue work is shared between two verbs and is worth more than it looks;
if it does not, the reason is itself a finding. This probe answers it, and nothing
else -- it was a MEASUREMENT, not a gate (§"a row that can only ever be red is doc
debt, not a gate" -- see the Makefile comment on `inputary-characterize`).

✅ IT IS A GATE NOW. D-ARYLV landed the array-lvalue target parse
(docs/spec-basic-arylv.md, 2026-08-08) and all 7 rows agree, so the condition
that blocked the promotion is gone: `make inputary-acceptance` scores 7/7. These
are the only rows in the tree that exercise `INPUT`'s three separate arms against
an array target, and `i.arynodim` is the only row anywhere that scores auto-dim
reached THROUGH a target parse.

WHY THE QUESTION IS NOT ALREADY ANSWERED BY READING THE CODE. It is tempting to
say "both verbs call var_name_key, which never parses a subscript, so both
refuse". That is a prediction from a shared callee, and D-READVAR has a row in its
own record for predicting from the class instead of from the path
([[a-count-is-predicted-by-reading-its-definition]]). It also cannot say what the
REFERENCES do, which is the half that decides whether this is work at all.

THE DENOMINATOR is the cross of (which INPUT arm) x (does the array already
exist), because those are the two things that could differ:

  * the NUMERIC arm and the STRING arm are separate code in basic/input.asm
    (inpc_vloop / inpc_vstr), and `LINE INPUT` is a THIRD arm (inpc_line) that
    re-parses its own target -- so a fix might have to land in three places, and
    the price in the TODO item is written against one.
  * `DIM`med vs not: on an MSX an unDIMmed array auto-dimensions to 10 on first
    reference, so a refusal that survives WITHOUT `DIM` is a refusal in the
    PARSE, not a complaint about a missing array.

🟢 `i.ctl` / `i.strctl` ARE THE POSITIVE CONTROLS, and here they are not a
formality: every row of this battery depends on a typed RESPONSE reaching a
blocked `INPUT`. If the response never arrives the read never completes, nothing
is printed, and all three sides agree on nothing -- the exact shape
`make fat-error-acceptance` once scored 8/8 against an all-$00 disk.rom with.
Their failure exits 2, not 1.

THE READING is the `[...]` span printed BY THE RUN, taken from the screen tail
after `RUN` -- never the whole screen. D-READVAR measured that trap: the echo of
`PRINT"[";A;"]"` contains a `[`, so a whole-screen scan turns "the machine printed
nothing" into `'";A;"'`, an artifact shaped exactly like a reading, on every
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

# (label, [program body lines], [responses injected AFTER `RUN`]). The last body
# line prints the read-back inside `[...]`; only that span is compared.
CASES = [
    # --- the controls: the two arms that already work everywhere -------------
    ("i.ctl",      ['INPUT A', 'PRINT"[";A;"]"'], ["7"]),
    ("i.strctl",   ['INPUT A$', 'PRINT"[";A$;"]"'], ["HI"]),
    ("i.linectl",  ['LINE INPUT A$', 'PRINT"[";A$;"]"'], ["HI"]),
    # --- the question: an ARRAY ELEMENT target, DIMmed ----------------------
    ("i.ary",      ['DIM A(3)', 'INPUT A(1)', 'PRINT"[";A(1);"]"'], ["7"]),
    ("i.arystr",   ['DIM A$(3)', 'INPUT A$(1)', 'PRINT"[";A$(1);"]"'], ["HI"]),
    ("i.lineary",  ['DIM A$(3)', 'LINE INPUT A$(1)', 'PRINT"[";A$(1);"]"'],
     ["HI"]),
    # --- ...and NOT DIMmed: separates a PARSE refusal from a missing array ---
    ("i.arynodim", ['INPUT A(1)', 'PRINT"[";A(1);"]"'], ["7"]),

    # === D-ARYSITE: the ERR-14 message at tss_ary's UNMEASURED call sites ====
    # D-ARYOOS (docs/aryoos-msx1-characterization.md) split `ARY_ERR` so that
    # aeng_copy_str's pool OOM reports `Out of string space` (ERR 14) instead of
    # `Out of memory` (ERR 7), and MEASURED that at ONE of tss_ary's call sites
    # -- console `INPUT` (row s.inpary). It reached the others "by construction",
    # which is a claim, not a reading, and D-CIRCOVF is the standing reminder
    # that a bound stated by construction is owned by whoever deletes the
    # construction.
    #
    # 🔴 AND THE DENOMINATOR IN THE FILED ITEM NAMED A CALLER THAT IS NOT ONE.
    # `tgt_store_str` has FOUR call sites, by grep over basic/ and sub/:
    #   basic/program.asm:1908  READ           -- measured, and NO TEST: a stored
    #                                             DATA literal's descriptor points
    #                                             AT THE PROGRAM TEXT, so the store
    #                                             charges the pool nothing and both
    #                                             references answer `[OK]`
    #   basic/input.asm:138     console INPUT  -- measured (s.inpary)
    #   basic/input.asm:224     console LINE INPUT        <- i.oosline below
    #   basic/files.asm:781     INPUT #n AND LINE INPUT #n, disk AND `CAS:`
    #                                                     <- i.oosfile / i.oosfline
    # docs/aryoos-msx1-characterization.md §2.3 calls the fifth one "the FIELD
    # read". THERE IS NO FIELD CALLER: basic/field.asm reaches `tgt_parse_fld` ->
    # `tgt_parse` and never `tgt_store_str`, because FIELD BINDS a descriptor
    # into the record buffer -- it runs no heap_alloc, so the OOM this class is
    # about cannot happen there at all. basic/vars.asm's own "these FIVE store
    # paths" is right when it counts VERBS (READ / INPUT / LINE INPUT / INPUT#n /
    # LINE INPUT#n); the doc turned the fifth VERB into a fifth SITE.
    #
    # THE FIXTURE, from D-ARYOOS §2.4's measured pool arithmetic: `CLEAR 60`,
    # then a 25-char `B$` and a 25-char `A$(1)` leave TEN bytes of pool. Any
    # store of more than ten characters into `A$(2)` must fail, and the
    # discriminator is WHICH MESSAGE -- both errors abort the RUN, so a row
    # scored error-vs-no-error is green under the defect this measures.
    #
    # 🎯 THE FILE ROWS WRITE NOTHING. `HI.TXT` on disk/test720.dsk is
    # `Hello from zerobas-disk!` + CRLF -- a 24-character line, which is over the
    # ten-byte headroom and under the 25 the console rows type. So no row here
    # needs a private disk copy, and none can perturb another on `--repeat 2`.
    ("i.oosline",     ['CLEAR 60', 'DIM A$(5)', 'B$=STRING$(25,"A")',
                       'A$(1)=B$', 'LINE INPUT A$(2)', 'PRINT"[OK]"'],
     ["AAAAAAAAAAAAAAAAAAAAAAAAA"]),
    # the SCALAR twin: the already-correct path (str_set_key, not the array
    # engine). If this one does NOT report, the FIXTURE is wrong and the array
    # row above is evidence about nothing.
    ("i.ooslinescal", ['CLEAR 60', 'B$=STRING$(25,"A")', 'C$=B$',
                       'LINE INPUT D$', 'PRINT"[OK]"'],
     ["AAAAAAAAAAAAAAAAAAAAAAAAA"]),
    ("i.oosfile",     ['CLEAR 60', 'DIM A$(5)', 'B$=STRING$(25,"A")',
                       'A$(1)=B$', 'OPEN"HI.TXT"FOR INPUT AS #1',
                       'INPUT#1,A$(2)', 'PRINT"[OK]"'], []),
    ("i.oosfilescal", ['CLEAR 60', 'B$=STRING$(25,"A")', 'C$=B$',
                       'OPEN"HI.TXT"FOR INPUT AS #1', 'INPUT#1,D$',
                       'PRINT"[OK]"'], []),
    ("i.oosfline",    ['CLEAR 60', 'DIM A$(5)', 'B$=STRING$(25,"A")',
                       'A$(1)=B$', 'OPEN"HI.TXT"FOR INPUT AS #1',
                       'LINE INPUT#1,A$(2)', 'PRINT"[OK]"'], []),
    # 🟢 THE TWO FIT CONTROLS. Every row above expects an ERROR, and a machine
    # that cannot read a line at all produces one for free
    # ([[gate-whose-answer-is-an-error-passes-a-dead-subject]]). These are the
    # same programs with a pool that FITS: they must come back with the stored
    # LENGTH, which is positive evidence that the verb reached the store.
    ("i.ooslinefit",  ['CLEAR 200', 'DIM A$(5)', 'LINE INPUT A$(2)',
                       'PRINT"[";LEN(A$(2));"]"'],
     ["AAAAAAAAAAAAAAAAAAAAAAAAA"]),
    ("i.oosfilefit",  ['CLEAR 200', 'DIM A$(5)', 'OPEN"HI.TXT"FOR INPUT AS #1',
                       'LINE INPUT#1,A$(2)', 'PRINT"[";LEN(A$(2));"]"'], []),
]

# The `i.oos*file*` rows need a disk interface. A diskless VG-8020 answers
# `Syntax error` to `OPEN`, which would measure the absence of hardware rather
# than a language rule, so it records `<NO DISK ON THIS SIDE>` -- never a
# reading, never an agreement. Same disposition as basic_probe_namspc.py.
NEEDS_DISK = ("i.oosfile", "i.oosfilescal", "i.oosfline", "i.oosfilefit")
NO_DISK_SIDES = ("vg8020",)

CONTROLS = ("i.ctl", "i.strctl", "i.linectl")
CONTROL_WANT = {"i.ctl": " 7 ", "i.strctl": "HI", "i.linectl": "HI"}
LABEL_W = 14

# A row that answers one of these is NEVER agreement, however many sides answer
# it -- two machines that both failed to print agree perfectly about nothing.
SENTINELS = ("<NO CAPTURE>", "<NO OUTPUT>")

# 🔴 NOT A SENTINEL AND NOT A READING. A sentinel means the apparatus failed and
# poisons the row; this means the QUESTION cannot be put to that machine. It is
# PRINTED (so the run states what it did not measure) and dropped from the
# agreement, and a row left with fewer than two answering sides scores as a
# divergence rather than as agreement-with-itself.
NO_DISK = "<NO DISK ON THIS SIDE>"

# ⚠️ ADDING A NAME HERE CAN CHANGE A SHIPPED ROW'S READING, so the full gate is
# re-run whenever this tuple grows -- never `ONLY=` the new rows (the D-FNARG2
# trap, basic_probe_namspc.py). `Out of string space` and `Out of memory` are the
# D-ARYSITE discriminator and both must be nameable: whichever one is missing
# reads as `<NO OUTPUT>`, and a silence is what a diverging pair agrees on.
ERRORS = ("Syntax error", "Type mismatch", "Subscript out of range",
          "Redimensioned array", "Illegal function call",
          "Out of string space", "Out of memory",
          "Overflow", "Bad file number", "File not found")


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
    for label, lines, responses in CASES:
        if only and label not in only:
            continue
        if label in NEEDS_DISK and side in NO_DISK_SIDES:
            out[label] = NO_DISK
            continue
        body = [f"{10 * (k + 1)} {ln}" for k, ln in enumerate(lines)]
        caps = omsx_repl.run_cases(
            cfg["machine"],
            [("direct", list(cfg["reset"]) + body + ["RUN"] + list(responses))],
            batch=False, reset=(), boot=cfg["boot"], step=cfg["step"], **kw)
        out[label] = bracket(caps[0])
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="D-READVAR follow-up: INPUT A(1)")
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

    print("D-READVAR follow-up — does INPUT take an ARRAY ELEMENT target?   "
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
            print(f"        wanted {CONTROL_WANT[lab]!r} -- a scalar target is "
                  "the INPUT shape every side already handles")
        print("\n*** A POSITIVE CONTROL FAILED, so nothing below it was "
              "measured.\n"
              "    EVERY row here needs a typed RESPONSE to reach a blocked "
              "INPUT. If the\n"
              "    response never arrives the read never completes, nothing is "
              "printed, and\n"
              "    all three sides agree on NOTHING. Check build/*.rom, `make "
              "repack-machine`\n"
              "    and the injector (`make latch-check`), THEN re-read the "
              "rows. Exit 2 (not\n"
              "    1) = the instrument was broken, NOT a regression.")
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
    refsplit = 0
    for lab in present:
        vals = {s: results[s][lab] for s in sides if lab in results[s]}
        scored = {s: v for s, v in vals.items() if v != NO_DISK}
        ok = len(set(scored.values())) == 1 and len(scored) > 1
        if any(v in SENTINELS for v in scored.values()):
            ok = False              # an apparatus sentinel is NEVER agreement
        agree += ok
        dis += not ok
        note = "   [POSITIVE CONTROL]" if lab in CONTROLS else ""
        if lab in NEEDS_DISK:
            note += "   [DISK ROW — two-sided by construction]"
        refs = {scored[s] for s in ("vg8020", "cf3300") if s in scored}
        if len(refs) > 1:
            refsplit += 1
            note += "   [REFERENCES DISAGREE — no oracle for this row]"
        print(probe_report.row("ok" if ok else "DIFF", lab, LABEL_W, vals, note))

    print(probe_report.footer(len(present), len(present),
                              f"{agree} agree, {dis} diverge"))
    print("=" * 78)
    print(f"{agree}/{agree + dis} readings agree "
          f"({len(CASES)} cases, {len(CONTROLS)} positive controls, "
          f"{refsplit} row(s) with no oracle)")
    print("SIDES: vg8020,cf3300,zb — console INPUT is core BASIC, present on "
          "every MSX1, so both references are legitimate oracles here. The four "
          f"{NO_DISK} rows ({', '.join(NEEDS_DISK)}) are TWO-sided by "
          "construction: a diskless VG-8020 answers `Syntax error` to OPEN, "
          "which measures the absence of hardware, not a language rule")
    print("DENOMINATOR: (INPUT arm: numeric / string / LINE INPUT) x (the array "
          "DIMmed or auto-dimensioned) — the three arms are separate code in "
          "basic/input.asm, and the unDIMmed row separates a PARSE refusal from "
          "a complaint about a missing array")
    print("DENOMINATOR, D-ARYSITE half: tgt_store_str's FOUR call sites, by "
          "grep — READ (basic/program.asm, measured NO TEST), console INPUT "
          "(basic/input.asm:138, measured by D-ARYOOS), console LINE INPUT "
          "(basic/input.asm:224), and INPUT#n + LINE INPUT#n sharing "
          "basic/files.asm:781. FIELD is NOT one: it binds a descriptor into "
          "the record buffer and never calls tgt_store_str, so the pool OOM "
          "this measures cannot happen there")
    if a.gate and dis:
        sys.stderr.write(f"inputary: {dis} reading(s) diverge\n")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
