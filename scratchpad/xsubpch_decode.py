#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""Decode scratchpad/AE_xsubpch_msx2.out (probes/bios/spec/xsubpch.asm): sub-ROM PUTCHR ($0139) -- the VRAM changes
as runs (xeol_decode.py's layout, 176-byte records, GRPACX / GRPACY / ESCCNT at +160).

    python3 scratchpad/xsubpch_decode.py [scratchpad/AE_xsubpch_msx2.out]
    python3 scratchpad/xsubpch_decode.py --r2 scratchpad/AE_xsubpch2_msx2.out   (round 2, xsubpch2.asm: the key buffer)

A run is printed as start+length=first-value, plus the text cell it starts at (row, column, 0-based) where the case
is a text mode (name-table base and width known).
"""
import re
import sys

NAMES = ["SLOT", "IFF2", "IFF1", "HL_", "DE_", "BC_", "AF_", "IY", "IX", "HL", "DE", "BC", "AF"]
ENT = dict(IX=0x0139, IY=0x1A2B, AF_=0x3C4D, BC_=0x5E6F, DE_=0x7081, HL_=0x92A3, BC=0xB1C2, DE=0x4E5F)
ORDER = [("msx2jp", "ref"), ("msx2eu", "ref"), ("msx2p", "ref"), ("msx2jp", "ours"), ("msx2eu", "ours"),
         ("msx2p", "ours")]
LABEL = ["F900", "8250", "WSX", "cb2jp", "cb2eu", "cb2+"]
# id: (description, name-table base, row stride) -- stride None for a bitmap / pattern span
CASES = [("w40 A 'Q' cursor (10,5) HL 140C", 0, 40), ("A 'R'", 0, 40), ("cursor (3,18)", 0, 40), ("HL 0303", 0, 40),
         ("A CR", 0, 40), ("A LF", 0, 40), ("A BS", 0, 40), ("A FF", 0, 40), ("A ESC", 0, 40), ("A DEL", 0, 40),
         ("A 01", 0, 40), ("cursor (40,5)", 0, 40), ("cursor (40,24)", 0, 40), ("w80", 0, 80),
         ("SCREEN 1", 0x1800, 32), ("EI", 0, 40), ("A space", 0, 40), ("A FF hex", 0, 40), ("A TAB", 0, 40),
         ("SCREEN 5", None, None)]


def caps(path):
    row, out = None, {}
    for line in open(path):
        m = re.match(r"===== \S+ (\w+):", line)
        if m:
            row = m.group(1)
        m = re.match(r"\s+CAP (ref |ours): ([0-9a-f]+)", line)
        if m and row:
            out[(row, m.group(1).strip())] = bytes.fromhex(m.group(2)) + bytes(0x1000)
    return out


def sig(r, base, stride):
    d = {n: r[1 + 2 * i] | r[2 + 2 * i] << 8 for i, n in enumerate(NAMES)}
    kept = all(d[n] == ENT[n] for n in ("IX", "IY", "AF_", "BC_", "DE_", "HL_"))
    regs = (f"AF {d['AF']:04X} BC {d['BC']:04X} DE {d['DE']:04X} HL {d['HL']:04X} "
            f"IX/IY/alt {'kept' if kept else 'CHANGED'} IFF {'on' if d['IFF1'] & 4 else 'off'}")
    a_ = d["AF"] >> 8
    lt = r[30:54]
    ltd = [f"{i}:{v:02X}" for i, v in enumerate(lt) if v != 0xC0 + i]
    n, nr = r[54] | r[55] << 8, r[56]
    runs = []
    for k in range(min(nr, 20)):
        e = r[57 + 5 * k: 62 + 5 * k]
        s, ln, v = e[0] | e[1] << 8, e[2] | e[3] << 8, e[4]
        cell = f"(r{(s - base) // stride} c{(s - base) % stride})" if stride else ""
        runs.append(f"{s:04X}{cell}+{ln}={v:02X}")
    gx, gy = r[160] | r[161] << 8, r[162] | r[163] << 8
    return (f"GRPACX {gx} GRPACY {gy} ESCCNT {r[164]:02X} CSRX {r[27]} CSRY {r[28]} CNSDFG {r[29]:02X} LINTTB changed [{' '.join(ltd)}] | changed {n} in {nr} "
            f"runs: {' '.join(runs)} | {regs}")


CASES2 = ["A 51, PUT FBF0 GET FBF0", "A 52, PUT FC05 GET FBF0", "A 53, PUT FC17 GET FC00",
          "A 54, PUT FBF5 GET FBF6 (full)", "A 55, PUT FC17 GET FBF0 (full across the wrap)", "A 00, PUT=GET=FBF0",
          "A 0D, PUT=GET=FBF0", "A FF, PUT=GET=FBF0", "A 51, EI", "A 56, PUT FC18 (past the buffer) GET FBF0",
          "A 57, PUT=GET=FC10"]


def main2(path):
    cs = caps(path)
    for i, name in enumerate(CASES2):
        print(f"\n== case {i}: {name} (KEYBUF[i] = 80+i, FC18.. = E1 E2 E3; F C5 BC B1C2 DE 4E5F HL 140C IY 1A2B)")
        groups = {}
        for k, lab in zip(ORDER, LABEL):
            r = cs[k][2 + 80 * i: 2 + 80 * (i + 1)]
            if r[79] != 0x5E or r[0] != i:
                sg = "missing"
            else:
                w = lambda o: r[o] | r[o + 1] << 8
                kb = r[28:68]
                kd = " ".join(f"{0xFBF0 + j:04X}:{v:02X}" for j, v in enumerate(kb) if v != 0x80 + j)
                ex = " ".join(f"{0xFC18 + j:04X}:{v:02X}" for j, v in enumerate(r[68:71]) if v != 0xE1 + j)
                chg = (f"CHSNS: waiting, CHGET {r[23]:02X}, then PUT {w(24):04X} GET {w(26):04X}" if r[22]
                       else "CHSNS: none waiting")
                sg = (f"A {r[1]:02X} F {r[2]:02X} BC {w(4):04X} DE {w(6):04X} HL {w(8):04X} IX {w(10):04X} "
                      f"IY {w(12):04X} IFF {r[3]}/{r[14]} | PUTPNT {w(16):04X} GETPNT {w(18):04X} CSRX {r[20]} "
                      f"CSRY {r[21]} | KEYBUF changed [{kd}] [{ex}] | {chg}")
            groups.setdefault(sg, []).append(lab)
        for sg, labs in groups.items():
            print(f"  {','.join(labs)}: {sg}")


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--r2":
        return main2(sys.argv[2] if len(sys.argv) > 2 else "scratchpad/AE_xsubpch2_msx2.out")
    cs = caps(sys.argv[1] if len(sys.argv) > 1 else "scratchpad/AE_xsubpch_msx2.out")
    for k, lab in zip(ORDER, LABEL):
        print(f"{lab:6} cases {cs[k][0]} sentinel {cs[k][1]:02X}")
    for i, (name, base, stride) in enumerate(CASES):
        sigs = []
        for k in ORDER:
            r = cs[k][16 + 176 * i: 16 + 176 * i + 176]
            sigs.append(sig(r, base, stride) if r[175] == 0x5A and r[0] == i else "missing")
        print(f"\n== case {i}: {name} (entry: LINTTB[i] = C0+i, GRPACX 40, GRPACY 50; F C5, BC B1C2, DE 4E5F)")
        groups = {}
        for lab, sg in zip(LABEL, sigs):
            groups.setdefault(sg, []).append(lab)
        for sg, labs in groups.items():
            print(f"  {','.join(labs)}: {sg}")


if __name__ == "__main__":
    main()
