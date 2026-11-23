#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""Decode probes/bios/spec/xtrdram.asm's run file (--row turbor): per CPU mode, the slot state, the mapper registers,
what IN $FE reads after OUT $FE,s, the write test (3 = writable) and the tag pass (1 own tag / 0 another's /
2 skipped) for segments 0-63, both machines.

    python3 scratchpad/xtrdram_decode.py scratchpad/AE_xtrdram_tr.out
"""
import re
import sys

MODES = {0x80: "Z80", 0x81: "R800 ROM", 0x82: "R800 DRAM"}


def main():
    for line in open(sys.argv[1]):
        m = re.match(r"\s*CAP (ref |ours): ([0-9a-f]+)", line)
        if not m:
            continue
        b = bytes.fromhex(m.group(2))
        b = b + bytes(0x400 - len(b))
        print(f"== {'A1GT' if m.group(1) == 'ref ' else 'A1ST'}: modes done {b[0]}")
        for k in range(b[0]):
            r = b[16 + k * 256: 16 + (k + 1) * 256]
            wt = r[80:144]
            print(f" {MODES.get(r[0], hex(r[0]))}: R#6 {r[1]:02X}  $A8 {r[2]:02X}  page-3 secondary {r[3]:02X}  "
                  f"IN $FC-$FF {r[4:8].hex(' ')}  EXPTBL {r[8:12].hex(' ')}")
            print("  IN $FE after OUT $FE,0..63:", r[16:80].hex(" "))
            print("  write test 0..63:", "".join(str(x) for x in wt),
                  "| not writable:", [s for s in range(64) if wt[s] != 3])
            print("  tag pass   0..63:", "".join(str(x) for x in r[144:208]))


if __name__ == "__main__":
    main()
