#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""D-MSX2SPEC: decode probes/bios/spec/xmode2.asm (the separating cases for the sub-ROM screen-mode calls).
    python3 scratchpad/xmode2_decode.py RUNFILE [--side ref|ours]
Refuses a record whose sentinel ($5E at +351) is missing."""
import re
import sys

RECLEN = 352
NAMES = ["CHGMOD 5 from 0, copies 00", "CHGMOD 5 from 1, copies 8F/FF, EI", "CHGMOD 2 from 1, copies 8F/FF",
         "CHGMOD 0 from 8, copies 00", "CHGMOD 0 from 8, LINL40 80", "CHGMOD 8 from 0, copies 8F/FF",
         "CHGMOD 9 from 0", "CHGMOD 4 from 7", "CHGMOD 1 from 5, LINL32 33, LINLEN 20",
         "CHGMDP 5 from 0", "CHGMDP 0 from 5, EI", "CHGMDP 8 from 0",
         "SETPAG SCR7 DP1 AC0", "SETPAG SCR8 DP2 AC1", "SETPAG SCR5 DP2 AC3 EI", "SETPAG SCR5 DP4 AC5",
         "SETPAG SCR5 (SCRMOD 7) DP1 AC2", "SETPAG SCR0 DP1 AC1",
         "INITXT from 5, LINL40 33, LINLEN 20, SCRMOD 7 OLD 6", "INITXT from 8, LINL40 80, EI",
         "INIT32 from 5, LINL32 33, LINLEN 20, SCRMOD 7 OLD 6", "INIGRP from 5, SCRMOD 7 OLD 6",
         "INIMLT from 8, SCRMOD 7 OLD 6", "SETTXT from 5, LINL40 33, LINLEN 20", "SETTXT from 0, LINL40 80, EI",
         "SETT32 from 5", "SETGRP from 4", "SETMLT from 0, copies 8F/FF", "SETMLT from 0, copies 00, A/F 00",
         "raw: R#0-7, R#10, R#11 := $FF by OUT",
         "CHGMOD 2 from 0, OLDSCR 6", "SETPAG SCR5 DP1, A/F 00", "SETTXT from 0, LINL40 37, LINLEN 80",
         "INITXT from 0, LINL40 37, LINLEN 80"]
VRAM = {0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 18, 19, 20, 21, 22, 23, 25, 26}  # the cases with flag 2 (VRAM read)
PG = bytes.fromhex("3102040157002207750640051304660332050504500323027601410014076706")


def hx(b):
    return b.hex()


def main():
    side = sys.argv[sys.argv.index("--side") + 1] if "--side" in sys.argv else "ref"
    for blk in re.split(r"^===== ", open(sys.argv[1]).read(), flags=re.M)[1:]:
        m = re.search(rf"CAP {'ref ' if side == 'ref' else 'ours'}: ([0-9a-f]+)", blk)
        if not m:
            continue
        b = bytes.fromhex(m.group(1)) + bytes(16000)
        print("#", blk.split("\n", 1)[0].split(".asm ")[-1].split(" =")[0], side, "done", hex(b[0]), "cases", b[1])
        for k in range(b[1]):
            r = b[2 + RECLEN * k: 2 + RECLEN * (k + 1)]
            if r[351] != 0x5E:
                sys.exit(f"REFUSE: case {k} has no sentinel")
            w = lambda o: r[o] | r[o + 1] << 8  # noqa: E731
            aft, bef = r[24:138], r[138:252]
            ra, rb = aft[:64], bef[:64]
            pa, pb = aft[82:114], bef[82:114]
            print(f"  [{r[0]:2}] {NAMES[r[0]]}")
            print(f"     out A={r[1]:02X} F={r[2]:02X} IFF={r[4]}/{r[3]} BC={w(5):04X} DE={w(7):04X} HL={w(9):04X}"
                  f" IX={w(11):04X} IY={w(13):04X} BC'={w(15):04X} DE'={w(17):04X} HL'={w(19):04X}"
                  f" AF'={r[22]:02X}{r[21]:02X}")
            print(f"     R0-11  before {hx(rb[:12])}  after {hx(ra[:12])}")
            print(f"     R12-27 before {hx(rb[12:28])}  after {hx(ra[12:28])}")
            ch = [f"R{i}:{rb[i]:02X}>{ra[i]:02X}" for i in range(32, 47) if ra[i] != rb[i]]
            print(f"     R32-46 after {hx(ra[32:47])} changed: {' '.join(ch) or '-'}")
            print(f"     copies RG0-7 {hx(r[252:260])} FFE7-FFFC {hx(r[260:282])}")
            c = r[282:291]
            print(f"     SCRMOD={c[0]} OLDSCR={c[1]} LINLEN={c[2]} CRTCNT={c[3]} LINL40={c[4]} LINL32={c[5]}"
                  f" FOR/BAK/BDR={c[6]:02X}/{c[7]:02X}/{c[8]:02X} cells="
                  + " ".join(f"{w(291 + 2 * i):04X}" for i in range(5))
                  + f" DP/AC={r[301]}/{r[302]} MODE={r[303]:02X} CSRY/X={r[348]}/{r[349]}")
            pal = "untouched" if pa == pb else ("= probe garbage" if pa == PG else "changed")
            print(f"     palette before {'garbage' if pb == PG else 'boot'}, after {pal}: {hx(pa)}")
            vb = " ".join(f"{w(304 + 3 * i)}:{r[306 + 3 * i]:02X}" for i in range(8))
            print(f"     VRAM !=5A per 16K (count:last) {vb if r[0] in VRAM else 'not read'}")
            print(f"     at ATRBAS {hx(r[328:336])}  palette table (6 entries) {hx(r[336:348])}")


if __name__ == "__main__":
    main()
