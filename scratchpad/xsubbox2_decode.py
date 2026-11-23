#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""D-MSX2SPEC goldfish pass 1: decode probes/bios/spec/xsubbox2.asm (NVBXLN / NVBXFL / DOGRPH): per case A / F, the
cells, R#36-R#45 after, the OUT $99 log parsed as register writes (`R#n=v`; a non-register pair as `addr`), the OUT $9B
log (indirect register data, after R#17), and the window (SCREEN 8: a byte a pixel; SCREEN 5: two nibbles a byte),
X 8-23 / Y 9-16.    python3 scratchpad/xsubbox2_decode.py RUNFILE [--side ref|ours]"""
import re
import sys

NAMES = ["NVBXLN (20,10)-(10,15)", "NVBXLN (10,15)-(20,10)", "NVBXLN (12,11)-(19,14)", "NVBXLN (19,14)-(12,11)",
         "NVBXLN XOR over $0C", "NVBXLN OR over $08", "NVBXLN TIMP over $0C", "NVBXFL (10,10)-(20,15)",
         "NVBXFL (20,15)-(10,10)", "NVBXFL SCREEN 5 (11,10)-(20,15)", "DOGRPH BC/DE (11,14) GX/GY (21,11)",
         "DOGRPH BC/DE (21,11) GX/GY (11,14)", "DOGRPH OR over $08", "NVBXFL XOR over $0C",
         "DOGRPH BC/DE (11,11) GX/GY (21,14)", "DOGRPH BC/DE (21,14) GX/GY (11,11)"]
PRESET = {4: 0x0C, 5: 0x08, 6: 0x0C, 12: 0x08, 13: 0x0C}
CAP0 = 0xC001


def parse99(log):
    out, i = [], 0
    while i + 1 < len(log):
        v, c = log[i], log[i + 1]
        out.append(f"R#{c & 63}={v:02X}" if c & 0x80 else f"addr({v:02X},{c:02X})")
        i += 2
    if i < len(log):
        out.append(f"odd:{log[i]:02X}")
    return out


def main():
    side = sys.argv[sys.argv.index("--side") + 1] if "--side" in sys.argv else "ref"
    for blk in re.split(r"^===== ", open(sys.argv[1]).read(), flags=re.M)[1:]:
        m = re.search(rf"CAP {'ref ' if side == 'ref' else 'ours'}: ([0-9a-f]+)", blk)
        if not m:
            continue
        b = bytes.fromhex(m.group(1)) + bytes(0x2000)
        if b[0] != 0xA5:
            sys.exit("FAIL: no $A5 sentinel")
        print("#", blk.split("\n", 1)[0].split(".asm ")[-1].split(" =")[0], side)
        for k in range(b[1]):
            r = b[2 + 160 * k: 162 + 160 * k]
            w = [r[4 + 2 * i] | r[5 + 2 * i] << 8 for i in range(4)]
            lp = [r[22 + 2 * i] | r[23 + 2 * i] << 8 for i in range(4)]
            l99 = b[lp[0] - CAP0: lp[1] - CAP0]
            l9b = b[lp[2] - CAP0: lp[3] - CAP0]
            print(f"  {k} {NAMES[r[0]]}: A={r[1]:02X} F={r[2]:02X} GX,GY={w[0]},{w[1]} GRPAC={w[2]},{w[3]}"
                  f" R36-45={r[12:22].hex()}")
            print(f"     $99 ({len(l99)}): " + " ".join(parse99(l99)))
            print(f"     $9B ({len(l9b)}): " + l9b.hex(" "))
            pre = PRESET.get(r[0], 0)
            for y in range(8):
                row = r[32 + 16 * y: 48 + 16 * y]
                if r[0] == 9:
                    px = "".join(f"{v >> 4:X}{v & 15:X}" for v in row).replace("0", ".")
                else:
                    px = "".join("+" if v == pre and pre else ("." if v == 0 else f"{v:X}"[-1]) for v in row)
                print(f"     y{9 + y:2} x8.. " + px)


if __name__ == "__main__":
    main()
