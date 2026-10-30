#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""prstr2x-acceptance (D-PRSTR2X): a PRINT item that starts as a string and has a
relational operator after it is evaluated ONCE.

Found by the program ladder's L2_keys: `LPRINT ...;INKEY$="";...` read two keys
on zerobas -- PRINT rewound to the item's start and ran it through `eval` again
(scratchpad/inkeycmp_measure.out). The VG-8020 reads one. Rows: INKEY$ and
INPUT$(1) compared inline (the key left over is read back by the next item), a
string variable / function / literal compared and combined with AND / OR, and a
plain numeric variable (the first cut of the fix made `PRINT T` a Type mismatch:
it fell through into the new block). Both zerobas targets against the VG-8020.

Clean-room: typed keys and a tape in; the printer port out.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "probes", "programs"))
import run_programs                                  # noqa: E402

PROG = "scratchpad/prstr2x_measure.bas"
ROWS = 7


def main():
    text = open(os.path.join(REPO, PROG)).read()
    ref = run_programs.run(run_programs.REF, "prstr2x", text)
    rl = ref[1].replace("\r", "").splitlines()
    print(f"{run_programs.REF:30} {ref[0]}  {len(rl)} rows")
    bad = 0
    for m in run_programs.ZB:
        zb = run_programs.run(m, "prstr2x", text)
        zl = zb[1].replace("\r", "").splitlines()
        diff = [(a, b) for a, b in zip(rl, zl) if a != b]
        ok = len(rl) == ROWS and zl == rl
        bad += not ok
        print(f"{m:30} {zb[0]}  {len(diff)} differ  {'SAME' if ok else 'DIVERGES'}")
        for a, b in diff:
            print(f"      ref {a!r}  zb {b!r}")
    print(f"\n{'PASS' if not bad else 'FAIL'}: a string item with a relop after it is read once, as on the VG-8020")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
