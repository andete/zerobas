<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `BLTVD` (sub-ROM $019D) — draw an array from a disk file

> **Spec:** DRAFT 0 (2026-11-23), from the published interface only; nothing measured yet. References to measure: HB-F900, NMS 8250, FS-A1WSX.

## Summary

`BLTVD` reads an array from the file FNPTR names and draws it at (DX, DY) with LOGOP — BASIC's
`COPY "file" TO (DX,DY)`. The size comes from the file. On a disk error control goes to BASIC's
error handler.

## The specification

The block, the array, the disk forms and the recording:
[block-transfer.md](../concepts/block-transfer.md).

### Interface

- **In:** HL = $F562; FNPTR (the file name's address), DX, DY, CDUMMY (not required), ARG, LOGOP
  in the block; NX / NY from the data [P A3 §3].
- **Out:** carry set when there is an error in the parameters [P A3 §3]. Any register may change
  [P A3 §3]. On an error, control jumps to the BASIC interpreter's error handler; a caller outside
  BASIC hooks H.ERRO to handle it [P A3 §3].

### Behaviour

- The drawing is BLTVM's with the array taken from the file [P A3 §3 lists the same fields; the
  equivalence is A].
- The file's layout, the name's syntax beyond the example, which errors set carry and which go to
  the error handler, and the file left open after an error are [A].

## Differences from the reference

Not measured yet.

## Open (not measured)

Recording as in [block-transfer.md](../concepts/block-transfer.md#how-every-blt-case-is-recorded)
(disk image made by the probe; H.ERRO hooked to record E and return).

| case | inputs | state | what it separates |
|---|---|---|---|
| VD-01 | a file written by BLTDV of a known rectangle | SCREEN 5 | the round trip; the header in the file |
| VD-02 | the same data saved by BSAVE ... ,S and by BLTDM | — | the accepted file layouts |
| VD-03 | name `"A:X.PIC"`, then `X.PIC` unquoted, then no 0 terminator | — | the name syntax; carry vs the error handler |
| VD-04 | a missing file, then a valid call | — | the error number; carry; a leaked FCB / open file shows in the second call |
| VD-05 | a file shorter than its header claims | — | carry ("incorrect size") vs error vs partial draw |
| VD-06 | LOGOP 0-15, $13 | LOGOPR preset different | each operation, the no-op codes, masking; LOGOPR used / written |
| VD-07 | DX odd; DX + NX past the edge; DY 1000 / DY 500 (SCREEN 7 / 8) + NY 50; DX 600 | — | mid-byte rows; clip / wrap / range check / the VRAM end |
| VD-08 | ARG DIX, DIY, bit 5 | file data asymmetric in X and Y | direction; expansion RAM |
| VD-09 | FNPTR pointing inside the block / BUF | — | the name read before the block is reused vs after |
| VD-10 | HL ≠ $F562, a block at HL differing in every byte | — | HL read vs fixed |
| VD-11 | — | SCREEN 1, 4; SCREEN 7, 8 (A3's "/2" for 8); FS-A1WSX SCREEN 10-12 | refused vs run; bytes per dot |
| VD-12 | — | a command running at entry (CE = 1) | waits vs overrides |
| VD-13 | — | no disk ROM (a diskless boot) | error, carry, or crash |
| VD-14 | — | called from MSX-DOS with H.ERRO hooked | the error path outside BASIC |
| VD-15 | — | the block $F55E-$F572 garbage; interrupts on / off; the control call | fields written; the call's interrupt state vs the path's |

## Related pages

[BLTDV](BLTDV.md) (the inverse), [BLTVM](BLTVM.md), [BLTMD](BLTMD.md);
[block-transfer.md](../concepts/block-transfer.md).

## Tests that cover it

None yet.
