<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `TRIGHT` (sub-ROM $00A1) — move the graphics position right, checking the edge

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the HB-F900, NMS 8250 and FS-A1WSX ([xsubmv.asm](../../../probes/bios/spec/xsubmv.asm), [scratchpad/AE_xsubmv_msx2.out](../../../scratchpad/AE_xsubmv_msx2.out), decoded by `scratchpad/xsubmv_decode.py`).

## Summary

`TRIGHT` has no MSX1 counterpart: by its name and place it is assumed to be [RIGHTC](RIGHTC.md)
with an edge check, as [TUPC](TUPC.md) / [TDOWNC](TDOWNC.md) are UPC / DOWNC with one. Whether it
stops at the right edge, and how it reports it, is entirely unpublished.

## The specification

**Interface.**
- No published entry at $00A1 [P TH A1 SUB-ROM, by absence]; the name and address are the C-BIOS
  peer's. A callable entry is [A] (case TR-00).
- Called through EXTROM, IX = $00A1 [P TH A1 SUB-ROM, preamble].
- There is no MSX1 main-ROM TRIGHT ([the MSX1 BIOS index](../../bios/index.md) has none); the MSX1 horizontal moves check no edge (measured on
  [RIGHTC](../../bios/RIGHTC.md)).
- Where it does not stop, as [RIGHTC](RIGHTC.md) [A]; at X 255 (SCREEN 5 / 8) or 511 (6 / 7) it
  stops with CLOC / CMASK kept, A = 0 and the carry set, as TUPC / TDOWNC report a stop [A].
- In SCREEN 2 / 3 the edge would be X 255 / block 63 [A].
- The bitmap cursor model is unpublished ([the concept page](../concepts/graphics-cursor.md#the-cursor-model--rival-rules-to-separate));
  the rules above are stated per model, all [A]. Pixel layout: [P TH 4 §3.6-§3.9].
- VDP registers and VRAM: none touched [A] (the MSX1 moves touch none, measured there). Registers
  other than A / F, and the interrupt state, kept [A, as MSX1].

**Measured** [M] (the same on all three references; the start set by MAPXYC): The edge test is the coordinate's (X 255 / 511 in SCREEN 5-8, 255 in SCREEN 2: carry set, nothing moves); otherwise it moves as RIGHTC does -- the multicolour cell step, not a pixel.

| SCREEN | (X, Y) | CLOC / CMASK before | after | carry |
|---|---|---|---|---|
| 2 | (10, 20) | $022C / $F0 | $022C / $0F | 0 |
| 2 | (0, 0) | $0000 / $F0 | $0000 / $0F | 0 |
| 2 | (255, 20) | $02FC / $0F | $02FC / $0F | 1 |
| 2 | (10, 191) | $072F / $F0 | $072F / $0F | 0 |
| 5 | (10, 20) | $000A / $14 | $0012 / $F0 | 0 |
| 5 | (0, 0) | $0000 / $00 | $0008 / $F0 | 0 |
| 5 | (255, 20) | $00FF / $14 | $00FF / $14 | 1 |
| 5 | (10, 211) | $000A / $D3 | $000A / $0F | 0 |
| 6 | (10, 20) | $000A / $14 | $0012 / $F0 | 0 |
| 6 | (0, 0) | $0000 / $00 | $0008 / $F0 | 0 |
| 6 | (255, 20) | $01FF / $14 | $01FF / $14 | 1 |
| 6 | (10, 211) | $000A / $D3 | $000A / $0F | 0 |
| 8 | (10, 20) | $000A / $14 | $0012 / $F0 | 0 |
| 8 | (0, 0) | $0000 / $00 | $0008 / $F0 | 0 |
| 8 | (255, 20) | $00FF / $14 | $00FF / $14 | 1 |
| 8 | (10, 211) | $000A / $D3 | $000A / $0F | 0 |

## Differences from the reference

C-BIOS's MSX2 / MSX2+ builds (the subject) do NOTHING here: CLOC / CMASK unchanged and A as the caller left it, in every mode, carry never set ([scratchpad/AE_xsubmv_msx2.out](../../../scratchpad/AE_xsubmv_msx2.out)).

## Open (not measured)

The sets [PG], [LN], [MD], [SN] and [R9] are defined on [the concept page](../concepts/graphics-cursor.md#shared-measurement-setup-every-pages-matrix-assumes-it).

Every case runs on all three references; each machine's result is recorded on its own, and a rule that holds on one generation only names it ([the concept page](../concepts/graphics-cursor.md)). `—` = not measured yet; `n/a` = the mode does not exist on that machine.

| case | inputs | state | what it separates | HB-F900 | NMS 8250 | FS-A1WSX |
|---|---|---|---|---|---|---|
| TR-00 | CLOC / CMASK from MAPXYC (10, 10) | SCREEN 5 | a callable entry vs not | — | — | — |
| TR-01 | MAPXYC (254, 3), (255, 3) | SCREEN 5, 8; [LN] | moves vs stops; the stop's A / F | — | — | — |
| TR-02 | MAPXYC (255, 3), (509, 3), (510, 3), (511, 3) | SCREEN 6 (CMASK $30, $0C, $03), 7; [LN] | the 512-pixel edge vs 255 | — | — | — |
| TR-03 | MAPXYC (255, 3) | SCREEN 2, 3, 4; [MD] | the edge in the MSX1 modes | — | — | — |
| TR-04 | CLOC at X 255, CMASK $F1, $00, $0F planted by hand | SCREEN 5 | the edge test's input (CMASK, CLOC, or a coordinate copy) | — | — | — |
| TR-05 | the same call at the edge, 2 times | SCREEN 5 | a stop is stable (no creep) | — | — | — |
| TR-90 | garbage in BC, DE, HL, IX, IY; entry A, F $00 / $FF; DI / EI | each mode | A and F left (MSX1: an AND's flags on the new mask or CLOC AND 7); registers and interrupts kept | — | — | — |
| TR-91 | CLOC / CMASK from MAPXYC | SCRMOD 2, 3, 4; [MD] | the MSX1 rules ([RIGHTC](../../bios/RIGHTC.md)) through the sub-ROM; SCREEN 4 as 2 | — | — | — |
| TR-92 | CLOC / CMASK from MAPXYC | SCRMOD 10-12 (FS-A1WSX) | the step in the YJK modes (as SCREEN 8?) | n/a | n/a | — |
| TR-93 | CLOC / CMASK from MAPXYC, and CLOC $8000 + offset planted by hand | [PG] in SCREEN 5 / 6 | whether the page is inside CLOC (and kept by the step) | — | — | — |
| TR-94 | a step from MAPXYC (100, 50) | SCREEN 5; [SN] | RAM other than CLOC / CMASK, VRAM, the VDP registers and S#n unchanged | — | — | — |

## Related pages

[The concept page](../concepts/graphics-cursor.md); the MSX1 [RIGHTC](../../bios/RIGHTC.md) (the unchecked move); the other sub-ROM moves
[RIGHTC](RIGHTC.md), [LEFTC](LEFTC.md), [UPC](UPC.md), [DOWNC](DOWNC.md), [TUPC](TUPC.md), [TDOWNC](TDOWNC.md), [TLEFTC](TLEFTC.md); [MAPXYC](MAPXYC.md).

## Tests that cover it

None yet.
