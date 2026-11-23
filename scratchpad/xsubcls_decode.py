#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""D-MSX2SPEC: decode probes/bios/spec/xsubcls.asm (sub-ROM CHGCLR / CLS).
    python3 scratchpad/xsubcls_decode.py RUNFILE [--side ref|ours]"""
import re
import sys

CASES = [("CHGCLR", m, 0xC5) for m in (0, 1, 2, 5, 8)] + [("CLS", m, bk) for m in (0, 1, 2, 3, 5, 6, 7, 8) for bk in (6, 0xC5)]
# goldfish pass 1 (2026-11-23): cases 21-36
CASES += [("CLS", "2 ends", 6), ("CLS", "3 ends", 6)] + [("CLS", 6, bk) for bk in (0, 1, 2, 3)] + [
    ("CHGCLR", "1 extent", 0xC5)] + [("CHGCLR", m, 0xC5) for m in (3, 4, 6, 7)] + [
    ("CHGCLR", "0 EI", 0xC5), ("CLS", "0 EI", 0xC5), ("CHGCLR", "VDP5/SCRMOD0", 0xC5),
    ("CHGCLR", "VDP0/SCRMOD5", 0xC5), ("CLS", "VDP5/SCRMOD0", 0xC5)]


def summ(w):
    if len(set(w)) == 1:
        return f"16x{w[0]:02X}"
    return w.hex()


def main():
    side = sys.argv[sys.argv.index("--side") + 1] if "--side" in sys.argv else "ref"
    for blk in re.split(r"^===== ", open(sys.argv[1]).read(), flags=re.M)[1:]:
        m = re.search(rf"CAP {'ref ' if side == 'ref' else 'ours'}: ([0-9a-f]+)", blk)
        if not m:
            continue
        b = bytes.fromhex(m.group(1)) + bytes(3000)
        print("#", blk.split("\n", 1)[0].split(".asm ")[-1].split(" =")[0], side)
        for k in range(b[1]):
            r = b[2 + 64 * k: 66 + 64 * k]
            op, md, bk = CASES[r[0]]
            ws = " | ".join(summ(r[16 + 16 * i: 32 + 16 * i]) for i in range(3))
            print(f"  {op:6} S{md} BAK=${bk:02X}: A={r[1]:02X} F={r[2]:02X} IFF={r[3]} R7={r[4]:02X} "
                  f"FOR/BAK/BDR={r[5]:02X}/{r[6]:02X}/{r[7]:02X}{f' SCRMOD={r[8]:02X}' if r[0] >= 21 else ''}  {ws}")


if __name__ == "__main__":
    main()
