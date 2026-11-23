#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""Decode scratchpad/AE_xextrom_msx2.out (probes/bios/spec/xextrom.asm): EXTROM / SUBROM with a RAM stub.

    python3 scratchpad/xextrom_decode.py [scratchpad/AE_xextrom_msx2.out]
"""
import re
import sys

ENT = dict(IX=None, IY=0x1A2B, AF_=0x3C4D, BC_=0x5E6F, DE_=0x7081, HL_=0x92A3, BC=0xB1C2, DE=0x4E5F, HL=0x9876)
CLOB = dict(IX=0xC1C2, IY=0xC3C4, AF_=0xC5C6, BC_=0xC7C8, DE_=0xC9CA, HL_=0xCBCC, AF=0xCDCE, BC=0xCFD0,
            DE=0xD1D2, HL=0xD3D4)
NAMES = ["SLOT", "IFF2", "IFF1", "HL_", "DE_", "BC_", "AF_", "IY", "IX", "HL", "DE", "BC", "AF"]
KIND = ["EXTROM p1", "EXTROM p2", "SUBROM p1", "SUBROM p2"]


def caps(path):
    row, out = None, {}
    for line in open(path):
        m = re.match(r"===== \S+ (\w+):", line)
        if m:
            row = m.group(1)
        m = re.match(r"\s+CAP (ref |ours): ([0-9a-f]+)", line)
        if m and row:
            out[(row, m.group(1).strip())] = bytes.fromhex(m.group(2)) + bytes(0x500)
    return out


def dump(b):
    d = {}
    for i, n in enumerate(NAMES):
        d[n] = b[2 * i] | b[2 * i + 1] << 8
    return d


def fmt(d):
    iff = lambda w: "on" if (w & 0x04) else "off"
    s = f"A8={d['SLOT'] >> 8:02X} FFFF={d['SLOT'] & 255:02X} IFF={iff(d['IFF1'])}/{iff(d['IFF2'])} "
    s += " ".join(f"{n}={d[n]:04X}" for n in NAMES[3:])
    return s


def sig(r):
    """One case's semantic reading: what reached the routine, what came back, IFF, slots, stack."""
    st, af = dump(r[2:28]), dump(r[30:56])
    ran = not (r[2] == 0xEE and r[3] == 0xEE)
    ssp, rsp, mk = r[28] | r[29] << 8, r[56] | r[57] << 8, r[58] | r[59] << 8
    o = {}
    if ran:
        o["in: A F BC DE HL"] = "entry" if (st["BC"], st["DE"], st["HL"]) == (ENT["BC"], ENT["DE"], ENT["HL"]) \
            and st["AF"] >> 8 == 0xA7 else f"{st['AF']:04X} {st['BC']:04X} {st['DE']:04X} {st['HL']:04X}"
        o["in: F"] = f"{st['AF'] & 255:02X}"
        o["in: IX"] = f"{st['IX']:04X}"
        o["in: IY, AF' BC' DE' HL'"] = "entry" if all(st[n] == ENT[n] for n in ("IY", "AF_", "BC_", "DE_", "HL_")) \
            else "not the entry values"
        o["in: IFF"] = ("on" if st["IFF1"] & 4 else "off") + "/" + ("on" if st["IFF2"] & 4 else "off")
        o["in: slots A8/FFFF"] = f"{st['SLOT'] >> 8:02X}/{st['SLOT'] & 255:02X}"
        o["frame: caller SP E7FC - routine SP"] = f"{0xE7FC - ssp}"
    else:
        o["in"] = "routine is the real sub-ROM"
    def cls(n):
        v = af[n]
        if v == CLOB.get(n):
            return "routine's"
        if ENT.get(n) is not None and v == ENT[n]:
            return "entry"
        return f"{v:04X}"
    for n in ("AF", "BC", "DE", "HL", "IX"):
        o["out: " + n] = cls(n)
    o["out: IY AF' BC' DE' HL'"] = "/".join(cls(n) for n in ("IY", "AF_", "BC_", "DE_", "HL_"))
    o["out: IFF"] = ("on" if af["IFF1"] & 4 else "off") + "/" + ("on" if af["IFF2"] & 4 else "off")
    o["slots before -> after (A8/FFFF)"] = f"{r[62]:02X}/{r[63]:02X} -> {af['SLOT'] >> 8:02X}/{af['SLOT'] & 255:02X}"
    o["SP after (E800 = balanced)"] = f"{rsp:04X}"
    o["stack: E7FC - lowest marker hit"] = f"{0xE7FC - mk}" if mk else "none"
    o["EXBRSA after"] = f"{r[60]:02X}"
    return o


CASES = ["EXTROM, clobber stub, entry DI", "EXTROM, clobber, entry EI, F FF", "EXTROM, stub does EI, entry DI",
         "EXTROM, stub does DI, entry EI", "EXTROM, IX 3ABC, clobber", "EXTROM, stub returns as entered",
         "EXTROM from page 2 RAM", "SUBROM, pushed A5A5, clobber", "SUBROM, pushed 1234", "SUBROM, entry EI",
         "SUBROM, stub EI, entry DI", "SUBROM from page 2 RAM", "EXTROM -> real SETPLT (5: A3/06)",
         "EXTROM -> real GETPLT, A 5", "EXTROM, EXBRSA back to the RAM slot", "SUBROM -> real GETPLT, EI"]
ORDER = [("msx2jp", "ref"), ("msx2eu", "ref"), ("msx2p", "ref"), ("msx2jp", "ours"), ("msx2eu", "ours"),
         ("msx2p", "ours")]
LABEL = {("msx2jp", "ref"): "F900", ("msx2eu", "ref"): "8250", ("msx2p", "ref"): "WSX",
         ("msx2jp", "ours"): "cb2jp", ("msx2eu", "ours"): "cb2eu", ("msx2p", "ours"): "cb2+"}


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "scratchpad/AE_xextrom_msx2.out"
    cs = caps(path)
    for k in ORDER:
        c = cs[k]
        print(f"{LABEL[k]:6} cases {c[0]} ramslot {c[1]:02X} EXBRSA@init {c[2]:02X} EXPTBL {c[3:7].hex()} "
              f"p0ram {c[7]} p2ram {c[8]} guard-ints {c[9]} sentinel {c[10]:02X}")
    for i, name in enumerate(CASES):
        print(f"\n== case {i}: {name}")
        sigs = {}
        for k in ORDER:
            r = cs[k][16 + 64 * i: 16 + 64 * i + 64]
            sigs[k] = sig(r) if r[61] == 0x5A else {"record": "missing"}
        keys = []
        for s in sigs.values():
            keys += [x for x in s if x not in keys]
        for f in keys:
            vals = [sigs[k].get(f, "-") for k in ORDER]
            if len(set(vals)) == 1:
                print(f"  {f:38} all six: {vals[0]}")
            else:
                print(f"  {f:38} " + " | ".join(f"{LABEL[k]} {v}" for k, v in zip(ORDER, vals)))


if __name__ == "__main__":
    main()
