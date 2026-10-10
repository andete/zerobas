#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-TXTCEIL acceptance — a line store may not grow past the string-pool floor.

The line store used to compare `PRGEND + size` against the CONSTANT `TXTMAX`
(`$DB00`), so `CLEAR n,himem` never reached the check and the program grew PAST
HIMEM into the string and variable area, silently. `dl_store` now publishes the
live variable-region ceiling in `SL_CEIL` and the lineedit tenant bounds against
it. This is the row that pins that, and it went **−225 B → +71 B** across the fix.

🎯 THE INVARIANT NEEDS NO ORACLE, AND THAT IS THE WHOLE REASON THIS PROBE EXISTS
SEPARATELY:

        PRGEND  <=  HIMEM - POOLSIZE

It is a claim about ZEROBAS's own map and holds whatever a machine reserves per
file channel. `crf-oomsay` / `crf-oomlst` in `basic_probe_lnblank.py` compare
`FRE(0)` against machines that reserve **293 + 267×MAXFILES** below HIMEM where
zerobas reserves **12 + 50×MAXFILES** (D-HIMEMRES) — because D-FCH's per-channel
block is *"state ONLY (no buffer)"*. Those rows can never agree and were the
wrong instrument for this defect. This one is zerobas-only ON PURPOSE and says so.

🔴 AND A ONE-SIDED INVARIANT IS TRIVIALLY SATISFIED BY A MACHINE THAT STORES
NOTHING, which is exactly how a bound that over-refuses would look GREEN here.
`c.fits` is the other half: a program that comfortably fits must be stored IN
FULL. Without it, `p.n25`/`p.n40` would pass on a ROM that refused every line
[[a-case-that-agrees-can-agree-for-the-wrong-reason]].

⚠️ AND EVERY ROW CHECKS ITS OWN FIXTURE BEFORE ITS SUBJECT. An earlier cut used
`CLEAR 300,TXTTAB+400`, which is REFUSED — HIMEM stays at its default `$F380` —
and the row then reported a comfortable green about a machine that had never
been set up. Each case asserts `HIMEM == TXTTAB+GAP` and `POOLSIZE == POOL`
first, and reports `NOT MEASURED` rather than a verdict when they disagree.
"""
from __future__ import annotations

import argparse
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl                                                  # noqa: E402
import probe_report                                               # noqa: E402

ZB_M = os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")
TXTTAB, PRGEND, HIMEM, POOL = 0xF676, 0xE026, 0xFC4A, 0xE232
BODY = "REM " + "A" * 30                 # ~36 stored bytes per line
LABEL_W = 9

# (label, nlines, pool, gap, want)
#   "fits"    the program must be stored IN FULL and stay inside the floor
#   "bounded" the program asks for more than there is: the store must stop
#             before the floor, wherever it stops
# 🔁 RE-PINNED 2026-10-10 (D-FCBSHAPE FCB #0): every gap +267. The channel area
# below the pool now holds FCB #0 as well (as both references do, at every
# MAXFILES), so at gap 1000 the 700 B under the floor no longer held the channel
# area + the 256 B stack margin + any program -- every row read stored=0
# (scratchpad/fcb0_diag_txtceil-acceptance.out). +267 keeps each row's geometry
# identical RELATIVE TO THE CHANNEL AREA, which is what the rows are about.
CASES = [
    ("c.fits",  3, 300, 1267, "fits"),
    ("p.n25",  25, 300, 1267, "bounded"),
    ("p.n40",  40, 300, 1267, "bounded"),
    # A second geometry, so "bounded" is not one arithmetic coincidence: a
    # SMALLER pool puts the floor 100 B higher, and the store must follow it.
    # 🔴 The first cut used pool 500 / gap 900 and the CLEAR was REFUSED (900
    # minus 500 leaves too little), so the row read `NOT MEASURED` -- which is the
    # fixture control working, and is why it is checked before the subject.
    ("p.pool2", 25, 200, 1267, "bounded"),
]


def peek16(addr):
    return f"PEEK(&H{addr:04X})+256*PEEK(&H{addr + 1:04X})"


def run(nlines, pool, gap):
    prog = (["A=PEEK(&HF676)+256*PEEK(&HF677)", f"CLEAR {pool},A+{gap}"]
            + [f"{10 * (k + 1)} {BODY}" for k in range(nlines)]
            + [f'PRINT"[T";{peek16(TXTTAB)};"]"',
               f'PRINT"[E";{peek16(PRGEND)};"]"',
               f'PRINT"[H";{peek16(HIMEM)};"]"',
               f'PRINT"[P";{peek16(POOL)};"]"'])
    raw = "".join(omsx_repl.run_cases(
        ZB_M, [("direct", ["NEW"] + prog)], batch=False, reset=(), boot=8.0,
        step=6.0, cap_gap=12.0, timeout=500.0)[0] or "")
    rows = [raw[i * 40:(i + 1) * 40].strip() for i in range(24)]
    out = {}
    for key in "TEHP":
        # 🔴 ONLY ROWS THAT *BEGIN* WITH THE FENCE. The echo of the PRINT line
        # contains `[T` too, and reading that reports the TYPED TEXT as a value.
        m = [mm for r in rows if r.startswith(f"[{key}")
             for mm in re.findall(rf"^\[{key}\s*(-?\d+)\s*\]", r)]
        out[key] = int(m[-1]) if m else None
    return out


def main():
    ap = argparse.ArgumentParser(
        description="D-TXTCEIL: a line store may not pass the string-pool floor")
    ap.add_argument("--only")
    ap.add_argument("--gate", action="store_true")
    a = ap.parse_args()

    sel = [c for c in CASES if not a.only or any(t in c[0]
                                                 for t in a.only.split(","))]
    if not sel:
        print(f"APPARATUS FAILURE: --only {a.only!r} selected no row; nothing "
              f"to measure is not a clean run.")
        return 2
    # c.fits is the row that stops a bound which refuses EVERYTHING from reading
    # green, so a scoped run gets it back whether it was asked for or not.
    if not any(c[0] == "c.fits" for c in sel):
        sel = [c for c in CASES if c[0] == "c.fits"] + sel

    bad = 0
    for label, n, pool, gap, want in sel:
        r = run(n, pool, gap)
        if any(r[k] is None for k in "TEHP"):
            bad += 1
            print(probe_report.row("DIFF", label, LABEL_W, {"zb": "<NO READING>"},
                                   "   🔴 the row never printed its sentinels "
                                   "— that is the probe, not the machine"))
            continue
        # the fixture, before the subject
        if r["H"] != r["T"] + gap or r["P"] != pool:
            bad += 1
            print(probe_report.row(
                "DIFF", label, LABEL_W,
                {"zb": f"HIMEM={r['H']} want {r['T'] + gap}, POOLSIZE={r['P']} "
                       f"want {pool}"},
                "   🔴 NOT MEASURED: the CLEAR did not take, so every other "
                "number here is about an un-set-up machine"))
            continue
        floor = r["H"] - r["P"]
        head = floor - r["E"]
        stored = r["E"] - r["T"]
        if want == "fits":
            ok = head >= 0 and stored >= 60      # 3 lines x ~36 B, floored low
            note = ("   [POSITIVE CONTROL — a program with room must be STORED, "
                    "or a bound that refuses everything reads green below]")
        else:
            ok = head >= 0 and stored > 0
            note = "   [the store must stop before the pool floor]"
        bad += not ok
        print(probe_report.row(
            "ok" if ok else "DIFF", label, LABEL_W,
            {"zb": f"stored={stored} PRGEND={r['E']} floor={floor} head={head}"},
            note))

    print(probe_report.footer(len(sel), len(sel),
                              f"{len(sel) - bad} within the pool floor, "
                              f"{bad} not"))
    print("SIDE: zb only — `PRGEND <= HIMEM - POOLSIZE` is a claim about "
          "ZEROBAS's own map. The references reserve 293 + 267*MAXFILES below "
          "HIMEM against 12 + 50*MAXFILES here (D-HIMEMRES), so an FRE(0) "
          "comparison measures that architectural difference and not this rule.")
    if a.gate and bad:
        sys.stderr.write(f"txtceil: {bad} row(s) outside the pool floor\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
