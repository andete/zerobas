#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-DEVBARE — the `FOR` clause is OPTIONAL on a device channel.

`basic/files.asm`'s device arm read `jr nz,oo_fail_syn ; device channels require
FOR OUTPUT`, and the comment asserted a rule the reference does not have.

🔴 FOUND BY A CONTROL THAT FAILED. `OPEN"LPT:"AS #1` was the baseline of a
D-OPEN2 discriminator run -- device-vs-disk -- and it was RED, which voided the
whole run before anyone noticed. The re-run with `FOR OUTPUT` is what produced
the D-OPEN2 table; this probe is the divergence that broke the first one.
[[classify-a-control-failure-by-which-side-failed-it]]

🟢 `LEN=` STAYS REFUSED, AND BY BOTH: `OPEN"CRT:"AS #1 LEN=128` is `Syntax error`
on the CF-3300 too (w.crtlen). The fix is a jump-target change, so the terminator
check after the channel parse still rejects it -- ZERO bytes, and the row proves
the refusal survived rather than assuming it.

⚠️ `FOR INPUT` ON A DEVICE IS DELIBERATELY NOT COPIED. The reference answers
`<NO OUTPUT>` -- the program dies or hangs -- and a hang is not a behaviour to
reproduce. zerobas keeps refusing it, and the rows record the divergence rather
than hiding it.
"""
from __future__ import annotations
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "basic"))
import basic_probe_fldwidth as F                                  # noqa: E402

OK = 'PRINT"[";"OK";"]"'
CASES = [
    ("w.forout",   "dsk", ['OPEN"CRT:"FOR OUTPUT AS #1', 'PRINT#1,"x"', OK]),
    ("w.crtbare",  "dsk", ['OPEN"CRT:"AS #1', OK]),
    ("w.crtwrite", "dsk", ['OPEN"CRT:"AS #1', 'PRINT#1,"x"', OK]),
    ("w.crtclose", "dsk", ['OPEN"CRT:"AS #1', 'PRINT#1,"x"', 'CLOSE#1', OK]),
    ("w.lptbare",  "dsk", ['OPEN"LPT:"AS #1', OK]),
    ("w.crtlen",   "dsk", ['OPEN"CRT:"AS #1 LEN=128', OK]),
    ("w.crtin",    "dsk", ['OPEN"CRT:"FOR INPUT AS #1', OK]),
    ("w.lptin",    "dsk", ['OPEN"LPT:"FOR INPUT AS #1', OK]),
]
F.CASES = CASES
sides = (sys.argv[1] if len(sys.argv) > 1 else "cf3300,zb").split(",")
res = {s: F.run_side(s, []) for s in sides}
w = max(len(l) for l, _, _ in CASES)
print(f"{'row':<{w}}  " + "  ".join(f"{s:>18}" for s in sides))
diff = []
for label, _, _ in CASES:
    vals = [str(res[s].get(label)) for s in sides]
    same = len(set(vals)) == 1
    if not same:
        diff.append(label)
    print(f"{label:<{w}}  " + "  ".join(f"{v:>18}" for v in vals)
          + f"   {'SAME' if same else 'DIFF'}")
print(f"\nDIFF: {len(diff)}/{len(CASES)}  " + " ".join(diff))
print("🎯 EXPECTED DIFF after the fix: w.crtin and w.lptin ONLY -- the reference"
      "\n   HANGS there and zerobas refuses, which is the divergence we keep.")
