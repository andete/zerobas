#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-EVALSLOPE R re-bisect (2026-10-20): deepexpr-acceptance row `edge136` -- the gate's own
program, a trapped flat `B=1` then `PRINT"[";E;A(X);"]"` right after an edge DIM -- the
VG-8020 completes at K=136 and zerobas at STK_EVAL_RESERVE 119 does not. The room actually
left is K + (0..7) by FRE(0)'s phase mod 8, so one program reads one phase; PAD=0..7 extra
`:` on line 30 walk all eight. Per pad, bisect the first K that prints the reading, on both
machines (scratchpad/flatedge_probe.py FE_SHAPE=deepctl is the same program, swept).
    python3 -u scratchpad/deepctl_edge_probe.py [pad ...]    (DC_LO, DC_HI, DC_ONLY=VG|ZB)
"""
import os, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                    # noqa: E402

VG, ZB = "Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK"


# DC_SHAPE: deepctl (the gate's program, default) | edgeprint | edgestr -- the latter two
# are scratchpad/flatedge_probe.py's shapes of the same names, padded the same way.
SHAPE = os.environ.get("DC_SHAPE", "deepctl")


def prog(k, pad):
    p = ":" * pad
    if SHAPE == "edgeprint":
        return ["NEW", '10 CLEAR 200:X=0:E=0:B=0:A$="":B$="HELLO":ON ERROR GOTO 100',
                f"20 X=INT((FRE(0)-{k})/8):DIM A(X):A(X)=12345", "30 B=1" + p,
                '40 PRINT E;A(X):PRINT"[";"OK";"]":END', "100 END", "RUN"]
    if SHAPE == "edgestr":
        return ["NEW", '10 CLEAR 200:X=0:E=0:B=0:A$="":B$="HELLO":ON ERROR GOTO 100',
                f"20 X=INT((FRE(0)-{k})/8):DIM A(X):A(X)=12345" + p,
                '30 PRINT"[";"OK";"]":END', "100 END", "RUN"]
    return ["NEW", "10 CLEAR 200:X=0:E=0:B=0:ON ERROR GOTO 100",
            f"20 X=INT((FRE(0)-{k})/8):DIM A(X):A(X)=12345", "30 B=1" + p,
            '40 PRINT"[";E;A(X);"]":PRINT"[";"OK";"]":END', "100 E=ERR:RESUME 40", "RUN"]


def fits(m, k, pad):
    r = omsx_repl.run_cases(m, [("direct", prog(k, pad))], batch=False,
                            reset=("CLS",), boot=8.0, capture="screen")[0]
    return "[OK]" in (r or "").replace(" ", "")


def edge(m, pad, lo, hi):
    if fits(m, lo, pad) or not fits(m, hi, pad):
        return f"UNBRACKETED {lo}..{hi}"
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if fits(m, mid, pad):
            hi = mid
        else:
            lo = mid
    return hi


def main():
    pads = [int(a) for a in sys.argv[1:]] or list(range(8))
    lo, hi = int(os.environ.get("DC_LO", "112")), int(os.environ.get("DC_HI", "160"))
    only = os.environ.get("DC_ONLY")
    sides = [m for t, m in (("VG", VG), ("ZB", ZB)) if only in (None, t)]
    for pad in pads:
        es = {m: edge(m, pad, lo, hi) for m in sides}
        tag = "" if len(sides) < 2 else ("SAME" if es[VG] == es[ZB] else "DIFF")
        print(f"pad {pad}: " + "  ".join(f"{m[:8]} {es[m]}" for m in sides) + f"  {tag}",
              flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
