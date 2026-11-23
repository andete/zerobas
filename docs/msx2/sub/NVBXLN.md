<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `NVBXLN` (sub-ROM $00C9) — draw a box

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the HB-F900, NMS 8250 and FS-A1WSX ([xsubbox.asm](../../../probes/bios/spec/xsubbox.asm), [scratchpad/AE_xsubbox_msx2.out](../../../scratchpad/AE_xsubbox_msx2.out), decoded by [xsubbox_decode.py](../../../scratchpad/xsubbox_decode.py); [xsubbox2.asm](../../../probes/bios/spec/xsubbox2.asm), [scratchpad/AE_xsubbox2_msx2.out](../../../scratchpad/AE_xsubbox2_msx2.out), decoded by [xsubbox2_decode.py](../../../scratchpad/xsubbox2_decode.py) into [AE_xsubbox2_msx2_decoded.out](../../../scratchpad/AE_xsubbox2_msx2_decoded.out)).
> Goldfish pass 1 (test writer) 2026-11-23: 11 findings, 6 measured, 1 moved to open.

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
- ATRBYT is **$F3F2** in the work-area listing [P TH A4]; the call reads $F3F2 [M xsubbox case 0, SCREEN 8;
  SCREEN 5 open, BL-01].
- Called through EXTROM, IX = $00C9 [P TH A1 SUB-ROM, preamble]. EXTROM keeps IY and the alternate
  registers [P TH A1 MAIN-ROM: EXTROM]; "all" therefore means AF, BC, DE, HL (IX by the convention).
- The modes: SCREEN 5-8 [A] (the VDP commands are guaranteed only there, [P TH 4 §6.2]); SCREEN 2-4
  unpublished [A].
- LOGOPR's encoding: the table 4.6 code [P TH 4 §6.3 for the codes; that LOGOPR holds them A].
- The method [M xsubbox2 cases 0-6, port log; SCREEN 8]: four LINE commands, each preceded by a wait for S#2 CE
  (see Measured); the command registers R#36-R#46 written through R#17 / port $9B [the command P TH 4 §6.5.9]. A wait
  for CE after the last command is not in the log; S#2 on return is unmeasured (BL-10).
- The Y coordinates: on the active page (ACPAGE x 256 added) or absolute VDP Y [A]; clipping of
  points off the screen [A].
- The cells: GRPACX / GRPACY kept, GXPOS / GYPOS changed (see Measured) [M xsubbox2 cases 0-6]; CLOC / CMASK [A].

**Measured** [M] (the same on all three references; SCREEN 8, the window X 8-23 x Y 9-16 read back; every OUT to
$99 / $9B logged in xsubbox2):
- **The figure.** The outline of (BC, DE)-(GXPOS, GYPOS), both corners INCLUSIVE ((10, 10)-(20, 15): rows 10 and 15
  from X 10 to 20, columns 10 and 20 between) [M xsubbox cases 0, 1; xsubbox2 cases 0-3]. The same box from all four
  corner orders: (10, 10)-(20, 15), (20, 15)-(10, 10), (20, 10)-(10, 15), (10, 15)-(20, 10) [M xsubbox cases 0, 1;
  xsubbox2 cases 0, 1], and (12, 11)-(19, 14) in both orders [M xsubbox2 cases 2, 3].
- **The commands.** Four LINEs, the corners sorted first (identical command bytes for every corner order): the
  bottom edge from (max X, max Y) leftwards (ARG $04), the top edge from (max X, min Y) leftwards, then the right and
  the left side from (x, min Y + 1) downwards (ARG $01) with NX = height - 2, so each side stops short of the corners
  and **every pixel is drawn once** [M xsubbox2 cases 0-6, the $9B log]. With LOGOPR 3 (XOR) over $0C every outline
  pixel, the corners too, reads $09 = $0C XOR ATRBYT $05 -- not $F3F3's $0A [M xsubbox2 case 4].
- **The colour is ATRBYT at $F3F2**, not the handbook's $F3F3: with $F3F2 $05 and $F3F3 $0A every drawn pixel is $05
  [M xsubbox case 0]; CLR = $05 in every LINE [M xsubbox2 cases 0-6].
- **LOGOPR** goes into R#46's low nibble: CMD = $70 OR LOGOPR, for LOGOPR 0, 2 (OR: $0D over $08), 3 (XOR) and 8 (TIMP:
  $05 over $0C) [M xsubbox2 cases 0, 4-6; xsubbox case 5]. Codes 1, 4-7, 9-15 are not measured (BL-04).
- **After.** GRPACX / GRPACY kept (markers 77 / 33 and 44 / 55) [M xsubbox2 cases 0-6]. GXPOS / GYPOS = (min X,
  max Y - 1), which is the last LINE's end point: (10, 14) for the box (10, 10)-(20, 15), (12, 13) for (12, 11)-(19, 14),
  whatever the corner order [M xsubbox cases 0, 1; xsubbox2 cases 0-3]. On every case measured the two readings
  coincide; a box less than 3 high separates them (BL-16). R#36-R#45 hold the last LINE's registers with DY advanced
  past its end [M xsubbox case 0]. **A = the last command byte written, $70 OR LOGOPR** ($70, $72, $73, $78) [M xsubbox
  cases 0, 5; xsubbox2 cases 4-6]; F follows it ($20, $24, $20, $2C) and is not a defined output [A].

## Differences from the reference

C-BIOS's MSX2 / MSX2+ builds (the subject), measured on the same cases:
- With the corners given as (min X, min Y)-(max X, max Y) the pixels are the reference's (four LINEs, but drawn from
  the minimum corner and with the sides running the full height), so under XOR the four corners are drawn twice and
  read back as the preset [[scratchpad/AE_xsubbox_msx2.out](../../../scratchpad/AE_xsubbox_msx2.out) case 0, 5; [scratchpad/AE_xsubbox2_msx2.out](../../../scratchpad/AE_xsubbox2_msx2.out) cases 2, 4].
- With any other corner order the figure is wrong: the sides run past the box (pixels at Y 9 and 16) and a horizontal
  edge continues past max X -- C-BIOS writes a negative NX ($FFF6) instead of sorting [[scratchpad/AE_xsubbox_msx2.out](../../../scratchpad/AE_xsubbox_msx2.out) case 1; [scratchpad/AE_xsubbox2_msx2.out](../../../scratchpad/AE_xsubbox2_msx2.out) cases 0, 1, 3].
- GXPOS / GYPOS are left at the end point, not (min X, max Y - 1) [[scratchpad/AE_xsubbox_msx2.out](../../../scratchpad/AE_xsubbox_msx2.out); [scratchpad/AE_xsubbox2_msx2.out](../../../scratchpad/AE_xsubbox2_msx2.out)].

## Open (not measured)

The sets [PG], [LG], [LN], [MD] and [SN] are defined on [the concept page](../concepts/graphics-cursor.md#shared-measurement-setup-every-pages-matrix-assumes-it).

Every case runs on all three references; each machine's result is recorded on its own, and a rule that holds on one generation only names it ([the concept page](../concepts/graphics-cursor.md)). `—` = not measured yet; `n/a` = the mode does not exist on that machine.

| case | inputs | state | what it separates | HB-F900 | NMS 8250 | FS-A1WSX |
|---|---|---|---|---|---|---|
| BL-01 | (10, 10)-(40, 30) | SCREEN 5, ATRBYT ($F3F2) 9, the byte at $F3F3 4 | the colour cell: $F3F2 vs the handbook's $F3F3 (SCREEN 8 settled: $F3F2, [M xsubbox case 0]) | — | — | — |
| BL-02 | (40, 30)-(10, 10); (40, 10)-(10, 30) | SCREEN 5 | corner order: the same box from any two opposite corners | S8: same box, 4 orders | S8: same box, 4 orders | S8: same box, 4 orders |
| BL-03 | (10, 10)-(40, 30) | LOGOPR 3 (EOR) over a filled area whose preset XOR ATRBYT differs from the byte at $F3F3; [SN] port log | each corner drawn once vs twice, and the commands issued | S8: 4 LINEs, once [M xsubbox2 4] | S8: 4 LINEs, once | S8: 4 LINEs, once |
| BL-04 | (10, 10)-(40, 30) | [LG] (ATRBYT 0 and 13 for the T-form; the undefined 5 and 13) | LOGOPR applied; T-forms; undefined codes passed, masked or refused; A out ($70 OR LOGOPR for 0, 2, 3, 8 measured) | S8: 0, 2, 3, 8 | S8: 0, 2, 3, 8 | S8: 0, 2, 3, 8 |
| BL-05 | (10, 10)-(10, 30); (10, 10)-(40, 10); (10, 10)-(10, 10) | SCREEN 5, LOGOPR 3 over a fill; [SN] port log | degenerate boxes: a line or a point drawn once or twice (EOR parity plus the command count) | — | — | — |
| BL-06 | (-5, 10)-(300, 250) | SCREEN 5, 6; [LN] | clipping: to 255 / 511 and 211 / 191, or wrapped into VRAM | — | — | — |
| BL-07 | (10, 10)-(40, 30) | [PG] | the page drawn on (ACPAGE vs DPPAGE vs 0) | — | — | — |
| BL-08 | (10, 10)-(40, 30) | SCREEN 6 (ATRBYT 7), 7, 8 (ATRBYT $C3) | the colour width per mode | — | — | — |
| BL-09 | the same | a long LMMV running at entry; R#45 DIX / DIY / MXD garbage | waits for CE; ARG rewritten | — | — | — |
| BL-10 | the same | [SN] | S#2 on return (returns before the last command ends); R#36-R#46 residue (measured S8: the last LINE, DY advanced) | — | — | — |
| BL-11 | the same | GRPACX/Y, CLOC / CMASK, GXPOS / GYPOS distinct markers | which cells it changes (measured S8: GRPACX/Y kept, GXPOS/GYPOS := (min X, max Y - 1); CLOC / CMASK open) | S8 part | S8 part | S8 part |
| BL-12 | garbage in IY, IX, the alternate set; DI / EI | SCREEN 5 | what "all" covers; the interrupt state after | — | — | — |
| BL-13 | (10, 10)-(40, 30) | SCRMOD 2, 3, 4 with [MD] | drawing in the MSX1-shaped modes vs nothing | — | — | — |
| BL-14 | the same | SCRMOD 10-12 (FS-A1WSX) | the YJK modes | n/a | n/a | — |
| BL-15 | (10, 10)-(40, 30) | SCREEN 2 / 4 with R#25 CMD set and clear | boxes outside 5-8 on the V9958 -- per machine (on the V9938 there is no R#25: the MSX2 rows are the baseline) | — | — | — |
| BL-16 | (10, 10)-(20, 11); (10, 10)-(20, 12); (10, 10)-(10, 10) | SCREEN 8, GXPOS / GYPOS read after; port log | GXPOS / GYPOS after: "(min X, max Y - 1)" vs "the last LINE's end" (they coincide on every box 3 or more high); the side LINEs' NX when height - 2 is 0 or negative | — | — | — |

## Related pages

[The concept page](../concepts/graphics-cursor.md); [NVBXFL](NVBXFL.md) (the filled box);
[DOGRPH](DOGRPH.md); [SETATR](SETATR.md).

## Tests that cover it

None yet.
