#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-CSRLIN — is `CSRLIN` off by one, or is the filed excuse right?

`make kwsweep` reports exactly one DIVERGENT word and has for some time:

    PRINT:PRINT:PRINT"[";CSRLIN;"]"      ref '[ 4 ]'   zb '[ 3 ]'

TODO.md files it as NOT a defect — *"`CSRLIN` in a row with no `CLS`, where the
reference disagrees with itself across differently scrolled batches"*. That is a
justification nobody has run, and it is cheap to run
[[a-justification-parenthesis-is-an-unrun-claim]].

🎯 THE DECISIVE ROWS ARE THE `LOCATE` ONES, NOT THE `CLS` ONES. Adding `CLS`
only anchors the scroll state; if the excuse is right the disagreement goes away,
but a residual difference could still be blamed on where `CLS` leaves the cursor.
`LOCATE 0,n` SETS the row outright, so scroll history cannot enter: whatever
`CSRLIN` then reports is the function's own answer, and it must be `n` on any
machine that implements it. Two of them, at different rows, because a single one
cannot tell "off by one" from "always reports the same thing".

`c.nocls` reproduces the kwsweep row verbatim so this probe can be compared with
the sweep it is explaining, rather than only with itself.
"""
from __future__ import annotations

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl                                                  # noqa: E402

SIDES = {
    "vg8020": ("Philips_VG_8020", 8.0, ("NEW",)),
    "cf3300": ("National_CF-3300", 14.0, ("", "SCREEN 0", "NEW")),
    "zb": (os.environ.get("ZEROBAS_BASIC_MACHINE",
                          "C-BIOS_MSX1_EU_REPACK_DISK"), 8.0, ("NEW",)),
}

CASES = [
    ("c.nocls",  "REM",                "the kwsweep row VERBATIM (no CLS) -- the "
                                       "reading the filed excuse is about"),
    ("c.cls",    "CLS",                "CLS alone: where the cursor lands"),
    ("c.p1",     "CLS:PRINT",          "one newline past it"),
    ("a.p2",     "CLS:PRINT:PRINT",    "the kwsweep row, scroll-anchored by CLS"),
    ("d.loc5",   "CLS:LOCATE 0,5",     "🎯 DECISIVE: the row is SET, so scroll "
                                       "history cannot enter. Must read 5"),
    ("d.loc10",  "CLS:LOCATE 0,10",    "🎯 DECISIVE twin at a different row -- "
                                       "one row alone cannot tell an off-by-one "
                                       "from a constant"),
    ("d.loc0",   "CLS:LOCATE 0,0",     "the bottom of the domain; must read 0"),
]


def run(side, setup):
    machine, boot, reset = SIDES[side]
    prog = ['10 ON ERROR GOTO 90',
            f'20 {setup}',
            '30 PRINT"ZQ";CSRLIN;"QZ":END',
            '90 PRINT"ZQERR";ERR;"QZ":END',
            'RUN']
    raw = "".join(omsx_repl.run_cases(
        machine, [("direct", list(reset) + prog)], batch=False, reset=(),
        boot=boot, step=6.0, cap_gap=10.0, timeout=300.0)[0] or "")
    for m in re.finditer(r"ZQ(ERR)?\s*(-?\d+)\s*QZ", raw):
        return (f"ERR {int(m.group(2))}" if m.group(1)
                else str(int(m.group(2))))
    return "<NO READING>"


def main() -> int:
    rows = []
    for tag, setup, note in CASES:
        got = {s: run(s, setup) for s in SIDES}
        rows.append((tag, setup, note, got))
        print(f"  {tag:9s} " + "  ".join(f"{s}={got[s]:>4s}" for s in SIDES),
              flush=True)

    print(f"\n{'row':9s} {'vg8020':>7s} {'cf3300':>7s} {'zb':>5s}   verdict")
    dis, refsplit = [], []
    for tag, setup, note, got in rows:
        v, c, z = got["vg8020"], got["cf3300"], got["zb"]
        if v != c:
            verdict, _ = "REFS SPLIT", refsplit.append(tag)
        elif z != v:
            verdict, _ = "🔴 DIFF", dis.append(tag)
        else:
            verdict = "SAME"
        print(f"{tag:9s} {v:>7s} {c:>7s} {z:>5s}   {verdict}")
        print(f"          {setup}   -- {note}")
    print(f"\n=== {len(dis)} divergence(s): {dis or 'none'}"
          + (f"; {len(refsplit)} REFS-SPLIT: {refsplit}" if refsplit else "")
          + " ===")
    if refsplit and not dis:
        print("⚠️  A REFS-SPLIT row cannot score zerobas at all -- the two "
              "references disagree, so there is no single answer to match.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
