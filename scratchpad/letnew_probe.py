#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-LETNEWFIRST measure-first (2026-10-19): WHICH statements create their target
variable before the right side on the VG-8020, and in what ORDER two new variables are
created? scratchpad/freabs_run.out found it for `X=FRE(0)` (11 B: the VG-8020 has made X
before FRE runs). Each row is one line in a fresh program, booted per row; it prints the
value the line computed (FRE in the line's own shape), so ZB-VG is the bytes the
reference has already spent when FRE runs. The `pre` twin of each row creates the target
first (0 = the shape itself agrees; any difference left is the creation order's).
Order rows print VARPTR(A)-VARPTR(B): negative = A was created first.
"""
import os, re, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                    # noqa: E402


def row(body, pre=""):
    return ["NEW", f'10 CLEAR 200:{pre}{body}', "RUN"]


ROWS = [
    ("dbl",      row('X=FRE(0):PRINT"[v";X;"]"')),
    ("dbl.pre",  row('X=FRE(0):PRINT"[v";X;"]"', "X=0:")),
    ("int",      row('X%=FRE(0):PRINT"[v";X%;"]"')),
    ("int.pre",  row('X%=FRE(0):PRINT"[v";X%;"]"', "X%=0:")),
    ("sng",      row('X!=FRE(0):PRINT"[v";X!;"]"')),
    ("str",      row('X$=STR$(FRE(0)):PRINT"[v";X$;"]"')),
    ("str.pre",  row('X$=STR$(FRE(0)):PRINT"[v";X$;"]"', 'X$="":')),
    ("ary",      row('X(1)=FRE(0):PRINT"[v";X(1);"]"')),
    ("ary.pre",  row('X(1)=FRE(0):PRINT"[v";X(1);"]"', "DIM X(10):")),
    ("for",      row('FOR I=FRE(0) TO 0 STEP -1E9:PRINT"[v";I;"]":NEXT')),
    ("for.pre",  row('FOR I=FRE(0) TO 0 STEP -1E9:PRINT"[v";I;"]":NEXT', "I=0:")),
    ("order",    row('A=B:PRINT"[v";VARPTR(A)-VARPTR(B);"]"')),
    ("order2",   row('A=B+C:PRINT"[v";VARPTR(A)-VARPTR(B);VARPTR(B)-VARPTR(C);"]"')),
]
MACHINES = ("Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK")


def main():
    got = {}
    for m in MACHINES:
        raws = omsx_repl.run_cases(m, [("direct", p) for _n, p in ROWS], batch=False,
                                   reset=("CLS",), boot=8.0, capture="screen")
        for (n, _p), r in zip(ROWS, raws):
            v = [x for x in re.findall(r"\[v([^\]\[]*)\]", (r or "").replace("\n", "")) if '"' not in x]
            got[(m, n)] = v[-1].strip() if v else "NO READING"
    print(f"{'row':10} {'VG':>14} {'ZB':>14}  ZB-VG")
    for n, _p in ROWS:
        a, b = got[(MACHINES[0], n)], got[(MACHINES[1], n)]
        try:
            d = int(float(b)) - int(float(a))
        except ValueError:
            d = "SAME" if a == b else "DIFF"
        print(f"{n:10} {a:>14} {b:>14}  {d}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
