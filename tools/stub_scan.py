#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""stub_scan -- which published MSX1 BIOS entries are still C-BIOS STUBS in OUR main ROM
(D-BIOSRUNG, 2026-11-12).

zerobas's main BIOS is C-BIOS, repacked (cbios-repack/*.patch, tools/build_mainrom.py).
C-BIOS leaves some entries as stubs, and a stub is still a stub here unless we replaced
it. The entry table (tools/entry_table.py) only said "exercised" -- a gate names the
entry -- so a stub called by a row that cannot tell it from the real thing read as
exercised. This scan follows each of the 108 published entries through the jump table
of the BUILT main ROM (build/zerobas-main-eu.rom: our own C-BIOS-based bytes, never a
reference ROM's) to the body it lands on, and names two stub shapes:

  print_debug  C-BIOS's stub: push hl / push af / ld hl,<name> / call print_debug
               (every match must call the SAME routine, or the shape is a coincidence)
  bare ret     the body is a lone `ret` (graphics-cursor.patch leaves PNTINI / SCANR /
               SCANL that way)

It REFUSES rather than answering on a degenerate input: a missing or wrongly sized ROM,
or a jump table that does not decode (fewer than MIN_DECODED entries are a `jp` or
`di / jp`) -- a scan that read the wrong bytes must not print "0 stubs".

    python3 tools/stub_scan.py            # the stubbed entries
    python3 tools/stub_scan.py --all      # every entry and where it lands
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROM = os.path.join(ROOT, "build", "zerobas-main-eu.rom")
MIN_DECODED = 100


class ScanRefused(Exception):
    pass


def _entries():
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    from entry_table import BIOS   # noqa: E402 -- the one list of published entries
    return BIOS


def scan(rom_path=ROM):
    """{addr: dict(name, target, kind)} for the 108 entries; kind '' when not a stub."""
    if not os.path.exists(rom_path):
        raise ScanRefused(f"{rom_path} does not exist -- build it (make basic-reloc)")
    rom = open(rom_path, "rb").read()
    if len(rom) != 0x8000:
        raise ScanRefused(f"{rom_path} is {len(rom)} B, not 32768 -- not a main ROM image")

    def follow(a, depth=0):
        if depth < 4 and rom[a] == 0xC3:
            return follow(rom[a + 1] | rom[a + 2] << 8, depth + 1)
        if depth < 4 and rom[a] == 0xF3 and rom[a + 1] == 0xC3:
            return follow(rom[a + 2] | rom[a + 3] << 8, depth + 1)
        return a

    out, decoded, pd_targets = {}, 0, set()
    for addr, name in _entries():
        if rom[addr] == 0xC3 or (rom[addr] == 0xF3 and rom[addr + 1] == 0xC3):
            decoded += 1
        t = follow(addr)
        body = rom[t:t + 8] if t + 8 <= len(rom) else b""
        kind = ""
        if len(body) == 8 and body[0] == 0xE5 and body[1] == 0xF5 and body[2] == 0x21 \
                and body[5] == 0xCD:
            kind = "print_debug"
            pd_targets.add(body[6] | body[7] << 8)
        elif body[:1] == b"\xC9":
            kind = "bare ret"
        out[addr] = dict(name=name, target=t, kind=kind)
    if decoded < MIN_DECODED:
        raise ScanRefused(f"only {decoded} of {len(out)} entries decode as a jump -- the "
                          "image is not the jump table this scan expects")
    if len(pd_targets) > 1:
        raise ScanRefused("the print_debug shape calls " + ", ".join(f"${x:04X}" for x in
                          sorted(pd_targets)) + " -- more than one routine, so the shape is "
                          "matching something else too")
    return out


def stubs(rom_path=ROM):
    return {a: r for a, r in scan(rom_path).items() if r["kind"]}


def main():
    try:
        rows = scan()
    except ScanRefused as e:
        print(f"🔴 stub_scan REFUSED: {e}")
        return 2
    show = rows if "--all" in sys.argv else {a: r for a, r in rows.items() if r["kind"]}
    for a, r in sorted(show.items()):
        print(f"${a:04X} {r['name']:7} -> ${r['target']:04X}  {r['kind'] or '-'}")
    n = sum(1 for r in rows.values() if r["kind"])
    print(f"stub_scan: {n} of {len(rows)} published entries are still stubs in "
          f"{os.path.relpath(ROM, ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
