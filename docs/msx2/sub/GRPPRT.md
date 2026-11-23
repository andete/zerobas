<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `GRPPRT` (sub-ROM $0089) — draw a character on a bitmap screen

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the HB-F900, NMS 8250 and FS-A1WSX ([xsubgpp.asm](../../../probes/bios/spec/xsubgpp.asm), [scratchpad/AE_xsubgpp_msx2.out](../../../scratchpad/AE_xsubgpp_msx2.out), decoded by `scratchpad/xsubgpp_decode.py`).

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
  in LOGOPR ($FB02) [P TH A1 MAIN-ROM: GRPPRT; legend `*2`]. That the sub-ROM entry reads LOGOPR
  too is [A].
- What "active only in SCREEN 5-8" does in other modes -- nothing, or the MSX1 drawing -- is [A].
- Position: GRPACX ($FCB7) / GRPACY ($FCB9) [A, as MSX1]; the colour FORCLR ($F3E9), with ATRBYT
  ($F3F2) := FORCLR [A, as MSX1]; the font from CGPNT ($F91F), the glyph perhaps via GETPAT (sub
  $0105, into PATWRK $FC40) [A].
- Advance: 8 pixels in X [A]; the wrap at X 255 (SCREEN 5 / 8) or 511 (6 / 7) [A]; the bottom at Y
  191 or 211 [A]; CR ($0D) a line feed and the other control codes nothing [A, as MSX1].
- Whether the glyph's 0 pixels are drawn (in BAKCLR, or left alone), and whether a T-operation
  makes them transparent, is [A].
- How it draws (CPU writes, PSET / LMMC commands) and whether it waits for CE is [A]; ACPAGE's part
  is [A].
- Interrupts after: [A] (the MSX1 call leaves them on).

**Measured** [M] (the same on all three references; FORCLR $05, ATRBYT $0A, BAKCLR $03 all different, the window
preset $0F):
- The glyph is drawn as an 8 x 8 cell at GRPACX / GRPACY: its 1 pixels in **FORCLR** (not ATRBYT), its 0 pixels in
  **BAKCLR** -- the whole cell is written. **LOGOPR 8 (TIMP) does not make the 0 pixels transparent**: the same cell.
  The same in SCREEN 5 (two pixels a byte).
- GRPACX += 8 after a character; **CR ($0D): GRPACX := 0, GRPACY += 8**; a character at X 250 wraps: GRPACX := 0,
  GRPACY += 8; at Y 207 GRPACY stays (no wrap, no scroll).
- In SCREEN 2 the call still advances GRPACX (by 8) -- not "nothing".
- Out: A kept, F $60, interrupts ON.

## Differences from the reference

C-BIOS's MSX2 / MSX2+ builds (the subject) draw the cell with their own font (ruled, D-BIOSINT) the same way, but CR is
drawn as a character (GRPACX advances, no line feed) and nothing wraps at the right edge (GRPACX 258); A out $03
([scratchpad/AE_xsubgpp_msx2.out](../../../scratchpad/AE_xsubgpp_msx2.out)).

## Open (not measured)

The sets [PG], [LG], [LN], [MD], [SN] and [R9] are defined on [the concept page](../concepts/graphics-cursor.md#shared-measurement-setup-every-pages-matrix-assumes-it).

Every case runs on all three references; each machine's result is recorded on its own, and a rule that holds on one generation only names it ([the concept page](../concepts/graphics-cursor.md)). `—` = not measured yet; `n/a` = the mode does not exist on that machine.

| case | inputs | state | what it separates | HB-F900 | NMS 8250 | FS-A1WSX |
|---|---|---|---|---|---|---|
| GP-01 | A 'A' | SCREEN 5, GRPACX/Y (10, 20), GXPOS/GYPOS (100, 100), CLOC elsewhere | which coordinate pair is the position | — | — | — |
| GP-02 | A 'A' | FORCLR 9, ATRBYT 4, BAKCLR 2, LOGOPR 0, over a patterned background | the colour cell; ATRBYT after; whether the glyph's 0 pixels become BAKCLR or stay | — | — | — |
| GP-03 | A 'A' | [LG] except the colour-0 forms, FORCLR 9, ATRBYT 4 | LOGOPR honoured on the sub-ROM entry | — | — | — |
| GP-04 | A 'A' | LOGOPR 8 with FORCLR = ATRBYT = 0 (so the result does not hang on GP-02's answer) | TIMP with the colour 0: nothing drawn | — | — | — |
| GP-05 | A 'A' | LOGOPR 8 and 0, FORCLR 9, BAKCLR 2 (non-zero), over a patterned background | whether the glyph's 0 pixels are drawn (in BAKCLR) under IMP and skipped under TIMP, or never drawn | — | — | — |
| GP-06 | A 'A' | GRPACX 250 / 252 / 255 in SCREEN 5 and 8; 506 / 511 in SCREEN 6 and 7 | the advance, the wrap point and its width (256 vs 512) per mode | — | — | — |
| GP-07 | A 'A' | GRPACY 185, 205, 211; [LN] | the bottom edge: clip, wrap to 0, or draw into the next page | — | — | — |
| GP-08 | A $0D, $0A, $08, $1F, $7F; A $01 then 'A' | SCREEN 5 | control codes: CR / LF meaning, GRPACX / GRPACY high bytes; DEL; the $01 graphic-character prefix (one call or two) | — | — | — |
| GP-09 | A 'A' | SCREEN 6, FORCLR 7 (over 3) | a colour wider than the pixel: masked, or spilt into the neighbour | — | — | — |
| GP-10 | A 'A' | SCREEN 8, FORCLR $C3 | a full-byte colour | — | — | — |
| GP-11 | A 'A' | [PG] | which page receives the glyph | — | — | — |
| GP-12 | A 'A' | SCRMOD 2, 3, 4 with [MD] via the sub-ROM entry | "active only in 5-8": no-op vs the MSX1 drawing | — | — | — |
| GP-13 | A 'A' | CGPNT at a probe font with distinctive glyphs | the font source | — | — | — |
| GP-14 | A 'A' | a long LMMV running at entry; R#45 garbage; [SN] | waits for CE vs corrupts; command registers' residue; commands in the port log; RAM changed (PATWRK?) | — | — | — |
| GP-15 | garbage in BC, DE, HL, IX, IY, F; DI and EI | SCREEN 5 | "registers: none" (A? F?) and the interrupt state after | — | — | — |
| GP-16 | A 'A' | SCRMOD 10-12 (FS-A1WSX) | drawing in the YJK modes | n/a | n/a | — |
| GP-17 | the GP-01, GP-03, GP-12 and GP-16 inputs | called at the main-ROM GRPPRT ($008D) | the main entry: forwards in 5-8 (`*2`), reads LOGOPR ("0 to 8"), and in SCREEN 2-4 draws the MSX1 way | — | — | — |
| GP-18 | A 'A' | SCREEN 2 / 4 with R#25 CMD set and clear; R#26 / R#27 (horizontal scroll) non-zero | the MSX2+ sub-ROM's drawing outside 5-8, and whether scroll offsets enter the position -- per machine (on the V9938 there is no R#25: the MSX2 rows are the baseline) | — | — | — |

## Related pages

[The concept page](../concepts/graphics-cursor.md); the MSX1 [GRPPRT](../../bios/GRPPRT.md);
[SETC](SETC.md), [MAPXYC](MAPXYC.md), [NVBXLN](NVBXLN.md) (the other LOGOPR readers).

## Tests that cover it

None yet.
