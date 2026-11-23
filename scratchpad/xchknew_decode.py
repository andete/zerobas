#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""Decode scratchpad/AE_xchknew_msx2.out (probes/bios/spec/xchknew.asm): CHKNEW ($0165) per screen mode.

    python3 scratchpad/xchknew_decode.py [scratchpad/AE_xchknew_msx2.out]
"""
import re
import sys

NAMES = ["SLOT", "IFF2", "IFF1", "HL_", "DE_", "BC_", "AF_", "IY", "IX", "HL", "DE", "BC", "AF"]
ENT = dict(IX=0x5A6B, IY=0x1A2B, AF_=0x3C4D, BC_=0x5E6F, DE_=0x7081, HL_=0x92A3, BC=0xB1C2, DE=0x4E5F, HL=0x9876)
ORDER = [("msx2jp", "ref"), ("msx2eu", "ref"), ("msx2p", "ref"), ("msx2jp", "ours"), ("msx2eu", "ours"),
         ("msx2p", "ours")]
LABEL = ["F900", "8250", "WSX", "cb2jp", "cb2eu", "cb2+"]
CASES = ["SCREEN 0 w40", "SCREEN 1", "SCREEN 2", "SCREEN 3", "SCREEN 4", "SCREEN 5", "SCREEN 6", "SCREEN 7",
         "SCREEN 8"]
CASES = [c + ", F 00" for c in CASES] + [c + ", F FF" for c in CASES] + [
    "SCREEN 0 w80, F 00", "VDP S1, SCRMOD 5", "VDP S5, SCRMOD 1", "S1, save cells S5's", "S5, save cells S1's",
    "S1, SCRMOD 9", "S1, SCRMOD $10", "S1 again", "S1, SCRMOD 10", "S1, SCRMOD 11", "S1, SCRMOD 12", "S5, EI",
    "S1, EI", "VDP S1, SCRMOD 4", "S1, SCRMOD $80",
    "S1, SCRMOD $FF", "S1, entry A $00", "S5, entry A $05", "S1, entry A $FF, F FF"]
ENTRY_A = [0xA7] * 34 + [0x00, 0x05, 0xFF]


def caps(path):
    row, out = None, {}
    for line in open(path):
        m = re.match(r"===== \S+ (\w+):", line)
        if m:
            row = m.group(1)
        m = re.match(r"\s+CAP (ref |ours): ([0-9a-f]+)", line)
        if m and row:
            out[(row, m.group(1).strip())] = bytes.fromhex(m.group(2)) + bytes(0x500)
    return out


def sig(r):
    d = {n: r[4 + 2 * i] | r[5 + 2 * i] << 8 for i, n in enumerate(NAMES)}
    a, f = d["AF"] >> 8, d["AF"] & 255
    kept = [n for n in ("BC", "DE", "HL", "IX", "IY", "AF_", "BC_", "DE_", "HL_") if d[n] == ENT[n]]
    chg = [f"{n}={d[n]:04X}" for n in ("BC", "DE", "HL", "IX", "IY", "AF_", "BC_", "DE_", "HL_") if d[n] != ENT[n]]
    return (f"SCRMOD {r[1]:02X} RG0/1 {r[2]:02X}/{r[3]:02X} | A {a:02X} F {f:02X} (C{f & 1} Z{f >> 6 & 1} "
            f"S{f >> 7} PV{f >> 2 & 1}) IFF {'on' if d['IFF1'] & 4 else 'off'} | "
            + ("others kept" if not chg else "changed: " + " ".join(chg)) + f" | SCRMOD after {r[30]:02X}")


def main():
    cs = caps(sys.argv[1] if len(sys.argv) > 1 else "scratchpad/AE_xchknew_msx2.out")
    for k, lab in zip(ORDER, LABEL):
        c = cs[k]
        print(f"{lab:6} cases {c[0]} S5 RG0/1 {c[1]:02X}/{c[2]:02X} S1 RG0/1 {c[3]:02X}/{c[4]:02X} sentinel {c[5]:02X}")
    for i, name in enumerate(CASES):
        sigs = []
        for k in ORDER:
            r = cs[k][16 + 32 * i: 16 + 32 * i + 32]
            sigs.append(sig(r) if r[31] == 0x5A and r[0] == i else "missing")
        print(f"\n== case {i}: {name} (entry A {ENTRY_A[i]:02X})")
        if len(set(sigs)) == 1:
            print(f"  all six: {sigs[0]}")
        else:
            for lab, s in zip(LABEL, sigs):
                print(f"  {lab:6} {s}")


if __name__ == "__main__":
    main()
