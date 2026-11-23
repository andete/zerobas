#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""D-MSX2SPEC: decode probes/bios/spec/xsubctx.asm (sub-ROM $0119, CLRTXT).
    python3 scratchpad/xsubctx_decode.py RUNFILE [--side ref|ours]
Per row: S = all spaces, G = first and last byte still the probe's garbage g(a), else the counts.
Refuses a record whose sentinel ($5E at +383) is missing."""
import re
import sys

REC = 384
NAMES = ["0 S0w40 Z A0", "1 S0w40 EI", "2 S0w40 NZ", "3 S0w40 Z A=FF", "4 S0w40 key on", "5 S0w37",
         "6 S0w80", "7 S0w80 key on", "8 S1", "9 S1 key on", "10 S2", "11 S5"]
WIN = {0: (0x0800, 0x0438, 0x1000), 6: (0x0800, 0x0870, 0x1000), 8: (0x2000, 0x0000, 0x1C00),
       10: (0x2000, 0x0000, 0x1C00), 11: (0x6A00, 0x7000, 0x7600)}


def g(a):
    return ((a & 0xFF) + 3 * (a >> 8)) & 0x7F | 0x80


def txt(bs):
    return "".join(chr(c) if 32 <= c < 127 else "." for c in bs)


def decode(b, k):
    r = b[2 + REC * k: 2 + REC * (k + 1)]
    if len(r) < REC or r[REC - 1] != 0x5E:
        sys.exit(f"REFUSED: case {k}: sentinel missing")
    c = r[0]
    out = [f"== {NAMES[c]}"]
    out.append(f"  A={r[1]:02X} F={r[2]:02X} IFF={r[3]} (first {r[14]}) BC={r[5]:02X}{r[4]:02X} DE={r[7]:02X}{r[6]:02X} "
               f"HL={r[9]:02X}{r[8]:02X} IX={r[11]:02X}{r[10]:02X} IY={r[13]:02X}{r[12]:02X}")
    out.append(f"  CSRY={r[16]} CSRX={r[17]} CNSDFG={r[18]:02X} SCRMOD={r[19]} LINLEN={r[20]} CRTCNT={r[21]} "
               f"LINL40={r[22]} LINL32={r[23]}")
    out.append("  LINTTB=" + r[24:48].hex(" ") + "  RG0-7SAV=" + r[48:56].hex(" "))
    rl, base = r[348], r[349] | r[350] << 8
    rows = []
    for i in range(27):
        sp, fi, la = r[56 + 3 * i: 59 + 3 * i]
        a0, a1 = base + rl * i, base + rl * i + rl - 1
        if sp == rl:
            rows.append("S")
        elif fi == g(a0) and la == g(a1) and sp == 0:
            rows.append("G")
        else:
            rows.append(f"[{sp}:{fi:02X}..{la:02X}]")
    out.append(f"  base=${base:04X} rowlen={rl} rows 0-26: " + " ".join(rows))
    out.append("  row0 : |" + txt(r[140:140 + rl]) + "|")
    out.append("  row23: |" + txt(r[220:220 + rl]) + "|")
    win = WIN[max(x for x in WIN if x <= c)]
    for i, a in enumerate(win):
        w = r[300 + 16 * i: 316 + 16 * i]
        same = all(w[j] == g(a + j) for j in range(16))
        out.append(f"  win ${a:04X}: {'garbage kept' if same else w.hex(' ')}")
    return "\n".join(out)


def main():
    side = sys.argv[sys.argv.index("--side") + 1] if "--side" in sys.argv else "ref"
    for blk in re.split(r"^===== ", open(sys.argv[1]).read(), flags=re.M)[1:]:
        m = re.search(rf"CAP {'ref ' if side == 'ref' else 'ours'}: ([0-9a-f]+)", blk)
        if not m:
            continue
        b = bytes.fromhex(m.group(1)) + bytes(REC * 20)
        if b[0] != 0xA5:
            print("# NOT FINISHED", blk.split("\n", 1)[0])
        print("#", blk.split("\n", 1)[0].split(".asm ")[-1].split(" =")[0], side, f"cases={b[1]}")
        for k in range(b[1]):
            print(decode(b, k))


if __name__ == "__main__":
    main()
