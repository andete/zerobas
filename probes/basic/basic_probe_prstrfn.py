#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""prstrfn-acceptance (D-PRSTRFN): every PRINT item that is a string prints as
one, and an operator after a string FUNCTION is a Type mismatch before anything
is printed.

Found by READING during D-REREAD (2026-10-30), then measured: PRINT classified
its items with its own copy of str_eval_one's classification, and the copy had
drifted. `PRINT INPUT$(1)` and `PRINT SPRITE$(1)` were Type mismatch where the
VG-8020 prints them, and `PRINT CHR$(65) AND 1` printed `A` and then gave Syntax
error where the VG-8020 raises Type mismatch first. Two programs:
scratchpad/prstrfn_measure.bas (INPUT$ in five shapes, SPRITE$ in five) and
scratchpad/prstrfn_op2_measure.bas (four operators after string functions, the
error and the screen read back, plus three controls). Both zerobas targets
against the VG-8020.

Clean-room: typed keys and a tape in; the printer port and VRAM out.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "probes", "programs"))
import run_programs                                  # noqa: E402

PROGS = [("scratchpad/prstrfn_measure.bas", 9),
         ("scratchpad/prstrfn_op2_measure.bas", 7)]


def main():
    bad = 0
    for prog, rows in PROGS:
        text = open(os.path.join(REPO, prog)).read()
        ref = run_programs.run(run_programs.REF, "prstrfn", text)
        rl = ref[1].replace("\r", "").splitlines()
        print(f"{prog}\n  {run_programs.REF:30} {ref[0]}  {len(rl)} rows")
        for m in run_programs.ZB:
            zb = run_programs.run(m, "prstrfn", text)
            zl = zb[1].replace("\r", "").splitlines()
            diff = [(a, b) for a, b in zip(rl, zl) if a != b]
            ok = len(rl) == rows and zl == rl
            bad += not ok
            print(f"  {m:30} {zb[0]}  {len(diff)} differ  {'SAME' if ok else 'DIVERGES'}")
            for a, b in diff:
                print(f"      ref {a!r}  zb {b!r}")
    print(f"\n{'PASS' if not bad else 'FAIL'}: string items print as strings, and an "
          f"operator after a string function is a Type mismatch, as on the VG-8020")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
