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
assertion is superseded (spec §5b). The durable guarantees this gate enforces:

  1. the relocated image spans $2812-$7FFF exactly (22510 bytes),
  2. the "AB" cartridge header is pinned at $4000 (C-BIOS boots via the page-1
     cartridge scan; page 0 is never scanned), and
  3. the reclaimed low region $2812-$3FFF is OCCUPIED (not all $00) — i.e. the
     string engine actually landed there, the point of the re-layout.

    python3 tools/check_reloc.py build/basic-reloc.rom build/basic-reloc.sym

It also REPORTS the page-0 low-region and page-1 free space from the
__MEAS_LOW_END / __MEAS_PAGE1_END labels (subrom wave-2 measurement pre-gate,
spec §7.1). ⚠️ THIS READOUT IS WHAT EVERY SLICE IS COSTED AGAINST — it is the
project's wall measurement, not a convenience print. The symbol file is a
REQUIRED argument for exactly that reason: it used to be optional, and an
optional sym is precisely the shape in which a wall readout silently stops
printing while the gate still exits 0 ([[gate-can-be-green-while-measuring-nothing]]).

REMOVED 2026-07-29 (RETIRE THE LEAN 16 KB CART, S2 --
docs/spec-lean-retire-s2-switch.md): a 4th check pinned the lean 16 KB basic.rom
to a frozen LEAN_SHA256 baseline, proving the co-maintained lean build never
drifted. zerobas no longer builds or ships lean; a build that would be CHERRY-
PICKED on demand from the finished tree needs no anti-drift proof, because it is
cut from a tree that is already gated. Checks 1-3 and the readout above are
untouched by that removal -- check 4 was the ONLY reader of the basic.rom
argument, which is why this became a deletion rather than a redesign.
"""
from __future__ import annotations

import re
import sys


def load_syms(path):
    syms = {}
    pat = re.compile(r"^(\S+)\s+EQU\s+([0-9A-Fa-f]+)H", re.IGNORECASE)
    with open(path) as fh:
        for line in fh:
            m = pat.match(line.strip())
            if m:
                syms[m.group(1)] = int(m.group(2), 16)
    return syms

LOW = 0x2812
HDR = 0x4000
TOP = 0x8000
SIZE = TOP - LOW  # 22510


def main() -> int:
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    reloc = open(sys.argv[1], "rb").read()
    off = HDR - LOW  # header offset within the relocated image
    errs = []
    if len(reloc) != SIZE:
        errs.append(f"reloc size {len(reloc)} != {SIZE} ($2812-$7FFF)")
    if reloc[off:off + 2] != b"AB":
        errs.append(f'"AB" header not at $4000 (offset {off:#x}): {reloc[off:off+2]!r}')
    if set(reloc[:off]) in ({0}, set()):
        errs.append("reclaimed low region $2812-$3FFF is empty ($00) — the string "
                    "engine did not land there (expected occupied per spec §5b)")
    if errs:
        for e in errs:
            print("FAIL:", e, file=sys.stderr)
        return 1
    used = max((i for i, b in enumerate(reloc[:off]) if b != 0), default=-1) + 1
    print(f"OK: relocated image {len(reloc)} B, header @ $4000, low region "
          f"$2812-$3FFF holds {used} B of string engine")

    # The wall readout. Both labels are REQUIRED to be present: a missing one used
    # to print nothing and still exit 0, which is a wall measurement that silently
    # became a 0-denominator. Every slice is costed against these two numbers.
    syms = load_syms(sys.argv[2])
    missing = [n for n in ("__MEAS_LOW_END", "__MEAS_PAGE1_END") if n not in syms]
    if missing:
        print(f"FAIL: {sys.argv[2]} defines no {', '.join(missing)} — the WALL "
              f"READOUT every slice is costed against would print nothing",
              file=sys.stderr)
        return 1
    low_end = syms["__MEAS_LOW_END"]
    p1_end = syms["__MEAS_PAGE1_END"]
    print(f"    measure: page-0 low region free = {HDR - low_end} B "
          f"($2812-$3FFF, __MEAS_LOW_END @ {low_end:#06x})")
    print(f"    measure: page-1 free            = {TOP - p1_end} B "
          f"($4000-$7FFF, __MEAS_PAGE1_END @ {p1_end:#06x}) "
          f"<- subrom wave-2 tokeniser-eviction relief")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
