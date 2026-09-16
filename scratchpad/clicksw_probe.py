#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-CLIKSW -- does SCREEN's key-click parameter have a READABLE cell after all?

TODO.md files `SCREEN` at 2/3 with "key-click has no cell any row here can read".
That is an INSTRUMENT claim, and this tree's record on those is twelve re-verified
and twelve stale -- so it gets asked rather than inherited.

THE CANDIDATE IS PUBLISHED, NOT GUESSED: CLIKSW $F3DB, the keyboard-click switch
in the MSX work area (MSX2 Technical Handbook work-area table, the same published
list basic/sysvars.inc already names dozens of cells from). If `SCREEN ,,0` and
`SCREEN ,,1` move it on the references, the blocker is dead and `screenkw` can
have its third form.

🔴 THE CONTROL IS THE POINT. A cell that reads 0 after `SCREEN ,,0` proves nothing
on its own -- it may have been 0 already, or always be 0. So each side is POKEd to
a sentinel FIRST, and both settings are asked:
  ctrl.poke   POKE the sentinel and read it straight back. If the cell does not
              even hold what BASIC writes, nothing below is a reading.
  click.off   sentinel, then `SCREEN ,,0` -> expect 0
  click.on    sentinel, then `SCREEN ,,1` -> expect 1
A cell that ends up 0 in BOTH is not the click cell; a cell that keeps the
sentinel in both was never written by SCREEN at all.
"""
from __future__ import annotations
import os, re, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

CLIKSW = 0xF3DB
SENTINEL = 99
SIDES = {
    "vg8020": ("Philips_VG_8020", 14.0),
    "cf3300": ("National_CF-3300", 14.0),
    "zb":     ("C-BIOS_MSX1_EU_REPACK_DISK", 8.0),
}
# 🔴 `click.two` DECIDES THE IMPLEMENTATION, not just the blocker. If the
# reference stores 2 raw then the handler writes the byte through; if it stores 1
# (or refuses) the handler normalises. Guessing here is how a verb ends up
# "implemented" and still divergent on its second value.
CASES = [
    ("ctrl.poke", None),
    ("click.off", "SCREEN ,,0"),
    ("click.on",  "SCREEN ,,1"),
    ("click.two", "SCREEN ,,2"),
]


def prog(stmt):
    lines = [f"10 POKE {CLIKSW},{SENTINEL}"]
    if stmt:
        lines.append(f"20 {stmt}")
    lines.append(f'30 PRINT"[";PEEK({CLIKSW});"]"')
    lines.append("RUN")
    for ln in lines:
        if len(ln) > 38:
            raise SystemExit(f"REFUSE: {len(ln)} cols: {ln!r}")
    return lines


def main() -> int:
    print(f"CLIKSW ${CLIKSW:04X}, sentinel {SENTINEL}\n")
    print(f"{'side':8s} " + " ".join(f"{n:>10s}" for n, _ in CASES))
    out = {}
    for side, (machine, boot) in SIDES.items():
        caps = omsx_repl.run_cases(machine, [(n, prog(s)) for n, s in CASES],
                                   batch=False, boot=boot, reset=("", "SCREEN 0"),
                                   cap_gap=30.0, timeout=1800.0)
        vals = []
        for cap in caps:
            m = re.search(r"\[\s*(-?\d+)\s*\]", cap or "")
            vals.append(int(m.group(1)) if m else None)
        out[side] = vals
        print(f"{side:8s} " + " ".join(f"{str(v):>10s}" for v in vals))

    print()
    for side, vals in out.items():
        ctrl, off, on = vals[0], vals[1], vals[2]
        two = vals[3]
        if ctrl != SENTINEL:
            print(f"  {side}: 🔴 INSTRUMENT FAULT -- the cell does not hold what "
                  f"BASIC poked ({ctrl}); nothing else on this side is a reading.")
        elif off == on:
            print(f"  {side}: the cell does NOT distinguish the two settings "
                  f"(both {off}) -- not the click cell, or SCREEN ignores the arg.")
        else:
            print(f"  {side}: 🎯 READABLE -- `SCREEN ,,0` -> {off}, "
                  f"`SCREEN ,,1` -> {on}, `SCREEN ,,2` -> {two}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
