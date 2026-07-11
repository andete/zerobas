#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Assert the two `kwtable` images are byte-identical (subrom wave 2, spec §4/§7.2).

The keyword crunch table is SHARED by two readers: `match_kw` (the tokeniser,
evicted to the sub-ROM in wave 2) and `detok_kw`/`detok_kw2` (LIST, which is
I/O-bound so it stays RESIDENT in the main ROM). A page-0 sub-ROM tenant cannot
see the main-ROM low region, so the sub-ROM carries its OWN copy of the table and
the resident copy stays put. Both are assembled from the SAME basic/kwtable.inc
under the SAME ROM_BASE (<$4000) gating, so they are byte-identical BY
CONSTRUCTION — this gate makes that a checked invariant (R-W2-3: the two copies
must never drift).

    python3 tools/check_kwtable_identity.py RELOC.rom RELOC.sym SUB.rom SUB.sym

RELOC image is based at $2812 (reclaimed low region); the SUB image at $0000.
The `kwtable` label in each sym gives the table start; the table is walked by its
own [klen][chars][tlen][tokens] structure to its 0-length terminator, so no length
constant is hardcoded here.
"""
from __future__ import annotations

import re
import sys

RELOC_BASE = 0x2812
SUB_BASE = 0x0000


def load_syms(path):
    syms = {}
    pat = re.compile(r"^(\S+)\s+EQU\s+([0-9A-Fa-f]+)H", re.IGNORECASE)
    with open(path) as fh:
        for line in fh:
            m = pat.match(line.strip())
            if m:
                syms[m.group(1)] = int(m.group(2), 16)
    return syms


def kwtable_bytes(rom, base, sym):
    """Return the keyword table bytes, walked from `kwtable` to its 0 terminator."""
    if "kwtable" not in sym:
        raise SystemExit(f"FAIL: no `kwtable` symbol in {sym!r}")
    start = sym["kwtable"] - base
    i = start
    while True:
        klen = rom[i]
        if klen == 0:            # 0-length entry = table terminator
            i += 1               # include the terminator byte
            break
        i += 1 + klen            # [klen][chars]
        tlen = rom[i]
        i += 1 + tlen            # [tlen][tokens]
    return rom[start:i]


def main() -> int:
    if len(sys.argv) != 5:
        sys.exit(__doc__)
    reloc = open(sys.argv[1], "rb").read()
    reloc_sym = load_syms(sys.argv[2])
    sub = open(sys.argv[3], "rb").read()
    sub_sym = load_syms(sys.argv[4])

    a = kwtable_bytes(reloc, RELOC_BASE, reloc_sym)
    b = kwtable_bytes(sub, SUB_BASE, sub_sym)
    if a != b:
        print(f"FAIL: kwtable copies DIFFER — resident {len(a)} B vs sub {len(b)} B",
              file=sys.stderr)
        n = min(len(a), len(b))
        for j in range(n):
            if a[j] != b[j]:
                print(f"       first diff at table offset {j}: "
                      f"resident {a[j]:#04x} vs sub {b[j]:#04x}", file=sys.stderr)
                break
        return 1
    print(f"OK: kwtable byte-identical across resident + sub-ROM copies ({len(a)} B)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
