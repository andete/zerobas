#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-EDITSCOUT step 3: a re-entry row that is not blind to its own subject.

🔴 STEP 2's PRIMARY ROW WAS BLIND BY CONSTRUCTION. `PRINT"AAA"`, re-entered from
the screen, reprints AAA over the AAA already there and `Ok` over the `Ok`
already there — the screen after a WORKING re-entry is byte-identical to the
screen after no re-entry at all. It read as "the editor did nothing" and the
editor had done its job. (What proved the mechanism was the WRONG-ROW control:
cursor-up x1 lands on an `Ok` row and re-entering it raises `Syntax error`.)

The fix is a payload whose re-execution CHANGES what it prints:
`A=A+1:PRINT A` reads 1 on first execution and 2 when re-entered.
"""
import os
import sys

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "probes", "lib"))
import omsx_repl                                                  # noqa: E402
import probe_tmp                                                  # noqa: E402

SIDES = {
    "vg8020": dict(machine="Philips_VG_8020", boot=8.0, step=2.5, reset=("NEW",)),
    "zb": dict(machine=os.environ.get("ZEROBAS_BASIC_MACHINE",
                                      "C-BIOS_MSX1_EU_REPACK_DISK"),
               boot=8.0, step=2.5, reset=("NEW",)),
}
COLS, ROWS = 40, 24
UP = "\x1e"
PAY = "A=A+1:PRINT A"

CASES = [
    ("control.once", ['CLS', PAY],
     "executed once -> the counter reads 1"),
    ("reentry.up3", ['CLS', PAY, UP * 3],
     "cursor UP x3 back onto the typed line, Enter -> re-executed -> 2"),
    ("reentry.up3x2", ['CLS', PAY, UP * 3, UP * 3],
     "re-entered TWICE -> 3, so the row scales with the number of re-entries"),
]


def rows(scr):
    if scr is None:
        return None
    return [(r, scr[r * COLS:(r + 1) * COLS].rstrip())
            for r in range(ROWS) if scr[r * COLS:(r + 1) * COLS].strip()]


def main():
    res = {s: omsx_repl.run_cases(c["machine"], [("direct", l) for _, l, _ in CASES],
                                  batch=True, reset=c["reset"], boot=c["boot"],
                                  step=c["step"], verify_delivery=False)
           for s, c in SIDES.items()}
    for i, (label, lines, asks) in enumerate(CASES):
        print(f"\n=== {label} — {asks}")
        for side in SIDES:
            rr = rows(res[side][i])
            if rr is None:
                print(f"  {side:8s} <NO CAPTURE>")
                continue
            print(f"  {side:8s} " + " | ".join(f"r{r:02d}:{t}" for r, t in rr))
    return 0


if __name__ == "__main__":
    sys.exit(main())
