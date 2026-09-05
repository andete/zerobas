#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-NTSEP — the row the PAINT item says is missing: what separates the rules.

TODO's SCREEN-2 `PAINT` item ends on a stated gap, and this builds exactly that
row and nothing else:

    "the first thing that slice must measure is NOT in hand: §4 says what the
     reference WRITES, not how its walk reaches a border row it can still see.
     **No row yet separates the candidate rules.**"

🎯 THE TWO RULES THAT FIT EVERY ROW MEASURED SO FAR.

  R-FLOOD  when `C != B` the walk ignores boundaries ALTOGETHER and fills to the
           screen edge, whatever is drawn. ("`C != B` floods everything.")
  R-BONLY  when `C != B` only pixels whose colour IS `B` stop being borders --
           because the fill writes `pattern := 0, bg := C` over the group and a
           B-coloured pixel in it ceases to read as B -- while a wall in ANY
           OTHER colour still bounds the fill.

Every fixture in `ntwall_probe.py` draws its wall in the SAME colour as `B`, so
both rules predict the identical answer on all 19 rows. That is why no row
separates them [[two-rules-that-coincide-on-every-row-you-have]].

🔴 THE SEPARATOR IS A SECOND WALL IN A THIRD COLOUR. Two horizontal walls below
the seed -- one in `B`, one in a colour that is neither `B` nor `C` -- and one
`PAINT`:

    SCREEN 2 : LINE(0,20)-(255,20),7 : LINE(0,40)-(255,40),15 : PAINT(128,8),9,7

  * R-FLOOD predicts 9 BELOW BOTH walls (y=41, and at (10,100)).
  * R-BONLY predicts 9 below the colour-7 wall (y=21..39) and NOT below the
    colour-4 one: y=41 and (10,100) stay 0.

⚠️ AND THE INVERSION IS PART OF THE MEASUREMENT, not a nicety. `sep.b15` repeats
the identical fixture with `B = 15`, so the two walls swap roles. Under R-BONLY
the fill must now stop at the colour-7 wall at y=20 and never reach y=39 at all.
A rule that only ever "explains" one arrangement is not a rule; if `sep.b7` and
`sep.b15` do not mirror each other, BOTH candidates are wrong and the finding is
that, rather than a fix.

🟢 CONTROLS. `sep.cb` is the same fixture with `C == B`, which the existing scout
already shows is bounded -- so a flood in `sep.b7` cannot be the fixture leaking.
`sep.noclr` samples with no PAINT at all, so "0 below the wall" is known to be
what an unfilled pixel reads rather than assumed.

⚠️ TIMING: a 256x192 SCREEN-2 flood needs step=90 (the scout's proven value); the
default fires mid-fill and reads a blank graphics screen.
"""
from __future__ import annotations

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl                                                  # noqa: E402

ZB_M = os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")
SIDES = {
    "vg8020": dict(machine="Philips_VG_8020", boot=8.0, reset=("NEW",)),
    "cf3300": dict(machine="National_CF-3300", boot=14.0,
                   reset=("", "SCREEN 0", "NEW")),
    "zb":     dict(machine=ZB_M, boot=8.0, reset=("NEW",)),
}
STEP = float(os.environ.get("NTS_STEP", "90"))
TMO = 900.0

# \U0001f534 ROUND 1 USED COLOUR 4 FOR THE SECOND WALL AND COLOUR 4 IS THE SCREEN-2
# BACKGROUND. `sep.noclr` -- the control that reads an unpainted pixel -- returned
# 4 everywhere, which is exactly what says the "third colour" was not a third
# colour at all: the second wall was INVISIBLE, drawn in the ground it stood on.
# zerobas's `sep.b4` then AGREED with the references for a reason that had
# nothing to do with the rule under test [[a-case-that-agrees-can-agree-for-the-
# wrong-reason]]. Round 2 uses 15, and `sep.noclr` stays because it is the row
# that caught it.
TWO_WALLS = "SCREEN 2:LINE(0,20)-(255,20),7:LINE(0,40)-(255,40),15"
# Samples: above wall A, between the walls (x3), just above/below wall B, and
# far below. "Between" is sampled three times because a walk that crosses wall A
# and then stops has to be seen to have FILLED that band, not merely to have
# entered it.
PTS = [(50, 19), (50, 21), (50, 30), (50, 39), (50, 41), (10, 100)]

CASES = {
    # \U0001f3af THE SEPARATOR.
    "sep.b7":  ([TWO_WALLS, "PAINT(128,8),9,7"], PTS),
    # \U0001f3af THE INVERSION -- the same walls, the roles swapped.
    "sep.b15": ([TWO_WALLS, "PAINT(128,8),9,15"], PTS),
    # \U0001f7e2 C == B: bounded at the first wall on all three, per the scout's `cb`.
    "sep.cb":  ([TWO_WALLS, "PAINT(128,8),7,7"], PTS),
    # \U0001f7e2 no PAINT at all: what an unfilled pixel reads, measured not assumed.
    "sep.noclr": ([TWO_WALLS], PTS),
}

ERR = re.compile(r"^\s*([A-Z][A-Za-z' ]+ error|Illegal function call|Overflow|"
                 r"Out of memory|Type mismatch|Subscript out of range)", re.M)


def read(cap, n):
    if cap is None:
        return "<NO CAPTURE>"
    txt = " ".join("".join(cap).split())
    m = re.search(r"R((?:\s*-?\d+){%d})" % n, txt)
    if m:
        return [int(v) for v in m.group(1).split()]
    e = ERR.search(txt)
    return f"<{e.group(1).strip()}>" if e else "<NO OUTPUT>"


def prog(setup, pts):
    q = ":".join(f"{chr(65 + i)}=POINT({x},{y})" for i, (x, y) in enumerate(pts))
    pr = ('SCREEN0:PRINT"R";'
          + ";".join(chr(65 + i) for i in range(len(pts))) + ":END")
    return [f"{20 + 10 * k} {ln}" for k, ln in enumerate(list(setup) + [q, pr])]


def main() -> int:
    want = sys.argv[1:] or list(CASES)
    hdr = "  ".join(f"({x},{y})" for x, y in PTS)
    print(f"\nsamples: {hdr}\n"
          f"         wall7@y=20   wall15@y=40   seed (128,8)\n")
    rows = {}
    blind = 0
    for label in want:
        setup, pts = CASES[label]
        body = ["10 ON ERROR GOTO 900"] + prog(setup, pts)
        body += ['900 SCREEN 0:PRINT"[ERR";ERR;"]":END']
        for side, cfg in SIDES.items():
            caps = omsx_repl.run_cases(
                cfg["machine"], [("direct", list(cfg["reset"]) + body + ["RUN"])],
                batch=False, boot=cfg["boot"], step=STEP, cap_gap=10.0,
                timeout=TMO)
            v = read(caps[0], len(pts))
            rows[(label, side)] = v
            blind += not isinstance(v, list)
            print(f"  {label:10s} {side:7s} {v}", flush=True)
        print(flush=True)

    # \U0001f534 A RUN THAT COULD NOT READ IS NOT A RUN THAT AGREED.
    if blind:
        print(f"\U0001f534 INSTRUMENT FAULT: {blind} cell(s) produced no list of "
              f"POINT values. A 256x192 flood needs a big step; raise NTS_STEP "
              f"and re-run. Refused.")
        return 2

    print("=== verdict ===")
    for label in want:
        v, c, z = (rows[(label, s)] for s in ("vg8020", "cf3300", "zb"))
        tag = "refs agree" if v == c else "\U0001f534 REFS SPLIT"
        print(f"  {label:10s} refs={v}  zb={z}   {tag}"
              + ("" if c == z else "   \U0001f534 zb DIFF"))
    if "sep.b7" in want and "sep.b15" in want:
        b7 = rows[("sep.b7", "vg8020")]
        b4 = rows[("sep.b15", "vg8020")]
        # index 4 is (50,41) -- below the SECOND wall; index 5 is (10,100).
        below2_b7 = b7[4] == 9 and b7[5] == 9
        print("\n\U0001f3af SEPARATOR READS (reference):")
        print(f"    sep.b7 below the colour-4 wall: (50,41)={b7[4]} "
              f"(10,100)={b7[5]}")
        print(f"    sep.b15 below the colour-7 wall: (50,41)={b4[4]} "
              f"(10,100)={b4[5]}")
        print("    R-FLOOD predicts 9 below BOTH walls in BOTH cases.")
        print("    R-BONLY predicts the fill stops at the wall whose colour is "
              "NOT B.")
        print(f"    -> reads as {'R-FLOOD' if below2_b7 else 'R-BONLY'} on b7; "
              f"the b15 inversion is what confirms or refutes that.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
