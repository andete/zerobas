#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-CSRSW -- does LOCATE's cursor switch have a READABLE cell after all?

`docs/decision-missing-class-slicing.md` O-3 proposed LOCATE's third argument be
"accepted-and-ignored, documented as a deviation", on this reasoning: *"nothing
in this tree reads CSRSW ($FCA9) or any equivalent, so there is no existing
mechanism for the argument to drive and storing it would be a write nobody
reads."*

🔴 THAT IS A CLAIM ABOUT OUR TREE, NOT ABOUT THE MACHINE, and the tier question
is a different one: does the REFERENCE leave something a row can read? If it
writes CSRSW then the cell is observable, matching it is what a faithful
reimplementation does, and "nobody reads it" describes a gap on our side rather
than a reason not to write it. The same sentence shape -- "no cell any row here
can read" -- was just measured false for SCREEN's key click (D-SCRCLICK).

METHOD, inherited from scratchpad/clicksw_probe.py: POKE a sentinel, run the
statement, PEEK back. The sentinel is the control -- a cell reading 0 after
`LOCATE ,,0` proves nothing unless it held 99 a moment earlier.
  ctrl.poke   POKE the sentinel and read it straight back. If the cell does not
              hold what BASIC writes, nothing below is a reading.
  cursor.off  sentinel, then `LOCATE ,,0`
  cursor.on   sentinel, then `LOCATE ,,1`
  cursor.two  sentinel, then `LOCATE ,,2` -- decides RAW vs normalised, the
              question that changed the code in D-SCRCLICK.
"""
from __future__ import annotations
import os, re, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

CSRSW = 0xFCA9           # the cursor-display switch
SENTINEL = 99
SIDES = {
    "vg8020": ("Philips_VG_8020", 14.0),
    "cf3300": ("National_CF-3300", 14.0),
    "zb":     ("C-BIOS_MSX1_EU_REPACK_DISK", 8.0),
}
# 🔴 `cursor.two` DECIDES THE IMPLEMENTATION, not just the blocker. If the
# reference stores 2 raw then the handler writes the byte through; if it stores 1
# (or refuses) the handler normalises. Guessing here is how a verb ends up
# "implemented" and still divergent on its second value.
CASES = [
    ("ctrl.poke", None),
    ("cursor.off", "LOCATE ,,0"),
    ("cursor.on",  "LOCATE ,,1"),
    ("cursor.two", "LOCATE ,,2"),
]


def prog(stmt):
    lines = [f"10 POKE {CSRSW},{SENTINEL}"]
    if stmt:
        lines.append(f"20 {stmt}")
    lines.append(f'30 PRINT"[";PEEK({CSRSW});"]"')
    lines.append("RUN")
    for ln in lines:
        if len(ln) > 38:
            raise SystemExit(f"REFUSE: {len(ln)} cols: {ln!r}")
    return lines


def main() -> int:
    print(f"CSRSW ${CSRSW:04X}, sentinel {SENTINEL}\n")
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
                  f"(both {off}) -- not the cursor cell, or LOCATE ignores it.")
        else:
            print(f"  {side}: 🎯 READABLE -- `LOCATE ,,0` -> {off}, "
                  f"`LOCATE ,,1` -> {on}, `LOCATE ,,2` -> {two}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
