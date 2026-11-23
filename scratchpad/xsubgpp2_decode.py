#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""D-MSX2SPEC goldfish pass 1: decode probes/bios/spec/xsubgpp2.asm (GRPPRT): per case A / F / IFF, GRPACX / GRPACY,
ATRBYT / FORCLR / BAKCLR after, BC / DE / HL / IX / IY after (in: B1C2 D3E4 A5F6 0089 9786), and the two windows,
row by row ('+' = the $0F preset untouched; SCREEN 5 two nibbles a byte; SCREEN 2 the bytes in hex).
    python3 scratchpad/xsubgpp2_decode.py RUNFILE [--side ref|ours]"""
import re
import sys

# name, window A (label, first row), window B (label, first row)
CASES = [("'A' S8 at (250,10)", "X240-255", 8, "X0-15", 8), ("'A' S8 at (250,207)", "X240-255", 196, "X0-15", 0),
         ("CR S8 at (10,207)", "X0-15", 196, "X0-15", 0), ("CR S8 at (10,203)", "X0-15", 196, "X0-15", 0),
         ("CR S8 at (10,204)", "X0-15", 196, "X0-15", 0), ("'A' S8 at (2,204)", "X0-15", 196, "X0-15", 0),
         ("'A' S2 at (10,10)", "pattern $0100+16r", 0, "colour $2100+16r", 0),
         ("'A' S5 at (11,10)", "X8-39", 8, "X40-71", 8), ("'A' S8 XOR (FORCLR 5 BAKCLR 3)", "X8-23", 8, "X24-39", 8),
         ("'A' S8 TIMP BAKCLR 0", "X8-23", 8, "X24-39", 8), ("'A' S8 PSET", "X8-23", 8, "X24-39", 8),
         ("'A' S8 TIMP FORCLR 0", "X8-23", 8, "X24-39", 8)]
SCR = [8, 8, 8, 8, 8, 8, 2, 5, 8, 8, 8, 8]
RL = 672


def row(v, scr):
    if scr == 2:
        return " ".join(f"{x:02X}" for x in v)
    if scr == 5:
        return "".join(f"{x >> 4:X}{x & 15:X}" for x in v).replace("F", "+").replace("0", ".")
    return "".join("+" if x == 0x0F else ("." if x == 0 else f"{x:X}"[-1]) for x in v)


def main():
    side = sys.argv[sys.argv.index("--side") + 1] if "--side" in sys.argv else "ref"
    for blk in re.split(r"^===== ", open(sys.argv[1]).read(), flags=re.M)[1:]:
        m = re.search(rf"CAP {'ref ' if side == 'ref' else 'ours'}: ([0-9a-f]+)", blk)
        if not m:
            continue
        b = bytes.fromhex(m.group(1)) + bytes(0x3000)
        if b[0] != 0xA5:
            sys.exit("FAIL: no $A5 sentinel")
        print("#", blk.split("\n", 1)[0].split(".asm ")[-1].split(" =")[0], side)
        for k in range(b[1]):
            r = b[2 + RL * k: 2 + RL * (k + 1)]
            w = lambda o: r[o] | r[o + 1] << 8  # noqa: E731
            name, la, ya, lb, yb = CASES[r[0]]
            print(f"  {r[0]} {name}: A={r[1]:02X} F={r[2]:02X} IFF={r[3]} GRPACX={w(4)} GRPACY={w(6)} ATRBYT={r[8]:02X}"
                  f" FORCLR={r[19]:02X} BAKCLR={r[20]:02X} BC={w(9):04X} DE={w(11):04X} HL={w(13):04X}"
                  f" IX={w(15):04X} IY={w(17):04X}")
            for lab, y0, off in ((la, ya, 32), (lb, yb, 352)):
                rows = [r[off + 16 * i: off + 16 * i + 16] for i in range(20)]
                print(f"    window {lab}:")
                for i, v in enumerate(rows):
                    if any(x != 0x0F for x in v) or SCR[r[0]] == 2:
                        print(f"     r{y0 + i:3} " + row(v, SCR[r[0]]))


if __name__ == "__main__":
    main()
