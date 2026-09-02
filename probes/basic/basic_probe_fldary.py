#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""D-FLDARY — an array element as a `FIELD` / `LSET` / `RSET` target.

docs/spec-basic-fldary.md. The last two of the four lvalue parse sites
docs/lvsites-msx1-characterization.md measured. D-LVFIX shipped `ex_mid_stmt`
and `inp_readvar` and DECLINED this pair with numbers; this slice re-priced the
decline against a design and three of its four reasons did not survive it (spec
§4.2 / §6.4). Three sites move:

  ex_field       basic/field.asm    `FIELD #n, w AS <target>`
  lrset_common   basic/field.asm    `LSET` / `RSET`   -- ONE site, see below
  str_eval_arr   basic/arrays.asm   the FIELDed-READ hook -- THE THIRD SITE

🔴 THE READ PATH IS A SITE, AND IT IS WHY THE TWO PARSE SITES ARE NOT THE FIX.
A fielded variable behaves only because `str_eval_one` (basic/strvar.asm) calls
`fld_lookup` on the SCALAR path; the array path pointed STRPTR straight at the
element and never consulted FLD_TAB. A fix that taught only the parse sites
about subscripts would have turned `d.ary` green FOR THE WRONG REASON -- the
subscript parsed and discarded, so `A$(1)` and `A$(2)` collide in the table --
and left `s.fldary` red. `s.fldary2` is the row that says so and K-FA2 is the
knife.

🔴 EVERY ROW HERE HAS **ONE** REFERENCE. `FIELD` and `LSET`/`RSET` are Disk
BASIC: the Philips VG-8020 has no disk controller, answers `Syntax error` to all
three words, and CANNOT EXPRESS THE QUESTION -- recording its answer would
manufacture an agreement out of an absent drive. Every row rests on the National
CF-3300 alone (NO_DISK_SIDES, the same disposition basic_probe_lvsites.py and
basic_probe_lvfix.py carry). That is weaker than anything D-ARYLV rested on, it
is not upgraded anywhere here, and every row prints its reference count.

🎯 `s.fldary2` AND `s.fldarymix` EXIST BECAUSE A KNIFE WAS DRAFTED FIRST.
Asking "which row moves?" of the element discriminator, before the row set was
frozen, answered NONE: with a single fielded element, a FIELD that stores the
wrong key and an LSET that looks up the SAME wrong key still agree with each
other, so `d.ary` and `s.fldary` are green under a completely broken
discriminator. A cut with no row is a missing row, not a bad cut
([[draft-the-knives-before-freezing-the-row-set]]) -- so two rows were added:
one where two elements of one array must stay apart (`s.fldary2`, deliberately
DIFFERENT WIDTHS so the wrong entry is visible in the padding), and one where an
element and a scalar must stay apart in the same FIELD (`s.fldarymix`, which is
the row the spec's §4.2 disjoint-key-space argument has to survive).

⚠️ A SITE WITH TWO ARMS NEEDS A CONTROL PER ARM. `d.ctl` scopes the FIELD rows
and `s.fld` scopes the LSET/RSET rows; a red `d.ctl` must never be allowed to
explain away an `s.*` reading. One control per SITE was the natural first draft
at this very verb and it would have disqualified a good row
(docs/lvsites-msx1-characterization.md §3).

🔴 A CONTROL FAILING ON A REFERENCE AND ON ZEROBAS ARE DIFFERENT EVENTS
([[classify-a-control-failure-by-which-side-failed-it]]):

  * control fails on the CF-3300 -> the fixture is broken (a disk that did not
    mount, a channel that never opened). Exit 2, score nothing. Only a reference
    can tell you the apparatus is wrong, because only it is supposed to be right.
  * control fails on ZEROBAS     -> an ordinary divergence, scored like any other
    row, which additionally SCOPES ITS OWN ARM.

⚠️ `RSET` IS NOT A SECOND PARSE SITE. `ex_lset` and `ex_rset` both fall into
`lrset_common`, so `r.fldary` measures the STORE's justify direction, not a
second parse. Said here rather than implied by a row count.

⚠️ EACH ROW GETS A FRESH COPY OF THE TEST IMAGE -- these rows CREATE and FIELD a
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

OPEN = 'OPEN"FA.DAT"AS #1'          # no FOR clause => RANDOM, which FIELD needs

# (label, needs_disk, [program lines])
CASES = [
    # --- FIELD: does the statement ACCEPT the target? ------------------------
    # These rows read `OK`, i.e. "the parse was accepted". What the table then
    # HOLDS is the s.* rows' question, not theirs -- the split is deliberate and
    # is named in the denominator rather than implied.
    ("d.ctl",       True, [OPEN, 'FIELD#1,10 AS A$', 'CLOSE#1',
                           'PRINT"[OK]"']),
    ("d.ary",       True, ['DIM A$(3)', OPEN, 'FIELD#1,10 AS A$(1)', 'CLOSE#1',
                           'PRINT"[OK]"']),
    ("d.aryvar",    True, ['DIM A$(3)', 'I=1', OPEN, 'FIELD#1,10 AS A$(I)',
                           'CLOSE#1', 'PRINT"[OK]"']),
    ("d.ary2d",     True, ['DIM A$(2,2)', OPEN, 'FIELD#1,10 AS A$(1,1)',
                           'CLOSE#1', 'PRINT"[OK]"']),
    # The ERROR face of the FIELD site. 🎯 K-FA5's row, and unlike D-LVFIX's two
    # aborts this one IS falsifiable: exec_stmt CLEARS FPERR at the statement
    # boundary and ex_field runs no check between the resolve and it, so with the
    # abort cut this row prints OK instead of the reference's error.
    # ⚠️ D-STMTPEND (docs/spec-basic-stmtpend.md §6.3) removed that premise: the
    # statement boundary now READS the pending cell and raises instead of
    # clearing it, so a cut falls through to a report rather than to OK. The row
    # is unchanged and still green; what K-FA5 now reads is UNMEASURED (filed in
    # TODO.md) and is deliberately not predicted here.
    ("d.aryoor",    True, ['DIM A$(3)', OPEN, 'FIELD#1,10 AS A$(9)']),
    # --- LSET / RSET: what the field actually HOLDS --------------------------
    ("s.fld",       True, [OPEN, 'FIELD#1,10 AS A$', 'LSET A$="HI"',
                           'PRINT"[";A$;"]"']),
    ("s.fldary",    True, ['DIM A$(3)', OPEN, 'FIELD#1,10 AS A$(1)',
                           'LSET A$(1)="HI"', 'PRINT"[";A$(1);"]"']),
    ("s.fldaryvar", True, ['DIM A$(3)', 'I=1', OPEN, 'FIELD#1,10 AS A$(I)',
                           'LSET A$(I)="HI"', 'PRINT"[";A$(1);"]"']),
    ("s.fldary2d",  True, ['DIM A$(2,2)', OPEN, 'FIELD#1,10 AS A$(1,1)',
                           'LSET A$(1,1)="HI"', 'PRINT"[";A$(1,1);"]"']),
    # 🎯 IDENTITY, row 1: two elements of ONE array, with DIFFERENT WIDTHS so a
    # table that cannot tell them apart is visible in the PADDING and not only in
    # the bytes. A subscript-discarding fix reads 'BB  ' (entry 1, width 4) here.
    ("s.fldary2",   True, ['DIM A$(3)', OPEN, 'FIELD#1,4 AS A$(1),6 AS A$(2)',
                           'LSET A$(1)="AA"', 'LSET A$(2)="BB"',
                           'PRINT"[";A$(2);"]"']),
    # 🎯 IDENTITY, row 2: a scalar and an element FIELDed in ONE statement. This
    # is the row the spec §4.2 key-space argument has to survive -- a scalar key
    # is (upcased letter, ...) and an element key is (offset_hi|$80, offset_lo),
    # and nothing but this row asks whether they can coexist in one table.
    ("s.fldarymix", True, ['DIM B$(3)', OPEN, 'FIELD#1,4 AS A$,6 AS B$(1)',
                           'LSET A$="XX"', 'LSET B$(1)="YY"',
                           'PRINT"[";A$;"|";B$(1);"]"']),
    ("s.fldaryoor", True, ['DIM A$(3)', OPEN, 'FIELD#1,10 AS A$(1)',
                           'LSET A$(9)="HI"']),
    # RSET shares lrset_common with LSET: this is the STORE's justify direction,
    # NOT a second parse site.
    ("r.fldary",    True, ['DIM A$(3)', OPEN, 'FIELD#1,10 AS A$(1)',
                           'RSET A$(1)="HI"', 'PRINT"[";A$(1);"]"']),
]

CONTROLS = ("d.ctl", "s.fld")
CONTROL_WANT = {"d.ctl": "OK", "s.fld": "HI        "}
# Which control scopes which row -- PER ARM, not per site (see the docstring).
SITE_CONTROL = {
    "d.ary": "d.ctl", "d.aryvar": "d.ctl", "d.ary2d": "d.ctl",
    "d.aryoor": "d.ctl",
    "s.fldary": "s.fld", "s.fldaryvar": "s.fld", "s.fldary2d": "s.fld",
    "s.fldary2": "s.fld", "s.fldarymix": "s.fld", "s.fldaryoor": "s.fld",
    "r.fldary": "s.fld",
}

LABEL_W = 12
SENTINELS = ("<NO CAPTURE>", "<NO OUTPUT>", "<NO DISK ON THIS SIDE>")

ERRORS = ("Syntax error", "Type mismatch", "Subscript out of range",
          "Illegal function call", "Out of memory", "Out of string space",
          "Overflow", "Bad file number", "File not found", "FIELD overflow",
          "Bad file name", "Disk offline", "File already open",
          "Bad file mode", "Redimensioned array")


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
            dsk = probe_tmp.tmp(f"zb_fldary_{side}_{label}.dsk")
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
        description="D-FLDARY: an array element as a FIELD / LSET / RSET target")
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

    print("D-FLDARY — an ARRAY ELEMENT as a FIELD / LSET / RSET target   "
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
              "    Each control is the SCALAR form of its own ARM's statement, "
              "on the same\n"
              "    fixture. A REFERENCE failing it means the fixture is broken "
              "-- a disk that\n"
              "    did not mount, a channel that never opened RANDOM.\n"
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
                     "evidence about the SUBSCRIPT]")
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
    print("🔴 ORACLE STRENGTH: EVERY row here has ONE reference. FIELD / LSET / "
          "RSET are Disk BASIC, which a diskless VG-8020 cannot express — so the "
          "whole table rests on the National CF-3300 alone, a weaker claim than "
          "every row D-ARYLV rested on. Not upgraded anywhere.")
    print("DENOMINATOR: (subscript FORM: literal / variable) x (RANK: 1-D / 2-D) "
          "x (VERB: FIELD / LSET / RSET), plus the out-of-range row at EACH parse "
          "site (whose oracle is an ERROR, not a value), plus the two IDENTITY "
          "rows the read hook forces — two elements of one array, and an element "
          "beside a scalar in ONE FIELD — plus one positive control PER ARM. The "
          "d.* rows measure ACCEPTANCE (the parse) and the s.*/r.* rows measure "
          "what the field HOLDS; that split is deliberate.")
    print("NOT COVERED, named rather than implied: `RSET` as a distinct PARSE "
          "site (it shares lrset_common, so r.fldary measures the store's justify "
          "direction only); a subscript that is itself an array element "
          "(FIELD#1,10 AS A$(B(1))); FIELD overflow past the record length "
          "(unchecked today, unchanged here); ERASE of a fielded array (spec §5.4 "
          "— the ARYTAB-relative key goes stale under aeng_erase's compaction, a "
          "named limit with a price and NO ORACLE TAKEN); LSET/RSET on a "
          "non-FIELDed element (the separate slice-1-limit residual); and the "
          "SECOND reference, which does not exist for any row here.")
    if a.gate and dis:
        sys.stderr.write(f"fldary: {dis} reading(s) diverge\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
