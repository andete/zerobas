<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `MAPXYC` (sub-ROM $0091) — turn coordinates into a graphics position

> **Spec:** DRAFT 0 (2026-11-23), from the published interface only; nothing measured yet. References to measure: HB-F900, NMS 8250, FS-A1WSX.

## Summary

`MAPXYC` is assumed to be the sub-ROM's counterpart of the main ROM's [MAPXYC](../../bios/MAPXYC.md)
($0111): it turns X (BC) and Y (DE) into the current graphics position, CLOC and CMASK, for the
mode in SCRMOD -- in SCREEN 5-8 by a cursor model the handbook does not publish. Which model it is
(byte address and pixel mask, or the coordinates themselves) is the first thing to measure; every
other cursor call depends on the answer.

## The specification

**Interface.**
- No published entry: the handbook's sub-ROM listing has nothing at $0091 [P TH A1 SUB-ROM, by
  absence]; the name is the C-BIOS peer's. That the references have a callable entry here is [A]
  (case MX-00).
- Called through EXTROM with IX = $0091 [P TH A1 SUB-ROM, preamble].
- In: X in C (or BC), Y in E (or DE), as the MSX1 call takes them [A]; SCRMOD, and in SCREEN 2 /
  3 GRPCGP / MLTCGP as the MSX1 call reads them [A]. In SCREEN 6 / 7 X runs to 511, so B must take
  part [A].
- Out: CLOC ($F92A) and CMASK ($F92C) [A]; their bitmap meaning is one of the models in
  [the concept page](../concepts/graphics-cursor.md#the-cursor-model--rival-rules-to-separate) [A].
  Registers and flags: unpublished [A]; MSX1 leaves HL = CLOC [A, by analogy].
- Pixel layout per mode: [the concept page](../concepts/graphics-cursor.md#the-bitmap-modes-pixel-layout)
  [P TH 4 §3.6-§3.9].
- Whether ACPAGE enters CLOC (a page's $8000 / $10000 offset) is [A].
- VDP registers: none written [A] (the MSX1 call writes none, measured there).

## Differences from the reference

Not measured yet.

## Open (not measured)

The sets [PG], [LG], [LN], [MD], [SN] and [R9] are defined on [the concept page](../concepts/graphics-cursor.md#shared-measurement-setup-every-pages-matrix-assumes-it).

Every case runs on all three references; each machine's result is recorded on its own, and a rule that holds on one generation only names it ([the concept page](../concepts/graphics-cursor.md)). `—` = not measured yet; `n/a` = the mode does not exist on that machine.

| case | inputs | state | what it separates | HB-F900 | NMS 8250 | FS-A1WSX |
|---|---|---|---|---|---|---|
| MX-00 | any | SCRMOD 5 | a callable entry vs an unused address (RET / garbage) | — | — | — |
| MX-01 | X 0, Y 0 | SCREEN 5, ACPAGE 0 | baseline: B gives CLOC 0 / CMASK $F0, C gives 0 / 0 | — | — | — |
| MX-02 | X 1, Y 0; X 2, Y 0 | SCREEN 5 | B: CMASK $0F then $F0 with CLOC 0 then 1; C: CLOC 1 then 2 | — | — | — |
| MX-03 | X 0, Y 1; X 0, Y 211 | SCREEN 5 | B: CLOC 128 / 27008; C: CLOC 0, CMASK 1 / 211 | — | — | — |
| MX-04 | X 255, Y 211 | SCREEN 5 / 8 | the last pixel: B's $69FF (5) vs $D3FF (8) | — | — | — |
| MX-05 | X 4, 5, 6, 7; Y 3 | SCREEN 6 | B: masks $C0 / $30 / $0C / $03 at CLOC 385; M: $08 / $04 / $02 / $01 | — | — | — |
| MX-06 | X 300, Y 3 | SCREEN 6 / 7 | B (B taking part) vs X AND 255 (B ignored) | — | — | — |
| MX-07 | X 0, Y 0 | SCREEN 5 and 6 over [PG] | the page in CLOC ($8000 x ACPAGE, ACPAGE 2 wrapping to 0) vs not. In SCREEN 7 / 8 CLOC cannot show the page (concept page); SETC's SC-08 and READC's RD-06 do | — | — | — |
| MX-08 | X 256..511 / Y 212..255 / X, Y $FFFF | SCREEN 5, 8; [LN] | out-of-range coordinates: wrapped, clipped, or computed through | — | — | — |
| MX-09 | X 100, Y 50 | SCRMOD 2, 3, 4; [MD] | the MSX1 rules ([MAPXYC](../../bios/MAPXYC.md)) through the sub-ROM entry; SCREEN 4 as 2 or as 3 | — | — | — |
| MX-10 | X 100, Y 50 | SCRMOD 10, 11, 12 (FS-A1WSX) | as SCREEN 8 (byte per pixel) vs something else | n/a | n/a | — |
| MX-11 | entry A, F, HL, IX, IY garbage | each mode | A / F / HL / D left (MSX1: HL = CLOC, D = X in SCREEN 2) | — | — | — |
| MX-12 | X 100, Y 50 | R#9 LN 0 vs 1 | whether the 192 / 212-line choice affects the mapping | — | — | — |
| MX-13 | X 100, Y 50; then X 37, Y 120 | SCREEN 5, 7; GRPACX/Y and GXPOS/GYPOS set to two other points; [SN] | the whole-RAM diff: a hidden coordinate copy (model C's Y, or X above 255) and where it lives; GRPACX/Y and GXPOS/GYPOS untouched | — | — | — |
| MX-14 | X 100, Y 50 | SCREEN 5; [SN] | VRAM, the VDP registers and S#n unchanged ("touches no VDP register") | — | — | — |
| MX-15 | X 100, Y 50 | SCREEN 5, called at the main-ROM MAPXYC ($0111) | the main entry forwards to the sub-ROM in SCREEN 5-8 vs runs the MSX1 rule | — | — | — |
| MX-16 | X 100, Y 50 | SCREEN 5 with R#25 / R#26 / R#27 non-zero (V9958 scroll) | whether the MSX2+ sub-ROM folds a scroll offset into CLOC -- per machine (on the V9938 there is no R#25: the MSX2 rows are the baseline) | — | — | — |

## Related pages

[The concept page](../concepts/graphics-cursor.md); the MSX1 [MAPXYC](../../bios/MAPXYC.md); the
sub-ROM cursor moves [RIGHTC](RIGHTC.md), [LEFTC](LEFTC.md), [UPC](UPC.md), [DOWNC](DOWNC.md),
[TUPC](TUPC.md), [TDOWNC](TDOWNC.md), [TRIGHT](TRIGHT.md), [TLEFTC](TLEFTC.md); [SCALXY](SCALXY.md)
(its usual predecessor); [READC](READC.md), [SETC](SETC.md).

## Tests that cover it

None yet.
