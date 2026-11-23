<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `BLTMV` (sub-ROM $0199) — copy a VRAM rectangle to an array in RAM

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the HB-F900, NMS 8250 and FS-A1WSX ([xsubblt.asm](../../../probes/bios/spec/xsubblt.asm), [scratchpad/AE_xsubblt_msx2.out](../../../scratchpad/AE_xsubblt_msx2.out), decoded by `scratchpad/xsubblt_decode.py`).

## Summary

`BLTMV` copies the NX x NY rectangle at (SX, SY) into RAM at DPTR as an array: a 4-byte header
with NX and NY, then the dots. It takes no logical operation and should leave VRAM as it was.

## The specification

The parameter block, the array format and the recording:
[block-transfer.md](../concepts/block-transfer.md).

### Interface

- **In:** HL = $F562; SX, SY, DPTR (the destination in RAM), NX, NY, CDUMMY (not required), ARG
  in the block [P A3 §2]. LOGOP is not listed [P A3 §2].
- **Out:** carry reset [P A3 §2]. Any register may change [P A3 §2].

### Behaviour

- The array is written to DPTR [P A3 §2]; that it begins with the 4-byte header is the array
  format [P A3 §2], and that BLTMV writes that header itself is [A].
- VRAM left unchanged, the bytes written past the array's end, ARG's direction, the edge, and what
  a value at $F570 does are [A].

**Measured** [M] (the same on all three references, SCREEN 8): the array at DPTR is NX (2 bytes), NY (2 bytes),
then the NX x NY dots row by row ((8, 8) 8 x 4 -> $0008 $0004 + 32 bytes), nothing written past it; the block left as
given; A $00, F $44, interrupts ON.

## Differences from the reference

C-BIOS's MSX2 / MSX2+ builds write the header and **only 31 of the 32 dots** -- the last one ($47) is missing, the
byte after the 4 + 31 left as it was ([scratchpad/AE_xsubblt_msx2.out](../../../scratchpad/AE_xsubblt_msx2.out)).

## Open (not measured)

Recording as in [block-transfer.md](../concepts/block-transfer.md#how-every-blt-case-is-recorded)
(whole VRAM diffed: the call must not write it), plus RAM at DPTR and 32 bytes beyond.

| case | inputs | state | what it separates |
|---|---|---|---|
| MV-01 | NX 8, NY 4 | SCREEN 5 | header written; exact length; nothing past it; VRAM untouched |
| MV-02 | NX 7, NY 3 | SCREEN 5, 6 | 11 vs 12 data bytes (SCREEN 5): rounded over the array vs per row |
| MV-02b | SX odd (SCREEN 5), SX mod 4 = 1, 3 (SCREEN 6) | — | a row starting mid-byte; logical vs high-speed read |
| MV-03 | $F570 = $13, $40 | — | ignored (as listed) vs applied |
| MV-04 | ARG DIX, DIY | source asymmetric in X and Y | the order of the dots in the array |
| MV-04b | ARG bit 4 (MXS), bits 0 / 1 / 6 / 7 | — | source in expansion RAM; other bits ignored |
| MV-05 | SY 200 + NY 100; SY 1000 + NY 50; SY 500 + NY 50 in SCREEN 7 / 8 | ACPAGE 1, DPPAGE 2 | source page crossing (absolute vs page-relative); the VRAM end |
| MV-05b | SX 600, SY 1100 | SCREEN 5 | range check vs the VDP's masking |
| MV-06 | NX 0, NY 0 (separately) | — | carry; header written |
| MV-07 | DPTR ending at $DFFF; DPTR inside the block / BUF | — | the end written exactly; the block read before the writes vs overwritten mid-call |
| MV-08 | — | SCREEN 8 | bytes per dot |
| MV-09 | then BLTVM of the result | — | the round trip is exact |
| MV-10 | — | the block $F55E-$F572 preset to garbage | which fields the call writes back |
| MV-11 | HL ≠ $F562, a block at HL differing in every byte | — | HL read vs fixed |
| MV-12 | — | SCREEN 1, 4; FS-A1WSX SCREEN 10-12 | refused vs run |
| MV-13 | — | a command running at entry (CE = 1) | waits vs overrides |
| MV-14 | — | entry F carry set; interrupts on / off; the control call | carry reset; the call's interrupt state vs the path's |

## Related pages

[BLTVM](BLTVM.md) (the inverse), [BLTVV](BLTVV.md), [BLTDV](BLTDV.md);
[block-transfer.md](../concepts/block-transfer.md).

## Tests that cover it

None yet.
