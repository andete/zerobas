<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `GETPAT` (sub-ROM $0105) — fetch a character's pattern

> **Spec:** DRAFT 0 (2026-11-23), from the published interface only; nothing measured yet. References to measure: HB-F900, NMS 8250, FS-A1WSX.

## Summary

`GETPAT` copies the 8-byte pattern of character A into PATWRK ($FC40). The handbook does not say
where the pattern comes from: the ROM font, or the pattern generator table in VRAM.

## The specification

Shared facts: [vdp-and-palette.md](../concepts/vdp-and-palette.md).

### Interface

- **In:** A, the character code [P A1 GETPAT].
- **Out:** PATWRK ($FC40, 8 bytes), the pattern [P A1 GETPAT, A4 PATWRK]. Any register may change
  [P A1 GETPAT].

### Behaviour

- The source — the main ROM's font, or VRAM from CGPBAS / the mode's pattern table — is [A].
- Whether it depends on SCRMOD (SCREEN 5-8 have no pattern generator table [P A5]) is [A].
- Anything written besides PATWRK's 8 bytes is [A].

## Differences from the reference

Not measured yet.

## Open (not measured)

Recording as in [vdp-and-palette.md](../concepts/vdp-and-palette.md#how-every-case-is-recorded);
the whole-RAM diff shows everything written besides PATWRK.

| case | inputs | state | what it separates |
|---|---|---|---|
| GP-01 | A $41 | VRAM pattern of $41 rewritten to garbage, SCRMOD 0 / 1 | ROM font vs VRAM table |
| GP-02 | A $41 | CGPBAS moved, the moved table distinct | VRAM via CGPBAS vs the mode's default table |
| GP-03 | A $41 | SCRMOD 5, 8 | the font in bitmap modes |
| GP-04 | A 0, $FF | — | the ends of the table |
| GP-05 | A $41 | PATWRK preset to garbage | exactly 8 bytes written; nothing else in RAM |
| GP-06 | all registers incl. AF' BC' DE' HL' IX IY garbage | interrupts on / off; the control call | registers and interrupt state on return |
| GP-07 | A $A0 | the Japanese machine (HB-F900) vs the European | the national font is the source |
| GP-08 | A $41 | a VDP command running (CE = 1), SCRMOD 1 | VRAM read during a command |

## Related pages

The graphics character calls that use PATWRK; [vdp-and-palette.md](../concepts/vdp-and-palette.md).

## Tests that cover it

None yet.
