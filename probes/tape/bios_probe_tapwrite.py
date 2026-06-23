#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Phase-1 write-path oracle probe: record what TAPOON+TAPOUT actually emit.

Unlike bios_probe_tapout.py (which only samples PPI-C and the carry flag), this
cart drives a *real* write session so the host can record the CAS-out signal as a
tape image and decode it back to bytes -- the signal-level oracle the cassette
spec marks "to capture". It is our own clean code: it calls only the public BIOS
entry points and observes outputs, never a reference disassembly.

Sequence: TAPOON (long header / leader tone) -> TAPOUT each of a known byte
pattern -> TAPOOF (flush + motor off) -> DONE landmark. Run on the VG-8020 oracle
with `cassetteplayer new <file>` (record mode); decode the file and assert the
bytes round-trip to PATTERN. On C-BIOS (tape stub) nothing is written -- the
negative control.

  python3 probes/tape/bios_probe_tapwrite.py --out tapwrite.rom
"""
from __future__ import annotations

# --- zerobas probes: locate shared infra (probes/lib) + sibling probes ---
import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))  # sibling probes
_sys.path.insert(0, _os.path.join(
    _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "lib"))  # shared infra

import argparse, os, sys
import z80probe as Z  # noqa: E402

TAPOON = 0x00EA
TAPOUT = 0x00ED
TAPOOF = 0x00F0

# A recognisable, non-symmetric pattern: alternating-bit bytes plus ASCII so a
# decode is unambiguous and bit-order errors are visible.
PATTERN = [0x55, 0xAA, 0x4A, 0x4F, 0x4E, 0x47]   # 0x55,0xAA,"JONG"


def build(pattern=PATTERN, long_header: bool = True, baud: int = 1200) -> bytes:
    c = Z.Cart()
    cy_on = c.alloc(1)          # carry after TAPOON
    cy_out = c.alloc(1)         # carry after the last TAPOUT
    nbytes = c.alloc(1)         # pattern length, for the decoder's convenience
    c.emit(Z.di())
    # Select the write baud the way a real BIOS + SCREEN ,,,baud would: lay down
    # the standard CS120/CS240 tables (blank on bare C-BIOS) and copy the chosen
    # one into the active slots, which our TAPOON/TAPOUT read to pick the baud.
    c.emit(Z.setup_cas_baud(baud))
    # TAPOON: A != 0 -> long header (leader tone); A == 0 -> short header.
    c.emit(Z.ld_a(0xFF if long_header else 0x00))
    c.emit(Z.call(TAPOON))
    c.emit([0xF5, 0xC1, 0x79, 0xE6, 0x01], Z.sta(cy_on))   # carry(TAPOON)->cy_on
    for b in pattern:
        c.emit(Z.ld_a(b))
        c.emit(Z.call(TAPOUT))
    c.emit([0xF5, 0xC1, 0x79, 0xE6, 0x01], Z.sta(cy_out))  # carry(last TAPOUT)
    c.emit(Z.call(TAPOOF))
    c.emit(Z.ld_a(len(pattern)), Z.sta(nbytes))
    return c.build()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True)
    ap.add_argument("--short-header", action="store_true",
                    help="use a short leader (TAPOON A=0) instead of long")
    ap.add_argument("--baud", type=int, choices=(1200, 2400), default=1200,
                    help="write baud rate (copies CS120/CS240 into the active "
                         "timing table before TAPOON, as SCREEN does; default 1200)")
    ap.add_argument("--pattern", help="hex bytes to write, e.g. '00 FF 00 FF' "
                    "(default: the standard 55 AA 4A 4F 4E 47)")
    args = ap.parse_args()
    pattern = [int(x, 16) for x in args.pattern.split()] if args.pattern else PATTERN
    with open(args.out, "wb") as f:
        f.write(build(pattern=pattern, long_header=not args.short_header, baud=args.baud))
    pat = " ".join(f"{b:02X}" for b in PATTERN)
    print(f"wrote {args.out}: TAPOON+TAPOUT[{pat}]+TAPOOF; "
          f"3 result bytes at 0x{Z.RESULT:04X}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
