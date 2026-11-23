#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""D-MSX2SPEC: decode probes/bios/spec/xclk.asm (REDCLK / WRTCLK).  python3 scratchpad/xclk_decode.py RUNFILE [--side ref|ours]"""
import re
import sys


def main():
    side = sys.argv[sys.argv.index("--side") + 1] if "--side" in sys.argv else "ref"
    for blk in re.split(r"^===== ", open(sys.argv[1]).read(), flags=re.M)[1:]:
        m = re.search(rf"CAP {'ref ' if side == 'ref' else 'ours'}: ([0-9a-f]+)", blk)
        if not m:
            continue
        b = bytes.fromhex(m.group(1)) + bytes(1000)
        print("#", blk.split("\n", 1)[0].split(".asm ")[-1].split(" =")[0], side)
        bad, modes, hi = [], set(), set()
        for k in range(64):
            c, a, f, mb, ma, pv = b[1 + 6 * k: 7 + 6 * k]
            modes.add((mb, ma)); hi.add(a & 0xF0)
            if (a & 15) != pv:
                bad.append(f"C={c:02X} A={a:02X} port={pv:X}")
        print(f"  REDCLK: A's low nibble == the port on {64 - len(bad)}/64; A's high nibbles {sorted(hex(x) for x in hi)};"
              f" MODE before->after {sorted(modes)[:6]}{' ...' if len(modes) > 6 else ''}")
        for x in bad:
            print("    differs:", x)
        for k in range(4):
            r = b[1 + 6 * 64 + 8 * k: 9 + 6 * 64 + 8 * k]
            print(f"  WRTCLK C={r[0]:02X}: before {r[1]:X}, wrote {r[2]:X}, read back {r[3]:X}, A={r[4]:02X} F={r[5]:02X}"
                  f" MODE after {r[6]:X}, restored -> {r[7]:X}")


if __name__ == "__main__":
    main()
