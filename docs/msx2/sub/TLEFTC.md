<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `TLEFTC` (sub-ROM $00A9) — move the graphics position left, checking the edge

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the HB-F900, NMS 8250 and FS-A1WSX ([xsubmv.asm](../../../probes/bios/spec/xsubmv.asm), [scratchpad/AE_xsubmv_msx2.out](../../../scratchpad/AE_xsubmv_msx2.out), decoded by `scratchpad/xsubmv_decode.py`).

## Summary

`TLEFTC` has no MSX1 counterpart: it is assumed to be [LEFTC](LEFTC.md) with an edge check at X 0,
the mirror of [TRIGHT](TRIGHT.md).

## The specification

**Interface.**
- No published entry at $00A9 [P TH A1 SUB-ROM, by absence]; the name and address are the C-BIOS
  peer's. A callable entry is [A] (case TL-00).
- Called through EXTROM, IX = $00A9 [P TH A1 SUB-ROM, preamble].
- There is no MSX1 main-ROM TLEFTC ([the MSX1 BIOS index](../../bios/index.md) has none); the MSX1 LEFTC checks no edge (measured on
  [LEFTC](../../bios/LEFTC.md)).
- Where it does not stop, as [LEFTC](LEFTC.md) [A]; at X 0 it stops with CLOC / CMASK kept, A = 0,
  the carry set [A].
- The bitmap cursor model is unpublished ([the concept page](../concepts/graphics-cursor.md#the-cursor-model--rival-rules-to-separate));
  the rules above are stated per model, all [A]. Pixel layout: [P TH 4 §3.6-§3.9].
- VDP registers and VRAM: none touched [A] (the MSX1 moves touch none, measured there). Registers
  other than A / F, and the interrupt state, kept [A, as MSX1].

**Measured** [M] (the same on all three references; the start set by MAPXYC): In SCREEN 5-8 it moves by a pixel: CLOC (X) - 1, carry set at X 0; in SCREEN 2 the multicolour step (CLOC - 8 / CMASK $0F), carry at the left cell.

| SCREEN | (X, Y) | CLOC / CMASK before | after | carry |
|---|---|---|---|---|
| 2 | (10, 20) | $022C / $F0 | $0224 / $0F | 0 |
| 2 | (0, 0) | $0000 / $F0 | $0000 / $F0 | 1 |
| 2 | (255, 20) | $02FC / $0F | $02FC / $F0 | 0 |
| 2 | (10, 191) | $072F / $F0 | $0727 / $0F | 0 |
| 5 | (10, 20) | $000A / $14 | $0009 / $14 | 0 |
| 5 | (0, 0) | $0000 / $00 | $0000 / $00 | 1 |
| 5 | (255, 20) | $00FF / $14 | $00FE / $14 | 0 |
| 5 | (10, 211) | $000A / $D3 | $0009 / $D3 | 0 |
| 6 | (10, 20) | $000A / $14 | $0009 / $14 | 0 |
| 6 | (0, 0) | $0000 / $00 | $0000 / $00 | 1 |
| 6 | (255, 20) | $01FF / $14 | $01FE / $14 | 0 |
| 6 | (10, 211) | $000A / $D3 | $0009 / $D3 | 0 |
| 8 | (10, 20) | $000A / $14 | $0009 / $14 | 0 |
| 8 | (0, 0) | $0000 / $00 | $0000 / $00 | 1 |
| 8 | (255, 20) | $00FF / $14 | $00FE / $14 | 0 |
| 8 | (10, 211) | $000A / $D3 | $0009 / $D3 | 0 |

## Differences from the reference

C-BIOS's MSX2 / MSX2+ builds (the subject) do NOTHING here: CLOC / CMASK unchanged and A as the caller left it, in every mode, carry never set ([scratchpad/AE_xsubmv_msx2.out](../../../scratchpad/AE_xsubmv_msx2.out)).

## Open (not measured)

The sets [PG], [LN], [MD], [SN] and [R9] are defined on [the concept page](../concepts/graphics-cursor.md#shared-measurement-setup-every-pages-matrix-assumes-it).

Every case runs on all three references; each machine's result is recorded on its own, and a rule that holds on one generation only names it ([the concept page](../concepts/graphics-cursor.md)). `—` = not measured yet; `n/a` = the mode does not exist on that machine.

| case | inputs | state | what it separates | HB-F900 | NMS 8250 | FS-A1WSX |
|---|---|---|---|---|---|---|
| TL-00 | CLOC / CMASK from MAPXYC (10, 10) | SCREEN 5 | a callable entry vs not | — | — | — |
| TL-01 | MAPXYC (1, 3), (0, 3) | SCREEN 5, 6 (also X 1, 2: CMASK $30, $0C), 7, 8 | moves vs stops | — | — | — |
| TL-02 | MAPXYC (0, 0) under [PG]; and CLOC $8000 / CMASK $F0 planted by hand, ACPAGE 0 and 1 | SCREEN 5 | X 0 on line 0, not hanging on whether MAPXYC adds the page | — | — | — |
| TL-03 | MAPXYC (0, 3) | SCREEN 2, 3, 4; [MD] | the edge in the MSX1 modes | — | — | — |
| TL-04 | CMASK not a pixel's | SCREEN 5, 6 | the edge test's input | — | — | — |
| TL-90 | garbage in BC, DE, HL, IX, IY; entry A, F $00 / $FF; DI / EI | each mode | A and F left (MSX1: an AND's flags on the new mask or CLOC AND 7); registers and interrupts kept | — | — | — |
| TL-91 | CLOC / CMASK from MAPXYC | SCRMOD 2, 3, 4; [MD] | the MSX1 rules ([LEFTC](../../bios/LEFTC.md)) through the sub-ROM; SCREEN 4 as 2 | — | — | — |
| TL-92 | CLOC / CMASK from MAPXYC | SCRMOD 10-12 (FS-A1WSX) | the step in the YJK modes (as SCREEN 8?) | n/a | n/a | — |
| TL-93 | CLOC / CMASK from MAPXYC, and CLOC $8000 + offset planted by hand | [PG] in SCREEN 5 / 6 | whether the page is inside CLOC (and kept by the step) | — | — | — |
| TL-94 | a step from MAPXYC (100, 50) | SCREEN 5; [SN] | RAM other than CLOC / CMASK, VRAM, the VDP registers and S#n unchanged | — | — | — |

## Related pages

[The concept page](../concepts/graphics-cursor.md); the MSX1 [LEFTC](../../bios/LEFTC.md) (the unchecked move); the other sub-ROM moves
[RIGHTC](RIGHTC.md), [LEFTC](LEFTC.md), [UPC](UPC.md), [DOWNC](DOWNC.md), [TUPC](TUPC.md), [TDOWNC](TDOWNC.md), [TRIGHT](TRIGHT.md); [MAPXYC](MAPXYC.md).

## Tests that cover it

None yet.
