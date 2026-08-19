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

    python3 tools/check_kwtable_identity.py RELOC.rom RELOC.sym SUB.rom SUB.sym

Four gates. The SUB image is based at $0000; the table is walked by its own
[klen][chars][tlen][tokens] structure to its 0-length terminator.

  1a  (RELOC.sym)  no `kwtable` symbol — the resident copy is gone.
  1a' (RELOC.rom)  and it is gone in BYTES, not merely in symbols: the table's
                   bytes occur ZERO times in the relocated image.
  1b  (SUB.rom)    the sole copy is structurally valid AND matches the pinned
                   baseline EXACTLY, in both length and content.
  1c  (SUB.rom)    the table occurs EXACTLY ONCE in the sub image — the gate's own
                   name, finally measured. It doubles as the in-run positive
                   control for the byte search 1a' depends on: if the search stops
                   finding things, this goes red in the same run.

🔴 THIS IS THE ONLY GATE IN `make basic-reloc` THAT READS sub.rom's CONTENT AT
ALL, and until D-ROMJUDGE (2026-08-05, docs/spec-rom-gate-judge.md) it printed its
own denominator without judging it. Measured, seven corrupted images through the
whole chain — FIVE passed at rc 0:

    all-$00 sub.rom           reported "1 B"     -> OK, rc 0   (the D-P0BASE incident)
    table terminated early    reported "9 B"     -> OK, rc 0
    ONE byte flipped in it    reported "6140 B"  -> OK, rc 0
    truncated to 50% / 99%    reported "1041 B"  -> OK, rc 0
    all-$FF sub.rom           IndexError traceback, not a judgement

⚠️ WHICH IS WHY THE MATCH IS EXACT AND NOT A FLOOR. A lower bound would catch the
1 B and 9 B rows and PASS the 6140 B one — a single flipped byte moves the size
UP. Same shape as the one-sided `delta >= 1` that passed a runaway in
basic_probe_subrom_inttest.py.

⚠️ AND THE TRUNCATION ROWS ARE WHY THIS GATE CANNOT BE THE WHOLE ANSWER: the table
is 1041 of 32768 bytes (3.2%) and sits at $2CD2, so a truncation at 50% or 99%
leaves it perfectly intact. The length of the image is answered in
tools/pad_rom.py, where the assembler's own output is still in hand.

THE PINNED BASELINE IS A CONTROL THAT MUST KEEP MATCHING, not a suppression —
same standing as tools/deadcode-allow.txt and check_reloc.py's SIZE. Adding a
keyword to basic/kwtable.inc moves it; the failure text prints the new values
ready to paste, and that bump is the point: it makes the crunch table's content a
REVIEWED change instead of a silent one.
"""
from __future__ import annotations

import hashlib
import re
import sys

RELOC_BASE = 0x2812
SUB_BASE = 0x0000

# Measured from `rm -rf build && make basic-reloc`. Bump BOTH when
# basic/kwtable.inc changes; the FAIL text below prints the replacements.
#
# D-DEFTYPETOK (2026-08-19): 1064 -> 1091 B, and the DELTA IS THE REVIEW. +27 is
# exactly the THREE rows added -- DEFSTR/DEFSNG/DEFDBL are 1(klen)+6(chars)+
# 1(tlen)+1(tok) = 9 B each -- against an otherwise-unchanged table, so the
# arithmetic itself says the table gained nothing else. These three had NO row
# at all before: they fell through to the plain "DEF" row and had their mnemonic
# copied as ASCII, which is the defect D-DEFTYPETOK closes.
# D-DEFINTTOK (2026-08-18): 1067 -> 1064 B, and the DELTA IS THE REVIEW. -3 is
# exactly the "DEFINT" row shrinking from the old 4-token-byte shape
# (`4,DEF_TOKEN,"INT"` = 1+3 = 4 token bytes) to a real single-byte token
# (`1,DEFINT_TOKEN` = 1 token byte): row size 1(klen)+6(chars)+1(tlen)+4(toks)
# =12 B -> 1+6+1+1=9 B, a -3 B row against an otherwise-unchanged table -- so
# the arithmetic itself says the table lost nothing else.
# D-LFILES (2026-08-06): 1058 -> 1067 B, and the DELTA IS THE REVIEW. +9 is
# exactly the ONE entry added -- LFILES is 1+6+1+1 = 9 B ([klen][chars][tlen]
# [tokens]) -- so the arithmetic itself says the table gained nothing else. A bump
# that matched no expected delta would be the finding.
# Previous pins: 1058 B / 334b29c4… at b5f4135 (D-LPTVERB, +17 = LPRINT 9 + LPOS
# 8); 1041 B / 8f120510… at 9bfcfb9 (2026-08-05), kwtable @ $2CD2.
KWTABLE_SIZE = 1091
KWTABLE_SHA = "ee1a142c2350b38112603318d20251d544552adca02723e5d2159e0670846c5d"


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
    """The keyword table bytes, walked from `kwtable` to its 0 terminator.

    BOUNDED: an image whose bytes do not form a valid table walks off the end, and
    that must be a judgement with a message rather than an IndexError traceback
    (measured on an all-$FF sub.rom, which is exactly what an unassembled or
    unmapped image looks like)."""
    if "kwtable" not in sym:
        raise SystemExit("FAIL: no `kwtable` symbol in the sub-ROM — the sole copy is missing")
    start = sym["kwtable"] - base
    if not 0 <= start < len(rom):
        raise SystemExit(f"FAIL: `kwtable` resolves to offset {start:#x}, outside "
                         f"the {len(rom)}-byte sub image")
    i = start

    def at(j):
        if j >= len(rom):
            raise SystemExit(
                f"FAIL: the `kwtable` walk ran off the end of the {len(rom)}-byte "
                f"sub image (started at {start:#x}). The bytes at `kwtable` are not "
                f"a [klen][chars][tlen][tokens] table — the image is corrupt, "
                f"truncated, or was never assembled.")
        return rom[j]

    while True:
        klen = at(i)
        if klen == 0:            # 0-length entry = table terminator
            i += 1               # include the terminator byte
            break
        i += 1 + klen            # [klen][chars]
        tlen = at(i)
        i += 1 + tlen            # [tlen][tokens]
        if i - start > len(rom):
            raise SystemExit("FAIL: the `kwtable` walk exceeded the sub image size")
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

    # Gate 1b: the sub-ROM must carry the sole, structurally valid copy, and it
    # must be the table this gate was pinned against.
    b = kwtable_bytes(sub, SUB_BASE, sub_sym)
    got_sha = hashlib.sha256(b).hexdigest()
    if len(b) != KWTABLE_SIZE or got_sha != KWTABLE_SHA:
        print(f"FAIL: the sub-ROM `kwtable` is not the pinned table.\n"
              f"       pinned : {KWTABLE_SIZE} B  sha256 {KWTABLE_SHA}\n"
              f"       walked : {len(b)} B  sha256 {got_sha}\n"
              f"       If you edited basic/kwtable.inc, this is expected — re-read the\n"
              f"       diff, then update KWTABLE_SIZE/KWTABLE_SHA in this file to the\n"
              f"       walked values above. If you did NOT, build/sub.rom does not hold\n"
              f"       what the assembler produced: check tools/pad_rom.py's report and\n"
              f"       rebuild from clean.", file=sys.stderr)
        return 1

    # Gate 1c: exactly one copy in the sub image (and the positive control for the
    # byte search gate 1a' below relies on).
    n_sub = sub.count(bytes(b))
    if n_sub != 1:
        why = ("the byte search found NOTHING, so gate 1a' below would be vacuous"
               if n_sub == 0 else
               "either a real duplicate is back, or the walked table is degenerate "
               "and gate 1b above should have caught it first")
        print(f"FAIL: the {len(b)}-byte `kwtable` occurs {n_sub} times in the "
              f"{len(sub)}-byte sub-ROM, expected exactly 1 — {why}", file=sys.stderr)
        return 1

    # Gate 1a': and the resident copy is gone in BYTES, not merely in symbols.
    n_reloc = reloc.count(bytes(b))
    if n_reloc != 0:
        print(f"FAIL: the `kwtable` bytes occur {n_reloc} time(s) in the repack main "
              f"ROM even though no `kwtable` symbol does — a resident copy is back "
              f"under another name (or no name at all)", file=sys.stderr)
        return 1

    print(f"OK: kwtable single-copy — resident dropped (wave 3) in symbols AND in bytes "
          f"(0 occurrences in the {len(reloc)} B main image), sub-ROM copy is the sole "
          f"source, 1 occurrence, {len(b)} B matching the pinned sha256")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
