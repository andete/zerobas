<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `DOWNC` (sub-ROM $00B5) — move the graphics position one pixel down

> **Spec:** DRAFT 0 (2026-11-23), from the published interface only; nothing measured yet. References to measure: HB-F900, NMS 8250, FS-A1WSX.

## Summary

`DOWNC` is assumed to be the sub-ROM's counterpart of the main ROM's [DOWNC](../../bios/DOWNC.md)
($0108): one line down, no edge check -- the mirror of [UPC](UPC.md).

## The specification

**Interface.**
- No published entry at $00B5 [P TH A1 SUB-ROM, by absence]; the name and address are the C-BIOS
  peer's. A callable entry is [A] (case DC-00).
- Called through EXTROM, IX = $00B5 [P TH A1 SUB-ROM, preamble].
- In / out: CLOC and CMASK [A]: under model B CMASK is kept; under model C it is the Y and changes.
- Model B [A]: CLOC + 128 (SCREEN 5 / 6), + 256 (7 / 8). Model C: CMASK (Y) + 1.
- No edge check [A]: past the last line model B runs into the non-visible lines and the next page,
  model C wraps Y at 255.
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
| DC-00 | CLOC / CMASK from MAPXYC (10, 10) | SCREEN 5 | a callable entry vs not | — | — | — |
| DC-01 | MAPXYC (10, 5) | SCREEN 5, 6, 7, 8 | the line step | — | — | — |
| DC-02 | MAPXYC (14, 7) and (15, 7) | SCREEN 5 (model B: CLOC $387, AND 7 = 7) | the MSX1 rule's + $F9 branch ($480) vs the bitmap step ($407) | — | — | — |
| DC-03 | MAPXYC (10, 211), (10, 255) | SCREEN 5; [LN] | past the visible bottom: 212, 256 (next page) | — | — | — |
| DC-04 | CLOC $FF80 | SCREEN 5 | the 16-bit carry | — | — | — |
| DC-05 | MAPXYC (4, 5), (5, 5), (6, 5) | SCREEN 6 (CMASK $C0, $30, $0C) | the mask kept by a vertical step | — | — | — |
| DC-90 | garbage in BC, DE, HL, IX, IY; entry A, F $00 / $FF; DI / EI | each mode | A and F left (MSX1: an AND's flags on the new mask or CLOC AND 7); registers and interrupts kept | — | — | — |
| DC-91 | CLOC / CMASK from MAPXYC | SCRMOD 2, 3, 4; [MD] | the MSX1 rules ([DOWNC](../../bios/DOWNC.md)) through the sub-ROM; SCREEN 4 as 2 | — | — | — |
| DC-92 | CLOC / CMASK from MAPXYC | SCRMOD 10-12 (FS-A1WSX) | the step in the YJK modes (as SCREEN 8?) | n/a | n/a | — |
| DC-93 | CLOC / CMASK from MAPXYC, and CLOC $8000 + offset planted by hand | [PG] in SCREEN 5 / 6 | whether the page is inside CLOC (and kept by the step) | — | — | — |
| DC-94 | a step from MAPXYC (100, 50) | SCREEN 5; [SN] | RAM other than CLOC / CMASK, VRAM, the VDP registers and S#n unchanged | — | — | — |
| DC-95 | the DC-01 inputs | SCREEN 5, called at the main-ROM DOWNC ($0108) | the main entry forwards to the sub-ROM in SCREEN 5-8 vs runs the MSX1 step | — | — | — |

## Related pages

[The concept page](../concepts/graphics-cursor.md); the MSX1 [DOWNC](../../bios/DOWNC.md); the other sub-ROM moves
[RIGHTC](RIGHTC.md), [LEFTC](LEFTC.md), [UPC](UPC.md), [TUPC](TUPC.md), [TDOWNC](TDOWNC.md), [TRIGHT](TRIGHT.md), [TLEFTC](TLEFTC.md); [MAPXYC](MAPXYC.md).

## Tests that cover it

None yet.
