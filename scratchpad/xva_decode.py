#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""D-MSX2SPEC: decode probes/bios/spec/xva.asm's capture -- per case and call, the 17-bit address the VDP holds after
the call (R#14 x $4000 + the pointer's 14 bits) and the port $99 writes the call made (register writes Rn := v, and
address settings).  python3 scratchpad/xva_decode.py RUNFILE [--side ref|ours]"""
import re
import sys

CALLS = ("NSETRD", "NSETWR", "NRDVRM", "NWRVRM")
NAMES = ["VA-1", "VA-2", "VA-3", "VA-4", "VA-5", "VA-6", "VA-7 S8", "VA-7 S7", "VA-8", "VA-9", "VA-10 S0/40",
         "VA-10 S0/80", "VA-10 S2", "VA-10 S3", "VA-10 S4", "VA-11", "VA-12", "VA-15", "VA-11b S1 AC2",
         "VA-11c S1 AC3", "VA-11d S1 $1234", "VA-11e S1 $0000", "VA-11f S0 AC1", "VA-11g S2 AC1", "VA-11h S4 AC1"]


def portlog(bs):
    out, i = [], 0
    while i + 1 < len(bs):
        v, c = bs[i], bs[i + 1]
        if c & 0x80:
            out.append(f"R{c & 0x3F}:={v:02X}")
        else:
            out.append(f"{'W' if c & 0x40 else 'R'}@{(c & 0x3F) << 8 | v:04X}")
        i += 2
    return " ".join(out)


def main():
    path = sys.argv[1]
    side = sys.argv[sys.argv.index("--side") + 1] if "--side" in sys.argv else "ref"
    t = open(path).read()
    for blk in re.split(r"^===== ", t, flags=re.M)[1:]:
        head = blk.split("\n", 1)[0]
        m = re.search(rf"CAP {'ref ' if side == 'ref' else 'ours'}: ([0-9a-f]+)", blk)
        if not m:
            print("#", head, "-- no", side, "capture"); continue
        b = bytes.fromhex(m.group(1)) + bytes(2000)
        print("#", head.split(".asm ")[-1], side)
        for r in range(b[1] * 4):
            rec = b[2 + 16 * r: 18 + 16 * r]
            a, f, r14, plo, phi, n = rec[:6]
            addr = r14 * 0x4000 + ((phi << 8 | plo) & 0x3FFF)
            print(f"  {NAMES[rec[14]] if rec[14] < len(NAMES) else rec[14]:12} {CALLS[rec[15] & 3]:7} "
                  f"A={a:02X} F={f:02X} addr=${addr:05X} FFED={rec[13]:02X} writes={n:2} {portlog(rec[6:6 + min(n, 7)])}")


if __name__ == "__main__":
    main()
