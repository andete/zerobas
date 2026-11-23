#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""Decode scratchpad/AE_xsubkyk{,2,3}_msx2.out (probes/bios/spec/xsubkyk{,2,3}.asm, sub-ROM
KYKLOK $0135), per machine and case.
The inputs are read from the probe's own `cases:` table.

    python3 scratchpad/xsubkyk_decode.py scratchpad/AE_xsubkyk_msx2.out
"""
import re
import sys

REC = 0x180
NAMES = {0xFCAB: "CAPST", 0xFCAC: "KANAST", 0xFCAD: "KANAMD", 0xF3F6: "SCNCNT", 0xFC9E: "JIFFY", 0xFC9F: "JIFFY+1",
         0xFCA2: "INTCNT", 0xF3E7: "STATFL", 0xFBEB: "NEWKEY6", 0xFBDA: "OLDKEY6"}


def load_cases(asm):
    src = open(asm).read().split("\ncases:\n", 1)[1]
    out = []
    for line in src.splitlines():
        m = re.match(r"\s+db\s+([^;]*)", line)
        if not m:
            break
        vals = [int(v.strip().replace("$", "0x"), 0) for v in m.group(1).split(",")]
        if vals == [0xEE]:
            break
        out.append(vals)
    return out


def decode(name, cap, cases):
    assert cap[0] == 0xA5, f"{name}: not finished ({cap[0]:02X})"
    n = cap[1]
    print(f"--- {name}: {n} cases")
    for k in range(n):
        r = cap[2 + k * REC: 2 + (k + 1) * REC]
        f, a, kanast, capst, nk6, ok6, mx6 = cases[k][:7]
        extra = ""
        if len(cases[k]) > 7:
            extra = f" R15-preset={cases[k][7]:02X} MODE-xor={cases[k][8]:02X} (MODE as booted {r[26]:02X}, after the call {r[27]:02X})"
        print(f" case {k} in: A={a:02X} F={f:02X} BC=B1C1 DE=D1E1 HL=4171 KANAST={kanast:02X} CAPST={capst:02X}"
              f" NEWKEY6={nk6:02X} OLDKEY6={ok6:02X} matrix6-pressed={mx6:02X}" + extra)
        print(f"   out: A={r[1]:02X} F={r[2]:02X} BC={r[3]:02X}{r[4]:02X} DE={r[5]:02X}{r[6]:02X} HL={r[7]:02X}{r[8]:02X}"
              f" IX={r[9]:02X}{r[10]:02X} IY={r[11]:02X}{r[12]:02X} IFF={r[13]} SP {r[22] | r[23] << 8:04X}->"
              f"{r[24] | r[25] << 8:04X}")
        print(f"   port AA {r[14]:02X}->{r[15]:02X}  PSG R15 {r[16]:02X}->{r[17]:02X}")
        wc = r[18]
        we = [(r[32 + 4 * i] | r[33 + 4 * i] << 8, r[34 + 4 * i], r[35 + 4 * i]) for i in range(min(wc, 32))]
        print(f"   work area changed: {wc}: " + " ".join(
            f"{NAMES.get(ad, '')}${ad:04X}:{o:02X}->{nv:02X}" for ad, o, nv in we))
        na, nb, npsg = r[19], r[20], r[21]
        print(f"   OUT $AA x{na}: " + " ".join(f"{b:02X}" for b in r[160:160 + min(na, 32)]))
        print(f"   OUT $AB x{nb}: " + " ".join(f"{b:02X}" for b in r[192:192 + min(nb, 32)]))
        ents = [r[256 + i: 256 + i + 5] for i in range(0, min(npsg, 125), 5)]
        print(f"   PSG writes x{npsg // 5}: " + " ".join(
            f"R{e[0]}={e[1]:02X}@{e[2] | e[3] << 8 | e[4] << 16}" for e in ents))


def main():
    txt = open(sys.argv[1]).read()
    cases = load_cases(re.search(r"^===== (\S+)", txt, re.M).group(1))
    for blk in re.split(r"^===== ", txt, flags=re.M)[1:]:
        m = re.match(r"\S+ (\S+): (\S+) vs (\S+)", blk)
        if not m:
            continue
        for side, mach in (("ref ", m.group(2)), ("ours", m.group(3))):
            c = re.search(rf"CAP {side}: ([0-9a-f]+)", blk)
            decode(f"{m.group(1)} {mach}", bytes.fromhex(c.group(1)), cases)


main()
