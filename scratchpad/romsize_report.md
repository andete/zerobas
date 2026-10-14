# zerobas ROM size: where the bytes go, measured (2026-10-14)

A read-only investigation (a subagent, at Joost's request: "the VG-8020 fits
everything in 32 KB; we need more than 64 KB — are we missing something?").
Inputs: zerobas's own built ROMs and symbol files, its sources, and the C-BIOS
source. No reference ROM was read, hashed or disassembled; reference figures are
published facts or general knowledge (marked). **M** = measured, **E** = estimate.
The scripts it used were one-off and live outside the repo.

## Direct answer

zerobas is ~1.6x the reference with a disk, ~1.8x without, and its BASIC alone
is ~2.2x the reference's BASIC. The BIOS side is at parity (0.9x). Nothing
"stupid" is hiding: no forgotten holes, no dead code, no padding, no MSX2 code in
the BIOS. ">64 KB" counts ROM images (112 KB) rather than content (75 KB): the
second sub ROM is a 32 KB image holding 598 bytes.

| ROM | image | content (M) |
|---|---|---|
| main (C-BIOS 7994 + tape 727 + islands 411 + BASIC 22625) | 32768 | 31757 |
| sub | 32768 | 32352 |
| sub2 | 32768 | 598 |
| disk | 16384 | 12315 |
| total | 114688 | 77022 |

Content = bytes in attributed label spans minus runs of >= 8 identical 00/FF.

| comparison | zerobas (M) | reference | factor |
|---|---|---|---|
| BIOS side (C-BIOS + tape) | 8.5 KB | ~9.6 KB (E: published layout, BASIC from ~$2680) | 0.9x |
| BASIC side minus the disk verbs a real MSX keeps in its disk ROM | ~48.5 KB | ~22.4 KB | ~2.2x |
| diskless machine, everything | ~57 KB | 32 KB | ~1.8x |
| with disk, everything | 75.2 KB | 48 KB | 1.6x |

## Where the BASIC side's bytes go (M, grouped by source file)

| # | subsystem | main | sub | sub2 | total |
|---|---|---|---|---|---|
| 1 | core interpreter (dispatch, program store, REPL, LIST, tokeniser/detokeniser, keyword table, line editor) | 5791 | 5562 | 305 | 11658 |
| 2 | floating point (14-digit BCD core, tokeniser/formatter, SQR..RND, coefficient tables 1497) | 2770 | 6157 | 0 | 8927 |
| 3 | file I/O + disk-BASIC verbs + FAT12 engine | 3414 | 5307 | 0 | 8721 |
| 4 | screen + graphics | 1637 | 5486 | 190 | 7313 |
| 5 | expressions + variables + arrays + DEF FN | 4070 | 2167 | 0 | 6237 |
| 6 | string engine + heap | 1885 | 3208 | 0 | 5093 |
| 7 | PRINT / INPUT / PRINT USING / READ-DATA | 1607 | 1245 | 0 | 2852 |
| 8 | sound | 471 | 1503 | 74 | 2048 |
| 9 | cassette (+727 on the BIOS side) | 740 | 739 | 0 | 1479 |
| 10 | traps + error messages | 491 | 774 | 0 | 1265 |
| 11 | inter-slot glue, fixed part | 160 | 204 | 29 | 393 |

## Duplication and glue

- Byte-identical runs >= 24 B across and within the four ROMs: 1863 B (M).
  Deliberate shared bodies (`*-body.inc` included on several sides): ~2.6 KB
  (M), the FAT primitives in sub AND disk ROM (1756) the largest. Union
  ~3.5-4 KB (E), ~5 % of content. Half is structural: four 16 KB code areas
  that cannot call each other directly.
- Inter-slot stubs, jump tables, tenant entries and marshalling: ~1.4-1.6 KB (E).

## Checked and not there

Padding (< 300 B across the code ROMs; the disk ROM's 3.8 KB of holes are pinned
geometry), dead code, test code (~0.2 KB), MSX2 paths in C-BIOS (not compiled),
instruction-level slack in main (4 jp-in-jr-reach sites). C-BIOS: 7994 B of
content incl. the 2 KB font, not bloated.

## Cheap wins found (all in the sub ROM; Joost 2026-10-14: lower priority)

Math constants stored packed (-600..-700 B), keyword table encoding (-160..-320
B), variable-length KEY defaults (-90 B), shared FAT / math prefixes (-240 B).

## The levers that move the factor (Joost 2026-10-14: address these, in order)

1. Disk BASIC and the FAT engine (~8.7 KB) into the disk ROM, where a real MSX
   keeps them; removes most of the deliberate duplication; no speed cost to
   non-disk code. The disk ROM has 3.8 KB free, so the move must compact.
2. The string engine (~5 KB heap design).
3. Graphics (~7 KB).
4. The float core (~9 KB: 14 digits, one per byte, 18 B per number against the
   reference's 8 B packed format).
