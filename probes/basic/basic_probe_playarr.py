#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""playarr-acceptance (D-PLAYEQARR): PLAY's `=name;` with an ARRAY ELEMENT.

`PLAY "V=A(1);"` works on the VG-8020 and was ERR 5 here after D-PLAYEQ.
Measured (scratchpad/playarr_measure.out, 20 rows): each subscript is a number
(its fraction cut) or a plain variable; an expression (`J+1`, `-1`, `()`) is
Syntax error 2; out of range or the wrong count is 9; a string array 13; an
array never dimensioned reads 0 within the automatic bound of 10. One program,
each PLAY's error code; both zerobas targets against the VG-8020.

Clean-room: typed keys and a tape in; the printer port out.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "probes", "programs"))
import run_programs                                  # noqa: E402

PROG = "scratchpad/playarr_measure.bas"
ROWS = 21


def main():
    text = open(os.path.join(REPO, PROG)).read()
    ref = run_programs.run(run_programs.REF, "playarr", text)
    rl = ref[1].replace("\r", "").splitlines()
    print(f"{run_programs.REF:30} {ref[0]}  {len(rl)} rows")
    bad = 0
    for m in run_programs.ZB:
        zb = run_programs.run(m, "playarr", text)
        zl = zb[1].replace("\r", "").splitlines()
        diff = [(a, b) for a, b in zip(rl, zl) if a != b]
        ok = len(rl) == ROWS and zl == rl
        bad += not ok
        print(f"{m:30} {zb[0]}  {len(diff)} differ  {'SAME' if ok else 'DIVERGES'}")
        for a, b in diff:
            print(f"      ref {a!r}  zb {b!r}")
    print(f"\n{'PASS' if not bad else 'FAIL'}: PLAY takes =A(i); as on the VG-8020")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
