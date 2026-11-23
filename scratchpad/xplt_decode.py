#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""D-MSX2SPEC: decode probes/bios/spec/xplt.asm (the palette calls).  python3 scratchpad/xplt_decode.py RUNFILE [--side ref|ours]"""
import re
import sys

STEPS = ["SCREEN 5", "INIPLT", "SETPLT 5 :=$73/$04", "GETPLT 5", "table := pattern", "GETPLT 5", "RSTPLT", "GETPLT 5",
         "SCREEN 1", "INIPLT", "SCREEN 0/40", "INIPLT", "SCREEN 0/80", "INIPLT", "SCREEN 8", "INIPLT", "SETPLT 5 (S8)"]


def main():
    side = sys.argv[sys.argv.index("--side") + 1] if "--side" in sys.argv else "ref"
    for blk in re.split(r"^===== ", open(sys.argv[1]).read(), flags=re.M)[1:]:
        m = re.search(rf"CAP {'ref ' if side == 'ref' else 'ours'}: ([0-9a-f]+)", blk)
        if not m:
            continue
        b = bytes.fromhex(m.group(1)) + bytes(3000)
        print("#", blk.split("\n", 1)[0].split(".asm ")[-1].split(" =")[0], side)
        for k in range(b[1]):
            r = b[2 + 96 * k: 98 + 96 * k]
            print(f"  {k:2} {STEPS[k]:20} A={r[0]:02X} F={r[1]:02X} B={r[2]:02X} C={r[3]:02X} D={r[4]:02X} E={r[5]:02X}")
            print(f"     palette {r[6:38].hex()}")
            print(f"     table   {r[38:86].hex()}")


if __name__ == "__main__":
    main()
