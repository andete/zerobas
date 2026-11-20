#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-SCANRSAVE / D-NTMSXPCLASH (Joost 2026-11-20: "measure how reference does it ram-wise
and match"): the UNION of every work-area cell the reference writes across all of kwram's
rows -- each row's window, plus the background and interrupt controls (those are writes
too) -- from probes/basic/basic_probe_kwram.py's own measure / controls / side, the
reference side only (its readings replay from the reference cache). Black box: write
watchpoints over RAM, no ROM byte read.
    python3 scratchpad/refwrites_union.py > scratchpad/REFWRITES_union.out"""
import json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "basic")); sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import basic_probe_kwram as K  # noqa: E402
kt = K.kt

rows = K.rows_for(None)
rows = [r for r in rows if not any(len(l) > kt.MAX_TYPED for l in K.case_lines(K.omsx_repl.as_stored(r[1]), 0))]
union, per = set(), {}
for group, refm in K.GROUPS:
    grows = [r for r in rows if kt.GROUP[r[0]] == group]
    for c0 in range(0, len(grows), K.CHUNK):
        ch = grows[c0:c0 + K.CHUNK]
        bodies = [K.omsx_repl.as_stored(r[1]) for r in ch]
        res, caps = K.measure(refm, bodies, kt.group_kwargs(group, refm))
        bg, isr = K.controls(res, caps, f"{group} ref")
        union |= set(bg) | set(isr)
        for j, r in enumerate(ch):
            s = K.side(res.get(j + 3), caps, j + 3, set(), set())   # nothing subtracted: every write
            per[r[0]] = sorted(s["cells"])
            union |= s["cells"]
std = sorted(a for a in union if 0xF380 <= a <= 0xFFFE)
print(f"refwrites: {len(rows)} rows; the reference wrote {len(std)} distinct cells in $F380-$FFFE")
# the longest runs the reference NEVER wrote, in $F380-$FFFE
runs, a = [], 0xF380
while a <= 0xFFFE:
    if a in union: a += 1; continue
    b = a
    while b + 1 <= 0xFFFE and b + 1 not in union: b += 1
    runs.append((b - a + 1, a, b)); a = b + 1
for n, a, b in sorted(runs, reverse=True)[:25]:
    print(f"  never written: ${a:04X}-${b:04X} ({n} B)")
json.dump({"union": std, "rows": per}, open(os.path.join(ROOT, "scratchpad", "REFWRITES_union.json"), "w"))
