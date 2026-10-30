#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""playeq-acceptance (D-PLAYEQ): PLAY takes `=name;` for a command's number.

Found by the program ladder's L3_turtle: `PLAY "T=T;O4XM$;"` was ERR 5 here.
Measured (scratchpad/playeq_measure.out): T V N O L S M R take `=name;`, a note
does not; the value is cut as CINT cuts and past an int16 is 6; an undefined
name is 0, a string 13, a missing `;` 5, spaces are skipped, a literal or `(` is
5. Thirty rows, each PLAY's error code; `O=X9;` / `O=X8;` and `T=Y1;` / `T=Y2;`
prove the VALUE is read (9 and 31 are out of range). An array element
(`V=I%(1);`) is not a row: D-PLAYEQARR.
One program, scratchpad/playeq_probe.bas; both zerobas targets against the
VG-8020.

Clean-room: typed keys and a tape in; the printer port out.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "probes", "programs"))
import run_programs                                  # noqa: E402

PROG = "scratchpad/playeq_probe.bas"
ROWS = 31


def main():
    text = open(os.path.join(REPO, PROG)).read()
    ref = run_programs.run(run_programs.REF, "playeq", text)
    rl = ref[1].replace("\r", "").splitlines()
    print(f"{run_programs.REF:30} {ref[0]}  {len(rl)} rows")
    bad = 0
    for m in run_programs.ZB:
        zb = run_programs.run(m, "playeq", text)
        zl = zb[1].replace("\r", "").splitlines()
        diff = [(a, b) for a, b in zip(rl, zl) if a != b]
        ok = len(rl) == ROWS and zl == rl
        bad += not ok
        print(f"{m:30} {zb[0]}  {len(diff)} differ  {'SAME' if ok else 'DIVERGES'}")
        for a, b in diff:
            print(f"      ref {a!r}  zb {b!r}")
    print(f"\n{'PASS' if not bad else 'FAIL'}: PLAY takes =name; as on the VG-8020")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
