#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""D-MSX2SPEC goldfish pass 1: decode probes/bios/spec/xsubscan2.asm (SCANR / SCANL): per case A / F / HL / DE,
CLOC / CMASK, CSAVEA / CSAVEM (markers in: $1357 / $2468), IFF, the OUT $99 log as register writes, the OUT $9B log,
and line 50 from X 20 ('.' = 0, '#' = the border $0F, digits = the colour).
    python3 scratchpad/xsubscan2_decode.py RUNFILE [--side ref|ours]"""
import re
import sys

NAMES = ["SCANR B0 DE1", "SCANR B1 DE1", "SCANR B$80 DE1", "SCANR DE2, borders 60-62", "SCANR DE3, borders 60-62",
         "SCANR DE4, borders 60-62", "SCANR DE$7FFF", "SCANR DE$8000", "SCANR DE2", "SCANR, $07 at X80",
         "SCANL, $07 at X45", "SCANL", "SCANR, line $07", "SCANL, line $07", "SCANR DE0 on a border", "SCANL B0"]
CAP0 = 0xC001


def parse99(log):
    out = []
    for i in range(0, len(log) - 1, 2):
        v, c = log[i], log[i + 1]
        out.append(f"R#{c & 63}={v:02X}" if c & 0x80 else f"addr({v:02X},{c:02X})")
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
            r = b[2 + 128 * k: 2 + 128 * (k + 1)]
            w = lambda o: r[o] | r[o + 1] << 8  # noqa: E731
            l99 = b[w(16) - CAP0: w(18) - CAP0]
            l9b = b[w(20) - CAP0: w(22) - CAP0]
            print(f"  {r[0]} {NAMES[r[0]]}: A={r[1]:02X} F={r[2]:02X} HL={w(3)} DE={w(5):04X} CLOC={w(7)} CMASK={r[9]}"
                  f" CSAVEA={w(10):04X} CSAVEM={w(12):04X} IFF={r[14]}")
            print(f"     $99 ({len(l99)}): " + " ".join(parse99(l99)))
            print(f"     $9B ({len(l9b)}): " + l9b.hex(" "))
            line = "".join("." if v == 0 else ("#" if v == 0x0F else f"{v:X}"[-1]) for v in r[32:128])
            print("     x20  " + line)
            print("          " + "".join(str((20 + i) // 10 % 10) if (20 + i) % 10 == 0 else " " for i in range(96)))


if __name__ == "__main__":
    main()
