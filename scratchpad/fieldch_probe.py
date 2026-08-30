#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-FIELDCH — the filed `FIELD #(A$<5)` divergence is NOT ONE. The reference
side was void.

`TODO.md` carried, filed 2026-08-09 by D-STMTPEND:

  `FIELD #(A$<5),1 AS Z$` IS `Type mismatch` HERE AND `Illegal function call`
  ON THE VG-8020 ... the reference evidently classifies the CHANNEL before it
  classifies the expression, i.e. the opposite order from fch_check's.

🔴 THE VG-8020 IS DISKLESS AND HAS NO `FIELD` AT ALL. It answers `Illegal
function call` to EVERY row here -- including `ctl.notopen`, a perfectly ordinary
`FIELD #1,1 AS Z$`. It is not an oracle for this statement, and the filed row
compared zerobas against a machine that cannot express the question. Other disk
items in that file carry the caveat verbatim ("ONE REFERENCE (Disk BASIC; a
diskless VG-8020 cannot express it)"); this one lacked it.

🟢 AGAINST THE MACHINE THAT CAN EXPRESS IT, ZEROBAS AGREES ON EVERY ROW.
And the rows go beyond the single filed case, because "the channel is classified
before the expression" is a claim about an ORDER and one row cannot show an
order. The cheaper rule the filed note never tested: a comparison yields -1 or 0,
and BOTH are illegal channel numbers -- so `#(1<2)` would raise ERR 5 with no
ordering rule involved at all. It does, on both machines, and so does a bare
`#-1`; `#(2<1)` and `#0` both give `File not open`. The type error and the
channel-domain error are simply different rows.
"""
from __future__ import annotations
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "basic"))
import basic_probe_fldwidth as F                                  # noqa: E402

OK = 'PRINT"[";"OK";"]"'
A = 'A$="AB"'
CASES = [
    ("c.filed",     "run", [A, 'FIELD #(A$<5),1 AS Z$', OK]),
    ("c.rev",       "run", [A, 'FIELD #(5<A$),1 AS Z$', OK]),
    ("c.cmptrue",   "run", [A, 'FIELD #(1<2),1 AS Z$', OK]),
    ("c.cmpfals",   "run", [A, 'FIELD #(2<1),1 AS Z$', OK]),
    ("c.neg1",      "run", [A, 'FIELD #-1,1 AS Z$', OK]),
    ("c.zero",      "run", [A, 'FIELD #0,1 AS Z$', OK]),
    ("c.strch",     "run", [A, 'FIELD #A$,1 AS Z$', OK]),
    ("ctl.notopen", "run", [A, 'FIELD #1,1 AS Z$', OK]),
    ("ctl.plain",   "run", [A, 'PRINT"[";"OK";"]"']),
]
F.CASES = CASES
sides = (sys.argv[1] if len(sys.argv) > 1 else "vg8020,cf3300,zb").split(",")
res = {s: F.run_side(s, []) for s in sides}
w = max(len(l) for l, _, _ in CASES)
print(f"{'row':<{w}}  " + "  ".join(f"{s:>24}" for s in sides))
diff = []
for label, _, _ in CASES:
    zb = str(res["zb"].get(label)) if "zb" in res else "-"
    cf = str(res["cf3300"].get(label)) if "cf3300" in res else None
    if cf is not None and cf != zb:
        diff.append(label)
    print(f"{label:<{w}}  " + "  ".join(f"{str(res[s].get(label)):>24}" for s in sides)
          + ("   DIFF" if label in diff else "   SAME"))
print(f"\nDIFF vs the CF-3300: {len(diff)}/{len(CASES)}  " + " ".join(diff))
print("⚠️  THE VG-8020 COLUMN IS NOT AN ORACLE HERE: it is diskless, has no FIELD,\n"
      "   and answers `Illegal function call` to every row INCLUDING ctl.notopen,\n"
      "   an ordinary well-formed FIELD. That is what the filed divergence was.")
