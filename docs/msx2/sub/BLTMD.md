<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `BLTMD` (sub-ROM $01A5) — load a disk file into RAM

> **Spec:** DRAFT 0 (2026-11-23), from the published interface only; nothing measured yet. References to measure: HB-F900, NMS 8250, FS-A1WSX.

## Summary

`BLTMD` loads array data from the file FNPTR names into RAM from SPTR to EPTR. It should not touch
VRAM. On a disk error control goes to BASIC's error handler.

## The specification

The block, the disk forms and the recording: [block-transfer.md](../concepts/block-transfer.md).

### Interface

- **In:** HL = $F562; FNPTR at $F562, SPTR (the start) at $F566, EPTR (the end) at $F568; the field
  at $F564 is named SY but is a dummy [P A3 §3].
- **Out:** carry reset [P A3 §3]. Any register may change [P A3 §3]. On an error, control jumps to
  the BASIC interpreter's error handler; a caller outside BASIC hooks H.ERRO [P A3 §3].

### Behaviour

- Whether EPTR is inclusive, what happens when the file is shorter or longer than the range,
  whether the file's header is loaded too, whether a load address in the file overrides SPTR, and
  VRAM left unchanged are [A].

## Differences from the reference

Not measured yet.

## Open (not measured)

Recording as in [block-transfer.md](../concepts/block-transfer.md#how-every-blt-case-is-recorded)
(whole VRAM diffed: the call must not write it), plus RAM from SPTR − 16 to EPTR + 16.

| case | inputs | state | what it separates |
|---|---|---|---|
| MD-01 | a 100-byte file of distinct bytes; EPTR − SPTR 49, 99, 100, 101 | RAM round garbage | stops at EPTR (inclusive / exclusive) vs loads the whole file |
| MD-02 | a file written by BLTDM | — | the round trip; header kept |
| MD-03 | a file written by BSAVE (with its header) | — | the header skipped vs loaded vs its address used |
| MD-04 | EPTR < SPTR; EPTR = SPTR | — | nothing / one byte / error / wrap |
| MD-05 | a missing file, then a valid call | — | the error number; a leaked FCB / open file in the second call |
| MD-06 | SPTR inside the block itself ($F562); FNPTR inside the block / BUF | — | the block and the name read before the load vs during |
| MD-07 | name unquoted / without terminator | — | the name syntax |
| MD-08 | HL ≠ $F562, a block at HL differing in every byte | — | HL read vs fixed |
| MD-09 | — | the block $F55E-$F572 garbage | fields the call writes back |
| MD-10 | — | no disk ROM | error / crash |
| MD-11 | — | called from MSX-DOS with H.ERRO hooked | the error path outside BASIC |
| MD-12 | — | interrupts on / off; entry F carry set; the control call | carry reset; the call's interrupt state vs the path's |

## Related pages

[BLTDM](BLTDM.md) (the inverse), [BLTVD](BLTVD.md); [block-transfer.md](../concepts/block-transfer.md).

## Tests that cover it

None yet.
