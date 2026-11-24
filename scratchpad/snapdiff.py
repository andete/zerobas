#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""D-NMSHOST item 4: compare dosref_probe.py DOSREF_SNAP runs. Per run: the published cells ($F39A-$FD99, named by
basic/sysvars.inc) that change between S0 (H.RUNC entry) and S1 (the first H.PHYD); then S1 of each run against the
first (the reference): differing cells and VRAM ranges.

    python3 scratchpad/snapdiff.py REF.out RUN2.out [RUN3.out ...]

The runs carry VRAM (SNAPVRAM: each machine's font, ROM content) -- never commit those lines.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sysdata_diff import names  # noqa: E402

BASE = 0xF39A


def load(path):
    d, v = {}, {}
    for ln in open(path, errors="replace"):
        p = ln.split()
        if ln.startswith("SNAPDATA "):
            d[p[1]] = bytes.fromhex(p[2])
        elif ln.startswith("SNAPVRAM "):
            v[p[1]] = bytes.fromhex(p[2])
    return d, v


def cells(a, b, nm):
    out = []
    i = 0
    while i < len(a):
        if a[i] != b[i]:
            addr = BASE + i
            name = next((f"{n}+{addr - c}" if addr != c else n for c, (n, w) in nm.items() if c <= addr < c + w), "?")
            out.append(f"${addr:04X} {name}: {a[i]:02X}->{b[i]:02X}")
        i += 1
    return out


def ranges(a, b):
    out, run = [], None
    for i in range(len(a)):
        if a[i] != b[i]:
            if run and i == run[1] + 1:
                run[1] = i
            else:
                if run:
                    out.append(run)
                run = [i, i]
    if run:
        out.append(run)
    return out


def main(paths):
    nm = names()
    runs = [(p, *load(p)) for p in paths]
    for p, d, v in runs:
        ch = cells(d["S0"], d["S1"], nm)
        print(f"### {os.path.basename(p)}: {len(ch)} published-area byte(s) change S0 -> S1")
        for c in ch:
            print("   ", c)
    rp, rd, rv = runs[0]
    for p, d, v in runs[1:]:
        print(f"### S1: {os.path.basename(p)} vs {os.path.basename(rp)}")
        for c in cells(rd["S1"], d["S1"], nm):
            print("    cell", c, "(ref->this)")
        rr = ranges(rv["S1"], v["S1"])
        print(f"    VRAM: {sum(e - s + 1 for s, e in rr)} differing byte(s) in {len(rr)} range(s)")
        for s, e in rr[:20]:
            print(f"      ${s:04X}-${e:04X}")


if __name__ == "__main__":
    main(sys.argv[1:])
