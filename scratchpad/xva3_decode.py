#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""D-MSX2SPEC: decode probes/bios/spec/xva3.asm's capture (the shared VRAM matrix's goldfish-pass cases) -- per case
and call: A / F after, the 17-bit address the VDP holds (R#14 x $4000 + the pointer's 14 bits), the port $99 writes,
the port $98 / $9A / $9B write counts, IFF2 (read twice), the registers that changed (S-REGS), the save cells
$FFE7-$FFF6 that changed, R#7 and the pointer after the probe's own R#7 := $5A, and on the sum cases the 128 KB VRAM
sum / XOR before and after with the expected address's byte.
    python3 scratchpad/xva3_decode.py RUNFILE [--side ref|ours]"""
import re
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from xva_decode import portlog  # noqa: E402

CALLS = ("NSETRD", "NSETWR", "NRDVRM", "NWRVRM", "BIGFIL")
NAMES = ["VA-1 sums", "VA-1 A00 FFF", "VA-1 AFF F00", "S5 AC1 C123", "S6 VA-3", "S6 VA-5", "S6 AC1 C123", "S6 VA-1",
         "S5 AC4", "S5 AC5", "S5 AC40", "S5 ACFF", "S1 AC4", "S1 AC40", "S1 AC80", "S1 ACFF", "S1 AC3 A00 FFF",
         "S8 AC2", "S8 AC3", "S7 AC2", "VA-3 MODE00", "VA-3 MODE11", "S1 AC1 DP2", "VA-11 sums", "VA-3 sums",
         "VC-1 FFFF", "VC-2 S1 3FFF", "S8 AC2 FF34", "S5 AC4 FF23"]
# S-REGS: BC (BIGFIL: 0001 in), DE, HL (the case's), IX, IY, BC', DE', HL', AF' (F, A)
SREGS = ("BC", 0x5AA5), ("DE", 0xA55A), ("HL", None), ("IX", 0x4321), ("IY", 0x8765), ("BC'", 0x1111), \
    ("DE'", 0x2222), ("HL'", 0x3333), ("AF'", 0x4444)


def main():
    path = sys.argv[1]
    side = sys.argv[sys.argv.index("--side") + 1] if "--side" in sys.argv else "ref"
    t = open(path).read()
    for blk in re.split(r"^===== ", t, flags=re.M)[1:]:
        head = blk.split("\n", 1)[0]
        m = re.search(rf"CAP {'ref ' if side == 'ref' else 'ours'}: ([0-9a-f]+)", blk)
        if not m:
            continue
        b = bytes.fromhex(m.group(1)) + bytes(9000)
        print("#", head.split(".asm ")[-1].split(" =")[0], side, f"-- {b[1]} cases")
        for r in range(b[1] * 5):
            rec = b[2 + 64 * r: 66 + 64 * r]
            a, f, r14, plo, phi, n = rec[:6]
            addr = r14 * 0x4000 + ((phi << 8 | plo) & 0x3FFF)
            c, k = rec[14], rec[15]
            w = [rec[22 + 2 * i] | rec[23 + 2 * i] << 8 for i in range(9)]
            changed = []
            for (nm, v), got in zip(SREGS, w):
                exp = v
                if nm == "BC" and k == 4:
                    exp = 0x0001
                if exp is not None and got != exp:
                    changed.append(f"{nm}={got:04X}")
            hl = w[2]
            iff = f"{rec[16] >> 2 & 1}{rec[17] >> 2 & 1}"
            mask = rec[56] | rec[57] << 8
            sv = ",".join(f"{0xFFE7 + i:04X}" for i in range(16) if mask >> i & 1) or "-"
            r7p = (rec[43] * 0x4000) + ((rec[42] << 8 | rec[41]) & 0x3FFF)
            line = (f"  {c:2} {NAMES[c] if c < len(NAMES) else c:14} {CALLS[k]:6} A={a:02X} F={f:02X} addr=${addr:05X} "
                    f"FFED={rec[13]:02X} IFF2={iff} w99={n} {portlog(rec[6:6 + min(n, 7)])}"
                    f"{' lone=' + format(rec[6 + n - 1], '02X') if n % 2 and n <= 7 else ''} "
                    f"w98={rec[18]}{'(' + format(rec[19], '02X') + ')' if rec[18] else ''} w9A={rec[20]} w9B={rec[21]} "
                    f"HL={hl:04X} chg=[{' '.join(changed)}] svchg={sv} R7={rec[40]:02X}@${r7p:05X} "
                    f"MODE={rec[52]:02X}/{rec[58]:02X} SCRMOD={rec[53]} AC={rec[54]:02X} DP={rec[55]}")
            if any(rec[44:52]):
                s0, x0, s1, x1 = rec[44] | rec[45] << 8, rec[46], rec[47] | rec[48] << 8, rec[49]
                old, new = rec[50], rec[51]
                one = (s1 - s0) & 0xFFFF == (new - old) & 0xFFFF and x1 == x0 ^ old ^ new
                line += (f"\n       sum {s0:04X}/{x0:02X} -> {s1:04X}/{x1:02X}; expected byte {old:02X} -> {new:02X}; "
                         f"{'unchanged' if (s0, x0) == (s1, x1) else ('only the expected byte' if one else 'OTHER BYTES CHANGED')}")
            print(line)


if __name__ == "__main__":
    main()
