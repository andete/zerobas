<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `UPC` (sub-ROM $00BD) — move the graphics position one pixel up

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the HB-F900, NMS 8250 and FS-A1WSX ([xsubmv.asm](../../../probes/bios/spec/xsubmv.asm), [scratchpad/AE_xsubmv_msx2.out](../../../scratchpad/AE_xsubmv_msx2.out), decoded by `scratchpad/xsubmv_decode.py`).

## Summary

`UPC` is assumed to be the sub-ROM's counterpart of the main ROM's [UPC](../../bios/UPC.md)
($0102): one line up, no edge check. In the bitmap modes a line is 128 or 256 bytes, so the MSX1
step (CLOC - 1, or - $F9 across a character row) cannot be right there; the step per mode is the
question.

## The specification

**Interface.**
- No published entry at $00BD [P TH A1 SUB-ROM, by absence]; the name and address are the C-BIOS
  peer's. A callable entry is [A] (case UC-00).
- Called through EXTROM, IX = $00BD [P TH A1 SUB-ROM, preamble].
- In / out: CLOC and CMASK [A]: under model B CMASK is kept; under model C it is the Y and changes.
- Model B [A]: CLOC - 128 (SCREEN 5 / 6), CLOC - 256 (7 / 8). Model C: CMASK (Y) - 1.
- No edge check [A]: from line 0 model B wraps below CLOC 0 (into the previous page, or $FFxx),
  model C to Y $FF.
- The bitmap cursor model is unpublished ([the concept page](../concepts/graphics-cursor.md#the-cursor-model--rival-rules-to-separate));
  the rules above are stated per model, all [A]. Pixel layout: [P TH 4 §3.6-§3.9].
- VDP registers and VRAM: none touched [A] (the MSX1 moves touch none, measured there). Registers
  other than A / F, and the interrupt state, kept [A, as MSX1].

**Measured** [M] (the same on all three references; the start set by MAPXYC): It steps CLOC by -1 within an 8-byte cell (SCREEN 2 / multicolour arithmetic: CLOC AND 7 = 0 moves up a row, $0000 -> $FF07) in every mode; CMASK kept. In SCREEN 5-8, where CLOC holds X, that is X - 1.

| SCREEN | (X, Y) | CLOC / CMASK before | after | carry |
|---|---|---|---|---|
| 2 | (10, 20) | $022C / $F0 | $022B / $F0 | 0 |
| 2 | (0, 0) | $0000 / $F0 | $FF07 / $F0 | 0 |
| 2 | (255, 20) | $02FC / $0F | $02FB / $0F | 0 |
| 2 | (10, 191) | $072F / $F0 | $072E / $F0 | 0 |
| 5 | (10, 20) | $000A / $14 | $0009 / $14 | 0 |
| 5 | (0, 0) | $0000 / $00 | $FF07 / $00 | 0 |
| 5 | (255, 20) | $00FF / $14 | $00FE / $14 | 0 |
| 5 | (10, 211) | $000A / $D3 | $0009 / $D3 | 0 |
| 6 | (10, 20) | $000A / $14 | $0009 / $14 | 0 |
| 6 | (0, 0) | $0000 / $00 | $FF07 / $00 | 0 |
| 6 | (255, 20) | $01FF / $14 | $01FE / $14 | 0 |
| 6 | (10, 211) | $000A / $D3 | $0009 / $D3 | 0 |
| 8 | (10, 20) | $000A / $14 | $0009 / $14 | 0 |
| 8 | (0, 0) | $0000 / $00 | $FF07 / $00 | 0 |
| 8 | (255, 20) | $00FF / $14 | $00FE / $14 | 0 |
| 8 | (10, 211) | $000A / $D3 | $0009 / $D3 | 0 |

## Differences from the reference

C-BIOS's MSX2 / MSX2+ builds give the same positions ([scratchpad/AE_xsubmv_msx2.out](../../../scratchpad/AE_xsubmv_msx2.out)).

## Open (not measured)

The sets [PG], [LN], [MD], [SN] and [R9] are defined on [the concept page](../concepts/graphics-cursor.md#shared-measurement-setup-every-pages-matrix-assumes-it).

Every case runs on all three references; each machine's result is recorded on its own, and a rule that holds on one generation only names it ([the concept page](../concepts/graphics-cursor.md)). `—` = not measured yet; `n/a` = the mode does not exist on that machine.

| case | inputs | state | what it separates | HB-F900 | NMS 8250 | FS-A1WSX |
|---|---|---|---|---|---|---|
| UC-00 | CLOC / CMASK from MAPXYC (10, 10) | SCREEN 5 | a callable entry vs not | — | — | — |
| UC-01 | MAPXYC (10, 5) | SCREEN 5, 6, 7, 8 | the line step: 128 vs 256 vs 1 vs the MSX1 rule | — | — | — |
| UC-02 | MAPXYC (0, 7) and (1, 7) | SCREEN 5 (model B: CLOC $380, AND 7 = 0) | the MSX1 rule's - $F9 branch (CLOC $287) vs the bitmap step ($300) | — | — | — |
| UC-03 | MAPXYC (10, 0); CLOC $8005 / CMASK $F0 by hand | SCREEN 5, [PG] | from line 0: the wrap; page 1 into page 0 | — | — | — |
| UC-04 | MAPXYC (4, 5), (5, 5), (6, 5) | SCREEN 6 (CMASK $C0, $30, $0C) | the mask kept by a vertical step | — | — | — |
| UC-90 | garbage in BC, DE, HL, IX, IY; entry A, F $00 / $FF; DI / EI | each mode | A and F left (MSX1: an AND's flags on the new mask or CLOC AND 7); registers and interrupts kept | — | — | — |
| UC-91 | CLOC / CMASK from MAPXYC | SCRMOD 2, 3, 4; [MD] | the MSX1 rules ([UPC](../../bios/UPC.md)) through the sub-ROM; SCREEN 4 as 2 | — | — | — |
| UC-92 | CLOC / CMASK from MAPXYC | SCRMOD 10-12 (FS-A1WSX) | the step in the YJK modes (as SCREEN 8?) | n/a | n/a | — |
| UC-93 | CLOC / CMASK from MAPXYC, and CLOC $8000 + offset planted by hand | [PG] in SCREEN 5 / 6 | whether the page is inside CLOC (and kept by the step) | — | — | — |
| UC-94 | a step from MAPXYC (100, 50) | SCREEN 5; [SN] | RAM other than CLOC / CMASK, VRAM, the VDP registers and S#n unchanged | — | — | — |
| UC-95 | the UC-01 inputs | SCREEN 5, called at the main-ROM UPC ($0102) | the main entry forwards to the sub-ROM in SCREEN 5-8 vs runs the MSX1 step | — | — | — |

## Related pages

[The concept page](../concepts/graphics-cursor.md); the MSX1 [UPC](../../bios/UPC.md); the other sub-ROM moves
[RIGHTC](RIGHTC.md), [LEFTC](LEFTC.md), [DOWNC](DOWNC.md), [TUPC](TUPC.md), [TDOWNC](TDOWNC.md), [TRIGHT](TRIGHT.md), [TLEFTC](TLEFTC.md); [MAPXYC](MAPXYC.md).

## Tests that cover it

None yet.
