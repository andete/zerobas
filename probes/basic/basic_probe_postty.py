#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""postty-acceptance (D-POSTTY): POS(0) is BASIC's print column, which CLS and
SCREEN leave alone.

Found by the program ladder's G2_runner: after a `PRINT ...;` in SCREEN 1 then
SCREEN 0 and END, the VG-8020's `Ok` came on row 2 (row 1 blank) and zerobas's
on row 1. Measured (scratchpad/screencsr_measure.out): after CLS or SCREEN the
VG-8020 reads CSRLIN 0 but POS(0) still the column the last PRINT left (12
after `PRINT "AB";` at column 10); WIDTH resets it to 0. zerobas read the screen
cursor (0 everywhere). One program, six rows; both zerobas targets against the
VG-8020. The prompt's own new line is the ladder's G2_runner.

Clean-room: typed keys and a tape in; the printer port out.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "probes", "programs"))
import run_programs                                  # noqa: E402

PROG = "scratchpad/screencsr_measure.bas"
ROWS = 1


def main():
    text = open(os.path.join(REPO, PROG)).read()
    ref = run_programs.run(run_programs.REF, "postty", text)
    rl = ref[1].replace("\r", "").splitlines()
    print(f"{run_programs.REF:30} {ref[0]}  {len(rl)} rows")
    bad = 0
    for m in run_programs.ZB:
        zb = run_programs.run(m, "postty", text)
        zl = zb[1].replace("\r", "").splitlines()
        diff = [(a, b) for a, b in zip(rl, zl) if a != b]
        ok = len(rl) == ROWS and zl == rl
        bad += not ok
        print(f"{m:30} {zb[0]}  {len(diff)} differ  {'SAME' if ok else 'DIVERGES'}")
        for a, b in diff:
            print(f"      ref {a!r}  zb {b!r}")
    print(f"\n{'PASS' if not bad else 'FAIL'}: POS(0) keeps the print column through "
          f"CLS and SCREEN, as on the VG-8020")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
