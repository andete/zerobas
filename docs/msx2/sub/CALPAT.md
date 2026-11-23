<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `CALPAT` (sub-ROM $00F9) — the address of a sprite pattern

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the HB-F900, NMS 8250 and FS-A1WSX ([xspr2.asm](../../../probes/bios/spec/xspr2.asm), [scratchpad/AE_xspr2_msx2.out](../../../scratchpad/AE_xspr2_msx2.out), decoded by [xspr2_decode.py](../../../scratchpad/xspr2_decode.py)).
> Goldfish pass 1 (test writer) 2026-11-23: 8 findings, 5 measured, 1 moved to open ([xspr3.asm](../../../probes/bios/spec/xspr3.asm), [scratchpad/AE_xspr3_msx2.out](../../../scratchpad/AE_xspr3_msx2.out), decoded by [xspr3_decode.py](../../../scratchpad/xspr3_decode.py)).

## Summary

`CALPAT` returns in HL the VRAM address of sprite pattern A. The handbook calls it the same
routine as the main ROM's CALPAT ($0084), whose measured MSX1 behaviour is PATBAS plus A times 8
or 32 bytes ([CALPAT](../../bios/CALPAT.md)).

## The specification

Shared facts: [vdp-and-palette.md](../concepts/vdp-and-palette.md).

### Interface

- **In:** A, the sprite (pattern) number [P A1 CALPAT]; RG1SAV bit 1, the size [M, below]; PATBAS ($F926) [M].
- **Out:** HL, the address [P A1 CALPAT]. AF, DE and HL may change [P A1 CALPAT]; measured: A = the size in
  bytes, DE = the offset, BC / IX / IY kept [M].
- "The same as CALPAT in MAIN-ROM" [P A1 CALPAT]: the MSX1 rule (PATBAS + A x size, size from RG1SAV bit 1,
  A := size, DE := offset) holds through the sub-ROM [M, below].

### Behaviour

**Measured** [M] (the same on all three references; SCREEN 1, 5 and 7):

- HL = PATBAS + A x 8 (RG1SAV bit 1 clear) or A x 32 (set) -- a plain 16-bit sum with no mask on A: A $FF at
  16 x 16 gives $57E0 in SCREEN 1 ($3800 + $1FE0), $97E0 in SCREEN 5 ([AE_xspr2](../../../scratchpad/AE_xspr2_msx2.out)).
  In SCREEN 7 (PATBAS $F000) the sum WRAPS at 16 bits: $F000 + $1FE0 = $0FE0, carry set ([AE_xspr3](../../../scratchpad/AE_xspr3_msx2.out)).
- The base is the PATBAS cell, not the mode's default: PATBAS := $6000 in SCREEN 5 gives $6018 for A 3 (the
  default would give $7818) (AE_xspr3).
- The size is RG1SAV's bit 1, not the VDP's R#1: with R#1 written through port $99 to the opposite size, A 3
  gives $3818 (RG1SAV 8 x 8) and $3860 (RG1SAV 16 x 16) (AE_xspr3).
- Out: A = the size in bytes ($08 / $20); DE = the offset (A x size: $0018, $0060, $1FE0); BC, IX (the entry
  address, as passed to EXTROM) and IY kept (AE_xspr3).
- F (21 cases): S and P/V clear; Z set for 8 x 8 and clear for 16 x 16; then the flags of a 16-bit `ADD HL,DE`
  -- H = the carry out of bit 11, N clear, C = the carry out of bit 15, bits 5 and 3 = those of the result's high
  byte. E.g. $68 ($3800, 8 x 8), $28 ($3820, 16 x 16), $10 ($57E0: H set), $09 ($0FE0: C set) (AE_xspr2, AE_xspr3).
- Whether ACPAGE enters the sum in SCREEN 7 / 8 is [A] (CP-03).

## Differences from the reference

C-BIOS's MSX2 / MSX2+ builds give the same HL, A, F, BC, DE, IX and IY in every case ([AE_xspr2](../../../scratchpad/AE_xspr2_msx2.out), [AE_xspr3](../../../scratchpad/AE_xspr3_msx2.out)).

## On the turbo R

Measured 2026-11-23 (D-TRSPEC) on the FS-A1GT / FS-A1ST: every case gives the same bytes as on the FS-A1WSX, on both models [M] ([AE_trall/xspr2.out](../../../scratchpad/AE_trall/xspr2.out), [AE_trall/xspr3.out](../../../scratchpad/AE_trall/xspr3.out); overview: [turbor/remeasured.md](../../turbor/remeasured.md)).

## Open (not measured)

Recording as in [vdp-and-palette.md](../concepts/vdp-and-palette.md#how-every-case-is-recorded)
(the VDP snapshot and port log are not needed: a pure computation, but the whole-RAM diff is).
Measured and removed: CP-01 (the MSX1 rule), CP-02 (the 16-bit wrap, in SCREEN 7 where $F000 is the default; the
cell-vs-default question is answered separately in SCREEN 5), CP-04 (RG1SAV vs R#1), CP-05 (SCREEN 1 vs 5).

| case | inputs | state | what it separates |
|---|---|---|---|
| CP-03 | A 3 | SCRMOD 7, ACPAGE 1, DPPAGE 0 | ACPAGE added vs not |
| CP-04b | A 3 | RG1SAV's size bit and another RAM copy of R#1 (none is known; CHGMOD's own cache, if any) disagree | RG1SAV vs another RAM cell |
| CP-06 | entry F $00 / $FF; AF' BC' DE' HL' garbage | interrupts on / off; the control call | whether entry F's S / P/V survive (all cases entered with the same F); alternate registers; interrupt state |

## Related pages

[CALATR](CALATR.md), [GSPSIZ](GSPSIZ.md), [CLRSPR](CLRSPR.md); the MSX1 call
[CALPAT $0084](../../bios/CALPAT.md).

## Tests that cover it

None yet.
