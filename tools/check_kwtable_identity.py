#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Assert the `kwtable` SINGLE-COPY invariant (subrom wave 3, spec §2/§7 gate 1).

The keyword crunch table has exactly two code readers: `match_kw` (the tokeniser)
and `detok_kw`/`detok_kw2` (the LIST/ASCII-SAVE detokeniser). Wave 2 evicted the
tokeniser to the sub-ROM, leaving the table duplicated (resident copy for the still-
resident detokeniser + a sub copy for the tokeniser). Wave 3 evicts the detokeniser
too, so BOTH readers are now sub-side and the resident copy is DROPPED — the sub-ROM
copy is the sole source of truth (recovering wave 2's duplication and removing the
drift risk R-W2-3 entirely).

This gate enforces that end state:
  * the RELOC (repack main ROM) must have NO `kwtable` symbol — the resident copy
    is gone;
  * the SUB image must carry a structurally valid `kwtable` — the sole copy.

    python3 tools/check_kwtable_identity.py RELOC.rom RELOC.sym SUB.rom SUB.sym

The SUB image is based at $0000. The `kwtable` label gives the table start; it is
walked by its own [klen][chars][tlen][tokens] structure to its 0-length terminator,
so no length constant is hardcoded here.
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
        raise SystemExit("FAIL: no `kwtable` symbol in the sub-ROM — the sole copy is missing")
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

    # Gate 1a: the resident copy must be GONE (wave 3 dropped it).
    if "kwtable" in reloc_sym:
        print("FAIL: a resident `kwtable` still exists in the repack main ROM — wave 3 "
              "should have dropped it (both readers are sub-side now)", file=sys.stderr)
        return 1

    # Gate 1b: the sub-ROM must carry the sole, structurally valid copy.
    b = kwtable_bytes(sub, SUB_BASE, sub_sym)
    print(f"OK: kwtable single-copy — resident dropped (wave 3), sub-ROM copy is the "
          f"sole source ({len(b)} B)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
