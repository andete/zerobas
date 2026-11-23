<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `INIT32` (sub-ROM $00D9) — set up the 32-column text screen (SCREEN 1)

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the HB-F900, NMS 8250 and FS-A1WSX ([xmode.asm](../../../probes/bios/spec/xmode.asm), [scratchpad/AE_xmode_msx2.out](../../../scratchpad/AE_xmode_msx2.out), decoded by [scratchpad/xmode_decode.py](../../../scratchpad/xmode_decode.py) into [scratchpad/AE_xmode_msx2_decoded.out](../../../scratchpad/AE_xmode_msx2_decoded.out); round 2 [xmode2.asm](../../../probes/bios/spec/xmode2.asm), [scratchpad/AE_xmode2_msx2.out](../../../scratchpad/AE_xmode2_msx2.out), decoded by [scratchpad/xmode2_decode.py](../../../scratchpad/xmode2_decode.py) into [scratchpad/AE_xmode2_msx2_decoded.out](../../../scratchpad/AE_xmode2_msx2_decoded.out)).
>
> Goldfish pass 1 (test writer) 2026-11-23: 13 findings, 10 measured, 3 moved to open.

## Summary

`INIT32` switches to GRAPHIC 1, the 32 × 24 text screen of SCREEN 1, programming the VDP from the
SCREEN 1 table cells. It does not touch the palette. Shared facts:
[the screen-modes page](../concepts/screen-modes.md).

## The specification

Case numbers as on [CHGMOD](CHGMOD.md#the-specification): `[M xmode r]` round 1 (every case after a main CHGMOD 0,
copies RG0SAV-RG7SAV := $A5), `[M xmode2 n]` round 2 (entered from another mode with no CHGMOD 0 in between, the
copies $00 or $8F / $FF, FORCLR / BAKCLR / BDRCLR $0A / $05 / $03 or $0E / $0C / $09, the widths and SCRMOD / OLDSCR
given other values, A / F on entry $FF / $FF unless stated, VRAM := $5A and a non-default palette where VRAM is
read). The three references agree on every output except the machine's own constants: R#9 bit 1 (PAL, $02 on the
NMS 8250), the default LINL40 (37 EU, 39 JP) and BDRCLR (4 EU, 7 JP), the font, MODE and $FFF7-$FFFC. The VDP keeps
only some bits of what is written: R#0 $7E, R#1 $7F, R#2 $7F, R#4 $3F, R#6 $3F, R#10 $07, R#11 $03 (a raw OUT of
$FF read back) [M xmode2 29]; the copies keep all 8.

**Interface.**
- In: T32NAM, T32COL, T32CGP, T32ATR, T32PAT ($F3BD-$F3C6) [P App. 1, SUB-ROM INIT32]; LINL32, FORCLR, BAKCLR,
  BDRCLR and the copies RG0SAV, RG1SAV (below). Not inputs: A, F, LINLEN, SCRMOD, OLDSCR [M xmode2 20].
- Out: A $00, F $40 (A / F $FF on entry); BC, DE, HL changed; IX $000C (not kept); IY and the alternates kept
  [M xmode2 20; xmode 12].
- The palette is not initialised [P App. 1, main-ROM INIT32]: left as found [M xmode2 20].
- Interrupts on return: as entered (off after DI) [M xmode2 20; xmode 12]; an EI entry was not measured (IE).

**Behaviour** (from SCREEN 5 with LINL32 33, LINLEN 20, SCRMOD 7, OLDSCR 6, copies $00, colours $0A / $05 / $03
[M xmode2 20]; from SCREEN 0 with copies $A5 [M xmode 12]):
- **VDP**: R#0 := RG0SAV AND $F1 ($00 / $A1 → VDP $20); R#1 := RG1SAV AND $07 OR $60 ($60 / $65); R#2 $06, R#3 $80,
  R#4 $00, R#5 $36, R#6 $07 (copies $00 and $A5 alike); **R#7 := BDRCLR** ($03 here, $04 / $07 by default); R#9 bit 7
  := 0 ($82 → $02); **R#11 := 0** (from $01, which INITXT had left: "kept" is excluded) [M xmode 11, 12]. The copies
  RG0SAV-RG7SAV := the same.
- **Cells**: SCRMOD := 1, OLDSCR := 1, **LINLEN := LINL32** (33 from LINLEN 20), NAMBAS..ATRBAS := $1800 $0000 $3800
  $1B00, cursor home [M xmode2 20; xmode 12]. The T32\* cells were at their defaults, so "from the cells" vs "App. 5
  constants" is open (I32-BASE).
- **VRAM** (2944 bytes rewritten, all below $4000): the name table (768), the patterns (2048), the colour table (32)
  := **FORCLR·16 + BAKCLR** ($A5), and the 32 sprite attribute entries: Y := **209**, pattern := n (8 × 8, RG1SAV
  bit 1 clear), 4th byte := FORCLR, X untouched [M xmode2 20]. No sprite colour table (VRAM at T32ATR − 512 not
  rewritten; the count holds no room for it).

## Differences from the reference

C-BIOS's MSX2 / MSX2+ builds set the same registers, cells and VRAM, but return with **interrupts ON** after a DI entry
[M xmode2 20; xmode 12] (and other A / F / IX, which the contract leaves free).

## Open (not measured)

Recorded per case: as [CHGMOD](CHGMOD.md#open-not-measured).

| case | inputs | state | what it separates | HB-F900 | NMS 8250 | FS-A1WSX |
|---|---|---|---|---|---|---|
| IE | the page's base case | entered once with DI, once with EI | interrupt state on return (DI: off) | ? | ? | ? |
| I32-BASE | all five cells moved, T32COL / T32ATR at $C000+ | R#10 / R#11 copies garbage | R#2-R#6 and R#10 / R#11 from the cells vs constants; R#11 := 0 vs T32ATR / 32768 | ? | ? | ? |
| I32-SPR | RG1SAV bit 1 set | — | pattern step 4 with 16 × 16 (INIGRP: yes) | ? | ? | ? |
| I32-W | LINL32 = 0, 1, 32, 255 | LINL40 = 77 | LINLEN := LINL32 as is (33 measured) | ? | ? | ? |
| I32-R89 | — | R#8 bits 1, 3, 5, 6, 7 and R#9 bits 1, 2, 3, 4, 5 each walked alone, copies ≠ VDP | which bits kept, from the copy or the VDP | ? | ? | ? |
| I32-COL | FORCLR $3A, BAKCLR $C5, BDRCLR $F9 | — | colour-table byte and R#7 in 8 bits (only nibble values measured) | ? | ? | ? |
| I32-PREV | — | from SCREEN 8 with DPPAGE 1, R#2 page bits | R#2 := $06 regardless | ? | ? | ? |
| I32-PAL | — | palette non-default | untouched | untouched [M xmode2 20] | untouched | untouched |
| I32-MAIN | main-ROM $006F | same set-ups | the *3 claim by a breakpoint on the sub-ROM entry and on EXTROM ($015F) as a call trace | ? | ? | ? |

## Related pages

[The screen-modes page](../concepts/screen-modes.md); [SETT32](SETT32.md); [INITXT](INITXT.md);
[CHGMOD](CHGMOD.md); MSX1 [INIT32](../../bios/INIT32.md).

## Tests that cover it

none yet
