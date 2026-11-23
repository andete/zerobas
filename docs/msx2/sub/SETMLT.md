<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `SETMLT` (sub-ROM $00F1) — set the VDP to MULTI COLOUR (SCREEN 3), only

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the HB-F900, NMS 8250 and FS-A1WSX ([xmode.asm](../../../probes/bios/spec/xmode.asm), [scratchpad/AE_xmode_msx2.out](../../../scratchpad/AE_xmode_msx2.out), decoded by [scratchpad/xmode_decode.py](../../../scratchpad/xmode_decode.py) into [scratchpad/AE_xmode_msx2_decoded.out](../../../scratchpad/AE_xmode_msx2_decoded.out); round 2 [xmode2.asm](../../../probes/bios/spec/xmode2.asm), [scratchpad/AE_xmode2_msx2.out](../../../scratchpad/AE_xmode2_msx2.out), decoded by [scratchpad/xmode2_decode.py](../../../scratchpad/xmode2_decode.py) into [scratchpad/AE_xmode2_msx2_decoded.out](../../../scratchpad/AE_xmode2_msx2_decoded.out)).
>
> Goldfish pass 1 (test writer) 2026-11-23: 9 findings, 7 measured, 2 moved to open.

## Summary

`SETMLT` programs the VDP for SCREEN 3 from the same cells as [INIMLT](INIMLT.md), without the rest
of INIMLT's work. Shared facts: [the screen-modes page](../concepts/screen-modes.md).

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
- In: as INIMLT (MLTNAM .. MLTPAT) [P App. 1, SUB-ROM SETMLT]; the copies RG0SAV, RG1SAV, RG3SAV, RG7SAV. Not
  inputs: A, F, SCRMOD [M xmode2 27, 28].
- Out: **A $00, F $44** whatever A / F were on entry ($FF / $FF and $00 / $00) [M xmode2 27, 28; xmode
  18]; BC, DE, HL changed; IX the entry; IY and the alternates kept [M xmode2 27, 28].
- Interrupts on return: **ON** after a DI entry [M xmode2 27, 28; xmode 18].

**Behaviour.**
- Sets the VDP to MULTI COLOUR [P App. 1, SUB-ROM SETMLT]: **M1 cleared, M2 set** -- RG1SAV $FF (M1 set) gives
  RG1SAV $EF, VDP $6F [M xmode2 27].
- **Only the VDP and the copies change**: SCRMOD, OLDSCR, LINLEN, NAMBAS..ATRBAS, the cursor and the palette are
  left as found -- SCRMOD stays 0 where a write would give 3 [M xmode2 27, 28; xmode 18]; VRAM was not read here.
- **R#0** := RG0SAV AND $F1 OR the mode's bits; **R#1** := RG1SAV AND $E7 OR the mode's M1 / M2: the screen-on,
  interrupt and size bits come from the copy -- RG1SAV $00 leaves the screen **off**, $FF on (bit 7 stays in the
  copy, the VDP keeps $7F) [M xmode2 27, 28]. The copies RG0SAV / RG1SAV := the same.
- **R#7 := RG7SAV** (the probe's $FF / $00 / $A5 came back, with FORCLR / BAKCLR / BDRCLR other values and the VDP's
  R#7 another): not rebuilt from the colours [M xmode2 27, 28; xmode 18].
- **R#2 $02, R#3 := RG3SAV** ($FF / $00 / $A5 came back), **R#4 $00, R#5 $36, R#6 $07** -- as INIMLT [M xmode2 27, 28;
  xmode 18]. Examples: copies $8F / $FF → `00 6F 02 FF 00 36 07 FF`; copies $00 → `00 08 02 00 00 36 07 00` (screen
  off); copies $A5 → R#1 **$2D** (RG1SAV $AD) [M xmode2 27, 28; xmode 18].
- R#9 $02 and R#11 $00 as on entry (from SCREEN 0: not separated).

## Differences from the reference

C-BIOS's MSX2 / MSX2+ builds set R#0-R#2 and R#4-R#6 the same, but [M xmode2 27, 28; xmode 18]: **R#3 := $00**
instead of RG3SAV ($FF / $A5); **R#7 is left as the VDP had it** ($F4 from CHGMOD 0; the references write RG7SAV); A
$07, F $42 on return.

## On the turbo R

Measured 2026-11-23 (D-TRSPEC) on the FS-A1GT / FS-A1ST: every register, VRAM sum and work-area byte is the FS-A1WSX's, on both models. What differs is the machine and the timing, not the call: $FFF8 = $FF as the boot leaves it (the A1WSX $00; no screen-mode call touches it), VDP S#2 read at a random moment, R#36 = $80 before case 0 (the boot's last VDP command), power-on cells, and one JIFFY count in xmode2 case 27 [M] ([AE_trall/xmode.out](../../../scratchpad/AE_trall/xmode.out), [AE_trall/xmode2.out](../../../scratchpad/AE_trall/xmode2.out); overview: [turbor/remeasured.md](../../turbor/remeasured.md)).

## Open (not measured)

Recorded per case: as [CHGMOD](CHGMOD.md#open-not-measured); the -ONLY cases add a whole work-area diff
$F380-$FFFF (only the register copies may differ).

| case | inputs | state | what it separates | HB-F900 | NMS 8250 | FS-A1WSX |
|---|---|---|---|---|---|---|
| IE | — | entered with DI and with EI | interrupt state on return: on after DI: "kept" and "forced off" are excluded; the EI half cannot add a rule | on [M xmode2 27, 28] | on | on |
| SM-ONLY | — | SCRMOD 5, name table, sprites, VRAM garbage | "VDP only" by a whole work-area diff (SCRMOD, cells, palette measured untouched from SCREEN 0; VRAM not read) | ? | ? | ? |
| SM-BASE | cells default / moved | R#3 / R#10 copies garbage | R#3 from RG3SAV (measured) vs MLTCOL when moved; R#10 | ? | ? | ? |
| SM-R9 | — | from SCREEN 5 (R#9 bit 7 set) | R#9 bit 7 := 0 as SETTXT / SETT32 | ? | ? | ? |
| SM-R89 | — | R#8 bits 1, 3, 5, 6, 7 and R#9 bits 1, 2, 3, 4, 5 each walked alone, copies ≠ VDP | which bits kept, from the copy or the VDP | ? | ? | ? |
| SM-MAIN | main-ROM $0081 | same | the *3 claim by a breakpoint on the sub-ROM entry and on EXTROM ($015F) as a call trace | ? | ? | ? |

## Related pages

[The screen-modes page](../concepts/screen-modes.md); [INIMLT](INIMLT.md); MSX1
[SETMLT](../../bios/SETMLT.md).

## Tests that cover it

none yet
