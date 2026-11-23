<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `CALPAT` (sub-ROM $00F9) — the address of a sprite pattern

> **Spec:** DRAFT 0 (2026-11-23), from the published interface only; nothing measured yet. References to measure: HB-F900, NMS 8250, FS-A1WSX.

## Summary

`CALPAT` returns in HL the VRAM address of sprite pattern A. The handbook calls it the same
routine as the main ROM's CALPAT ($0084), whose measured MSX1 behaviour is PATBAS plus A times 8
or 32 bytes ([CALPAT](../../bios/CALPAT.md)).

## The specification

Shared facts: [vdp-and-palette.md](../concepts/vdp-and-palette.md).

### Interface

- **In:** A, the sprite (pattern) number [P A1 CALPAT].
- **Out:** HL, the address [P A1 CALPAT]. AF, DE and HL may change [P A1 CALPAT].
- "The same as CALPAT in MAIN-ROM" [P A1 CALPAT]: the MSX1 rule (PATBAS + A x size, size from
  RG1SAV bit 1, A := size, DE := offset) carrying over is [A].

### Behaviour

- Whether the result is a 16-bit sum (wrapping at $FFFF) in SCREEN 7 / 8, whose pattern table is
  at $F000 [P A5 SCREEN 7, 8], and whether ACPAGE enters it, are [A].

## Differences from the reference

Not measured yet.

## Open (not measured)

Recording as in [vdp-and-palette.md](../concepts/vdp-and-palette.md#how-every-case-is-recorded)
(the VDP snapshot and port log are not needed: a pure computation, but the whole-RAM diff is).

| case | inputs | state | what it separates |
|---|---|---|---|
| CP-01 | A 0, 1, $1F, $FF | RG1SAV bit 1 clear / set | the MSX1 rule holds via the sub-ROM |
| CP-02 | A $FF, 16 x 16 | PATBAS $F000 | HL = $0FE0 (16-bit wrap) vs a saturated / refused result; the carry flag after it |
| CP-03 | A 3 | SCRMOD 7, ACPAGE 1, DPPAGE 0 | ACPAGE added vs not |
| CP-04 | A 3 | RG1SAV and R#1 disagree on the size | the RAM copy vs the VDP |
| CP-05 | A 3 | SCRMOD 1 vs 5 | sprite mode plays no part vs it does |
| CP-06 | entry F $00 / $FF; BC, IX, IY, AF' BC' DE' HL' garbage | interrupts on / off; the control call | the main ROM's F rule; kept registers; IX after EXTROM; interrupt state |

## Related pages

[CALATR](CALATR.md), [GSPSIZ](GSPSIZ.md), [CLRSPR](CLRSPR.md); the MSX1 call
[CALPAT $0084](../../bios/CALPAT.md).

## Tests that cover it

None yet.
