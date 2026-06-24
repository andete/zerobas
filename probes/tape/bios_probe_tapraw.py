#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Diagnostic: dump raw CAS-in half-period counts.

Measures successive half-periods of the cassette read signal (PSG R14 bit 7) the
same way the BIOS read loop does -- counting tight-loop iterations between edges
-- and stores each count as a byte.  This reveals the real signal structure
(short leader halves, then the long start-bit halves, then the per-byte data
pattern) and the actual short/long counts, so the TAPION threshold and TAPIN
alignment can be calibrated.  Pure black-box observation.

  0xE000..00FF : 256 successive half-period iteration counts (after spin-up)

  python3 probes/tape/bios_probe_tapraw.py --out tapraw.rom
  python3 probes/lib/omsx_run.py --machine C-BIOS_MSX1_EU_TAPE --cart tapraw.rom \
      --cassette ours.wav --bp 0x7FF0 --mem memory:0xE000:256 --out cap.txt
  python3 probes/tape/bios_probe_tapraw.py --analyze cap.txt
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

STMOTR = 0x00F3
PSG_REGS = 0xA0
PSG_STAT = 0xA2
NSAMP = 256


def build() -> bytes:
    c = Z.Cart()
    c.emit(Z.di())
    c.emit(Z.ld_a(1), Z.call(STMOTR))            # motor on
    c.emit(Z.ld_a(14), Z.out_a(PSG_REGS))        # latch PSG R14
    c.emit(Z.in_a(PSG_STAT), [0xE6, 0x80, 0x57])  # IN A,(A2); AND 80; LD D,A
    # skip 16 edges of spin-up transient
    c.emit(Z.ld_c(16))
    c.emit(Z.loop_c(Z.ld_b(1) + Z.wait_edge(PSG_STAT)))
    # measure NSAMP half-periods into 0xE000..
    c.emit(Z.ld_hl(0xE000))
    c.emit(Z.ld_c(NSAMP & 0xFF))                  # 0 -> 256
    body = Z.ld_b(1) + Z.wait_edge(PSG_STAT) + [0x70, 0x23]  # ...; LD (HL),B; INC HL
    c.emit(Z.loop_c(body))
    return c.build()


def analyze(path: str) -> int:
    raw = None
    with open(path) as f:
        for line in f:
            if line.startswith("mem.memory:0xE000:"):
                raw = line.strip().split("=", 1)[1]
    if not raw:
        print("no mem.memory:0xE000:* line", file=sys.stderr)
        return 2
    data = list(bytes.fromhex(raw))
    print("raw half-period counts (after spin-up):")
    for i in range(0, len(data), 16):
        print(" ".join(f"{b:3d}" for b in data[i:i + 16]))
    lo = min(data); hi = max(data)
    shorts = [b for b in data if b < (lo + hi) / 2]
    longs = [b for b in data if b >= (lo + hi) / 2]
    print(f"\nmin={lo} max={hi}  "
          f"short~{sum(shorts)//max(1,len(shorts))} (n={len(shorts)})  "
          f"long~{sum(longs)//max(1,len(longs))} (n={len(longs)})")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out")
    ap.add_argument("--analyze", metavar="CAP")
    args = ap.parse_args()
    if args.analyze:
        return analyze(args.analyze)
    if not args.out:
        ap.error("need --out or --analyze")
    with open(args.out, "wb") as f:
        f.write(build())
    print(f"wrote {args.out}: 256 raw half-period counts at 0x{Z.RESULT:04X}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
