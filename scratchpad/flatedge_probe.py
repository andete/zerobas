#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""flatedge_probe.py -- D-EDGEONERR / D-DEEPEXPR step 3 (2026-10-20): where does a FLAT statement right after a DIM
at the memory edge stop fitting -- the VG-8020's margin for a flat expression (the spec's Q1 /
X), against zerobas's STK_EVAL_RESERVE? `X=INT((FRE(0)-K)/2):DIM A%(X):A%(X)=12345` then
`PRINT "[OK]"`, no handler; the first K that prints [OK] is the edge. 2-byte elements, so the
edge reads to 2 B; ODD=1 adds one program byte for the other parity. Boot per case.
"""
import os, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                    # noqa: E402

KS = list(range(int(os.environ.get("K0", "96")), int(os.environ.get("K1", "140")) + 1))
PRE = 'CLEAR 200: X=0:' if os.environ.get("ODD") else 'CLEAR 200:X=0:'


def prog(k):
    # FE_SHAPE=edgestr: D-EDGEONERR's own shape -- 8-byte elements, more variables first,
    # an ON ERROR handler (100 END) -- where one R cannot also match the integer shape
    if os.environ.get("FE_SHAPE") == "edgeprint":   # edgestr_probe's line 40: PRINT numbers
        return ["NEW", '10 CLEAR 200:X=0:E=0:B=0:A$="":B$="HELLO":ON ERROR GOTO 100',
                f"20 X=INT((FRE(0)-{k})/8):DIM A(X):A(X)=12345", "30 B=1",
                '40 PRINT E;A(X):PRINT"[";"OK";"]":END', "100 END", "RUN"]
    if os.environ.get("FE_SHAPE") == "deepctl":   # deepexpr-acceptance's own program, B=1
        # PAD=n lengthens line 30 by n bytes: the room left is K + (0..7) by FRE(0)'s phase
        # mod 8, so the 8 pads together read the edge to the byte.
        pad = int(os.environ.get("PAD", "0"))
        return ["NEW", "10 CLEAR 200:X=0:E=0:B=0:ON ERROR GOTO 100",
                f"20 X=INT((FRE(0)-{k})/8):DIM A(X):A(X)=12345", "30 B=1" + ":" * pad,
                '40 PRINT"[";E;A(X);"]":PRINT"[";"OK";"]":END', "100 E=ERR:RESUME 40", "RUN"]
    if os.environ.get("FE_SHAPE") == "edgestr":
        return ["NEW", '10 CLEAR 200:X=0:E=0:B=0:A$="":B$="HELLO":ON ERROR GOTO 100',
                f"20 X=INT((FRE(0)-{k})/8):DIM A(X):A(X)=12345", '30 PRINT"[";"OK";"]":END',
                "100 END", "RUN"]
    return ["NEW", f"10 {PRE}X=INT((FRE(0)-{k})/2):DIM A%(X):A%(X)=12345", '20 PRINT"[";"OK";"]"', "RUN"]


def main():
    # FE_ZB_ONLY=1: zerobas alone, while R is bisected (the VG-8020's edges are known)
    for m in (("C-BIOS_MSX1_EU_REPACK_NODISK",) if os.environ.get("FE_ZB_ONLY") else ("Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK")):
        raws = omsx_repl.run_cases(m, [("direct", prog(k)) for k in KS], batch=False,
                                   reset=("CLS",), boot=8.0, capture="screen")
        ok = [k for k, r in zip(KS, raws) if "[OK]" in (r or "").replace(" ", "")]
        line = "".join("F" if k in ok else "." for k in KS)
        print(f"{m:30} first OK K={min(ok) if ok else None}  {KS[0]}..{KS[-1]}: {line}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
