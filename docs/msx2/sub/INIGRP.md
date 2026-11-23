<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `INIGRP` (sub-ROM $00DD) — set up the high-resolution graphics screen (SCREEN 2)

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the HB-F900, NMS 8250 and FS-A1WSX ([xmode.asm](../../../probes/bios/spec/xmode.asm), [scratchpad/AE_xmode_msx2.out](../../../scratchpad/AE_xmode_msx2.out), decoded by [scratchpad/xmode_decode.py](../../../scratchpad/xmode_decode.py) into [scratchpad/AE_xmode_msx2_decoded.out](../../../scratchpad/AE_xmode_msx2_decoded.out); round 2 [xmode2.asm](../../../probes/bios/spec/xmode2.asm), [scratchpad/AE_xmode2_msx2.out](../../../scratchpad/AE_xmode2_msx2.out), decoded by [scratchpad/xmode2_decode.py](../../../scratchpad/xmode2_decode.py) into [scratchpad/AE_xmode2_msx2_decoded.out](../../../scratchpad/AE_xmode2_msx2_decoded.out)).
>
> Goldfish pass 1 (test writer) 2026-11-23: 9 findings, 7 measured, 2 moved to open.

## Summary

`INIGRP` switches to GRAPHIC 2 (SCREEN 2, 256 × 192, colour per 8 dots), programming the VDP from
the SCREEN 2 table cells. It does not touch the palette. Shared facts:
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
- In: GRPNAM, GRPCOL, GRPCGP, GRPATR, GRPPAT ($F3C7-$F3D0) [P App. 1, SUB-ROM INIGRP]; FORCLR, BAKCLR, BDRCLR and
  the copies RG0SAV, RG1SAV (below). Not inputs: A, F, LINLEN, SCRMOD, OLDSCR [M xmode2 21].
- Out: A $00, F $40 (A / F $FF on entry); BC, DE, HL changed; IX the entry ($00DD); IY and the alternates kept
  [M xmode2 21; xmode 13].
- The palette is not initialised [P App. 1, main-ROM INIGRP]: left as found [M xmode2 21].
- Interrupts on return: as entered (off after DI) [M xmode2 21; xmode 13]; an EI entry was not measured (IE).

**Behaviour** (from SCREEN 5 with SCRMOD 7, OLDSCR 6, copies $8F / $FF, colours $0E / $0C / $09 [M xmode2 21]; from
SCREEN 0 with copies $A5 [M xmode 13]):
- **VDP**: R#0 := RG0SAV AND $F1 OR $02 (RG0SAV $83, VDP $02); R#1 := RG1SAV AND $07 OR $60 ($67 / $65); R#2 $06, R#3
  $FF, R#4 $03, R#5 $36, R#6 $07; **R#7 := BDRCLR** ($09; $04 / $07 by default); R#9 bit 7 := 0; R#11 $00 [M xmode2 21;
  xmode 13]. Copies := the same.
- **Cells**: SCRMOD := 2; **OLDSCR and LINLEN are left as found** (6 and 29 stay) [M xmode2 21]; NAMBAS..ATRBAS :=
  $1800 $0000 $3800 $1B00 [M xmode2 21; xmode 13]. The GRP\* cells were at their defaults (IG-BASE).
- **VRAM** (13149 bytes rewritten, all below $4000): the name table 0..255 three times (768, of which 3 bytes are
  $5A anyway), the pattern table (6144), the colour table (6144, its last byte := **BAKCLR**, $0C), and the 32
  sprite attribute entries: Y := **209**, pattern := 4n (16 × 16: RG1SAV bit 1 set), 4th byte := FORCLR ($0E), X
  untouched; no sprite colour table [M xmode2 21].

## Differences from the reference

C-BIOS's MSX2 / MSX2+ builds set the same registers, cells and VRAM, but return with **interrupts ON** after a DI entry
[M xmode2 21; xmode 13] (and other A / F, which the contract leaves free).

## Open (not measured)

Recorded per case: as [CHGMOD](CHGMOD.md#open-not-measured).

| case | inputs | state | what it separates | HB-F900 | NMS 8250 | FS-A1WSX |
|---|---|---|---|---|---|---|
| IE | the page's base case | entered once with DI, once with EI | interrupt state on return (DI: off) | ? | ? | ? |
| IG-BASE | cells default, moved, unaligned (GRPCOL $2040, GRPCGP $0800), GRPCOL / GRPATR at $C000+ | R#3 / R#4 / R#10 copies garbage | low "mask" bits of R#3 ($FF) and R#4 ($03) forced vs taken from the cell; R#10 / R#11 := 0 vs cell / 16384 | ? | ? | ? |
| IG-BYTE | — | VRAM $5A, read byte for byte | the pattern-table fill and every colour-table byte (only the count and the last byte measured) | ? | ? | ? |
| IG-R89 | — | R#8 bits 1, 3, 5, 6, 7 and R#9 bits 1, 2, 3, 4, 5 each walked alone, copies ≠ VDP | which bits kept, from the copy or the VDP | ? | ? | ? |
| IG-PREV | — | from SCREEN 0, 4, 7 with OLDSCR ≠ SCRMOD | OLDSCR untouched (measured from SCREEN 5 with OLDSCR 6); R#0 M4 cleared | OLDSCR untouched [M xmode2 21] | same | same |
| IG-COL | BDRCLR $F9, BAKCLR $C5 | — | R#7 and the colour-table byte in 8 bits | ? | ? | ? |
| IG-PAL | — | palette non-default | untouched | untouched [M xmode2 21] | untouched | untouched |
| IG-MAIN | main-ROM $0072 | same set-ups | the *3 claim by a breakpoint on the sub-ROM entry and on EXTROM ($015F) as a call trace | ? | ? | ? |

## Related pages

[The screen-modes page](../concepts/screen-modes.md); [SETGRP](SETGRP.md); [CHGMOD](CHGMOD.md);
MSX1 [INIGRP](../../bios/INIGRP.md).

## Tests that cover it

none yet
