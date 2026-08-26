#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-EDITSCOUT step 1: LOOK AT THE SCREEN before designing any row.

A screen-editor characterisation has to aim cursor-up at a specific ROW, and the
two machines do not lay out a prompt the same way (zerobas prints "ZB", the
reference "Ok"). Guessing the offset would produce rows that miss their target
and read as "the editor did nothing" — the exact shape of a false negative. So
step 1 draws the screen and counts.
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


def draw(label, scr):
    print(f"--- {label} " + "-" * (60 - len(label)))
    if scr is None:
        print("    <NO CAPTURE>")
        return
    for r in range(ROWS):
        row = scr[r * COLS:(r + 1) * COLS].rstrip()
        if row:
            print(f"    r{r:02d} |{row}|")


def main():
    cases = [
        ("direct", ['PRINT"AAA"']),                    # C0 baseline layout
        ("direct", ['CLS', "\x1f\x1f\x1f", 'PRINT"Z"']),  # C1 cursor-DOWN x3
    ]
    for side, cfg in SIDES.items():
        print(f"\n================ {side} ================")
        outs = omsx_repl.run_cases(cfg["machine"], cases, batch=True,
                                   reset=cfg["reset"], boot=cfg["boot"],
                                   step=cfg["step"], verify_delivery=False)
        for (mode, lines), scr in zip(cases, outs):
            draw(f"{side}: {lines!r}", scr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
