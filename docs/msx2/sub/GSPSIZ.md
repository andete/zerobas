<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `GSPSIZ` (sub-ROM $0101) — the current sprite size

> **Spec:** DRAFT 0 (2026-11-23), from the published interface only; nothing measured yet. References to measure: HB-F900, NMS 8250, FS-A1WSX.

## Summary

`GSPSIZ` returns the sprite size — 8 for 8 x 8 sprites, and 32 or 16 for 16 x 16 — and sets the
carry for 16 x 16. The handbook calls it the same routine as the main ROM's GSPSIZ ($008A)
([GSPSIZ](../../bios/GSPSIZ.md)). The other pages use it as the control call.

## The specification

Shared facts: [vdp-and-palette.md](../concepts/vdp-and-palette.md).

### Interface

- **In:** none [P A1 GSPSIZ]. The source of the size — RG1SAV bit 1 [P 4§5.2.2 for R#1's bit] —
  is [A].
- **Out:** A, the sprite size; carry set only for 16 x 16 [P A1 GSPSIZ]. Only AF changes
  [P A1 GSPSIZ].

### Behaviour

- A = 8 or 32 (pattern bytes, as the MSX1 call) rather than 8 / 16 (dots) is [A].
- The other flags are [A].

## Differences from the reference

Not measured yet.

## Open (not measured)

Recording as in [vdp-and-palette.md](../concepts/vdp-and-palette.md#how-every-case-is-recorded).
Because this call is the other pages' control, its own register and interrupt results are
measured first.

| case | inputs | state | what it separates |
|---|---|---|---|
| GS-01 | — | RG1SAV $E0, $E2, $E1, $E3 | A 8 / 32 vs 8 / 16; magnification (bit 0) ignored |
| GS-02 | — | RG1SAV bit 1 ≠ R#1 bit 1 | the RAM copy vs the VDP |
| GS-03 | — | SCRMOD 1 vs 5 | sprite mode plays no part |
| GS-04 | entry F $00 / $FF; all registers incl. AF' BC' DE' HL' IX IY garbage | interrupts on / off | S / Z / P/V / H / bits 5-3; every other register kept; the EXTROM path's interrupt state |

## Related pages

[CALPAT](CALPAT.md), [CALATR](CALATR.md), [CLRSPR](CLRSPR.md); the MSX1 call
[GSPSIZ $008A](../../bios/GSPSIZ.md).

## Tests that cover it

None yet.
