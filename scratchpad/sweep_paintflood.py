#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""TODO sweep 2026-08-26 — T131 (SCREEN-2 PAINT flood) ISOLATED.

⚠️ THIS ROW MAY NOT SHARE A BATCH. The item's own claim is that the references
FLOOD THE ENTIRE SCREEN, and a full-screen SCREEN-2 flood fill does not finish
inside the batch `step`. In tranche 1 both references returned NO span for this
case while the no-PAINT control returned 4 on all three sides — i.e. the row read
as "the references printed nothing", which is the `<NO OUTPUT>`-means-two-things
trap, not a divergence.

So: one boot per case, a long step, and a control on the SAME apparatus.
"""
import os
import sys

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "probes", "lib"))
import omsx_repl                                                  # noqa: E402
import probe_tmp                                                  # noqa: E402

SIDES = {
    "vg8020": dict(machine="Philips_VG_8020", boot=8.0, reset=("NEW", "CLS")),
    "cf3300": dict(machine="National_CF-3300", boot=14.0,
                   reset=("", "SCREEN 0", "NEW", "CLS")),
    "zb": dict(machine=os.environ.get("ZEROBAS_BASIC_MACHINE",
                                      "C-BIOS_MSX1_EU_REPACK_DISK"),
               boot=8.0, reset=("NEW", "CLS")),
}
COLS, ROWS = 40, 24
WALL = 'SCREEN 2:LINE(0,20)-(255,20),7'
CASES = [
    ("paint", [f'{WALL}:PAINT(128,8),9,7:P=POINT(50,21):SCREEN 0:PRINT"[";P;"]"']),
    ("control.nopaint", [f'{WALL}:P=POINT(50,21):SCREEN 0:PRINT"[";P;"]"']),
    ("control.above", [f'{WALL}:PAINT(128,8),9,7:P=POINT(50,8):SCREEN 0:PRINT"[";P;"]"']),
]


def spans(scr):
    if scr is None:
        return None
    flat = " ".join(scr[r * COLS:(r + 1) * COLS].rstrip() for r in range(ROWS))
    out, i = [], 0
    while (a := flat.find("[", i)) >= 0 and (b := flat.find("]", a)) >= 0:
        out.append(flat[a + 1:b].strip()); i = b + 1
    return out


def main():
    step = float(os.environ.get("STEP", "25.0"))
    for label, lines in CASES:
        print(f"\n=== {label}   (step={step}s, one boot per case)")
        for side, cfg in SIDES.items():
            scr = omsx_repl.run_case(cfg["machine"], "direct", lines,
                                     boot=cfg["boot"], step=step)
            sp = spans(scr)
            rows = [scr[r * COLS:(r + 1) * COLS].rstrip()
                    for r in range(ROWS)] if scr else []
            err = [r for r in rows if "rror" in r]
            print(f"  {side:8s} spans={sp}" + (f"  ERRORS={err}" if err else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
