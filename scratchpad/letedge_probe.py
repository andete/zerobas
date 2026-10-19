#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-LETNEWFIRST edges (2026-10-19): with a NEW scalar target created before the right
side (letnew_run.out), what is left when the statement FAILS? Each row: one statement
with a new target T, its error trapped; then `VARPTR(T)` says whether T exists (Illegal
function call when it does not -- both machines, letnew_run.out's `order` rows).
Prints [<err> <exists>] -- err 0 = the statement ran; exists 1 / 0.
"""
import os, re, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                    # noqa: E402

ROWS = [("varptr", "X=VARPTR(X)", "X"),       # its own address, or 5?
        ("divz",   "X=1/0", "X"),
        ("tmint",  'A%="X"', "A%"),
        ("tmstr",  "A$=1", "A$"),
        ("ovf",    "A%=40000", "A%"),
        ("noeq",   "LET X", "X"),
        ("noeq2",  "X 5", "X"),
        ("forstr", 'FOR I="A" TO 2', "I"),
        ("forok",  "FOR I=1 TO 0:NEXT", "I")]


def prog(stmt, tgt):
    return ["NEW", "10 E=0:Q=0:ON ERROR GOTO 100", f"20 {stmt}", "30 GOTO 110",
            "100 E=ERR:RESUME 110", f"110 ON ERROR GOTO 200:Q=VARPTR({tgt}):PRINT\"[\";E;\"1]\":END",
            '200 PRINT"[";E;"0]":END', "RUN"]


def main():
    got = {}
    for m in ("Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK"):
        raws = omsx_repl.run_cases(m, [("direct", prog(s, t)) for _n, s, t in ROWS], batch=False,
                                   reset=("CLS",), boot=8.0, capture="screen")
        for (n, _s, _t), r in zip(ROWS, raws):
            v = [x for x in re.findall(r"\[([^\]\[]*)\]", (r or "").replace("\n", ""))
                 if '"' not in x and re.fullmatch(r"\s*\d+\s+[01]\s*", x)]
            got[(m, n)] = " ".join(v[-1].split()) if v else "NO READING"
    print(f"{'row':8} {'stmt':20} {'VG':>8} {'ZB':>8}")
    for n, s, _t in ROWS:
        a, b = got[("Philips_VG_8020", n)], got[("C-BIOS_MSX1_EU_REPACK_NODISK", n)]
        print(f"{n:8} {s:20} {a:>8} {b:>8}  {'SAME' if a == b else 'DIFF'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
