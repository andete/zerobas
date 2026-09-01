#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""D-ARYLV follow-up — the FOUR lvalue parse sites D-ARYLV did NOT measure.

D-ARYLV closed `READ` / `INPUT` / `LINE INPUT` against an array-element target
and, in doing so, recorded that its own "FOUR PARSE SITES" figure was a HAND-LIST:
it counted the sites MEASURED to diverge, not the sites that parse an lvalue
target ([[a-hand-listed-denominator-is-a-scope-claim]]). Walking every caller of
`var_name_key` outside `vars.asm` found four more, all of them named in
docs/spec-basic-arylv.md §3 and none of them measured, because each needs a
file/FIELD fixture rather than a bare boot:

  inp_readvar   basic/files.asm:702      `INPUT #n` / `LINE INPUT #n`
  ex_field      basic/field.asm:194      `FIELD #n, w AS <var>`
  lrset_common  basic/field.asm:283      `LSET` / `RSET`   (ONE site: ex_lset and
                                          ex_rset both fall into it)
  ex_mid_stmt   basic/str-engine.asm:957 `MID$(<var>,n,m) = <expr>` -- whose own
                                          header already says "array lvalues
                                          deferred", i.e. the gap was KNOWN and
                                          never priced

Every one of them does `var_str_type` -> `var_name_key` -> use the KEY, with no
`(` peek anywhere, so all four should refuse an array element. THAT PREDICTION IS
NOT THE MEASUREMENT: what decides whether any of this is work is what the
REFERENCE does, and for `FIELD` in particular it is genuinely unobvious whether
an MSX accepts an array element as a FIELD target at all.

🔴 SIX OF THESE EIGHT ROWS HAVE **ONE** REFERENCE, NOT TWO -- AND THAT IS A
WEAKER ORACLE THAN EVERY ROW D-ARYLV MEASURED. `INPUT #n`, `FIELD` and
`LSET`/`RSET` are Disk BASIC: a diskless MSX1 answers `Syntax error` to every one
of those words, so the Philips VG-8020 cannot oracle them and only the National
CF-3300 can (the same disposition `basic_probe_dskmsg.py` carries, and the same
NO_DISK_SIDES name). The probe prints the per-row reference COUNT and refuses to
describe a one-reference row as "both references agree". Only the `MID$` rows,
which need no disk at all, get two.

🟢 EVERY SITE CARRIES ITS OWN POSITIVE CONTROL -- the SCALAR form of the very
same statement, in the same program, on the same fixture. Without it a red array
row has two candidate causes: the target parse, or the whole statement being
unsupported/mis-fixtured on that side ([[row-with-two-candidate-causes]]). This is
not theoretical here: `INPUT #n` needs a file that a previous line WROTE, `FIELD`
and `LSET` need an open RANDOM channel, and any of those can fail for reasons
that have nothing to do with a subscript.

🔴 A CONTROL FAILING ON A **REFERENCE** AND ON **ZEROBAS** ARE DIFFERENT EVENTS,
AND THE FIRST DRAFT OF THIS PROBE CONFLATED THEM. It exited 2 -- "the instrument
broke, nothing was measured" -- for either, and the first run tripped on
`s.ctl`: zerobas answers `Syntax error` to `LSET A$="HI"` on a plain non-FIELDed
scalar, where the CF-3300 answers `'HI   '`. That is a **finding about zerobas**,
not a broken fixture, and treating it as one threw away six perfectly good
readings from the other three sites -- whose own controls had all passed, which
is itself proof the disk mounted and the channels opened. So:

  * control fails on a REFERENCE  -> the fixture is broken. Exit 2, score nothing.
    Only a reference can tell you the apparatus is wrong, because only it is
    supposed to be right.
  * control fails on ZEROBAS      -> an ordinary divergence, scored like any
    other row, and it SCOPES its site: the array row beside it can no longer be
    read as "the subscript was refused" ([[row-with-two-candidate-causes]] again,
    one level up).

⚠️ The lesson generalises past this probe: **a positive control's failure mode
has to be classified by WHICH SIDE failed it**, or a defect in the tree gets
reported as a broken instrument and silences the rows around it.

⚠️ EACH ROW GETS A FRESH COPY OF THE TEST IMAGE. The `INPUT #n` rows CREATE a
file, so a shared image would let one row's leftovers decide another row's
reading ([[test-disk-mutation-gotcha]]).

⚠️ MEASUREMENT ONLY. Nothing is implemented for these four sites and this is not
an acceptance gate; rows that can only ever be red are doc debt, not a gate.

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

SIDES = {
    "vg8020": dict(machine="Philips_VG_8020", boot=8.0, step=2.5,
                   reset=("NEW",), diska=False),
    "cf3300": dict(machine="National_CF-3300", boot=14.0, step=4.5,
                   reset=("", "SCREEN 0", "NEW"), diska=True),
    "zb":     dict(machine=ZB_MACHINE, boot=8.0, step=2.5,
                   reset=("NEW",), diska=True),
}
# Stated, not derived: a diskless MSX1 answers `Syntax error` to every Disk BASIC
# word, so it is not an oracle for a row built out of them -- it is a machine
# that cannot express the question. Same disposition as basic_probe_dskmsg.py.
NO_DISK_SIDES = ("vg8020",)

# (label, needs_disk, [program lines])
CASES = [
    # --- MID$(...)= : the one site that needs NO fixture, so it gets BOTH refs -
    ("m.ctl",   False, ['A$="HELLO"', 'MID$(A$,1,2)="XY"', 'PRINT"[";A$;"]"']),
    ("m.ary",   False, ['DIM A$(3)', 'A$(1)="HELLO"', 'MID$(A$(1),1,2)="XY"',
                        'PRINT"[";A$(1);"]"']),
    # --- INPUT #n : sequential read back into the target ---------------------
    ("f.ctl",   True,  ['OPEN"LV.TXT"FOR OUTPUT AS #1', 'PRINT#1,"HI"',
                        'CLOSE#1', 'OPEN"LV.TXT"FOR INPUT AS #1',
                        'INPUT#1,A$', 'CLOSE#1', 'PRINT"[";A$;"]"']),
    ("f.ary",   True,  ['OPEN"LV.TXT"FOR OUTPUT AS #1', 'PRINT#1,"HI"',
                        'CLOSE#1', 'DIM A$(3)', 'OPEN"LV.TXT"FOR INPUT AS #1',
                        'INPUT#1,A$(1)', 'CLOSE#1', 'PRINT"[";A$(1);"]"']),
    # --- FIELD : the target is a FIELD buffer alias, not a value -------------
    ("d.ctl",   True,  ['OPEN"LV.DAT"AS #1', 'FIELD#1,10 AS A$', 'CLOSE#1',
                        'PRINT"[OK]"']),
    ("d.ary",   True,  ['DIM A$(3)', 'OPEN"LV.DAT"AS #1',
                        'FIELD#1,10 AS A$(1)', 'CLOSE#1', 'PRINT"[OK]"']),
    # --- LSET : ex_lset and ex_rset share ONE parse site (lrset_common), so one
    #     pair of rows covers both verbs. A non-FIELDed target is the simpler
    #     half of that site and needs no open channel to reach the name parse.
    #     The site needs a 2x2, not a pair: LSET has a FIELDed arm and a
    #     non-FIELDed one, and `lrset_notfld` (field.asm) is a bare
    #     `jp stmt_error` commented "slice-1 limit". So a red `s.ctl` says
    #     nothing about the SUBSCRIPT, and without the FIELDed arm the site's
    #     array question could not be asked at all.
    ("s.ctl",   True,  ['A$="XXXXX"', 'LSET A$="HI"', 'PRINT"[";A$;"]"']),
    ("s.ary",   True,  ['DIM A$(3)', 'A$(1)="XXXXX"', 'LSET A$(1)="HI"',
                        'PRINT"[";A$(1);"]"']),
    ("s.fld",   True,  ['OPEN"LV.DAT"AS #1', 'FIELD#1,10 AS A$',
                        'LSET A$="HI"', 'PRINT"[";A$;"]"']),
    ("s.fldary", True, ['DIM A$(3)', 'OPEN"LV.DAT"AS #1',
                        'FIELD#1,10 AS A$(1)', 'LSET A$(1)="HI"',
                        'PRINT"[";A$(1);"]"']),
]
CONTROLS = ("m.ctl", "f.ctl", "d.ctl", "s.ctl", "s.fld")
CONTROL_WANT = {"m.ctl": "XYLLO", "f.ctl": "HI", "d.ctl": "OK",
                "s.ctl": "HI   ", "s.fld": "HI        "}
# The LSET site's two arms are controlled separately: a red `s.ctl` (non-FIELDed)
# must not be allowed to explain away `s.fldary`, whose own control is `s.fld`.
SITE_CONTROL = {"s.ary": "s.ctl", "s.fldary": "s.fld"}
LABEL_W = 8

SENTINELS = ("<NO CAPTURE>", "<NO OUTPUT>", "<NO DISK ON THIS SIDE>")

ERRORS = ("Syntax error", "Type mismatch", "Subscript out of range",
          "Illegal function call", "Out of memory", "Out of string space",
          "Bad file number", "File not found", "Field overflow",
          "Bad file name", "Disk offline", "File already open")


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
    return "<NO OUTPUT>"


def run_side(side: str, only: list[str]) -> dict:
    cfg = SIDES[side]
    out = {}
    for label, needs_disk, lines in CASES:
        if only and label not in only:
            continue
        if needs_disk and side in NO_DISK_SIDES:
            # NOT a reading. A diskless machine cannot express the question, and
            # recording its `Syntax error` as an answer would manufacture an
            # agreement with zerobas out of an absent disk controller.
            out[label] = "<NO DISK ON THIS SIDE>"
            continue
        kw = {}
        if cfg["diska"]:
            # A FRESH image per row: f.ctl/f.ary CREATE a file.
            dsk = probe_tmp.tmp(f"zb_lvsites_{side}_{label}.dsk")
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
        description="D-ARYLV follow-up: the four unmeasured lvalue parse sites")
    ap.add_argument("--sides", default="vg8020,cf3300,zb")
    ap.add_argument("--only", default="")
    ap.add_argument("--gate", action="store_true",
                    help="exit 1 unless every scored row agrees across sides")
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

    print("D-ARYLV follow-up — the four lvalue parse sites NOT measured by it   "
          f"sides: {', '.join(sides)}")
    print("=" * 78)

    # 🔴 ONLY A REFERENCE CAN SAY THE APPARATUS IS BROKEN (see the docstring).
    # A control that fails on `zb` is a finding and is scored below like any
    # other row; a control that fails on a REFERENCE means the fixture never
    # mounted / opened / wrote, and nothing in this run means anything.
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
              "    Each control is the SCALAR form of its own site's statement, "
              "on the same\n"
              "    fixture. A REFERENCE failing it means the fixture is broken "
              "-- a disk that\n"
              "    did not mount, a file that was never written, a channel that "
              "never opened.\n"
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

    # Which SITES has zerobas already failed on the SCALAR form? An array row in
    # such a site cannot be read as "the subscript was refused" -- the statement
    # does not work for any target there, and saying otherwise would attribute a
    # wider defect to this narrow one. Sites are the label prefix (m/f/d/s).
    def ctl_red_on_zb(ctl: str) -> bool:
        got = results.get("zb", {}).get(ctl)
        return (got not in (None, "<NO DISK ON THIS SIDE>")
                and got != CONTROL_WANT[ctl])

    zb_broken_sites = {
        ctl.split(".")[0] for ctl in CONTROLS
        if ctl in present and ctl_red_on_zb(ctl)
    }

    agree = dis = noref = 0
    onlyone = 0
    for lab in present:
        vals = {s: results[s][lab] for s in sides if lab in results[s]}
        refs = {s: v for s, v in vals.items()
                if s in ("vg8020", "cf3300") and v not in SENTINELS}
        note = "   [POSITIVE CONTROL]" if lab in CONTROLS else ""
        # A row is disqualified as subscript evidence only by ITS OWN arm's
        # control -- SITE_CONTROL names it where a site has more than one arm,
        # so a red non-FIELDed LSET cannot explain away the FIELDed array row.
        if lab not in CONTROLS:
            own = SITE_CONTROL.get(lab)
            blocked = (ctl_red_on_zb(own) if own and own in present
                       else lab.split(".")[0] in zb_broken_sites and not own)
            if blocked:
                note += ("   [ITS OWN SCALAR CONTROL IS RED ON zb — this row is "
                         "NOT evidence about the SUBSCRIPT]")
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
            note += f"   [ONE REFERENCE ONLY ({list(refs)[0]}) — Disk BASIC]"
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
          f"({len(CASES)} cases, {len(CONTROLS)} positive controls, "
          f"{onlyone} row(s) with ONE reference only, "
          f"{noref} row(s) with none)")
    print("🔴 ORACLE STRENGTH IS NOT UNIFORM HERE: only the MID$ rows have TWO "
          "references. INPUT #n / FIELD / LSET are Disk BASIC, which a diskless "
          "VG-8020 cannot express — so those rows rest on the CF-3300 alone, "
          "which is a weaker claim than every row D-ARYLV measured.")
    print("DENOMINATOR: the four var_name_key callers outside vars.asm that "
          "parse an LVALUE target and were never measured against an array "
          "element (inp_readvar, ex_field, lrset_common, ex_mid_stmt) x (scalar "
          "control / array element). ex_lset and ex_rset share ONE parse site.")
    if a.gate and dis:
        sys.stderr.write(f"lvsites: {dis} reading(s) diverge\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
