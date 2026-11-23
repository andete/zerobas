<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `SETGRP` (sub-ROM $00ED) — set the VDP to GRAPHIC 2 (SCREEN 2), only

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the HB-F900, NMS 8250 and FS-A1WSX ([xmode.asm](../../../probes/bios/spec/xmode.asm), [scratchpad/AE_xmode_msx2.out](../../../scratchpad/AE_xmode_msx2.out), decoded by [scratchpad/xmode_decode.py](../../../scratchpad/xmode_decode.py) into [scratchpad/AE_xmode_msx2_decoded.out](../../../scratchpad/AE_xmode_msx2_decoded.out); round 2 [xmode2.asm](../../../probes/bios/spec/xmode2.asm), [scratchpad/AE_xmode2_msx2.out](../../../scratchpad/AE_xmode2_msx2.out), decoded by [scratchpad/xmode2_decode.py](../../../scratchpad/xmode2_decode.py) into [scratchpad/AE_xmode2_msx2_decoded.out](../../../scratchpad/AE_xmode2_msx2_decoded.out)).
>
> Goldfish pass 1 (test writer) 2026-11-23: 9 findings, 7 measured, 2 moved to open.

## Summary

`SETGRP` programs the VDP for SCREEN 2 from the same cells as [INIGRP](INIGRP.md), without the rest
of INIGRP's work. Shared facts: [the screen-modes page](../concepts/screen-modes.md).

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
- In: as INIGRP (GRPNAM .. GRPPAT) [P App. 1, SUB-ROM SETGRP]; the copies RG0SAV, RG1SAV, RG7SAV. Not inputs: A, F,
  SCRMOD [M xmode2 26].
- Out: **A $00, F $44** whatever A / F were on entry ($FF / $FF here; SETMLT also $00 / $00) [M xmode2 26; xmode
  17]; BC, DE, HL changed; IX the entry; IY and the alternates kept [M xmode2 26].
- Interrupts on return: **ON** after a DI entry [M xmode2 26; xmode 17].

**Behaviour.**
- Sets the VDP to GRAPHIC 2 [P App. 1, SUB-ROM SETGRP; main-ROM SETGRP]; **M4 is cleared**: RG0SAV $8F (M4 set)
  from SCREEN 4 gives RG0SAV $83, VDP $02 -- GRAPHIC 2, not GRAPHIC 3 [M xmode2 26].
- **Only the VDP and the copies change**: SCRMOD, OLDSCR, LINLEN, NAMBAS..ATRBAS, the cursor, the palette and VRAM
  are left as found -- SCRMOD stays 4 after SCREEN 4 [M xmode2 26].
- **R#0** := RG0SAV AND $F1 OR the mode's bits; **R#1** := RG1SAV AND $E7 OR the mode's M1 / M2: the screen-on,
  interrupt and size bits come from the copy -- RG1SAV $00 leaves the screen **off**, $FF on (bit 7 stays in the
  copy, the VDP keeps $7F) [M xmode2 26]. The copies RG0SAV / RG1SAV := the same.
- **R#7 := RG7SAV** (the probe's $FF / $00 / $A5 came back, with FORCLR / BAKCLR / BDRCLR other values and the VDP's
  R#7 another): not rebuilt from the colours [M xmode2 26; xmode 17].
- **R#2 $06, R#3 $FF, R#4 $03, R#5 $36, R#6 $07** -- as INIGRP -- written to the VDP and the copies (R#5 $3F of
  SCREEN 4 becomes $36) [M xmode2 26; xmode 17]. Example: copies $8F / $FF from SCREEN 4 → `02 67 06 FF 03 36 07 FF`.
- R#9 $02 and R#11 $00 as on entry (from SCREEN 4: not separated).

## Differences from the reference

C-BIOS's MSX2 / MSX2+ builds set R#0-R#6 the same, but [M xmode2 26; xmode 17]: **R#7 is left as the VDP had it**
($04; the references write RG7SAV); A $07, F $00 on return.

## Open (not measured)

Recorded per case: as [CHGMOD](CHGMOD.md#open-not-measured); the -ONLY cases add a whole work-area diff
$F380-$FFFF (only the register copies may differ).

| case | inputs | state | what it separates | HB-F900 | NMS 8250 | FS-A1WSX |
|---|---|---|---|---|---|---|
| IE | — | entered with DI and with EI | interrupt state on return: on after DI: "kept" and "forced off" are excluded; the EI half cannot add a rule | on [M xmode2 26] | on | on |
| SG-ONLY | — | SCRMOD, name table, sprites garbage | "VDP only" by a whole work-area diff (SCRMOD, cells, VRAM, palette measured untouched) | untouched [M xmode2 26] | same | same |
| SG-BASE | cells default / moved / unaligned | R#3 / R#4 / R#10 / R#11 copies garbage | R#3 low bits $FF and R#4 low bits $03 forced vs from the cell | ? | ? | ? |
| SG-R9 | — | from SCREEN 5 (R#9 bit 7 set) | R#9 bit 7 := 0 as SETTXT / SETT32 | ? | ? | ? |
| SG-R89 | — | R#8 bits 1, 3, 5, 6, 7 and R#9 bits 1, 2, 3, 4, 5 each walked alone, copies ≠ VDP | which bits kept, from the copy or the VDP | ? | ? | ? |
| SG-MAIN | main-ROM $007E | same | the *3 claim by a breakpoint on the sub-ROM entry and on EXTROM ($015F) as a call trace | ? | ? | ? |

## Related pages

[The screen-modes page](../concepts/screen-modes.md); [INIGRP](INIGRP.md); MSX1
[SETGRP](../../bios/SETGRP.md).

## Tests that cover it

none yet
