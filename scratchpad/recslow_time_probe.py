#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-RECSLOW (2026-11-05): how many frames one far random PUT takes on a fresh
LEN=1 file -- `T=TIME:PUT #1,n:PRINT TIME-T`, then LOF and the record read back.
TIME is work-area RAM. Typed BASIC in, the screen out.

    python3 -u scratchpad/recslow_time_probe.py [CF|ZB]
"""
import os, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
sys.path.insert(0, os.path.join(REPO, "probes", "disk"))
import omsx_repl                                    # noqa: E402
import probe_tmp                                    # noqa: E402
import shutil
from disk_probe_recbig import reading               # noqa: E402

MACH = {"CF": "National_CF-3300", "ZB": "C-BIOS_MSX1_EU_REPACK_DISK"}
for side in sys.argv[1:] or list(MACH):
    for n in ("32767", "65535"):
        prog = [f'20 OPEN "R.DAT" AS #1 LEN=1:FIELD #1,1 AS A$:LSET A$="Q"',
                f"30 T=TIME:PUT #1,{n}:T=TIME-T",
                f'40 LSET A$="-":GET #1,{n}:PRINT "[";T;LOF(1);A$;"]":CLOSE:END']
        dsk = probe_tmp.tmp(f"recslow_t_{side}_{n}.dsk")
        shutil.copyfile(os.path.join(REPO, "disk", "test720.dsk"), dsk)
        scr = omsx_repl.run_cases(MACH[side], [("direct", ["SCREEN 0", "NEW"] + prog + ["RUN"])],
                                  batch=False, diska=dsk, run_gap=150.0)[0]
        print(f"{side} {n:6s} {reading(scr)}", flush=True)
print(__import__("probe_refcache").summary())
