#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Phase-2 read-path probe: read bytes back via TAPION + TAPIN.

Mounts a known-good FSK recording as cassette media (e.g. our own write-path WAV
from bios_probe_tapwrite.py) and drives the BIOS read path: TAPION locks onto the
leader and derives the baud threshold, then TAPIN reads each framed byte.  The
bytes recovered are written to the result buffer so the host can assert they
round-trip to the pattern that was written -- closing the write->read loop.

  0xE000      : carry after TAPION (00 = locked)
  0xE001..06  : the 6 bytes read by TAPIN
  0xE007      : carry after the last TAPIN (00 = ok)

It calls only public BIOS entry points and observes the bytes out -- black-box,
no reference disassembly.  On the unmodified C-BIOS stub TAPION returns carry=1
and no bytes are read (the negative control).

  python3 probes/tape/bios_probe_tapread.py --out tapread.rom
  python3 probes/lib/omsx_run.py --machine C-BIOS_MSX1_EU_TAPE --cart tapread.rom \
      --cassette ours.wav --bp 0x7FF0 --mem memory:0xE000:8 --out cap.txt
  python3 probes/tape/bios_probe_tapread.py --analyze cap.txt
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

TAPION = 0x00E1
TAPIN = 0x00E4
TAPIOF = 0x00E7

# Must match bios_probe_tapwrite.PATTERN so the round-trip assertion is symmetric.
PATTERN = [0x55, 0xAA, 0x4A, 0x4F, 0x4E, 0x47]


def build(n=None) -> bytes:
    if n is None:
        n = len(PATTERN)
    c = Z.Cart()
    cy_ion = c.alloc(1)             # carry after TAPION
    buf = c.alloc(n)               # bytes read
    cy_in = c.alloc(1)             # carry after the last TAPIN
    c.emit(Z.di())
    c.emit(Z.call(TAPION))
    c.emit([0xF5, 0xC1, 0x79, 0xE6, 0x01], Z.sta(cy_ion))   # carry(TAPION)->cy_ion
    for i in range(n):
        c.emit(Z.call(TAPIN))
        c.emit(Z.sta(buf + i))                              # LD (buf+i),A (flags kept)
        if i == n - 1:
            c.emit([0xF5, 0xC1, 0x79, 0xE6, 0x01], Z.sta(cy_in))
    c.emit(Z.call(TAPIOF))
    return c.build()


def analyze(path: str, n=None) -> int:
    if n is None:
        n = len(PATTERN)          # read at call time so --pattern takes effect
    raw = None
    with open(path) as f:
        for line in f:
            if line.startswith("mem.memory:0xE000:"):
                raw = line.strip().split("=", 1)[1]
    if not raw:
        print("no mem.memory:0xE000:* line in", path, file=sys.stderr)
        return 2
    data = bytes.fromhex(raw)
    cy_ion = data[0]
    got = list(data[1:1 + n])
    cy_in = data[1 + n] if len(data) > 1 + n else None
    exp = " ".join(f"{b:02X}" for b in PATTERN)
    gots = " ".join(f"{b:02X}" for b in got)
    print(f"TAPION carry: {cy_ion:02X} ({'locked' if cy_ion == 0 else 'FAILED'})")
    print(f"last TAPIN carry: {cy_in:02X}" if cy_in is not None else "last TAPIN carry: n/a")
    print(f"expected: {exp}")
    print(f"read:     {gots}")
    if got == PATTERN and cy_ion == 0:
        print("MATCH -- write->read round-trip closed")
        return 0
    print("MISMATCH")
    return 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", help="write the probe cart ROM")
    ap.add_argument("--analyze", metavar="CAP", help="analyze an omsx_run.py capture")
    ap.add_argument("--pattern", help="hex bytes expected, e.g. '00 FF 00 FF' "
                    "(must match the write probe's --pattern)")
    args = ap.parse_args()
    global PATTERN
    if args.pattern:
        PATTERN = [int(x, 16) for x in args.pattern.split()]
    if args.analyze:
        return analyze(args.analyze)
    if not args.out:
        ap.error("need --out or --analyze")
    with open(args.out, "wb") as f:
        f.write(build())
    pat = " ".join(f"{b:02X}" for b in PATTERN)
    print(f"wrote {args.out}: TAPION + TAPIN x{len(PATTERN)} [{pat}] + TAPIOF; "
          f"results at 0x{Z.RESULT:04X}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
