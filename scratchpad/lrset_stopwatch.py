#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-LRSETCLOCK — what a FIELD/LSET/RSET statement costs, BEFORE the move.

Joost ruled the full move of the channel trio into disk.rom on 2026-09-17 (*"A,
lets worry about speed when we reach the next tiers"*), and
disk/docs/spec-diskcode-eviction.md §7.1 attaches an obligation to that ruling:
the per-statement price must be MEASURED, not carried as an estimate. The
estimate it would otherwise be carried as is 5-6 call-backs x 0.156 ms, and
🔴 THAT 0.156 ms IS D-XSLOTPRICE'S **main->disk** FIGURE. The direction this move
adds is disk->main, and nothing here has measured it. A number that only ever
existed as an estimate is the kind a later slice quotes as if it had been taken.

THE INSTRUMENT is paint_stopwatch.py's mark stopwatch (docs/spec-probe-budget.md
§6): the case's own BASIC POKEs a watched address either side of the work, and
openMSX logs the emulated instant of every write, so the difference IS the
duration -- on the black-box references too, and bit-identical across runs.

🎯 A LOOP, NOT ONE STATEMENT, and the reason is the instrument's resolution: one
LSET is a handful of microseconds and the marks themselves are POKEs. N=200 makes
the statement's own cost dominate the two marks, and the per-statement figure is
the difference divided by N. ⚠️ The EMPTY loop is measured too and subtracted --
without it this would be timing `FOR`/`NEXT` as much as `LSET`, and this tree's
FOR/NEXT is itself 2.5-3.8x the reference (D-SPEEDPROF).

⚠️ THE REFERENCES ARE THE POINT OF COMPARISON, NOT A PASS MARK. The CF-3300 runs
these verbs in its DISK ROM already, so its figure is what our post-move figure
should be read against -- if ours lands near it, the architecture is priced
correctly even though it got slower. The VG-8020 has no disk and answers ERR 5;
it is recorded as the control that the rig reaches the verb at all.

⚠️ NEEDS A DISK. `FIELD` requires an OPEN random channel, so the zb side runs on
the DISK machine and the cf3300 on its own image. A run whose `FIELD` errors
produces marks anyway -- the loop still executes -- so THE ERROR LINE IS CHECKED:
a case that raises is reported as such rather than timed.
"""
from __future__ import annotations
import os, shutil, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl                                                   # noqa: E402

ZB = os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")
SIDES = {
    "cf3300": dict(machine="National_CF-3300", boot=14.0,
                   reset=("", "SCREEN 0", "NEW", "CLS")),
    "zb":     dict(machine=ZB, boot=8.0, reset=("NEW", "CLS")),
}
MARK = 0xE000
N = 200
# 🔴 A CHANNEL NEEDS A DISK, AND THE FIRST RUN OF THIS PROBE HAD NONE. It mounted
# nothing, so `OPEN"TEST.DAT"AS#1` raised at line 10 and the program never
# reached its first POKE -- NO MARKS on both machines, which looks exactly like
# the instrument failing to arm. The `control` row is what separated the two.
# ⚠️ A FRESH TEMP COPY PER RUN, never disk/test720.dsk itself: this probe OPENs,
# FIELDs, LSETs and CLOSEs, so it WRITES. Timing a verb against a tracked
# fixture would leave the fixture dirty and the next probe reading a disk this
# one modified.
DSK = os.path.join(ROOT, "disk", "test720.dsk")

# (label, the statement repeated N times; "" = the empty-loop baseline)
# 🔴 `control` NEEDS NO DISK AND NO CHANNEL, AND IT IS FIRST FOR A REASON. The
# first run of this probe returned NO MARKS on BOTH machines, which has two
# completely different causes: the sentinel watchpoint never armed (an
# INSTRUMENT failure -- omsx_repl documents one, where a trailing @WAIT armed it
# 117.5 emulated seconds late), or the program RAISED before reaching its first
# POKE (a PROGRAM failure -- `OPEN"TEST.DAT"AS#1` on a machine with no disk).
# Without a row that needs neither, the two are indistinguishable and the
# temptation is to guess. If `control` times and the rest do not, it is the
# OPEN; if `control` does not time either, it is the instrument.
OPS = [
    ("control",   "", False),     # no OPEN, no FIELD -- proves the marks fire
    ("baseline",  "", True),      # the empty loop, WITH the channel set up
    ("lset",      'LSET A$="X"', True),
    ("rset",      'RSET A$="X"', True),
    ("field",     "FIELD#1,16 AS A$", True),
]


def measure(side, op, chan=True):
    cfg = SIDES[side]
    body = (['10 OPEN"TEST.DAT"AS#1 LEN=32',
             "20 FIELD#1,16 AS A$"] if chan else
            ["10 REM no channel -- the control", "20 REM"]) + [
            f"30 POKE&H{MARK:04X},1",
            f"40 FOR I%=1 TO {N}",
            ("50 REM" if not op else f"50 {op}"),
            "60 NEXT I%",
            f"70 POKE&H{MARK:04X},255",
            ("80 CLOSE#1:GOTO80" if chan else "80 GOTO80")]
    spec = ("direct", list(cfg["reset"]) + body + ["RUN"])
    so: dict = {}
    fh = tempfile.NamedTemporaryFile(suffix=".dsk", delete=False); fh.close()
    shutil.copy(DSK, fh.name)
    out = omsx_repl.run_batch(cfg["machine"], [spec], reset=(), boot=cfg["boot"],
                              step=2.5, run_gap=120.0, cap_gap=8.0,
                              timeout=600.0, verify_delivery=False,
                              sentinel=(MARK, 255), settle_out=so,
                              diska=fh.name)
    text = "\n".join(str(x) for x in (out or []))
    marks = so.get("marks", {}).get(0, [])
    t = {v: i for i, v in marks}
    if 1 not in t or 255 not in t:
        return None, ("RAISED: " + text[-90:]) if "rror" in text or "ame" in text \
                     else ("NO MARKS: %r" % (marks,))
    return t[255] - t[1], None


def main():
    only = [a for a in sys.argv[1:] if not a.startswith("-")]
    base: dict = {}
    print(f"N={N} per loop; figures are SECONDS of emulated time\n")
    print(f"{'op':<10} {'cf3300 loop':>13} {'zb loop':>13} "
          f"{'cf3300/stmt':>13} {'zb/stmt':>13}")
    missing = []
    for label, op, chan in OPS:
        if only and label not in only:
            continue
        row = {}
        for side in ("cf3300", "zb"):
            dur, why = measure(side, op, chan)
            row[side] = dur
            if dur is None:
                print(f"  !! {label} {side}: {why}")
                missing.append((label, side, why))
        def fmt(v):
            return "  (no reading)" if v is None else f"{v:>13.6f}"
        if label in ("control", "baseline"):
            if label == "baseline":
                base = row
            print(f"{label:<10} {fmt(row.get('cf3300'))} {fmt(row.get('zb'))} "
                  f"{'--':>13} {'--':>13}")
            continue
        cells = []
        for side in ("cf3300", "zb"):
            if row.get(side) is None or base.get(side) is None:
                cells.append(None)
            else:
                cells.append((row[side] - base[side]) / N)
        print(f"{label:<10} {fmt(row.get('cf3300'))} {fmt(row.get('zb'))} "
              f"{fmt(cells[0])} {fmt(cells[1])}")
    print("\n🔴 READ THE PER-STATEMENT COLUMNS ONLY: the loop figures include "
          "FOR/NEXT, which is itself 2.5-3.8x the reference here, and the "
          "baseline row is what removes it.")
    print("⚠️ A `!!` line is an APPARATUS result, not a fast statement -- a run "
          "whose FIELD raised still produces marks, because the loop still ran.")
    if missing:
        ctl = [m for m in missing if m[0] == "control"]
        print("\n\U0001f534 REFUSING: %d reading(s) absent." % len(missing))
        print("   " + ("THE CONTROL DID NOT TIME EITHER, so this is the "
                       "INSTRUMENT, not the OPEN -- fix the rig before "
                       "believing any row above." if ctl else
                       "The control DID time, so the marks fire and the rig is "
                       "sound: the absent rows are the PROGRAM (the channel "
                       "set-up), not the stopwatch."))
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
