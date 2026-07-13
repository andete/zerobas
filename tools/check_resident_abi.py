#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""STRONG consistency gate for the sub-ROM resident-ABI import (subrom-mathpack
arc, spec §4/§8 sign-off).

`sub/basic-resident-abi.inc` is a GENERATED file (tools/gen_resident_abi.py):
it bakes the current build/basic-reloc.sym addresses of fp_sqrt's 9 resident
callees into sub.rom at assemble time. If the page-0 low region ever shifts
(any basic/*.asm edit in the reclaimed low region) WITHOUT sub.rom being
rebuilt from a freshly regenerated .inc, sub.rom would silently keep calling
the OLD (now wrong) addresses — the same class of stale-artifact trap the
$(MAIN_ROM) Makefile bug was (see [[ips-rebuild-after-basic-change]]).

The Makefile's build-order dependency (RELOC_SYM -> basic-resident-abi.inc ->
SUB_ROM) should make this impossible in a clean build, but this gate is the
STANDING assert that catches it anyway (a stale checked-in .inc some other
tool forgot to regenerate, a partial/interrupted build, a hand-edit, etc.):
it re-runs the SAME generator against the CURRENT basic-reloc.sym into memory
and diffs the result against the committed/on-disk .inc byte-for-byte. Any
mismatch means the shipped sub.rom was assembled from a STALE resident-ABI
surface — fail loudly rather than let a silently-wrong tenant ship.

    python3 tools/check_resident_abi.py build/basic-reloc.sym sub/basic-resident-abi.inc
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gen_resident_abi  # noqa: E402


def main() -> int:
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    sym_path, inc_path = sys.argv[1], sys.argv[2]

    fresh = gen_resident_abi.generate(sym_path, out_path=None)

    try:
        on_disk = Path(inc_path).read_text()
    except FileNotFoundError:
        print(f"FAIL: {inc_path} does not exist — run `make sub` to generate it",
              file=sys.stderr)
        return 1

    if fresh != on_disk:
        print(f"FAIL: {inc_path} is STALE relative to {sym_path} — a fresh "
              "regen (tools/gen_resident_abi.py) differs from the on-disk "
              "file. sub.rom may have been assembled from OLD resident "
              "addresses (a page-0 low-region shift without a full "
              "`make sub` rebuild). Re-run `make sub` (or the abi.inc rule) "
              "and rebuild.", file=sys.stderr)
        return 1

    n = fresh.count("equ")
    print(f"OK: {inc_path} matches a fresh regen from {sym_path} "
          f"({n} resident-ABI addresses, sub.rom is not stale)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
