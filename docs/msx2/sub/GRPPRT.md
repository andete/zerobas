<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `GRPPRT` (sub-ROM $0089) — draw a character on a bitmap screen

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the HB-F900, NMS 8250 and FS-A1WSX ([xsubgpp.asm](../../../probes/bios/spec/xsubgpp.asm), [scratchpad/AE_xsubgpp_msx2.out](../../../scratchpad/AE_xsubgpp_msx2.out), decoded by [xsubgpp_decode.py](../../../scratchpad/xsubgpp_decode.py); [xsubgpp2.asm](../../../probes/bios/spec/xsubgpp2.asm), [scratchpad/AE_xsubgpp2_msx2.out](../../../scratchpad/AE_xsubgpp2_msx2.out), decoded by [xsubgpp2_decode.py](../../../scratchpad/xsubgpp2_decode.py) into [AE_xsubgpp2_msx2_decoded.out](../../../scratchpad/AE_xsubgpp2_msx2_decoded.out)).
> Goldfish pass 1 (test writer) 2026-11-23: 12 findings, 7 measured, 0 moved to open.

## Summary

`GRPPRT` (the handbook spells it **GRPRT**) draws the character in A on the graphics screen,
working only in SCREEN 5-8. The main ROM's GRPPRT ($008D) hands SCREEN 5-8 to the sub-ROM and
takes the logical operation from LOGOPR. Position, colour, font, the advance and the wrap are not
published; the MSX1 call ([GRPPRT](../../bios/GRPPRT.md)) draws at GRPACX / GRPACY in FORCLR and
moves on 8 pixels, and the measurement asks how much of that carries over.

## The specification

**Interface.**
- One character to the graphics screen, active only in SCREEN 5-8; in: A, the character code;
  out: none; registers: none changed [P TH A1 SUB-ROM: GRPRT].
- The main-ROM entry ($008D) calls the sub-ROM in SCREEN 5-8 and takes the logical operation code
  in LOGOPR ($FB02) [P TH A1 MAIN-ROM: GRPPRT; legend `*2`]. The sub-ROM entry reads LOGOPR too
  [M xsubgpp2 cases 8, 9, 11].
- "Active only in SCREEN 5-8": in SCREEN 2 nothing is drawn in the character cell, but GRPACX still advances and
  ATRBYT := FORCLR [M xsubgpp case 6; xsubgpp2 case 6]; SCREEN 3 / 4 [A].
- Position: GRPACX ($FCB7) / GRPACY ($FCB9); the colour FORCLR ($F3E9), with ATRBYT ($F3F2) := FORCLR [M, see
  Measured]; the font from CGPNT ($F91F), the glyph perhaps via GETPAT (sub $0105, into PATWRK $FC40) [A].
- Advance, wrap, bottom edge and CR: measured in SCREEN 8 with 212 lines (see Measured); SCREEN 6 / 7 (512 wide),
  192 lines, and the control codes other than CR are [A].
- The glyph's 0 pixels are drawn in BAKCLR, and a T-operation makes the colour-0 pixels of either kind
  transparent [M, see Measured].
- How it draws (CPU writes, PSET / LMMC commands) and whether it waits for CE is [A]; ACPAGE's part
  is [A].
- Interrupts after: ON [M xsubgpp, xsubgpp2, every case, entered with them off].

**Measured** [M] (the same on all three references; FORCLR $05, ATRBYT $0A, BAKCLR $03 all different unless named,
the windows preset $0F):
- **The cell.** The glyph is drawn as an 8 x 8 cell at GRPACX / GRPACY: its 1 pixels in **FORCLR** (not the ATRBYT
  found at entry), its 0 pixels in **BAKCLR** -- the whole cell is written [M xsubgpp case 0; xsubgpp2 case 10]. The
  same in SCREEN 5, per pixel: at X 11 the cell covers X 11-18 and pixels 10 and 19, which share their bytes, are left
  [M xsubgpp case 2; xsubgpp2 case 7].
- **ATRBYT := FORCLR** after a printable character ($05; $00 with FORCLR 0) [M xsubgpp2 cases 0, 1, 5-11]; after CR
  ATRBYT keeps its $0A [M xsubgpp2 cases 2-4]. Whether the pixels are drawn from FORCLR or from the ATRBYT just set
  cannot be told apart from outside the call; the result is the same.
- **LOGOPR is honoured for both kinds of pixel.** XOR (3) over $0F: 1 pixels $0A = $0F XOR FORCLR, 0 pixels $0C = $0F
  XOR BAKCLR [M xsubgpp2 case 8]. TIMP (8) with BAKCLR 0: the 0 pixels are left, the 1 pixels drawn; with FORCLR 0: the
  1 pixels left, the 0 pixels drawn [M xsubgpp2 cases 9, 11]. With both colours non-zero TIMP draws the whole cell
  [M xsubgpp case 1].
- **The advance.** GRPACX += 8 after a character [M xsubgpp case 0]. **CR ($0D): GRPACX := 0 and a line feed**
  [M xsubgpp case 3].
- **The right edge.** A character at X 250 is drawn at X 250-255 only (its first 6 columns, rows 10-17); nothing
  appears at X 0-15 of rows 8-27; then GRPACX := 0 and a line feed (GRPACY 10 -> 18) [M xsubgpp case 4; xsubgpp2
  case 0]. Where between X 248 and 255 the wrap starts is open (GP-06).
- **The line feed** (from CR or the right-edge wrap): GRPACY + 8 when that is at most 211, otherwise 0 -- CR at Y 203
  gives 211, at Y 204 and 207 gives 0; 'A' at (250, 207) gives (0, 0) [M xsubgpp2 cases 1-4]. No scroll: rows 0-19 at
  X 0-15 are untouched [M the same cases]. A character at Y 207 is clipped at row 211: rows 207-211 drawn, 212-215
  left [M xsubgpp2 case 1]; one at Y 207 with no line feed due leaves GRPACY 207 [M xsubgpp case 5].
  Measured in SCREEN 8 with 212 lines only.
- **SCREEN 2.** Nothing is written to the pattern bytes $0100-$023F or the colour bytes $2100-$223F (the character
  cell of (10, 10) is $0108-$010F / $2108-$210F); GRPACX += 8 [M xsubgpp case 6; xsubgpp2 case 6].
- **Registers.** A, BC, DE, HL and IY kept (garbage in) [M xsubgpp2, every case]; IX := $000C after a printable
  character, IX ($0089, EXTROM's) kept after CR [M the same]; F is not a defined output ($60 in xsubgpp, $28 in
  xsubgpp2) [A]. Interrupts ON.

## Differences from the reference

C-BIOS's MSX2 / MSX2+ builds (the subject) draw the cell with their own font (ruled, D-BIOSINT) the same way --
FORCLR / BAKCLR, LOGOPR honoured, per pixel in SCREEN 5, nothing in SCREEN 2, ATRBYT := FORCLR -- but:
- CR is drawn as a character (GRPACX advances, no line feed) [[scratchpad/AE_xsubgpp_msx2.out](../../../scratchpad/AE_xsubgpp_msx2.out) case 3; [scratchpad/AE_xsubgpp2_msx2.out](../../../scratchpad/AE_xsubgpp2_msx2.out) cases 2-4];
- nothing wraps at the right edge (GRPACX 258, GRPACY kept) [[scratchpad/AE_xsubgpp_msx2.out](../../../scratchpad/AE_xsubgpp_msx2.out) case 4; [scratchpad/AE_xsubgpp2_msx2.out](../../../scratchpad/AE_xsubgpp2_msx2.out) cases 0, 1];
- a character at Y 207 is drawn into rows 212-214 instead of being clipped at 211 [[scratchpad/AE_xsubgpp2_msx2.out](../../../scratchpad/AE_xsubgpp2_msx2.out) case 1];
- A out $03 ($00 under TIMP with BAKCLR 0) instead of A kept; IX kept ($0089) [[scratchpad/AE_xsubgpp_msx2.out](../../../scratchpad/AE_xsubgpp_msx2.out); [scratchpad/AE_xsubgpp2_msx2.out](../../../scratchpad/AE_xsubgpp2_msx2.out)].

## On the turbo R

Measured 2026-11-23 (D-TRSPEC) on the FS-A1GT / FS-A1ST: every case gives the same bytes as on the FS-A1WSX, on both models [M] ([AE_trall/xsubgpp.out](../../../scratchpad/AE_trall/xsubgpp.out), [AE_trall/xsubgpp2.out](../../../scratchpad/AE_trall/xsubgpp2.out); overview: [turbor/remeasured.md](../../turbor/remeasured.md)).

## Open (not measured)

The sets [PG], [LG], [LN], [MD], [SN] and [R9] are defined on [the concept page](../concepts/graphics-cursor.md#shared-measurement-setup-every-pages-matrix-assumes-it).

Every case runs on all three references; each machine's result is recorded on its own, and a rule that holds on one generation only names it ([the concept page](../concepts/graphics-cursor.md)). `—` = not measured yet; `n/a` = the mode does not exist on that machine.

| case | inputs | state | what it separates | HB-F900 | NMS 8250 | FS-A1WSX |
|---|---|---|---|---|---|---|
| GP-01 | A 'A' | SCREEN 5, GRPACX/Y (10, 20), GXPOS/GYPOS (100, 100), CLOC elsewhere | which coordinate pair is the position | — | — | — |
| GP-02 | A 'A' | FORCLR 9, ATRBYT 4, BAKCLR 2, LOGOPR 0, over a patterned background | the colour cell; ATRBYT after; whether the glyph's 0 pixels become BAKCLR or stay (SCREEN 8 / 5: FORCLR, BAKCLR, ATRBYT := FORCLR) | S8, S5 | S8, S5 | S8, S5 |
| GP-03 | A 'A' | [LG] except the colour-0 forms, FORCLR 9, ATRBYT 4 | LOGOPR honoured on the sub-ROM entry | — | — | — |
| GP-04 | A 'A' | LOGOPR 8 with FORCLR = ATRBYT = 0 (so the result does not hang on GP-02's answer) | TIMP with the colour 0: nothing drawn (SCREEN 8, FORCLR 0: the 1 pixels left, the 0 pixels in BAKCLR) | S8 | S8 | S8 |
| GP-05 | A 'A' | LOGOPR 8 and 0, FORCLR 9, BAKCLR 0 (TIMP skips only colour 0, so BAKCLR must be 0 to separate) and LOGOPR 3 over a patterned background | the 0 pixels drawn in BAKCLR under IMP and skipped under TIMP, or never drawn (SCREEN 8: drawn under PSET / XOR, skipped under TIMP with BAKCLR 0) | S8 | S8 | S8 |
| GP-06 | A 'A' | GRPACX 248 / 249 / 252 / 255 in SCREEN 5 and 8; 504 / 506 / 511 in SCREEN 6 and 7 | the wrap point and its width (256 vs 512) per mode (SCREEN 8 at X 250: clipped glyph, then the wrap) | S8 250 | S8 250 | S8 250 |
| GP-07 | A 'A' at X 250 and A $0D, both at GRPACY 185, 203, 204, 211, so the line feed is triggered; [LN] | the bottom edge: clip, wrap to 0, or draw into the next page (SCREEN 8, 212 lines: wrap to 0 when Y + 8 > 211; a glyph clipped at 211) | S8 212 lines | S8 212 lines | S8 212 lines |
| GP-08 | A $0D, $0A, $08, $1F, $7F; A $01 then 'A' | SCREEN 5 | control codes: CR / LF meaning, GRPACX / GRPACY high bytes; DEL; the $01 graphic-character prefix (one call or two) | — | — | — |
| GP-09 | A 'A' | SCREEN 6, FORCLR 7 (over 3) | a colour wider than the pixel: masked, or spilt into the neighbour | — | — | — |
| GP-10 | A 'A' | SCREEN 8, FORCLR $C3 | a full-byte colour | — | — | — |
| GP-11 | A 'A' | [PG] | which page receives the glyph | — | — | — |
| GP-12 | A 'A' | SCRMOD 2, 3, 4 with [MD] via the sub-ROM entry | "active only in 5-8": no-op vs the MSX1 drawing | — | — | — |
| GP-13 | A 'A' | CGPNT at a probe font with distinctive glyphs | the font source | — | — | — |
| GP-14 | A 'A' | a long LMMV running at entry; R#45 garbage; [SN] | waits for CE vs corrupts; command registers' residue; commands in the port log; RAM changed (PATWRK?) | — | — | — |
| GP-15 | garbage in BC, DE, HL, IX, IY, F; DI and EI | SCREEN 5 | "registers: none" (A? F?) and the interrupt state after (SCREEN 8: A, BC, DE, HL, IY kept, IX $000C, EI after DI) | S8, DI | S8, DI | S8, DI |
| GP-16 | A 'A' | SCRMOD 10-12 (FS-A1WSX) | drawing in the YJK modes | n/a | n/a | — |
| GP-17 | the GP-01, GP-03, GP-12 and GP-16 inputs | called at the main-ROM GRPPRT ($008D) | the main entry: forwards in 5-8 (`*2`), reads LOGOPR ("0 to 8"), and in SCREEN 2-4 draws the MSX1 way | — | — | — |
| GP-18 | A 'A' | SCREEN 2 / 4 with R#25 CMD set and clear; R#26 / R#27 (horizontal scroll) non-zero | the MSX2+ sub-ROM's drawing outside 5-8, and whether scroll offsets enter the position -- per machine (on the V9938 there is no R#25: the MSX2 rows are the baseline) | — | — | — |
| GP-19 | A 'A' | GRPACX 11 / 12 in SCREEN 6 (four pixels a byte) and 7 | the per-pixel drawing in the 2- and 4-bit modes at a shared byte (SCREEN 5 measured: per pixel) | — | — | — |

## Related pages

[The concept page](../concepts/graphics-cursor.md); the MSX1 [GRPPRT](../../bios/GRPPRT.md);
[SETC](SETC.md), [MAPXYC](MAPXYC.md), [NVBXLN](NVBXLN.md) (the other LOGOPR readers).

## Tests that cover it

None yet.
