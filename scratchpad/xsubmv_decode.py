#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""D-MSX2SPEC: decode probes/bios/spec/xsubmv.asm (the cursor moves).
    python3 scratchpad/xsubmv_decode.py RUNFILE [--side ref|ours]"""
import re
import sys

N = {0xA5: "RIGHTC", 0xAD: "LEFTC", 0xBD: "UPC", 0xB5: "DOWNC", 0xA1: "TRIGHT", 0xA9: "TLEFTC", 0xB9: "TUPC",
     0xB1: "TDOWNC"}


def main():
    side = sys.argv[sys.argv.index("--side") + 1] if "--side" in sys.argv else "ref"
    for blk in re.split(r"^===== ", open(sys.argv[1]).read(), flags=re.M)[1:]:
        m = re.search(rf"CAP {'ref ' if side == 'ref' else 'ours'}: ([0-9a-f]+)", blk)
        if not m:
            continue
        b = bytes.fromhex(m.group(1)) + bytes(3000)
        n = b[1] | b[2] << 8
        print("#", blk.split("\n", 1)[0].split(".asm ")[-1].split(" =")[0], side, n)
        for k in range(n):
            r = b[3 + 12 * k: 15 + 12 * k]
            print(f"  S{r[0]} x{r[10]:3} y{r[11]:3} {N.get(r[1], hex(r[1])):6} CLOC {r[2] | r[3] << 8:04X}/{r[4]:02X} -> "
                  f"{r[5] | r[6] << 8:04X}/{r[7]:02X}  A={r[8]:02X} F={r[9]:02X} C={r[9] & 1}")


if __name__ == "__main__":
    main()
