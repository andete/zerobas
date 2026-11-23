#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""D-MSX2SPEC: decode probes/bios/spec/xspr2.asm (the sub-ROM sprite calls).
    python3 scratchpad/xspr2_decode.py RUNFILE [--side ref|ours]"""
import re
import sys

OPS = ("CLRSPR", "CALPAT", "CALATR", "GSPSIZ", "GETPAT")


def main():
    side = sys.argv[sys.argv.index("--side") + 1] if "--side" in sys.argv else "ref"
    for blk in re.split(r"^===== ", open(sys.argv[1]).read(), flags=re.M)[1:]:
        m = re.search(rf"CAP {'ref ' if side == 'ref' else 'ours'}: ([0-9a-f]+)", blk)
        if not m:
            continue
        b = bytes.fromhex(m.group(1)) + bytes(3000)
        print("#", blk.split("\n", 1)[0].split(".asm ")[-1].split(" =")[0], side)
        for k in range(b[1]):
            r = b[2 + 32 * k: 34 + 32 * k]
            print(f"  {OPS[r[0]]:6} A={r[1]:02X} S{r[2]} {'16' if r[3] else ' 8'}  ->  A={r[4]:02X} F={r[5]:02X} "
                  f"HL={r[6]:02X}{r[7]:02X} PATWRK={r[8:16].hex()} ATR={r[16:32].hex()}")


if __name__ == "__main__":
    main()
