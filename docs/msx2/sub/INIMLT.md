<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `INIMLT` (sub-ROM $00E1) — set up the multicolour screen (SCREEN 3)

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the HB-F900, NMS 8250 and FS-A1WSX ([xmode.asm](../../../probes/bios/spec/xmode.asm), [scratchpad/AE_xmode_msx2.out](../../../scratchpad/AE_xmode_msx2.out), decoded by [scratchpad/xmode_decode.py](../../../scratchpad/xmode_decode.py) into [scratchpad/AE_xmode_msx2_decoded.out](../../../scratchpad/AE_xmode_msx2_decoded.out); round 2 [xmode2.asm](../../../probes/bios/spec/xmode2.asm), [scratchpad/AE_xmode2_msx2.out](../../../scratchpad/AE_xmode2_msx2.out), decoded by [scratchpad/xmode2_decode.py](../../../scratchpad/xmode2_decode.py) into [scratchpad/AE_xmode2_msx2_decoded.out](../../../scratchpad/AE_xmode2_msx2_decoded.out)).
>
> Goldfish pass 1 (test writer) 2026-11-23: 9 findings, 7 measured, 2 moved to open.

## Summary

`INIMLT` switches to MULTI COLOUR (SCREEN 3, 64 × 48 blocks), programming the VDP from the SCREEN 3
table cells. It does not touch the palette. Shared facts:
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
- In: MLTNAM, MLTCOL, MLTCGP, MLTATR, MLTPAT ($F3D1-$F3DA) [P App. 1, SUB-ROM INIMLT]; FORCLR, BDRCLR and the
  copies RG0SAV, RG1SAV, RG3SAV (below). Not inputs: A, F, LINLEN, SCRMOD, OLDSCR [M xmode2 22].
- Out: A $00, F $40 (A / F $FF on entry); BC, DE, HL changed; IX the entry ($00E1); IY and the alternates kept
  [M xmode2 22; xmode 14].
- The palette is not initialised [P App. 1, main-ROM INIMLT]: left as found [M xmode2 22].
- Interrupts on return: as entered (off after DI) [M xmode2 22; xmode 14]; an EI entry was not measured (IE).

**Behaviour** (from SCREEN 8 with SCRMOD 7, OLDSCR 6, copies $00, colours $0A / $05 / $03 [M xmode2 22]; from
SCREEN 0 with copies $A5 [M xmode 14]):
- **VDP**: R#0 := RG0SAV AND $F1 ($00 / $A1 → VDP $20); R#1 := RG1SAV AND $07 OR $68 ($68 / $6D); R#2 $02; **R#3 :=
  RG3SAV** ($00 / $A5 came back -- the mode has no colour table); R#4 $00, R#5 $36, R#6 $07; **R#7 := BDRCLR**
  ($03); R#9 bit 7 := 0 ($82 → $02); **R#11 := 0** (from $01 after SCREEN 8) [M xmode2 22; xmode 14]. Copies := the
  same.
- **Cells**: SCRMOD := 3; **OLDSCR and LINLEN are left as found** (6 and 29 stay) [M xmode2 22]; NAMBAS..ATRBAS :=
  $0800 $0000 $3800 $1B00 [M xmode2 22; xmode 14]. The MLT\* cells were at their defaults (IM-BASE).
- **VRAM** (2396 bytes rewritten, all below $4000): the name table, the pattern table and the 32 sprite attribute
  entries (Y := **209**, pattern n, 4th byte FORCLR) [M xmode2 22]. Which bytes the name table gets is open (IM-NAME).

## Differences from the reference

C-BIOS's MSX2 / MSX2+ builds ([scratchpad/AE_xmode2_msx2_decoded.out](../../../scratchpad/AE_xmode2_msx2_decoded.out), `ours`):
- **Interrupts ON on return** after a DI entry [M xmode2 22; xmode 14].
- **R#11 is not reset**: $01 stays after SCREEN 8 (RG11SAV too) [M xmode2 22].
- **R#3 := $00 and RG3SAV := $00** instead of R#3 := RG3SAV [M xmode 14].
- **Other VRAM**: 1632 bytes rewritten below $4000 (references 2396) and 384 bytes in $4000-$7FFF, which the
  references do not touch [M xmode2 22].

## On the turbo R

Measured 2026-11-23 (D-TRSPEC) on the FS-A1GT / FS-A1ST: every register, VRAM sum and work-area byte is the FS-A1WSX's, on both models. What differs is the machine and the timing, not the call: $FFF8 = $FF as the boot leaves it (the A1WSX $00; no screen-mode call touches it), VDP S#2 read at a random moment, R#36 = $80 before case 0 (the boot's last VDP command), power-on cells, and one JIFFY count in xmode2 case 27 [M] ([AE_trall/xmode.out](../../../scratchpad/AE_trall/xmode.out), [AE_trall/xmode2.out](../../../scratchpad/AE_trall/xmode2.out); overview: [turbor/remeasured.md](../../turbor/remeasured.md)).

## Open (not measured)

Recorded per case: as [CHGMOD](CHGMOD.md#open-not-measured).

| case | inputs | state | what it separates | HB-F900 | NMS 8250 | FS-A1WSX |
|---|---|---|---|---|---|---|
| IE | the page's base case | entered once with DI, once with EI | interrupt state on return (DI: off) | ? | ? | ? |
| IM-BASE | cells default, moved, unaligned | R#3 / R#10 copies garbage | R#3 from RG3SAV (measured) vs MLTCOL when moved; R#10 | ? | ? | ? |
| IM-NAME | — | name table $5A, read byte for byte | the 0..31 × 4-rows layout written | ? | ? | ? |
| IM-SPR | RG1SAV bit 1 set | — | pattern step 4 with 16 × 16 | ? | ? | ? |
| IM-R89 | — | R#8 bits 1, 3, 5, 6, 7 and R#9 bits 1, 2, 3, 4, 5 each walked alone, copies ≠ VDP | which bits kept, from the copy or the VDP | ? | ? | ? |
| IM-PREV | — | from SCREEN 5, 8 (DPPAGE 1) | R#2 page bits; OLDSCR untouched (measured from SCREEN 8 with OLDSCR 6) | ? | ? | ? |
| IM-PAL | — | palette non-default | untouched | untouched [M xmode2 22] | untouched | untouched |
| IM-MAIN | main-ROM $0075 | same set-ups | the *3 claim by a breakpoint on the sub-ROM entry and on EXTROM ($015F) as a call trace | ? | ? | ? |

## Related pages

[The screen-modes page](../concepts/screen-modes.md); [SETMLT](SETMLT.md); [CHGMOD](CHGMOD.md);
MSX1 [INIMLT](../../bios/INIMLT.md).

## Tests that cover it

none yet
