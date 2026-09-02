#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""D-LRVAR — `LSET` / `RSET` on a NON-FIELDed variable.

docs/spec-basic-lrvar.md. The last open row-pair of the lvalue/FIELD surface:
docs/lvsites-msx1-characterization.md reads 8/10 and `s.ctl` / `s.ary` are the
only two rows still red. `lrset_notfld` (basic/field.asm) is a bare
`jp stmt_error` commented "LSET/RSET on a non-fielded var (slice-1 limit)" -- a
KNOWN limit, measured for the first time 2026-08-08 and never characterised
beyond the single reading `LSET A$="HI"` on `A$="XXXXX"` reads `HI   `.

🔴 ONE DATA POINT IS NOT A RULE, AND THIS PROBE EXISTS TO SAY WHAT THE RULE IS.
`HI   ` on a 5-char target is consistent with at least three different
implementations: "left-justify into the target's CURRENT length", "left-justify
and pad to 5 because the source was shorter", and "assign, then pad to the old
length". They diverge on a target that is UNSET, on a target that is EMPTY, on a
source LONGER than the target, on whether LEN() changes, and on RSET's
direction over all of the above -- and each of those is a row here whose
REFERENCE COLUMN IS THE PREDICTION. Nothing about the store was implemented from
the inferred rule.

🔴 EVERY ROW HAS **ONE** REFERENCE. `LSET`/`RSET` are Disk BASIC words: the
Philips VG-8020 has no disk controller, answers `Syntax error` to both, and
CANNOT EXPRESS THE QUESTION -- recording its answer would manufacture an
agreement out of an absent drive. Every row rests on the National CF-3300 alone
(NO_DISK_SIDES, the same disposition basic_probe_lvsites.py, basic_probe_lvfix.py
and basic_probe_fldary.py carry). Weaker than anything D-ARYLV rested on, not
upgraded anywhere here, and every row prints its reference count.

⚠️ A SITE WITH TWO ARMS NEEDS A CONTROL PER ARM, and this site has three things
to scope, so it has three controls (docs/lvsites-msx1-characterization.md §3):

  n.fldctl  the FIELDed arm -- a FIELDed scalar LSET, which works today. It is
            what says a red non-FIELDed row is about the MISSING arm and not
            about LSET being broken outright.
  n.ctl     the non-FIELDed arm itself. 🔴 RED ON ZEROBAS BEFORE THIS SLICE, and
            that is a FINDING, not a broken fixture -- see the classification
            rule below.
  e.ctl     the ERASE pair's own arm: the same FIELD-on-an-element program
            WITHOUT the ERASE. Without it a red `e.erase` has two candidate
            causes ([[row-with-two-candidate-causes]]).

🔴 A CONTROL FAILING ON A REFERENCE AND ON ZEROBAS ARE DIFFERENT EVENTS
([[classify-a-control-failure-by-which-side-failed-it]]):

  * control fails on the CF-3300 -> the fixture is broken (a disk that did not
    mount, a channel that never opened RANDOM). Exit 2, score nothing. Only a
    reference can tell you the apparatus is wrong, because only it is supposed to
    be right.
  * control fails on ZEROBAS     -> an ordinary divergence, scored like any other
    row, which additionally SCOPES ITS OWN ARM.

🎯 `n.fld2`, `n.mix` AND `n.arysep` EXIST BECAUSE THE KNIVES WERE DRAFTED FIRST
([[draft-the-knives-before-freezing-the-row-set]]). Asking "which row moves?" of
each planned cut answered NONE for three of them:

  * the store's destination stops being an implicit `FSECTOR_BUF + offset` and
    becomes an explicit address, so the FIELDed arm now computes what the tenant
    used to. With a SINGLE field at offset 0 a destination that dropped the
    offset entirely still reads correctly -- `n.fld2` is two fields of DIFFERENT
    widths, so the second one's offset is visible.
  * the arm is chosen on FLD_CHAN, so a discriminator that always answered
    "fielded" or always "not" needs a program holding BOTH kinds at once to show
    it -- `n.mix` FIELDs A$ and leaves B$ plain, in one program.
  * an element target resolves through its ARYTAB-relative offset, and with one
    element in play a resolve that always returned the same slot still agrees
    with itself -- `n.arysep` writes A$(2) and reads BOTH elements back.

⚠️ `RSET` IS NOT A SECOND PARSE SITE. `ex_lset` and `ex_rset` both fall into
`lrset_common`, so the `r.*` rows measure the STORE's justify direction over the
new arm, not a second parse. Said here rather than implied by a row count.

⚠️ EACH ROW GETS A FRESH COPY OF THE TEST IMAGE -- several rows OPEN and FIELD a
random-access file, so a shared image would let one row's record buffer decide
another's reading ([[test-disk-mutation-gotcha]]).

Clean-room: observed screen output only; the reference ROM is a black box.
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

SIDES = {
    "vg8020": dict(machine="Philips_VG_8020", boot=8.0, step=2.5,
                   reset=("NEW",), diska=False),
    "cf3300": dict(machine="National_CF-3300", boot=14.0, step=4.5,
                   reset=("", "SCREEN 0", "NEW"), diska=True),
    "zb":     dict(machine=ZB_MACHINE, boot=8.0, step=2.5,
                   reset=("NEW",), diska=True),
}
NO_DISK_SIDES = ("vg8020",)

OPEN = 'OPEN"LR.DAT"AS #1'          # no FOR clause => RANDOM, which FIELD needs

# (label, needs_disk, [program lines])
CASES = [
    # === the FIELDed arm — it must not move, and one row of it is new ========
    ("n.fldctl",  True, [OPEN, 'FIELD#1,10 AS A$', 'LSET A$="HI"',
                         'PRINT"[";A$;"]"']),
    # 🎯 K-LV2's row: two fields of DIFFERENT widths, so the SECOND one's byte
    # offset into the record buffer is visible in what it reads back. This is the
    # row a destination that forgot the offset fails, and nothing else asks.
    ("n.fld2",    True, [OPEN, 'FIELD#1,4 AS A$,6 AS B$', 'LSET A$="AA"',
                         'LSET B$="BB"', 'PRINT"[";B$;"]"']),
    # D-FLDARY's own row, carried as a regression check on the arm it landed.
    ("n.fldary",  True, ['DIM A$(3)', OPEN, 'FIELD#1,10 AS A$(1)',
                         'LSET A$(1)="HI"', 'PRINT"[";A$(1);"]"']),
    # === the non-FIELDed arm, SCALAR — the rule itself ======================
    ("n.ctl",     True, ['A$="XXXXX"', 'LSET A$="HI"', 'PRINT"[";A$;"]"']),
    # Does the target's LENGTH change? A "left-justify in place" rule and an
    # "assign then pad" rule are indistinguishable in n.ctl and differ here.
    ("n.len",     True, ['A$="XXXXX"', 'LSET A$="HI"', 'PRINT"[";LEN(A$);"]"']),
    ("n.exact",   True, ['A$="XX"', 'LSET A$="HI"', 'PRINT"[";A$;"]"']),
    # A source LONGER than the target: does it grow, truncate, or error -- and
    # from WHICH end does a truncation take its bytes?
    ("n.long",    True, ['A$="AB"', 'LSET A$="HELLO"', 'PRINT"[";A$;"]"']),
    # A target that was NEVER assigned. Nothing in the one filed reading says
    # whether this is a no-op, an assignment, or an error.
    ("n.unset",   True, ['LSET A$="HI"', 'PRINT"[";A$;"|";LEN(A$);"]"']),
    ("n.empty",   True, ['A$=""', 'LSET A$="HI"',
                         'PRINT"[";A$;"|";LEN(A$);"]"']),
    # 🎯 IDENTITY: a FIELDed variable and a plain one, LSET in ONE program. This
    # is the row that says the two arms are chosen PER TARGET and not per
    # program state -- a discriminator stuck either way reads wrong here.
    ("n.mix",     True, [OPEN, 'FIELD#1,10 AS A$', 'B$="XXXXX"',
                         'LSET A$="HI"', 'LSET B$="LO"',
                         'PRINT"[";A$;"|";B$;"]"']),
    ("r.ctl",     True, ['A$="XXXXX"', 'RSET A$="HI"', 'PRINT"[";A$;"]"']),
    ("r.long",    True, ['A$="AB"', 'RSET A$="HELLO"', 'PRINT"[";A$;"]"']),
    # === the non-FIELDed arm, ARRAY ELEMENT =================================
    ("n.ary",     True, ['DIM A$(3)', 'A$(1)="XXXXX"', 'LSET A$(1)="HI"',
                         'PRINT"[";A$(1);"]"']),
    ("n.aryvar",  True, ['DIM A$(3)', 'I=1', 'A$(I)="XXXXX"',
                         'LSET A$(I)="HI"', 'PRINT"[";A$(1);"]"']),
    ("n.ary2d",   True, ['DIM A$(2,2)', 'A$(1,1)="XXXXX"',
                         'LSET A$(1,1)="HI"', 'PRINT"[";A$(1,1);"]"']),
    # 🎯 IDENTITY: two elements of one array must stay APART. A resolve that
    # always lands on the same slot agrees with itself when only one element is
    # in play; this row writes A$(2) and reads BOTH back.
    ("n.arysep",  True, ['DIM A$(3)', 'A$(1)="XXXXX"', 'A$(2)="YYYYY"',
                         'LSET A$(2)="HI"', 'PRINT"[";A$(1);"|";A$(2);"]"']),
    # The ERROR face of the element target on the non-FIELDed arm.
    ("n.aryoor",  True, ['DIM A$(3)', 'A$(1)="XXXXX"', 'LSET A$(9)="HI"']),
    ("r.ary",     True, ['DIM A$(3)', 'A$(1)="XXXXX"', 'RSET A$(1)="HI"',
                         'PRINT"[";A$(1);"]"']),
    # === grammar: a NUMERIC target is not a string variable ==================
    ("n.num",     True, ['A=1', 'LSET A=2']),
    # === grammar: the RHS DECLINE has TWO causes (D-LSETTM) =================
    # 🔴 THESE SIX ARE MARKED disk-ONLY ON PURPOSE, and D-LSETREF is why. The
    # cassette VG-8020 raises ERR 5 for every LSET row -- not a third opinion
    # about the RHS but a refusal of the whole verb -- and scoring against it
    # would file a Type-mismatch question as a three-way disagreement. The
    # National CF-3000 (cassette) runs a main BASIC ROM BYTE-IDENTICAL to the
    # CF-3300's (sha1 c7a2c5ba...) and also answers ERR 5, so the split is the
    # DISK ROM, not a firmware revision: the CF-3300 is the oracle here and the
    # cassette machines have no vote. docs/spec-basic-lsetref.md.
    # `str_eval` declines both for "the slot is EMPTY" and for "something is
    # here and it is not a string"; the CF-3300 answers 24 and 13.
    ("d.miss",    True, ['A$="12345"', 'LSET A$=']),
    ("d.misscol", True, ['A$="12345"', 'LSET A$=:PRINT']),
    ("d.rmiss",   True, ['A$="12345"', 'RSET A$=']),
    ("d.num",     True, ['A$="12345"', 'LSET A$=5']),
    ("d.rnum",    True, ['A$="12345"', 'RSET A$=5']),
    ("d.numvar",  True, ['A$="12345"', 'N=5', 'LSET A$=N']),
    # === the ERASE oracle D-FLDARY declined to take (spec §5.4) =============
    # An element's field key is its ARYTAB-relative offset, and aeng_erase
    # COMPACTS the descriptor list -- so a key above the erased array is stale.
    # D-FLDARY priced the sweep (~20 B page 1 + 3 B LOW) and declined it FOR WANT
    # OF AN ORACLE: whether the reference drops, keeps or dangles the field
    # across ERASE was never measured. These two rows are that measurement.
    ("e.ctl",     True, ['DIM A$(3),B$(3)', OPEN, 'FIELD#1,10 AS B$(1)',
                         'LSET B$(1)="HI"', 'PRINT"[";B$(1);"]"']),
    ("e.erase",   True, ['DIM A$(3),B$(3)', OPEN, 'FIELD#1,10 AS B$(1)',
                         'ERASE A$', 'LSET B$(1)="HI"',
                         'PRINT"[";B$(1);"]"']),
]

# One per ARM (see the docstring): the FIELDed arm, the non-FIELDed arm, and the
# ERASE pair's own arm.
CONTROLS = ("n.fldctl", "n.ctl", "e.ctl")
CONTROL_WANT = {"n.fldctl": "HI        ", "n.ctl": "HI   ",
                "e.ctl": "HI        "}
# Which control scopes which row -- PER ARM, not per site.
SITE_CONTROL = {
    "n.fld2": "n.fldctl", "n.fldary": "n.fldctl",
    "n.len": "n.ctl", "n.exact": "n.ctl", "n.long": "n.ctl",
    "n.unset": "n.ctl", "n.empty": "n.ctl", "n.mix": "n.ctl",
    "r.ctl": "n.ctl", "r.long": "n.ctl",
    "n.ary": "n.ctl", "n.aryvar": "n.ctl", "n.ary2d": "n.ctl",
    "n.arysep": "n.ctl", "n.aryoor": "n.ctl", "r.ary": "n.ctl",
    "e.erase": "e.ctl",
}

LABEL_W = 10
SENTINELS = ("<NO CAPTURE>", "<NO OUTPUT>", "<NO DISK ON THIS SIDE>")

# 🔴 THIS LIST IS AN ALPHABET, AND A CLOSED ALPHABET IS A BLIND SPOT. D-LSETTM
# added three rows whose answer is `Missing operand` (ERR 24) -- absent here --
# and all three read `<NO OUTPUT>` and were reported as "without a reference"
# while BOTH machines had printed a perfectly good message. The old list was
# ALSO wrong for a message it did name: it said `Field overflow` where the ROM
# says `FIELD overflow` (sub/errmsg.asm), so that row would have dropped the
# same way had anything ever provoked it. Both faults are the same fault --
# a hand-maintained alphabet drifting from sub/errmsg.asm + main's err_msgtab.
# Re-derived from those tables 2026-09-02. The `bracket()` fallback below is
# what stops the NEXT omission from being silent.
# [[a-coverage-row-whose-geometry-cannot-reach-the-case]]
ERRORS = ("Syntax error", "Type mismatch", "Subscript out of range",
          "Illegal function call", "Out of memory", "Out of string space",
          "Overflow", "Bad file number", "File not found", "FIELD overflow",
          "Bad file name", "Disk offline", "File already open",
          "Bad file mode", "Redimensioned array",
          "Missing operand", "Division by zero", "NEXT without FOR",
          "RETURN without GOSUB", "Out of DATA", "Undefined line number",
          "Undefined user function", "String too long", "Can't CONTINUE",
          "RESUME without error", "Illegal direct", "Internal error",
          "Device I/O error", "Direct statement in file", "Input past end",
          "Bad drive name", "Bad sector number", "Bad FAT", "File not OPEN",
          "File still open", "Sequential I/O only", "Unprintable error")


def bracket(raw: str | None) -> str:
    """The `[...]` span the RUN printed, or a sentinel naming what came instead."""
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
    # 🔴 THE SCREEN HAD TEXT AND THE ALPHABET COULD NOT NAME IT. That is a fault
    # in THIS PROBE, not a missing reading, and it must not wear `<NO OUTPUT>`'s
    # clothes -- that sentinel routes the row to "without a reference", which is
    # a sentence about the MACHINE and reads as "nothing to see". Carry the text
    # so the next reader can classify it in one glance rather than re-running.
    if txt.replace("Ok", "").strip():
        return f"<UNREADABLE: {txt.strip()[:48]}>"
    return "<NO OUTPUT>"


def run_side(side: str, only: list[str]) -> dict:
    cfg = SIDES[side]
    out = {}
    for label, needs_disk, lines in CASES:
        if only and label not in only:
            continue
        if needs_disk and side in NO_DISK_SIDES:
            # NOT a reading: a diskless machine cannot express the question.
            out[label] = "<NO DISK ON THIS SIDE>"
            continue
        kw = {}
        if cfg["diska"]:
            dsk = probe_tmp.tmp(f"zb_lrvar_{side}_{label}.dsk")
            shutil.copy(TEST_DSK, dsk)
            kw["diska"] = dsk
        body = [f"{10 * (k + 1)} {ln}" for k, ln in enumerate(lines)]
        caps = omsx_repl.run_cases(
            cfg["machine"], [("direct", list(cfg["reset"]) + body + ["RUN"])],
            batch=False, reset=(), boot=cfg["boot"], step=cfg["step"], **kw)
        out[label] = bracket(caps[0])
    return out


def main() -> int:
    ap = argparse.ArgumentParser(
        description="D-LRVAR: LSET / RSET on a NON-FIELDed variable")
    ap.add_argument("--sides", default="cf3300,zb")
    ap.add_argument("--only", default="")
    ap.add_argument("--gate", action="store_true",
                    help="exit 1 unless every scored row agrees with its oracle")
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

    print("D-LRVAR — LSET / RSET on a NON-FIELDed variable   "
          f"sides: {', '.join(sides)}")
    print("=" * 78)

    # 🔴 ONLY A REFERENCE CAN SAY THE APPARATUS IS BROKEN (see the docstring).
    bad = []
    for ctl in CONTROLS:
        if ctl not in present:
            continue
        for s in sides:
            if s == "zb":
                continue                # a zerobas miss is a RESULT, not a break
            got = results[s].get(ctl)
            if got in (None, "<NO DISK ON THIS SIDE>"):
                continue                # not a reading, not a failure
            if got != CONTROL_WANT[ctl]:
                bad.append((ctl, s, got))
    if bad:
        for lab, s, got in bad:
            print(probe_report.row("FAIL", lab, LABEL_W, {s: got},
                                   "   [POSITIVE CONTROL]"))
            print(f"        wanted {CONTROL_WANT[lab]!r}")
        print("\n*** A POSITIVE CONTROL FAILED ON A REFERENCE, so nothing was "
              "measured.\n"
              "    Each control is its own ARM's statement on the same fixture. "
              "A REFERENCE\n"
              "    failing it means the fixture is broken -- a disk that did not "
              "mount, a\n"
              "    channel that never opened RANDOM.\n"
              "    (A control failing on `zb` is NOT this: that is an ordinary "
              "divergence and\n"
              "    is scored, because only a reference is supposed to be right.)"
              " Exit 2 (not 1)\n"
              "    = the instrument was broken, NOT a regression.")
        for lab in present:
            vals = {s: results[s][lab] for s in sides if lab in results[s]}
            print(probe_report.row("....", lab, LABEL_W, vals,
                                   "   (not scored)"))
        print(probe_report.footer(len(bad) + len(present), 0,
                                  "NOT MEASURED (a positive control failed)"))
        return 2

    def ctl_red_on_zb(ctl: str) -> bool:
        got = results.get("zb", {}).get(ctl)
        return (got not in (None, "<NO DISK ON THIS SIDE>")
                and got != CONTROL_WANT.get(ctl))

    agree = dis = noref = onlyone = 0
    for lab in present:
        vals = {s: results[s][lab] for s in sides if lab in results[s]}
        refs = {s: v for s, v in vals.items()
                if s in ("vg8020", "cf3300") and v not in SENTINELS}
        note = "   [POSITIVE CONTROL]" if lab in CONTROLS else ""
        own = SITE_CONTROL.get(lab)
        if own and own in present and ctl_red_on_zb(own):
            note += ("   [ITS OWN ARM'S CONTROL IS RED ON zb — this row is NOT "
                     "evidence about the TARGET FORM]")
        # An UNREADABLE face is a PROBE failure. It is deliberately not a
        # sentinel: a sentinel would be excluded from `refs` and the row would
        # print as "no reference", which is exactly the silent drop D-LSETTM
        # found. Red, loud, and carrying the screen.
        unread = [s_ for s_, v in vals.items() if v.startswith("<UNREADABLE")]
        if unread:
            dis += 1
            print(probe_report.row("DIFF", lab, LABEL_W, vals,
                                   "   [PROBE CANNOT READ THIS SCREEN on "
                                   + ",".join(unread)
                                   + " — ERRORS does not name what the machine "
                                     "printed; this row scored NOTHING]"))
            continue
        if not refs:
            noref += 1
            print(probe_report.row("....", lab, LABEL_W, vals,
                                   "   [NO REFERENCE ON ANY REQUESTED SIDE]"))
            continue
        if len(set(refs.values())) > 1:
            dis += 1
            print(probe_report.row("DIFF", lab, LABEL_W, vals,
                                   note + "   [REFERENCES DISAGREE — no oracle]"))
            continue
        if len(refs) == 1:
            onlyone += 1
            note += f"   [ONE REFERENCE ONLY ({list(refs)[0]})]"
        oracle = list(refs.values())[0]
        zb = vals.get("zb")
        ok = zb == oracle and zb not in SENTINELS
        agree += ok
        dis += not ok
        print(probe_report.row("ok" if ok else "DIFF", lab, LABEL_W, vals, note))

    print(probe_report.footer(len(present), len(present) - noref,
                              f"{agree} agree, {dis} diverge, "
                              f"{noref} without a reference"))
    print("=" * 78)
    print(f"{agree}/{agree + dis} readings match their reference "
          f"({len(CASES)} cases, {len(CONTROLS)} positive controls — one per "
          f"ARM, {onlyone} row(s) with ONE reference only)")
    print("🔴 ORACLE STRENGTH: EVERY row here has ONE reference. LSET / RSET are "
          "Disk BASIC, which a diskless VG-8020 cannot express — so the whole "
          "table rests on the National CF-3300 alone, a weaker claim than every "
          "row D-ARYLV rested on. Not upgraded anywhere.")
    print("DENOMINATOR: (VERB: LSET / RSET) x (TARGET FORM: scalar / array "
          "element) x (SOURCE vs TARGET LENGTH: shorter / equal / longer), plus "
          "the two degenerate target STATES a single reading cannot separate "
          "(never assigned / assigned empty), plus whether LEN() moves, plus the "
          "subscript FORM (literal / variable) and RANK (1-D / 2-D), plus the "
          "out-of-range and numeric-target ERROR faces, plus the three IDENTITY "
          "rows the knives forced (two fields of different widths, a FIELDed and "
          "a plain target in one program, two elements of one array), plus one "
          "positive control PER ARM, plus the ERASE pair.")
    print("NOT COVERED, named rather than implied: `RSET` as a distinct PARSE "
          "site (it shares lrset_common); a target that is its own source "
          "(LSET A$=A$ — the store space-fills the destination BEFORE reading "
          "the source, so an alias is destroyed, and the reference's answer is "
          "not measured); a subscript that is itself an array element; LSET into "
          "a target whose body a string GC moves DURING the RHS (unreachable — "
          "no program either reference accepts allocates a scalar mid-statement, "
          "docs/spec-basic-lvsites.md's VARPTR residual); and the SECOND "
          "reference, which does not exist for any row here.")
    if a.gate and dis:
        sys.stderr.write(f"lrvar: {dis} reading(s) diverge\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
