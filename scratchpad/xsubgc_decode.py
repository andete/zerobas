#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""D-MSX2SPEC: decode probes/bios/spec/xsubgc.asm (MAPXYC / SETATR / SETC / READC / SCALXY).
    python3 scratchpad/xsubgc_decode.py RUNFILE [--side ref|ours]"""
import re
import sys


def s16(v):
    return v - 65536 if v & 0x8000 else v


def main():
    side = sys.argv[sys.argv.index("--side") + 1] if "--side" in sys.argv else "ref"
    for blk in re.split(r"^===== ", open(sys.argv[1]).read(), flags=re.M)[1:]:
        m = re.search(rf"CAP {'ref ' if side == 'ref' else 'ours'}: ([0-9a-f]+)", blk)
        if not m:
            continue
        b = bytes.fromhex(m.group(1)) + bytes(2000)
        print("#", blk.split("\n", 1)[0].split(".asm ")[-1].split(" =")[0], side)
        n = b[1]
        for k in range(n):
            r = b[3 + 16 * k: 19 + 16 * k]
            x, y = r[1] | r[2] << 8, r[3] | r[4] << 8
            print(f"  S{r[0]} ({x},{y}): CLOC=${r[5] | r[6] << 8:04X} CMASK=${r[7]:02X} READC={r[8]:02X} byte={r[9]:02X}"
                  f" ATRBYT={r[10]:02X} F(MAPXYC)={r[11]:02X}")
        o = 3 + 16 * n
        for k in range(b[2]):
            r = b[o + 8 * k: o + 8 + 8 * k]
            print(f"  SCALXY S{r[0]}: -> BC={s16(r[1] | r[2] << 8)} DE={s16(r[3] | r[4] << 8)} F={r[5]:02X} (carry {r[5] & 1})")


if __name__ == "__main__":
    main()
