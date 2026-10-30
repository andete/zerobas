#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""inputcont-acceptance (D-INPUTCONT): INPUT's `??` continuation and the redo prompt.

Found by the program ladder's L2_survey: `INPUT "NAME, AGE";N$,G` answered
`JONES` was `?Redo from start` here, and every later answer then landed in the
wrong question. Measured (scratchpad/inputcont_measure.out): when the variable
list wants more than the line held, the VG-8020 asks `?? ` for the rest and goes
on with the next variable, once per missing value; a bad field on a `??` line is
a ?Redo of the whole statement; and a ?Redo shows the statement's own prompt
again (`P1? `), where zerobas showed a bare `? `. And a COMMA after the prompt
literal (`INPUT "P7",X`, `LINE INPUT "P8",Q$`) is Syntax error on both
references, where zerobas took it (D-INPUTCOMMA, scratchpad/inputcomma_measure.out). The program reads the screen
back with VPEEK at the end, so the prompts are compared too. Both zerobas
targets against the VG-8020.

Clean-room: typed keys and a tape in; the printer port out.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "probes", "programs"))
import run_programs                                  # noqa: E402

PROG = "scratchpad/inputcont_measure.bas"
ROWS = 31


def main():
    text = open(os.path.join(REPO, PROG)).read()
    ref = run_programs.run(run_programs.REF, "inputcont", text)
    rl = ref[1].replace("\r", "").splitlines()
    print(f"{run_programs.REF:30} {ref[0]}  {len(rl)} rows")
    bad = 0
    for m in run_programs.ZB:
        zb = run_programs.run(m, "inputcont", text)
        zl = zb[1].replace("\r", "").splitlines()
        diff = [(a, b) for a, b in zip(rl, zl) if a != b]
        ok = len(rl) == ROWS and zl == rl
        bad += not ok
        print(f"{m:30} {zb[0]}  {len(diff)} differ  {'SAME' if ok else 'DIVERGES'}")
        for a, b in diff:
            print(f"      ref {a!r}  zb {b!r}")
    print(f"\n{'PASS' if not bad else 'FAIL'}: INPUT asks ?? for the rest and redoes "
          f"the whole statement, as on the VG-8020")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
