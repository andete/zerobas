#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""D-MSX2SPEC: decode probes/bios/spec/xsubgpp.asm (GRPPRT): GRPACX / GRPACY after and the window as a pixel grid
(X 8-23, Y 9-18; '+' = the $0F preset untouched).  python3 scratchpad/xsubgpp_decode.py RUNFILE [--side ref|ours]"""
import re
import sys

NAMES = ["'A' PSET SCREEN 8", "'A' TIMP SCREEN 8", "'A' SCREEN 5", "CR", "'A' at X 250", "'A' at Y 207", "'A' SCREEN 2"]


def main():
    side = sys.argv[sys.argv.index("--side") + 1] if "--side" in sys.argv else "ref"
    for blk in re.split(r"^===== ", open(sys.argv[1]).read(), flags=re.M)[1:]:
        m = re.search(rf"CAP {'ref ' if side == 'ref' else 'ours'}: ([0-9a-f]+)", blk)
        if not m:
            continue
        b = bytes.fromhex(m.group(1)) + bytes(3000)
        print("#", blk.split("\n", 1)[0].split(".asm ")[-1].split(" =")[0], side)
        for k in range(b[1]):
            r = b[2 + 176 * k: 178 + 176 * k]
            print(f"  {NAMES[r[0]]}: A={r[1]:02X} F={r[2]:02X} IFF={r[3]} GRPACX={r[4] | r[5] << 8} GRPACY={r[6] | r[7] << 8}")
            if r[0] in (0, 1, 2):
                for y in range(10):
                    row = r[16 + 16 * y: 32 + 16 * y]
                    if r[0] == 2:
                        px = "".join(f"{v >> 4:X}{v & 15:X}" for v in row)
                    else:
                        px = "".join(f"{v:X}"[-1] for v in row)
                    print(f"     y{9 + y:2} " + px.replace("F", "+"))


if __name__ == "__main__":
    main()
