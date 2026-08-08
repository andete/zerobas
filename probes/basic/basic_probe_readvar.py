#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""D-READVAR — what a `READ` target may BE, and how a DATA item lexes into it.

docs/spec-basic-readvar.md. `TODO.md` filed ONE face — *"zerobas has no string
`READ`"* — but `ex_read` (basic/program.asm) consumes a bare letter and stores
through `var_get`/`var_set`, the SINGLE-LETTER int16 compatibility shim
(basic/vars.asm), while every other variable reference in the tree goes through
`var_name_key`, which handles a second name character AND a type suffix. A
scratchpad scout on 2026-08-07 measured five divergences, not one.

TWO DENOMINATORS, and they are different questions:

  A. THE TARGET GRAMMAR. A variable reference is (name, type-suffix, subscript),
     and the DEFtbl supplies the type when the suffix is absent. Rows A* walk
     that surface -- 1- and 2-character names, each suffix, an array element,
     and the two DEFtbl resolutions -- because the defect is in the PARSE of the
     target, so the parse surface is the denominator.

  B. HOW A DATA ITEM LEXES INTO A STRING. This axis is INVISIBLE TODAY and
     becomes observable only once a string target exists at all: an int16 parse
     cannot tell `DATA HELLO` from `DATA "HELLO"` from `DATA HI THERE`. Rows B*
     are therefore characterization of a surface this tree has never read, not a
     regression check. ⚠️ They are the rows most likely to carry a surprise, and
     `DATA 42` into a string target is the one the D-DEFSTR residual actually
     saw: both references answer `42`, NOT ` 42 ` -- the missing PRINT spaces are
     the tell that it is a STRING and not a number.

  C. THE CROSS. A string DATA item read into a NUMERIC target, which is the
     reverse of the filed defect and has no reason to behave the same way.

🟢 `a.one` IS THE POSITIVE CONTROL and it is not decoration: every other row in
this battery can go red at once for a reason that has nothing to do with READ
(a machine that ran no program prints no bracket either). `make
fat-error-acceptance` once scored 8/8 on an all-$00 disk.rom. `a.one` is the
positive text that says READ reached a variable at all.

✅ ALL 24 ROWS ARE SCORED SINCE D-ARYLV (2026-08-08). `a.ary` / `a.arystr` were
deferred and printed but not scored, because `READ A(1)` needed ex_let's array
lvalue path, which was outside the `INPUT` twin D-READVAR was priced against.
That work landed (docs/spec-basic-arylv.md): the target parse and the two stores
are now shared with all three of `INPUT`'s arms, and this gate is 24/24 with an
empty DEFERRED set.

Clean-room: observed outputs only; both reference ROMs are black boxes.
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

# Each case: (label, [program body lines]). The LAST line prints the read-back
# inside `[...]`; only that span is compared, and it is taken from the screen
# tail AFTER `RUN` -- never from the whole screen, because the typed line's own
# ECHO contains a `[` and matching it turns "the machine printed nothing" into a
# value-shaped artifact (measured while scouting this slice, 2026-08-07).
CASES = [
    # --- A. the TARGET GRAMMAR ---------------------------------------------
    ("a.one",     ['DATA 7', 'READ A', 'PRINT"[";A;"]"']),
    ("a.two",     ['DATA 7', 'READ AB', 'PRINT"[";AB;"]"']),
    ("a.digit",   ['DATA 7', 'READ A1', 'PRINT"[";A1;"]"']),
    ("a.pct",     ['DATA 7', 'READ A%', 'PRINT"[";A%;"]"']),
    ("a.bang",    ['DATA 7', 'READ A!', 'PRINT"[";A!;"]"']),
    ("a.hash",    ['DATA 7', 'READ A#', 'PRINT"[";A#;"]"']),
    ("a.str",     ['DATA HELLO', 'READ A$', 'PRINT"[";A$;"]"']),
    ("a.str2",    ['DATA HELLO', 'READ AB$', 'PRINT"[";AB$;"]"']),
    ("a.ary",     ['DATA 7', 'DIM A(3)', 'READ A(1)', 'PRINT"[";A(1);"]"']),
    ("a.arystr",  ['DATA HI', 'DIM A$(3)', 'READ A$(1)', 'PRINT"[";A$(1);"]"']),
    ("a.defstr",  ['DEFSTR Z', 'DATA HELLO', 'READ Z', 'PRINT"[";Z;"]"']),
    ("a.defint",  ['DEFINT Z', 'DATA 7', 'READ Z', 'PRINT"[";Z;"]"']),
    # --- B. how a DATA ITEM LEXES into a string -----------------------------
    ("b.bare",    ['DATA HELLO', 'READ A$', 'PRINT"[";A$;"]"']),
    ("b.digits",  ['DATA 42', 'READ A$', 'PRINT"[";A$;"]"']),
    ("b.quoted",  ['DATA "HI"', 'READ A$', 'PRINT"[";A$;"]"']),
    ("b.qcomma",  ['DATA "A,B"', 'READ A$', 'PRINT"[";A$;"]"']),
    ("b.embsp",   ['DATA HI THERE', 'READ A$', 'PRINT"[";A$;"]"']),
    ("b.leadsp",  ['DATA   PAD', 'READ A$', 'PRINT"[";A$;"]"']),
    ("b.empty",   ['DATA ,X', 'READ A$', 'PRINT"[";A$;"]"']),
    ("b.trailsp", ['DATA PAD  ,X', 'READ A$', 'PRINT"[";A$;"]"']),
    ("b.qspace",  ['DATA " P "', 'READ A$', 'PRINT"[";A$;"]"']),
    ("b.two",     ['DATA A,B', 'READ A$,B$', 'PRINT"[";A$;B$;"]"']),
    ("b.mixed",   ['DATA 1,X', 'READ A,B$', 'PRINT"[";A;B$;"]"']),
    # --- C. the CROSS: a string item into a NUMERIC target ------------------
    ("c.strnum",  ['DATA HELLO', 'READ A', 'PRINT"[";A;"]"']),
]
CONTROL = "a.one"
LABEL_W = 10

# --- DEFERRED rows: measured, printed, NEVER scored -------------------------
# ✅ EMPTY SINCE D-ARYLV (2026-08-08, docs/spec-basic-arylv.md). `a.ary` /
# `a.arystr` were deferred here because an array target needed ex_let's lvalue
# path (ary_op0_resolve / ary_store_write), which was outside the `INPUT` twin
# D-READVAR was priced against. That work landed: `tgt_parse` / `tgt_store_num` /
# `tgt_store_str` (basic/vars.asm) are shared by ex_read and all three of
# input.asm's arms, so both rows are now SCORED and this gate is 24/24.
# ⚠️ The mechanism is deliberately KEPT rather than deleted with its last entry --
# it is 6 lines, and the next deferral is otherwise re-invented by whoever needs
# one. An empty dict scores every row, which is the correct behaviour here.
DEFERRED: dict[str, str] = {}

# Sentinels. A row that answers one of these is NEVER agreement, however many
# sides answer it -- two machines that both failed to print agree perfectly.
SENTINELS = ("<NO CAPTURE>", "<NO OUTPUT>")

ERRORS = ("Syntax error", "Type mismatch", "Out of DATA",
          "Illegal function call", "Subscript out of range",
          "Redimensioned array", "Overflow")


def bracket(raw: str | None) -> str:
    """The `[...]` span the RUN printed, or a sentinel naming what came instead.

    🔴 THE TAIL AFTER `RUN`, NOT THE WHOLE SCREEN. Scanning the name table makes
    the ECHO of `PRINT"[";A$;"]"` a match, so a machine that printed NOTHING
    reports `'";A$;"'` -- an artifact shaped exactly like a reading, on every
    divergent row at once."""
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
            cfg["machine"], [("direct", list(cfg["reset"]) + body + ["RUN"])],
            batch=False, boot=cfg["boot"], step=cfg["step"], **kw)
        out[label] = bracket(caps[0])
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="D-READVAR")
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
    present = [lab for lab, _ in CASES if any(lab in results[s] for s in sides)]

    print("D-READVAR — what a READ target may BE, and how a DATA item lexes   "
          f"sides: {', '.join(sides)}")
    print("=" * 78)

    # --- the POSITIVE control, first and gating ----------------------------
    bad = []
    if CONTROL in present:
        for s in sides:
            got = results[s].get(CONTROL)
            if got != " 7 ":
                bad.append((CONTROL, s, got))
    if bad:
        for lab, s, got in bad:
            print(probe_report.row("FAIL", lab, LABEL_W, {s: got},
                                   "   [POSITIVE CONTROL]"))
            print("        wanted ' 7 ' -- `READ A` is the one target shape "
                  "every side already handles")
        print("\n*** THE POSITIVE CONTROL FAILED, so nothing below it was "
              "measured.\n"
              "    Every row here answers with a short bracketed span, which a "
              "machine that\n"
              "    ran no program at all produces identically on all three "
              "sides. Check\n"
              "    build/*.rom, `make repack-machine` and the mounted image, "
              "THEN re-read\n"
              "    the rows. Exit 2 (not 1) = the instrument was broken, NOT a "
              "regression.")
        for lab in present:
            vals = {s: results[s][lab] for s in sides if lab in results[s]}
            print(probe_report.row("....", lab, LABEL_W, vals, "   (not scored)"))
        print(probe_report.footer(len(bad) + len(present), 0,
                                  "NOT MEASURED (the positive control failed)"))
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
    deferred = 0
    for lab in present:
        vals = {s: results[s][lab] for s in sides if lab in results[s]}
        ok = len(set(vals.values())) == 1 and len(vals) > 1
        if any(v in SENTINELS for v in vals.values()):
            ok = False                  # an apparatus sentinel is NEVER agreement
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
        note = "   [POSITIVE CONTROL]" if lab == CONTROL else ""
        if len(refs) > 1:
            refsplit += 1
            note += "   [REFERENCES DISAGREE — no oracle for this row]"
        print(probe_report.row("ok" if ok else "DIFF", lab, LABEL_W, vals, note))

    print(probe_report.footer(len(present), len(present) - deferred,
                              f"{agree} agree, {dis} diverge, "
                              f"{deferred} deferred (not scored)"))
    print("=" * 78)
    print(f"{agree}/{agree + dis} readings agree "
          f"({len(CASES)} cases, 1 positive control, "
          f"{refsplit} row(s) with no oracle, "
          f"{len(DEFERRED)} DEFERRED row(s) measured but not scored)")
    print("SIDES: vg8020,cf3300,zb — READ/DATA is core BASIC, present on every "
          "MSX1, so both references are legitimate oracles here")
    print("DENOMINATORS: A = the target grammar (name x suffix x subscript x "
          "DEFtbl); B = how a DATA item lexes into a STRING, a surface that is "
          "INVISIBLE until a string target exists; C = the reverse cross")
    if a.gate and dis:
        sys.stderr.write(f"readvar: {dis} reading(s) diverge\n")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
