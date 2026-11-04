#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-RECBIG widening, measure first (2026-11-04): PUT # records past 65535.

    python3 -u scratchpad/recwide_probe.py [CF|ZB] [ROW...]

LEN=1 rows PUT #1,n on a fresh file; L256 rows OPEN with LEN=256. Prints
`[LOF LOC]`, or `[ERR e LOC]`. Typed BASIC in, the screen out.
"""
import os, shutil, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                    # noqa: E402
import probe_tmp                                    # noqa: E402
sys.path.insert(0, os.path.join(REPO, "probes", "disk"))
from disk_probe_recbig import reading               # noqa: E402

ROWS = {"w65536": (1, "65536"), "w70000": (1, "70000"), "w100000": (1, "100000"),
        "w1e6": (1, "1000000"), "w2p24m": (1, "16777215"), "w2p24": (1, "16777216"),
        "w1e10": (1, "1E10"), "w1e30": (1, "1E30"),
        "l2000": (256, "2000"), "l3000": (256, "3000"),
        # round 2: where Overflow starts, and LOC after a failed write when the
        # previous LOC differs from n - 1 (the two rules round 1 cannot separate)
        "w1e8": (1, "1E8"), "w2p32m": (1, "4294967295#"), "w2p32": (1, "4294967296#"),
        "w1e9": (1, "1E9"),
        "s1full": (1, "1:PUT #1,1000000"), "s5get9": (1, "5:GET #1,9"),
        "s1e9": (1, "1:PUT #1,1E9")}
MACH = {"CF": "National_CF-3300", "ZB": "C-BIOS_MSX1_EU_REPACK_DISK"}


def main():
    args = sys.argv[1:]
    side = args.pop(0) if args and args[0] in MACH else "CF"
    for name in args or list(ROWS):
        ln, n = ROWS[name]
        prog = ["10 ON ERROR GOTO 90",
                f'20 OPEN "R.DAT" AS #1 LEN={ln}:FIELD #1,1 AS A$:LSET A$="X"',
                f"40 PUT #1,{n}",
                '50 PRINT "[";LOF(1);LOC(1);"]":CLOSE:END',
                '90 PRINT "[ERR";ERR;LOC(1);"]":END', "RUN"]
        dsk = probe_tmp.tmp(f"recwide_{name}_{side}.dsk")
        shutil.copyfile(os.path.join(REPO, "disk", "test720.dsk"), dsk)
        got = reading(omsx_repl.run_cases(MACH[side], [("direct", ["SCREEN 0", "NEW"] + prog)],
                                          batch=False, diska=dsk,
                                          run_gap=20.0 if side == "CF" else 300.0)[0])
        print(f"{side} {name:8s} PUT #1,{n:9s} LEN={ln:<3d} {got}", flush=True)
    print(__import__("probe_refcache").summary())


if __name__ == "__main__":
    main()
