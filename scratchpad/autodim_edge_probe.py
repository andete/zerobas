#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-EVALSLOPE measure (2026-10-20): deepexpr-acceptance row lb4 -- a first-touch 11x11
double array inside 15 parens -- completes on zerobas after the climber rewrite where the
VG-8020 refuses (ERR 7). Is that the parens (the expression's stack) or the auto-DIM's own
room test? For each paren count P, bisect the smallest K (bytes below FRE(0) after the canary
DIM) at which `B=(((...Z#(1,1)...)))` completes with the canary intact, on both machines.
The same program shape as probes/basic/basic_probe_deepexpr.py.
    python3 -u scratchpad/autodim_edge_probe.py [P ...]     (AE_ONLY=VG|ZB, AE_LO, AE_HI)
"""
import os, re, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                    # noqa: E402

VG, ZB = "Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK"


def prog(k, p):
    expr = "(" * p + "Z#(1,1)" + ")" * p
    return ["NEW", "10 CLEAR 200:X=0:E=0:B=0:ON ERROR GOTO 100",
            f"20 X=INT((FRE(0)-{k})/8):DIM A(X):A(X)=12345",
            f"30 B={expr}",
            '40 PRINT"[";E;A(X);"]":END',
            "100 E=ERR:RESUME 40", "RUN"]


def reading(m, k, p):
    r = omsx_repl.run_cases(m, [("direct", prog(k, p))], batch=False,
                            reset=("CLS",), boot=8.0, capture="screen")[0]
    flat = (r or "").replace("\n", "")
    v = [x for x in re.findall(r"\[([^\]\[]*)\]", flat)
         if '"' not in x and re.fullmatch(r"[\s\d.E+-]+", x)]
    return " ".join(v[-1].split()) if v else "NO READING"


def edge(m, p, lo, hi):
    """Smallest K in (lo, hi] that reads '0 12345'; lo must refuse, hi must complete."""
    rl, rh = reading(m, lo, p), reading(m, hi, p)
    if rl == "0 12345" or rh != "0 12345":
        return f"UNBRACKETED lo={rl!r} hi={rh!r}"
    seen = {}
    while hi - lo > 1:
        mid = (lo + hi) // 2
        r = reading(m, mid, p)
        seen[mid] = r
        if r == "0 12345":
            hi = mid
        elif r == "7 12345":
            lo = mid
        else:
            return f"CORRUPT/ODD at K={mid}: {r!r}"
    return hi


def main():
    ps = [int(a) for a in sys.argv[1:]] or [0, 15]
    lo, hi = int(os.environ.get("AE_LO", "900")), int(os.environ.get("AE_HI", "1400"))
    only = os.environ.get("AE_ONLY")
    sides = [m for k, m in (("VG", VG), ("ZB", ZB)) if only in (None, k)]
    for p in ps:
        es = {m: edge(m, p, lo, hi) for m in sides}
        print(f"P={p:3} " + "  ".join(f"{m[:8]} edge K={es[m]}" for m in sides), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
