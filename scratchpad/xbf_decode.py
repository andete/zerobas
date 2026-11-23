#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""D-MSX2SPEC: decode probes/bios/spec/xbf.asm (BIGFIL) -- per case the registers after, R#14 after, IFF, and per
VRAM window which bytes read $C7 (filled), $5A (the preset, untouched) or other.
    python3 scratchpad/xbf_decode.py RUNFILE [--side ref|ours]"""
import re
import sys

NAMES = ["VA-1 $1231/8", "VA-3 AC2 $C120/8", "VA-5 AC3 $C120/8", "VA-11 S1 AC1", "VA-8 S1 $C120", "BF-1 $FFF8/16",
         "BF-2 $3FF8/16", "BF-3 S1 $3FF8/16", "BF-4 BC 0", "BF-5 BC 1", "BF-5 BC $100", "BF-6 EI"]
# the windows, as the probe's table lists them: (17-bit address, length)
WINS = [[(0x01229, 16)], [(0x1C11C, 16), (0x0C11C, 16), (0x1411C, 16), (0x0411C, 16)],
        [(0x1411C, 16), (0x1C11C, 16), (0x0411C, 16), (0x0C11C, 16)],
        [(0x0C11C, 16), (0x0011C, 16), (0x00156, 16), (0x1411C, 16)],
        [(0x0C11C, 16), (0x0011C, 16), (0x0411C, 16), (0x1C11C, 16)],
        [(0x0FFF4, 12), (0x10000, 12), (0x00000, 12), (0x1FFF4, 12)],
        [(0x03FF4, 12), (0x04000, 12), (0x00000, 12), (0x1C000, 12)],
        [(0x03FF4, 12), (0x04000, 12), (0x00000, 12), (0x10000, 12)],
        [(0x07FFC, 8), (0x0FFFC, 8), (0x17FFC, 8), (0x18000, 4)], [(0x07FFC, 8)], [(0x080F8, 16), (0x07FF8, 16)],
        [(0x01229, 16)]]


def main():
    side = sys.argv[sys.argv.index("--side") + 1] if "--side" in sys.argv else "ref"
    t = open(sys.argv[1]).read()
    for blk in re.split(r"^===== ", t, flags=re.M)[1:]:
        head = blk.split("\n", 1)[0]
        m = re.search(rf"CAP {'ref ' if side == 'ref' else 'ours'}: ([0-9a-f]+)", blk)
        if not m:
            continue
        b = bytes.fromhex(m.group(1)) + bytes(2000)
        print("#", head.split(".asm ")[-1].split(" =")[0], side)
        for c in range(b[1]):
            r = b[2 + 80 * c: 82 + 80 * c]
            regs = f"A={r[0]:02X} F={r[1]:02X} BC={r[2]:02X}{r[3]:02X} DE={r[4]:02X}{r[5]:02X} HL={r[6]:02X}{r[7]:02X}" \
                   f" IXl={r[8]:02X} IYl={r[9]:02X} R14={r[10]:02X} IFF={r[11]} w99={r[12]}"
            ws = []
            for i, (a, n) in enumerate(WINS[c]):
                if not n:
                    continue
                bs = r[16 + 16 * i: 16 + 16 * i + n]
                filled = [a + k for k, v in enumerate(bs) if v == 0xC7]
                other = [f"{a + k:05X}={v:02X}" for k, v in enumerate(bs) if v not in (0xC7, 0x5A)]
                span = f"${filled[0]:05X}-${filled[-1]:05X}({len(filled)})" if filled else "none"
                ws.append(f"[{a:05X}+{n}: C7 {span}{' OTHER ' + ' '.join(other) if other else ''}]")
            print(f"  {c:2} {NAMES[c]:18} {regs}\n       " + " ".join(ws))


if __name__ == "__main__":
    main()
