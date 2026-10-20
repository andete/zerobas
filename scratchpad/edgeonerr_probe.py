#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-EDGEONERR measure-first (2026-10-20): which ingredient moves zerobas's DIM edge ~25 B off
the VG-8020's (edgestr_head.out, K=136)? dimedge-acceptance's plain shape agrees (108 / 109).
For each SHAPE, every K: does `X=INT((FRE(0)-K)/8):DIM A(X)` fit? The first fitting K is the
edge; prints both machines' edges per shape. Boot per case. X exists first in every shape.
  plain   CLEAR 200:X=0
  str     + A$="":B$="HELLO"
  onerr   + ON ERROR GOTO 100 (100 END)
  both    + the strings and the handler (and E=0:B=0, as edgestr_probe)
"""
import os, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
sys.path.insert(0, os.path.join(REPO, "probes", "basic"))
import omsx_repl                                    # noqa: E402
import basic_probe_dimedge as D                     # noqa: E402

SHAPES = {"plain": "CLEAR 200:X=0:",
          "str": 'CLEAR 200:X=0:A$="":B$="HELLO":',
          "onerr": "CLEAR 200:X=0:ON ERROR GOTO 100:",
          "both": 'CLEAR 200:X=0:E=0:B=0:A$="":B$="HELLO":ON ERROR GOTO 100:'}
KS = list(range(int(os.environ.get("K0", "104")), int(os.environ.get("K1", "148")) + 1, 2))


def prog(pre, k):
    return ["NEW", f"10 {pre}X=INT((FRE(0)-{k})/8):DIM A(X)", '20 PRINT"[";"FIT";"]":END',
            "100 END", "RUN"]


def main():
    for shape, pre in SHAPES.items():
        edges = {}
        for m in (D.REF, D.ZB):
            raws = omsx_repl.run_cases(m, [("direct", prog(pre, k)) for k in KS], batch=False,
                                       reset=("CLS",), boot=8.0, capture="screen")
            fits = [k for k, r in zip(KS, raws) if "[FIT]" in (r or "").replace(" ", "")]
            edges[m] = min(fits) if fits else None
        a, b = edges[D.REF], edges[D.ZB]
        print(f"{shape:6} first fitting K: VG {a}  ZB {b}  {'SAME' if a == b else 'DIFF'}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
