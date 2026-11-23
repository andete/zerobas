<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `INIMLT` (sub-ROM $00E1) — set up the multicolour screen (SCREEN 3)

> **Spec:** DRAFT 0 (2026-11-23), from the published interface only; nothing measured yet. References to measure: HB-F900, NMS 8250, FS-A1WSX.

## Summary

`INIMLT` switches to MULTI COLOUR (SCREEN 3, 64 × 48 blocks), programming the VDP from the SCREEN 3
table cells. It does not touch the palette. Shared facts:
[the screen-modes page](../concepts/screen-modes.md).

## The specification

**Interface.**
- In: MLTNAM, MLTCOL, MLTCGP, MLTATR, MLTPAT ($F3D1-$F3DA) [P App. 1, SUB-ROM INIMLT].
- Out: none; all registers may change [P App. 1, SUB-ROM INIMLT].
- The palette is not initialised [P App. 1, main-ROM INIMLT].
- Interrupts on return: [A].

**Behaviour.**
- Sets the VDP to MULTI COLOUR [P App. 1, SUB-ROM INIMLT; Ch. 4 §3.3]; R#2, R#4-R#6 from the cells
  [A]; MLTCOL's use (the mode has no colour table) [A].
- Writes the name-table pattern, clears, parks sprites, R#7 := BDRCLR, SCRMOD := 3 [A]
  (as MSX1 [INIMLT](../../bios/INIMLT.md)).

## Differences from the reference

Not measured yet.

## Open (not measured)

Recorded per case: as [CHGMOD](CHGMOD.md#open-not-measured).

| case | inputs | state | what it separates | HB-F900 | NMS 8250 | FS-A1WSX |
|---|---|---|---|---|---|---|
| IE | the page's base case (its first row) | entered once with DI, once with EI | interrupt state on return: forced on, forced off, or kept (read twice, §3a) | ? | ? | ? |
| IM-BASE | cells default, moved, unaligned | R#3 / R#10 copies garbage | R#3 / R#10 written from MLTCOL, a constant, or kept | ? | ? | ? |
| IM-NAME | — | name table garbage | the 0..31 × 4-rows layout written | ? | ? | ? |
| IM-SPR | R#1 bit 1 set / clear | sprite table garbage | Y 209 | ? | ? | ? |
| IM-R89 | — | R#8 bits 1, 3, 5, 6, 7 and R#9 bits 1, 2, 3, 4, 5, 7, each walked alone, copies ≠ VDP | kept bits | ? | ? | ? |
| IM-PREV | — | from SCREEN 5, 8 (DPPAGE 1) | R#2 page bits; OLDSCR | ? | ? | ? |
| IM-PAL | — | palette non-default | untouched | ? | ? | ? |
| IM-MAIN | main-ROM $0075 | same set-ups | the *3 claim by a breakpoint on the sub-ROM entry and on EXTROM ($015F) as a call trace | ? | ? | ? |

## Related pages

[The screen-modes page](../concepts/screen-modes.md); [SETMLT](SETMLT.md); [CHGMOD](CHGMOD.md);
MSX1 [INIMLT](../../bios/INIMLT.md).

## Tests that cover it

none yet
