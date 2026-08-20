#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""D-DSKMSG — what a directory-MUTATING disk verb says when nothing matched.

Measurement `docs/dskmsg-msx1-characterization.md`; specs
`docs/spec-basic-dskmsg.md` (KILL, R-DK1) and `docs/spec-basic-dkname.md`
(NAME, R-DK2). This is the reference reading D-LFILES's residual was blocked on,
and nothing else:

    do_kill's no-match prints `load error` where its own comment (basic/files.asm)
    says `File not found`. The message is UNMEASURED for KILL, and
    `make fat-error-acceptance` pins `kill-missing` to `load error` ON PURPOSE.
    Changing it on the strength of a reading taken for a DIFFERENT verb is the
    thing this project does not do.

D-LFILES made `FILES`/`LFILES` reference-exact for that disposition (R-LF4/R-LF6,
ERR 53 `File not found`) and deliberately did NOT re-point `KILL`. So the open
question is a fact about a machine, and this probe asks it.

⚠️ BOTH VERBS ARE GATED NOW, AND THEY LANDED ONE SLICE APART ON PURPOSE.
D-DSKMSG (2026-08-07) took both readings and moved `KILL` only, printing
`dsk-namenone` as an explicitly NOT-GATED characterization row: `do_kill`'s
divergence was one its own comment CONTRADICTED, `do_name`'s was one
basic/PROVENANCE.md §NAME STATED, and -- the reason that was a number rather
than a preference -- `nm_fail` was a SHARED exit for the fat_mount failure and
the fat_find miss, so the fix was an arm split, not a jump-target swap.
D-DKNAME made the split (basic/files.asm's `nm_notfound`), moved this row into
the gated set, and deleted the printed `NOT GATED:` line with it: a list of
exclusions holding a non-exclusion stops being read as a list of holes.

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
reason that has nothing to do with the disposition under test. THREE POSITIVE
controls run in the same invocation, on the same mounted image, and all three
assert POSITIVE TEXT rather than the absence of an error string:

  `dsk-ctl`      `FILES"HI.TXT"` must LIST `HI`/`TXT` -- the volume mounts, the
                 root-directory walk runs, and a named file is FOUND. This is
                 the Cy=0 half of the path `dsk-killnone` is the Cy=1 half of.
  `dsk-killhit`  `KILL"HI.TXT"` then `FILES` must show `HI` GONE and `TEST`/`BIN`
                 still there. The first half alone is a negative assertion (a
                 machine that cannot read a directory also fails to list HI); the
                 second half is what makes it positive evidence, and together
                 they say KILL reached the FAT layer and SUCCEEDED.
  `dsk-namehit`  `NAME"HI.TXT" AS "BYE.TXT"` then `FILES` must show `BYE`/`TXT`
                 PRESENT, `TEST` still there and `HI      .TXT` gone -- the same
                 shape, for the verb `dsk-killhit` says nothing about.

ONE CONTROL PER GATED VERB, AND THAT IS THE POINT. Without `dsk-killhit`, a
build whose KILL was a no-op that always errored would score a perfect run:
`dsk-ctl` green (KILL untouched), `dsk-killnone` green (it errors, which is the
want). `dsk-namehit` closes the identical hole for NAME, which stood open for as
long as `dsk-namenone` was ungated and would have shipped with it -- neither of
the first two controls executes NAME at all. Knife K-NAMECTL
(docs/spec-basic-dkname.md §5) is that build made real: `tnt_name_stamp` re-reads
the directory sector instead of writing it back, so NAME reports success and
renames nothing; `dsk-namehit` reds and every other row holds, `dsk-namenone`
included.

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
import probe_report                                              # noqa: E402
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
    # 🔴 NAME's OWN POSITIVE CONTROL, and it is not optional (D-DKNAME,
    # docs/spec-basic-dkname.md §3.2). Gating `dsk-namenone` puts a second
    # ERROR-expecting row in a battery a DEAD subject already passes, and
    # NEITHER existing control can see NAME: under a NAME that silently renames
    # nothing, `dsk-ctl` is green (NAME untouched), `dsk-killhit` is green (KILL
    # untouched) and `dsk-namenone` is green too, because it errors, which is
    # the want. Knife K-NAMECTL is that build, and this is the row that reds.
    ("dsk-namehit",  ['NAME"HI.TXT" AS "BYE.TXT"', "FILES"]),
    # THE SUBJECT of D-DSKMSG. basic/files.asm's do_kill tail, whose own comment
    # read "nothing matched -> File not found" while the code said load_error.
    ("dsk-killnone", ['KILL"NOSUCH.XXX"']),
    # 🔴 THE SUBJECT of D-DKNAME -- R-DK2, GATED SINCE 2026-08-07. This row was
    # a printed, explicitly NOT-GATED characterization row for one slice: the
    # reading existed (the CF-3300 answers `File not found`) but `nm_fail` was a
    # SHARED exit for the fat_mount failure and the fat_find miss, so acting on
    # it was an arm split rather than a jump-target swap. The split landed
    # (basic/files.asm's nm_notfound), and the row moved here WITH the printed
    # `NOT GATED:` line deleted -- a list of exclusions that contains a
    # non-exclusion stops being read as a list of holes.
    ("dsk-namenone", ['NAME"NOSUCH.BAS" AS "ZZ.BAS"']),

    # === D-LOADERR: the SIX verbs the `load error` class still had no reading
    # === for. PRINTED, NOT GATED -- they DIVERGE today, and gating a known
    # === divergence turns a battery red forever instead of measuring anything.
    # This is exactly the state `dsk-namenone` was in until 2026-08-07: a
    # printed characterization row whose reading existed but whose fix was an
    # ARM SPLIT rather than a jump-target swap. It graduated the day the split
    # landed. These will graduate the same way, and until then a row that
    # started AGREEING is itself a finding.
    #
    # 🎯 KILL AND NAME ARE THE PRECEDENT AND THE CONTROL. `dsk-killnone` and
    # `dsk-namenone` are GATED and agree -- their missing-file arms already
    # route at `df_notfound` (ERR 53, raised). So the target face is not a
    # guess: it is what two verbs in this same battery already produce.
    #
    # MEASURED 2026-08-20, both sides, stored programs (docs/loaderr-msx1-
    # characterization.md). Every one of the six: CF-3300 raises
    # `File not found in <line>` and STOPS; zerobas prints `load error` and
    # the program RUNS ON.
    ("dsk-loadnone",  ['LOAD"NOSUCH.BAS"']),
    ("dsk-bloadnone", ['BLOAD"NOSUCH.BIN"']),
    ("dsk-runnone",   ['RUN"NOSUCH.BAS"']),
    ("dsk-mergenone", ['MERGE"NOSUCH.BAS"']),
    ("dsk-opennone",  ['OPEN"NOSUCH.DAT"FOR INPUT AS #1']),
    ("dsk-appnone",   ['OPEN"NOSUCH.DAT"FOR APPEND AS #1']),
    # 🎯 AND A SEVENTH FACE THE CLASS DID NOT KNOW ABOUT: the reference tells
    # NOT FOUND apart from WRONG KIND. `BLOAD` of a BASIC file is `Bad file
    # mode` there and `load error` here, so zerobas collapses two distinct
    # errors into one string -- the same conflation shape D-ARYOOS found in
    # `ARY_ERR=4`, and the reason the fix is an ARM SPLIT and not a rename.
    ("dsk-bloadmode", ['BLOAD"PROG.BAS"']),
]

# Rows PRINTED but NOT SCORED: a measured, filed divergence. Keeping them out of
# the tally is what stops a known-red row from masking a NEW red one.
#
# ✅ FIVE OF THE ORIGINAL SEVEN GRADUATED THE SAME DAY THEY WERE FILED (D-LOADERR,
# 2026-08-20): `dsk-loadnone`, `dsk-runnone`, `dsk-mergenone`, `dsk-opennone` and
# `dsk-appnone` are now GATED, exactly the way `dsk-namenone` graduated when its
# own arm split landed. That is what this set is for -- a holding pen with an
# exit, not a place rows go to be forgotten.
#
# 🔴 THE TWO THAT REMAIN ARE BOTH `BLOAD`, AND THEY REMAIN FOR ONE STATED REASON:
# BLOAD's loader is the sub-ROM PAGE-1 tenant (sub/bload.asm), where the shared
# fatio-body.inc binds to the REAL sub-side primitives and `DISKOP_OP` is never
# written -- so the DISKOP_OP test df_or_loaderr (basic/files.asm) uses cannot
# see it. BLOAD reports through BL_STAT and needs a value of its own.
# `dsk-bloadmode` additionally needs a SECOND face (`Bad file mode`), which no
# arm in the tree produces yet.
NOT_GATED = {"dsk-bloadnone", "dsk-bloadmode"}

# Rows that WRITE to the image they mount, and therefore get a private copy.
# Boot-per-case reboots the machine but keeps handing openMSX the SAME file.
# Shared, `dsk-namehit` would rename HI.TXT out from under `dsk-ctl` on a
# `--repeat 2` second pass, exactly as `dsk-killhit` would delete it.
WRITES = {"dsk-killhit", "dsk-namehit"}

# --- the CONTROL assertions, as (row, must-contain, must-NOT-contain) --------
# Positive text on both sides of each. `dsk-killhit`/`dsk-namehit` assert the
# SURVIVORS as well as the casualty on purpose: "HI is absent" alone is
# satisfied by a machine that cannot list a directory at all, so the absence
# half is a negative assertion and the survivors are what make it evidence.
CONTROLS = {
    "dsk-ctl":     (("HI", "TXT"), ()),
    "dsk-killhit": (("TEST", "BIN"), ("HI      .TXT",)),
    "dsk-namehit": (("BYE", "TXT", "TEST"), ("HI      .TXT",)),
}

# D-LOADERR: the anchor is derived from THIS list, so a new verb that is not in
# it anchors on `lines[-1]` by luck rather than by rule. LOAD/BLOAD/RUN/MERGE/
# OPEN added with their rows.
VERBS = ("KILL", "NAME", "FILES", "PRINT",
         "BLOAD", "LOAD", "MERGE", "OPEN", "RUN")


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
    rows = [r for r in CASES
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


# The label pad for every report row this probe prints, on every exit path.
# docs/spec-probe-rowshape.md: ONE grammar, so a knife runner's baseline taken
# on one path can be read against another.
LABEL_W = 14


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

    measured = [r[0] for r in CASES if any(r[0] in results[s] for s in sides)]
    gated = [r for r in measured if r not in NOT_GATED]
    reported = [r for r in measured if r in NOT_GATED]

    print(f"D-DSKMSG/D-DKNAME — KILL's and NAME's no-match message   "
          f"sides: {', '.join(sides)}")
    print("=" * 78)

    bad = check_controls(results, sides)
    if bad:
        for label, s, got, miss, hit in bad:
            print(probe_report.row("FAIL", label, LABEL_W, {s: got},
                                   "   [POSITIVE CONTROL]"))
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
        for label in gated:
            vals = {s: results[s][label] for s in sides if label in results[s]}
            print(probe_report.row("....", label, LABEL_W, vals,
                                   "   (not scored)"))
        print(probe_report.footer(len(bad) + len(gated), 0,
                                  "NOT MEASURED (a positive control failed)"))
        return 2

    if len(sides) < 2:
        n = 0
        for label in gated:
            for s in sides:
                if label in results[s]:
                    print(probe_report.row("--", label, LABEL_W,
                                           {s: results[s][label]}))
                    n += 1
        print(probe_report.footer(n, 0, "CHARACTERIZATION (one side)"))
        print("=" * 78)
        print(f"{len(gated)} row(s) measured on {sides[0]} — "
              "CHARACTERIZATION, no agreement verdict is possible from one side")
        if a.gate:
            sys.stderr.write("dskmsg: --gate needs at least two sides\n")
            return 2
        return 0

    for label in reported:
        vals = {s: results[s][label] for s in sides if label in results[s]}
        print(probe_report.row("....", label, LABEL_W, vals,
                               "   [D-LOADERR: measured, filed, NOT gated]"))

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
        print(probe_report.row("ok" if ok else "DIFF", label, LABEL_W,
                               vals, note))
    print(probe_report.footer(len(gated), len(gated),
                              f"{agree} agree, {dis} diverge"))
    print("=" * 78)
    print(f"{agree}/{agree + dis} gated rows agree")
    print(f"SIDES: {','.join(SIDES)} — the VG-8020 has no disk ROM and CANNOT "
          "measure any row here (stated, not silently dropped)")
    if reported:
        print(f"{len(reported)} row(s) PRINTED, NOT GATED (D-LOADERR): "
              "a measured, filed divergence — `load error` is printed and not "
              "raised, so the program runs on. They graduate into the tally the "
              "day the arm split lands, exactly as dsk-namenone did.")
    if a.gate and dis:
        sys.stderr.write(f"dskmsg: {dis} row(s) diverge\n")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
