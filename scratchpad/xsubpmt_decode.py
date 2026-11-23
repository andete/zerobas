#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""D-MSX2SPEC: decode probes/bios/spec/xsubpmt.asm (sub-ROM PROMPT).
    python3 scratchpad/xsubpmt_decode.py RUNFILE [--side ref|ours]
Refuses a record whose sentinel ($5E at +511) is missing."""
import re
import sys

REC = 512
NAMES = ["0 S0w40 found (1,6)", "1 same EI", "2 ID2 ABC\\0QR", "3 ID2 ABCDEF", "4 ID2 six 00", "5 ID2 ABC+zeros",
         "6 ID0 title XYZ", "7 ID1 password XYZ", "8 ID3 XYZ", "9 ABCDEF at (5,6)", "10 title at (5,6)",
         "11 ABCDEF w80", "12 ABCDEF SCREEN1", "13 ABCDEF SCREEN5", "14 ABCDEF row 23 CNSDFG FF",
         "15 title row 23 CNSDFG FF", "16 ID6 ABCDEF", "17 IDA ABCDEF", "18 IDF ABCDEF", "19 ABCDEF MODE 8 before"]


def txt(bs):
    return "".join(chr(c) if 32 <= c < 127 else "." for c in bs)


def decode(b, k):
    r = b[2 + REC * k: 2 + REC * (k + 1)]
    if len(r) < REC or r[REC - 1] != 0x5E:
        sys.exit(f"REFUSED: case {k}: sentinel missing")
    out = [f"== {NAMES[r[0]]}"]
    out.append(f"  A={r[1]:02X} F={r[2]:02X} IFF={r[3]} (first {r[14]}) BC={r[5]:02X}{r[4]:02X} DE={r[7]:02X}{r[6]:02X} "
               f"HL={r[9]:02X}{r[8]:02X} IX={r[11]:02X}{r[10]:02X} IY={r[13]:02X}{r[12]:02X}")
    out.append(f"  CSRY={r[16]} CSRX={r[17]} CNSDFG={r[18]:02X} SCRMOD={r[19]} LINLEN={r[20]} CRTCNT={r[21]}")
    n = r[24]
    out.append(f"  H.CHPU count={n} chars={r[25:25 + min(n, 48)].hex(' ')} |{txt(r[25:25 + min(n, 48)])}|")
    out.append(f"  port98 bytes={r[74] | r[75] << 8} blk3=" + "".join(f"{x:X}" for x in r[76:89])
               + f" MODE before={r[92]:X} after={r[89]:X}")
    rl, fr = r[90], r[91]
    for i in range(4):
        out.append(f"  row{fr + i:2}: |" + txt(r[96 + 80 * i: 96 + 80 * i + rl]) + "|")
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
