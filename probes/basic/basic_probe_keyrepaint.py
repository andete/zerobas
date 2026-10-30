#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""keyrepaint-acceptance (D-KEYREPAINT): `KEY n,"..."` repaints the function-key
row at once when it is shown.

Found by the program ladder's L2_keys: after KEY ON, `KEY 1,"LIST"+CHR$(13)`
left the old `color` on the bottom row on zerobas; the VG-8020 shows the new
text immediately. Rows read the row back by VPEEK: SCREEN 0 and SCREEN 1 with
the row on, KEY OFF (nothing painted), SCREEN 2 with the line on (nothing
painted into the pattern table: the sum stays 0), and the defaults restored.
Both zerobas targets against the VG-8020.

Clean-room: a tape in; the printer port out.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "probes", "programs"))
import run_programs                                  # noqa: E402

PROG = "scratchpad/keyrepaint_measure.bas"
ROWS = 5


def main():
    text = open(os.path.join(REPO, PROG)).read()
    ref = run_programs.run(run_programs.REF, "keyrepaint", text)
    rl = ref[1].replace("\r", "").splitlines()
    print(f"{run_programs.REF:30} {ref[0]}  {len(rl)} rows")
    bad = 0
    for m in run_programs.ZB:
        zb = run_programs.run(m, "keyrepaint", text)
        zl = zb[1].replace("\r", "").splitlines()
        diff = [(a, b) for a, b in zip(rl, zl) if a != b]
        ok = len(rl) == ROWS and zl == rl
        bad += not ok
        print(f"{m:30} {zb[0]}  {len(diff)} differ  {'SAME' if ok else 'DIVERGES'}")
        for a, b in diff:
            print(f"      ref {a!r}  zb {b!r}")
    print(f"\n{'PASS' if not bad else 'FAIL'}: KEY n repaints the shown key row at once, as on the VG-8020")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
