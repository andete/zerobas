#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""Decode probes/bios/spec/xsubknj.asm's capture (D-MSX2SPEC, docs/msx2/sub/KNJPRT.md).

    python3 scratchpad/xsubknj_decode.py scratchpad/AE_xsubknj_msx2.out

Per machine and case: the registers, IFF, GXPOS / GYPOS / GRPACX / GRPACY after, and the window (X 12-35, Y 12-35)
as one hex digit per dot ('.' = the preset colour 3 untouched); the cell drawn sits at X 16-31, Y 16-31 (columns /
rows 4-19 of the picture), and a per-colour dot count.
"""
import re
import sys
from collections import Counter

CASES = ["A0 $3021", "A1 $3021", "A2 $3021", "A0 $2422", "A0 $4F53", "A0 $3021 XOR", "A0 $0000", "A3 $3021",
         "A0 $3021 at (13,15) GX/GY (20,19)", "A4 $3021", "A5 $3021", "A0 $0021", "A0 $2100", "A0 $2120",
         "A0 $3021 colours $15/$24", "A0 $2220", "A$FF $3021"]


def caps(path):
    row = None
    for line in open(path):
        m = re.match(r"===== \S+ (\w+): (\S+) vs (\S+) =====", line)
        if m:
            row = (m.group(2), m.group(3))
        m = re.match(r"\s+CAP (ref |ours): ([0-9a-f]+)", line)
        if m and row:
            yield row[0] if m.group(1) == "ref " else row[1], bytes.fromhex(m.group(2))


for name, c in caps(sys.argv[1]):
    c = c + bytes(max(0, 0x1600 - len(c)))
    print(f"## {name}: finished={c[0] == 0xA5} cases={c[1]}")
    for k in range(c[1]):
        r = c[2 + 320 * k: 2 + 320 * (k + 1)]
        if r[18] != 0xEE:
            print(f"  case {k}: SENTINEL MISSING"); continue
        w = lambda i: r[i] | r[i + 1] << 8
        print(f"  case {k} ({CASES[k]}): A={r[1]:02X} F={r[2]:02X} BC={r[4]:02X}{r[3]:02X} DE={r[6]:02X}{r[5]:02X} "
              f"HL={r[8]:02X}{r[7]:02X} IFF={r[9]} S#2first={r[19]:02X} GX/GY={w(10)}/{w(12)} GRPACX/Y={w(14)}/{w(16)}")
        dots = []
        for y in range(24):
            row = ""
            for b in r[32 + 12 * y: 44 + 12 * y]:
                row += f"{b >> 4:X}{b & 15:X}"
            dots.append(row)
        cnt = Counter("".join(dots))
        print("     colours: " + " ".join(f"{k}:{v}" for k, v in sorted(cnt.items())))
        for y, row in enumerate(dots):
            print(f"     {12 + y:3} " + row.replace("3", "."))
