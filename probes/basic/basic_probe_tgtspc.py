#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""D-TGTSPC — a SPACE between a variable reference and its `(`, at every
`tgt_parse` call site.

D-NXARY measured `NEXT A (1)` (`a.spc`), found **NEXT without FOR** on both
references and **Syntax error** here, and DEFERRED it -- NOT for space. The fix
is one instruction in `tgt_parse` (`basic/vars.asm`), and `tgt_parse` is the
lvalue family's SHARED target parse, so that instruction decides what
`READ A (1)`, `INPUT A (1)`, `LINE INPUT A$ (1)`, `MID$(A$ (1),1,2)=`,
`INPUT#1,A$ (1)`, `FIELD#1,10 AS A$ (1)` and `LSET A$ (1)=` MEAN. None of those
was measured ([[a-shared-engine-fix-must-measure-its-other-callers]]).

MS-BASIC's CHRGET/CHRGOT skips spaces, so the change is very likely right
everywhere. VERY LIKELY IS WHAT THIS TREE DOES NOT SHIP -- hence this probe.

🔴 THE CALL-SITE COUNT WAS WRONG WHEN IT WAS FILED, AND WALKING IT IS THE FIRST
THING THIS PROBE'S DENOMINATOR OWES. `TODO.md` and
`docs/nxary-msx1-characterization.md` §4 both say **seven** call sites.
`grep -n "call\\s*tgt_parse\\b" basic/` says **EIGHT** `call tgt_parse`
instructions, from **NINE** statement surfaces:

  ex_next       basic/program.asm:1665   `NEXT`
  ex_read       basic/program.asm:1845   `READ`
  inpc_vloop    basic/input.asm:102      console `INPUT`, NUMERIC arm
  inpc_vstr     basic/input.asm:127      console `INPUT`, STRING arm
  inpc_line     basic/input.asm:200      `LINE INPUT`
  ex_mid_stmt   basic/str-engine.asm:1014 `MID$(<var>,n,m) = <expr>`
  inp_readvar   basic/files.asm:708      `INPUT #n` / `LINE INPUT #n`
  tgt_parse_fld basic/field.asm:201      -> `FIELD ... AS` (field.asm:288)
                                         -> `LSET`/`RSET`  (field.asm:384)

The filed list ("READ, console INPUT, LINE INPUT, MID$(...)=, FIELD, LSET/RSET
and files.asm") is seven OTHER surfaces and forgot to count `ex_next`, the site
that filed it ([[a-hand-listed-denominator-is-a-scope-claim]]).

🔴 THE FIRST QUESTION IS NOT "DOES THE REFERENCE SKIP THE SPACE" BUT "IS THE
SPACE STILL THERE". If the reference's CRUNCH strips a space before a `(`, the
fix belongs in the TOKENISER and every parser-side byte would be spent in the
wrong file. `t.ctl` / `t.spc` read the STORED LINE BYTES back through TXTTAB --
the same instrument `basic_probe_crunch.py` uses -- so the question is answered
by the artifact rather than by a screen that cannot tell the two apart.

🟢 EVERY SITE CARRIES ITS OWN POSITIVE CONTROL: the CONTIGUOUS `A(1)` form of
the very same statement, on the same fixture. Those are green today (D-ARYLV,
D-LVFIX, D-FLDARY, D-LRVAR, D-NXARY), so a red spaced row beside a green
contiguous one is evidence about the SPACE and nothing else. Without it the
spaced row has two candidate causes ([[row-with-two-candidate-causes]]).

🔴 A CONTROL FAILING ON A **REFERENCE** AND ON **ZEROBAS** ARE DIFFERENT EVENTS
([[classify-a-control-failure-by-which-side-failed-it]]): a reference miss means
the fixture never mounted/opened/wrote -> exit 2, score nothing; a zerobas miss
is an ordinary divergence, scored, and it SCOPES its site.

🔴 ORACLE STRENGTH IS NOT UNIFORM. `INPUT #n`, `FIELD` and `LSET` are Disk
BASIC; a diskless VG-8020 answers `Syntax error` to every one of those words, so
it is not an oracle for them -- it is a machine that cannot express the
question. Those six rows rest on the **CF-3300 alone**, which is a weaker claim
than every other row here, and the report says so per row rather than letting it
pass silently.

⚠️ THE `x.*` ROWS ARE THE BOUNDARY, MEASURED RATHER THAN ASSUMED. A space before
the `$` SUFFIX (`x.dollar`) is `var_name_key`/`var_str_type`'s business, not
`tgt_parse`'s, and a space INSIDE the subscript (`x.inner`) is the array
engine's own expression eval. They are named here so that "the fix works" cannot
quietly mean "some spaces work".

🔴 `z.for` IS A NEGATIVE CONTROL. `FOR A (1)=1 TO 3` must STAY `Syntax error`:
`ex_for` parses its loop variable with `for_name`, NOT `tgt_parse`
(docs/spec-basic-nxary.md §5.2), and both references REFUSE an array element
there ([[gate-whose-answer-is-an-error-passes-a-dead-subject]]).

⚠️ EACH DISK ROW GETS A FRESH COPY OF THE TEST IMAGE -- the `INPUT #n` rows
CREATE a file ([[test-disk-mutation-gotcha]]).

THE READING is the `[...]` span printed BY THE RUN, taken from the screen tail
after `RUN` -- never the whole screen ([[readout-blind-to-its-own-subject]]) --
except for the two `t.*` rows, whose reading is the stored line's token bytes.

Clean-room: observed screen output and observed RAM only; both reference ROMs
are black boxes.
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

TXTTAB = 0xF676   # sysvar: 2-byte LE pointer to the BASIC text base

SIDES = {
    "vg8020": dict(machine="Philips_VG_8020", boot=8.0, step=2.5,
                   reset=("NEW",), diska=False),
    "cf3300": dict(machine="National_CF-3300", boot=14.0, step=4.5,
                   reset=("", "SCREEN 0", "NEW"), diska=True),
    "zb":     dict(machine=ZB_MACHINE, boot=8.0, step=2.5,
                   reset=("NEW",), diska=True),
}
# Stated, not derived: a diskless MSX1 answers `Syntax error` to every Disk BASIC
# word, so it is not an oracle for a row built out of them. Same disposition as
# basic_probe_lvsites.py / basic_probe_dskmsg.py.
NO_DISK_SIDES = ("vg8020",)

# (label, kind, needs_disk, [program lines], [responses typed after RUN])
#   kind "run" -> the `[...]` span the RUN printed
#   kind "tok" -> the STORED line's body bytes (hex), no RUN at all
CASES = [
    # === 0. IS THE SPACE EVEN STORED? the row that decides WHICH FILE ========
    ("t.ctl",     "tok", False, ['1 NEXT A(1)'], []),
    ("t.spc",     "tok", False, ['1 NEXT A (1)'], []),

    # === 1. NEXT — ex_next (basic/program.asm:1665) =========================
    ("n.ctl",     "run", False, ['FOR A=1 TO 2', 'NEXT A(1)',
                                 'PRINT"[OK]"'], []),
    ("n.spc",     "run", False, ['FOR A=1 TO 2', 'NEXT A (1)',
                                 'PRINT"[OK]"'], []),
    # The spaced form must run the FULL resolve, not merely reach a `(`: 99 is
    # outside the auto-DIMmed 0..10, so a subscript that is EVALUATED answers
    # `Subscript out of range` and one that is skipped does not.
    ("n.spcoob",  "run", False, ['FOR A=1 TO 2', 'NEXT A (99)',
                                 'PRINT"[OK]"'], []),

    # === 2. READ — ex_read (basic/program.asm:1845) =========================
    # `PRINT A;A(1)` names WHICH cell took the value: the scalar or the element.
    # A site that read the space as "scalar A, then junk" cannot print ` 0  7 `.
    ("r.ctl",     "run", False, ['DATA 7', 'DIM A(3)', 'READ A(1)',
                                 'PRINT"[";A;A(1);"]"'], []),
    ("r.spc",     "run", False, ['DATA 7', 'DIM A(3)', 'READ A (1)',
                                 'PRINT"[";A;A(1);"]"'], []),
    # ⚠️ AND WHETHER THE SPACED FORM AUTO-DIMS. D-NXARY's a.autodim established
    # that the resolve creates the array on first reference; a site that reads
    # the space differently could create one where zerobas does not. Here the
    # array is NOT DIMmed, so ` 0  7 ` is the auto-DIM answering.
    ("r.spcauto", "run", False, ['DATA 7', 'READ A (1)',
                                 'PRINT"[";A;A(1);"]"'], []),
    ("r.spcoob",  "run", False, ['DATA 7', 'DIM A(3)', 'READ A (9)',
                                 'PRINT"[OK]"'], []),

    # === 3. console INPUT — inpc_vloop / inpc_vstr (basic/input.asm:102,127) =
    ("i.ctl",     "run", False, ['DIM A(3)', 'INPUT A(1)',
                                 'PRINT"[";A;A(1);"]"'], ["7"]),
    ("i.spc",     "run", False, ['DIM A(3)', 'INPUT A (1)',
                                 'PRINT"[";A;A(1);"]"'], ["7"]),
    # the STRING arm is a separate `call tgt_parse`, so it gets its own row
    ("i.spcstr",  "run", False, ['DIM A$(3)', 'INPUT A$ (1)',
                                 'PRINT"[";A$(1);"]"'], ["HI"]),

    # === 4. LINE INPUT — inpc_line (basic/input.asm:200) =====================
    ("l.ctl",     "run", False, ['DIM A$(3)', 'LINE INPUT A$(1)',
                                 'PRINT"[";A$(1);"]"'], ["HI"]),
    ("l.spc",     "run", False, ['DIM A$(3)', 'LINE INPUT A$ (1)',
                                 'PRINT"[";A$(1);"]"'], ["HI"]),

    # === 5. MID$(...)= — ex_mid_stmt (basic/str-engine.asm:1014) ==============
    ("m.ctl",     "run", False, ['DIM A$(3)', 'A$(1)="HELLO"',
                                 'MID$(A$(1),1,2)="XY"',
                                 'PRINT"[";A$(1);"]"'], []),
    ("m.spc",     "run", False, ['DIM A$(3)', 'A$(1)="HELLO"',
                                 'MID$(A$ (1),1,2)="XY"',
                                 'PRINT"[";A$(1);"]"'], []),
    # 🔴 THE ONE ROW THAT IS NOT ABOUT THE SUBSCRIPT. Skipping spaces inside
    # `tgt_parse` also consumes a TRAILING space on the SCALAR path, and
    # `ex_mid_stmt` is the ONLY caller that then reads its delimiter with a bare
    # `ld a,(hl)` -- every other site does its own `skip_spaces` first. So this
    # is the whole SIDE EFFECT of the change, measured rather than argued.
    ("m.trail",   "run", False, ['A$="HELLO"', 'MID$(A$ ,1,2)="XY"',
                                 'PRINT"[";A$;"]"'], []),

    # === 6. INPUT #n — inp_readvar (basic/files.asm:708) — DISK BASIC ========
    ("f.ctl",     "run", True,  ['OPEN"TS.TXT"FOR OUTPUT AS #1', 'PRINT#1,"HI"',
                                 'CLOSE#1', 'DIM A$(3)',
                                 'OPEN"TS.TXT"FOR INPUT AS #1', 'INPUT#1,A$(1)',
                                 'CLOSE#1', 'PRINT"[";A$(1);"]"'], []),
    ("f.spc",     "run", True,  ['OPEN"TS.TXT"FOR OUTPUT AS #1', 'PRINT#1,"HI"',
                                 'CLOSE#1', 'DIM A$(3)',
                                 'OPEN"TS.TXT"FOR INPUT AS #1',
                                 'INPUT#1,A$ (1)',
                                 'CLOSE#1', 'PRINT"[";A$(1);"]"'], []),

    # === 7. FIELD — tgt_parse_fld <- ex_field (field.asm:288) — DISK BASIC ===
    ("d.ctl",     "run", True,  ['DIM A$(3)', 'OPEN"TS.DAT"AS #1',
                                 'FIELD#1,10 AS A$(1)', 'CLOSE#1',
                                 'PRINT"[OK]"'], []),
    ("d.spc",     "run", True,  ['DIM A$(3)', 'OPEN"TS.DAT"AS #1',
                                 'FIELD#1,10 AS A$ (1)', 'CLOSE#1',
                                 'PRINT"[OK]"'], []),

    # === 8. LSET/RSET — tgt_parse_fld <- lrset_common (field.asm:384) ========
    #     ex_lset and ex_rset fall into ONE parse site, so one pair covers both.
    ("s.ctl",     "run", True,  ['DIM A$(3)', 'OPEN"TS.DAT"AS #1',
                                 'FIELD#1,10 AS A$(1)', 'LSET A$(1)="HI"',
                                 'PRINT"[";A$(1);"]"'], []),
    ("s.spc",     "run", True,  ['DIM A$(3)', 'OPEN"TS.DAT"AS #1',
                                 'FIELD#1,10 AS A$(1)', 'LSET A$ (1)="HI"',
                                 'PRINT"[";A$(1);"]"'], []),

    # === 9. the BOUNDARY — other space positions, named rather than implied ==
    # more than ONE space: separates "skip spaces" from "step over one byte"
    ("x.multi",   "run", False, ['FOR A=1 TO 2', 'NEXT A   (1)',
                                 'PRINT"[OK]"'], []),
    # spaces INSIDE the subscript: the ARRAY ENGINE's expression eval, not
    # tgt_parse. Green on all three sides BEFORE the fix is what makes this the
    # control that scopes the defect to the `(` position itself.
    ("x.inner",   "run", False, ['FOR A=1 TO 2', 'NEXT A( 1 )',
                                 'PRINT"[OK]"'], []),
    # a space before the `$` SUFFIX: var_name_key / var_str_type, a DIFFERENT
    # mechanism at a DIFFERENT cursor position -- the skip this slice adds
    # happens AFTER var_name_key has already stopped at the space, so it cannot
    # reach either of these. Both DIVERGE and both are DEFERRED, with their own
    # residual: a space INSIDE a variable reference's name/suffix scan.
    ("x.dollar",  "run", False, ['FOR A=1 TO 2', 'NEXT A $(1)',
                                 'PRINT"[OK]"'], []),
    # ...and how far that goes: is a space inside the NAME ITSELF insignificant?
    # `NEXT A B` against `FOR AB` says whether the reference's name scan skips
    # spaces too, which is what sizes the residual x.dollar files.
    ("x.name",    "run", False, ['FOR AB=1 TO 2', 'NEXT A B',
                                 'PRINT"[OK]"'], []),

    # === the NEGATIVE control ===============================================
    ("z.for",     "run", False, ['DIM A(3)', 'FOR A (1)=1 TO 3', 'NEXT',
                                 'PRINT"[OK]"'], []),
]

CONTROLS = ("t.ctl", "n.ctl", "r.ctl", "i.ctl", "l.ctl", "m.ctl",
            "f.ctl", "d.ctl", "s.ctl")
# `t.ctl`'s want is stated as a CROSS-SIDE identity rather than a literal: the
# token bytes for `NEXT A(1)` are the reference's, and basic_probe_crunch.py
# already gates zerobas byte-for-byte against them. Checked below by comparison,
# not by a hard-coded string, so this probe never re-states the crunch oracle.
CONTROL_WANT = {"n.ctl": "<NEXT without FOR>", "r.ctl": " 0  7 ",
                "i.ctl": " 0  7 ", "l.ctl": "HI", "m.ctl": "XYLLO",
                "f.ctl": "HI", "d.ctl": "OK", "s.ctl": "HI        "}
NEGATIVE = ("z.for",)
LABEL_W = 10

# --- DEFERRED: measured, printed, NEVER scored ------------------------------
# 🔴 A SPACE INSIDE THE NAME, OR BEFORE THE `$` SUFFIX, IS A DIFFERENT AND FAR
# WIDER RULE. Both rows DIVERGE and neither is reachable from this slice: the
# skip D-TGTSPC adds runs AFTER `var_name_key` has already stopped at the space,
# so `NEXT A $(1)` and `NEXT A B` are decided one cursor position earlier, in
# `var_name_key` / `var_str_type`.
# 🎯 `x.name` sizes the residual: `NEXT A B` CLOSING a `FOR AB` loop on both
# references means the reference's whole name scan skips spaces -- which reaches
# every variable reference in every EXPRESSION, not just the nine lvalue targets
# this slice fixes. Folding it in would leave no row able to separate the two
# rules ([[one-row-cannot-separate-two-rules]]).
# Filed in TODO.md with these two readings as its denominator; a deferred row
# that started AGREEING would itself be a finding.
# ✅ CLOSED 2026-08-08 BY D-NAMSPC (docs/spec-basic-namspc.md), and the dict is
# EMPTY. The wider rule was measured on 55 rows of its own -- a space inside a
# variable NAME is insignificant at EVERY reference, not just at these nine
# lvalue targets -- and the fix is one `call skip_spaces` inside `is_ident_cont`
# (basic/vars.asm), the routine all three name-scan read points share. Both rows
# below now SCORE like any other ([[a-deferral-honoured-is-worth-more-than-one-filed]]).
DEFERRED = {}

SENTINELS = ("<NO CAPTURE>", "<NO OUTPUT>", "<NO DISK ON THIS SIDE>",
             "<NOT STORED>")

ERRORS = ("Syntax error", "Type mismatch", "Subscript out of range",
          "Redimensioned array", "Illegal function call", "Out of memory",
          "Out of string space", "Overflow", "Out of DATA", "Bad file number",
          "File not found", "Field overflow", "Bad file name", "Disk offline",
          "File already open", "NEXT without FOR")


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


def tokens(raw: str | None) -> str:
    """The stored line's BODY bytes: everything after link(2) + lineno(2), up to
    and including the 0x00 terminator. `<NOT STORED>` when the line never made
    it into the program area (a crunch that errored leaves link == 00 00)."""
    if not raw:
        return "<NOT STORED>"
    b = bytes.fromhex(raw)
    if len(b) < 5:
        return "<NOT STORED>"
    return b[4:].hex()


def run_side(side: str, only: list[str]) -> dict:
    cfg = SIDES[side]
    out = {}
    for label, kind, needs_disk, lines, responses in CASES:
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
            # A FRESH image per row: the INPUT#n rows CREATE a file.
            dsk = probe_tmp.tmp(f"zb_tgtspc_{side}_{label}.dsk")
            shutil.copy(TEST_DSK, dsk)
            kw["diska"] = dsk
        if kind == "tok":
            caps = omsx_repl.run_cases(
                cfg["machine"], [("direct", list(cfg["reset"]) + list(lines))],
                batch=False, boot=cfg["boot"], step=cfg["step"],
                capture=("stored_line", TXTTAB), **kw)
            out[label] = tokens(caps[0])
            continue
        body = [f"{10 * (k + 1)} {ln}" for k, ln in enumerate(lines)]
        caps = omsx_repl.run_cases(
            cfg["machine"],
            [("direct", list(cfg["reset"]) + body + ["RUN"] + list(responses))],
            batch=False, boot=cfg["boot"], step=cfg["step"], **kw)
        out[label] = bracket(caps[0])
    return out


# Each spaced row is evidence about the SPACE only while its own site's
# CONTIGUOUS control is green on zerobas.
SITE_CONTROL = {
    "t.spc": "t.ctl",
    "n.spc": "n.ctl", "n.spcoob": "n.ctl",
    "r.spc": "r.ctl", "r.spcauto": "r.ctl", "r.spcoob": "r.ctl",
    "i.spc": "i.ctl", "i.spcstr": "i.ctl",
    "l.spc": "l.ctl",
    "m.spc": "m.ctl", "m.trail": "m.ctl",
    "f.spc": "f.ctl",
    "d.spc": "d.ctl",
    "s.spc": "s.ctl",
}


def main() -> int:
    ap = argparse.ArgumentParser(
        description="D-TGTSPC: a space before the `(` at every tgt_parse site")
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
    present = [lab for lab, _, _, _, _ in CASES
               if any(lab in results[s] for s in sides)]

    print("D-TGTSPC — a SPACE before the `(`, at every tgt_parse call site   "
          f"sides: {', '.join(sides)}")
    print("=" * 78)

    def want(ctl: str, side: str):
        """`t.ctl` has no literal oracle: its want is whatever the REFERENCES
        stored, which basic_probe_crunch.py already gates zerobas against."""
        if ctl != "t.ctl":
            return CONTROL_WANT[ctl]
        refs = {results[s].get(ctl) for s in ("vg8020", "cf3300")
                if s in results and results[s].get(ctl) not in
                (None,) + SENTINELS}
        return list(refs)[0] if len(refs) == 1 else None

    # 🔴 ONLY A REFERENCE CAN SAY THE APPARATUS IS BROKEN. A control that fails
    # on `zb` is a finding and is scored below like any other row.
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
            exp = want(ctl, s)
            if exp is None:
                continue                # t.ctl with a single reference: below
            if got != exp:
                bad.append((ctl, s, got, exp))
    if bad:
        for lab, s, got, exp in bad:
            print(probe_report.row("FAIL", lab, LABEL_W, {s: got},
                                   "   [POSITIVE CONTROL]"))
            print(f"        wanted {exp!r}")
        print("\n*** A POSITIVE CONTROL FAILED ON A REFERENCE, so nothing was "
              "measured.\n"
              "    Each control is the CONTIGUOUS `A(1)` form of its own "
              "site's statement, on\n"
              "    the same fixture -- green on all three sides since D-ARYLV / "
              "D-LVFIX /\n"
              "    D-FLDARY / D-LRVAR / D-NXARY. A REFERENCE failing it means "
              "the fixture is\n"
              "    broken: a disk that did not mount, a file never written, a "
              "channel never\n"
              "    opened, a typed response never delivered. (A control failing "
              "on `zb` is NOT\n"
              "    this: that is an ordinary divergence and IS scored, because "
              "only a\n"
              "    reference is supposed to be right.) Check build/*.rom, `make "
              "repack-machine`\n"
              "    and `make latch-check`, THEN re-read the rows. Exit 2 (not "
              "1) = the\n"
              "    instrument was broken, NOT a regression.")
        for lab in present:
            vals = {s: results[s][lab] for s in sides if lab in results[s]}
            print(probe_report.row("....", lab, LABEL_W, vals,
                                   "   (not scored)"))
        print(probe_report.footer(len(bad) + len(present), 0,
                                  "NOT MEASURED (a positive control failed)"))
        return 2

    def ctl_red_on_zb(ctl: str) -> bool:
        got = results.get("zb", {}).get(ctl)
        if got in (None, "<NO DISK ON THIS SIDE>"):
            return False
        exp = want(ctl, "zb")
        return exp is not None and got != exp

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

    agree = dis = noref = onlyone = refsplit = deferred = 0
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
        if lab in NEGATIVE:
            note = "   [NEGATIVE CONTROL — both references REFUSE this]"
        own = SITE_CONTROL.get(lab)
        if own and own in present and ctl_red_on_zb(own):
            note += ("   [ITS OWN CONTIGUOUS CONTROL IS RED ON zb — this row "
                     "is NOT evidence about the SPACE]")
        if not refs:
            noref += 1
            print(probe_report.row("....", lab, LABEL_W, vals,
                                   "   [NO REFERENCE ON ANY REQUESTED SIDE]"))
            continue
        if len(set(refs.values())) > 1:
            refsplit += 1
            dis += 1
            print(probe_report.row("DIFF", lab, LABEL_W, vals,
                                   note + "   [REFERENCES DISAGREE — no oracle "
                                          "for this row]"))
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

    print(probe_report.footer(len(present), len(present) - noref - deferred,
                              f"{agree} agree, {dis} diverge, "
                              f"{noref} without a reference, "
                              f"{deferred} deferred (not scored)"))
    print("=" * 78)
    print(f"{agree}/{agree + dis} readings match their reference "
          f"({len(CASES)} cases, {len(CONTROLS)} positive controls, "
          f"{len(NEGATIVE)} negative control, "
          f"{onlyone} row(s) with ONE reference only, "
          f"{noref} row(s) with none, "
          f"{refsplit} row(s) where the references disagree, "
          f"{len(DEFERRED)} DEFERRED row(s) measured but not scored)")
    print("🔴 ORACLE STRENGTH IS NOT UNIFORM: `INPUT #n` (f.*), `FIELD` (d.*) "
          "and `LSET` (s.*) are Disk BASIC, which a diskless VG-8020 cannot "
          "express — those six rows rest on the CF-3300 ALONE. Every other row "
          "has two references.")
    print("DENOMINATOR: (the NINE statement surfaces that reach tgt_parse: "
          "NEXT, READ, console INPUT numeric, console INPUT string, LINE "
          "INPUT, MID$()=, INPUT #n, FIELD, LSET/RSET) x (CONTIGUOUS `A(1)` "
          "control / SPACED `A (1)`), plus whether the space SURVIVES THE "
          "CRUNCH at all (t.*, read from the stored line bytes, which is what "
          "says whether the fix belongs in the tokeniser or the parser), plus "
          "whether the spaced form runs the FULL resolve (range check, "
          "n.spcoob / r.spcoob) and AUTO-DIMS (r.spcauto), plus the SCALAR-path "
          "side effect at the one caller that reads its delimiter without its "
          "own skip_spaces (m.trail), plus the OTHER space positions — x.multi "
          "(more than one space) and x.inner (inside the subscript) this fix "
          "DOES cover or already covered, x.dollar (before the `$` suffix) and "
          "x.name (inside the NAME) it does NOT, both DEFERRED as a wider rule "
          "in var_name_key, plus the `FOR A (1)=` "
          "form both references REFUSE (z.for). NOT COVERED: a TAB or other "
          "whitespace byte; a space before the `(` of a FUNCTION call or of "
          "`DIM`; `RSET` measured separately from `LSET` (they share one parse "
          "site).")
    if a.gate and dis:
        sys.stderr.write(f"tgtspc: {dis} reading(s) diverge\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
