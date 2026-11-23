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
        # goldfish pass 1 (2026-11-23): R2 and W2, appended
        o = 1 + 6 * 64 + 8 * 4
        if not any(b[o:o + 7 * 52]):
            print("  (no R2 / W2 section in this capture)")
            continue
        if b[o + 7 * 52 + 10 * 4] != 0x5A:
            sys.exit("REFUSED: the R2 / W2 sentinel $5A is missing")
        bad, nosep, modebad, fbad, hi = [], [], [], [], set()
        for k in range(52):
            c, a, f, mb, ma, pn, pp = b[o + 7 * k: o + 7 * k + 7]
            hi.add(a & 0xF0)
            if (a & 15) != pn:
                bad.append(f"C={c:02X} A={a:02X} named={pn:X} preselected={pp:X}")
            if pn == pp:
                nosep.append(f"{c:02X}")
            if ma != (mb & 0x0C) | (c >> 4):
                modebad.append(f"C={c:02X} MODE {mb:X}->{ma:X}")
            v = a & 15
            pe = bin(v).count("1") % 2 == 0
            fx = 0x10 | (0x40 if v == 0 else 0) | (0x04 if pe else 0) | (v & 0x08)
            if f != fx:
                fbad.append(f"C={c:02X} A={a:02X} F={f:02X} (AND $0F flags {fx:02X})")
        print(f"  R2 REDCLK (blocks 2 / 3 preset NOT blocks 0 / 1; MODE := TE/AE (reg AND 3) | block XOR 2):"
              f" A low == named block on {52 - len(bad)}/52; named != preselected on {52 - len(nosep)}/52"
              f" (not separated: {nosep}); A high nibbles {sorted(hex(x) for x in hi)};"
              f" MODE after == (before AND $0C) | MM on {52 - len(modebad)}/52; F == flags of AND $0F on {52 - len(fbad)}/52")
        for x in bad + modebad + fbad:
            print("    differs:", x)
        o += 7 * 52
        for k in range(4):
            c, mb, ov, pv, wv, a, f, ma, na, pa = b[o + 10 * k: o + 10 * k + 10]
            print(f"  W2 WRTCLK C={c:02X} MODE before {mb:X}: named {ov:X}->{na:X}, preselected (block {mb & 3}) {pv:X}->{pa:X},"
                  f" A={wv:02X} -> A={a:02X} F={f:02X}, MODE after {ma:X}")


if __name__ == "__main__":
    main()
