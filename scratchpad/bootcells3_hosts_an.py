#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""D-BOOTCELLS step 3: print the candidate host spans of a bootcells3_hosts_probe.py log, one row per snapshot."""
import sys
snaps = [(l.split()[1], bytes.fromhex(l.split()[2])) for l in open(sys.argv[1]) if l.startswith("SNAP")]
B = 0xF39A
def show(lo, hi, label):
    print(f"-- {label} ${lo:04X}-${hi:04X}")
    for tag, d in snaps:
        print(f"  {tag:6s} {d[lo-B:hi-B+1].hex().upper()}")
show(0xF672, 0xF675, "MEMSIZ/STKTOP (control: CLEAR/MAXFILES moved them?)")
show(0xFB35, 0xFB40, "PLAY area (control: PLAY ran?)")
show(0xFCB3, 0xFCBA, "GXPOS..GRPACY (control: graphics ran?)")
show(0xFC4C, 0xFC50, "TRPTBL head (control: KEY trap)")
show(0xFC82, 0xFC9A, "TRPTBL reserved tail + RTYCNT")
show(0xFAF5, 0xFB34, "RS2IQ")
show(0xF6E8, 0xF6E9, "PARM1 head")
show(0xF66A, 0xF66D, "CONLO")
show(0xF6A5, 0xF6A5, "SUBFLG")
show(0xFD09, 0xFD10, "SLTWRK slot0")
ch = [a for a in range(len(snaps[0][1])) if len({d[a] for _, d in snaps}) == 1 and snaps[0][1][a] == 0]
print("never-nonzero bytes:", len(ch))
