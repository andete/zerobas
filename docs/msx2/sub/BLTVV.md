<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `BLTVV` (sub-ROM $0191) — copy a VRAM rectangle within VRAM

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the HB-F900, NMS 8250 and FS-A1WSX ([xsubblt.asm](../../../probes/bios/spec/xsubblt.asm), [scratchpad/AE_xsubblt_msx2.out](../../../scratchpad/AE_xsubblt_msx2.out), decoded by [xsubblt_decode.py](../../../scratchpad/xsubblt_decode.py)). `[B n]` = that run's case n (cases 6-13 added by goldfish pass 1; every case records S#2 as the debugger reads it right after the call returns, before the probe's own wait for the engine). Every reading below is the same on all three references.
>
> Goldfish pass 1 (test writer) 2026-11-23: 5 findings, 3 measured, 1 moved to open.

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
- Clipping at the screen edge or the VRAM end, whether the call waits for a command running at entry, the VDP
  command registers afterwards, and SCREEN 0-4 are [A]. (It does not wait for its own command's end: below.)

**Measured** [M] (HL = $F562, through EXTROM unless said):
- The rectangle (SX, SY) NX x NY is copied to (DX, DY) dot for dot [M B 0, 5, 6]. In SCREEN 5 the dots are exact at
  an odd SX, an odd DX and an odd NX together: (9, 8) NX 5 -> (41, 8) over $BC gives $B2 $34 $56 $BC, the dots
  left of DX and right of DX + NX - 1 kept [M B 6] (and from an odd SX to an even DX: pixels 2 3 4 5 land as $23 $45
  [M B 5]).
- LOGOP is applied: 3 (EOR) over $FF turns $10 into $EF [M B 1, SCREEN 8]. That is the one operation measured; the
  others are BV-03 / BV-04.
- **ARG's DIX (bit 2) and DIY (bit 3) run the source and the destination leftwards / upwards from SX / DX, SY / DY,
  as the VDP's command does** [M B 2, 7 (DIX); B 8 (DIY)], and an overlapping copy is then a correct move: SX 15 -> DX 19 (NX 8, DIX)
  and SY 11 -> DY 13 (NY 4, DIY) leave the destination equal to the original source [M B 7, 8]. Copying the same
  rectangles in the normal order would smear them (x 16-19 = the source's x 8-11 again), which the data rule out.
- **The call returns with the command still running:** S#2's CE = 1 on return in every BLTVV case, through EXTROM
  and through SUBROM [M B 0-2, 5-8, 12]. A caller reads the result only after waiting for CE = 0 (the probe does).
- The block is left as given; A $90 / $93 (LOGOP 3), F $94; interrupts ON on return, entered with DI, through
  EXTROM and through SUBROM [M B 0-2, 5-8, 12] — both are main-ROM paths, so whether the call itself or the path
  enables them is not separated [A].

## Differences from the reference

C-BIOS's MSX2 / MSX2+ builds copy the same dots in every case, including the overlapping ones; F after $84. Their
CE on return is 0 in the two SCREEN 5 cases [B 5, 6] (1 in the others)
([scratchpad/AE_xsubblt_msx2.out](../../../scratchpad/AE_xsubblt_msx2.out), `--side ours`).

## On the turbo R

Measured 2026-11-23 (D-TRSPEC) on the FS-A1GT / FS-A1ST: every case gives the same bytes as on the FS-A1WSX, on both models except VDP S#2, which the probe reads at a random moment (timing) [M] ([AE_trall/xsubblt.out](../../../scratchpad/AE_trall/xsubblt.out); overview: [turbor/remeasured.md](../../turbor/remeasured.md)).

## Open (not measured)

Recording as in [block-transfer.md](../concepts/block-transfer.md#how-every-blt-case-is-recorded)
(whole VRAM, the block, LOGOPR, R#32-R#46, time, the control call).
BV-01 is measured in SCREEN 8 and 5 (B 0, 5, 6). BV-02b (HMMM vs LMMM on aligned coordinates) stays open: no dot
separates them there, only the time, which the probe does not record.

| case | inputs | state | what it separates |
|---|---|---|---|
| BV-02a | SX / DX odd, NX odd, LOGOP 0 | SCREEN 6 (SCREEN 5 measured, B 6) | dot-exact (LMMM) vs byte-rounded (HMMM): 4 dots per byte |
| BV-02b | aligned SX / DX / NX; LOGOP 0, then LOGOP 8 (TIMP, source without colour 0) | SCREEN 5 | same dots; the time tells HMMM for 0 vs LMMM for both |
| BV-03 | LOGOP 1-4, 8-12 | source with colour-0 dots; LOGOPR preset to a different op | each operation; T skips colour 0; LOGOPR used vs ignored vs written |
| BV-04 | LOGOP 5, 6, 7, 13, $13, $40, $FF | — | no-op codes; bits 4-7 masked ($13 acts as 3) vs passed ($40: high-speed only if unmasked) |
| BV-05 | ARG DIX and DIY together; DIX with DX < SX | overlapping rectangles; data asymmetric in X and Y | the direction rule where it is not a correct move (DIX / DIY alone with DX > SX / DY > SY measured, B 7, 8) |
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
| BV-16 | — | entry F carry set; registers garbage; interrupts on; a call path that is not the main ROM's (CALSLT to the sub-ROM) | carry reset; the call's own interrupt state vs the path's (on after EXTROM and SUBROM, B 12) |
| BV-17 | — | SCREEN 7, 8 | 512-wide / byte-per-dot coordinates |

## Related pages

[BLTVM](BLTVM.md), [BLTMV](BLTMV.md), [BLTVD](BLTVD.md); [block-transfer.md](../concepts/block-transfer.md).

## Tests that cover it

None yet.
