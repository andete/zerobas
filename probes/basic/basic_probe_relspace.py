#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""relspace-acceptance (D-RELSPACE): a space after a two-character relational
operator (`<=`, `>=`, `<>`, or between its halves) before a STRING right-hand
side is ignored, as on the VG-8020.

Found 2026-10-31 by a D-REREAD batch 6 reviewer and measured the same day
(scratchpad/relspace_run.out): zerobas raised Type mismatch for `"A"<= "B"` and
four relatives, because the string comparison stepped past the second relop
without skipping the spaces after it. The program prints each answer and ends;
both zerobas targets against the VG-8020, row for row.

Clean-room: typed keys in; the printer port out.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "probes", "programs"))
import run_programs                                  # noqa: E402

PROG, ROWS = "scratchpad/relspace_measure.bas", 8


def main():
    bad = 0
    text = open(os.path.join(REPO, PROG)).read()
    ref = run_programs.run(run_programs.REF, "relspace", text)
    rl = ref[1].replace("\r", "").splitlines()
    print(f"{PROG}\n  {run_programs.REF:30} {ref[0]}  {len(rl)} rows")
    for r in rl:
        print(f"      {r!r}")
    if len(rl) != ROWS:
        print(f"  the reference printed {len(rl)} rows, not {ROWS}: the program did not run as written")
        bad += 1
    for m in run_programs.ZB:
        zb = run_programs.run(m, "relspace", text)
        zl = zb[1].replace("\r", "").splitlines()
        diff = [(a, b) for a, b in zip(rl, zl) if a != b]
        ok = len(rl) == ROWS and zl == rl and zb[0].split()[0] == "ENDED"
        bad += not ok
        print(f"  {m:30} {zb[0]}  {len(diff)} differ  {'SAME' if ok else 'DIVERGES'}")
        for a, b in diff:
            print(f"      ref {a!r}  zb {b!r}")
    print(f"\n{'PASS' if not bad else 'FAIL'}: a space after a compound relop before a string "
          f"is ignored, as on the VG-8020")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
