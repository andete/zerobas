#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-DEEPEXPR risk 1 (2026-10-20): right after a DIM near the memory edge, do FLAT statements
-- a numeric LET, a string copy, a string literal store -- complete on zerobas exactly where
they complete on the VG-8020? The guarded heap gateway asks for STK_EVAL_RESERVE below the
heap op itself, and a string LET has no factor guard, so zerobas may now refuse earlier.
Every variable exists first; X sizes the DIM; the canary is A(X). Prints [err canary] for
`B=1`, `A$=B$` and `A$="XYZ"` at each K (bytes left below FRE(0) before the DIM).
"""
import os, re, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                    # noqa: E402

KS = (112, 120, 136, 160, 200, 260)
STMTS = (("num", "B=1"), ("copy", "A$=B$"), ("lit", 'A$="XYZ"'))


def prog(k, stmt):
    return ["NEW", '10 CLEAR 200:X=0:E=0:B=0:A$="":B$="HELLO":ON ERROR GOTO 100',
            f"20 X=INT((FRE(0)-{k})/8):DIM A(X):A(X)=12345",
            f"30 {stmt}", '40 PRINT"[";E;A(X);"]":END', "100 E=ERR:RESUME 40", "RUN"]


def main():
    cases = [(k, n, s) for k in KS for n, s in STMTS]
    got = {}
    for m in ("Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK"):
        raws = omsx_repl.run_cases(m, [("direct", prog(k, s)) for k, _n, s in cases], batch=False,
                                   reset=("CLS",), boot=8.0, capture="screen")
        for (k, n, _s), r in zip(cases, raws):
            flat = (r or "").replace("\n", "")
            v = [x for x in re.findall(r"\[([^\]\[]*)\]", flat)
                 if '"' not in x and re.fullmatch(r"[\s\d.E+-]+", x)]
            got[(m, k, n)] = " ".join(v[-1].split()) if v else "NO READING"
    print(f"{'K':>4} {'stmt':5} {'VG':>10} {'ZB':>10}")
    for k, n, _s in cases:
        a, b = got[("Philips_VG_8020", k, n)], got[("C-BIOS_MSX1_EU_REPACK_NODISK", k, n)]
        print(f"{k:4} {n:5} {a:>10} {b:>10}  {'SAME' if a == b else 'DIFF'}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
