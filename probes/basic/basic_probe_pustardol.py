#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""pustardol-acceptance (D-PUSTARDOL): PRINT USING's `**$` floats the dollar.

Found by the program ladder's ledger: `PRINT USING "**$##.##";5` is `***$5.00`
on the VG-8020 and was `$***5.00` here. Twelve shapes, one program
(scratchpad/pustardol_probe.bas): the `$` sits right before the digits after
any sign (`**-$5.00`), `+**$` makes the `+` the sign (`***+$5.00`), `**$.##`
floats too, a value too wide is `%$123456.00`, commas and a trailing `-` work
as with `**`. Both zerobas targets against the VG-8020 -- the CF-3300 does not
implement the floating dollar at all (basic/pu-render.inc ptf_dollar), so the
VG-8020 is the reference for this specifier on both.

Clean-room: typed keys and a tape in; the printer port out.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "probes", "programs"))
import run_programs                                  # noqa: E402

PROG = "scratchpad/pustardol_probe.bas"


def main():
    text = open(os.path.join(REPO, PROG)).read()
    ref = run_programs.run(run_programs.REF, "pustardol", text)
    rl = ref[1].replace("\r", "").splitlines()
    print(f"{run_programs.REF:30} {ref[0]}  {len(rl)} rows")
    bad = 0
    for m in run_programs.ZB:
        zb = run_programs.run(m, "pustardol", text)
        zl = zb[1].replace("\r", "").splitlines()
        diff = [(a, b) for a, b in zip(rl, zl) if a != b]
        ok = len(rl) == 12 and zl == rl
        bad += not ok
        print(f"{m:30} {zb[0]}  {len(diff)} differ  {'SAME' if ok else 'DIVERGES'}")
        for a, b in diff:
            print(f"      ref {a!r}  zb {b!r}")
    print(f"\n{'PASS' if not bad else 'FAIL'}: `**$` floats the dollar against the digits, "
          f"as on the VG-8020")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
