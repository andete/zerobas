#!/usr/bin/env python3
"""Drop the zerobas page-1 image into a stock C-BIOS main ROM and vet the splice.

On a real MSX, slot-0 page 1 ($4000-$7FFF) holds BASIC, right next to the BIOS in
page 0. C-BIOS has no BASIC, so it leaves page 1 almost empty -- which is exactly
where zerobas belongs. This builds the combined 32 KB main ROM (BIOS in page 0,
zerobas in page 1) that `rom_patch.py make` then diffs into the shipping patch.

The vet: C-BIOS does sprinkle a few small routines into the otherwise-empty page 1
(its `unknown@XXXX` unimplemented-BIOS-call stubs, plus a couple of thunks).
Overlaying zerobas overwrites those bytes. That is benign *iff* nothing actually
reaches them, so before writing the combined ROM we scan the whole stock ROM for a
direct CALL/JP into any overwritten byte. None expected (these are dead stubs that
a real BASIC ROM would itself have occupied); if one is ever found the splice is
unsafe and we stop. Indirect dispatch can't be caught statically -- the end-to-end
boot test (see build-patches.sh / the harness) is the backstop.

    python3 tools/overlay_page1.py stock_cbios.rom basic.rom combined.rom
"""
from __future__ import annotations

import sys

PAGE1 = 0x4000
PAGE2 = 0x8000


def spans(addrs):
    """Group a sorted address list into (start, end_inclusive) runs."""
    out = []
    for a in addrs:
        if out and a == out[-1][1] + 1:
            out[-1][1] = a
        else:
            out.append([a, a])
    return [(a, b) for a, b in out]


def refs_into(rom: bytes, lo: int, hi: int):
    """Offsets of any CALL($CD)/JP($C3) whose literal target is in [lo, hi]."""
    hits = []
    for i in range(len(rom) - 2):
        if rom[i] in (0xCD, 0xC3):
            tgt = rom[i + 1] | (rom[i + 2] << 8)
            if lo <= tgt <= hi:
                hits.append((i, rom[i]))
    return hits


def main() -> int:
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    stock_path, basic_path, out_path = sys.argv[1:4]
    stock = open(stock_path, "rb").read()
    basic = open(basic_path, "rb").read()
    if len(stock) != 0x8000:
        sys.exit(f"{stock_path}: expected a 32 KB C-BIOS main ROM, got {len(stock)}")
    if len(basic) != 0x4000:
        sys.exit(f"{basic_path}: expected a 16 KB zerobas page, got {len(basic)}")
    if basic[:2] != b"AB":
        sys.exit(f"{basic_path}: missing the 'AB' cartridge header")

    p1 = stock[PAGE1:PAGE2]
    overwritten = [i for i in range(0x4000) if p1[i] != 0 and p1[i] != basic[i]]
    unsafe = False
    if overwritten:
        print(f"note: zerobas overwrites {len(overwritten)} non-empty C-BIOS "
              f"page-1 byte(s):")
        for a, b in spans(overwritten):
            seg = p1[a:b + 1]
            asc = "".join(chr(c) if 32 <= c < 127 else "." for c in seg)
            refs = refs_into(stock, PAGE1 + a, PAGE1 + b)
            tag = "  <-- REFERENCED" if refs else "  (unreferenced)"
            print(f"  0x{PAGE1 + a:04X}-0x{PAGE1 + b:04X}  |{asc}|{tag}")
            for off, op in refs:
                kind = "JP" if op == 0xC3 else "CALL"
                print(f"      {kind} from 0x{off:04X}")
                unsafe = True
    else:
        print("note: zerobas occupies only empty ($00) C-BIOS page-1 space.")

    if unsafe:
        sys.exit("error: a stock routine reachable by direct CALL/JP would be "
                 "clobbered -- this C-BIOS variant needs the routine relocated "
                 "before zerobas can take page 1.")

    combined = stock[:PAGE1] + basic + stock[PAGE2:]
    open(out_path, "wb").write(combined)
    print(f"wrote {out_path}: 32 KB (C-BIOS page 0 + zerobas page 1)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
