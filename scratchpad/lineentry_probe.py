#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-LINEENTRY — does the PROGRAM ARRIVE, or does the run fail?

D-PUTCOST measured the work on the guest's own `TIME` clock and found nothing
slow: 1.71 ticks per `PUT` here against 2.14 on the CF-3300, and the exact
three-`PUT` program that reads `<NO OUTPUT>` at `step=2.5` runs in **6 ticks —
0.12 s**. So execution time is not what those rows are measuring, and raising
`step` fixing them has some other explanation.

🎯 THE CANDIDATE, AND THE ROW THAT SEPARATES IT. `step` is the wait between
TYPED LINES, so a machine that is still busy when the next line's keystrokes
arrive loses characters — and a mangled program `RUN`s to nothing while every
statement in it is fast. That predicts something checkable and cheap: at the
failing step the LISTING should not match what was typed.

🔴 AND THE FIRST ATTEMPT AT THIS ROW WAS BLIND ON ALL THREE SIDES, INCLUDING
THE CF-3300. It filtered `raw.splitlines()` for rows beginning with a line
number and found none — because the capture is the SCREEN, returned as one
string with **no newlines**, 40 columns to a row. A readout that fails on its
own positive control is the instrument, not the machine
[[readout-blind-to-its-own-subject]]; this one chunks the capture into 40-column
rows, which is what the screen actually is.

⚠️ AND THE ECHO IS NOT THE LISTING. Typing the program leaves it on screen
BEFORE `LIST` runs, so a reader that scans the whole capture finds the lines
whether or not the machine stored them — the same echo-fence trap that has cost
this tree several readings [[trapsvc-echo-fence]]. Only the text after the LAST
`LIST` row is the listing.
"""
from __future__ import annotations

import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
sys.path.insert(0, os.path.join(ROOT, "probes", "basic"))
import omsx_repl                                                  # noqa: E402
import probe_tmp                                                  # noqa: E402
import basic_probe_fldwidth as F                                  # noqa: E402

COLS = 40
PROG = ['CLEAR 1000',
        'OPEN"TS.DAT"AS #1 LEN=128',
        'FIELD#1,128 AS A$',
        'LSET A$=STRING$(128,"A"):PUT#1,5',
        'LSET A$=STRING$(128,"B"):PUT#1,6',
        'LSET A$=STRING$(128,"C"):PUT#1,7']
TYPED = [f"{10 * (k + 1)} {ln}" for k, ln in enumerate(PROG)]


def rows(raw):
    """The capture is the SCREEN: one string, no newlines, COLS to a row."""
    flat = (raw or "").replace("\n", "")
    return [flat[i:i + COLS].rstrip() for i in range(0, len(flat), COLS)]


PROMPTS = ("Ok", "ZB")


def listing(raw):
    """Everything after the LAST `LIST` echo row, up to the next prompt.

    🔴 THE PROMPT SHARES THE ROW, AND ASSUMING `Ok` LOST EVERY ZEROBAS
    READING. zerobas prints `ZB` with no trailing newline, so its echo row is
    `ZBLIST` and its terminator is a bare `ZB` -- a reader matching the row
    `== "LIST"` and breaking on `== "Ok"` returned None on all three zb steps
    while the program had in fact arrived INTACT. The CF-3300 control passed
    throughout, which is what said the fault was mine.
    """
    r = rows(raw)
    start = None
    for i, row in enumerate(r):
        t = row.strip()
        if t == "LIST" or (t.endswith("LIST") and t[:-4] in PROMPTS):
            start = i + 1
    if start is None:
        return None                      # the LIST never ran: an INSTRUMENT result
    out = []
    for row in r[start:]:
        t = row.strip()
        if t in PROMPTS:
            break
        if t:
            out.append(t)
    return out


def run(side, step):
    cfg = F.SIDES[side]
    kw = {}
    if cfg["diska"]:
        dsk = probe_tmp.tmp(f"lineentry_{side}_{step}.dsk")
        shutil.copy(os.path.join(ROOT, "disk", "test720.dsk"), dsk)
        kw["diska"] = dsk
    caps = omsx_repl.run_cases(
        cfg["machine"], [("direct", list(cfg["reset"]) + TYPED + ["LIST"])],
        batch=False, reset=(), boot=cfg["boot"], step=step, timeout=600.0, **kw)
    return listing(caps[0])


def main():
    print(f"\ntyped {len(TYPED)} line(s); comparing against the LISTING\n")
    mangled = blind = 0
    SIDES_RUN = (("cf3300", 4.5), ("zb", 2.5), ("zb", 5.0), ("zb", 8.0))
    for side, step in SIDES_RUN:
        got = run(side, step)
        tag = f"{side} step={step}"
        if got is None:
            print(f"  {tag:18} 🔴 NO LISTING — the `LIST` row never appeared. "
                  f"That is the INSTRUMENT, not the machine.")
            blind += 1
            continue
        ok = got == TYPED
        print(f"  {tag:18} {'ok  ' if ok else '🔴 MANGLED'} "
              f"{len(got)}/{len(TYPED)} line(s) match")
        if not ok:
            mangled += 1
            for i in range(max(len(got), len(TYPED))):
                a = TYPED[i] if i < len(TYPED) else "<absent>"
                b = got[i] if i < len(got) else "<absent>"
                if a != b:
                    print(f"      typed  {a}")
                    print(f"      listed {b}")
    print()
    if blind:
        print(f"🔴 {blind} row(s) read NOTHING -- that is the INSTRUMENT, and no "
              f"conclusion about line entry can be drawn from this run.")
        return 2
    if mangled:
        print("🔴 a step at which the program does NOT arrive intact is the "
              "finding: the `<NO OUTPUT>` rows are LINE ENTRY, not execution.")
    else:
        print("🟢 the program arrives INTACT at every step, including the failing "
              "one — so line entry is REFUTED and the cause is still unknown.")
    # `DIFF: n/m` -- the summary line filed_row_sweep.py already parses. This probe
    # DOES score (each side is checked against the LISTING), so it is deliberately
    # NOT declared NO-VERDICT alongside the five characterisation probes filed with
    # it. Without this line a CLEAN run reported as "NOTHING PARSED".
    print(f"DIFF: {mangled}/{len(SIDES_RUN)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
