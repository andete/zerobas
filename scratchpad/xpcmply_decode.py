#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""Decode probes/bios/spec/xpcmply.asm's run file (--row turbor): one block per case, both machines.

    python3 scratchpad/xpcmply_decode.py scratchpad/AE_xpcmply_tr.out [RECLEN]
"""
import re
import sys

RECLEN, REC0 = 0x200, 16
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
    b = b + bytes(RECLEN - len(b))                  # a CAP line may end early (trailing zeros)
    d = b[8:34]
    regs = dict(zip(NAMES, (w(d, i) for i in range(0, 26, 2))))
    snaps = [(b[34 + 5 * j], b[35 + 5 * j] | b[36 + 5 * j] << 8 | b[37 + 5 * j] << 16 | b[38 + 5 * j] << 24)
             for j in range(2)]
    n4, n5 = w(b, 56), w(b, 58)
    ch = [(w(b, 61 + 4 * j), b[63 + 4 * j], b[64 + 4 * j]) for j in range(min(11, b[60]))]
    return dict(case=b[0], start=b[1], A=b[2], F=b[3], ei=b[4], r6pre=b[5], log=b[6], mark=b[7], regs=regs,
                snaps=snaps, r6=b[44], getcpu=b[45], a4=b[46], a5=b[47], fcb1=b[48], a7=b[49],
                hl=w(b, 50), bc=w(b, 52), d=b[54], e=b[55], n4=n4, n5=n5, nch=b[60], changes=ch, a5pre=b[109],
                log5=b[110:110 + min(n5, 32)], log4=b[190:190 + min(n4, 322)],
                loge4=b[142:142 + min(b[105], 16)], loge5=b[158:158 + min(b[106], 16)],
                loga7=b[174:174 + min(b[107], 16)], n7=(b[105], b[106], b[107]))


def iff(f):
    return "EI" if f & 4 else "DI"


def main():
    c = caps(sys.argv[1])
    n = min(x[0] for x in c.values())
    print(f"cases done: " + ", ".join(f"{m} {c[m][0]}" for m in c))
    for k in range(max(x[0] for x in c.values())):
        print(f"--- case {k}")
        for m in ("A1GT", "A1ST"):
            if k >= c[m][0]:
                print(f"  {m}: (not reached)")
                continue
            r = rec(c[m], k)
            R = r["regs"]
            dt = r["snaps"][1][1] - r["snaps"][0][1]
            print(f"  {m}: start={r['start']:02X} A={r['A']:02X} F={r['F']:02X} {'EI' if r['ei'] & 1 else 'DI'}"
                  f" HL={r['hl']:04X} BC={r['bc']:04X} D={r['d']:02X} E={r['e']:02X} | R6 {r['r6pre']:02X}->"
                  f"{r['r6']:02X} cpu {r['snaps'][0][0]}->{r['snaps'][1][0]} getcpu={r['getcpu']:02X}"
                  f" dt={dt}us A4in={r['a4']:02X} A5 {r['a5pre']:02X}->{r['a5']:02X} A7={r['a7']:02X}"
                  f" FCB1={r['fcb1']:02X}")
            print("     out: " + " ".join(f"{k2}={R[k2]:04X}" for k2 in NAMES[3:]) +
                  f" iff={iff(R['iff1'])}/{iff(R['iff2'])} slot={R['slot']:04X}")
            print(f"     wa: {r['nch']} " + " ".join(f"{a:04X}:{x:02X}->{y:02X}" for a, x, y in r["changes"]))
            if r["log"]:
                print(f"     A4 x{r['n4']}: {r['log4'].hex()}")
                print(f"     A5 x{r['n5']}: {r['log5'].hex()}   E4 x{r['n7'][0]}: {r['loge4'].hex()}"
                      f"  E5 x{r['n7'][1]}: {r['loge5'].hex()}  A7 x{r['n7'][2]}: {r['loga7'].hex()}")


if __name__ == "__main__":
    main()
