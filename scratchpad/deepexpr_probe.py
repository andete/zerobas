#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""docs/spec-basic-deepexpr-guard.md's live-bug rows LB1-LB4 (2026-10-20, found by reading):
near the memory edge, does a deep expression OVERWRITE the arrays on zerobas where the
VG-8020 refuses (ERR 7) or completes cleanly? A canary element A(X)=12345 is the LAST
thing in the array region; the expression runs trapped; the row prints [err canary].
A changed canary, or no reading at all, is memory corruption.
  lb1  B=((((...1...))))      40 leading parens (the string probe recursing per `(`)
  lb2  B=++++...1             120 unary plus
  lb3  B=LEN(LEFT$(LEFT$(...("ABC",3)...,3),3))   20 nested LEFT$
  lb4  B=(((...Z#(1,1)...)))  a first-touch 11x11 double array inside 15 parens
K is the bytes left below FRE(0) after the canary DIM (lb4: room for Z#'s 968 B).
"""
import os, re, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                    # noqa: E402

ROWS = [
    ("lb1", 200, "(" * 40 + "1" + ")" * 40),
    ("lb2", 200, "+" * 120 + "1"),
    ("lb3", 200, "LEN(" + "LEFT$(" * 20 + '"ABC"' + ",3)" * 20 + ")"),
    ("lb4", 1150, "(" * 15 + "Z#(1,1)" + ")" * 15),
    ("ctl", 200, "1"),                               # positive control: plain, completes
]


def prog(k, expr):
    return ["NEW", "10 CLEAR 200:X=0:E=0:B=0:ON ERROR GOTO 100",
            f"20 X=INT((FRE(0)-{k})/8):DIM A(X):A(X)=12345",
            f"30 B={expr}",
            '40 PRINT"[";E;A(X);"]":END',
            "100 E=ERR:RESUME 40", "RUN"]


def main():
    got = {}
    for m in ("Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK"):
        raws = omsx_repl.run_cases(m, [("direct", prog(k, e)) for _n, k, e in ROWS], batch=False,
                                   reset=("CLS",), boot=8.0, capture="screen")
        for (n, _k, _e), r in zip(ROWS, raws):
            flat = (r or "").replace("\n", "")
            v = [x for x in re.findall(r"\[([^\]\[]*)\]", flat)
                 if '"' not in x and re.fullmatch(r"[\s\d.E+-]+", x)]
            got[(m, n)] = " ".join(v[-1].split()) if v else "NO READING"
    for n, _k, _e in ROWS:
        a, b = got[("Philips_VG_8020", n)], got[("C-BIOS_MSX1_EU_REPACK_NODISK", n)]
        print(f"{n:4} VG=[{a}] ZB=[{b}] {'SAME' if a == b else 'DIFF'}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
