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

import sys


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


def build_cas_basic_nopad(name: str, program: bytes) -> bytes:
    """A tokenised BASIC .cas file whose data block ends EXACTLY at the
    program's $0000 end-link, with NO trailing in-block padding.

    🔴 USE THIS FOR ANY MULTI-FILE TAPE. `build_cas_basic` appends 16 `$00`
    bytes so a SINGLE-file image can be framed (the device half blocks on
    silence once a block's data runs out). On a tape holding more than one file
    those unread pad bytes leave a SKIPPED file mid-block, so the next `TAPION`
    cannot relock on the following header -- `cload.asm`'s `cas_skip_data`
    states exactly that assumption in its own body, naming this encoder as the
    hazard.
    🔬 IT COST A FALSE ACCUSATION ON 2026-09-23 (D-CLOADSKIP, withdrawn).
    `basic_probe_kwsweep.py` built a two-file tape with the padded builder, so
    `CLOAD"ZR"` read `Skip :ZQ|load error` where the reference read
    `Skip :ZQ|Found:ZR`. That was filed as a TIER 1 ROM defect and refuted the
    same night -- 🔴 AND THE REFUTATION WAS ITSELF WRONG (D-CASRELOCK,
    2026-09-28). "Real CSAVE tapes have no such pad" was sourced from OUR OWN
    save.asm, never from a reference. Decoded off the recording, CSAVE writes
    the end-link and then SEVEN $00 on the VG-8020, the CF-3300 and zerobas alike
    (scratchpad/csavetail_probe.out) -- so NEITHER builder is faithful: this one
    is 7 short, `build_cas_basic` 9 long. On the faithful tape zerobas's
    `CLOAD"ZR"` DID fail where both references load (TAPION locked inside the
    seven bytes; fixed in tape/tape.asm). Both references HANG loading a file
    built by THIS function (they never return to `Ok`), so it is only a shape
    for a file that is SKIPPED, and even then not a real one.
    👉 USE `build_cas_basic_csave` FOR A TAPE A MACHINE COULD HAVE WRITTEN.
    ⚠️ The caller still owns the terminating $0000 link, exactly as for
    `build_cas_basic`."""
    return (CAS_SYNC + bytes([BASIC_ID] * 10)
            + name[:6].ljust(6).encode("ascii") + CAS_SYNC + program)


# What CSAVE writes after the program's $0000 end-link: SEVEN $00, identical on
# the VG-8020, the CF-3300 and zerobas (scratchpad/csavetail_probe.out, decoded
# off each machine's own recording -- outputs only).
CSAVE_TAIL = 7


def build_cas_basic_csave(name: str, program: bytes) -> bytes:
    """A tokenised BASIC .cas file laid out EXACTLY as CSAVE writes it: header,
    then the program image, its $0000 end-link, and CSAVE_TAIL $00 bytes.

    The one builder of the three that a real machine could have produced, so the
    one to use for ANY tape a row reads as a real tape -- single-file or multi.
    D-CASRELOCK (2026-09-28): on a two-file tape of this shape both references
    read `Skip :ZQ` / `Found:ZR` / `Ok` and zerobas read `load error`; neither of
    the other builders could have shown it.
    ⚠️ The caller still owns the terminating $0000 link."""
    return build_cas_basic_nopad(name, program) + bytes(CSAVE_TAIL)


def selftest() -> int:
    """🔴 THE PADDED/UNPADDED DISTINCTION, PINNED — it is the one that cost a
    withdrawn TIER 1 filing, so it is asserted rather than described."""
    fails = 0

    def arm(label, cond):
        nonlocal fails
        if not cond:
            print(f"  cas_encode: FAIL {label}")
            fails += 1

    prog = bytes([0x00, 0x00])                      # a bare $0000 end-link
    pad = build_cas_basic("ZQ", prog)
    nop = build_cas_basic_nopad("ZQ", prog)
    arm("the unpadded file ENDS at the program's last byte", nop.endswith(prog))
    arm("the padded file appends exactly 16 zero bytes",
        pad == nop + bytes(16))
    # NEGATIVE: they must not be the same object or the same bytes -- without
    # this, both builders could be aliased and every arm above would pass.
    arm("NEGATIVE: padded and unpadded DIFFER", pad != nop)
    arm("NEGATIVE: the unpadded file carries no trailing zero pad",
        not nop.endswith(bytes(16)))
    # The header half must be identical: only the tail may differ, or a caller
    # switching builders would silently change the file NAME as well.
    arm("only the TAIL differs -- the header block is byte-identical",
        pad[:len(nop)] == nop)
    arm("the name is space-padded to six", b"ZQ    " in nop)
    # A two-file tape built the faithful way has its second header immediately
    # after the first file's last byte, which is the property the skip needs.
    two = nop + build_cas_basic_nopad("ZR", prog)
    arm("a two-file tape puts the next SYNC straight after the end-link",
        two[len(nop):len(nop) + len(CAS_SYNC)] == CAS_SYNC)
    print("  cas_encode: PASS" if not fails else f"  cas_encode: {fails} FAILURE(S)")
    return 1 if fails else 0


if __name__ == "__main__":
    import argparse

    if "--selftest" in sys.argv:
        raise SystemExit(selftest())

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
