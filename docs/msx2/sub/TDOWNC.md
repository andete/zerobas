<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `TDOWNC` (sub-ROM $00B1) — move the graphics position down, checking the edge

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the HB-F900, NMS 8250 and FS-A1WSX ([xsubmv.asm](../../../probes/bios/spec/xsubmv.asm), [scratchpad/AE_xsubmv_msx2.out](../../../scratchpad/AE_xsubmv_msx2.out), decoded by `scratchpad/xsubmv_decode.py`).

## Summary

`TDOWNC` is assumed to be the sub-ROM's counterpart of the main ROM's [TDOWNC](../../bios/TDOWNC.md)
($010B): [DOWNC](DOWNC.md), but at the bottom line it stops. The bottom is the open question: line
191 or 211, fixed or following R#9, and measured from the active page or absolute.

## The specification

**Interface.**
- No published entry at $00B1 [P TH A1 SUB-ROM, by absence]; the name and address are the C-BIOS
  peer's. A callable entry is [A] (case TD-00).
- Called through EXTROM, IX = $00B1 [P TH A1 SUB-ROM, preamble].
- Where it does not stop, as [DOWNC](DOWNC.md) [A]; the carry clear.
- Where it stops [A]: the last line -- 191 or 211 [screen heights P TH 4 §3.6-§3.9; which one A];
  CLOC / CMASK kept, A = 0, the carry set [A, as MSX1].
- The bitmap cursor model is unpublished ([the concept page](../concepts/graphics-cursor.md#the-cursor-model--rival-rules-to-separate));
  the rules above are stated per model, all [A]. Pixel layout: [P TH 4 §3.6-§3.9].
- VDP registers and VRAM: none touched [A] (the MSX1 moves touch none, measured there). Registers
  other than A / F, and the interrupt state, kept [A, as MSX1].

**Measured** [M] (the same on all three references; the start set by MAPXYC): In SCREEN 5-8 it moves by a pixel: CMASK (Y) + 1, carry set at the last line (211); in SCREEN 2 the multicolour step, carry at line 191.

| SCREEN | (X, Y) | CLOC / CMASK before | after | carry |
|---|---|---|---|---|
| 2 | (10, 20) | $022C / $F0 | $022D / $F0 | 0 |
| 2 | (0, 0) | $0000 / $F0 | $0001 / $F0 | 0 |
| 2 | (255, 20) | $02FC / $0F | $02FD / $0F | 0 |
| 2 | (10, 191) | $072F / $F0 | $072F / $F0 | 1 |
| 5 | (10, 20) | $000A / $14 | $000A / $15 | 0 |
| 5 | (0, 0) | $0000 / $00 | $0000 / $01 | 0 |
| 5 | (255, 20) | $00FF / $14 | $00FF / $15 | 0 |
| 5 | (10, 211) | $000A / $D3 | $000A / $D3 | 1 |
| 6 | (10, 20) | $000A / $14 | $000A / $15 | 0 |
| 6 | (0, 0) | $0000 / $00 | $0000 / $01 | 0 |
| 6 | (255, 20) | $01FF / $14 | $01FF / $15 | 0 |
| 6 | (10, 211) | $000A / $D3 | $000A / $D3 | 1 |
| 8 | (10, 20) | $000A / $14 | $000A / $15 | 0 |
| 8 | (0, 0) | $0000 / $00 | $0000 / $01 | 0 |
| 8 | (255, 20) | $00FF / $14 | $00FF / $15 | 0 |
| 8 | (0, 0) | $000A / $D3 | $000A / $D3 | 0 |

## Differences from the reference

C-BIOS's MSX2 / MSX2+ builds differ in 1 of the 16 cases -- in SCREEN 2 at line 191 they move on ($072F -> $0828) where the references stop with carry set ([scratchpad/AE_xsubmv_msx2.out](../../../scratchpad/AE_xsubmv_msx2.out)).

## Open (not measured)

The sets [PG], [LN], [MD], [SN] and [R9] are defined on [the concept page](../concepts/graphics-cursor.md#shared-measurement-setup-every-pages-matrix-assumes-it).

Every case runs on all three references; each machine's result is recorded on its own, and a rule that holds on one generation only names it ([the concept page](../concepts/graphics-cursor.md)). `—` = not measured yet; `n/a` = the mode does not exist on that machine.

| case | inputs | state | what it separates | HB-F900 | NMS 8250 | FS-A1WSX |
|---|---|---|---|---|---|---|
| TD-00 | CLOC / CMASK from MAPXYC (10, 10) | SCREEN 5 | a callable entry vs not | — | — | — |
| TD-01 | MAPXYC (10, 190), (10, 191), (10, 210), (10, 211) | SCREEN 5, R#9 LN 0 and 1 | the bottom: 191 vs 211; fixed vs R#9 | — | — | — |
| TD-02 | the same | SCREEN 7 / 8 (256-byte lines) | the line length in the test | — | — | — |
| TD-03 | MAPXYC (10, 211) under ACPAGE 1; and CLOC $8000 + $6985 / CMASK $F0 planted by hand, ACPAGE 0 and 1 | SCREEN 5, [PG] | the bottom relative to the page, not hanging on MAPXYC | — | — | — |
| TD-04 | MAPXYC (10, 211) | [R9] located first; R#9 LN 1 with its copy 0, and the reverse | whether the call reads R#9 or its copy | — | — | — |
| TD-05 | MAPXYC (5, 211), (6, 211) | SCREEN 6 (CMASK $30, $0C); [LN] | the stop with the inner masks | — | — | — |
| TD-06 | CLOC $6985 with CMASK $F1, $00 | SCREEN 5 | whether the bottom test reads CMASK | — | — | — |
| TD-90 | garbage in BC, DE, HL, IX, IY; entry A, F $00 / $FF; DI / EI | each mode | A and F left (MSX1: an AND's flags on the new mask or CLOC AND 7); registers and interrupts kept | — | — | — |
| TD-91 | CLOC / CMASK from MAPXYC | SCRMOD 2, 3, 4; [MD] | the MSX1 rules ([TDOWNC](../../bios/TDOWNC.md)) through the sub-ROM; SCREEN 4 as 2 | — | — | — |
| TD-92 | CLOC / CMASK from MAPXYC | SCRMOD 10-12 (FS-A1WSX) | the step in the YJK modes (as SCREEN 8?) | n/a | n/a | — |
| TD-93 | CLOC / CMASK from MAPXYC, and CLOC $8000 + offset planted by hand | [PG] in SCREEN 5 / 6 | whether the page is inside CLOC (and kept by the step) | — | — | — |
| TD-94 | a step from MAPXYC (100, 50) | SCREEN 5; [SN] | RAM other than CLOC / CMASK, VRAM, the VDP registers and S#n unchanged | — | — | — |
| TD-95 | the TD-01 inputs | SCREEN 5, called at the main-ROM TDOWNC ($010B) | the main entry forwards to the sub-ROM in SCREEN 5-8 vs runs the MSX1 step | — | — | — |

## Related pages

[The concept page](../concepts/graphics-cursor.md); the MSX1 [TDOWNC](../../bios/TDOWNC.md); the other sub-ROM moves
[RIGHTC](RIGHTC.md), [LEFTC](LEFTC.md), [UPC](UPC.md), [DOWNC](DOWNC.md), [TUPC](TUPC.md), [TRIGHT](TRIGHT.md), [TLEFTC](TLEFTC.md); [MAPXYC](MAPXYC.md).

## Tests that cover it

None yet.
