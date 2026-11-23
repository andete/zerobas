#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""D-MSX2SPEC goldfish pass 1: decode probes/bios/spec/xspr3.asm (the sub-ROM sprite calls, separating cases).
    python3 scratchpad/xspr3_decode.py RUNFILE [--side ref|ours]"""
import re
import sys

OPS = ("CLRSPR", "CALPAT", "CALATR", "GSPSIZ", "GETPAT")
VAR = ("-", "FORCLR0A", "FORCLRFF", "moved", "R1!=RG1SAV", "magnify", "CGPNT-RAM", "VRAMgarb")


def w(r, i):
    return r[i] | r[i + 1] << 8


def main():
    side = sys.argv[sys.argv.index("--side") + 1] if "--side" in sys.argv else "ref"
    for blk in re.split(r"^===== ", open(sys.argv[1]).read(), flags=re.M)[1:]:
        m = re.search(rf"CAP {'ref ' if side == 'ref' else 'ours'}: ([0-9a-f]+)", blk)
        if not m:
            continue
        b = bytes.fromhex(m.group(1)) + bytes(10000)
        print("#", blk.split("\n", 1)[0].split(".asm ")[-1].split(" =")[0], side, "done" if b[0] == 0xA5 else "NOT DONE")
        for k in range(b[1]):
            r = b[2 + 256 * k: 258 + 256 * k]
            reg = r[8:20]
            print(f"  {OPS[r[0]]:6} A={r[1]:02X} S{r[2]} {'16' if r[3] else ' 8'} {VAR[r[4]]:10} -> A={reg[0]:02X} "
                  f"F={reg[1]:02X} BC={reg[2]:02X}{reg[3]:02X} DE={reg[4]:02X}{reg[5]:02X} HL={reg[6]:02X}{reg[7]:02X} "
                  f"IX={reg[8]:02X}{reg[9]:02X} IY={reg[10]:02X}{reg[11]:02X} RG1SAV={r[20]:02X} FORCLR={r[21]:02X} "
                  f"PATWRK={r[24:32].hex()}")
            if r[0] == 0:
                print(f"      patterns: zero {w(r, 32)}/2048, $A5 left {w(r, 36)}; past 2048: zero {w(r, 34)}/256")
                print(f"      colour p0-1 {r[64:96].hex()}  p31 {r[96:112].hex()}")
                a = r[128:256]
                print("      attr " + " ".join(a[4 * i:4 * i + 4].hex() for i in range(32)))


if __name__ == "__main__":
    main()
