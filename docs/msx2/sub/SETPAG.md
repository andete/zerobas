<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `SETPAG` (sub-ROM $013D) — switch the display and active pages

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the HB-F900, NMS 8250 and FS-A1WSX ([xmode.asm](../../../probes/bios/spec/xmode.asm), [scratchpad/AE_xmode_msx2.out](../../../scratchpad/AE_xmode_msx2.out), decoded by [scratchpad/xmode_decode.py](../../../scratchpad/xmode_decode.py) into [scratchpad/AE_xmode_msx2_decoded.out](../../../scratchpad/AE_xmode_msx2_decoded.out); round 2 [xmode2.asm](../../../probes/bios/spec/xmode2.asm), [scratchpad/AE_xmode2_msx2.out](../../../scratchpad/AE_xmode2_msx2.out), decoded by [scratchpad/xmode2_decode.py](../../../scratchpad/xmode2_decode.py) into [scratchpad/AE_xmode2_msx2_decoded.out](../../../scratchpad/AE_xmode2_msx2_decoded.out)).
>
> Goldfish pass 1 (test writer) 2026-11-23: 9 findings, 7 measured, 2 moved to open.

## Summary

`SETPAG` makes DPPAGE the displayed page in the bitmap modes (SCREEN 5-8): it rewrites R#0-R#7 and R#11 from the
copies, SCRMOD and the table cells, with the name table, the sprite attribute table and the sprite pattern table
all moved to the display page. ACPAGE is not applied to any VDP register. Shared facts:
[the screen-modes page](../concepts/screen-modes.md).

## The specification

Case numbers as on [CHGMOD](CHGMOD.md#the-specification): `[M xmode r]` round 1 (records 19-21: SCREEN 5, DPPAGE
1 / 0 / 3, copies $A5), `[M xmode2 n]` round 2 (cases 12-17 and 31: SCREEN 7 / 8 / 5 / 0, DPPAGE 0-4, copies $00
or $8F / $FF, SCRMOD 7 with the VDP in SCREEN 5). The three references agree on every output.

**Interface.**
- In: DPPAGE ($FAF5) the display page, ACPAGE ($FAF6) the active page [P App. 1, SUB-ROM SETPAG]; SCRMOD and
  PATBAS / ATRBAS (below) [M xmode2 16]. A, BC, DE, HL are not inputs.
- Out: **A = SCRMOD** (7 with the VDP in SCREEN 5 and SCRMOD 7; 0 in SCREEN 0) [M xmode2 12-17, 31; xmode 19-21];
  **F as on entry** ($FF and $00 came back) [M xmode2 12, 31]. BC, DE, HL, IX, IY and the alternates kept: "registers:
  AF" [P App. 1, SUB-ROM SETPAG] holds [M xmode2 12-17, 31].
- Interrupts on return: **ON**, after a DI and after an EI entry [M xmode2 12-17; xmode 19-21].

**Behaviour** (SCRMOD 5-8). "page step": $10 / 1 for SCRMOD 5 / 6, $20 / 2 for SCRMOD 7 / 8 -- chosen by SCRMOD, not
by the mode the VDP is in [M xmode2 16].
- **R#2** := DPPAGE · 32 OR $1F, the same in SCREEN 5 and 7 / 8 (64 KB a page there: R#2 bit 5 is A16) [P Ch. 4 §4,
  "Switching the display page"] [M xmode2 12-16, 31; xmode 19-21]. DPPAGE is not masked: DPPAGE 4 gives RG2SAV $9F,
  of which the VDP keeps $1F [M xmode2 15]. The low bits are forced to $1F whatever RG2SAV held ($00, $FF, $A5).
- **R#6** := PATBAS / 2048 + DPPAGE · page step ($10 / $20); **R#11** := ATRBAS / 32768 + DPPAGE · page step (1 / 2);
  **R#5** := (ATRBAS / 128) OR 7, low byte. Written to the copies in full (SCREEN 8, DPPAGE 2: RG6SAV $5E, RG11SAV
  $05); the VDP keeps R#6's low 6 bits and R#11's low 2 [M xmode2 12-16, 31; xmode 19-21]. So the sprite tables
  follow the display page; with SCRMOD 7 and SCREEN 5's cells ($7800 / $7600): R#6 $2F, R#11 $02, R#5 $EF [M xmode2 16].
- **R#0** := RG0SAV AND $F1 OR SCRMOD's mode bits -- SCRMOD 7 with the VDP in SCREEN 5 switches the VDP to GRAPHIC 6
  ($0A) [M xmode2 12, 13, 16; xmode 19-21].
- **R#1** := RG1SAV AND $E7 OR SCRMOD's M1 / M2 (none in 5-8): the display and interrupt bits come from the copy --
  RG1SAV $00 turns the screen **off**, $FF gives $E7 (the VDP keeps $67), $A5 gives $25 [M xmode2 12-14; xmode 19-21].
- **R#3, R#4, R#7** := RG3SAV, RG4SAV, RG7SAV ($00 / $FF / $A5 came back; the VDP keeps R#4's low 6 bits)
  [M xmode2 12, 13; xmode 19-21].
- ACPAGE: no VDP register changes with it -- R#8-R#10, R#12, R#13, R#15, R#16, R#18-R#46 are left as found,
  NAMBAS..ATRBAS unchanged; DPPAGE and ACPAGE stay as set [M xmode2 12-16, 31]. R#14 (VRAM address A16-A14) becomes
  $00 and R#17 (the indirect-register pointer) $18 in every case: whether the call touches VRAM is open (SP-VRAM)
  [M xmode2 12-17, 31].
- The palette is left as found [M xmode2 31].
- **SCREEN 0** (DPPAGE 1, copies $00): the call still rewrites the VDP -- R#0 $00, R#1 $10, R#2 $04, R#3 $00, R#4
  $03, R#5 $00, R#6 $00, R#7 $00, R#11 $00 [M xmode2 17]. The rule (R#2 and R#4 moved by the page? R#5 / R#6 from
  the copies?) is open (SP-LOW).

## Differences from the reference

C-BIOS's MSX2 / MSX2+ builds ([scratchpad/AE_xmode2_msx2_decoded.out](../../../scratchpad/AE_xmode2_msx2_decoded.out), `ours`) write R#2 the same,
but [M xmode2 12-17, 31; xmode 19-21]:
- **R#6 does not follow the page** in SCREEN 5 (stays $0F for DPPAGE 1 / 2 / 3; the references $1F / $2F / $3F); in
  SCREEN 7 it becomes $20 (references $3E) [M xmode2 12, 14, 31; xmode 19, 21].
- **R#11** := DPPAGE · 2 + 1 masked to 2 bits in SCREEN 8 page 2 ($03; the references write $05, of which the VDP keeps
  $01); RG6SAV / RG11SAV other values [M xmode2 13].
- **R#0, R#1, R#3, R#4, R#5, R#7 are not rewritten** from the copies (R#1 stays $60 with RG1SAV $00: the screen
  stays on), and **SCRMOD does not select the mode** (SCRMOD 7 with the VDP in SCREEN 5: the VDP stays GRAPHIC 4,
  R#6 $2F, R#11 $02 as the references) [M xmode2 12, 13, 16].
- **A** := another value (1-4, not SCRMOD), **F $A8** (not kept) [M xmode2 12-17, 31].
- In SCREEN 0 it writes R#2 $3F, R#5 $EF, R#6 $07, R#11 $01 (the references $04, $00, $00, $00) [M xmode2 17].

## Open (not measured)

Recorded per case: as [CHGMOD](CHGMOD.md#open-not-measured); VRAM was not read in the SETPAG cases.

| case | inputs | state | what it separates | HB-F900 | NMS 8250 | FS-A1WSX |
|---|---|---|---|---|---|---|
| IE | DPPAGE 2, ACPAGE 3 | entered once with DI, once with EI | interrupt state on return | on / on [M xmode2 13, 14] | on / on | on / on |
| SP-5 | DPPAGE 0..4, ACPAGE ≠ DPPAGE | SCREEN 5 | R#2 = DPPAGE · 32 OR $1F, unmasked | as stated [M xmode2 14-16, 31; xmode 19-21] | same | same |
| SP-6 | DPPAGE 1, 3 | SCREEN 6 | the SCREEN 5 step ($10 / 1) also in SCREEN 6 | ? | ? | ? |
| SP-7 | DPPAGE 0, 1, 2 | SCREEN 7, 8 | 64 KB step; page 2 written raw | as stated [M xmode2 12, 13] | same | same |
| SP-YJK | DPPAGE 1 | SCREEN 10-12 on the MSX2+ (SCRMOD 10-12) | page step and mode bits for SCRMOD > 8 | ? | ? | ? |
| SP-LOW | DPPAGE 0, 1, 2; copies $00 and $FF | SCREEN 0 (TEXT 1 and 2), 1, 2, 4 | the rule behind SCREEN 0's R#2 $04 / R#4 $03 (page-moved name and pattern bases?) and R#5 / R#6 | ? | ? | ? |
| SP-R1 | RG1SAV $00, $FF, $A5 | SCREEN 5 | R#1 from the copy, M1 / M2 cleared | as stated [M xmode2 12-14] | same | same |
| SP-AC | ACPAGE 0..5 | SCREEN 5 | ACPAGE stored only vs written to NAMBAS / R#45 / R#14 | stored only [M xmode2 12-16] | same | same |
| SP-VRAM | DPPAGE 1 | SCREEN 5, VRAM $5A | VRAM untouched | ? | ? | ? |
| SP-REG | BC, DE, HL distinct | SCREEN 5 | "registers: AF" holds | holds [M xmode2 12-17, 31] | holds | holds |
| SP-R13 | — | R#13 garbage | alternation rate untouched | ? | ? | ? |

## Related pages

[The screen-modes page](../concepts/screen-modes.md); [CLS](CLS.md); [CHGMOD](CHGMOD.md).

## Tests that cover it

none yet
