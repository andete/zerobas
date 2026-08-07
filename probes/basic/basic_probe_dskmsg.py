#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""D-DSKMSG — what a directory-MUTATING disk verb says when nothing matched.

Measurement `docs/dskmsg-msx1-characterization.md`, spec
`docs/spec-basic-dskmsg.md`. This is the reference reading D-LFILES's residual
was blocked on, and nothing else:

    do_kill's no-match prints `load error` where its own comment (basic/files.asm)
    says `File not found`. The message is UNMEASURED for KILL, and
    `make fat-error-acceptance` pins `kill-missing` to `load error` ON PURPOSE.
    Changing it on the strength of a reading taken for a DIFFERENT verb is the
    thing this project does not do.

D-LFILES made `FILES`/`LFILES` reference-exact for that disposition (R-LF4/R-LF6,
ERR 53 `File not found`) and deliberately did NOT re-point `KILL`. So the open
question is a fact about a machine, and this probe asks it.

🔴 THE VG-8020 CANNOT MEASURE ANY ROW HERE, and that is a fact about the
hardware, not a gap to be silently dropped. `KILL`, `NAME` and `FILES` are
Disk-BASIC words that live in the disk ROM; on a diskless MSX1 the crunch has no
entry for them and the machine answers `Syntax error` to all three. Measuring
that would measure the absence of a disk interface. The battery is two-sided BY
CONSTRUCTION (cf3300, zb) and the report says so rather than leaving a reader to
infer it from a silent absence.

🔴 EVERY SUBJECT ROW'S EXPECTED ANSWER IS AN ERROR MESSAGE, WHICH IS EXACTLY
WHAT A DEAD SUBJECT PRINTS. `make fat-error-acceptance` scored 8/8 on a
16384-byte all-$00 `build/disk.rom`
([[gate-whose-answer-is-an-error-passes-a-dead-subject]]): when the disk
subsystem is dead every file is missing, so the expected observable arrives for a
reason that has nothing to do with the disposition under test. Two POSITIVE
controls run in the same invocation, on the same mounted image, and both assert
POSITIVE TEXT rather than the absence of an error string:

  `dsk-ctl`      `FILES"HI.TXT"` must LIST `HI`/`TXT` -- the volume mounts, the
                 root-directory walk runs, and a named file is FOUND. This is
                 the Cy=0 half of the path `dsk-killnone` is the Cy=1 half of.
  `dsk-killhit`  `KILL"HI.TXT"` then `FILES` must show `HI` GONE and `TEST`/`BIN`
                 still there. The first half alone is a negative assertion (a
                 machine that cannot read a directory also fails to list HI); the
                 second half is what makes it positive evidence, and together
                 they say KILL reached the FAT layer and SUCCEEDED.

Without `dsk-killhit`, a build whose KILL was a no-op that always errored would
score a perfect run: `dsk-ctl` green (KILL untouched), `dsk-killnone` green (it
errors, which is the want). The control is what separates "KILL refuses a
no-match" from "KILL refuses".

⚠️ THE READOUT IS BORROWED AND RE-JUSTIFIED, NOT BORROWED AND ASSUMED
([[a-borrowed-window-inherits-its-corpus]] -- a guard proven in one check is an
unmeasured rule in the next). `screen_rows`/`strip_prompt`/`reading` come from
`basic_probe_lptverb`, and they are right here for the same reasons they are
right there: rows are stripped so the C-BIOS/VG-8020 margin difference cannot
diverge a row, the function-key row is dropped, and the two empty sentinels stay
DISTINCT (`<NO ECHO>` = the apparatus lost the anchor; `<nothing>` = the machine
printed nothing, which for no row here is the expected answer and would
therefore be a finding).

🔴 `anchor_for` IS **NOT** BORROWED, AND THAT IS THE HALF THAT WOULD HAVE BITTEN.
Its verb list is `LPRINT/LPOS/LFILES/FILES/RUN/PRINT`, and `dsk-killhit` types
`KILL"HI.TXT"` and then `FILES`. Borrowed verbatim it would have anchored on the
SECOND line, so everything `KILL` printed would fall outside the window and a
KILL that printed an error message would read exactly like a KILL that printed
nothing -- D-EDITVERB's blindness, in a probe written after it was documented.
This file derives its own anchor from its own verb list, KILL and NAME first.

Clean-room: typed inputs and observed outputs only, no reference-ROM
disassembly. See CONTRIBUTING.md.
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))    # sibling probes
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lib"))
import omsx_repl                                                 # noqa: E402
from basic_probe_lptverb import reading                          # noqa: E402

ZB_MACHINE = os.environ.get("ZEROBAS_BASIC_MACHINE",
                            "C-BIOS_MSX1_EU_REPACK_DISK")
TEST_DSK = os.environ.get("ZEROBAS_TEST_DSK", "disk/test720.dsk")

SIDES = {
    "cf3300": dict(machine="National_CF-3300", boot=14.0, step=4.5,
                   reset=("", "SCREEN 0", "NEW")),
    "zb":     dict(machine=ZB_MACHINE, boot=8.0, step=2.5, reset=("NEW",)),
}
# Stated, not derived: see the docstring. A diskless MSX1 answers `Syntax error`
# to every word this probe types.
NO_DISK_SIDES = ("vg8020",)

# The GATED rows. The two controls are gated as well as asserted -- they are
# cross-side observables in their own right, and a layout that agrees is what
# lets `dsk-killhit`'s listing be read as evidence at all.
CASES = [
    ("dsk-ctl",      ['FILES"HI.TXT"']),
    ("dsk-killhit",  ['KILL"HI.TXT"', "FILES"]),
    # THE SUBJECT. basic/files.asm's `jp z,load_error` at do_kill's tail, whose
    # own comment on the same line reads "nothing matched -> File not found".
    ("dsk-killnone", ['KILL"NOSUCH.XXX"']),
]

# CHARACTERIZATION ONLY -- measured, printed, and NOT gated.
#
# 🔴 THE REASON IS A DISTINCTION, NOT A CONVENIENCE. `do_kill`'s divergence is
# one its own inline comment CONTRADICTS; `do_name`'s is one basic/PROVENANCE.md
# §NAME states outright ("Errors ... reuse load_error"), with the code and the
# comment agreeing. Fixing the first needs a reading; changing the second would
# be retiring a documented, quarantined divergence on no evidence at all -- and
# retiring it silently, one verb at a time, is how a divergence register stops
# describing the tree. So NAME is MEASURED here, so that "why KILL and not
# NAME?" has a number behind it, and filed rather than fixed.
CHARACTERIZE = [
    ("dsk-namenone", ['NAME"NOSUCH.BAS" AS "ZZ.BAS"']),
]

# Rows that WRITE to the image they mount, and therefore get a private copy.
# Boot-per-case reboots the machine but keeps handing openMSX the SAME file.
WRITES = {"dsk-killhit"}

# --- the CONTROL assertions, as (row, must-contain, must-NOT-contain) --------
# Positive text on both sides of each. `dsk-killhit` asserts the survivors as
# well as the casualty on purpose: "HI is absent" alone is satisfied by a
# machine that cannot list a directory at all.
CONTROLS = {
    "dsk-ctl":     (("HI", "TXT"), ()),
    "dsk-killhit": (("TEST", "BIN"), ("HI      .TXT",)),
}

VERBS = ("KILL", "NAME", "FILES", "PRINT")


def anchor_for(lines):
    """The typed line the reading starts AFTER -- derived from THIS probe's own
    verb list (docstring: borrowing lptverb's would anchor `dsk-killhit` on its
    trailing FILES and hide everything KILL printed)."""
    for ln in lines:
        for verb in VERBS:
            if verb in ln:
                return ln
    return lines[-1] if lines else ""


def run_side(side, only):
    cfg = SIDES[side]
    out = {}
    rows = [r for r in CASES + CHARACTERIZE
            if not only or any(r[0].startswith(o) for o in only)]
    if not rows:
        return out
    if not os.path.exists(TEST_DSK):
        for label, _ in rows:
            out[label] = "<NO DISK FIXTURE>"
        return out

    def battery(sel, dsk):
        cases = [("direct", list(cfg["reset"]) + list(lines)) for _, lines in sel]
        caps = omsx_repl.run_cases(cfg["machine"], cases, batch=False,
                                   boot=cfg["boot"], step=cfg["step"], diska=dsk)
        for (label, lines), raw in zip(sel, caps):
            out[label] = reading(raw, anchor_for(lines))

    ro = [r for r in rows if r[0] not in WRITES]
    if ro:
        dsk = os.path.join(tempfile.gettempdir(), f"zb_dskmsg_{side}.dsk")
        shutil.copy(TEST_DSK, dsk)
        battery(ro, dsk)
    for row in [r for r in rows if r[0] in WRITES]:
        dsk = os.path.join(tempfile.gettempdir(), f"zb_dskmsg_{side}_{row[0]}.dsk")
        shutil.copy(TEST_DSK, dsk)
        battery([row], dsk)
    return out


def check_controls(results, sides):
    """Every control must hold on EVERY side, on positive evidence. Returns the
    list of failures; a non-empty list means nothing below was measured."""
    bad = []
    for label, (want, unwant) in CONTROLS.items():
        for s in sides:
            got = results[s].get(label)
            if got is None:
                continue                      # excluded by --only
            miss = [w for w in want if w not in got]
            hit = [u for u in unwant if u in got]
            if miss or hit:
                bad.append((label, s, got, miss, hit))
    return bad


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sides", default="cf3300,zb")
    ap.add_argument("--only", default="")
    ap.add_argument("--repeat", type=int, default=1)
    ap.add_argument("--gate", action="store_true",
                    help="exit 1 unless every gated row agrees across sides")
    a = ap.parse_args()

    sides = [s for s in a.sides.split(",") if s]
    only = [o for o in a.only.split(",") if o]
    for s in sides:
        if s in NO_DISK_SIDES:
            sys.stderr.write(
                f"{s}: a diskless MSX1 has no KILL/NAME/FILES in its crunch "
                "table -- every row would measure the absence of a disk "
                "interface, not a language rule. Refused.\n")
            return 2
        if s not in SIDES:
            sys.stderr.write(f"unknown side {s!r}\n")
            return 2

    results = {}
    for s in sides:
        for r in range(a.repeat):
            got = run_side(s, only)
            if r and got != results[s]:
                sys.stderr.write(
                    f"⚠️  {s}: repeat {r + 1} disagrees with repeat 1 -- the "
                    "reading is not stable, so no verdict is possible\n")
                for k in sorted(set(got) | set(results[s])):
                    if got.get(k) != results[s].get(k):
                        sys.stderr.write(
                            f"    {k}: {results[s].get(k)!r} vs {got.get(k)!r}\n")
                return 2
            results[s] = got

    gated = [r[0] for r in CASES if any(r[0] in results[s] for s in sides)]
    chars = [r[0] for r in CHARACTERIZE if any(r[0] in results[s] for s in sides)]

    print(f"D-DSKMSG — KILL's no-match message   sides: {', '.join(sides)}")
    print("=" * 78)

    bad = check_controls(results, sides)
    if bad:
        for label, s, got, miss, hit in bad:
            print(f"  FAIL  {label:14} [{s}] -> {got!r}")
            if miss:
                print(f"        wanted {miss} in the reading")
            if hit:
                print(f"        wanted {hit} ABSENT from the reading")
        print("\n*** A POSITIVE CONTROL FAILED, so nothing below it was "
              "measured.\n"
              "    Every subject row here expects an ERROR MESSAGE, and a dead "
              "disk subsystem\n"
              "    produces one for free -- `make fat-error-acceptance` scored "
              "8/8 on an\n"
              "    all-$00 build/disk.rom. Check build/disk.rom, "
              "`make repack-machine`, and\n"
              "    the mounted image, THEN re-read the rows.\n"
              "    Exit 2 (not 1) = the instrument was broken, NOT a message "
              "regression.")
        for label in gated + chars:
            vals = {s: results[s][label] for s in sides if label in results[s]}
            print(f"  ....  {label:14} "
                  + "  ".join(f"{s}={v!r}" for s, v in vals.items())
                  + "  (not scored)")
        return 2

    if len(sides) < 2:
        for label in gated + chars:
            for s in sides:
                if label in results[s]:
                    print(f"     {label:<14} {results[s][label]!r}")
        print("=" * 78)
        print(f"{len(gated + chars)} row(s) measured on {sides[0]} — "
              "CHARACTERIZATION, no agreement verdict is possible from one side")
        if a.gate:
            sys.stderr.write("dskmsg: --gate needs at least two sides\n")
            return 2
        return 0

    agree = dis = 0
    for label in gated:
        vals = {s: results[s][label] for s in sides if label in results[s]}
        ok = len(set(vals.values())) == 1 and len(vals) > 1
        if any(v.startswith("<NO ") or v.startswith("<BAD ")
               for v in vals.values()):
            ok = False              # an apparatus sentinel is NEVER an agreement
        agree += ok
        dis += not ok
        note = "   [CONTROL]" if label in CONTROLS else ""
        print(f"{'ok ' if ok else 'DIFF'} {label:<14} "
              + ("  ".join(f"{s}={vals[s]!r}" for s in vals)
                 if not ok else repr(next(iter(vals.values())))) + note)
    print("=" * 78)
    print(f"{agree}/{agree + dis} gated rows agree")

    for label in chars:
        vals = {s: results[s][label] for s in sides if label in results[s]}
        same = len(set(vals.values())) == 1
        print(f"     {label:<14} "
              + "  ".join(f"{s}={vals[s]!r}" for s in vals)
              + f"   [CHARACTERIZATION, not gated — {'agrees' if same else 'DIVERGES'}]")
    if chars:
        print("NOT GATED: dsk-namenone (NAME) — do_name's `load error` is a "
              "divergence basic/PROVENANCE.md §NAME states, with code and "
              "comment agreeing; do_kill's is one its own comment contradicts. "
              "Measured so the distinction has a number, filed not fixed "
              "(TODO.md).")
    print(f"SIDES: {','.join(SIDES)} — the VG-8020 has no disk ROM and CANNOT "
          "measure any row here (stated, not silently dropped)")
    if a.gate and dis:
        sys.stderr.write(f"dskmsg: {dis} row(s) diverge\n")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
