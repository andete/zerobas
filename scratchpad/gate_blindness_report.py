#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-GATEBLIND -- aggregate the sweep, with a parser that does NOT lose rows.

🔴 THE SWEEP'S OWN PARSER WAS LOSSY AND IT WAS CAUGHT BEFORE ITS OUTPUT WAS
BELIEVED. Keying rows by bare label collapses 355 gate lines into 349: `scr0_err`
appears in three phases, `colour16_err` and `after` in two, and phase Q prints
`PASS <machine> <label>` so `Philips` and `C-BIOS` get captured AS the label.
A merged label counts as reddened if ANY instance reddens, so a genuinely blind
instance hides behind a live sibling with the same name -- the aggregate would
have made the gate look BETTER than it is, which is the direction that matters.

This re-derives everything from the RAW gate logs the sweep saved, keying each
row by (phase, label, occurrence-within-phase). No emulator time is re-spent.

    python3 -u scratchpad/gate_blindness_report.py <baseline.log> [muts...]
"""
from __future__ import annotations

import collections
import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "gate_blindness.json")

PHASE = re.compile(r"^=== PHASE ([^:]+)")
ROW = re.compile(r"^\s+(PASS|FAIL)\s+(.*)$")


def parse(path):
    """-> {(phase, label, nth): passed}. Keeps every one of the 355 lines."""
    phase, seen, out = "?", collections.Counter(), {}
    for line in open(path, errors="replace"):
        m = PHASE.match(line)
        if m:
            phase = m.group(1).strip()
            continue
        m = ROW.match(line)
        if not m:
            continue
        rest = m.group(2).split()
        # phase Q prints `PASS <machine> <label> ...`; everything else prints
        # `PASS <label> ...`. Machine names are the only tokens with a dash.
        label = rest[0]
        if label in ("Philips", "C-BIOS") and len(rest) > 1:
            label = f"{label}/{rest[1]}"
        seen[(phase, label)] += 1
        out[(phase, label, seen[(phase, label)])] = m.group(1) == "PASS"
    return out


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    if not args:
        print("usage: gate_blindness_report.py <baseline.log> [mutant.log ...]")
        return 2
    baseline = parse(args[0])
    logs = args[1:] or sorted(glob.glob("/tmp/mut_*_gate.log"))
    print(f"=== D-GATEBLIND aggregate ===")
    print(f"  baseline rows (phase,label,nth): {len(baseline)}")
    green0 = [k for k, v in baseline.items() if not v]
    if green0:
        print(f"  🔴 baseline is NOT clean: {len(green0)} already failing")

    reddened = collections.defaultdict(list)
    battery = []
    for lg in logs:
        name = re.sub(r".*/mut_(.*)_gate\.log", r"\1", lg)
        rows = parse(lg)
        red = [k for k, ok in rows.items() if not ok]
        battery.append(name)
        for k in red:
            reddened[k].append(name)
        print(f"  {name:11} rows {len(rows):4d}  RED {len(red):4d}")

    never = [k for k in baseline if k not in reddened]
    print(f"\n=== battery {len(battery)}: "
          f"{len(baseline) - len(never)} of {len(baseline)} rows reddened, "
          f"{len(never)} NEVER ===")
    print("\n⚠️ 'NEVER' means blind TO THIS BATTERY, which mutates the pixel,")
    print("   clamp, line and colour paths only. A sprite, PAINT, cassette or")
    print("   error-surface row is EXPECTED here. This is a candidate roster to")
    print("   re-derive by hand, not a verdict.\n")
    byphase = collections.defaultdict(list)
    for ph, lb, n in never:
        byphase[ph].append(lb if n == 1 else f"{lb}#{n}")
    for ph in sorted(byphase):
        print(f"  --- {ph} ({len(byphase[ph])}) ---")
        print("      " + ", ".join(sorted(byphase[ph])))

    with open(OUT, "w") as f:
        json.dump({"battery": battery,
                   "never": [list(k) for k in never],
                   "reddened": {"|".join(map(str, k)): v
                                for k, v in reddened.items()}}, f, indent=1)
    print(f"\n-> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
