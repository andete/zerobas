#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Verify a raw ROM image is exactly <size> bytes (or, with --pad, fill it to that
size with $00).

    pad_rom.py <rom> <size> [--pad]

⚠️ PADDING IS OPT-IN, AND NO CALLER IN THE TREE OPTS IN. Every live call site
assembles a source that already spans its whole image, so the correct amount of
padding is ZERO and any padding at all is a defect being covered up:

    build/sub.rom            32768 / 32768     (Makefile, $(SUB_ROM))
    build/disk.rom           16384 / 16384     (Makefile, $(DISK_ROM))
    build/sub-unguarded.rom  32768 / 32768     (Makefile, graphics-floor-teeth)

measured D-ROMJUDGE 2026-08-05, docs/spec-rom-gate-judge.md §2.3. So `--pad` has
zero slack to absorb; it exists to keep the DECISION explicit for a future caller
that genuinely needs it, not to serve anyone today.

🔴 WHY THE DEFAULT FLIPPED. This script used to pad silently, and it reported the
size it WROTE rather than the size it READ -- so a short assembler output came out
the far end as a legitimate-looking image and printed a line indistinguishable
from a healthy build. Two ways in, both measured:

  * a NEGATIVE `ds` count (`ds <fixed addr> - $`, i.e. a region that overran its
    own ceiling) -- pasmo answers it with a *warning* and EXIT 0, writing NOTHING.
    Three source shapes tested, all produce 0 bytes, so this route always lands on
    the empty-input refusal below (D-P0BASE, spec-rom-region-p0base.md §6.3).
    The tree has 74 such `ds <fixed> - $` sites, 68 of them under disk/.
  * a SHORT assembly -- one edit to the final pad line of sub/sub.asm and pasmo
    emits 30444 bytes instead of 32768. The old code padded the missing 2324 with
    $00, printed "32768 bytes", and `make basic-reloc` passed at rc 0 with every
    gate OK, as did `make subrom-acceptance`. THAT is the reachable route, and it
    is the one the empty-input refusal does not cover.

The chain downstream cannot catch this for us: exactly ONE gate in `make
basic-reloc` reads sub.rom's content at all (check_kwtable_identity, 1041 of
32768 bytes), and a truncation below the trailing pad length is invisible to the
emulator corpus by construction. The length question has to be answered HERE,
where the assembler's own output is still in hand.
"""
import sys


def main() -> int:
    args = [a for a in sys.argv[1:] if a != "--pad"]
    allow_pad = "--pad" in sys.argv[1:]
    if len(args) != 2:
        sys.exit(__doc__)
    path, size = args[0], int(args[1])
    with open(path, "rb") as f:
        data = f.read()

    if not data:
        # A ZERO-BYTE INPUT IS NOT SOMETHING TO PAD, IT IS A FAILED ASSEMBLY.
        print(f"{path}: EMPTY -- the assembler wrote no bytes (check for a "
              f"negative `ds` count / a region that overran a fixed address); "
              f"refusing to pad it to {size}", file=sys.stderr)
        return 1
    if len(data) > size:
        print(f"{path}: {len(data)} bytes exceeds target {size}", file=sys.stderr)
        return 1
    if len(data) < size:
        short = size - len(data)
        if not allow_pad:
            print(f"{path}: SHORT -- the assembler wrote {len(data)} bytes, "
                  f"{short} short of {size}. The source is supposed to span the "
                  f"whole image, so this is a truncated build, not something to "
                  f"pad: check for a removed/shortened final `ds <top> - $` pad, "
                  f"a dropped include, or a region that overran a fixed address. "
                  f"Padding it would ship {short} invented $00 bytes that nothing "
                  f"downstream can see. Pass --pad only if this caller really is "
                  f"meant to be padded.", file=sys.stderr)
            return 1
        data += b"\x00" * short
        with open(path, "wb") as f:
            f.write(data)
        print(f"{path}: {size} bytes (--pad: {short} bytes of $00 INVENTED here, "
              f"only {len(data) - short} came from the assembler)")
        return 0

    print(f"{path}: {size} bytes (exact -- the assembler wrote the whole image)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
