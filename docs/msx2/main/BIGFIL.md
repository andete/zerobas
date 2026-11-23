<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `BIGFIL` ($016B) — fill VRAM with a byte, without the 16 KB limit

> **Spec:** DRAFT 0 (2026-11-23), from the published interface only; nothing measured yet. References to measure: HB-F900, NMS 8250, FS-A1WSX.

## Summary

`BIGFIL` fills BC bytes of VRAM, from the address in HL, with A — as [FILVRM](../../bios/FILVRM.md),
but without FILVRM's MSX2 test of the screen mode: FILVRM treats VRAM as 16 KB in SCREEN 0-3, BIGFIL
takes its parameters as given in every mode. Where A16 comes from is not published.

## The specification

**Interface.**
- In: HL = the first VRAM address, BC = the length, A = the byte [P A1]. Out: none [P A1]. Changes:
  AF, BC [P A1].
- It does not test the screen mode; FILVRM does, and treats VRAM as 16 KB in SCREEN 0-3 [P A1].
  So AR-16K is not its rule in SCREEN 0-3 [P A1]; the rest of the rival rules of the
  [shared VRAM address matrix](README.md#the-shared-vram-address-matrix) stay open [A].
- What BC = 0 fills; whether a fill crosses $FFFF into $10000 or wraps to $00000; DE, HL, IX, IY
  kept; the interrupt state [A].

## Differences from the reference

Not measured yet.

## Open (not measured)

The [shared VA cases](README.md#the-shared-vram-address-matrix) VA-1 to VA-16 with HL lowered by 3,
BC $0008 and A $C7: S-MARK marks each rival's 8-byte span and the byte beyond each end, so no marked
byte is $C7 before the call; after it, the spans that read $C7 name the rule, the end bytes that
the length is exact, the block sums that nothing else changed. VA-8 to VA-11 check the
[P A1] statement that BIGFIL does not mask. Plus:

| case | inputs | state | separates | F900 | 8250 | WSX |
|---|---|---|---|---|---|---|
| BF-1 | HL $FFF8, BC $10, A $C7 | S-BASE, every rival's span marked (among them $0FFF8-$1000F and $00000-$00007) | crosses into $10000 vs wraps to $00000 (VDP carry vs a BIOS bank rule: the port log tells which wrote R#14) | ? | ? | ? |
| BF-2 | HL $3FF8, BC $10, A $C7 | S-BASE (entry R#14 $06, a bank neither $0xxxx span uses) | across a 16 KB bank: R#14 after = $06 (put back), $01 (left at the last byte's bank), or the first byte's $00 | ? | ? | ? |
| BF-3 | HL $3FF8, BC $10 | SCREEN 1, R14 $00 | in a 16 KB mode: a wrap to $00000 vs straight on to $04000 | ? | ? | ? |
| BF-4 | HL $8000, BC $0000, A $C7 | S-BASE | BC 0: nothing, or 64 KB (block sums) | ? | ? | ? |
| BF-5 | HL $8000, BC $0001 and $0100, A $C7 | S-BASE, $07FFF and $08001 / $08100 marked | the length is exact | ? | ? | ? |
| BF-6 | as BF-5; A $00 / $FF; DE $9BDF; F $00 / $FF | S-REGS, interrupts off, then on | AF and BC on return (BC 0? A kept?); DE / HL / IX / IY kept; the interrupt state | ? | ? | ? |
| BF-7 | HL $1234, BC $10 | as NSETRD's SR-3 | no other VDP register or save cell written | ? | ? | ? |
| BF-8 | HL $8000, BC $4000 | S-BASE, interrupts on, VDP interrupts enabled | a fill that spans a frame: interrupts taken during it (the H.TIMI handler's count), the fill still exact | ? | ? | ? |
| BF-9 | HL $8000, BC $0100 | S-BASE | stack depth and time (README methods) | ? | ? | ? |

Also open: the display off.

## Related pages

[region page](README.md), [NSETWR](NSETWR.md), [NWRVRM](NWRVRM.md); MSX1 [FILVRM](../../bios/FILVRM.md).

## Tests that cover it

None yet.
