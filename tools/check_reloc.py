#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Verify the relocated BASIC image (cbios-repack arc -> string-engine arc S3).

The relocated variant (basic/main-reloc.asm, ROM_BASE=$2812) spans $2812-$7FFF and
now CARRIES FEATURES the lean build cannot fit: the string engine and its keyword
table live in the reclaimed low region $2812-$3FFF (string-engine arc, spec §5b).

The original WS-2/S3 gate asserted the reloc page-1 body was byte-identical to the
shipping basic.rom — a pure-RELOCATION property that only held while the low region
was empty $00 pad. Once the string engine grows into the low region and widens
STRMAX (repack build), the reloc page-1 body legitimately DIFFERS from lean, so that
assertion is superseded (spec §5b). The durable guarantees this gate now enforces:

  1. the relocated image spans $2812-$7FFF exactly (22510 bytes),
  2. the "AB" cartridge header is pinned at $4000 (C-BIOS boots via the page-1
     cartridge scan; page 0 is never scanned),
  3. the reclaimed low region $2812-$3FFF is OCCUPIED (not all $00) — i.e. the
     string engine actually landed there, the point of the re-layout, and
  4. the lean shipping basic.rom is BYTE-IDENTICAL to its frozen baseline (the whole
     string engine is gated behind IF ROM_BASE < $4000, so the lean 16 KB build must
     not change by construction; this pins that as a hard regression gate).

    python3 tools/check_reloc.py build/basic-reloc.rom build/basic.rom
"""
from __future__ import annotations

import hashlib
import sys

LOW = 0x2812
HDR = 0x4000
TOP = 0x8000
SIZE = TOP - LOW  # 22510

# Frozen baseline of the lean 16 KB basic.rom (default ROM_BASE=$4000). The string
# engine is entirely gated to the repack build, so this must never change unless a
# lean-affecting change is made DELIBERATELY (then update this hash in the same commit).
LEAN_SHA256 = "e21f61fe9ecb855ce69a29831a5990070c215613479310da368c350bd4228005"


def main() -> int:
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    reloc = open(sys.argv[1], "rb").read()
    ship = open(sys.argv[2], "rb").read()
    off = HDR - LOW  # header offset within the relocated image
    errs = []
    if len(reloc) != SIZE:
        errs.append(f"reloc size {len(reloc)} != {SIZE} ($2812-$7FFF)")
    if reloc[off:off + 2] != b"AB":
        errs.append(f'"AB" header not at $4000 (offset {off:#x}): {reloc[off:off+2]!r}')
    if set(reloc[:off]) in ({0}, set()):
        errs.append("reclaimed low region $2812-$3FFF is empty ($00) — the string "
                    "engine did not land there (expected occupied per spec §5b)")
    if len(ship) != HDR:
        errs.append(f"shipping basic.rom size {len(ship)} != 16384")
    else:
        got = hashlib.sha256(ship).hexdigest()
        if got != LEAN_SHA256:
            errs.append("lean basic.rom NOT byte-identical to baseline\n"
                        f"       expected {LEAN_SHA256}\n"
                        f"       got      {got}\n"
                        "       (the string engine must be gated to the repack build; "
                        "if a lean change was intended, update LEAN_SHA256)")
    if errs:
        for e in errs:
            print("FAIL:", e, file=sys.stderr)
        return 1
    used = max((i for i, b in enumerate(reloc[:off]) if b != 0), default=-1) + 1
    print(f"OK: relocated image {len(reloc)} B, header @ $4000, low region "
          f"$2812-$3FFF holds {used} B of string engine, lean basic.rom byte-identical")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
