<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `BLTDM` (sub-ROM $01A9) — save RAM to a disk file

> **Spec:** DRAFT 0 (2026-11-23), from the published interface only; nothing measured yet. References to measure: HB-F900, NMS 8250, FS-A1WSX.

## Summary

`BLTDM` saves the RAM from SPTR to EPTR to the file FNPTR names. It should not touch VRAM. On a
disk error control goes to BASIC's error handler.

## The specification

The block, the disk forms and the recording: [block-transfer.md](../concepts/block-transfer.md).

### Interface

- **In:** HL = $F562; SPTR (the start) at $F562, EPTR (the end) at $F564, FNPTR at $F566
  [P A3 §3]. The order differs from BLTMD's, where FNPTR comes first [P A3 §3].
- **Out:** carry reset [P A3 §3]. Any register may change [P A3 §3]. On an error, control jumps to
  the BASIC interpreter's error handler; a caller outside BASIC hooks H.ERRO [P A3 §3].

### Behaviour

- Whether EPTR is inclusive, whether a header is added to the file, replacing an existing file,
  and VRAM left unchanged are [A].

## Differences from the reference

Not measured yet.

## Open (not measured)

Recording as in [block-transfer.md](../concepts/block-transfer.md#how-every-blt-case-is-recorded)
(whole VRAM diffed; the file read back byte for byte).

| case | inputs | state | what it separates |
|---|---|---|---|
| DM-01 | SPTR $C000, EPTR $C063; every source byte distinct | — | the file's first data byte = (SPTR) locates any header; then length tells inclusive vs not |
| DM-02 | the same, then BLTMD back and BLOAD back | — | the layout BLTMD and BLOAD accept |
| DM-03 | EPTR < SPTR; EPTR = SPTR | — | empty file / one byte / error / wrap |
| DM-04 | an existing longer file | — | replaced vs overwritten in place |
| DM-05 | a full / protected disk, then a valid call | — | the error; the directory left; a leaked FCB / open file |
| DM-06 | SPTR range covering $F562-$F570; FNPTR inside the block / BUF | — | the block saved as at entry vs as the call changed it; the name read before reuse |
| DM-07 | name unquoted / without terminator | — | the name syntax |
| DM-08 | HL ≠ $F562, a block at HL differing in every byte | — | HL read vs fixed |
| DM-09 | — | the block $F55E-$F572 garbage | fields the call writes back |
| DM-10 | — | no disk ROM | error / crash |
| DM-11 | — | called from MSX-DOS with H.ERRO hooked | the error path outside BASIC |
| DM-12 | — | interrupts on / off; entry F carry set; the control call | carry reset; the call's interrupt state vs the path's |

## Related pages

[BLTMD](BLTMD.md) (the inverse), [BLTDV](BLTDV.md); [block-transfer.md](../concepts/block-transfer.md).

## Tests that cover it

None yet.
