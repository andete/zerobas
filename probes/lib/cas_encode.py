#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Encode a logical .cas file containing a BSAVE-format binary block.

This is clean-room: every constant is traced to an allowed source (MSX2
Technical Handbook cassette chapter / MSX Assembly Page), never a disassembly.
See the clean-room firewall (CONTRIBUTING.md).

Provenance of constants
-----------------------
- CAS_SYNC (8 bytes): MSX2 Technical Handbook, chapter on cassette I/O.
  The header sync pattern that precedes every logical block in a .cas file.
- BINARY_ID 0xD0 (x10): MSX2 Technical Handbook — file-type identifier byte
  for binary (BSAVE) files. Ten copies form the file-type block.
- Address header layout (start LE, end LE, exec LE): MSX2 Technical Handbook,
  BSAVE file format description.
"""
from __future__ import annotations


# Source: MSX2 Technical Handbook, cassette I/O chapter.
CAS_SYNC = bytes([0x1F, 0xA6, 0xDE, 0xBA, 0xCC, 0x13, 0x7D, 0x74])

# Source: MSX2 Technical Handbook — cassette file-type identifiers (the 10-byte
# file-type block before the filename). Binary (BSAVE) = 0xD0; tokenised BASIC
# (CSAVE / CLOAD) = 0xD3; ASCII (SAVE/LOAD) = 0xEA.
BINARY_ID = 0xD0
BASIC_ID = 0xD3


def _le16(n: int) -> bytes:
    return (n & 0xFFFF).to_bytes(2, "little")


def build_cas(name: str, load_addr: int, exec_addr: int,
              data: bytes) -> bytes:
    """Build a logical .cas image for a BSAVE-format binary.

    Parameters
    ----------
    name : str
        Filename (up to 6 chars, space-padded).
    load_addr : int
        Start address where the binary is loaded into RAM.
    exec_addr : int
        Execution address jumped to by BLOAD's ,R option.
    data : bytes
        Raw binary payload (loaded at load_addr..load_addr+len(data)-1).

    Returns
    -------
    bytes
        Complete .cas file content.
    """
    padded = name[:6].ljust(6).encode("ascii")
    end_addr = load_addr + len(data) - 1

    buf = bytearray()
    # Header block: sync + 10x BINARY_ID + 6-char filename
    buf += CAS_SYNC
    buf += bytes([BINARY_ID] * 10)
    buf += padded
    # Data block: sync + start/end/exec addresses (LE) + payload
    buf += CAS_SYNC
    buf += _le16(load_addr)
    buf += _le16(end_addr)
    buf += _le16(exec_addr)
    buf += data
    return bytes(buf)


def build_cas_basic(name: str, program: bytes) -> bytes:
    """Build a logical .cas image for a tokenised BASIC program.

    Parameters
    ----------
    name : str
        Filename (up to 6 chars, space-padded).
    program : bytes
        The tokenised program-area image: a chain of
        [link:2 LE][lineno:2 LE][tokens...][00] lines ending in a $0000 link
        word (the in-memory line-link layout). The caller is responsible for the
        terminating $0000 link.

    Returns
    -------
    bytes
        Complete .cas file content (header block + program data block).

    Source: MSX2 Technical Handbook, cassette file format. Like a BSAVE binary,
    a tokenised BASIC file is TWO logical .cas blocks (each preceded by the 8-byte
    sync/leader marker openMSX uses for block boundaries): a header block ($D3 x10
    + 6-char name) and a data block (the program-area image). The data block omits
    the binary's 6-byte address header — it is just the program image: a chain of
    [link:2 LE][lineno:2 LE][tokens...][00] lines ending in a $0000 link word.
    A run of trailing $00 padding follows the end-link so the loader can frame the
    final byte (the device half blocks on silence once a block's data runs out).
    """
    padded = name[:6].ljust(6).encode("ascii")
    buf = bytearray()
    # Header block: sync + 10x BASIC_ID + 6-char filename
    buf += CAS_SYNC
    buf += bytes([BASIC_ID] * 10)
    buf += padded
    # Data block: sync + the tokenised program image + trailing $00 padding
    buf += CAS_SYNC
    buf += program
    buf += bytes([0x00] * 16)
    return bytes(buf)


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--name", default="TEST", help="filename (max 6 chars, default TEST)")
    ap.add_argument("--load", type=lambda s: int(s, 0), required=True,
                    help="load address (hex ok)")
    ap.add_argument("--exec", type=lambda s: int(s, 0), dest="exec_addr",
                    help="exec address (default = load address)")
    ap.add_argument("--data", required=True, help="path to raw binary payload")
    ap.add_argument("--out", required=True, help="output .cas path")
    args = ap.parse_args()

    with open(args.data, "rb") as f:
        payload = f.read()
    cas = build_cas(args.name, args.load,
                    args.exec_addr if args.exec_addr is not None else args.load,
                    payload)
    with open(args.out, "wb") as f:
        f.write(cas)
    end = args.load + len(payload) - 1
    print(f"wrote {args.out}: .cas BSAVE, name={args.name!r}, "
          f"load=0x{args.load:04X}, end=0x{end:04X}, "
          f"exec=0x{(args.exec_addr or args.load):04X}, {len(payload)} bytes payload")
