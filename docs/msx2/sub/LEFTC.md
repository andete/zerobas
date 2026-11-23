<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `LEFTC` (sub-ROM $00AD) — move the graphics position one pixel left

> **Spec:** DRAFT 0 (2026-11-23), from the published interface only; nothing measured yet. References to measure: HB-F900, NMS 8250, FS-A1WSX.

## Summary

`LEFTC` is assumed to be the sub-ROM's counterpart of the main ROM's [LEFTC](../../bios/LEFTC.md)
($00FF): one pixel left, no edge check -- the mirror of [RIGHTC](RIGHTC.md), with the same open
question of how a bitmap position is held.

## The specification

**Interface.**
- No published entry at $00AD [P TH A1 SUB-ROM, by absence]; the name and address are the C-BIOS
  peer's. A callable entry is [A] (case LC-00).
- Called through EXTROM, IX = $00AD [P TH A1 SUB-ROM, preamble].
- In / out: CLOC, CMASK [A].
- Model B [A]: SCREEN 5 / 7 CMASK $0F → $F0, CLOC kept; $F0 → $0F, CLOC - 1. SCREEN 6 CMASK shifts
  left 2 bits, from $C0 to $03 with CLOC - 1. SCREEN 8 CLOC - 1. Model C: CLOC (X) - 1.
- No edge check [A, as MSX1]: from X 0 model B goes to the previous line's last pixel (or, at
  CLOC 0, wraps to $FFFF), model C to X -1 ($FFFF).
- The bitmap cursor model is unpublished ([the concept page](../concepts/graphics-cursor.md#the-cursor-model--rival-rules-to-separate));
  the rules above are stated per model, all [A]. Pixel layout: [P TH 4 §3.6-§3.9].
- VDP registers and VRAM: none touched [A] (the MSX1 moves touch none, measured there). Registers
  other than A / F, and the interrupt state, kept [A, as MSX1].

## Differences from the reference

Not measured yet.

## Open (not measured)

The sets [PG], [LN], [MD], [SN] and [R9] are defined on [the concept page](../concepts/graphics-cursor.md#shared-measurement-setup-every-pages-matrix-assumes-it).

Every case runs on all three references; each machine's result is recorded on its own, and a rule that holds on one generation only names it ([the concept page](../concepts/graphics-cursor.md)). `—` = not measured yet; `n/a` = the mode does not exist on that machine.

| case | inputs | state | what it separates | HB-F900 | NMS 8250 | FS-A1WSX |
|---|---|---|---|---|---|---|
| LC-00 | CLOC / CMASK from MAPXYC (10, 10) | SCREEN 5 | a callable entry vs not | — | — | — |
| LC-01 | MAPXYC (5, 3), (4, 3) | SCREEN 5 | the half-byte step | — | — | — |
| LC-02 | MAPXYC X 4..0 | SCREEN 6 | the 2-bit sequence | — | — | — |
| LC-03 | MAPXYC (0, 3); (0, 0) | SCREEN 5, 8 | the line start and CLOC 0: previous line / $FFFF | — | — | — |
| LC-04 | CMASK $8F, $4F, $00 | SCREEN 5, 6 | which bit of CMASK the step tests | — | — | — |
| LC-90 | garbage in BC, DE, HL, IX, IY; entry A, F $00 / $FF; DI / EI | each mode | A and F left (MSX1: an AND's flags on the new mask or CLOC AND 7); registers and interrupts kept | — | — | — |
| LC-91 | CLOC / CMASK from MAPXYC | SCRMOD 2, 3, 4; [MD] | the MSX1 rules ([LEFTC](../../bios/LEFTC.md)) through the sub-ROM; SCREEN 4 as 2 | — | — | — |
| LC-92 | CLOC / CMASK from MAPXYC | SCRMOD 10-12 (FS-A1WSX) | the step in the YJK modes (as SCREEN 8?) | n/a | n/a | — |
| LC-93 | CLOC / CMASK from MAPXYC, and CLOC $8000 + offset planted by hand | [PG] in SCREEN 5 / 6 | whether the page is inside CLOC (and kept by the step) | — | — | — |
| LC-94 | a step from MAPXYC (100, 50) | SCREEN 5; [SN] | RAM other than CLOC / CMASK, VRAM, the VDP registers and S#n unchanged | — | — | — |
| LC-95 | the LC-01 inputs | SCREEN 5, called at the main-ROM LEFTC ($00FF) | the main entry forwards to the sub-ROM in SCREEN 5-8 vs runs the MSX1 step | — | — | — |

## Related pages

[The concept page](../concepts/graphics-cursor.md); the MSX1 [LEFTC](../../bios/LEFTC.md); the other sub-ROM moves
[RIGHTC](RIGHTC.md), [UPC](UPC.md), [DOWNC](DOWNC.md), [TUPC](TUPC.md), [TDOWNC](TDOWNC.md), [TRIGHT](TRIGHT.md), [TLEFTC](TLEFTC.md); [MAPXYC](MAPXYC.md).

## Tests that cover it

None yet.
