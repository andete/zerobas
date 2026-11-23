#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""D-MSX2SPEC: decode probes/bios/spec/xsubfnk.asm (sub-ROM DSPFNK).
    python3 scratchpad/xsubfnk_decode.py RUNFILE [--side ref|ours]
Per case: A, F, IFF, CNSDFG after, the span as text ('.' = the VRAM pattern still there, for the diffed cases),
and for the diffed cases (4 and up except 12) the number of VRAM bytes that differ from the pattern, the first and
last such address, how many of them lie inside the span, and LINLEN after."""
import re
import sys

NAMES = ["S0 w40", "S0 w80", "S1 w32", "S5 line 204",
         "S0 w40 3-char", "S0 w80 3-char", "S0 w80 16-char", "S0 w37", "S1 LINL32 29", "S0 LINLEN := 36",
         "S0 CRTCNT 13 (row 12)", "S0 CNSDFG $FF", "S0 EI entry", "S5 diffed", "S2", "S3", "S4", "S6", "S7", "S8"]
SPAN = [(0x0398, 40), (0x0730, 80), (0x1AE0, 32), (0x6600, 96), (0x0398, 40), (0x0730, 80), (0x0730, 80),
        (0x0398, 40), (0x1AE0, 32), (0x0398, 40), (0x01E0, 40), (0x0398, 40), (0x0398, 40), (0x6600, 96),
        (0x1AE0, 32), (0x0AE0, 32), (0x1AE0, 32), (0x6600, 96), (0xCC00, 96), (0xCC00, 96)]
KEYS = [0x5A, 0x7F, 0x14, 0x31, 0xC6, 0xE3, 0x88, 0xAD]


def pat(a):
    o = a & 0x3FFF
    return (o & 0xFF) ^ (o >> 8) ^ KEYS[a >> 14]


def main():
    side = sys.argv[sys.argv.index("--side") + 1] if "--side" in sys.argv else "ref"
    for blk in re.split(r"^===== ", open(sys.argv[1]).read(), flags=re.M)[1:]:
        m = re.search(rf"CAP {'ref ' if side == 'ref' else 'ours'}: ([0-9a-f]+)", blk)
        if not m:
            continue
        b = bytes.fromhex(m.group(1)) + bytes(4000)
        if b[0] != 0xA5:
            sys.exit("REFUSED: no $A5 finish mark")
        print("#", blk.split("\n", 1)[0].split(".asm ")[-1].split(" =")[0], side)
        for k in range(b[1]):
            r = b[2 + 112 * k: 114 + 112 * k]
            c = r[0]
            addr, ln = SPAN[c]
            sp = r[16:16 + ln]
            diffed = c >= 4 and c != 12
            txt = "".join("." if diffed and v == pat(addr + i) else (chr(v) if 32 <= v < 127 else f"<{v:02X}>")
                          for i, v in enumerate(sp))
            line = f"  {c:2} {NAMES[c]:22} A={r[1]:02X} F={r[2]:02X} IFF={r[3]} CNSDFG={r[4]:02X}"
            if diffed:
                n = r[5] | r[6] << 8 | r[7] << 16
                fa = r[8] | r[9] << 8 | r[10] << 16
                la = r[11] | r[12] << 8 | r[13] << 16
                inspan = sum(1 for i, v in enumerate(sp) if v != pat(addr + i))
                line += (f" VRAM changed {n} (first ${fa:05X}, last ${la:05X}; in the span {inspan},"
                         f" outside {n - inspan}) LINLEN={r[14]}")
            print(line)
            print(f"       [{txt}]")


if __name__ == "__main__":
    main()
