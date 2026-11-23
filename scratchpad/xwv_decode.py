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
        if not any(b[0x0840: 0x0840 + 38]):
            continue                            # a run from before phases 3 / 4 (2026-11-23 goldfish pass 1)
        p4 = 0x1020
        sp = b[p4] | b[p4 + 1] << 8
        n3 = b[p4 + 2]
        print(f"  PHASE 3 ({n3} cases; whole $F380-$FFFE diff; SP=${sp:04X}):")
        for k in range(n3):
            r = b[0x0840 + 38 * k: 0x0840 + 38 * (k + 1)]
            log = " ".join(f"{r[4 + j]:02X}" for j in range(min(r[3], 8)))
            d = " ".join(f"${r[14 + 3 * j] | r[15 + 3 * j] << 8:04X}={r[16 + 3 * j]:02X}" for j in range(min(r[13], 8)))
            print(f"    C={r[0]:2} B={r[1]:02X} reg={r[2]:02X} w99={r[3]} [{log}] w9B={r[12]} diffs={r[13]}: {d or '-'}")
        for k, what in enumerate(("STATFL $5A, F pending, A 0", "STATFL $A5, at once, A 0", "STATFL $5A, A 1")):
            r = b[p4 + 3 + 12 * k: p4 + 15 + 12 * k]
            log = " ".join(f"{r[5 + j]:02X}" for j in range(min(r[4], 6)))
            print(f"    VDPSTA {what}: A={r[0]:02X} F={r[1]:02X} S#before={r[2]:02X} STATFL after={r[3]:02X} "
                  f"w99={r[4]} [{log}] IFF={r[11]}")


if __name__ == "__main__":
    main()
