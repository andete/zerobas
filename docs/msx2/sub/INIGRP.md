<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `INIGRP` (sub-ROM $00DD) — set up the high-resolution graphics screen (SCREEN 2)

> **Spec:** DRAFT 0 (2026-11-23), from the published interface only; nothing measured yet. References to measure: HB-F900, NMS 8250, FS-A1WSX.

## Summary

`INIGRP` switches to GRAPHIC 2 (SCREEN 2, 256 × 192, colour per 8 dots), programming the VDP from
the SCREEN 2 table cells. It does not touch the palette. Shared facts:
[the screen-modes page](../concepts/screen-modes.md).

## The specification

**Interface.**
- In: GRPNAM, GRPCOL, GRPCGP, GRPATR, GRPPAT ($F3C7-$F3D0) [P App. 1, SUB-ROM INIGRP].
- Out: none; all registers may change [P App. 1, SUB-ROM INIGRP].
- The palette is not initialised [P App. 1, main-ROM INIGRP].
- Interrupts on return: [A].

**Behaviour.**
- Sets the VDP to GRAPHIC 2 [P App. 1, SUB-ROM INIGRP; Ch. 4 §3.5]; R#2-R#6 from the cells, R#3 /
  R#4 with their mode-fixed low bits, R#10 / R#11 [A].
- Writes the name table 0..255 three times, clears, parks sprites, R#7 := BDRCLR, SCRMOD := 2 [A]
  (as MSX1 [INIGRP](../../bios/INIGRP.md)).
- OLDSCR, R#8 / R#9: [A].

## Differences from the reference

Not measured yet.

## Open (not measured)

Recorded per case: as [CHGMOD](CHGMOD.md#open-not-measured).

| case | inputs | state | what it separates | HB-F900 | NMS 8250 | FS-A1WSX |
|---|---|---|---|---|---|---|
| IE | the page's base case (its first row) | entered once with DI, once with EI | interrupt state on return: forced on, forced off, or kept (read twice, §3a) | ? | ? | ? |
| IG-BASE | cells default, moved, unaligned (GRPCOL $2040, GRPCGP $0800), GRPCOL / GRPATR at $C000+ | R#3 / R#4 / R#10 copies garbage | low "mask" bits of R#3 ($FF) and R#4 ($03) forced vs taken from the cell; R#10 / R#11 := 0 vs cell >> 14 | ? | ? | ? |
| IG-NAME | — | name table garbage | 0..255 × 3 written | ? | ? | ? |
| IG-SPR | R#1 bit 1 set / clear | sprite table garbage | Y 209; no sprite colour table | ? | ? | ? |
| IG-R89 | — | R#8 bits 1, 3, 5, 6, 7 and R#9 bits 1, 2, 3, 4, 5, 7, each walked alone, copies ≠ VDP | kept bits | ? | ? | ? |
| IG-PREV | — | from SCREEN 0 (TEXT 2), 4, 7 | OLDSCR rule; R#0 M4 cleared | ? | ? | ? |
| IG-COL | BDRCLR $F9, BAKCLR $C5 | — | R#7 value; colour table filled with what | ? | ? | ? |
| IG-PAL | — | palette non-default | untouched | ? | ? | ? |
| IG-MAIN | main-ROM $0072 | same set-ups | the *3 claim by a breakpoint on the sub-ROM entry and on EXTROM ($015F) as a call trace | ? | ? | ? |

## Related pages

[The screen-modes page](../concepts/screen-modes.md); [SETGRP](SETGRP.md); [CHGMOD](CHGMOD.md);
MSX1 [INIGRP](../../bios/INIGRP.md).

## Tests that cover it

none yet
