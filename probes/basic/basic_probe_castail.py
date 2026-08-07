#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""D-CASTAIL — what a machine prints AFTER `RUN"CAS:x"` / `LOAD"CAS:x",R`.

The TAPE TWIN of `basic_probe_runtail.py`, and the residual that battery filed:
`docs/spec-basic-runtail.md` §9.

    `basic/cload.asm`'s `dl_cas_close` (LOAD"CAS:x",R) and `dr_is_cas`
    (RUN"CAS:x") end in the identical `jp run_prog` from a STATEMENT context, so
    D-RUNTAIL's defect A is structurally present there verbatim -- but that
    battery mounts a disk, not a `.cas`, so no row read them before OR after.

🔴 THE INSTRUMENT WAS ALREADY THERE. §9 says `omsx_repl.run_cases` "mounts a
disk, not a `.cas`", which is true of its SIGNATURE and false of the module: the
`prologue` seam (input-devices arc I2) runs raw Tcl before the timeline, and
`basic_probe_lnblank`'s `cld` rows already mount a tape with
`cassetteplayer insert`. No library change was needed for the mount; what this
battery adds is the `@WAIT` budget per row and the tape FIXTURE.

WHAT THE ROWS ASK, each one a whole-tail EXACT match (never a substring --
the subject IS an extra screen row):

  `cas-run-hit`        a program loaded from TAPE and run prints its OWN output
                       and nothing else
  `cas-run-hit-res`    ...even with a different program already resident
  `cas-loadr-hit`      `LOAD"CAS:x",R` is the same verb by another spelling
  `cas-run-brk`        a tape load ABORTED with Ctrl-STOP prints ONE message
  `cas-run-brk-res`    ...and does NOT then run the program already resident
  `cas-loadr-brk-res`  ...nor does the `LOAD",R` spelling of it
  `bare-run`           🟢 CONTROL: plain `RUN` is the path this slice does not
                       touch; it must keep printing exactly the program's output
  `cas-load-plain`     🟢 CONTROL: `LOAD"CAS:x"` without `,R` loads and does NOT
                       run -- its `:listing` half proves the tape arrived

🔴 THE `-res` ROWS EXIST BECAUSE AN EMPTY PROGRAM HIDES A WRONG RUN. Measured in
D-RUNTAIL under two separate knives ([[an-empty-program-hides-a-wrong-run]]):
`run-miss` -- a failed load with NOTHING resident -- held GREEN over a machine
that ran the store anyway, because running an EMPTY program is silent. "Refused
to run" and "ran an empty store" print the identical string. Every failure row
here therefore has `10 PRINT"ZQ1"` resident and asks whether `ZQ1` is ABSENT.

🔴 EVERY ROW IS SCORED BY CROSS-SIDE AGREEMENT, NOT AGAINST A HAND-WRITTEN WANT.
The references define the answer. The exception is CONTROLS below, which
additionally require POSITIVE TEXT in the agreed reading -- two DEAD machines
agree perfectly, and `<nothing>` is a legitimate answer for one row here
([[gate-whose-answer-is-an-error-passes-a-dead-subject]]).

⚠️ ONE STRING IS NORMALISED PER SIDE, AND ONLY ONE -- exactly as in
`basic_probe_runtail`. An aborted tape read answers `Device I/O error` on the
references and zerobas's own lowercase `load error`: the quarantined no-disk /
mount / I-O wording divergence (`basic/PROVENANCE.md`), deliberately NOT in
scope. A tail that is EXACTLY that one message reads `<load-failed>` on both
sides, so the rows are scored on SHAPE -- how many messages, and did the
resident program run -- without re-opening the wording. A tail that merely
CONTAINS it is not normalised: the extra row is the subject.

🔴 AND ONE CLASS OF ROW IS FILTERED OUT, WHICH IS A DIVERGENCE, SO IT GETS ITS
OWN PINNED ROW RATHER THAN A SILENT NORMALISATION. Both references print the
BIOS tape-search progress line -- `Found:RT` when the search takes a file,
`Skip :RT` when it steps over one -- and zerobas prints NEITHER. That is a
previously unrecorded divergence, found here (docs/castail-msx1-characterization
.md §5, filed in TODO.md); it is about the SEARCH, not about what the verb does
after the load, so scoring it inside every row would DIFF all six subject rows
for a reason none of them is asking about. `SEARCH_ROWS` therefore drops those
two EXACT strings from a tail -- and `cas-load-plain:search` reads the SAME
case's LOAD line UNFILTERED and pins all three sides' readings verbatim
(PINNED). So the filter cannot hide the thing it removes: the day either side
moves, the pin rots and the gate fails.

⚠️ THE FILTER ONLY EVER FIRES ON A REFERENCE, WHICH IS EXACTLY WHY THE PIN IS
NOT OPTIONAL. A normalisation that is a no-op on the side under test is a
normalisation that blesses one machine's silence ([[readout-blind-to-its-own-
subject]]).

🟢 AND UNLIKE THE DISK BATTERY, THE VG-8020 IS A LEGITIMATE SIDE. `RUN"A:name"`
needs a disk interface, which is why `basic_probe_runtail` refuses a vg8020 run;
`RUN"CAS:x"` needs a CASSETTE PORT, which every MSX1 has, and the Philips
VG-8020 answers these rows out of its own main ROM. It is a side here, and its
agreement with the CF-3300 is what says a reading is the MSX1 rule rather than a
property of one machine's Disk BASIC.

⚠️ THE TAPE FIXTURE IS $EA ASCII, AND THAT IS FORCED BY THE REFERENCE.
`LOAD"CAS:"`/`RUN"CAS:"` on a real MSX search the tape for an ASCII file and
SKIP a tokenised ($D3) one -- past it, to the end of the tape, where they wait
forever (measured in docs/dotgaps-msx1-characterization.md §1.2; zerobas accepts
both, a divergence filed there, not re-opened here). A $D3 fixture would
therefore HANG both references and gate nothing.

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
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omsx_repl                                                 # noqa: E402
from basic_probe_cas_ascii import build_ascii_cas                # noqa: E402

ZB_MACHINE = os.environ.get("ZEROBAS_BASIC_MACHINE",
                            "C-BIOS_MSX1_EU_REPACK_DISK")
TEST_DSK = os.environ.get("ZEROBAS_TEST_DSK", "disk/test720.dsk")

# `failmsg` is the ONE string normalised per side -- see the docstring.
SIDES = {
    "vg8020": dict(machine="Philips_VG_8020", boot=8.0, step=2.5,
                   reset=("NEW",), failmsg="Device I/O error", diska=False),
    "cf3300": dict(machine="National_CF-3300", boot=14.0, step=4.5,
                   reset=("", "SCREEN 0", "NEW"), failmsg="Device I/O error",
                   diska=True),
    "zb":     dict(machine=ZB_MACHINE, boot=8.0, step=2.5,
                   reset=("NEW",), failmsg="load error", diska=True),
}

FAILED = "<load-failed>"

# The BIOS tape-search progress rows, dropped from every scored tail and PINNED
# verbatim by `cas-load-plain:search`. Two EXACT strings, never a prefix match:
# a rule wide enough to catch `Found:`-anything is wide enough to eat a program's
# output, and the whole point of this battery is that an extra row is the subject.
SEARCH_ROWS = ("Found:{n}", "Skip :{n}")

# The tape this battery writes and reads back. It PRINTS, and that is the whole
# design: `ZQ9` in the tail says the file arrived AND ran AND nothing followed
# it, in ONE string -- the disk battery's trick, for the same reason.
CAS_NAME = "RT"
CAS_PROG = ['10 PRINT"ZQ9"']

# A tape read runs for ~10-30 EMULATED seconds while the harness keeps injecting
# on schedule, and each injection overwrites whatever is still pending, so the
# clock must be advanced past the operation before the next line is typed
# (omsx_repl.WAIT_PREFIX, and the D-DOTGAPS §1.4b measurement behind it).
W_LOAD = "@WAIT25"       # find + read the first file on the tape
W_SEEK = "@WAIT12"       # let the search run before breaking it
W_AFTER = "@WAIT8"       # let the abort report land

# Each row is (label, lines, subject_index, extra), `extra` = None or a tuple of
# (index, name, drop_search) triples naming FURTHER lines of the same case that
# are read as readings of their own. Subject indices are EXPLICIT rather than
# derived: several rows type a verb twice, and any "the line with the verb in it"
# rule picks the wrong one.
RUNCAS = f'RUN"CAS:{CAS_NAME}"'
LOADRCAS = f'LOAD"CAS:{CAS_NAME}",R'
MISSCAS = 'RUN"CAS:NOSUCH"'
MISSLOADR = 'LOAD"CAS:NOSUCH",R'

CASES = [
    ("cas-run-hit",       [RUNCAS, W_LOAD],                            0, None),
    ("cas-run-hit-res",   ['10 PRINT"ZQ1"', RUNCAS, W_LOAD],           1, None),
    ("cas-loadr-hit",     [LOADRCAS, W_LOAD],                          0, None),
    # --- the failure half: a tape read the operator ABORTS ----------------
    # 🔴 THERE IS NO OTHER TERMINATING TAPE FAILURE ON THE REFERENCE. A named
    # file that is not on the tape is not an error there: the machine searches
    # PAST the end of the tape and waits on silence forever. Ctrl-STOP is the
    # only failure a reference reports and returns from, which makes it the only
    # shape in which "did the resident program run afterwards?" is a question a
    # reference can answer at all.
    ("cas-run-brk",       [MISSCAS, W_SEEK, "@BREAK", W_AFTER],        0, None),
    ("cas-run-brk-res",   ['10 PRINT"ZQ1"', MISSCAS, W_SEEK, "@BREAK",
                           W_AFTER],                                   1, None),
    ("cas-loadr-brk-res", ['10 PRINT"ZQ1"', MISSLOADR, W_SEEK, "@BREAK",
                           W_AFTER],                                   1, None),
    # 🟢 THE TWO GREEN CONTROLS. `bare-run` is the REPL's own RUN command path
    # (basic/program.asm dl_run), which reaches run_prog at the depth its `ret`
    # returns to the prompt from -- the shape the tape paths are being corrected
    # TO. It must not move. `cas-load-plain` is LOAD"CAS:" without `,R`: it must
    # load the tape (the LIST half) and must NOT run it (the empty tail half).
    ("bare-run",          ['10 PRINT"ZQ1"', "RUN"],                    1, None),
    # `:listing` is the control's positive half (the tape ARRIVED); `:search` is
    # the SAME LOAD line read UNFILTERED, and it is the pinned divergence row --
    # see PINNED and the docstring.
    ("cas-load-plain",    ['10 PRINT"ZQ1"', f'LOAD"CAS:{CAS_NAME}"',
                           W_LOAD, "LIST"],                            1,
     ((3, "listing", True), (1, "search", False))),
]

# 🔴 THE PINNED DIVERGENCE. Not an agreement row: the three sides are EXPECTED to
# differ, and each side's exact reading is written down so the day any of them
# moves the pin ROTS and this gate fails. This is what keeps `SEARCH_ROWS` from
# being a normalisation that quietly blesses zerobas's silence.
PINNED = {
    "cas-load-plain:search": {
        "vg8020": f"Found:{CAS_NAME}",
        "cf3300": f"Found:{CAS_NAME}",
        "zb":     "<nothing>",
    },
}

# Rows whose agreed reading must additionally carry POSITIVE TEXT: proof that a
# program actually RAN (or, for `cas-load-plain`, that the tape actually
# arrived). Without these the battery is satisfied by machines that do nothing
# at all -- one row expects `<nothing>` and three expect an error message, and a
# dead subject produces both for free.
CONTROLS = {
    "cas-run-hit":            ("ZQ9",),
    "bare-run":               ("ZQ1",),
    "cas-load-plain:listing": ("ZQ9",),
}

ROWS = 24
COLS = 40


def tail_after(raw, cmdline, failmsg, drop_search=True):
    """Everything `cmdline` printed: the rows between its echo and the NEXT
    prompt or echo. Not `omsx_repl.screen_tail`, for the reason
    `basic_probe_runtail` states: that window ends at a row EQUAL to a prompt,
    which is only correct when the subject is the last line typed -- and here it
    never is (every row carries a trailing `@WAIT`, and two carry a `LIST`).

    Two DISTINCT empty sentinels, never one: `<NO ECHO>` says the apparatus lost
    its anchor and nothing was measured, `<nothing>` says the machine printed
    nothing -- which for one row here IS the answer.
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
    search = [s.format(n=CAS_NAME) for s in SEARCH_ROWS]
    out = []
    for r in rows[idx + 1:]:
        if any(r == p or r.startswith(p) for p in omsx_repl.PROMPTS):
            break                                # next prompt, echo or not
        if drop_search and r in search:
            continue        # the pinned search-progress divergence (see PINNED)
        if r:
            out.append(r)
    if not out:
        return "<nothing>"
    # The ONE normalisation, and only when the message is the WHOLE tail.
    return " / ".join(FAILED if r == failmsg else r for r in out)


_TAPE: dict[str, str] = {}


def tape_path() -> str:
    """Build (and cache) the one $EA ASCII cassette every row mounts."""
    if "p" not in _TAPE:
        d = tempfile.mkdtemp(prefix="zb_castail_")
        p = os.path.join(d, "castail.cas")
        with open(p, "wb") as f:
            f.write(build_ascii_cas(CAS_NAME, CAS_PROG))
        _TAPE["p"] = p
    return _TAPE["p"]


def run_side(side, only):
    cfg = SIDES[side]
    out = {}
    rows = [c for c in CASES if not only or any(c[0].startswith(o)
                                                for o in only)]
    if not rows:
        return out
    kw = {}
    if cfg["diska"]:
        # ⚠️ A /tmp COPY, never the committed image. Nothing here writes to a
        # disk, but a probe that hands openMSX the repo's own .dsk is one bug
        # away from mutating a committed artifact. The CF-3300 and the repack
        # machine both boot into Disk BASIC with a drive attached; the tape
        # verbs under test are main-ROM verbs either way.
        if not os.path.exists(TEST_DSK):
            for label, *_ in rows:
                out[label] = "<NO DISK FIXTURE>"
            return out
        dsk = os.path.join(tempfile.gettempdir(), f"zb_castail_{side}.dsk")
        shutil.copy(TEST_DSK, dsk)
        kw["diska"] = dsk
    cases = [("direct", list(cfg["reset"]) + list(lines))
             for _, lines, _, _ in rows]
    caps = omsx_repl.run_cases(
        cfg["machine"], cases, batch=False, boot=cfg["boot"], step=cfg["step"],
        prologue=(f"cassetteplayer insert {{{tape_path()}}}",), **kw)
    for (label, lines, subj, extra), raw in zip(rows, caps):
        out[label] = tail_after(raw, lines[subj], cfg["failmsg"])
        for i, name, drop in (extra or ()):
            out[f"{label}:{name}"] = tail_after(raw, lines[i], cfg["failmsg"],
                                                drop_search=drop)
    return out


def labels_of(row):
    label, _, _, extra = row
    return [label] + [f"{label}:{n}" for _, n, _ in (extra or ())]


def main() -> int:
    ap = argparse.ArgumentParser(description="D-CASTAIL")
    ap.add_argument("--sides", default="cf3300,zb")
    ap.add_argument("--only", default="")
    ap.add_argument("--repeat", type=int, default=1)
    ap.add_argument("--gate", action="store_true",
                    help="exit 1 unless every row agrees across sides")
    a = ap.parse_args()

    sides = [s for s in a.sides.split(",") if s]
    only = [o for o in a.only.split(",") if o]
    for s in sides:
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

    present = [lab for row in CASES for lab in labels_of(row)
               if any(lab in results[s] for s in sides)]
    scored = [lab for lab in present if lab not in PINNED]
    pins = [lab for lab in present if lab in PINNED]

    print("D-CASTAIL — what a machine prints after RUN\"CAS:x\" / "
          f"LOAD\"CAS:x\",R   sides: {', '.join(sides)}")
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
            print(f"  FAIL  {lab:22} [{s}] -> {got!r}")
            print(f"        wanted {miss} in the reading")
        print("\n*** A POSITIVE CONTROL FAILED, so nothing below it was "
              "measured.\n"
              "    ONE row here expects `<nothing>` and THREE expect an error "
              "message, and a\n"
              "    machine that runs no program at all produces both for free "
              "-- `make\n"
              "    fat-error-acceptance` once scored 8/8 on an all-$00 "
              "build/disk.rom. These\n"
              "    controls are the positive text that says a program REACHED "
              "the screen.\n"
              "    Check build/*.rom, `make repack-machine` and the cassette "
              "fixture, THEN\n"
              "    re-read the rows. Exit 2 (not 1) = the instrument was "
              "broken, NOT a\n"
              "    regression.")
        for lab in present:
            vals = {s: results[s][lab] for s in sides if lab in results[s]}
            print(f"  ....  {lab:22} "
                  + "  ".join(f"{s}={v!r}" for s, v in vals.items())
                  + "  (not scored)")
        return 2

    if len(sides) < 2:
        for lab in present:
            for s in sides:
                if lab in results[s]:
                    print(f"     {lab:<22} {results[s][lab]!r}")
        print("=" * 78)
        print(f"{len(scored)} row(s) measured on {sides[0]} — "
              "CHARACTERIZATION, no agreement verdict is possible from one side")
        if a.gate:
            sys.stderr.write("castail: --gate needs at least two sides\n")
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
        print(f"{'ok ' if ok else 'DIFF'} {lab:<22} "
              + ("  ".join(f"{s}={vals[s]!r}" for s in vals)
                 if not ok else repr(next(iter(vals.values())))) + note)
    # --- the PINNED divergence rows: each side against its OWN written-down
    # reading, never against another side. A pin that still reads what it was
    # pinned at is not agreement -- it is a divergence that has not moved.
    rotted = []
    for lab in pins:
        want = PINNED[lab]
        vals = {s: results[s][lab] for s in sides if lab in results[s]}
        bad = {s: v for s, v in vals.items() if want.get(s) != v}
        rotted += [(lab, s, want.get(s), v) for s, v in bad.items()]
        print(f"{'PIN ' if not bad else 'ROT '} {lab:<22} "
              + "  ".join(f"{s}={vals[s]!r}" for s in vals)
              + "   [PINNED DIVERGENCE]")
    for lab, s, want, got in rotted:
        print(f"      ROTTED [{s}] pinned {want!r}, read {got!r}")

    print("=" * 78)
    print(f"{agree}/{agree + dis} scored readings agree "
          f"({len(CASES)} cases, {len(CONTROLS)} positive controls, "
          f"{len(pins)} pinned divergence row(s))")
    print(f"SIDES: {','.join(SIDES)} — every MSX1 has a CASSETTE PORT, so "
          "unlike the disk battery the VG-8020 is a legitimate reference here")
    print(f"NORMALISED: a tail that is EXACTLY the side's own aborted-load "
          f"message reads {FAILED!r} "
          f"({', '.join(f'{s}={SIDES[s]['failmsg']!r}' for s in SIDES)}) — "
          "the quarantined wording divergence, not re-opened here")
    print(f"PINNED: the BIOS tape-search progress rows "
          f"({', '.join(repr(s.format(n=CAS_NAME)) for s in SEARCH_ROWS)}) are "
          "dropped from every scored tail — zerobas prints NEITHER, a "
          "divergence of the SEARCH that is pinned above, not blessed")
    if a.gate and (dis or rotted):
        if dis:
            sys.stderr.write(f"castail: {dis} reading(s) diverge\n")
        if rotted:
            sys.stderr.write(
                f"castail: {len(rotted)} pinned reading(s) ROTTED -- a "
                "divergence this battery deliberately does not score has "
                "MOVED, so the filter above is no longer describing the "
                "machines. Re-measure and re-pin.\n")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
