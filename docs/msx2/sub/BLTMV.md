<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `BLTMV` (sub-ROM $0199) — copy a VRAM rectangle to an array in RAM

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the HB-F900, NMS 8250 and FS-A1WSX ([xsubblt.asm](../../../probes/bios/spec/xsubblt.asm), [scratchpad/AE_xsubblt_msx2.out](../../../scratchpad/AE_xsubblt_msx2.out), decoded by [xsubblt_decode.py](../../../scratchpad/xsubblt_decode.py)). `[B n]` = that run's case n (cases 6-13 added by goldfish pass 1; every case records S#2 as the debugger reads it right after the call returns, before the probe's own wait for the engine). Every reading below is the same on all three references.
>
> Goldfish pass 1 (test writer) 2026-11-23: 3 findings, 2 measured, 0 moved to open.

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

**Measured** [M] (SCREEN 8): the array at DPTR is NX (2 bytes), NY (2 bytes), then the NX x NY dots row by row
((8, 8) 8 x 4 -> $0008 $0004 + 32 bytes) [M B 3, 10, 13]; **nothing written in the 60 bytes past it** ($EE preset
over $D224-$D25F, all kept) [M B 10]; the 16 x 6 VRAM window round the source ((4, 7)-(19, 12)) unchanged [M B 11]
(the rest of VRAM was not read); the block left as given; A $00, F $44; CE = 0 on return; interrupts ON on return,
entered with DI, through EXTROM and through SUBROM [M B 3, 10, 11, 13].

## Differences from the reference

C-BIOS's MSX2 / MSX2+ builds write the header and **only 31 of the 32 dots** -- the last one ($47) is missing, the
byte after the 4 + 31 left as it was, through EXTROM and SUBROM alike [B 3, 10, 13]; A / F differ ([scratchpad/AE_xsubblt_msx2.out](../../../scratchpad/AE_xsubblt_msx2.out)).

## On the turbo R

Measured 2026-11-23 (D-TRSPEC) on the FS-A1GT / FS-A1ST: every case gives the same bytes as on the FS-A1WSX, on both models except VDP S#2, which the probe reads at a random moment (timing) [M] ([AE_trall/xsubblt.out](../../../scratchpad/AE_trall/xsubblt.out); overview: [turbor/remeasured.md](../../turbor/remeasured.md)).

## Open (not measured)

Recording as in [block-transfer.md](../concepts/block-transfer.md#how-every-blt-case-is-recorded)
(whole VRAM diffed: the call must not write it), plus RAM at DPTR and 32 bytes beyond.
MV-08 (SCREEN 8: a byte per dot) is measured (B 3, 10).

| case | inputs | state | what it separates |
|---|---|---|---|
| MV-01 | NX 8, NY 4 | SCREEN 5 | header written; exact length; nothing past it; VRAM untouched — in SCREEN 5 (SCREEN 8 measured, B 10, 11; there only a window of VRAM was read) |
| MV-02 | NX 7, NY 3 | SCREEN 5, 6 | 11 vs 12 data bytes (SCREEN 5): rounded over the array vs per row |
| MV-02b | SX odd (SCREEN 5), SX mod 4 = 1, 3 (SCREEN 6) | — | a row starting mid-byte; logical vs high-speed read |
| MV-03 | $F570 = $13, $40 | — | ignored (as listed) vs applied |
| MV-04 | ARG DIX, DIY | source asymmetric in X and Y | the order of the dots in the array |
| MV-04b | ARG bit 4 (MXS), bits 0 / 1 / 6 / 7 | — | source in expansion RAM; other bits ignored |
| MV-05 | SY 200 + NY 100; SY 1000 + NY 50; SY 500 + NY 50 in SCREEN 7 / 8 | ACPAGE 1, DPPAGE 2 | source page crossing (absolute vs page-relative); the VRAM end |
| MV-05b | SX 600, SY 1100 | SCREEN 5 | range check vs the VDP's masking |
| MV-06 | NX 0, NY 0 (separately) | — | carry; header written |
| MV-07 | DPTR ending at $DFFF; DPTR inside the block / BUF | — | the end written exactly; the block read before the writes vs overwritten mid-call |
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
