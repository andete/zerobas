<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `SCANR` (sub-ROM $00C1) — scan right for the PAINT border

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the HB-F900, NMS 8250 and FS-A1WSX ([xsubscan.asm](../../../probes/bios/spec/xsubscan.asm), [scratchpad/AE_xsubscan_msx2.out](../../../scratchpad/AE_xsubscan_msx2.out)).

## Summary

`SCANR` is assumed to be the sub-ROM's counterpart of the main ROM's [SCANR](../../bios/SCANR.md)
($012C), PAINT's right-hand scan: from the current position it skips border-colour pixels (counting
DE down), then counts -- and, when B is not 0, paints -- the run of other pixels up to the next
border pixel. In the bitmap modes the VDP's SRCH command finds a colour along a line, which the call
may use; the border cell, the paint method and LOGOPR's part are unpublished.

## The specification

**Interface.**
- No published entry at $00C1 [P TH A1 SUB-ROM, by absence]; a callable entry is [A] (case SR-00).
- In [A, as MSX1]: CLOC / CMASK, B (paint or not), DE (the skip count), the border colour BRDATR
  ($FCB2: "the border colour used by PAINT" [P TH A4]), ATRBYT. Out [A, as MSX1]: HL the run's
  length, DE the counted-down skip, CLOC / CMASK the stopping pixel, CSAVEA / CSAVEM ($F942 /
  $F944, [P TH A4] calls them a reservation area) the run's start.
- The scan [A]: SRCH (border colour in R#44, EQ, DIX 0; the found X in S#8 / S#9 and BD in S#2
  bit 4, [P TH 4 §6.5.10 for the command]) or per-pixel CPU reads. The paint [A]: LMMV, LINE, or
  per-pixel writes; with or without LOGOPR.
- The right edge: X 255 (SCREEN 5 / 8) or 511 (6 / 7) [A]; MSX1: interrupts on after [A here].

**Measured** [M] (the same on all three references; SCREEN 8, line 50 $00 with the border $0F at X 30 and 100, the
start (60, 50) set by MAPXYC, ATRBYT $05): the entry $00C1 IS callable. With B 1 and **DE 1** it paints X 60-99 --
the start pixel included, up to the border -- and returns HL 40 (the run), CLOC 100 / CMASK 50 (the border pixel), DE
1, CSAVEA / CSAVEM := 60 / 50 (the start). With **DE 0** it returns at once (HL 0, nothing painted); with DE $FFFF
likewise, DE coming back 0. Interrupts ON.

## Differences from the reference

C-BIOS's MSX2 / MSX2+ builds (the subject) do nothing here (HL garbage, no paint, CLOC unchanged) ([scratchpad/AE_xsubscan_msx2.out](../../../scratchpad/AE_xsubscan_msx2.out)).

## Open (not measured)

The sets [PG], [LG], [LN], [MD] and [SN] are defined on [the concept page](../concepts/graphics-cursor.md#shared-measurement-setup-every-pages-matrix-assumes-it).

Every case runs on all three references; each machine's result is recorded on its own, and a rule that holds on one generation only names it ([the concept page](../concepts/graphics-cursor.md)). `—` = not measured yet; `n/a` = the mode does not exist on that machine.

| case | inputs | state | what it separates | HB-F900 | NMS 8250 | FS-A1WSX |
|---|---|---|---|---|---|---|
| SR-00 | B 0, DE 0 | SCREEN 5, MAPXYC (10, 10) | a callable entry vs not | — | — | — |
| SR-01 | B 1, DE 5 | SCREEN 5, a row: 3 border pixels, a 20-pixel run, a border | skip, count, paint; HL, DE, CLOC / CMASK, CSAVEA / CSAVEM | — | — | — |
| SR-02 | B 0, B 1, B $80 | the same | paint gated by B as a whole byte vs one bit (MSX1 SCREEN 2) vs always (MSX1 SCREEN 3) | — | — | — |
| SR-03 | DE 2 with 3 border pixels first; DE 0 starting on a border pixel; DE $FFFF | SCREEN 5 | the skip exhausted on a border pixel (MSX1: HL 0, nothing painted); DE 0 as 0 or 65536; DE counted down past 0 | — | — | — |
| SR-04 | B 1 | no border to the right | the run ends at X 255 / 511 (SCREEN 5 / 7) | — | — | — |
| SR-05 | B 1 | BRDATR 9 vs ATRBYT 9 vs $F3F3 9 (one at a time) | which cell is the border | — | — | — |
| SR-06 | B 1 | [LG] | LOGOPR applied to the painted run | — | — | — |
| SR-07 | B 1 | run starting / ending on odd X | per-pixel paint vs byte-wise | — | — | — |
| SR-08 | B 1 | S#8 / S#9 garbage, R#44 garbage | SRCH used (S#8 / S#9 changed, R#44 = BRDATR) vs CPU scan | — | — | — |
| SR-09 | B 1 | [PG] | the page scanned and the page painted | — | — | — |
| SR-10 | B 1 | SCREEN 6 (2-bit), 8 (BRDATR $C3) | the colour width compared | — | — | — |
| SR-11 | garbage in all registers; DI / EI | SCREEN 5 | registers left; interrupts after | — | — | — |
| SR-12 | — | SCRMOD 2, 3, 4 with [MD]; 10-12 (FS-A1WSX only) | the MSX1 rules through the sub-ROM; the YJK modes | — | — | — |
| SR-13 | B 1 | SCREEN 2 with R#25 CMD set and clear | SRCH outside 5-8 on the V9958 -- per machine (on the V9938 there is no R#25: the MSX2 rows are the baseline) | — | — | — |
| SR-14 | B 1 | a long LMMV running at entry; [SN] | waits for CE; S#2 on return; SRCH / LMMV residue and command count | — | — | — |
| SR-15 | B 1 | [SN] whole-RAM diff | every cell written: the run's start (CSAVEA / CSAVEM?) and length (the cell SCANL's join reads) | — | — | — |
| SR-16 | the SR-01 inputs | SCREEN 5, called at the main-ROM SCANR ($012C) | the main entry forwards in SCREEN 5-8 | — | — | — |

## Related pages

[The concept page](../concepts/graphics-cursor.md); the MSX1 [SCANR](../../bios/SCANR.md) and
[PNTINI](../../bios/PNTINI.md); [SCANL](SCANL.md), [READC](READC.md), [SETC](SETC.md).

## Tests that cover it

None yet.
