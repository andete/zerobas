<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `GSPSIZ` (sub-ROM $0101) — the current sprite size

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the HB-F900, NMS 8250 and FS-A1WSX ([xspr2.asm](../../../probes/bios/spec/xspr2.asm), [scratchpad/AE_xspr2_msx2.out](../../../scratchpad/AE_xspr2_msx2.out), decoded by [xspr2_decode.py](../../../scratchpad/xspr2_decode.py)).
> Goldfish pass 1 (test writer) 2026-11-23: 6 findings, 4 measured, 1 moved to open ([xspr3.asm](../../../probes/bios/spec/xspr3.asm), [scratchpad/AE_xspr3_msx2.out](../../../scratchpad/AE_xspr3_msx2.out), decoded by [xspr3_decode.py](../../../scratchpad/xspr3_decode.py)).

## Summary

`GSPSIZ` returns the sprite pattern's size in bytes — 8 for 8 x 8 sprites, 32 for 16 x 16 — and
sets the carry for 16 x 16. The handbook calls it the same routine as the main ROM's GSPSIZ ($008A)
([GSPSIZ](../../bios/GSPSIZ.md)). The other pages use it as the control call.

## The specification

Shared facts: [vdp-and-palette.md](../concepts/vdp-and-palette.md).

### Interface

- **In:** none [P A1 GSPSIZ]. The source of the size is RG1SAV bit 1 [M, below; P 4§5.2.2 for R#1's bit].
- **Out:** A, the sprite size; carry set only for 16 x 16 [P A1 GSPSIZ]. Only AF changes [P A1 GSPSIZ;
  M for BC, DE, HL, IX, IY].

### Behaviour

**Measured** [M] (the same on all three references, SCREEN 1 and 5):

- A = the pattern's size in BYTES, $08 for 8 x 8 and $20 for 16 x 16 (not the pixel size 8 / 16), carry set for
  16 x 16 ([AE_xspr2](../../../scratchpad/AE_xspr2_msx2.out)).
- The size is RG1SAV's bit 1, not the VDP's R#1: with R#1 written through port $99 to the opposite size, A follows
  RG1SAV ([AE_xspr3](../../../scratchpad/AE_xspr3_msx2.out)).
- Magnification (RG1SAV bit 0) is ignored: RG1SAV $61 gives $08, $63 gives $20 (AE_xspr3).
- The sprite mode plays no part (SCREEN 1 and 5 give the same) (AE_xspr2).
- F = $48 (8 x 8) / $49 (16 x 16): Z and bit 3 set, S / H / P/V / N / bit 5 clear, C = the size (8 cases)
  (AE_xspr2, AE_xspr3).
- BC, DE, HL, IX (the entry address) and IY kept; RG1SAV not written (AE_xspr2, AE_xspr3).

## Differences from the reference

C-BIOS's MSX2 / MSX2+ builds give the same A, F and registers in every case ([AE_xspr2](../../../scratchpad/AE_xspr2_msx2.out), [AE_xspr3](../../../scratchpad/AE_xspr3_msx2.out)).

## On the turbo R

Measured 2026-11-23 (D-TRSPEC) on the FS-A1GT / FS-A1ST: every case gives the same bytes as on the FS-A1WSX, on both models [M] ([AE_trall/xspr2.out](../../../scratchpad/AE_trall/xspr2.out), [AE_trall/xspr3.out](../../../scratchpad/AE_trall/xspr3.out); overview: [turbor/remeasured.md](../../turbor/remeasured.md)).

## Open (not measured)

Recording as in [vdp-and-palette.md](../concepts/vdp-and-palette.md#how-every-case-is-recorded).
Because this call is the other pages' control, its own register and interrupt results are
measured first. Measured and removed: GS-01 (A 8 / 32; bit 0 ignored), GS-02 (RG1SAV vs R#1), GS-03 (the sprite
mode).

| case | inputs | state | what it separates |
|---|---|---|---|
| GS-02b | — | RG1SAV's size bit and another RAM copy of R#1 (none is known; CHGMOD's own cache, if any) disagree | RG1SAV vs another RAM cell |
| GS-04 | entry F $00 / $FF; AF' BC' DE' HL' garbage | interrupts on / off | whether F's Z / bit 3 are constants or survive from entry (every case was entered with the same F); the alternate registers; the EXTROM path's interrupt state |

## Related pages

[CALPAT](CALPAT.md), [CALATR](CALATR.md), [CLRSPR](CLRSPR.md); the MSX1 call
[GSPSIZ $008A](../../bios/GSPSIZ.md).

## Tests that cover it

None yet.
