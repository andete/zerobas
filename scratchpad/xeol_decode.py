#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""Decode scratchpad/AE_xeol_msx2.out (probes/bios/spec/xeol.asm): EOL ($0168) -- the VRAM changes as runs.

    python3 scratchpad/xeol_decode.py [scratchpad/AE_xeol_msx2.out]

A run is printed as start+length=first-value, plus the text cell it starts at (row, column, 0-based) where the case
is a text mode (name-table base and width known).
"""
import re
import sys

NAMES = ["SLOT", "IFF2", "IFF1", "HL_", "DE_", "BC_", "AF_", "IY", "IX", "HL", "DE", "BC", "AF"]
ENT = dict(IX=0x5A6B, IY=0x1A2B, AF_=0x3C4D, BC_=0x5E6F, DE_=0x7081, HL_=0x92A3, BC=0xB1C2, DE=0x4E5F)
ORDER = [("msx2jp", "ref"), ("msx2eu", "ref"), ("msx2p", "ref"), ("msx2jp", "ours"), ("msx2eu", "ours"),
         ("msx2p", "ours")]
LABEL = ["F900", "8250", "WSX", "cb2jp", "cb2eu", "cb2+"]
# id: (description, name-table base, row stride) -- stride None for a bitmap / pattern span
CASES = [("SCREEN 1 w32, H5 L3", 0x1800, 32), ("SCREEN 0 w40, H1 L1", 0, 40), ("SCREEN 0 w80, H30 L3", 0, 80),
         ("SCREEN 0 LINL40 30, H5 L3", 0, 40), ("w40 H5 L3, LINTTB[2]=0", 0, 40), ("w40 H5 L3, LINTTB[3]=0", 0, 40),
         ("w40 H0 L3", 0, 40), ("w40 H41 L3", 0, 40), ("w40 H40 L3", 0, 40), ("w80 H80 L3", 0, 80),
         ("w40 H5 L24, CNSDFG 0", 0, 40), ("w40 H5 L24, CNSDFG FF", 0, 40), ("w40 H5 L0", 0, 40),
         ("w40 H5 L25", 0, 40), ("SCREEN 5 H5 L3", None, None), ("SCREEN 2 H5 L3", None, None),
         ("SCREEN 8 H5 L3", None, None), ("w40 H5 L3, EI", 0, 40), ("SCREEN 1 H32 L3", 0x1800, 32),
         ("w40 H5 L4, LINTTB[3]=0", 0, 40), ("w40 H5 L3 (baseline)", 0, 40),
         ("LINL40 30 H5 L3 (sets LINLEN 30)", 0, 40), ("SCREEN 2 after LINLEN 30, H5 L3", None, None),
         ("LINL40 30 H5 L3 (sets LINLEN 30)", 0, 40), ("SCREEN 5 after LINLEN 30, H5 L3", None, None),
         ("LINL40 39 H1 L3", 0, 40), ("LINL40 29 H1 L3", 0, 40), ("LINL40 75 (80 col) H1 L3", 0, 80),
         ("SCREEN 1 LINL32 29 H1 L3", 0x1800, 32), ("w40 H42 L3", 0, 40), ("w40 H255 L3", 0, 40)]


RL = 168  # record stride (160 before goldfish pass 1)


def caps(path):
    row, out = None, {}
    for line in open(path):
        m = re.match(r"===== \S+ (\w+):", line)
        if m:
            row = m.group(1)
        m = re.match(r"\s+CAP (ref |ours): ([0-9a-f]+)", line)
        if m and row:
            out[(row, m.group(1).strip())] = bytes.fromhex(m.group(2)) + bytes(0x1480)
    return out


def sig(r, base, stride):
    d = {n: r[1 + 2 * i] | r[2 + 2 * i] << 8 for i, n in enumerate(NAMES)}
    kept = all(d[n] == ENT[n] for n in ("IX", "IY", "AF_", "BC_", "DE_", "HL_"))
    regs = (f"AF {d['AF']:04X} BC {d['BC']:04X} DE {d['DE']:04X} HL {d['HL']:04X} "
            f"IX/IY/alt {'kept' if kept else 'CHANGED'} IFF {'on' if d['IFF1'] & 4 else 'off'}")
    lt = r[30:54]
    ltd = [f"{i}:{v:02X}" for i, v in enumerate(lt) if v != 0xC0 + i]
    n, nr = r[54] | r[55] << 8, r[56]
    runs = []
    for k in range(min(nr, 20)):
        e = r[57 + 5 * k: 62 + 5 * k]
        s, ln, v = e[0] | e[1] << 8, e[2] | e[3] << 8, e[4]
        cell = f"(r{(s - base) // stride} c{(s - base) % stride})" if stride else ""
        runs.append(f"{s:04X}{cell}+{ln}={v:02X}")
    return (f"CSRX {r[27]} CSRY {r[28]} CNSDFG {r[29]:02X} LINTTB changed [{' '.join(ltd)}] | changed {n} in {nr} "
            f"runs: {' '.join(runs)} | {regs} | FBB1 {r[160]:02X} FCB1 {r[157]:02X} FBCA {r[158]:02X}")


def main():
    cs = caps(sys.argv[1] if len(sys.argv) > 1 else "scratchpad/AE_xeol_msx2.out")
    for k, lab in zip(ORDER, LABEL):
        print(f"{lab:6} cases {cs[k][0]} sentinel {cs[k][1]:02X}")
    for i, (name, base, stride) in enumerate(CASES):
        sigs = []
        for k in ORDER:
            r = cs[k][16 + RL * i: 16 + RL * i + RL]
            sigs.append(sig(r, base, stride) if r[159] == 0x5A and r[0] == i else "missing")
        print(f"\n== case {i}: {name} (entry: cursor (20, 10), LINTTB[i] = C0+i)")
        if len(set(sigs)) == 1:
            print(f"  all six: {sigs[0]}")
        else:
            for lab, s in zip(LABEL, sigs):
                print(f"  {lab:6} {s}")


if __name__ == "__main__":
    main()
