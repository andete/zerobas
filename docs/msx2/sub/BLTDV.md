<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `BLTDV` (sub-ROM $01A1) — save a VRAM rectangle to a disk file

> **Spec:** DRAFT 0 (2026-11-23), from the published interface only; nothing measured yet. References to measure: HB-F900, NMS 8250, FS-A1WSX.

## Summary

`BLTDV` writes the NX x NY rectangle at (SX, SY) to the file FNPTR names, as an array — BASIC's
`COPY (SX,SY)-STEP(...) TO "file"`. It should leave VRAM as it was. On a disk error control goes
to BASIC's error handler.

## The specification

The block, the array, the disk forms and the recording:
[block-transfer.md](../concepts/block-transfer.md).

### Interface

- **In:** HL = $F562; SX, SY, FNPTR, NX, NY, CDUMMY (not required) in the block [P A3 §3]. ARG and
  LOGOP are not listed [P A3 §3].
- **Out:** carry reset [P A3 §3]. Any register may change [P A3 §3]. On an error, control jumps to
  the BASIC interpreter's error handler; a caller outside BASIC hooks H.ERRO [P A3 §3].

### Behaviour

- The file's contents and layout, VRAM left unchanged, whether an existing file is replaced, and
  the file's state after an error are [A].

## Differences from the reference

Not measured yet.

## Open (not measured)

Recording as in [block-transfer.md](../concepts/block-transfer.md#how-every-blt-case-is-recorded)
(whole VRAM diffed; the file read back byte for byte).

| case | inputs | state | what it separates |
|---|---|---|---|
| DV-01 | NX 8, NY 4 | SCREEN 5 | the file's exact bytes and length; VRAM untouched |
| DV-02 | NX 7, NY 3 | SCREEN 5, 6 | rounded over the array vs per row |
| DV-02b | SX odd (SCREEN 5), SX mod 4 = 1, 3 (SCREEN 6) | — | a row starting mid-byte |
| DV-03 | an existing file of the same name, longer | — | replaced (truncated) vs overwritten in place |
| DV-04 | ARG $F56F set (DIX, DIY, bit 4) | source asymmetric | ignored (not listed) vs obeyed |
| DV-05 | a write-protected / full disk, then a valid call | — | the error; the directory left; a leaked FCB / open file in the second call |
| DV-06 | SY 200 + NY 100; SY 1000 / 500 (SCREEN 7 / 8) + NY 50; SX 600 | ACPAGE 1, DPPAGE 2 | page crossing; the VRAM end; range check vs masking |
| DV-07 | name unquoted / without terminator; FNPTR inside the block / BUF | — | the name syntax; the name read before the block is reused |
| DV-08 | HL ≠ $F562, a block at HL differing in every byte | — | HL read vs fixed |
| DV-09 | — | SCREEN 1, 4; SCREEN 7, 8 (the "/2" size); FS-A1WSX SCREEN 10-12 | refused vs run; bytes per dot in the file |
| DV-10 | — | a command running at entry (CE = 1) | waits vs overrides |
| DV-11 | — | no disk ROM | error / crash |
| DV-12 | — | called from MSX-DOS with H.ERRO hooked | the error path outside BASIC |
| DV-13 | — | the block, BUF, and RAM below HIMEM after the call | what the call uses as a buffer; fields written back |
| DV-14 | — | entry F carry set; interrupts on / off; the control call | carry reset; the call's interrupt state vs the path's |

## Related pages

[BLTVD](BLTVD.md) (the inverse), [BLTMV](BLTMV.md), [BLTDM](BLTDM.md);
[block-transfer.md](../concepts/block-transfer.md).

## Tests that cover it

None yet.
