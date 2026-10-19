#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-FREPLUS14 follow-up (2026-10-17): dimedge-acceptance's coarse rows (K = 100, 108,
120, 136, ...) no longer bracket zerobas's DIM edge once FRE(0) reads the reference's
live-stack depth -- `X=INT((FRE(0)-K)/8)` now reads lower by its paren + LET base, so
every K lands elsewhere. This scans K one by one on both machines to find each one's
first FITTED K. The probe's own rows and verdicts (basic_probe_dimedge.py), reused.
"""
import os, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
sys.path.insert(0, os.path.join(REPO, "probes", "basic"))
import omsx_repl                                    # noqa: E402
import basic_probe_dimedge as D                     # noqa: E402

KS = list(range(int(os.environ.get("K0", "96")), int(os.environ.get("K1", "116")) + 1))


def main():
    for m in (D.REF, D.ZB):
        # boot per case, exactly as basic_probe_dimedge.py runs (batched and per-case
        # read the same edges: VG 113, zerobas 108 -- dimedge_scan.out / _scan2.out)
        # PRE=1: X exists BEFORE the measured statement (freabs_run.out: a LET whose
        # target is new reads FRE(0) 11 B lower on the VG-8020, which creates the
        # target before the right side; this isolates the ALLOCATION edge)
        case = (lambda k: [l.replace("CLEAR 200:", "CLEAR 200:X=0:") for l in D.dim_case(k)]) \
            if os.environ.get("PRE") else D.dim_case
        if os.environ.get("INT"):           # 2-byte elements: the edge to 2 B, not 8
            case = lambda k: [l.replace("CLEAR 200:", "CLEAR 200:X=0:").replace(
                f"-{k})/8):DIM A(X)", f"-{k})/2):DIM A%(X)") for l in D.dim_case(k)]
        if os.environ.get("ODD"):           # one more program byte: FRE(0)'s other parity
            prev = case
            case = lambda k: [l.replace("CLEAR 200:X=0:", "CLEAR 200: X=0:") for l in prev(k)]
        raws = omsx_repl.run_cases(m, [("direct", case(k)) for k in KS], batch=False,
                                   reset=("CLS",), boot=8.0, capture="screen")
        line = " ".join(f"{k}:{(D.dim_reading(r) or '?')[0]}" for k, r in zip(KS, raws))
        print(f"{m:30} {line}", flush=True)
    print("F = FITTED, R = REFUSED, ? = no reading")
    return 0


if __name__ == "__main__":
    sys.exit(main())
