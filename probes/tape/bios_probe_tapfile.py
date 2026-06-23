#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Phase-3 block-structure probe: a full BSAVE-style cassette file round-trip.

Writes a real MSX binary-file structure through the byte-level BIOS calls, then
reads it back -- exercising what single-block probes did not: the *short* header,
a *second* block, and TAPION re-locking mid-tape after TAPIOF.

On the audio tape a binary file is two blocks, each introduced by a leader tone
(there is no on-tape 8-byte sync sequence -- that lives only in the .cas
*container*; the leader is the boundary):

  [ long leader ][ header block: 0xD0 x10 + 6-char filename            ]
  [ short leader][ data block:  start/end/exec (3x LE word) + payload   ]

Write cart:  TAPOON(long)  + TAPOUT(header 16) + TAPOOF
             TAPOON(short) + TAPOUT(data 6+N)  + TAPOOF
Read cart:   TAPION + TAPIN x16 + TAPIOF   (header block)
             TAPION + TAPIN x(6+N) + TAPIOF (data block)

Result buffer (read cart):
  0xE000      : carry after header TAPION (00 = locked)
  0xE001..10  : 16 header bytes
  0xE011      : carry after data TAPION
  0xE012..1B  : 6+N data bytes

  python3 probes/tape/bios_probe_tapfile.py --write w.rom [--baud 2400]
  python3 probes/lib/omsx_run.py ... --cart w.rom --record file.wav ...
  python3 probes/tape/bios_probe_tapfile.py --read r.rom
  python3 probes/lib/omsx_run.py ... --cart r.rom --cassette file.wav --mem memory:0xE000:28 ...
  python3 probes/tape/bios_probe_tapfile.py --analyze cap.txt
"""
from __future__ import annotations

# --- zerobas probes: locate shared infra (probes/lib) + sibling probes ---
import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))  # sibling probes
_sys.path.insert(0, _os.path.join(
    _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "lib"))  # shared infra

import argparse, os, sys

CAS_SYNC = bytes([0x1F, 0xA6, 0xDE, 0xBA, 0xCC, 0x13, 0x7D, 0x74])
import z80probe as Z  # noqa: E402

TAPION, TAPIN, TAPIOF = 0x00E1, 0x00E4, 0x00E7
TAPOON, TAPOUT, TAPOOF = 0x00EA, 0x00ED, 0x00F0

# A faithful BSAVE binary file: header block (type id + name) then data block.
FILENAME = [ord(ch) for ch in "CBTAPE"]            # 6 chars
HEADER = [0xD0] * 10 + FILENAME                     # 16 bytes
START, END, EXEC = 0x8000, 0x8003, 0x8000
PAYLOAD = [0xC9, 0x00, 0x11, 0x22]
DATA = [START & 0xFF, START >> 8, END & 0xFF, END >> 8,
        EXEC & 0xFF, EXEC >> 8] + PAYLOAD           # 6 + 4 bytes
NH, ND = len(HEADER), len(DATA)


def build_cas() -> bytes:
    """Emit a .cas container with the same two-block content as the write cart.

    Used to test the read path at the 3744-baud speed openMSX uses when
    synthesising .cas files, without going through the BIOS write path.
    """
    return CAS_SYNC + bytes(HEADER) + CAS_SYNC + bytes(DATA)


def build_write(baud: int = 1200) -> bytes:
    c = Z.Cart()
    c.emit(Z.di())
    # Set up the standard timing tables (blank on bare C-BIOS) and select baud,
    # as a real BIOS + SCREEN ,,,baud would; our TAPOON/TAPOUT read the result.
    c.emit(Z.setup_cas_baud(baud))
    # header block -- long leader
    c.emit(Z.ld_a(0xFF), Z.call(TAPOON))
    for b in HEADER:
        c.emit(Z.ld_a(b), Z.call(TAPOUT))
    c.emit(Z.call(TAPOOF))
    # data block -- short leader
    c.emit(Z.ld_a(0x00), Z.call(TAPOON))
    for b in DATA:
        c.emit(Z.ld_a(b), Z.call(TAPOUT))
    c.emit(Z.call(TAPOOF))
    return c.build()


def build_read() -> bytes:
    c = Z.Cart()
    cy1 = c.alloc(1)
    hbuf = c.alloc(NH)
    cy2 = c.alloc(1)
    dbuf = c.alloc(ND)
    c.emit(Z.di())
    # header block
    c.emit(Z.call(TAPION))
    c.emit([0xF5, 0xC1, 0x79, 0xE6, 0x01], Z.sta(cy1))   # carry -> cy1
    for i in range(NH):
        c.emit(Z.call(TAPIN), Z.sta(hbuf + i))
    c.emit(Z.call(TAPIOF))
    # data block
    c.emit(Z.call(TAPION))
    c.emit([0xF5, 0xC1, 0x79, 0xE6, 0x01], Z.sta(cy2))   # carry -> cy2
    for i in range(ND):
        c.emit(Z.call(TAPIN), Z.sta(dbuf + i))
    c.emit(Z.call(TAPIOF))
    return c.build()


def analyze(path: str) -> int:
    raw = None
    with open(path) as f:
        for line in f:
            if line.startswith("mem.memory:0xE000:"):
                raw = line.strip().split("=", 1)[1]
    if not raw:
        print("no mem.memory:0xE000:* line in", path, file=sys.stderr)
        return 2
    d = bytes.fromhex(raw)
    cy1 = d[0]
    hdr = list(d[1:1 + NH])
    cy2 = d[1 + NH]
    dat = list(d[2 + NH:2 + NH + ND])
    hx = lambda xs: " ".join(f"{b:02X}" for b in xs)
    ok_h = (cy1 == 0 and hdr == HEADER)
    ok_d = (cy2 == 0 and dat == DATA)
    print(f"header TAPION carry: {cy1:02X}   data TAPION carry: {cy2:02X}")
    print(f"header expected: {hx(HEADER)}")
    print(f"header read:     {hx(hdr)}   {'OK' if ok_h else 'BAD'}")
    print(f"data   expected: {hx(DATA)}")
    print(f"data   read:     {hx(dat)}   {'OK' if ok_d else 'BAD'}")
    if ok_h and ok_d:
        print("MATCH -- full two-block file round-trip closed")
        return 0
    print("MISMATCH")
    return 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--write", metavar="ROM", help="emit the BIOS write cart")
    ap.add_argument("--write-cas", metavar="CAS",
                    help="emit a .cas container with the known test pattern "
                         "(same content as --write, synthesised by openMSX at 3744 baud)")
    ap.add_argument("--read", metavar="ROM", help="emit the BIOS read cart")
    ap.add_argument("--baud", type=int, choices=(1200, 2400), default=1200)
    ap.add_argument("--analyze", metavar="CAP")
    args = ap.parse_args()
    if args.analyze:
        return analyze(args.analyze)
    if args.write:
        with open(args.write, "wb") as f:
            f.write(build_write(baud=args.baud))
        print(f"wrote {args.write}: header(16) + data({ND}) file @ {args.baud} baud; "
              f"read buffer is {2 + NH + ND} bytes at 0x{Z.RESULT:04X}")
        return 0
    if args.write_cas:
        with open(args.write_cas, "wb") as f:
            f.write(build_cas())
        print(f"wrote {args.write_cas}: .cas container, "
              f"header({NH}) + data({ND}); openMSX synthesises at 3744 baud")
        return 0
    if args.read:
        with open(args.read, "wb") as f:
            f.write(build_read())
        print(f"wrote {args.read}: TAPION+TAPIN x{NH} (header), "
              f"TAPION+TAPIN x{ND} (data); results at 0x{Z.RESULT:04X}")
        return 0
    ap.error("need --write, --write-cas, --read or --analyze")


if __name__ == "__main__":
    raise SystemExit(main())
