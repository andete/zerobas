#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""D-MSX2SPEC: decode probes/bios/spec/xsubmv2.asm (the cursor moves, goldfish pass 1 separating cases).
    python3 scratchpad/xsubmv2_decode.py RUNFILE [--side ref|ours]
Refuses a record that lies past the captured bytes (xsubmv_decode.py padded with zeros and so invented one)."""
import re
import sys

N = {0xA5: "RIGHTC", 0xAD: "LEFTC", 0xBD: "UPC", 0xB5: "DOWNC", 0xA1: "TRIGHT", 0xA9: "TLEFTC", 0xB9: "TUPC",
     0xB1: "TDOWNC"}
R = 24


def main():
    side = sys.argv[sys.argv.index("--side") + 1] if "--side" in sys.argv else "ref"
    for blk in re.split(r"^===== ", open(sys.argv[1]).read(), flags=re.M)[1:]:
        m = re.search(rf"CAP {'ref ' if side == 'ref' else 'ours'}: ([0-9a-f]+)", blk)
        if not m:
            continue
        b = bytes.fromhex(m.group(1))
        n = b[1] | b[2] << 8
        print("#", blk.split("\n", 1)[0].split(".asm ")[-1].split(" =")[0], side, n, "done" if b[0] == 0xA5 else "NOT DONE")
        for k in range(n):
            r = b[3 + R * k: 3 + R * (k + 1)]
            if len(r) < R:
                sys.exit(f"record {k} truncated: {len(r)} of {R} bytes captured")
            w = lambda i: r[i] | r[i + 1] << 8
            fl = "".join(c for c, bit in (("P", 1), ("L", 2), ("A", 4)) if r[2] & bit) or "-"
            print(f"  {k:2} S{r[0]} {fl:3} x{w(11):3} y{w(13):3} {N.get(r[1], hex(r[1])):6} "
                  f"{w(3):04X}/{r[5]:02X} -> {w(6):04X}/{r[8]:02X}  A={r[9]:02X} F={r[10]:02X} C={r[10] & 1}  "
                  f"R9={r[15]:02X} AP={r[16]} BC={w(17):04X} DE={w(19):04X} HL={w(21):04X} IFF2={r[23] >> 2 & 1}")


if __name__ == "__main__":
    main()
