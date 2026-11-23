#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""D-MSX2SPEC: decode probes/bios/spec/xplt.asm (the palette calls).  python3 scratchpad/xplt_decode.py RUNFILE [--side ref|ours]"""
import re
import sys

STEPS = ["SCREEN 5", "INIPLT", "SETPLT 5 :=$73/$04", "GETPLT 5", "table := pattern", "GETPLT 5", "RSTPLT", "GETPLT 5",
         "SCREEN 1", "INIPLT", "SCREEN 0/40", "INIPLT", "SCREEN 0/80", "INIPLT", "SCREEN 8", "INIPLT", "SETPLT 5 (S8)"]
STEPS += ['SCREEN 1', 'the table := the pattern', 'RSTPLT, D $C3 E $3C', 'GETPLT 5, D $C3 E $3C', 'SETPLT 5 := R 7, B 3, G 4', 'SCREEN 0, width 40', 'the table := the pattern', 'RSTPLT, D $C3 E $3C', 'GETPLT 5, D $C3 E $3C', 'SETPLT 5 := R 7, B 3, G 4', 'SCREEN 0, width 80', 'the table := the pattern', 'RSTPLT, D $C3 E $3C', 'GETPLT 5, D $C3 E $3C', 'SCREEN 8', 'the table := the pattern', 'RSTPLT, D $C3 E $3C', 'GETPLT 5, D $C3 E $3C', 'SCREEN 5', 'the table := $FF', 'GETPLT 5: bits 3 / 7', 'RSTPLT from $FF', 'the table := $88', 'GETPLT 5', 'the pattern at $0400', 'the pattern at $0F00', 'the pattern at $2020', 'the pattern at $1B80', 'the pattern at $7680', 'the pattern at $FA80', 'INIPLT (SCREEN 5)', 'read $0400', 'read $0F00', 'read $2020', 'read $1B80', 'read $FA80', 'the pattern at $7680', 'SETPLT 5 (SCREEN 5)', 'read $0400', 'read $0F00', 'read $2020', 'read $1B80', 'read $FA80']  # goldfish pass 1 (2026-11-23), steps 17-59


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
            print(f"  {k:2} {STEPS[k]:28} A={r[0]:02X} F={r[1]:02X} B={r[2]:02X} C={r[3]:02X} D={r[4]:02X} E={r[5]:02X} R16={r[86]:02X} vptr={r[87] | r[88] << 8:04X}")
            print(f"     palette {r[6:38].hex()}")
            print(f"     table   {r[38:86].hex()}")


if __name__ == "__main__":
    main()
