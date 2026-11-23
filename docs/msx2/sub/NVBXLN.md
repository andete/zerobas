<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `NVBXLN` (sub-ROM $00C9) — draw a box

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the HB-F900, NMS 8250 and FS-A1WSX ([xsubbox.asm](../../../probes/bios/spec/xsubbox.asm), [scratchpad/AE_xsubbox_msx2.out](../../../scratchpad/AE_xsubbox_msx2.out), decoded by `scratchpad/xsubbox_decode.py`).

## Summary

`NVBXLN` draws the outline of a rectangle from the point (BC, DE) to the point (GXPOS, GYPOS) in
ATRBYT, combined with what is there by the logical operation in LOGOPR. It is one of the three
entries in this area the handbook publishes. Unpublished: the modes it works in, whether it draws
with the VDP's LINE / LMMV commands, how the corners are drawn (which an EOR shows), clipping, the
active page, and what it leaves in the cursor cells.

## The specification

**Interface.**
- Draws a box; in: the start point X in BC, Y in DE; the end point X in GXPOS ($FCB3), Y in GYPOS
  ($FCB5); the colour in ATRBYT, given as **$F3F3**; the logical operation code in LOGOPR ($FB02);
  out: none; registers: all changed [P TH A1 SUB-ROM: NVBXLN].
- ATRBYT is **$F3F2** in the work-area listing [P TH A4]; which cell the call reads is [A] (case BL-01).
- Called through EXTROM, IX = $00C9 [P TH A1 SUB-ROM, preamble]. EXTROM keeps IY and the alternate
  registers [P TH A1 MAIN-ROM: EXTROM]; "all" therefore means AF, BC, DE, HL (IX by the convention).
- The modes: SCREEN 5-8 [A] (the VDP commands are guaranteed only there, [P TH 4 §6.2]); SCREEN 2-4
  unpublished [A].
- LOGOPR's encoding: the table 4.6 code [P TH 4 §6.3 for the codes; that LOGOPR holds them A].
- The method [A]: four LINE commands, or two LINE and two LMMV, or CPU writes; the command
  registers R#36-R#46 written [P TH 4 §6.5.9 for LINE; its use here A]; waits for CE at entry
  and / or at exit [A].
- The Y coordinates: on the active page (ACPAGE x 256 added) or absolute VDP Y [A]; clipping of
  points off the screen [A].
- The cells: GRPACX / GRPACY, CLOC / CMASK, GXPOS / GYPOS kept or changed [A].

**Measured** [M] (the same on all three references; SCREEN 8, the window X 8-23 x Y 9-16 read back): the
outline of (BC, DE)-(GXPOS, GYPOS), both corners INCLUSIVE ((10, 10)-(20, 15): rows 10 and 15 from X 10 to 20, columns
10 and 20 between), the same with the corners in either order. **The colour is ATRBYT at $F3F2**, not the handbook's $F3F3: with $F3F2 $05 and $F3F3 $0A every drawn pixel is $05. With LOGOPR 3 (XOR) over $0F every outline pixel
reads $0A -- the corners too: each pixel is drawn once. After: GXPOS / GYPOS = (10, 14), the last side's start; A $70,
F $20.

## Differences from the reference

C-BIOS's MSX2 / MSX2+ builds (the subject) draw a different figure: the sides run past the corners (pixels at Y 9
and 16) and a horizontal edge continues past X 20; under XOR the top and bottom edges stop short of the corners; GXPOS
/ GYPOS are left at the end point ([scratchpad/AE_xsubbox_msx2.out](../../../scratchpad/AE_xsubbox_msx2.out)).

## Open (not measured)

The sets [PG], [LG], [LN], [MD] and [SN] are defined on [the concept page](../concepts/graphics-cursor.md#shared-measurement-setup-every-pages-matrix-assumes-it).

Every case runs on all three references; each machine's result is recorded on its own, and a rule that holds on one generation only names it ([the concept page](../concepts/graphics-cursor.md)). `—` = not measured yet; `n/a` = the mode does not exist on that machine.

| case | inputs | state | what it separates | HB-F900 | NMS 8250 | FS-A1WSX |
|---|---|---|---|---|---|---|
| BL-01 | (10, 10)-(40, 30) | SCREEN 5, ATRBYT ($F3F2) 9, the byte at $F3F3 4 | the colour cell: $F3F2 vs the handbook's $F3F3 | — | — | — |
| BL-02 | (40, 30)-(10, 10); (40, 10)-(10, 30) | SCREEN 5 | corner order: the same box from any two opposite corners | — | — | — |
| BL-03 | (10, 10)-(40, 30) | LOGOPR 3 (EOR) over a filled area; [SN] port log and S#2 sampled during the call | each corner drawn once vs twice (EOR shows only the parity) together with the number of LINE / LMMV commands issued and their parameters (4 LINEs vs 2 LINEs + 2 LMMVs vs CPU writes) | — | — | — |
| BL-04 | (10, 10)-(40, 30) | [LG] (ATRBYT 0 and 13 for the T-form; the undefined 5 and 13) | LOGOPR applied; T-forms; undefined codes passed, masked or refused | — | — | — |
| BL-05 | (10, 10)-(10, 30); (10, 10)-(40, 10); (10, 10)-(10, 10) | SCREEN 5, LOGOPR 3 over a fill; [SN] port log | degenerate boxes: a line or a point drawn once or twice (EOR parity plus the command count) | — | — | — |
| BL-06 | (-5, 10)-(300, 250) | SCREEN 5, 6; [LN] | clipping: to 255 / 511 and 211 / 191, or wrapped into VRAM | — | — | — |
| BL-07 | (10, 10)-(40, 30) | [PG] | the page drawn on (ACPAGE vs DPPAGE vs 0) | — | — | — |
| BL-08 | (10, 10)-(40, 30) | SCREEN 6 (ATRBYT 7), 7, 8 (ATRBYT $C3) | the colour width per mode | — | — | — |
| BL-09 | the same | a long LMMV running at entry; R#45 DIX / DIY / MXD garbage | waits for CE; ARG rewritten | — | — | — |
| BL-10 | the same | [SN] | S#2 on return (returns before the last command ends); R#36-R#46 residue (the last command's DX / DY / NX / NY / CLR / ARG / CMR) | — | — | — |
| BL-11 | the same | GRPACX/Y, CLOC / CMASK, GXPOS / GYPOS distinct markers | which cells it changes (does the end become the "last point"?) | — | — | — |
| BL-12 | garbage in IY, IX, the alternate set; DI / EI | SCREEN 5 | what "all" covers; the interrupt state after | — | — | — |
| BL-13 | (10, 10)-(40, 30) | SCRMOD 2, 3, 4 with [MD] | drawing in the MSX1-shaped modes vs nothing | — | — | — |
| BL-14 | the same | SCRMOD 10-12 (FS-A1WSX) | the YJK modes | n/a | n/a | — |
| BL-15 | (10, 10)-(40, 30) | SCREEN 2 / 4 with R#25 CMD set and clear | boxes outside 5-8 on the V9958 -- per machine (on the V9938 there is no R#25: the MSX2 rows are the baseline) | — | — | — |

## Related pages

[The concept page](../concepts/graphics-cursor.md); [NVBXFL](NVBXFL.md) (the filled box);
[DOGRPH](DOGRPH.md); [SETATR](SETATR.md).

## Tests that cover it

None yet.
