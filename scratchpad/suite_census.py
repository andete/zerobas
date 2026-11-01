#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-SUITESWEEP, step 1: which gate suites have EVER gone red -- a census of the
recorded runs, at zero emulator cost.

Joost, 2026-11-01: "I have a feeling 90% of our test suite is wasted time" (and
yes to a mutation sweep). Before planting anything, read what the tree already
holds: every scratchpad/*.out that a gate run wrote (`GATES:` in it) lists each
suite's rc and seconds. A suite that went red and came back green on its serial
retry is a FLAKE, not a catch. Second pass: any `make: *** [<suite>] Error` in
ANY scratchpad output (knife and iteration runs go through single make targets
and never write a GATES line).

⚠️ The output is a CANDIDATE list, not a verdict, for three reasons:
  * the saved logs are the runs someone kept -- a suite that is fixed before its
    gate ever runs red looks never-red here;
  * some knife scripts print their own "red rows" lines instead of failing through
    make, which this scan does not see;
  * never red can mean "guards something nobody broke lately", not "blind".
Step 2 (the mutation sweep) plants a knife in each candidate's subject and asks
whether IT, only another suite, or nothing goes red.

    python3 scratchpad/suite_census.py [--min-runs 20] [--top 40]
"""
import argparse
import collections
import glob
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ROW = re.compile(r"^\s+rc=(\d+)\s+(\d+)s\s+(\S+)\s*$")
MAKE_ERR = re.compile(r"make: \*\*\* \[([A-Za-z0-9#/_.-]+)\] Error")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-runs", type=int, default=20)
    ap.add_argument("--top", type=int, default=40)
    a = ap.parse_args()
    runs, red = collections.Counter(), collections.Counter()
    secs = collections.defaultdict(list)
    caught, where = collections.Counter(), collections.defaultdict(set)
    nlogs = 0
    for f in sorted(glob.glob(os.path.join(HERE, "*.out"))):
        try:
            txt = open(f, errors="replace").read()
        except OSError:
            continue
        for m in MAKE_ERR.finditer(txt):
            caught[m.group(1)] += 1
            where[m.group(1)].add(os.path.basename(f))
        if "GATES:" not in txt:
            continue
        nlogs += 1
        seen = {}
        for ln in txt.splitlines():
            m = ROW.match(ln)
            if m:
                s = m.group(3)
                secs[s].append(int(m.group(2)))
                seen[s] = max(seen.get(s, 0), int(m.group(1)) != 0)
        for s, r in seen.items():
            runs[s] += 1
            if r and not re.search(r"retry %s: rc \d+->0" % re.escape(s), txt):
                red[s] += 1
    avg = {s: sum(v) / len(v) for s, v in secs.items()}
    pool = [s for s in runs if runs[s] >= a.min_runs]
    never = [s for s in pool if red[s] == 0]
    tot = sum(avg[s] for s in pool)
    tot_never = sum(avg[s] for s in never)
    print(f"gate logs read: {nlogs}; suites with >= {a.min_runs} logged runs: {len(pool)}")
    if not pool or tot == 0:
        print("NO DATA -- refusing to rank (an empty census is not 'nothing is wasted')")
        return 2
    print(f"never red in a logged gate run: {len(never)} suites, "
          f"{tot_never:.0f} of {tot:.0f} summed avg seconds ({100 * tot_never / tot:.0f}%)")
    print(f"\nNEVER RED IN A GATE RUN, most expensive first (top {a.top}): avg s, runs, "
          "red elsewhere (knife / iteration logs)")
    for s in sorted(never, key=lambda s: -avg[s])[:a.top]:
        other = f"{caught[s]} log(s), e.g. {sorted(where[s])[0]}" if caught[s] else "NONE"
        print(f"  {avg[s]:6.0f}s {runs[s]:5d}  {s:30s} {other}")
    print("\nRED IN A GATE RUN AT LEAST ONCE (red / runs):")
    for s in sorted(pool, key=lambda s: -red[s]):
        if red[s]:
            print(f"  {red[s]:4d}/{runs[s]:<5d} {s}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
