<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `CALATR` (sub-ROM $00FD) — the address of a sprite's attributes

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the HB-F900, NMS 8250 and FS-A1WSX ([xspr2.asm](../../../probes/bios/spec/xspr2.asm), [scratchpad/AE_xspr2_msx2.out](../../../scratchpad/AE_xspr2_msx2.out), decoded by `scratchpad/xspr2_decode.py`).

## Summary

`CALATR` returns in HL the VRAM address of sprite plane A's four attribute bytes. The handbook
calls it the same routine as the main ROM's CALATR ($0087) ([CALATR](../../bios/CALATR.md)). It
does not return the address of the sprite-mode-2 colour table.

## The specification

Shared facts: [vdp-and-palette.md](../concepts/vdp-and-palette.md).

### Interface

- **In:** A, the sprite number [P A1 CALATR].
- **Out:** HL, the address [P A1 CALATR]. AF, DE and HL may change [P A1 CALATR].

### Behaviour

- "The same as CALATR in MAIN-ROM" [P A1 CALATR]: ATRBAS + 4 x A, the MSX1 rule, is [A].
- In sprite mode 2 a plane's colour bytes lie at ATRBAS − 512 + 16 x A [P 4§5.3.2]; that CALATR
  returns the attribute address there too, not the colour one, is [A].
- A above 31 (no such plane [P 4§5.1]) is [A].

**Measured** [M] (the same on all three references): HL = ATRBAS + A x 4, a plain 16-bit sum: SCREEN 1 $1B00,
$1B04, $1B7C, $1EFC for A 0, 1, 31, 255; SCREEN 5 $7600 ... $79FC. A kept.

## Differences from the reference

C-BIOS's MSX2 / MSX2+ builds give the same ([scratchpad/AE_xspr2_msx2.out](../../../scratchpad/AE_xspr2_msx2.out)).

## Open (not measured)

Recording as in [vdp-and-palette.md](../concepts/vdp-and-palette.md#how-every-case-is-recorded).

| case | inputs | state | what it separates |
|---|---|---|---|
| CA-01 | A 0, 1, 31 | ATRBAS $1B00, $7600, $FA00 | the MSX1 rule |
| CA-02 | A $FF | ATRBAS $FA00 | 16-bit 4 x A ($FDFC) vs 8-bit A x 4 ($FAFC) vs A masked to 5 bits ($FA7C) |
| CA-02b | A $FF | ATRBAS $FF00 | a 16-bit wrap ($02FC) |
| CA-03 | A 5 | SCRMOD 5 vs 1 | the colour table never returned |
| CA-04 | A 5 | ACPAGE 1, DPPAGE 2, SCRMOD 5 | ACPAGE added vs not |
| CA-05 | A 5 | ATRBAS moved; RG5SAV and $FFEA (R#11's copy) left | the cell vs the register copies |
| CA-06 | entry F $00 / $FF; all registers incl. AF' BC' DE' HL' garbage | interrupts on / off; the control call | F, DE, kept registers, the interrupt state |

## Related pages

[CALPAT](CALPAT.md), [GSPSIZ](GSPSIZ.md), [CLRSPR](CLRSPR.md); the MSX1 call
[CALATR $0087](../../bios/CALATR.md).

## Tests that cover it

None yet.
