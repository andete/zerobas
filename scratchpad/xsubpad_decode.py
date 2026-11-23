#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""Decode probes/bios/spec/xsubpad{,m,x}.asm's captures (D-MSX2SPEC, docs/msx2/sub/NEWPAD.md).

    python3 scratchpad/xsubpad_decode.py scratchpad/AE_xsubpad_msx2.out [more .out files] [--classes]

One table per run file: a row per call (n, function, path), a column per machine: A F IFF R15 BC DE HL.
--classes (for xsubpads / xsubpadg): per machine, the calls grouped by their result (A F IFF BC DE HL; R15 left
out -- the timer interrupt writes it), each group's function numbers listed.
"""
import re
import sys


def caps(path):
    row = None
    for line in open(path):
        m = re.match(r"===== \S+ (\w+): (\S+) vs (\S+) =====", line)
        if m:
            row = (m.group(2), m.group(3))
        m = re.match(r"\s+CAP (ref |ours): ([0-9a-f]+)", line)
        if m and row:
            yield row[0] if m.group(1) == "ref " else row[1], bytes.fromhex(m.group(2))


def recs(c):
    c = c + bytes(max(0, 0x400 - len(c)))
    if c[0] != 0xA5:
        return None
    out = []
    n = c[1]
    while 18 + 16 * n <= len(c) and c[2 + 16 * n + 13] == 0xEE:   # xsubpads: 257 calls, the count byte wraps
        n += 1
    for k in range(n):
        r = c[2 + 16 * k: 18 + 16 * k]
        if r[13] != 0xEE:
            out.append((r[0], r[1], "SENTINEL MISSING"))
            continue
        out.append((r[0], r[1], f"A={r[2]:02X} F={r[3]:02X} I={r[4]}{r[5]} R15={r[6]:02X} "
                                f"BC={r[8]:02X}{r[7]:02X} DE={r[10]:02X}{r[9]:02X} HL={r[12]:02X}{r[11]:02X}"))
    return out


def classes(path):
    for n, c in caps(path):
        cls = {}
        for k, (fn, pa, res) in enumerate(recs(c) or []):
            key = re.sub(r" R15=..", "", res)
            cls.setdefault(key, []).append(f"{k}:{fn}{'g' if pa else ''}")
        print(f"## {n}: {sum(len(v) for v in cls.values())} calls")
        for key, fns in cls.items():
            print(f"   {key}: {len(fns)} calls: {' '.join(fns)}")


if "--classes" in sys.argv:
    for path in sys.argv[1:]:
        if path != "--classes":
            classes(path)
    sys.exit(0)

for path in sys.argv[1:]:
    print(f"### {path}")
    m = {n: recs(c) for n, c in caps(path)}
    names = list(m)
    print("  n  fn path | " + " | ".join(n[:18] for n in names))
    for k in range(max(len(v or []) for v in m.values())):
        f = next(v[k] for v in m.values() if v and k < len(v))
        cells = [(m[n][k][2] if m[n] and k < len(m[n]) else "-") for n in names]
        print(f" {k:2} {f[0]:3} {'GTPAD' if f[1] else 'sub  '} | " + " | ".join(cells))
