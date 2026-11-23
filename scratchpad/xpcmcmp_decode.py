#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""Decode probes/bios/spec/xpcmcmp.asm's run file (--row turbor): per pattern, the $A4 bytes PCMPLY wrote, run-length
compressed for reading (`80*37` = 37 x $80), both machines.

    python3 scratchpad/xpcmcmp_decode.py scratchpad/AE_xpcmcmp_tr.out
"""
import re
import sys

RECLEN, REC0 = 0x400, 16


def caps(path):
    out = {}
    for line in open(path):
        m = re.match(r"\s*CAP (ref |ours): ([0-9a-f]+)", line)
        if m:
            out["A1GT" if m.group(1) == "ref " else "A1ST"] = bytes.fromhex(m.group(2))
    return out


def rle(bs):
    out, i = [], 0
    while i < len(bs):
        j = i
        while j < len(bs) and bs[j] == bs[i]:
            j += 1
        out.append(f"{bs[i]:02x}" + (f"*{j - i}" if j - i > 1 else ""))
        i = j
    return " ".join(out)


def main():
    c = caps(sys.argv[1])
    for m in c:
        print(f"{m}: cases done {c[m][0]}")
    for k in range(max(x[0] for x in c.values())):
        for m in ("A1GT", "A1ST"):
            b = c[m][REC0 + k * RECLEN: REC0 + (k + 1) * RECLEN]
            if k >= c[m][0]:
                print(f"case {k} {m}: not reached")
                continue
            n = b[1]
            t0 = int.from_bytes(b[19:23], "little")
            t1 = int.from_bytes(b[24:28], "little")
            n4 = b[28] | b[29] << 8
            n5 = b[30] | b[31] << 8
            hl, bc, af = (b[32] | b[33] << 8), (b[34] | b[35] << 8), (b[36] | b[37] << 8)
            print(f"case {k} {m}: pattern {b[2:2 + n].hex(' ')} | dt={t1 - t0}us HL={hl:04X} BC={bc:04X} AF={af:04X}"
                  f" | A5 x{n5}: {b[64:64 + min(n5, 16)].hex()} | A4 x{n4}: {rle(b[80:80 + min(n4, 944)])}")


if __name__ == "__main__":
    main()
