#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""D-MSX2SPEC: decode probes/bios/spec/xsubblt.asm (BLTVV / BLTVM / BLTMV).
    python3 scratchpad/xsubblt_decode.py RUNFILE [--side ref|ours]"""
import re
import struct
import sys

NAMES = ["BLTVV (8,8) 8x4 -> (40,8)", "BLTVV XOR over $FF", "BLTVV ARG DIX", "BLTMV -> $D200", "BLTVM $D100 -> (40,20)",
         "BLTVV SCREEN 5 SX 9 -> 40",
         # goldfish pass 1 (2026-11-23)
         "BLTVV S5 SX 9 -> DX 41 NX 5 over $BC", "BLTVV DIX overlap SX 15 -> DX 19", "BLTVV DIY overlap SY 11 -> DY 13",
         "BLTVM block NX/NY garbage", "BLTMV -> $D200 (96 B)", "BLTMV, VRAM window", "BLTVV case 0 via SUBROM",
         "BLTMV case 3 via SUBROM"]
PRE = [0x00, 0xFF, 0x00, 0xEE, 0x00, 0x00, 0xBC, None, None, 0x00, 0xEE, None, 0x00, 0xEE]
RAM = {3: 44, 10: 96, 13: 44}


def main():
    side = sys.argv[sys.argv.index("--side") + 1] if "--side" in sys.argv else "ref"
    for blk in re.split(r"^===== ", open(sys.argv[1]).read(), flags=re.M)[1:]:
        m = re.search(rf"CAP {'ref ' if side == 'ref' else 'ours'}: ([0-9a-f]+)", blk)
        if not m:
            continue
        b = bytes.fromhex(m.group(1)) + bytes(3000)
        print("#", blk.split("\n", 1)[0].split(".asm ")[-1].split(" =")[0], side)
        for k in range(b[1]):
            r = b[2 + 128 * k: 130 + 128 * k]
            f = struct.unpack("<6H", r[4:16]) + tuple(r[16:19])
            print(f"  {NAMES[r[0]]}: A={r[1]:02X} F={r[2]:02X} IFF={r[3]} block after SX={f[0]} SY={f[1]} DX={f[2]:X} DY={f[3]}"
                  f" NX={f[4]} NY={f[5]} CD={f[6]:02X} ARG={f[7]:02X} LOG={f[8]:02X} S#2-on-return={r[19]:02X}")
            w = r[32:128]
            if r[0] in RAM:
                print("     RAM " + w[:RAM[r[0]]].hex())
            else:
                for y in range(6):
                    print("     " + " ".join(".." if v == PRE[r[0]] else f"{v:02X}" for v in w[16 * y: 16 * y + 16]))


if __name__ == "__main__":
    main()
