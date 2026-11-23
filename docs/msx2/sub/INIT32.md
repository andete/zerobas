<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `INIT32` (sub-ROM $00D9) — set up the 32-column text screen (SCREEN 1)

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the HB-F900, NMS 8250 and FS-A1WSX ([xmode.asm](../../probes/bios/spec/xmode.asm), [scratchpad/AE_xmode_msx2.out](../../scratchpad/AE_xmode_msx2.out), decoded by `scratchpad/xmode_decode.py`).

## Summary

`INIT32` switches to GRAPHIC 1, the 32 × 24 text screen of SCREEN 1, programming the VDP from the
SCREEN 1 table cells. It does not touch the palette. Shared facts:
[the screen-modes page](../concepts/screen-modes.md).

## The specification

**Interface.**
- In: T32NAM, T32COL, T32CGP, T32ATR, T32PAT ($F3BD-$F3C6) [P App. 1, SUB-ROM INIT32].
- Out: none; all registers may change [P App. 1, SUB-ROM INIT32].
- The palette is not initialised [P App. 1, main-ROM INIT32].
- Interrupts on return: [A].

**Behaviour.**
- Sets the VDP to GRAPHIC 1 (32 × 24) [P App. 1, SUB-ROM INIT32]; R#2-R#6 and R#10 / R#11 from the
  cells [A].
- Fills the colour table, parks the 32 sprites, sets LINLEN := LINL32, SCRMOD / OLDSCR := 1, clears
  and homes, draws the key line [A] (as the MSX1 main-ROM INIT32: [INIT32](../../bios/INIT32.md)).
- The parked sprites' Y: 209 (modes 0-3) per CLRSPR [P App. 1, main-ROM CLRSPR]; whether INIT32
  parks them at all on an MSX2, [A].
- R#7 := BDRCLR [A]; R#8 / R#9: [A].

**Measured** [M] (the same on all three references, entered with interrupts off and RG0SAV-RG7SAV := $A5): the
same VDP registers and table cells as [CHGMOD](CHGMOD.md) with A 1 -- see its table -- interrupts as entered
(off), A $00, F $40.

## Differences from the reference

C-BIOS's MSX2 / MSX2+ builds set the same, but return with interrupts ON ([scratchpad/AE_xmode_msx2.out](../../scratchpad/AE_xmode_msx2.out)).

## Open (not measured)

Recorded per case: as [CHGMOD](CHGMOD.md#open-not-measured), plus LINTTB, the colour table and the
sprite attribute table byte for byte.

| case | inputs | state | what it separates | HB-F900 | NMS 8250 | FS-A1WSX |
|---|---|---|---|---|---|---|
| IE | the page's base case (its first row) | entered once with DI, once with EI | interrupt state on return: forced on, forced off, or kept (read twice, §3a) | ? | ? | ? |
| I32-BASE | all five cells moved, T32COL / T32ATR at $C000+ | R#10 / R#11 copies garbage | R#10 / R#11 := 0 vs cell >> 14 vs kept; R#5 bits from T32ATR | ? | ? | ? |
| I32-SPR | R#1 bit 1 set / clear | sprite table garbage | Y 209 vs 217; pattern step 1 vs 4; colour FORCLR | ? | ? | ? |
| I32-SPRCOL | — | VRAM at T32ATR − 512 garbage | no sprite colour table written (sprite mode 1) | ? | ? | ? |
| I32-W | LINL32 = 0, 1, 29, 32, 33, 255 | LINL40 = 77 | LINLEN as is | ? | ? | ? |
| I32-R89 | — | R#8 bits 1, 3, 5, 6, 7 and R#9 bits 1, 2, 3, 4, 5, 7, each walked alone, copies ≠ VDP | which bits kept | ? | ? | ? |
| I32-COL | FORCLR $3A, BAKCLR $C5, BDRCLR $F9 | — | colour table byte and R#7 in 8 bits | ? | ? | ? |
| I32-PREV | — | from SCREEN 8 with DPPAGE 1, R#2 page bits | R#2 recomputed from T32NAM | ? | ? | ? |
| I32-PAL | — | palette non-default | untouched | ? | ? | ? |
| I32-MAIN | main-ROM $006F | same set-ups | the *3 claim by a breakpoint on the sub-ROM entry and on EXTROM ($015F) as a call trace | ? | ? | ? |

## Related pages

[The screen-modes page](../concepts/screen-modes.md); [SETT32](SETT32.md); [INITXT](INITXT.md);
[CHGMOD](CHGMOD.md); MSX1 [INIT32](../../bios/INIT32.md).

## Tests that cover it

none yet
