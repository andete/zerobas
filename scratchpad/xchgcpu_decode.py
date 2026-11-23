#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""Decode probes/bios/spec/xchgcpu.asm's run file (--row turbor): one line block per case, both machines.

    python3 scratchpad/xchgcpu_decode.py scratchpad/AE_xchgcpu_tr.out
"""
import re
import sys

RECLEN, REC0 = 0xC0, 16
TICK_US = 1e6 / 255682          # the S1990 system timer's period, as openMSX models it (3.911 us)


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
    d = b[8:34]
    regs = dict(zip(("slot", "iff2", "iff1", "HL'", "DE'", "BC'", "AF'", "IY", "IX", "HL", "DE", "BC", "AF"),
                    (w(d, i) for i in range(0, 26, 2))))
    snaps = [(b[34 + 5 * j], b[35 + 5 * j] | b[36 + 5 * j] << 8 | b[37 + 5 * j] << 16 | b[38 + 5 * j] << 24)
             for j in range(3)]
    ch = [(w(b, 99 + 4 * j), b[101 + 4 * j], b[102 + 4 * j]) for j in range(min(20, b[98]))]
    n7, ne4, ne5 = b[179], b[180], b[181]
    return dict(case=b[0], start=b[1], A=b[2], F=b[3], ei=b[4], r6pre=b[5], a7pre=b[6], mark=b[7], regs=regs,
                snaps=snaps, s1990=b[49:65], a7=b[65], getcpu=b[66], ramok=b[67],
                t_ram=w(b, 68), t_bios=w(b, 70), t_rom=w(b, 72),
                log_a7=b[74:74 + min(n7, 8)], log_e4=b[82:82 + min(ne4, 8)], log_e5=b[90:90 + min(ne5, 8)],
                nlog=(n7, ne4, ne5), nch=b[98], changes=ch, sentinel=b[191], fffd=w(b, 182), fcb1set=b[184] if b[4] & 2 else None)


def main():
    c = caps(sys.argv[1])
    n = min(x[0] for x in c.values())
    for m in ("A1GT", "A1ST"):
        h = c[m]
        print(f"{m} INIT: cases {h[0]} | S1990 R#6 {h[1]:02X} | $FCB1 {h[2]:02X} | $A7 {h[3]:02X} | ($FFFD) {w(h, 4):04X} | "
              f"active cpu {'r800' if h[6] else 'z80'} at t = {(h[7] | h[8] << 8 | h[9] << 16 | h[10] << 24) / 1e6:.6f} s")
    for m in ("A1GT", "A1ST"):
        h = c[m]
        print(f"{m} END: R#6 {h[11]:02X} -> CHGCPU($82) -> R#6 {h[12]:02X}, $FCB1 {h[13]:02X}, GETCPU {h[14]:02X}")
    for k in range(n):
        for m in ("A1GT", "A1ST"):
            r = rec(c[m], k)
            rg = r["regs"]
            iff = "EI" if rg["iff2"] & 0x04 else "DI"
            fc = "" if r["fcb1set"] is None else f" FCB1:={r['fcb1set']:02X}"
            print(f"{m} case {r['case']:2d} start {r['start']:02X} A {r['A']:02X} F {r['F']:02X} "
                  f"{'EI' if r['ei'] & 1 else 'DI'}{fc} | R6 pre {r['r6pre']:02X} A7 pre {r['a7pre']:02X} -> "
                  f"AF {rg['AF']:04X} BC {rg['BC']:04X} DE {rg['DE']:04X} HL {rg['HL']:04X} IX {rg['IX']:04X} "
                  f"IY {rg['IY']:04X} AF' {rg['AF\'']:04X} BC' {rg['BC\'']:04X} DE' {rg['DE\'']:04X} "
                  f"HL' {rg['HL\'']:04X} iff(1st,2nd) {rg['iff1']:04X},{rg['iff2']:04X} -> {iff} "
                  f"slot {rg['slot']:04X} | mark {r['mark']:02X} sent {r['sentinel']:02X} ram {r['ramok']:02X}")
            print(f"     cpu@A {r['snaps'][0][0]} | S1990 {r['s1990'].hex(' ')} | A7 {r['a7']:02X} | "
                  f"GETCPU {r['getcpu']:02X} | timer ram {r['t_ram']} bios {r['t_bios']} rom {r['t_rom']} "
                  f"(us: {r['t_ram'] * TICK_US:.0f} / {r['t_bios'] * TICK_US:.0f} / {r['t_rom'] * TICK_US:.0f}) | "
                  f"snap T0->T1 {r['snaps'][2][1] - r['snaps'][1][1]} us cpu {r['snaps'][1][0]},{r['snaps'][2][0]} | "
                  f"($FFFD) after {r['fffd']:04X}")
            print(f"     OUT $A7 {r['log_a7'].hex(' ') or '-'} ({r['nlog'][0]}) | $E4 {r['log_e4'].hex(' ') or '-'} "
                  f"({r['nlog'][1]}) | $E5 {r['log_e5'].hex(' ') or '-'} ({r['nlog'][2]}) | WA changes {r['nch']}: "
                  + " ".join(f"{a:04X}:{o:02X}>{nw:02X}" for a, o, nw in r["changes"]))


if __name__ == "__main__":
    main()
