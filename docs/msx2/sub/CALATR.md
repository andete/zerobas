<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `CALATR` (sub-ROM $00FD) — the address of a sprite's attributes

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the HB-F900, NMS 8250 and FS-A1WSX ([xspr2.asm](../../../probes/bios/spec/xspr2.asm), [scratchpad/AE_xspr2_msx2.out](../../../scratchpad/AE_xspr2_msx2.out), decoded by [xspr2_decode.py](../../../scratchpad/xspr2_decode.py)).
> Goldfish pass 1 (test writer) 2026-11-23: 5 findings, 4 measured, 0 moved to open ([xspr3.asm](../../../probes/bios/spec/xspr3.asm), [scratchpad/AE_xspr3_msx2.out](../../../scratchpad/AE_xspr3_msx2.out), decoded by [xspr3_decode.py](../../../scratchpad/xspr3_decode.py)).

## Summary

`CALATR` returns in HL the VRAM address of sprite plane A's four attribute bytes. The handbook
calls it the same routine as the main ROM's CALATR ($0087) ([CALATR](../../bios/CALATR.md)). It
does not return the address of the sprite-mode-2 colour table.

## The specification

Shared facts: [vdp-and-palette.md](../concepts/vdp-and-palette.md).

### Interface

- **In:** A, the sprite number [P A1 CALATR]; ATRBAS ($F928) [M, below].
- **Out:** HL, the address [P A1 CALATR]. AF, DE and HL may change [P A1 CALATR]; measured: A kept, DE = the
  offset 4 x A, BC / IX / IY kept [M].

### Behaviour

- "The same as CALATR in MAIN-ROM" [P A1 CALATR]: ATRBAS + 4 x A, the MSX1 rule, holds [M, below].
- In sprite mode 2 a plane's colour bytes lie at ATRBAS − 512 + 16 x A [P 4§5.3.2]; CALATR returns the
  attribute address there too, never the colour one [M: SCREEN 5 gives $7600 + 4 x A].

**Measured** [M] (the same on all three references; SCREEN 1, 5 and 8):

- HL = ATRBAS + A x 4, a plain 16-bit sum with no mask on A: SCREEN 1 $1B00, $1B04, $1B7C, $1EFC for A 0, 1, 31,
  255; SCREEN 5 $7600 ... $79FC ([AE_xspr2](../../../scratchpad/AE_xspr2_msx2.out)); SCREEN 8 (ATRBAS $FA00) A $FF
  gives $FDFC -- not the 8-bit $FAFC nor the 5-bit-masked $FA7C ([AE_xspr3](../../../scratchpad/AE_xspr3_msx2.out)).
- The base is the ATRBAS cell: ATRBAS := $6E00 in SCREEN 5 gives $6E14 for A 5 (AE_xspr3).
- The sprite size plays no part: A 5 gives $1B14 with RG1SAV bit 1 clear and set (AE_xspr3).
- Out: A kept; DE = 4 x A ($0014, $03FC); BC, IX (the entry address) and IY kept (AE_xspr3).
- F (12 cases): S, P/V and C clear, Z set, then the flags of the 16-bit `ADD HL,DE`: H = the carry out of bit 11
  (never set in the cases), N clear, bits 5 and 3 = those of the result's high byte -- $48 ($1Bxx), $60 ($76xx),
  $68 ($79FC, $6E14, $FDFC) (AE_xspr2, AE_xspr3).

## Differences from the reference

C-BIOS's MSX2 / MSX2+ builds give the same HL, A, F, BC, DE, IX and IY in every case ([AE_xspr2](../../../scratchpad/AE_xspr2_msx2.out), [AE_xspr3](../../../scratchpad/AE_xspr3_msx2.out)).

## Open (not measured)

Recording as in [vdp-and-palette.md](../concepts/vdp-and-palette.md#how-every-case-is-recorded).
Measured and removed: CA-01 (the MSX1 rule at $1B00, $7600, $FA00), CA-02 (16-bit, unmasked), CA-03 (the colour
table never returned), CA-05 (the cell, not the mode's default).

| case | inputs | state | what it separates |
|---|---|---|---|
| CA-02b | A $FF | ATRBAS $FF00 | a 16-bit wrap ($02FC; C set as in CALPAT's wrap) |
| CA-04 | A 5 | ACPAGE 1, DPPAGE 2, SCRMOD 5 | ACPAGE added vs not |
| CA-06 | entry F $00 / $FF; AF' BC' DE' HL' garbage | interrupts on / off; the control call | whether entry F's S / P/V survive; alternate registers; the interrupt state |

## Related pages

[CALPAT](CALPAT.md), [GSPSIZ](GSPSIZ.md), [CLRSPR](CLRSPR.md); the MSX1 call
[CALATR $0087](../../bios/CALATR.md).

## Tests that cover it

None yet.
