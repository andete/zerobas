<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `TUPC` (sub-ROM $00B9) — move the graphics position up, checking the edge

> **Spec:** DRAFT 0 (2026-11-23), from the published interface only; nothing measured yet. References to measure: HB-F900, NMS 8250, FS-A1WSX.

## Summary

`TUPC` is assumed to be the sub-ROM's counterpart of the main ROM's [TUPC](../../bios/TUPC.md)
($0105): [UPC](UPC.md), but at the top line it stops -- CLOC / CMASK kept, A = 0, the carry set. In
the bitmap modes "the top" may be Y 0 of the active page, VRAM address 0, or a test that only
looks at the byte's position in a line.

## The specification

**Interface.**
- No published entry at $00B9 [P TH A1 SUB-ROM, by absence]; the name and address are the C-BIOS
  peer's. A callable entry is [A] (case TU-00).
- Called through EXTROM, IX = $00B9 [P TH A1 SUB-ROM, preamble].
- Where it does not stop, as [UPC](UPC.md) [A]; the carry clear.
- Where it stops [A]: Y 0 -- under model B, CLOC below 128 (SCREEN 5 / 6) or 256 (7 / 8), perhaps
  relative to the active page's start; under model C, CMASK 0. The stop leaves CLOC / CMASK, A = 0,
  the carry set [A, as MSX1].
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
| TU-00 | CLOC / CMASK from MAPXYC (10, 10) | SCREEN 5 | a callable entry vs not | — | — | — |
| TU-01 | MAPXYC (10, 1), (10, 0) | SCREEN 5, 6, 7, 8 | moves vs stops; the step | — | — | — |
| TU-02 | MAPXYC (10, 0) under ACPAGE 1 (model B with the page: CLOC $8005); and CLOC $8005 / CMASK $F0 planted by hand, ACPAGE 0 and 1 | SCREEN 5, [PG] | the top relative to the page vs absolute -- the planted case does not hang on whether MAPXYC adds the page | — | — | — |
| TU-03 | CLOC 127, 128 by hand | SCREEN 5 vs 7 | the line length in the test (128 vs 256) | — | — | — |
| TU-04 | CLOC $8005 by hand, ACPAGE 0 | SCREEN 5 | an absolute "CLOC < 128" test (moves) vs a within-page "CLOC AND $7F80 = 0" test (stops) | — | — | — |
| TU-05 | MAPXYC (5, 0), (6, 0) | SCREEN 6 (CMASK $30, $0C) | the stop with the inner masks | — | — | — |
| TU-06 | CLOC 10 with CMASK $F1, $00 (not a pixel's) | SCREEN 5 | whether the top test reads CMASK | — | — | — |
| TU-90 | garbage in BC, DE, HL, IX, IY; entry A, F $00 / $FF; DI / EI | each mode | A and F left (MSX1: an AND's flags on the new mask or CLOC AND 7); registers and interrupts kept | — | — | — |
| TU-91 | CLOC / CMASK from MAPXYC | SCRMOD 2, 3, 4; [MD] | the MSX1 rules ([TUPC](../../bios/TUPC.md)) through the sub-ROM; SCREEN 4 as 2 | — | — | — |
| TU-92 | CLOC / CMASK from MAPXYC | SCRMOD 10-12 (FS-A1WSX) | the step in the YJK modes (as SCREEN 8?) | n/a | n/a | — |
| TU-93 | CLOC / CMASK from MAPXYC, and CLOC $8000 + offset planted by hand | [PG] in SCREEN 5 / 6 | whether the page is inside CLOC (and kept by the step) | — | — | — |
| TU-94 | a step from MAPXYC (100, 50) | SCREEN 5; [SN] | RAM other than CLOC / CMASK, VRAM, the VDP registers and S#n unchanged | — | — | — |
| TU-95 | the TU-01 inputs | SCREEN 5, called at the main-ROM TUPC ($0105) | the main entry forwards to the sub-ROM in SCREEN 5-8 vs runs the MSX1 step | — | — | — |

## Related pages

[The concept page](../concepts/graphics-cursor.md); the MSX1 [TUPC](../../bios/TUPC.md); the other sub-ROM moves
[RIGHTC](RIGHTC.md), [LEFTC](LEFTC.md), [UPC](UPC.md), [DOWNC](DOWNC.md), [TDOWNC](TDOWNC.md), [TRIGHT](TRIGHT.md), [TLEFTC](TLEFTC.md); [MAPXYC](MAPXYC.md).

## Tests that cover it

None yet.
