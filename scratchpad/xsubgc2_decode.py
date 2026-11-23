#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""D-MSX2SPEC: decode probes/bios/spec/xsubgc2.asm (the graphics-cursor separating cases).
    python3 scratchpad/xsubgc2_decode.py RUNFILE [--side ref|ours]"""
import re
import sys


def s16(v):
    return v - 65536 if v & 0x8000 else v


def scal_inputs():
    """The SCALXY table's (X, Y) pairs, read from the probe (the record holds only the outputs)."""
    src = open(__file__.replace("scratchpad/xsubgc2_decode.py", "probes/bios/spec/xsubgc2.asm")).read()
    return [(int(m.group(1).replace("$", "0x"), 0), int(m.group(2).replace("$", "0x"), 0))
            for m in re.finditer(r"^ +sc +\S+, *(-?\$?[0-9A-Fa-f]+), *(-?\$?[0-9A-Fa-f]+), ", src, flags=re.M)]


def main():
    sc = scal_inputs()
    side = sys.argv[sys.argv.index("--side") + 1] if "--side" in sys.argv else "ref"
    for blk in re.split(r"^===== ", open(sys.argv[1]).read(), flags=re.M)[1:]:
        m = re.search(rf"CAP {'ref ' if side == 'ref' else 'ours'}: ([0-9a-f]+)", blk)
        if not m:
            continue
        b = bytes.fromhex(m.group(1)) + bytes(4000)
        print("#", blk.split("\n", 1)[0].split(".asm ")[-1].split(" =")[0], side, "done" if b[0] == 0xA5 else "NOT DONE")
        o = 5
        for _ in range(b[1]):
            r = b[o:o + 122]
            v = r[8:]
            regs, st = v[:64], v[64:80]
            print(f"  STATE S{r[0]}: LOGOPR={r[1]:02X} ACPAGE={r[2]} DPPAGE={r[3]} GRPCGP=${r[4] | r[5] << 8:04X}"
                  f" MLTCGP=${r[6] | r[7] << 8:04X} R#9={regs[9]:02X} (LN {regs[9] >> 7 & 1}) S#2={st[2]:02X}"
                  f" (CE {st[2] & 1}) R#46={regs[46]:02X} R#45={regs[45]:02X} R#14={regs[14]:02X}")
            o += 122
        for k in range(b[2]):
            r = b[o:o + 4]
            print(f"  A{k + 1:02d} SETATR S{r[0]} A=${r[1]:02X}: ATRBYT=${r[2]:02X} F={r[3]:02X} (carry {r[3] & 1})")
            o += 4
        for k in range(b[3]):
            r = b[o:o + 16]
            ad = r[9] | r[10] << 8
            print(f"  P{k + 1:02d} S{r[0]}: CLOC=${r[1] | r[2] << 8:04X} CMASK=${r[3]:02X} F(MAPXYC)={r[4]:02X}"
                  f" addr=${ad:04X} READC1={r[5]:02X} byte(after READC1)={r[11]:02X} byte(after SETC)={r[6]:02X}"
                  f" READC2={r[7]:02X} ATRBYT={r[8]:02X} LOGOPR={r[12]:02X}")
            o += 16
        for k in range(b[4]):
            r = b[o:o + 8]
            x, y = sc[k] if k < len(sc) else ("?", "?")
            print(f"  X{k + 1:02d} SCALXY ({x}, {y}) S{r[0] & 0x7F}{' LN0' if r[0] & 0x80 else ''} (F in {r[7]:02X}): -> BC={s16(r[1] | r[2] << 8)} DE={s16(r[3] | r[4] << 8)}"
                  f" F={r[5]:02X} (carry {r[5] & 1}) A={r[6]:02X}")
            o += 8


if __name__ == "__main__":
    main()
