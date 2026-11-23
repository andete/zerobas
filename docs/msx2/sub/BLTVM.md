<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `BLTVM` (sub-ROM $0195) — copy an array from RAM to VRAM

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the HB-F900, NMS 8250 and FS-A1WSX ([xsubblt.asm](../../../probes/bios/spec/xsubblt.asm), [scratchpad/AE_xsubblt_msx2.out](../../../scratchpad/AE_xsubblt_msx2.out), decoded by [xsubblt_decode.py](../../../scratchpad/xsubblt_decode.py)). `[B n]` = that run's case n (cases 6-13 added by goldfish pass 1; every case records S#2 as the debugger reads it right after the call returns, before the probe's own wait for the engine). Every reading below is the same on all three references.
>
> Goldfish pass 1 (test writer) 2026-11-23: 2 findings, 2 measured, 0 moved to open.

## Summary

`BLTVM` draws an array from RAM at (DX, DY) on the screen, combining it with LOGOP. The array
carries its own size: its first four bytes are NX and NY. It sets the carry when the data's size
is wrong.

## The specification

The parameter block, the array format, ARG, LOGOP and the recording:
[block-transfer.md](../concepts/block-transfer.md).

### Interface

- **In:** HL = $F562; DPTR (the array's address), DX, DY, CDUMMY (not required), ARG, LOGOP in
  the block; NX / NY are taken from the array's first four bytes [P A3 §2].
- **Out:** carry set "when the number of data bytes to be transferred is incorrect" [P A3 §2].
  Any register may change [P A3 §2].

### Behaviour

- The dots after the 4-byte header drawn as an NX x NY rectangle at (DX, DY) [P A3 §2].
- What "incorrect" means — NX or NY zero, beyond the screen, a size overflowing 16 bits — and
  whether anything is drawn then, are [A].
- Whether NX / NY are copied into the block, dot packing, a mid-byte DX, and the direction bits are
  [A].

**Measured** [M] (SCREEN 8, through EXTROM): the array at DPTR (NX 4, NY 2, 8 dots) lands at (DX, DY) [M B 4].
**NX / NY come from the array's header and are WRITTEN to the block** ($F56A / $F56C := 4 / 2): with the block's
NX / NY preset to $33 / $11 the same 4 x 2 dots land and the block ends 4 / 2 [M B 9]. The rest of the block as
given; A $00, F $44; CE = 0 on return (the data pass through the CPU, so the transfer has ended); interrupts ON on
return, entered with DI [M B 4, 9].

## Differences from the reference

C-BIOS's MSX2 / MSX2+ builds draw the same dots and fill NX / NY the same, but also write CDUMMY ($F56E) := $A1 (the
first dot) and return other A / F ([scratchpad/AE_xsubblt_msx2.out](../../../scratchpad/AE_xsubblt_msx2.out)).

## Open (not measured)

Recording as in [block-transfer.md](../concepts/block-transfer.md#how-every-blt-case-is-recorded),
plus the RAM round the array.

| case | inputs | state | what it separates |
|---|---|---|---|
| BM-01 | array NX 8, NY 4; block NX / NY garbage | SCREEN 5 | the header used, the block's ignored, in SCREEN 5 (measured in SCREEN 8, B 9) |
| BM-02 | NX 7, NY 3 | SCREEN 5, 6 | packing of a row's last dot; row-to-row continuation |
| BM-02b | DX odd (SCREEN 5), DX mod 4 = 1, 3 (SCREEN 6) | — | a row starting mid-byte; logical vs high-speed transfer |
| BM-03a | NX 0 | — | carry; anything drawn |
| BM-03b | NY 0 | — | the same, apart from NX |
| BM-03c | NX 300 | SCREEN 5 (width 256) | geometry bound: carry vs clipped vs wrapped |
| BM-03d | NX 256, NY 600 | SCREEN 5 | NX x NY overflowing 16 bits: carry vs a wrapped size |
| BM-04 | DX + NX past the edge; DY 1000 + NY 50; DY 500 + NY 50 in SCREEN 7 / 8 | — | clipped vs wrapped vs carry; the VRAM end |
| BM-04b | DX 600, DY 1100 | SCREEN 5 | range check vs the VDP's masking |
| BM-05 | LOGOP 0-15, $13 | destination non-zero; array with colour-0 dots; LOGOPR preset different | each operation; no-op codes; masking; LOGOPR used / written |
| BM-06 | ARG DIX, DIY | array asymmetric in X and Y | filled right-to-left / bottom-up vs ignored |
| BM-06b | ARG bit 5 (MXD), bits 0 / 1 / 6 / 7 | — | destination in expansion RAM; other bits ignored |
| BM-07 | array overlapping the block / BUF ($F55E-$F65F); array ending at $DFFF | — | the block read before the data vs during; the array's end read exactly |
| BM-08 | — | SCREEN 8 vs 7 | bytes per dot: A3's size formula vs one per dot |
| BM-09 | — | the block $F562-$F570 after the call | which fields the call writes |
| BM-10 | HL ≠ $F562, a block at HL differing in every byte | — | HL read vs fixed |
| BM-11 | — | SCREEN 1, 4; FS-A1WSX SCREEN 10-12 and its command-enable register | refused vs run |
| BM-12 | — | a command running at entry (CE = 1) | waits vs overrides |
| BM-13 | — | entry F carry set / clear; interrupts on / off; the control call | carry's only cause; the call's interrupt state vs the path's |

## Related pages

[BLTMV](BLTMV.md) (the inverse), [BLTVV](BLTVV.md), [BLTVD](BLTVD.md);
[block-transfer.md](../concepts/block-transfer.md).

## Tests that cover it

None yet.
