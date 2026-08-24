#!/usr/bin/env python3
"""Peephole size-seam scout -- COUNT the 1-byte encoding wins in main-image source.

The user's example is the canonical one: `sla a` (CB 27, 2 B) does the same
LEFT SHIFT as `add a,a` (87, 1 B). The class is "an instruction with a smaller
encoding of the same DATA effect". It is orthogonal to every carve swept so far:
no routine moves, each hit is a local -1 B.

🔴 THE CATCH, STATED UP FRONT: these pairs are NOT flag-equivalent, so a hit is a
CANDIDATE, never a change. `add a,a` sets H and P/V as an ADD; `sla a` sets them
as a shift. `xor a` clobbers every flag; `ld a,0` clobbers none. A rewrite is
safe ONLY where the differing flags are dead before the next flag-writer -- which
this scan CANNOT decide (no flag-liveness here) and which zerobas's differential
is the authority on. So the deliverable is a NUMBER: is the seam 5 B or 150 B?

Scans SOURCE (mnemonics are visible and a fix lands here anyway), main image
only -- basic/*.asm + the .inc it includes. Comments stripped. Per class:
what it becomes, the byte saving, and which flags DIFFER (the safety question).
"""
from __future__ import annotations
import glob, re, os, collections
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# (regex on the stripped, lowercased mnemonic) -> (replacement, saved, flags-that-differ)
CLASSES = [
    (re.compile(r'^sla\s+a$'),        "add a,a",  1, "H, P/V (shift vs add)"),
    (re.compile(r'^rlc\s+a$'),        "rlca",     1, "S, Z, P/V (unchanged by rlca)"),
    (re.compile(r'^rrc\s+a$'),        "rrca",     1, "S, Z, P/V"),
    (re.compile(r'^rl\s+a$'),         "rla",      1, "S, Z, P/V"),
    (re.compile(r'^rr\s+a$'),         "rra",      1, "S, Z, P/V"),
    (re.compile(r'^ld\s+a\s*,\s*0$'), "xor a",    1, "ALL (xor a clobbers; ld a,0 preserves)"),
    (re.compile(r'^cp\s+0$'),         "or a",     1, "N (and H); Z/S/C identical"),
    (re.compile(r'^sub\s+a$'),        "xor a",    0, "-- same size, skip"),
]

hits = collections.defaultdict(list)
files = sorted(set(glob.glob("basic/*.asm")) | set(glob.glob("basic/*.inc")))
for f in files:
    for i, raw in enumerate(open(f, errors="ignore"), 1):
        code = raw.split(";", 1)[0]
        # drop a leading label, keep the instruction
        m = re.match(r'^\s*(?:[A-Za-z_]\w*:)?\s*(.*?)\s*$', code)
        insn = re.sub(r'\s+', ' ', m.group(1).strip().lower()) if m else ""
        if not insn:
            continue
        for rx, repl, saved, flags in CLASSES:
            if saved and rx.match(insn):
                hits[(rx.pattern, repl, saved, flags)].append(f"{f}:{i}")

total = 0
print(f"main-image source: {len(files)} files scanned\n")
for (pat, repl, saved, flags), locs in sorted(hits.items(), key=lambda x: -len(x[1])):
    ex = pat.replace(r'\s+', ' ').replace(r'\s*', '').replace('^','').replace('$','').replace('\\','')
    print(f"  {len(locs):3} x  {ex:12} -> {repl:9}  (-{saved} B each; DIFFERS: {flags})")
    for l in locs[:4]:
        print(f"          {l}")
    if len(locs) > 4:
        print(f"          ... +{len(locs)-4} more")
    total += len(locs) * saved
print(f"\n  ~{total} B nominal IF every hit were flag-safe -- which is the whole "
      f"question,\n  and this scan does NOT answer it. A CANDIDATE COUNT, not a carve.")
