<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `KNJPRT` (sub-ROM $01BD) — draw a kanji on a bitmap screen

> **Spec:** DRAFT 1 (2026-11-23): MEASURED in SCREEN 5 on the HB-F900, NMS 8250 and FS-A1WSX ([xsubknj.asm](../../../probes/bios/spec/xsubknj.asm), [scratchpad/AE_xsubknj_msx2.out](../../../scratchpad/AE_xsubknj_msx2.out), decoded by [xsubknj_decode.py](../../../scratchpad/xsubknj_decode.py)).

## Summary

`KNJPRT` draws one kanji, read from the kanji ROM by its JIS code, on a bitmap screen (SCREEN 5-8) —
the machine-code side of BASIC's `PUT KANJI`. It draws the full 16 x 16 character, or only its even or
odd dots. The kanji ROM and the cells it is assumed to use are on the
[concept page](../concepts/clock-and-misc.md#other-devices-the-calls-in-this-region-reach).

Measured in SCREEN 5: the character is drawn at (GRPACX, GRPACY), foreground dots in the colour at $F3F2 and
background dots in BAKCLR, through LOGOPR; then GRPACX moves 16 to the right. Mode 1 / 2 draw the even / odd ROWS
only, packed into 8 lines. The NMS 8250, which has no kanji ROM, draws a solid 16 x 16 (or 16 x 8) block in the
foreground colour. C-BIOS's MSX2 / MSX2+ builds draw nothing.

## The specification

Tags as on the [concept page](../concepts/clock-and-misc.md#references-subject-citation-tags).
**[M KJ n]**: case n of [xsubknj.asm](../../../probes/bios/spec/xsubknj.asm), run 2026-11-23 on all three references,
`--fresh`. Every case: CHGMOD 5; the window X 12-35, Y 12-35 (the cell at (16, 16) and a 4-dot margin) := colour 3
by hand; FORCLR ($F3E9) 15, BAKCLR ($F3EA) 4, $F3F2 5, $F3F3 10 (four different colours, so a dot's colour names
its source cell); GRPACX / GRPACY := 16 / 16, GXPOS / GYPOS := 40 / 40; DE $2468, HL $369C, IY $8765; the call; the
command engine waited for; then the registers, the four position cells and the window. Cases: 0 A 0 BC $3021;
1 A 1 $3021; 2 A 2 $3021; 3 A 0 $2422 (a kana); 4 A 0 $4F53; 5 A 0 $3021 with LOGOPR 3 (XOR); 6 A 0 BC $0000;
7 A 3 $3021. Which machine has a kanji ROM comes from openMSX's device list (`machine_info device`: "Kanji ROM" on
the HB-F900 and the FS-A1WSX, none on the NMS 8250 or the C-BIOS machines); the kanji ROM is never read.

**Interface.**
- Called through EXTROM / SUBROM with IX = $01BD [P A1].
- In: BC = the JIS kanji code; A = the display mode [P A1]. Out: nothing listed [P A1].
- Registers on return [M KJ 0-7], all three references: A, BC, DE, HL kept; F = $00. Interrupts on (entered with DI).

**Behaviour** (SCREEN 5; the kanji machines are the HB-F900 and the FS-A1WSX).
- **Position:** the cell's top-left is (GRPACX, GRPACY) [M KJ 0]; GXPOS / GYPOS are neither used nor changed
  [M KJ 0-7]. After drawing, **GRPACX += 16**, GRPACY unchanged [M KJ 0-5, 7].
- **Colours:** a set dot of the character is drawn in the colour at **$F3F2** (5), an unset dot in **BAKCLR**
  (4); neither FORCLR (15) nor $F3F3 (10) appears [M KJ 0-4]. Every dot of the cell is written: none keeps the
  preset 3 [M KJ 0]. Nothing outside the cell changes: the 4-dot margin keeps its preset in every case [M KJ 0-7].
- **Logical operation:** LOGOPR applies to both kinds of dot: with XOR, the preset 3 became 3 XOR 5 = 6 and
  3 XOR 4 = 7 [M KJ 5]. Only PSET (0) and XOR (3) measured.
- **Mode 0:** the whole 16 x 16 character, 16 lines [M KJ 0, 3, 4]. **Mode 1:** rows 0, 2, ..., 14 of the
  character, drawn on 8 consecutive lines from GRPACY; **mode 2:** rows 1, 3, ..., 15, the same way; the lines
  below the eighth are left as found [M KJ 1, 2] -- each line of mode 1 / 2 equals the matching row of mode 0's
  drawing on the same machine. "Even / odd" are rows, halved in height (as for an interlaced picture made of two
  pages). Both modes still move GRPACX by 16 [M KJ 1, 2].
- **Mode 3** draws as mode 2 on both kanji machines [M KJ 7, 2]; on the NMS 8250 too (a 16 x 8 block).
- **BC = $0000:** nothing is drawn and GRPACX does not move, on all three [M KJ 6]: the call checks the code.
  Which codes it refuses beyond $0000 [A].
- **The character's dots** are the machine's own kanji ROM's: the HB-F900 and the FS-A1WSX draw $3021 with
  82 / 80 foreground dots and $2422 with 67 / 52 -- their fonts differ, so a comparison compares the placement and
  the colours, never the font [M KJ 0, 3].
- **Without a kanji ROM (the NMS 8250):** the call draws as if every dot were set: a solid block of the $F3F2
  colour, 16 x 16 in mode 0, 16 x 8 in modes 1-3, no background colour, GRPACX += 16; with XOR it XORs the block
  [M KJ 0-5, 7]. $0000 draws nothing there too [M KJ 6].

## Differences from the reference

C-BIOS's MSX2 / MSX2+ builds (the subject), all three rows [M KJ 0-7]: **KNJPRT draws nothing and leaves GRPACX
unchanged** for every code and mode. (A, BC, DE, HL kept, F $00 and interrupts on, as the references.) The C-BIOS
machines have no kanji ROM; the NMS 8250, also without one, still draws its solid block and moves GRPACX, so the
comparison with no ROM on either side still differs.

## Open (not measured)

Measured: KJ-1 (SCREEN 5 only; three codes; modes 0-2), KJ-2 (as rows; the display not changed to interlace),
KJ-3, KJ-4 (PSET and XOR), KJ-7 ($0000 only), KJ-9 (A = 3), KJ-10 (the NMS 8250 and the C-BIOS machines), KJ-12
(registers, interrupts, the cursor advance). The concept page's plan to give the subject the reference's kanji ROM
image is not done: C-BIOS draws nothing, so there is nothing to compare yet. Still open:

| case | inputs | desynced state | what it separates |
|---|---|---|---|
| KJ-1b | SCREEN 6, 7, 8 | — | the placement and the dot width there |
| KJ-4b | LOGOPR 1, 2, 4, 8-12 | — | the other operations; whether TPSET etc. leave background dots alone |
| KJ-5 | one code | ACPAGE ≠ DPPAGE, each page | the page it draws on |
| KJ-6 | the right edge (X = 248 in SCREEN 5) and the bottom edge | — | clip, wrap or overrun; GRPACX past the edge |
| KJ-7b | BC = $2120, $7F7F, $FFFF, a gap in the JIS table | — | which codes are refused |
| KJ-8 | BC = $5021, $7E7E (JIS level 2) | with and without a level-2 ROM | level-2 codes |
| KJ-9b | A = $FF, 4 | — | other modes |
| KJ-11 | SCREEN 0-4; 10-12 on the FS-A1WSX | — | no-op, fallback or VRAM damage |
| KJ-12b | entered with EI | — | the interrupt state (DI measured) |
| KJ-13 | the KJ-1 set through SUBROM | — | equal to EXTROM's results |

## Related pages

[the concept page](../concepts/clock-and-misc.md); the bitmap screens:
[screen-modes concept page](../concepts/screen-modes.md); [the inventory](../index.md).

## Tests that cover it

none yet
