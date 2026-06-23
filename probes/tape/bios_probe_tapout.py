#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Probe: TAPOUT ($00ED) — write one byte to cassette tape.

Writes byte $42 ('B') as FSK to the CAS-out pin by toggling PPI port C bit 7
in a software loop.  Preceded by TAPOON to start the motor.

Result buffer (3 bytes):
  [0] PPI port C before TAPOON
  [1] carry flag after TAPOUT (0=success, 1=error)
  [2] PPI port C after TAPOUT

    python3 probes/tape/bios_probe_tapout.py --out tapout.rom
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
PPI_C = 0xAA


def build() -> bytes:
    c = Z.Cart()
    before = c.alloc(1)
    cy_flag = c.alloc(1)
    after = c.alloc(1)
    c.emit(Z.di())
    c.emit(Z.in_a(PPI_C), Z.sta(before))
    c.emit(Z.call(TAPOON))
    c.emit(Z.ld_a(0x42))
    c.emit(Z.call(TAPOUT))
    # Store carry via: PUSH AF; POP BC; LD A,C (=F); AND 1; STA cy_flag
    c.emit([0xF5, 0xC1, 0x79, 0xE6, 0x01])   # PUSH AF; POP BC; LD A,C; AND 1
    c.emit(Z.sta(cy_flag))
    c.emit(Z.in_a(PPI_C), Z.sta(after))
    return c.build()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    with open(args.out, "wb") as f:
        f.write(build())
    print(f"wrote {args.out}: TAPOUT probe, 3 result bytes at 0x{Z.RESULT:04X}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
