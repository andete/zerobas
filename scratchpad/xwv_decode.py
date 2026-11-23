#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""D-MSX2SPEC: decode probes/bios/spec/xwv.asm (sub-ROM WRTVDP / VDPSTA). A copy cell "changed" when it differs
from that cell's most common value over all the cases (each case's copies are put back before the next).
    python3 scratchpad/xwv_decode.py RUNFILE [--side ref|ours]"""
import collections
import re
import sys


def main():
    side = sys.argv[sys.argv.index("--side") + 1] if "--side" in sys.argv else "ref"
    for blk in re.split(r"^===== ", open(sys.argv[1]).read(), flags=re.M)[1:]:
        m = re.search(rf"CAP {'ref ' if side == 'ref' else 'ours'}: ([0-9a-f]+)", blk)
        if not m:
            continue
        b = bytes.fromhex(m.group(1)) + bytes(4000)
        print("#", blk.split("\n", 1)[0].split(".asm ")[-1].split(" =")[0], side)
        recs = [b[2 + 48 * k: 50 + 48 * k] for k in range(b[1])]
        cells = [[r[16 + i] for r in recs] for i in range(32)]
        base = [collections.Counter(c).most_common(1)[0][0] for c in cells]
        names = [f"${0xF3DF + i:04X}" for i in range(8)] + [f"${0xFFE7 + i:04X}" for i in range(25)]
        for r in recs:
            ch = [f"{names[i]}={r[16 + i]:02X}" for i in range(32) if r[16 + i] != base[i]]
            log = " ".join(f"{r[8 + j]:02X}" for j in range(min(r[7], 6)))
            print(f"  C={r[0]:2} B={r[1]:02X} reg={r[2]:02X} A={r[3]:02X} F={r[4]:02X} B'={r[5]:02X} C'={r[6]:02X} "
                  f"w99={r[7]} [{log}] w9B={r[14]} copies: {' '.join(ch) or '-'}")
        v = b[2 + 48 * 43: 2 + 48 * 43 + 40]
        print("  VDPSTA: " + " ".join(f"S#{v[4 * k + 3]}:A={v[4 * k]:02X}/dbg={v[4 * k + 2]:02X}" for k in range(10)))


if __name__ == "__main__":
    main()
