#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""D-MSX2SPEC: decode probes/bios/spec/xsubbox.asm (NVBXLN / NVBXFL / DOGRPH): each window as a grid of pixel
values (SCREEN 8: a byte a pixel; SCREEN 5: two nibbles a byte), X 8-23 across, Y 9-16 down.
    python3 scratchpad/xsubbox_decode.py RUNFILE [--side ref|ours]"""
import re
import sys

NAMES = ["NVBXLN (10,10)-(20,15)", "NVBXLN (20,15)-(10,10)", "NVBXFL (10,10)-(20,15)", "NVBXFL (20,15)-(10,10)",
         "DOGRPH BC/DE (20,15) GX/GY (23,9) GRPAC (10,10)", "NVBXLN XOR over $0F", "NVBXFL SCREEN 5"]


def main():
    side = sys.argv[sys.argv.index("--side") + 1] if "--side" in sys.argv else "ref"
    for blk in re.split(r"^===== ", open(sys.argv[1]).read(), flags=re.M)[1:]:
        m = re.search(rf"CAP {'ref ' if side == 'ref' else 'ours'}: ([0-9a-f]+)", blk)
        if not m:
            continue
        b = bytes.fromhex(m.group(1)) + bytes(3000)
        print("#", blk.split("\n", 1)[0].split(".asm ")[-1].split(" =")[0], side)
        for k in range(b[1]):
            r = b[2 + 160 * k: 162 + 160 * k]
            cells = [r[4 + 2 * i] | r[5 + 2 * i] << 8 for i in range(4)]
            print(f"  {NAMES[r[0]]}: A={r[1]:02X} F={r[2]:02X} GX,GY={cells[0]},{cells[1]} GRPAC={cells[2]},{cells[3]}"
                  f" R36-45={r[12:22].hex()}")
            s5 = r[0] == 6
            for y in range(8):
                row = r[32 + 16 * y: 48 + 16 * y]
                if s5:
                    px = "".join(f"{v >> 4:X}{v & 15:X}" for v in row)
                    print(f"     y{9 + y:2} x8.. " + px.replace("0", "."))
                else:
                    print(f"     y{9 + y:2} x8.. " + "".join("." if v == 0 else ("+" if v == 0x0F and r[0] == 5 else f"{v:X}"[-1]) for v in row))


if __name__ == "__main__":
    main()
