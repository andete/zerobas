#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""putiny-acceptance (D-PUTINY): PRINT USING's fixed fields take values that
PRINT writes in E form.

Found by the program ladder's L4_tables: `PRINT USING "+#.#####";COS(PI/2)`
prints `-0.00000` on the VG-8020 and printed `-3.38082` here, because the fixed
renderer read PRINT's text ` -3.38081E-15 ` and stopped at the `E`. Measured
(scratchpad/putiny_measure.out, putiny_big.out, putiny_neg.out, putiny_wide.out):
  * a SMALL value is rounded half-up into the field's places like any other
    (`5D-6` -> `+0.00001`, `4D-6` -> `+0.00000`, `-6D-6` -> `-0.00001`);
  * a LARGE one is `%`, a space, and PRINT's own E text, whatever the field:
    no padding, its `-` dropped, and `+`, a trailing `-`, `**` and `$$` ignored.
One program, scratchpad/putiny_probe.bas; both zerobas targets against the
VG-8020.

Clean-room: typed keys and a tape in; the printer port out.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "probes", "programs"))
import run_programs                                  # noqa: E402

PROG = "scratchpad/putiny_probe.bas"
ROWS = 13


def main():
    text = open(os.path.join(REPO, PROG)).read()
    ref = run_programs.run(run_programs.REF, "putiny", text)
    rl = ref[1].replace("\r", "").splitlines()
    print(f"{run_programs.REF:30} {ref[0]}  {len(rl)} rows")
    bad = 0
    for m in run_programs.ZB:
        zb = run_programs.run(m, "putiny", text)
        zl = zb[1].replace("\r", "").splitlines()
        diff = [(a, b) for a, b in zip(rl, zl) if a != b]
        ok = len(rl) == ROWS and zl == rl
        bad += not ok
        print(f"{m:30} {zb[0]}  {len(diff)} differ  {'SAME' if ok else 'DIVERGES'}")
        for a, b in diff:
            print(f"      ref {a!r}  zb {b!r}")
    print(f"\n{'PASS' if not bad else 'FAIL'}: values PRINT shows in E form fill a fixed "
          f"PRINT USING field as on the VG-8020")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
