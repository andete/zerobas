#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""D-RUNTAIL — what a machine prints AFTER a `RUN"file"` / `LOAD"file",R`.

Measurement `docs/runtail-msx1-characterization.md`; spec
`docs/spec-basic-runtail.md`. The residual this closes is
`docs/spec-fat-error-verb-control.md` §8.6:

    `make fat-error-acceptance` reads `run-missing` as
    `'load error|Illegal function call in 3346'` -- TWO screen rows where every
    sibling row reads one. Unexplained by any document, and passing for as long
    as the battery has existed because its `want` is a SUBSTRING.

🔴 AND THE SECOND MESSAGE IS NOT A PROPERTY OF THE MISS. Measured before any of
this was written: `RUN"A:PROG.BAS"` -- the SUCCESS path of a shipped verb, with
the file present and the program demonstrably run -- prints
`Illegal function call in 3346` too. `fat-error`'s `run-alive` control could not
see it, because that control reads the tail of its LAST typed line
(`PRINT PEEK`) and the stray message lands on the RUN line above it. The
residual named the miss; the defect is the verb.

WHAT THE ROWS ASK, and every one of them is a whole-tail EXACT match rather than
a substring, because the subject IS an extra row:

  `run-hit`         a program loaded from disk and run prints its OWN output and
                    NOTHING ELSE
  `run-miss`        a missing file prints ONE message
  `run-miss-res`    ...and does NOT run the program that is already resident
  `run-hit-res`     a successful RUN"file" REPLACES the resident program (the
                    loaded program's output, alone)
  `loadr-hit`       `LOAD"file",R` is the same verb by another spelling
  `loadr-miss-res`  ...including the miss
  `bare-run`        🟢 CONTROL: plain `RUN` is the path this slice does not
                    touch, and it must keep printing exactly the program's output
  `load-plain`      🟢 CONTROL: `LOAD"file"` without `,R` loads and does NOT run

🔴 EVERY ROW IS SCORED BY CROSS-SIDE AGREEMENT, NOT AGAINST A HAND-WRITTEN WANT.
The National CF-3300 defines the answer; this file does not get an opinion. The
one exception is CONTROLS below, which additionally require POSITIVE TEXT in the
agreed reading -- because two DEAD machines agree perfectly, and `<nothing>` is
the expected answer of three rows here ([[gate-whose-answer-is-an-error-passes-a-
dead-subject]]).

⚠️ ONE STRING IS NORMALISED PER SIDE, AND ONLY ONE. zerobas answers a missing
file with its own lowercase `load error` where the CF-3300 says `File not
found` -- the wording divergence `basic/PROVENANCE.md` quarantines for the whole
no-disk / mount / I-O class, deliberately NOT in scope here. A row whose whole
tail is exactly that one message reads `<file-missing>` on both sides, so the
rows can be scored on SHAPE (how many messages, and did the resident program
run) without either re-opening the wording or silently blessing it. A tail that
merely CONTAINS the message is not normalised: the extra row is the subject.

🔴 THE VG-8020 CANNOT MEASURE ANY ROW HERE. `RUN"A:name"` needs a disk
interface; a diskless MSX1 answers `Syntax error`, which would measure the
absence of hardware rather than a language rule. The battery is two-sided BY
CONSTRUCTION (cf3300, zb) and refuses a vg8020 side rather than dropping it
silently -- the `basic_probe_dskmsg` pattern.

⚠️ THE READOUT IS NOT BORROWED, AND THIS IS THE HALF THAT WOULD HAVE BITTEN
([[a-borrowed-window-inherits-its-corpus]]). `omsx_repl.screen_tail` ends the
window at a row that EQUALS a prompt -- correct only when the subject is the
LAST line typed, which here it never is for `load-plain` and is only accidentally
so elsewhere. zerobas prints its prompt and the next echo on the SAME row
(`ZBLIST`), so screen_tail would run straight through the following command and
its output into this row's reading. `tail_after` below ends the window at the
next prompt OR the next echo, which is what "what did THIS command print" means
on both machines.

Clean-room: typed inputs and observed outputs only, no reference-ROM
disassembly. See CONTRIBUTING.md.
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lib"))
import omsx_repl                                                 # noqa: E402
import probe_report                                              # noqa: E402

ZB_MACHINE = os.environ.get("ZEROBAS_BASIC_MACHINE",
                            "C-BIOS_MSX1_EU_REPACK_DISK")
TEST_DSK = os.environ.get("ZEROBAS_TEST_DSK", "disk/test720.dsk")

# `missmsg` is the ONE string normalised per side -- see the docstring.
SIDES = {
    "cf3300": dict(machine="National_CF-3300", boot=14.0, step=4.5,
                   reset=("", "SCREEN 0", "NEW"), missmsg="File not found"),
    "zb":     dict(machine=ZB_MACHINE, boot=8.0, step=2.5,
                   reset=("NEW",), missmsg="load error"),
}
NO_DISK_SIDES = ("vg8020",)

MISSING = "<file-missing>"

# The scratch program this battery writes and reads back. It PRINTS, and that is
# the whole design: a fixture that prints nothing (test720.dsk's own PROG.BAS is
# `10 POKE &HD002,123`) can only be checked by a SECOND instrument, and the
# expected tail of every hit row would then be an ABSENCE with no positive half
# in the same reading. `ZQ9` in the tail says the file arrived AND ran AND
# nothing followed it, in one string.
#
# ⚠️ THE ROWS LEAN ON `SAVE`, and that is acceptable HERE for the same reason
# `merge-alive` may lean on it (docs/spec-fat-error-verb-control.md §8.2): the
# failure is LOUD. A SAVE that wrote nothing makes every hit row read
# `<file-missing>` -- a DIFF against the reference, never a silent pass.
MK = ['10 PRINT"ZQ9"', 'SAVE"A:RT.BAS"', "NEW"]

# Each row is (label, lines, subject_index, extra) where `extra` is None or
# (index, label) naming a SECOND line of the same case whose tail is also scored
# by agreement. Subject indices are explicit rather than derived from a verb
# list: three rows type the SAME verb twice (SAVE...RUN, LOAD...LIST) and any
# derivation rule that picks "the line with the verb" picks the wrong one.
CASES = [
    ("run-hit",        MK + ['RUN"A:RT.BAS"'],                     -1, None),
    ("run-miss",       ['RUN"A:NOSUCH.BAS"'],                      -1, None),
    ("run-miss-res",   ['10 PRINT"ZQ1"', 'RUN"A:NOSUCH.BAS"'],     -1, None),
    ("run-hit-res",    MK + ['10 PRINT"ZQ1"', 'RUN"A:RT.BAS"'],    -1, None),
    ("loadr-hit",      MK + ['LOAD"A:RT.BAS",R'],                  -1, None),
    ("loadr-miss-res", ['10 PRINT"ZQ1"', 'LOAD"A:NOSUCH.BAS",R'],  -1, None),
    # 🟢 THE TWO GREEN CONTROLS. `bare-run` is the REPL's own RUN command path
    # (basic/program.asm dl_run), which reaches run_prog at the depth its `ret`
    # returns to the prompt from -- the shape the disk paths are being corrected
    # TO. It must not move. `load-plain` is LOAD without `,R`: it must load the
    # file (the LIST half) and must NOT run it (the empty tail half).
    ("bare-run",       ['10 PRINT"ZQ1"', "RUN"],                   -1, None),
    ("load-plain",     MK + ['10 PRINT"ZQ1"', 'LOAD"A:RT.BAS"', "LIST"],
     -2, (-1, "listing")),
]

# Rows whose agreed reading must additionally carry POSITIVE TEXT: proof that a
# program actually RAN (or, for `load-plain`, that the file actually arrived).
# Without these the battery is satisfied by two machines that do nothing at all
# -- three rows here expect `<nothing>` and two expect an error message, and a
# dead subject produces both for free.
CONTROLS = {
    "run-hit":            ("ZQ9",),
    "bare-run":           ("ZQ1",),
    "load-plain:listing": ("ZQ9",),
}

ROWS = 24
COLS = 40


def tail_after(raw, cmdline, missmsg):
    """Everything `cmdline` printed: the rows between its echo and the NEXT
    prompt or echo. See the docstring for why screen_tail is not reused.

    Two DISTINCT empty sentinels, never one: `<NO ECHO>` says the apparatus lost
    the anchor and nothing was measured, `<nothing>` says the machine printed
    nothing -- which for three rows here IS the answer. Collapsing them would
    let an apparatus failure compare equal across sides and score as agreement.
    """
    if raw is None:
        return "<NO CAPTURE>"
    # Row 23 is the SCREEN-0 function-key display, which both references show
    # and zerobas does not.
    rows = [raw[r * COLS:(r + 1) * COLS].strip() for r in range(ROWS)][:-1]
    key = cmdline.strip()
    idx = None
    for i, r in enumerate(rows):
        if r == key or r.endswith(key):
            idx = i                              # keep the LAST occurrence
    if idx is None:
        return "<NO ECHO>"
    out = []
    for r in rows[idx + 1:]:
        if any(r == p or r.startswith(p) for p in omsx_repl.PROMPTS):
            break                                # next prompt, echo or not
        if r:
            out.append(r)
    if not out:
        return "<nothing>"
    # The ONE normalisation, and only when the message is the WHOLE tail.
    return " / ".join(MISSING if r == missmsg else r for r in out)


def run_side(side, only):
    cfg = SIDES[side]
    out = {}
    rows = [c for c in CASES if not only or any(c[0].startswith(o)
                                                for o in only)]
    if not rows:
        return out
    if not os.path.exists(TEST_DSK):
        for label, *_ in rows:
            out[label] = "<NO DISK FIXTURE>"
        return out
    # ⚠️ A /tmp COPY, never the committed image: every hit row WRITES RT.BAS.
    dsk = os.path.join(tempfile.gettempdir(), f"zb_runtail_{side}.dsk")
    shutil.copy(TEST_DSK, dsk)
    cases = [("direct", list(cfg["reset"]) + list(lines))
             for _, lines, _, _ in rows]
    caps = omsx_repl.run_cases(cfg["machine"], cases, batch=False,
                               boot=cfg["boot"], step=cfg["step"], diska=dsk)
    for (label, lines, subj, extra), raw in zip(rows, caps):
        out[label] = tail_after(raw, lines[subj], cfg["missmsg"])
        if extra:
            i, name = extra
            out[f"{label}:{name}"] = tail_after(raw, lines[i], cfg["missmsg"])
    return out


def labels_of(row):
    label, _, _, extra = row
    return [label] + ([f"{label}:{extra[1]}"] if extra else [])


# The label pad for every report row this probe prints, on every exit path.
# docs/spec-probe-rowshape.md: ONE grammar, so a knife runner's baseline taken
# on one path can be read against another.
LABEL_W = 20


def main() -> int:
    ap = argparse.ArgumentParser(description="D-RUNTAIL")
    ap.add_argument("--sides", default="cf3300,zb")
    ap.add_argument("--only", default="")
    ap.add_argument("--repeat", type=int, default=1)
    ap.add_argument("--gate", action="store_true",
                    help="exit 1 unless every row agrees across sides")
    a = ap.parse_args()

    sides = [s for s in a.sides.split(",") if s]
    only = [o for o in a.only.split(",") if o]
    for s in sides:
        if s in NO_DISK_SIDES:
            sys.stderr.write(
                f"{s}: a diskless MSX1 has no disk RUN at all -- every row "
                "would measure the absence of a disk interface, not a language "
                "rule. Refused.\n")
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

    scored = [lab for row in CASES for lab in labels_of(row)
              if any(lab in results[s] for s in sides)]

    print("D-RUNTAIL — what a machine prints after RUN\"file\" / LOAD\"file\",R"
          f"   sides: {', '.join(sides)}")
    print("=" * 78)

    # --- the POSITIVE controls, first and gating ---------------------------
    bad = []
    for lab, want in CONTROLS.items():
        for s in sides:
            got = results[s].get(lab)
            if got is None:
                continue                          # excluded by --only
            miss = [w for w in want if w not in got]
            if miss:
                bad.append((lab, s, got, miss))
    if bad:
        for lab, s, got, miss in bad:
            print(probe_report.row("FAIL", lab, LABEL_W, {s: got},
                                   "   [POSITIVE CONTROL]"))
            print(f"        wanted {miss} in the reading")
        print("\n*** A POSITIVE CONTROL FAILED, so nothing below it was "
              "measured.\n"
              "    THREE rows here expect `<nothing>` and TWO expect an error "
              "message, and a\n"
              "    machine that runs no program at all produces both for free "
              "-- `make\n"
              "    fat-error-acceptance` once scored 8/8 on an all-$00 "
              "build/disk.rom. These\n"
              "    controls are the positive text that says a program REACHED "
              "the screen.\n"
              "    Check build/disk.rom, `make repack-machine` and the mounted "
              "image, THEN\n"
              "    re-read the rows. Exit 2 (not 1) = the instrument was "
              "broken, NOT a\n"
              "    regression.")
        for lab in scored:
            vals = {s: results[s][lab] for s in sides if lab in results[s]}
            print(probe_report.row("....", lab, LABEL_W, vals,
                                   "   (not scored)"))
        print(probe_report.footer(len(bad) + len(scored), 0,
                                  "NOT MEASURED (a positive control failed)"))
        return 2

    if len(sides) < 2:
        n = 0
        for lab in scored:
            for s in sides:
                if lab in results[s]:
                    print(probe_report.row("--", lab, LABEL_W,
                                           {s: results[s][lab]}))
                    n += 1
        print(probe_report.footer(n, 0, "CHARACTERIZATION (one side)"))
        print("=" * 78)
        print(f"{len(scored)} row(s) measured on {sides[0]} — "
              "CHARACTERIZATION, no agreement verdict is possible from one side")
        if a.gate:
            sys.stderr.write("runtail: --gate needs at least two sides\n")
            return 2
        return 0

    agree = dis = 0
    for lab in scored:
        vals = {s: results[s][lab] for s in sides if lab in results[s]}
        ok = len(set(vals.values())) == 1 and len(vals) > 1
        if any(v.startswith("<NO ") or v.startswith("<BAD ")
               for v in vals.values()):
            ok = False                # an apparatus sentinel is NEVER agreement
        agree += ok
        dis += not ok
        note = "   [CONTROL]" if lab in CONTROLS else ""
        print(probe_report.row("ok" if ok else "DIFF", lab, LABEL_W,
                               vals, note))
    print(probe_report.footer(len(scored), len(scored),
                              f"{agree} agree, {dis} diverge"))
    print("=" * 78)
    print(f"{agree}/{agree + dis} scored readings agree "
          f"({len(CASES)} cases, {len(CONTROLS)} positive controls)")
    print(f"SIDES: {','.join(SIDES)} — the VG-8020 has no disk ROM and CANNOT "
          "measure any row here (stated, not silently dropped)")
    print(f"NORMALISED: a tail that is EXACTLY the side's own missing-file "
          f"message reads {MISSING!r} "
          f"({', '.join(f'{s}={SIDES[s]['missmsg']!r}' for s in SIDES)}) — "
          "the quarantined wording divergence, not re-opened here")
    if a.gate and dis:
        sys.stderr.write(f"runtail: {dis} reading(s) diverge\n")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
