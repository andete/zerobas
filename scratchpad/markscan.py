#!/usr/bin/env python3
"""Which open blocks are unmarked, and which carry MORE THAN ONE marker."""
import re, sys
s = open("TODO.md").read()
marks = ("\U0001f916", "\U0001f52d", "\U0001f64b", "⛔")
off = 0
for b in re.split(r"\n(?=- \[[ x]\] )", s):
    ln = s[:s.index(b, off)].count("\n") + 1 if b in s[off:] else -1
    off = max(off, s.index(b, off) if b in s[off:] else off)
    if not b.startswith("- [ ] "):
        continue
    hit = [m for m in marks if re.search(r"^\s*" + m + r" ", b, re.M)]
    if len(hit) != 1:
        print(f"{'NONE' if not hit else 'MULTI ' + ''.join(hit)}  line {ln}: {b.splitlines()[0][:90]}")
