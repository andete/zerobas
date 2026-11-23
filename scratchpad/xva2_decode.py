#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""D-MSX2SPEC: decode probes/bios/spec/xva2.asm's DATA section (goldfish pass 1, 2026-11-23).
    python3 scratchpad/xva2_decode.py RUNFILE [--side ref|ours]
The address-matrix records (cases 0-35) are decoded by scratchpad/xva_decode.py (cases 25-35 print by number).
Per data case and call: A, F, the registers after (preset BC $5AA5 DE $A55A IX $1357 IY $2468 BC' $1122 DE' $3344
HL' $5566 AF' $7788), the number of VRAM bytes that differ from the pattern, the first one's 17-bit address and byte;
for the two read calls, whether A equals the pattern byte at the address the same entry's write call landed on."""
import re
import struct
import sys

CALLS = ("main NRDVRM $0174", "main NWRVRM $0177", "sub NRDVRM $010D", "sub NWRVRM $0109")
DNAMES = ["D0 S5 AC0 $1234", "D1 S5 AC1 $1234", "D2 S1 AC1 $C123", "D3 S0/40 AC1 $D123", "D4 S8 AC1 $1234"]
KEYS = [0x5A, 0x7F, 0x14, 0x31, 0x46, 0x63, 0x08, 0x2D]
NCASES = 36


def pat(a):
    o = a & 0x3FFF
    return ((o & 0xFF) ^ (o >> 8) ^ KEYS[a >> 14]) & 0x7F


def main():
    side = sys.argv[sys.argv.index("--side") + 1] if "--side" in sys.argv else "ref"
    for blk in re.split(r"^===== ", open(sys.argv[1]).read(), flags=re.M)[1:]:
        m = re.search(rf"CAP {'ref ' if side == 'ref' else 'ours'}: ([0-9a-f]+)", blk)
        if not m:
            continue
        b = bytes.fromhex(m.group(1)) + bytes(4000)
        if b[0] != 0xA5 or b[1] != NCASES:
            sys.exit(f"REFUSED: finish mark {b[0]:02X}, case count {b[1]}")
        print("#", blk.split("\n", 1)[0].split(".asm ")[-1].split(" =")[0], side)
        o = 2 + NCASES * 64
        for d in range(len(DNAMES)):
            recs = [b[o + 32 * (4 * d + k): o + 32 * (4 * d + k) + 32] for k in range(4)]
            for r in recs:
                if r[30:32] != b"\xda\xda" or r[0] != d:
                    sys.exit(f"REFUSED: data record {d} sentinel / case byte wrong: {r.hex()}")
            landed = {}
            for k in (1, 3):
                r = recs[k]
                n = r[22] | r[23] << 8 | r[24] << 16
                landed[k - 1] = (r[25] | r[26] << 8 | r[27] << 16) if n else None
            for k, r in enumerate(recs):
                a, f = r[2], r[3]
                bc, de, hl, ix, iy, bc2, de2, hl2, af2 = struct.unpack("<9H", r[4:22])
                n = r[22] | r[23] << 8 | r[24] << 16
                fa = r[25] | r[26] << 8 | r[27] << 16
                line = (f"  {DNAMES[d]:19} {CALLS[k]:18} A={a:02X} F={f:02X} BC={bc:04X} DE={de:04X} HL={hl:04X}"
                        f" IX={ix:04X} IY={iy:04X} BC'={bc2:04X} DE'={de2:04X} HL'={hl2:04X} AF'={af2:04X}"
                        f" VRAM changed {n}")
                if n:
                    line += f" first ${fa:05X} := {r[28]:02X}"
                if k in landed:
                    la = landed[k]
                    line += (f"  | A vs the pattern at ${la:05X} ({pat(la):02X}): {'EQUAL' if la is not None and pat(la) == a else 'differs'}"
                             if la is not None else "  | (the write call changed nothing)")
                print(line)


if __name__ == "__main__":
    main()
