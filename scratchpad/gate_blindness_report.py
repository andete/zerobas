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

🔴 A ROW CAN ALSO BE MISSING FROM A MUTANT'S LOG, WHICH IS NOT THE SAME AS GREEN
UNDER IT. Round 1 ran against a 355-row gate; D-GATEBLIND then split `clip_noop`
into two rows, so the 356-row baseline carries two rows the round-1 logs never
contained. Counting those as "no mutation could redden it" would be the same
lossy direction the parser bug had -- it makes the gate look better than it is.
Every never-reddened row is therefore printed with the number of battery members
that ACTUALLY MEASURED it, and any row measured by fewer than all of them is
called out.

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
    measured = collections.Counter()        # how many mutants CONTAINED the row
    per_mut, battery = {}, []
    for lg in logs:
        name = re.sub(r".*/mut_(.*)_gate\.log", r"\1", lg)
        rows = parse(lg)
        red = [k for k, ok in rows.items() if not ok]
        battery.append(name)
        per_mut[name] = red
        for k in rows:
            measured[k] += 1
        for k in red:
            reddened[k].append(name)
        print(f"  {name:12} rows {len(rows):4d}  RED {len(red):4d}"
              f"{'' if len(rows) == len(baseline) else '   ⚠️ row set differs'}")

    def fmt(k):
        ph, lb, n = k
        return f"{ph}/{lb}" + ("" if n == 1 else f"#{n}")

    if "--per-mut" in sys.argv:
        print("\n=== what each mutation reddened (score the predictions here) ===")
        for name in battery:
            byph = collections.defaultdict(list)
            for k in per_mut[name]:
                byph[k[0]].append(k[1] if k[2] == 1 else f"{k[1]}#{k[2]}")
            print(f"\n  {name} ({len(per_mut[name])} rows)")
            for ph in sorted(byph):
                print(f"    {ph:3} {', '.join(sorted(byph[ph]))}")

    never = [k for k in baseline if k not in reddened]
    print(f"\n=== battery {len(battery)}: "
          f"{len(baseline) - len(never)} of {len(baseline)} rows reddened, "
          f"{len(never)} NEVER ===")
    print("\n⚠️ 'NEVER' means blind TO THIS BATTERY AND NOTHING MORE. The output")
    print("   is a candidate roster to re-derive by hand, not a verdict.")
    partial = sorted((k for k in never if measured[k] < len(battery)), key=fmt)
    if partial:
        print(f"\n🔴 {len(partial)} never-reddened row(s) were NOT PRESENT in every")
        print("   mutant's log -- they were not measured by the whole battery, which")
        print("   is a weaker claim than the rest of the roster:")
        for k in partial:
            print(f"      {fmt(k)}  measured by {measured[k]}/{len(battery)}")
    print()
    byphase = collections.defaultdict(list)
    for ph, lb, n in never:
        byphase[ph].append(lb if n == 1 else f"{lb}#{n}")
    for ph in sorted(byphase):
        print(f"  --- {ph} ({len(byphase[ph])}) ---")
        print("      " + ", ".join(sorted(byphase[ph])))

    with open(OUT, "w") as f:
        json.dump({"battery": battery,
                   "never": [list(k) for k in never],
                   "measured": {"|".join(map(str, k)): measured[k]
                                for k in baseline},
                   "reddened": {"|".join(map(str, k)): v
                                for k, v in reddened.items()}}, f, indent=1)
    print(f"\n-> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
