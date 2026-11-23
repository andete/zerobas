<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `BLTVV` (sub-ROM $0191) — copy a VRAM rectangle within VRAM

> **Spec:** DRAFT 0 (2026-11-23), from the published interface only; nothing measured yet. References to measure: HB-F900, NMS 8250, FS-A1WSX.

## Summary

`BLTVV` copies the NX x NY rectangle at (SX, SY) to (DX, DY), combining each dot with the
destination by LOGOP — BASIC's `COPY` within VRAM. The coordinates are absolute over all pages;
ARG gives the direction.

## The specification

The parameter block, coordinates, ARG, LOGOP and how every case is recorded:
[block-transfer.md](../concepts/block-transfer.md).

### Interface

- **In:** HL = $F562; SX, SY, DX, DY, NX, NY, CDUMMY (not required), ARG, LOGOP in the block
  [P A3 §1].
- **Out:** carry reset [P A3 §1]. Any register may change [P A3 §1].

### Behaviour

- The rectangle is copied with LOGOP, in ARG's direction [P A3 §1; 4§6.3; 4§6.4].
- Which VDP command it issues is [A]: LMMM carries the operation, HMMM / YMMM do not and move
  bytes [P 4§6.2 Table 4.5, 4§6.5.3, 4§6.5.7]. An odd SX / DX in SCREEN 5 with LOGOP 0 separates
  them by the dots; on aligned coordinates only the time does.
- Clipping at the screen edge or the VRAM end, the wait for the command's end, the block and the
  VDP command registers afterwards, and SCREEN 0-4 are [A].

## Differences from the reference

Not measured yet.

## Open (not measured)

Recording as in [block-transfer.md](../concepts/block-transfer.md#how-every-blt-case-is-recorded)
(whole VRAM, the block, LOGOPR, R#32-R#46, time, the control call).

| case | inputs | state | what it separates |
|---|---|---|---|
| BV-01 | SCREEN 5, 16 x 8 rectangle, LOGOP 0, ARG 0 | — | the copy itself |
| BV-02a | SX / DX odd, NX odd, LOGOP 0 | SCREEN 5, 6 | dot-exact (LMMM) vs byte-rounded (HMMM) |
| BV-02b | aligned SX / DX / NX; LOGOP 0, then LOGOP 8 (TIMP, source without colour 0) | SCREEN 5 | same dots; the time tells HMMM for 0 vs LMMM for both |
| BV-03 | LOGOP 1-4, 8-12 | source with colour-0 dots; LOGOPR preset to a different op | each operation; T skips colour 0; LOGOPR used vs ignored vs written |
| BV-04 | LOGOP 5, 6, 7, 13, $13, $40, $FF | — | no-op codes; bits 4-7 masked ($13 acts as 3) vs passed ($40: high-speed only if unmasked) |
| BV-05 | ARG DIX, DIY, both | overlapping rectangles; data asymmetric in X and Y | direction obeyed; overlap result |
| BV-06 | DY 200, NY 100 | SCREEN 5 | crosses into page 1 (absolute) vs clipped vs wrapped |
| BV-07 | DX 200, NX 100 | SCREEN 5 (width 256) | clipped at X 255 vs wrapped in the line |
| BV-08 | DY 1000, NY 50 | SCREEN 5 | the VRAM end: clipped (NY left reduced, [P 4§6.7 Table 4.7 #]) vs wrapped to line 0 |
| BV-08b | DY 500, NY 50 | SCREEN 7, 8 | the same at Y 511 |
| BV-09 | SY in page 0, DY in page 3; then SY in page 2, DY in page 0 | ACPAGE 1, DPPAGE 2 | coordinates absolute vs ACPAGE / DPPAGE added, on either side |
| BV-10 | DX 600, DY 1100, SX 520 | SCREEN 5 / 7 | range check (carry, nothing done) vs the VDP's masking |
| BV-11 | HL ≠ $F562, a block at HL differing in every byte | — | HL read vs the fixed address |
| BV-12 | ARG bit 4, bit 5, bits 0 / 1 / 6 / 7 | — | expansion RAM selected; the other bits ignored vs passed to R#45 |
| BV-13a | NX 0, NY 0 (separately) | — | nothing copied vs a full-width / full-height transfer |
| BV-14 | — | SCREEN 1, 4 | refused (carry?) vs run anyway |
| BV-14b | — | FS-A1WSX: SCREEN 1 with commands enabled by its extra register; SCREEN 10-12 | the MSX2+ VDP's extras honoured |
| BV-15 | — | a command running at entry (CE = 1) | waits vs overrides |
| BV-16 | — | entry F carry set; registers garbage; interrupts on / off; the control call | carry reset; interrupt state of the call vs the path; return before / after CE = 0 |
| BV-17 | — | SCREEN 7, 8 | 512-wide / byte-per-dot coordinates |

## Related pages

[BLTVM](BLTVM.md), [BLTMV](BLTMV.md), [BLTVD](BLTVD.md); [block-transfer.md](../concepts/block-transfer.md).

## Tests that cover it

None yet.
