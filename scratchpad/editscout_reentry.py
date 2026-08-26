#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-EDITSCOUT step 2: the two questions that decide where the editor can live.

Q1 RE-ENTRY (the feature): cursor UP onto an earlier line and press Enter — does
the reference re-read that line FROM THE SCREEN and execute it? That is the whole
screen editor, and it is a PER-ENTER act, not a per-keystroke one. If it is
per-Enter, its granularity is `lineedit_tenant`'s.

Q2 WHO MOVES THE CURSOR (the price): is cursor motion done by the BIOS CHPUT
(which C-BIOS supplies, so zerobas gets it for the cost of not dropping the byte)
or by the BASIC ROM's own editor (which zerobas would have to write)?
`PRINT CHR$(31);CHR$(31);"Z"` asks CHPUT directly, with no editor involved.

⚠️ EVERY PAYLOAD HERE IS CURSOR MOTION, SO DELIVERY CANNOT BE VERIFIED. The
harness says so itself — `verify_delivery` marks an unprintable payload
BLIND/unprintable, citing the `lnblank` TAB that the ROM renders as cursor
movement. So each question carries its own control whose consequence IS
printable, and no row is believed without it.
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
UP, DOWN = "\x1e", "\x1f"

# (label, mode, lines, what it asks)
CASES = [
    ("q1.control", "direct", ['CLS', 'PRINT"AAA"'],
     "baseline: ONE AAA on the screen, and the row layout re-entry aims at"),
    ("q1.reentry", "direct", ['CLS', 'PRINT"AAA"', UP * 3],
     "cursor UP x3 onto the typed line, then Enter -> a SECOND AAA?"),
    ("q1.short", "direct", ['CLS', 'PRINT"AAA"', UP * 1],
     "UP x1 lands on the 'Ok'/'ZB' row -- a wrong-row control: re-entering a "
     "PROMPT row must NOT print AAA, so a second AAA in q1.reentry cannot be "
     "'Enter re-runs whatever was last typed'"),
    ("q2.chput", "direct", ['CLS', 'PRINT CHR$(31);CHR$(31);"Z"'],
     "does CHPUT itself honour $1F? Z two rows below where it would sit"),
    ("q2.control", "direct", ['CLS', 'PRINT "Z"'],
     "same PRINT with no control bytes -- pins where Z sits WITHOUT motion"),
]


def rows(scr):
    if scr is None:
        return None
    return [(r, scr[r * COLS:(r + 1) * COLS].rstrip())
            for r in range(ROWS) if scr[r * COLS:(r + 1) * COLS].strip()]


def main():
    out = {}
    for side, cfg in SIDES.items():
        res = omsx_repl.run_cases(cfg["machine"],
                                  [(m, l) for _, m, l, _ in CASES],
                                  batch=True, reset=cfg["reset"],
                                  boot=cfg["boot"], step=cfg["step"],
                                  verify_delivery=False)
        out[side] = res
    for i, (label, _, lines, asks) in enumerate(CASES):
        print(f"\n=== {label} — {asks}")
        for side in SIDES:
            rr = rows(out[side][i])
            if rr is None:
                print(f"  {side:8s} <NO CAPTURE>")
                continue
            print(f"  {side:8s} " + " | ".join(f"r{r:02d}:{t}" for r, t in rr))
        for side in SIDES:
            rr = rows(out[side][i]) or []
            n = sum(t.count("AAA") for _, t in rr)
            print(f"    {side:8s} AAA occurrences on screen: {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
