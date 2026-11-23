#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""Decode the run file of probes/bios/spec/xpcmrec.asm or xpcmstop.asm (same record; --row turbor), both machines.

    python3 scratchpad/xpcmrec_decode.py scratchpad/AE_xpcmrec_tr.out
    python3 scratchpad/xpcmrec_decode.py --entryf scratchpad/AE_xpcmrec2_tr.out   # xpcmrec2.asm: entry F at +210
"""
import re
import sys

RECLEN, REC0 = 0x100, 16
NAMES = ("slot", "iff2", "iff1", "HL'", "DE'", "BC'", "AF'", "IY", "IX", "HL", "DE", "BC", "AF")
KEYS = {0: "-", 1: "CTRL+STOP", 2: "STOP", 3: "CTRL"}


def caps(path):
    out = {}
    for line in open(path):
        m = re.match(r"\s*CAP (ref |ours): ([0-9a-f]+)", line)
        if m:
            out["A1GT" if m.group(1) == "ref " else "A1ST"] = bytes.fromhex(m.group(2))
    return out


def w(b, i):
    return b[i] | b[i + 1] << 8


def main():
    args = sys.argv[1:]
    entryf = "--entryf" in args
    args = [a for a in args if a != "--entryf"]
    c = caps(args[0])
    for m in c:
        print(f"{m}: cases done {c[m][0]}")
    for k in range(max(x[0] for x in c.values()) + 1):
        print(f"--- case {k}")
        for m in ("A1GT", "A1ST"):
            b = c[m][REC0 + k * RECLEN: REC0 + (k + 1) * RECLEN]
            b = b + bytes(RECLEN - len(b))          # a CAP line may end early (trailing zeros)
            if b[11] != 0x5A:
                print(f"  {m}: not reached")
                continue
            t0, t1 = int.from_bytes(b[13:17], "little"), int.from_bytes(b[18:22], "little")
            if k >= c[m][0]:
                print(f"  {m}: start={b[1]:02X} A={b[2]:02X} keys={KEYS[b[3]]} -- ENTERED, NEVER RETURNED "
                      f"(cpusnap at {t0}us)")
                continue
            d = b[22:48]
            R = dict(zip(NAMES, (w(d, i) for i in range(0, 26, 2))))
            n4, n5, ne4, ne5, na7 = w(b, 48), w(b, 50), b[55], b[56], b[57]
            print(f"  {m}: start={b[1]:02X} A={b[2]:02X} keys={KEYS[b[3]]} HL={w(b, 4):04X} BC={w(b, 6):04X} "
                  f"D={b[8]:02X} E={b[9]:02X}" + (f" F={b[210]:02X}" if entryf else "") + f" | R6 {b[10]:02X}->{b[52]:02X} cpu {b[12]}->{b[17]} dt={t1 - t0}us "
                  f"A4in={b[53]:02X} A5in={b[54]:02X}")
            print("     out: " + " ".join(f"{x}={R[x]:04X}" for x in NAMES[3:]) +
                  f" iff={'EI' if R['iff1'] & 4 else 'DI'} slot={R['slot']:04X}")
            print(f"     A5 x{n5} (first 16): {b[58:58 + min(n5, 16)].hex()}  E4 x{ne4}: {b[74:74 + min(ne4, 8)].hex()}"
                  f"  E5 x{ne5}: {b[82:82 + min(ne5, 8)].hex()}  A7 x{na7}: {b[90:90 + min(na7, 8)].hex()}")
            print(f"     buf: {b[98:146].hex()}")
            print(f"     A4 x{n4} (first 64): {b[146:146 + min(n4, 64)].hex()}")


if __name__ == "__main__":
    main()
