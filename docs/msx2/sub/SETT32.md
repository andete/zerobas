<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `SETT32` (sub-ROM $00E9) — set the VDP to GRAPHIC 1 (SCREEN 1), only

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the HB-F900, NMS 8250 and FS-A1WSX ([xmode.asm](../../../probes/bios/spec/xmode.asm), [scratchpad/AE_xmode_msx2.out](../../../scratchpad/AE_xmode_msx2.out), decoded by [scratchpad/xmode_decode.py](../../../scratchpad/xmode_decode.py) into [scratchpad/AE_xmode_msx2_decoded.out](../../../scratchpad/AE_xmode_msx2_decoded.out); round 2 [xmode2.asm](../../../probes/bios/spec/xmode2.asm), [scratchpad/AE_xmode2_msx2.out](../../../scratchpad/AE_xmode2_msx2.out), decoded by [scratchpad/xmode2_decode.py](../../../scratchpad/xmode2_decode.py) into [scratchpad/AE_xmode2_msx2_decoded.out](../../../scratchpad/AE_xmode2_msx2_decoded.out)).
>
> Goldfish pass 1 (test writer) 2026-11-23: 9 findings, 7 measured, 2 moved to open.

## Summary

`SETT32` programs the VDP for SCREEN 1 from the same cells as [INIT32](INIT32.md), without the rest
of INIT32's work. Shared facts: [the screen-modes page](../concepts/screen-modes.md).

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
- In: as INIT32 (T32NAM .. T32PAT) [P App. 1, SUB-ROM SETT32]; the copies RG0SAV, RG1SAV, RG7SAV, RG9SAV. Not
  inputs: A, F, SCRMOD [M xmode2 25].
- Out: **A $00, F $44** whatever A / F were on entry ($FF / $FF here; SETMLT also $00 / $00) [M xmode2 25; xmode
  16]; BC, DE, HL changed; IX the entry; IY and the alternates kept [M xmode2 25].
- Interrupts on return: **ON** after a DI entry [M xmode2 25; xmode 16].

**Behaviour.**
- Sets the VDP to GRAPHIC 1 [P App. 1, SUB-ROM SETT32; main-ROM SETT32].
- **Only the VDP and the copies change**: SCRMOD, OLDSCR, LINLEN, NAMBAS..ATRBAS, the cursor, the palette and VRAM
  are left as found -- SCRMOD stays 5 after SCREEN 5 [M xmode2 25].
- **R#0** := RG0SAV AND $F1 OR the mode's bits; **R#1** := RG1SAV AND $E7 OR the mode's M1 / M2: the screen-on,
  interrupt and size bits come from the copy -- RG1SAV $00 leaves the screen **off**, $FF on (bit 7 stays in the
  copy, the VDP keeps $7F) [M xmode2 25]. The copies RG0SAV / RG1SAV := the same.
- **R#7 := RG7SAV** (the probe's $FF / $00 / $A5 came back, with FORCLR / BAKCLR / BDRCLR other values and the VDP's
  R#7 another): not rebuilt from the colours [M xmode2 25; xmode 16].
- **R#2 $06, R#3 $80, R#4 $00, R#5 $36, R#6 $07** -- as INIT32 -- written to the VDP and the copies (from SCREEN 5,
  where the VDP held $1F / $80 / $00 / $EF / $0F) [M xmode2 25; xmode 16]. Example: copies $8F / $FF from SCREEN 5 →
  `00 67 06 80 00 36 07 FF` [M xmode2 25].
- **R#9** bit 7 := 0 ($82 → $02) [M xmode2 25]. R#11 $00 as on entry.

## Differences from the reference

C-BIOS's MSX2 / MSX2+ builds set R#0-R#6 the same, but [M xmode2 25; xmode 16]: **R#7 is left as the VDP had it**
($04; the references write RG7SAV); **R#9 bit 7 is left set** ($82); A $07, F $42 on return.

## Open (not measured)

Recorded per case: as [CHGMOD](CHGMOD.md#open-not-measured); the -ONLY cases add a whole work-area diff
$F380-$FFFF (only the register copies may differ).

| case | inputs | state | what it separates | HB-F900 | NMS 8250 | FS-A1WSX |
|---|---|---|---|---|---|---|
| IE | — | entered with DI and with EI | interrupt state on return: on after DI: "kept" and "forced off" are excluded; the EI half cannot add a rule | on [M xmode2 25] | on | on |
| S32-BASE | cells moved, T32COL / T32ATR at $C000+ | R#10 / R#11 copies garbage | R#2-R#6, R#10 / R#11 from the cells vs constants; R#11 := 0 vs kept | ? | ? | ? |
| S32-ONLY | — | SCRMOD, cursor, LINLEN, colour / sprite tables garbage | "VDP only" by a whole work-area diff (SCRMOD, LINLEN, cells, VRAM, palette measured untouched) | untouched [M xmode2 25] | same | same |
| S32-R89 | — | R#8 bits 1, 3, 5, 6, 7 and R#9 bits 1, 2, 3, 4, 5 each walked alone, copies ≠ VDP | which bits kept, from the copy or the VDP | ? | ? | ? |
| S32-MAIN | main-ROM $007B | same | the *3 claim by a breakpoint on the sub-ROM entry and on EXTROM ($015F) as a call trace | ? | ? | ? |

## Related pages

[The screen-modes page](../concepts/screen-modes.md); [INIT32](INIT32.md); MSX1
[SETT32](../../bios/SETT32.md).

## Tests that cover it

none yet
