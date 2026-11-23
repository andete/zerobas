#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""Decode scratchpad/AE_xsubpvr{,2,3}_msx2.out (probes/bios/spec/xsubpvr{,2,3}.asm, sub-ROM
PUTVRM $0129), per machine and case. The inputs are read from the probe's own `cases:` table.

    python3 scratchpad/xsubpvr_decode.py scratchpad/AE_xsubpvr_msx2.out
"""
import re
import sys

REC = 0x230
CASES = []
ROUND3 = False  # xsubpvr3.asm records LINLEN .. RG1SAV at +532


def load_cases(asm):
    """The probe's case table: a list of byte lists, one per case (the `db` / `dw` lines after `cases:`)."""
    src = open(asm).read().split("\ncases:\n", 1)[1]
    cur, out = [], []
    for line in src.splitlines():
        m = re.match(r"\s+(db|dw)\s+([^;]*)", line)
        if not m:
            if out or cur:
                break
            continue
        vals = [int(v.strip().replace("$", "0x"), 0) for v in m.group(2).split(",")]
        if m.group(1) == "db":
            if vals == [0xEE]:
                break
            if cur:
                out.append(cur)
            cur = list(vals)
        else:
            for v in vals:
                cur += [v & 255, v >> 8]
    if cur:
        out.append(cur)
    return out


VDPN = ["R#%d" % i for i in range(64)] + ["S#%d" % i for i in range(16)] + ["VP0", "VP1"] + \
       ["PAL%d" % i for i in range(32)]


def decode(name, cap):
    assert cap[0] == 0xA5, f"{name}: not finished ({cap[0]:02X})"
    n = cap[1]
    print(f"--- {name}: {n} cases")
    for k in range(n):
        r = cap[2 + k * REC: 2 + (k + 1) * REC]
        c = CASES[k]
        ovr = ""
        if len(c) > 12 and c[12]:
            ovr = (f" | LINLEN={c[13]} LINL40={c[14]} LINL32={c[15]} NAMBAS={c[16] | c[17] << 8:04X}"
                   f" TXTNAM={c[18] | c[19] << 8:04X} T32NAM={c[20] | c[21] << 8:04X}")
        print(f" case {k} SCREEN {c[0]} width {c[1]} in: A={c[3]:02X} F={c[2]:02X} BC={c[5]:02X}{c[4]:02X}"
              f" DE={c[7]:02X}{c[6]:02X} HL={c[9]:02X}{c[8]:02X} CSRX={c[10]} CSRY={c[11]}" + ovr)
        print(f"   out: A={r[1]:02X} F={r[2]:02X} BC={r[3]:02X}{r[4]:02X} DE={r[5]:02X}{r[6]:02X} HL={r[7]:02X}{r[8]:02X}"
              f" IX={r[9]:02X}{r[10]:02X} IY={r[11]:02X}{r[12]:02X} IFF={r[13]} CSRX={r[14]} CSRY={r[15]}"
              f" SP {r[28] | r[29] << 8:04X}->{r[30] | r[31] << 8:04X}")
        dc = r[16] | r[17] << 8
        ents = [(r[32 + 3 * i] << 8 | r[33 + 3 * i], r[34 + 3 * i]) for i in range(min(dc, 48))]
        print(f"   VRAM $0000-$7FFF changed: {dc}: " + " ".join(f"{ad:04X}={v:02X}" for ad, v in ents))
        sb = (r[18] | r[19] << 8, r[20] | r[21] << 8)
        sa = (r[22] | r[23] << 8, r[24] | r[25] << 8)
        print(f"   sums 8000-FFFF {sb[0]:04X}->{sa[0]:04X}, 10000-1FFFF {sb[1]:04X}->{sa[1]:04X}"
              + ("" if sb == sa else "  CHANGED"))
        wc = r[26]
        we = [(r[176 + 4 * i] | r[177 + 4 * i] << 8, r[178 + 4 * i], r[179 + 4 * i]) for i in range(min(wc, 32))]
        print(f"   work area changed: {wc}: " + " ".join(f"{ad:04X}:{o:02X}->{nv:02X}" for ad, o, nv in we))
        if ROUND3:
            q = r[532:545]
            w = lambda o: q[o] | q[o + 1] << 8
            print(f"   before the call: LINLEN={q[0]} LINL40={q[1]} LINL32={q[2]} NAMBAS={w(3):04X} TXTNAM={w(5):04X}"
                  f" T32NAM={w(7):04X} SCRMOD={q[9]} RG0SAV={q[10]:02X} RG1SAV={q[11]:02X}")
        vb, va = r[304:418], r[418:532]
        print("   VDP changed: " + (" ".join(f"{VDPN[i]}:{vb[i]:02X}->{va[i]:02X}" for i in range(114)
                                         if vb[i] != va[i] and not VDPN[i].startswith("S#")) or "none")
              + "  | status: " + " ".join(f"{VDPN[i]}:{vb[i]:02X}->{va[i]:02X}" for i in range(64, 80) if vb[i] != va[i]))


def main():
    txt = open(sys.argv[1]).read()
    global ROUND3
    asm = re.search(r"^===== (\S+)", txt, re.M).group(1)
    ROUND3 = asm.endswith("xsubpvr3.asm")
    CASES[:] = load_cases(asm)
    for blk in re.split(r"^===== ", txt, flags=re.M)[1:]:
        m = re.match(r"\S+ (\S+): (\S+) vs (\S+)", blk)
        if not m:
            continue
        for side, mach in (("ref ", m.group(2)), ("ours", m.group(3))):
            c = re.search(rf"CAP {side}: ([0-9a-f]+)", blk)
            decode(f"{m.group(1)} {mach}", bytes.fromhex(c.group(1)))


main()
