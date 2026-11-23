#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""Decode probes/bios/spec/xgetcpu.asm's run file (--row turbor): one line pair per case, both machines.

    python3 scratchpad/xgetcpu_decode.py scratchpad/AE_xgetcpu_tr.out
"""
import re
import sys

RECLEN, REC0 = 0x40, 16
TICK_US = 1e6 / 255682          # the S1990 system timer's period, as openMSX models it (3.911 us)
NAMES = ("slot", "iff2", "iff1", "HL'", "DE'", "BC'", "AF'", "IY", "IX", "HL", "DE", "BC", "AF")


def caps(path):
    out = {}
    for line in open(path):
        m = re.match(r"\s*CAP (ref |ours): ([0-9a-f]+)", line)
        if m:
            out["A1GT" if m.group(1) == "ref " else "A1ST"] = bytes.fromhex(m.group(2))
    return out


def w(b, i):
    return b[i] | b[i + 1] << 8


def rec(cap, k):
    b = cap[REC0 + k * RECLEN: REC0 + (k + 1) * RECLEN]
    b = b + bytes(RECLEN - len(b))
    regs = {n: w(b, 8 + 2 * i) for i, n in enumerate(NAMES)}
    ch = [(w(b, 41 + 4 * j), b[43 + 4 * j], b[44 + 4 * j]) for j in range(min(4, b[40]))]
    return dict(case=b[0], mode=b[1], A=b[2], F=b[3], flags=b[4], value=b[5], r6pre=b[6], fcb1pre=b[7], regs=regs,
                r6=b[34], fcb1=b[35], t_get=w(b, 36), t_kil=w(b, 38), nch=b[40], changes=ch, sentinel=b[63])


def main():
    c = caps(sys.argv[1])
    n = min(x[0] for x in c.values())
    for k in range(n):
        for m in ("A1GT", "A1ST"):
            r = rec(c[m], k)
            g = r["regs"]
            f = r["flags"]
            setup = ("EI " if f & 1 else "DI ") + (f"FCB1:={r['value']:02X} " if f & 2 else "") + \
                (f"R6:={r['value']:02X} " if f & 4 else "")
            iff = "EI" if g["iff2"] & 0x04 else "DI"
            print(f"{m} case {r['case']:2d} CHGCPU({r['mode']:02X}) {setup}| A {r['A']:02X} F {r['F']:02X} | before R6 "
                  f"{r['r6pre']:02X} FCB1 {r['fcb1pre']:02X} -> A {g['AF'] >> 8:02X} F {g['AF'] & 255:02X} BC {g['BC']:04X} "
                  f"DE {g['DE']:04X} HL {g['HL']:04X} IX {g['IX']:04X} IY {g['IY']:04X} AF' {g['AF' + chr(39)]:04X} "
                  f"BC' {g['BC' + chr(39)]:04X} DE' {g['DE' + chr(39)]:04X} HL' {g['HL' + chr(39)]:04X} "
                  f"iff {g['iff1'] & 255:02X},{g['iff2'] & 255:02X} -> {iff} slot {g['slot']:04X} sent {r['sentinel']:02X}")
            print(f"     after R6 {r['r6']:02X} FCB1 {r['fcb1']:02X} | 200 x GETCPU {r['t_get']} ticks "
                  f"({r['t_get'] * TICK_US:.0f} us), 200 x KILBUF {r['t_kil']} ({r['t_kil'] * TICK_US:.0f} us) | "
                  f"WA changes {r['nch']}: " + " ".join(f"{a:04X}:{o:02X}>{x:02X}" for a, o, x in r["changes"]))


if __name__ == "__main__":
    main()
