<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `RIGHTC` (sub-ROM $00A5) — move the graphics position one pixel right

> **Spec:** DRAFT 0 (2026-11-23), from the published interface only; nothing measured yet. References to measure: HB-F900, NMS 8250, FS-A1WSX.

## Summary

`RIGHTC` is assumed to be the sub-ROM's counterpart of the main ROM's [RIGHTC](../../bios/RIGHTC.md)
($00FC): one pixel right, no edge check. In SCREEN 5-8 one step is half a byte, a quarter byte or a
whole byte, so the step depends on the mode and on how CLOC / CMASK hold the position.

## The specification

**Interface.**
- No published entry at $00A5 [P TH A1 SUB-ROM, by absence]; the name and address are the C-BIOS
  peer's. A callable entry is [A] (case RC-00).
- Called through EXTROM, IX = $00A5 [P TH A1 SUB-ROM, preamble].
- In / out: CLOC ($F92A), CMASK ($F92C) [A; the cells P TH A4].
- Model B [A]: SCREEN 5 / 7 CMASK $F0 → $0F, CLOC kept; $0F → $F0, CLOC + 1. SCREEN 6 CMASK
  shifts right 2 bits, from $03 to $C0 with CLOC + 1. SCREEN 8 CLOC + 1. Model C: CLOC (X) + 1.
- No edge check [A, as MSX1]: past the last pixel model B runs into the next line's first pixel
  (the layout is contiguous), model C to X 256 / 512.
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
| RC-00 | CLOC / CMASK from MAPXYC (10, 10) | SCREEN 5 | a callable entry vs not | — | — | — |
| RC-01 | MAPXYC (4, 3), (5, 3) | SCREEN 5 | the half-byte step vs CLOC + 1 each time | — | — | — |
| RC-02 | MAPXYC X 0..4 (CMASK $C0, $30, $0C, $03, $C0) | SCREEN 6 | four steps per byte; CMASK sequence | — | — | — |
| RC-03 | MAPXYC (7, 3) | SCREEN 8 | a whole-byte step; CMASK kept ($FF?) | — | — | — |
| RC-04 | MAPXYC (255, 3); (511, 3) | SCREEN 5; 7 | the line end: next line (B) vs X past the edge (C) | — | — | — |
| RC-05 | CMASK $F1, $3C, $00 (not a pixel's) | SCREEN 5, 6 | which bit of CMASK the step tests | — | — | — |
| RC-06 | CMASK $80 (SCREEN 2's) | SCREEN 5 | whether SCRMOD decides the step or the mask's shape does | — | — | — |
| RC-90 | garbage in BC, DE, HL, IX, IY; entry A, F $00 / $FF; DI / EI | each mode | A and F left (MSX1: an AND's flags on the new mask or CLOC AND 7); registers and interrupts kept | — | — | — |
| RC-91 | CLOC / CMASK from MAPXYC | SCRMOD 2, 3, 4; [MD] | the MSX1 rules ([RIGHTC](../../bios/RIGHTC.md)) through the sub-ROM; SCREEN 4 as 2 | — | — | — |
| RC-92 | CLOC / CMASK from MAPXYC | SCRMOD 10-12 (FS-A1WSX) | the step in the YJK modes (as SCREEN 8?) | n/a | n/a | — |
| RC-93 | CLOC / CMASK from MAPXYC, and CLOC $8000 + offset planted by hand | [PG] in SCREEN 5 / 6 | whether the page is inside CLOC (and kept by the step) | — | — | — |
| RC-94 | a step from MAPXYC (100, 50) | SCREEN 5; [SN] | RAM other than CLOC / CMASK, VRAM, the VDP registers and S#n unchanged | — | — | — |
| RC-95 | the RC-01 inputs | SCREEN 5, called at the main-ROM RIGHTC ($00FC) | the main entry forwards to the sub-ROM in SCREEN 5-8 vs runs the MSX1 step | — | — | — |

## Related pages

[The concept page](../concepts/graphics-cursor.md); the MSX1 [RIGHTC](../../bios/RIGHTC.md); the other sub-ROM moves
[LEFTC](LEFTC.md), [UPC](UPC.md), [DOWNC](DOWNC.md), [TUPC](TUPC.md), [TDOWNC](TDOWNC.md), [TRIGHT](TRIGHT.md), [TLEFTC](TLEFTC.md); [MAPXYC](MAPXYC.md).

## Tests that cover it

None yet.
