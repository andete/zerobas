#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""resnextend-acceptance (D-RESNEXTDIRECT): RESUME NEXT after an error in the
last statement of the LAST program line, or of a DIRECT line, ends the run.

Found 2026-10-30 when an unread answer key reached the prompt with a program's
`ON ERROR GOTO` still set: the VG-8020 ran the handler once and said Ok; zerobas
ran the bytes past the end marker as statements and the handler caught every
error forever (scratchpad/resnextdirect_measure.out). A program whose last line
errs did the same (resnextlast_measure.out). The third program reads TRON's
`[100][40]` back across an end-of-line RESUME NEXT: the run loop's own step to
the next line, which the fix uses, traces it as the VG-8020 does. Each program
runs to its end
-- a TIMEOUT is a failure -- both zerobas targets against the VG-8020.

Clean-room: typed keys and a tape in; the printer port out.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "probes", "programs"))
import run_programs                                  # noqa: E402

PROGS = [("scratchpad/resnextdirect_measure.bas", 2),
         ("scratchpad/resnextlast_measure.bas", 2),
         ("scratchpad/resnexttron_measure.bas", 3)]


def main():
    bad = 0
    for prog, rows in PROGS:
        text = open(os.path.join(REPO, prog)).read()
        ref = run_programs.run(run_programs.REF, "resnextend", text)
        rl = ref[1].replace("\r", "").splitlines()
        print(f"{prog}\n  {run_programs.REF:30} {ref[0]}  {len(rl)} rows")
        for m in run_programs.ZB:
            zb = run_programs.run(m, "resnextend", text)
            zl = zb[1].replace("\r", "").splitlines()
            diff = [(a, b) for a, b in zip(rl, zl) if a != b]
            ok = len(rl) == rows and zl == rl and zb[0].split()[0] == "ENDED"
            bad += not ok
            print(f"  {m:30} {zb[0]}  {len(diff)} differ  {'SAME' if ok else 'DIVERGES'}")
            for a, b in diff:
                print(f"      ref {a!r}  zb {b!r}")
    print(f"\n{'PASS' if not bad else 'FAIL'}: RESUME NEXT after the last statement ends the run, "
          f"as on the VG-8020")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
