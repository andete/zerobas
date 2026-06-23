#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Probe: TAPOOF ($00F0) — turn off cassette tape output.

Calls TAPOOF (tape-output close) without a prior TAPOON.  Should simply stop
the motor/tone and return — or return immediately if already off.

Result buffer (2 bytes):
  [0] PPI port C before TAPOOF
  [1] PPI port C after TAPOOF

    python3 probes/tape/bios_probe_tapoof.py --out tapoof.rom
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

TAPOOF = 0x00F0
PPI_C = 0xAA


def build() -> bytes:
    c = Z.Cart()
    before = c.alloc(1)
    after = c.alloc(1)
    c.emit(Z.di())
    c.emit(Z.in_a(PPI_C), Z.sta(before))
    c.emit(Z.call(TAPOOF))
    c.emit(Z.in_a(PPI_C), Z.sta(after))
    return c.build()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    with open(args.out, "wb") as f:
        f.write(build())
    print(f"wrote {args.out}: TAPOOF probe, 2 result bytes at 0x{Z.RESULT:04X}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
