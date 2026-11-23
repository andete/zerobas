<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `SETTXT` (sub-ROM $00E5) — set the VDP to the text mode, only

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the HB-F900, NMS 8250 and FS-A1WSX ([xmode.asm](../../../probes/bios/spec/xmode.asm), [scratchpad/AE_xmode_msx2.out](../../../scratchpad/AE_xmode_msx2.out), decoded by [scratchpad/xmode_decode.py](../../../scratchpad/xmode_decode.py) into [scratchpad/AE_xmode_msx2_decoded.out](../../../scratchpad/AE_xmode_msx2_decoded.out); round 2 [xmode2.asm](../../../probes/bios/spec/xmode2.asm), [scratchpad/AE_xmode2_msx2.out](../../../scratchpad/AE_xmode2_msx2.out), decoded by [scratchpad/xmode2_decode.py](../../../scratchpad/xmode2_decode.py) into [scratchpad/AE_xmode2_msx2_decoded.out](../../../scratchpad/AE_xmode2_msx2_decoded.out)).
>
> Goldfish pass 1 (test writer) 2026-11-23: 13 findings, 10 measured, 3 moved to open.

## Summary

`SETTXT` programs the VDP for the SCREEN 0 text mode from the same cells as [INITXT](INITXT.md),
without the rest of INITXT's work (no clear, no cursor, no width). Shared facts:
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
- In: TXTNAM, TXTCGP [P App. 1, SUB-ROM SETTXT]; **LINLEN** (not LINL40) chooses TEXT 1 / TEXT 2; the copies
  RG0SAV-RG7SAV and RG9SAV (below). Not inputs: A, F, SCRMOD [M xmode2 23, 24, 32].
- Out: **A $00, F $44** whatever A / F were on entry ($FF / $FF here; SETMLT also $00 / $00) [M xmode2 23, 24, 32; xmode
  15]; BC, DE, HL changed; IX the entry; IY and the alternates kept [M xmode2 23, 24, 32].
- Interrupts on return: **ON**, after a DI and after an EI entry [M xmode2 23, 24; xmode 15].

**Behaviour.**
- Sets the VDP to "the text mode (40x24)" [P App. 1, SUB-ROM SETTXT] -- **TEXT 2 when LINLEN is 80** (LINL40 37),
  TEXT 1 with LINLEN 20 / 37 even when LINL40 is 80: SETTXT reads LINLEN where INITXT reads LINL40 [M xmode2 23, 24,
  32]. The threshold between 37 and 80 is open (ST-W).
- **Only the VDP and the copies change**: SCRMOD, OLDSCR, LINLEN, NAMBAS..ATRBAS, the cursor, the palette and VRAM
  are left as found -- SCRMOD stays 5 after SCREEN 5 (VRAM read in case 23 only) [M xmode2 23, 24, 32].
- **R#0** := RG0SAV AND $F1 OR the mode's bits; **R#1** := RG1SAV AND $E7 OR the mode's M1 / M2: the screen-on,
  interrupt and size bits come from the copy -- RG1SAV $00 leaves the screen **off**, $FF on (bit 7 stays in the
  copy, the VDP keeps $7F) [M xmode2 23, 24]. The copies RG0SAV / RG1SAV := the same.
- **R#7 := RG7SAV** (the probe's $FF / $00 / $A5 came back, with FORCLR / BAKCLR / BDRCLR other values and the VDP's
  R#7 another): not rebuilt from the colours [M xmode2 23, 24, 32; xmode 15].
- **R#2 $00, R#3 := RG3SAV, R#4 $01, R#5 := RG5SAV, R#6 := RG6SAV** in TEXT 1 (the copies $FF / $00 / $A5 came
  back, the VDP held $80 / $EF / $0F from SCREEN 5) [M xmode2 23, 24; xmode 15]; in TEXT 2 R#2 $03, **R#3 $27**, R#4
  $02 (R#3 was $80 in the VDP and the copy before), R#5 / R#6 $36 / $07 as both the copy and the VDP held them
(not separated) [M xmode2 32]. Examples: copies $8F / $FF from SCREEN 5 → `00 77 00 FF 01 FF 3F FF`;
  copies $00 → `00 10 00 00 01 00 00 00` (screen off) [M xmode2 23, 24].
- **R#9** bit 7 := 0 ($82 → $02 from SCREEN 5; RG9SAV too) [M xmode2 23]. R#11 $00 as on entry.

## Differences from the reference

C-BIOS's MSX2 / MSX2+ builds ([scratchpad/AE_xmode2_msx2_decoded.out](../../../scratchpad/AE_xmode2_msx2_decoded.out), `ours`) set R#0-R#2 and R#4 the
same, but [M xmode2 23, 24, 32; xmode 15]:
- **R#3, R#5, R#6, R#7 are left as the VDP had them** (from SCREEN 5: $80 / $EF / $0F / $04; the references write
  the copies). C-BIOS's R#7 $F4 in round 1 was what CHGMOD 0 had left, with RG7SAV still $A5: not written.
- **TEXT 2 (LINLEN 80): R#3 stays $80** where the references write $27 (the blink table).
- **R#9 bit 7 is left set** ($82) after SCREEN 5.
- A $01, F $00 on return (references $00 / $44).

## On the turbo R

Measured 2026-11-23 (D-TRSPEC) on the FS-A1GT / FS-A1ST: every register, VRAM sum and work-area byte is the FS-A1WSX's, on both models. What differs is the machine and the timing, not the call: $FFF8 = $FF as the boot leaves it (the A1WSX $00; no screen-mode call touches it), VDP S#2 read at a random moment, R#36 = $80 before case 0 (the boot's last VDP command), power-on cells, and one JIFFY count in xmode2 case 27 [M] ([AE_trall/xmode.out](../../../scratchpad/AE_trall/xmode.out), [AE_trall/xmode2.out](../../../scratchpad/AE_trall/xmode2.out); overview: [turbor/remeasured.md](../../turbor/remeasured.md)).

## Open (not measured)

Recorded per case: as [CHGMOD](CHGMOD.md#open-not-measured); the -ONLY cases add a whole work-area diff
$F380-$FFFF (only the register copies may differ).

| case | inputs | state | what it separates | HB-F900 | NMS 8250 | FS-A1WSX |
|---|---|---|---|---|---|---|
| IE | — | entered with DI and with EI | interrupt state on return: on after both: forced on ("kept" and "forced off" excluded); nothing left to separate | on [M xmode2 23, 24] | on | on |
| ST-W | LINLEN = 40, 41, 79 with LINL40 ≠ LINLEN | — | the TEXT 2 threshold on LINLEN (≤ 37 TEXT 1, 80 TEXT 2 measured) | ? | ? | ? |
| ST-ONLY | — | SCRMOD 5, cursor / LINLEN / VRAM garbage | "VDP only" by a whole work-area diff (SCRMOD, LINLEN, cells, VRAM, palette measured untouched) | untouched [M xmode2 23] | same | same |
| ST-BASE | TXTNAM / TXTCGP moved | — | R#2 / R#4 from the cells vs constants | ? | ? | ? |
| ST-BLINK | LINLEN 80 | R#10 / R#12 / R#13 copies garbage | blink registers written in TEXT 2 | ? | ? | ? |
| ST-R89 | — | R#8 bits 1, 3, 5, 6, 7 and R#9 bits 1, 2, 3, 4, 5 each walked alone, copies ≠ VDP | which bits kept, from the copy or the VDP | ? | ? | ? |
| ST-MAIN | main-ROM $0078 | same | the *3 claim by a breakpoint on the sub-ROM entry and on EXTROM ($015F) as a call trace | ? | ? | ? |

## Related pages

[The screen-modes page](../concepts/screen-modes.md); [INITXT](INITXT.md); MSX1
[SETTXT](../../bios/SETTXT.md).

## Tests that cover it

none yet
