#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Build the merged zerobas main ROM (cbios-repack arc, WS-3 / S4).

Per decision D4, the repacked stack ships as ONE 32 KB slot-0 "main ROM" -- the
MSX-spec BIOS-low + BASIC-high layout -- rather than two disjoint IPS patches. This
splices the three source components into that combined image:

  1. the repacked C-BIOS (page 0 BIOS; its dead ROM-BASIC placeholder dropped so
     $2812-$3FFF is free, contiguous below page 1) -- the base,
  2. the relocated BASIC ($2812-$7FFF, basic/main.asm; "AB" header pinned at
     $4000, reclaimed low region $2812-$3FFF reserved $00 for now), and
  3. the zerobas-tape page-0 completions (LPTOUT vector $00A5, GTPAD/GTPDL vectors
     $00DB/$00DE, cassette vectors $00E2-$00F6, routine bodies $09EE-tape_end --
     the $00DB/$00DE vectors repoint C-BIOS's GTPAD/GTPDL debug stubs; D5 rev 2026-07-11:
     moved from $3A72 into the all-variant gap-1 fill when float F2 grew BASIC
     over the old block; see tape/tape.asm FREE_ORG).

Overlay order is BASIC then tape: BASIC's reserved low region is $00, and the tape
bodies sit below it ($09EE-tape_end, C-BIOS gap-1 fill), so order no longer
matters, but tape still lands last. The two never conflict
in the vector regions ($00A5/$00E1 are below BASIC's $2812 base).

Safety: reuses overlay_page1's ref check -- if BASIC would clobber any repacked
byte that a direct CALL/JP targets, stop. Asserts the tape body region is free
($00) in the repacked base before writing.

    python3 tools/build_mainrom.py REPACKED.rom BASIC_RELOC.rom TAPE.bin TAPE.sym OUT.rom
"""
from __future__ import annotations

import sys

from overlay_page1 import refs_into, spans


def sym_value(sym_path: str, label: str) -> int:
    """Read one label's address from a pasmo .sym file (`LABEL\tEQU\tXXXXH`)."""
    for line in open(sym_path):
        parts = line.replace(":", " ").split()
        if parts and parts[0] == label:
            return int(parts[-1].rstrip("Hh"), 16)
    raise SystemExit(f"label {label!r} not found in {sym_path}")

BASIC_BASE = 0x2812   # relocated BASIC low boundary (BASIC_ORG in basic/main.asm)
TOP = 0x8000
TAPE_BIN_BASE = 0x00A5
LPTOUT_VEC = (0x00A5, 0x00A8)      # C3 JP vector, target repointed to LPTOUT body
PAD_PDL_VECS = (0x00DB, 0x00E1)    # GTPAD ($00DB) + GTPDL ($00DE) JP vectors,
                                   # repointed off the C-BIOS debug stubs to our bodies
CASSETTE_VECS = (0x00E2, 0x00F6)   # seven cassette vector targets
TAPE_BODY_LO = 0x09EE              # routine bodies; hi = tape_end (arg); must
                                   # equal tape/tape.asm FREE_ORG (D5 rev 2026-07-11)


def build(repacked: bytes, basic: bytes, tape: bytes, tape_end: int) -> bytes:
    if len(repacked) != TOP:
        sys.exit(f"repacked C-BIOS: expected 32 KB, got {len(repacked)}")
    if len(basic) != TOP - BASIC_BASE:
        sys.exit(f"relocated BASIC: expected {TOP - BASIC_BASE} B "
                 f"(${BASIC_BASE:04X}-$7FFF), got {len(basic)}")
    hdr = 0x4000 - BASIC_BASE
    if basic[hdr:hdr + 2] != b"AB":
        sys.exit('relocated BASIC: "AB" header not pinned at $4000')

    merged = bytearray(repacked)

    # 1) splice BASIC over $2812-$7FFF, checking we clobber no referenced stub.
    overwritten = [BASIC_BASE + i for i in range(len(basic))
                   if repacked[BASIC_BASE + i] != 0
                   and repacked[BASIC_BASE + i] != basic[i]]
    unsafe = False
    if overwritten:
        print(f"note: BASIC overwrites {len(overwritten)} non-empty C-BIOS byte(s):")
        for a, b in spans(overwritten):
            refs = refs_into(repacked, a, b)
            tag = "  <-- REFERENCED" if refs else "  (unreferenced)"
            print(f"  0x{a:04X}-0x{b:04X}{tag}")
            for off, op in refs:
                print(f"      {'JP' if op == 0xC3 else 'CALL'} from 0x{off:04X}")
                unsafe = True
    else:
        print("note: BASIC occupies only empty ($00) space in the repacked base.")
    if unsafe:
        sys.exit("error: BASIC would clobber a stock routine reachable by direct "
                 "CALL/JP -- relocate it before BASIC can take this region.")
    merged[BASIC_BASE:TOP] = basic

    # 2) overlay tape. Assert the body region is free in the repacked base first.
    body = merged[TAPE_BODY_LO:tape_end]
    if any(x != 0 for x in body):
        bad = TAPE_BODY_LO + next(i for i, x in enumerate(body) if x)
        sys.exit(f"error: tape body region ${TAPE_BODY_LO:04X}-${tape_end:04X} not free "
                 f"(non-zero at ${bad:04X}) in the merged base")
    for lo, hi in (LPTOUT_VEC, PAD_PDL_VECS, CASSETTE_VECS, (TAPE_BODY_LO, tape_end)):
        merged[lo:hi] = tape[lo - TAPE_BIN_BASE:hi - TAPE_BIN_BASE]

    print(f"OK: merged main ROM -- repacked C-BIOS + BASIC(${BASIC_BASE:04X}-$7FFF) "
          f"+ tape(${TAPE_BODY_LO:04X}-${tape_end:04X})")
    return bytes(merged)


def main() -> int:
    if len(sys.argv) != 6:
        sys.exit(__doc__)
    repacked = open(sys.argv[1], "rb").read()
    basic = open(sys.argv[2], "rb").read()
    tape = open(sys.argv[3], "rb").read()
    tape_end = sym_value(sys.argv[4], "tape_end")
    out = sys.argv[5]
    merged = build(repacked, basic, tape, tape_end)
    open(out, "wb").write(merged)
    print(f"wrote {out}: {len(merged)} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
