#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""D-NMSHOST: diff the system area's DATA cells ($F39A-$FD99) as the NMS 1200's INIT finds them, VG-8020 vs zerobas
(the SYSDATA lines scratchpad/nmshost_probe.py writes at the cartridge's first code), named by zerobas's own
basic/sysvars.inc (the published MSX names it uses). Cells that legitimately differ by machine (JIFFY, the key buffer
contents, the cursor ...) are listed like the rest -- judge them per row.

    python3 scratchpad/sysdata_diff.py REF.log ZB.log
"""
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = 0xF39A


def names():
    """address -> (name, width) from basic/sysvars.inc (published cells, $F39A-$FD99)"""
    out = {}
    for f in [os.path.join(ROOT, "basic", "sysvars.inc")] + glob.glob(os.path.join(ROOT, "basic", "*.inc")):
        for ln in open(f, errors="replace"):
            m = re.match(r"([A-Za-z_][A-Za-z0-9_]*)\s+equ\s+\$([0-9A-Fa-f]{4})\b(.*)", ln)
            if not m:
                continue
            a = int(m.group(2), 16)
            if not BASE <= a <= 0xFD99 or a in out:
                continue
            w = re.search(r"\((\d+)\)", m.group(3))
            out[a] = (m.group(1), int(w.group(1)) if w else 1)
    return out


def snap(path):
    for ln in open(path, errors="replace"):
        if ln.startswith("SYSDATA "):
            return bytes.fromhex(ln.split()[1])
    sys.exit(f"no SYSDATA line in {path}")


def main(ref, zb):
    r, z = snap(ref), snap(zb)
    nm = names()
    cells = sorted(nm.items())
    covered = set()
    print("cell      name                ref                      zerobas")
    for a, (n, w) in cells:
        i = a - BASE
        rv, zv = r[i:i + w], z[i:i + w]
        covered.update(range(a, a + w))
        if rv != zv:
            print(f"${a:04X} {w:3d}  {n:18s}  {rv.hex().upper():24s} {zv.hex().upper()}")
    rest = [BASE + i for i in range(len(r)) if r[i] != z[i] and BASE + i not in covered]
    print(f"\n{len(rest)} differing byte(s) in cells zerobas does not name:")
    run = []
    for a in rest + [None]:
        if run and (a is None or a != run[-1] + 1):
            s, e = run[0], run[-1]
            print(f"  ${s:04X}-${e:04X}  ref {r[s - BASE:e - BASE + 1].hex().upper()[:32]}  zb {z[s - BASE:e - BASE + 1].hex().upper()[:32]}")
            run = []
        if a is not None:
            run.append(a)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
