#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-EVALSLOPE's typed frame (2026-10-20): a PENDING `+` holds 20 B a level on zerobas
(the entry, FACTYP+FAC 10, the lhs, the paren's 6) against the VG-8020's 16
(scratchpad/evalslope_after.out; docs/spec-basic-deepexpr-guard.md §5.3.1). stackcorrupt's
P(n) = `((1+1)+1)` holds parens only. Here `B=1+(1+(...1...))` (OP=+), or `1*(` (OP=*),
nests the operator itself. Per K (bytes below FRE(0) after an edge DIM, the canary A(X)
last), bisect the deepest nest that completes with the canary intact, on both machines.
    python3 -u scratchpad/arithnest_probe.py [K ...]     (AN_OP=+|*, AN_MAX)
"""
import os, re, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                    # noqa: E402

VG, ZB = "Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK"
OP = os.environ.get("AN_OP", "+")


def prog(k, n):
    expr = f"1{OP}(" * n + "1" + ")" * n
    return ["NEW", f'10 CLEAR 200:ON ERROR GOTO 90:X=INT((FRE(0)-{k})/8):DIM A(X):A(X)=12345',
            f"20 B={expr}",
            '30 PRINT CHR$(91);"OK";A(X);CHR$(93):END',
            '90 PRINT CHR$(91);"ERR";ERR;A(X);CHR$(93):END', "RUN"]


def outcome(m, k, n):
    raw = omsx_repl.run_cases(m, [("direct", prog(k, n))], batch=False, reset=("CLS",),
                              boot=8.0, step=3.0, run_gap=20.0, capture="screen")[0]
    got = re.findall(r"\[([^\]\"]*)\]", raw or "")
    r = " ".join(got[-1].split()) if got else "NO READING"
    if r == "OK 12345":
        return "fit"
    if r == "ERR 7 12345":
        return "oom"
    return r


def deepest(m, k, hi):
    lo, top = 0, hi
    if outcome(m, k, top) == "fit":
        return f">={top}"
    while top - lo > 1:
        mid = (lo + top) // 2
        o = outcome(m, k, mid)
        if o == "fit":
            lo = mid
        elif o == "oom":
            top = mid
        else:
            return f"ODD at {mid}: {o!r}"
    return lo


def main():
    ks = [int(a) for a in sys.argv[1:]] or [400, 700]
    hi = int(os.environ.get("AN_MAX", "56"))
    for k in ks:
        d = {m: deepest(m, k, hi) for m in (VG, ZB)}
        print(f"K={k:4} op {OP}  deepest that fits: VG {d[VG]}  ZB {d[ZB]}  "
              f"{'SAME' if d[VG] == d[ZB] else 'DIFF'}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
