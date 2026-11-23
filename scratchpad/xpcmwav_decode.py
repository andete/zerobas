#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""D-TRSPEC (tr6): decode an xpcmwav* run file (probes/bios/spec/xpcmwav.inc): per case and model the return
registers, the time across the call, and the recorded bytes (the case's HL .. HL+BC), with run lengths.

    python3 scratchpad/xpcmwav_decode.py scratchpad/AE_xpcmwavsq_tr.out [--cases FILE.asm]
"""
import re
import sys


def cases_of(asm):
    t = open(asm).read().split("cases:")[1]
    v = re.findall(r"db\s+\$([0-9A-F]{2})\s*\n\s*dw\s+\$([0-9A-F]{4}),\s*\$([0-9A-F]{4})", t)
    return [(int(a, 16), int(h, 16), int(b, 16)) for a, h, b in v]


def runs(b):
    out, i = [], 0
    while i < len(b):
        j = i
        while j < len(b) and b[j] == b[i]:
            j += 1
        out.append(f"{b[i]:02X}x{j - i}" if j - i > 1 else f"{b[i]:02X}")
        i = j
    return " ".join(out)


def main():
    fn = sys.argv[1]
    asm = re.search(r"===== (\S+\.asm)", open(fn).read()).group(1)
    t = open(fn).read()
    cs = cases_of(asm)
    for side, name in (("ref", "FS-A1GT"), ("ours", "FS-A1ST")):
        b = bytes.fromhex(re.search(r"CAP %s\s*: ([0-9a-f]+)" % side, t).group(1)) + bytes(0x1000)
        print(f"===== {name}")
        for i, (a, hl, bc) in enumerate(cs):
            r = b[32 * i:32 * i + 32]
            if r[11] != 0x5A:
                print(f"case {i}: A in ${a:02X} HL ${hl:04X} BC ${bc:04X}: NOT RETURNED (no record)")
                buf = b[hl - 0x8001:hl - 0x8001 + bc]
                print(f"   buffer: {runs(buf)}")
                continue
            t0 = int.from_bytes(r[13:17], "little")
            t1 = int.from_bytes(r[18:22], "little")
            w = lambda k: int.from_bytes(r[k:k + 2], "little")
            print(f"case {i}: A in ${a:02X} HL ${hl:04X} BC ${bc:04X} -> A ${r[2]:02X} F ${r[3]:02X} HL ${w(4):04X} "
                  f"BC ${w(6):04X} DE ${w(8):04X} {'EI' if r[10] else 'DI'} cpu {r[12]}/{r[17]} {t1 - t0} us")
            buf = b[hl - 0x8001:hl - 0x8001 + bc]
            print(f"   stored: {runs(buf)}")
            tr = [k for k in range(1, len(buf)) if buf[k] != buf[k - 1]]
            if "xpcmwavsq" in fn and len(tr) > 2 and set(buf) <= {0x40, 0xC0}:
                # the 1 kHz square changes level every 500 us: the sample period from the first to the last change
                print(f"   sample period: {500 * (len(tr) - 1) / (tr[-1] - tr[0]):.1f} us ({len(tr)} level changes)")
            after = b[hl - 0x8001 + bc:hl - 0x8001 + bc + 2]
            print(f"   after the area: {after.hex()}")


if __name__ == "__main__":
    main()
