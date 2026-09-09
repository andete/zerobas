#!/usr/bin/env python3
"""Loose rule (today's --count) vs a TIGHT rule that requires the bucket NAME."""
import re, json, subprocess, sys
BUCKETS = {"\U0001f916": "AUTONOMOUS", "\U0001f52d": "SCOUT-THEN-ASK",
           "\U0001f64b": "NEEDS-JOOST", "⛔": "BLOCKED"}
LOOSE = {m: re.compile(r"^\s*" + m + r" ", re.M) for m in BUCKETS}
TIGHT = {m: re.compile(r"^\s*" + m + r" \*{0,2}" + n + r"\*{0,2}[ ,]*[—:]", re.M)
         for m, n in BUCKETS.items()}
s = open("TODO.md").read()
blocks = [b for b in re.split(r"\n(?=- \[[ x]\] )", s) if b.startswith("- [ ] ")]
print("open blocks:", len(blocks))
dis = 0
for b in blocks:
    lo = {m for m, rx in LOOSE.items() if rx.search(b)}
    ti = {m for m, rx in TIGHT.items() if rx.search(b)}
    if lo != ti or len(ti) != 1:
        dis += 1
        ln = s[:s.index(b)].count("\n") + 1
        print(f"  line {ln:5d}  loose={''.join(sorted(lo)) or '-':8s} tight={''.join(sorted(ti)) or '-':8s}  {b.splitlines()[0][6:76]}")
print("blocks where the two rules disagree, or tight != exactly 1:", dis)
