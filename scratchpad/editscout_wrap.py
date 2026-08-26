#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-EDITSCOUT step 4: is the re-read unit a ROW or a LOGICAL LINE?

The complexity driver for any implementation. A line longer than the machine's
LINLEN wraps onto two screen rows; if Enter on the FIRST of them re-executes the
whole statement, the reader must join a row with its continuations (and know
where they stop). If it reads one row, the payload is truncated mid-string and
says so loudly.

The counter payload from step 3 is reused so the answer is a NUMBER that scales,
not a screen that could agree for the wrong reason.
"""
import os
import sys

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "probes", "lib"))
import omsx_repl                                                  # noqa: E402
import probe_tmp                                                  # noqa: E402

SIDE = dict(machine="Philips_VG_8020", boot=8.0, step=2.5, reset=("NEW",))
COLS, ROWS = 40, 24
UP = "\x1e"
LONG = 'A=A+1:PRINT A;"' + "X" * 30 + '"'      # 46 chars -> wraps

CASES = [
    ("control.once", ['CLS', LONG]),
    ("up3", ['CLS', LONG, UP * 3]),
    ("up4", ['CLS', LONG, UP * 4]),
    ("up5", ['CLS', LONG, UP * 5]),
]


def show(label, scr):
    print(f"\n=== {label}  (payload is {len(LONG)} chars)")
    if scr is None:
        print("  <NO CAPTURE>"); return
    for r in range(ROWS):
        t = scr[r * COLS:(r + 1) * COLS].rstrip()
        if t:
            print(f"  r{r:02d} |{t}|")


def main():
    res = omsx_repl.run_cases(SIDE["machine"], [("direct", l) for _, l in CASES],
                              batch=True, reset=SIDE["reset"], boot=SIDE["boot"],
                              step=SIDE["step"], verify_delivery=False)
    for (label, _), scr in zip(CASES, res):
        show(label, scr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
