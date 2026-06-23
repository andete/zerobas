#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Probe: STMOTR ($00F3) — cassette motor control.

Reads PPI port C baseline, then calls STMOTR(1) to start the motor.
Reads PPI port C again to check bit 4 (motor relay).

Result buffer (2 bytes):
  [0] PPI port C before STMOTR
  [1] PPI port C after STMOTR(1)

    python3 probes/tape/bios_probe_stmotr.py --out stmotr.rom
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
PPI_C = 0xAA


def build() -> bytes:
    c = Z.Cart()
    before = c.alloc(1)
    after = c.alloc(1)
    c.emit(Z.di())
    c.emit(Z.in_a(PPI_C), Z.sta(before))
    c.emit(Z.ld_a(1), Z.call(STMOTR))
    c.emit(Z.in_a(PPI_C), Z.sta(after))
    return c.build()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    with open(args.out, "wb") as f:
        f.write(build())
    print(f"wrote {args.out}: STMOTR probe, 2 result bytes at 0x{Z.RESULT:04X}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
