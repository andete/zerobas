#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Mint a tiny, self-authored MSX cartridge for the openMSX harness.

This is *our own* clean code -- nothing is derived from any copyrighted BIOS.
The default cartridge is a Phase-1 "sentinel": its INIT routine writes a marker
string to a RAM address, then jumps to a fixed DONE landmark and loops there.
The harness boots it under a machine, runs until a breakpoint at DONE, and reads
the marker back -- proving the full insert -> run -> observe loop works.

The fixed DONE landmark (default 0x7FF0) is the synchronisation point: it sits at
a constant address regardless of payload size, so the harness can `--bp 0x7FF0`
and capture exactly when the cartridge has finished, independent of how long the
machine's BIOS took to boot and call INIT.

Phase 2 (parked) will grow the payload into a battery of BIOS calls that records
results into a RAM buffer; the header/DONE scaffolding here is reused as-is.

    python3 probes/lib/probe_cart.py --out sentinel.rom            # default marker
    python3 probes/lib/probe_cart.py --marker JONG --at 0xE000 --out sentinel.rom
"""
from __future__ import annotations

import argparse

INIT = 0x4010   # cartridge INIT entry (page-1 mapped address)
DONE = 0x7FF0   # fixed "finished" landmark -> JR $ ; the harness breakpoints here


def build(marker: bytes, at: int) -> bytes:
    rom = bytearray(b"\xff" * 0x4000)            # 16 KB, page 1 (0x4000-0x7FFF)

    def w(addr: int, *bs: int) -> None:
        off = addr - 0x4000
        for i, b in enumerate(bs):
            rom[off + i] = b

    # Cartridge header: 'AB', INIT pointer, then STATEMENT/DEVICE/TEXT = 0.
    w(0x4000, 0x41, 0x42, INIT & 0xFF, INIT >> 8)

    # INIT: write each marker byte to `at`, then JP DONE.
    prog: list[int] = []
    for i, ch in enumerate(marker):
        dst = at + i
        prog += [0x3E, ch, 0x32, dst & 0xFF, dst >> 8]   # LD A,ch ; LD (dst),A
    prog += [0xC3, DONE & 0xFF, DONE >> 8]               # JP DONE
    w(INIT, *prog)

    w(DONE, 0x18, 0xFE)                                  # DONE: JR $  (halt here)
    return bytes(rom)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--marker", default="JONG",
                    help="ASCII marker the INIT routine writes (default JONG)")
    ap.add_argument("--at", type=lambda s: int(s, 0), default=0xE000,
                    help="RAM address to write the marker to (default 0xE000)")
    ap.add_argument("--out", required=True, help="output .rom path")
    args = ap.parse_args()

    rom = build(args.marker.encode("ascii"), args.at)
    with open(args.out, "wb") as f:
        f.write(rom)
    print(f"wrote {args.out}: 16K cart, INIT=0x{INIT:04X}, DONE=0x{DONE:04X}, "
          f"marker {args.marker!r} -> 0x{args.at:04X}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
