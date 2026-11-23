<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `SCALXY` (sub-ROM $008D) — clip a graphics coordinate

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the HB-F900, NMS 8250 and FS-A1WSX ([xsubgc.asm](../../probes/bios/spec/xsubgc.asm), [scratchpad/AE_xsubgc_msx2.out](../../scratchpad/AE_xsubgc_msx2.out), decoded by `scratchpad/xsubgc_decode.py`).

## Summary

`SCALXY` is assumed to be the sub-ROM's counterpart of the main ROM's [SCALXY](../../bios/SCALXY.md)
($010E): it clips X (BC) and Y (DE) to the screen and reports whether it had to. In the bitmap modes
the screen is 256 or 512 pixels wide and 192 or 212 lines high, so the bounds depend on the mode
and possibly on R#9's line count; none of that is published.

## The specification

**Interface.**
- No published entry: nothing at $008D in the handbook's sub-ROM listing [P TH A1 SUB-ROM, by
  absence]. Note that **$008D in the main ROM is GRPPRT** [P TH A1 MAIN-ROM: GRPPRT]: a caller that
  confuses the two slots draws a character instead. A callable entry here is [A] (case SX-00).
- In: X in BC, Y in DE, both signed 16-bit [A, as MSX1]. Out: BC, DE clipped; the carry set (A =
  $80) when nothing was clipped, clear (A = 0) when something was [A, as MSX1].
- Bounds [A]: X 0..255 in SCREEN 5 / 8, 0..511 in SCREEN 6 / 7; Y 0..211 or 0..191 -- by R#9 LN,
  by a fixed 211, or by the MSX1 191. Screen sizes: [P TH 4 §3.6-§3.9].
- In SCREEN 3 the MSX1 call divides by 4 [A for this entry]; in SCREEN 5-8 no scaling is expected [A].
- Cells and VDP registers: none written [A].

**Measured** [M] (the same on all three references; BC = X, DE = Y, signed): SCREEN 5 / 8 clip to 255 x 211,
SCREEN 6 / 7 to 511 x 211; negative values to 0; carry SET only when nothing was clipped (F $81), clear when clipped
(F $80 / $00). **In SCREEN 2 the result is MULTICOLOUR scaled**: (300, 250) -> (63, 47), (100, 100) -> (25, 25) --
divided by 4 and clipped to 63 x 47.

## Differences from the reference

C-BIOS's MSX2 / MSX2+ builds clip the same in SCREEN 5-8 (F's bit 7 clear where the references set it); in SCREEN 2
they clip to 255 x 191 and do not divide ([scratchpad/AE_xsubgc_msx2.out](../../scratchpad/AE_xsubgc_msx2.out)).

## Open (not measured)

The sets [PG], [LG], [LN], [MD], [SN] and [R9] are defined on [the concept page](../concepts/graphics-cursor.md#shared-measurement-setup-every-pages-matrix-assumes-it).

Every case runs on all three references; each machine's result is recorded on its own, and a rule that holds on one generation only names it ([the concept page](../concepts/graphics-cursor.md)). `—` = not measured yet; `n/a` = the mode does not exist on that machine.

| case | inputs | state | what it separates | HB-F900 | NMS 8250 | FS-A1WSX |
|---|---|---|---|---|---|---|
| SX-00 | X 10, Y 10 | SCREEN 5 | a callable entry vs not | — | — | — |
| SX-01 | X 255, 256, 511, 512 | SCREEN 5, 6, 7, 8 | the X bound per mode (255 vs 511) | — | — | — |
| SX-02 | Y 191, 192, 211, 212 | SCREEN 5; [LN]; with [R9] located, R#9 and its copy set apart both ways | Y bound 191 vs 211; fixed vs following R#9 vs following its RAM copy | — | — | — |
| SX-03 | X -1, Y -1 ($FFFF) | each mode | negative to 0 (MSX1) | — | — | — |
| SX-04 | X 600, Y 5 (X only); X 5, Y 300 (Y only); X 600, Y 300 (both); X 5, Y 5 (neither) | SCREEN 6 | the carry and A for each: set / $80 only when nothing is clipped (MSX1) | — | — | — |
| SX-05 | X 100, Y 100 | SCREEN 2, 3, 4, 5 | the divide by 4 only in SCREEN 3; SCREEN 4 as 2 | — | — | — |
| SX-06 | Y 256..1023 | SCREEN 5, ACPAGE 2 | whether a page's Y range (VDP Y 512..767) is accepted unclipped | — | — | — |
| SX-07 | any | SCRMOD 10-12 (FS-A1WSX) | bounds as SCREEN 8 | n/a | n/a | — |
| SX-08 | garbage HL, IX, IY, F | each mode | registers kept (MSX1: HL, IX, IY kept) | — | — | — |
| SX-09 | X 600, Y 300 | SCREEN 5; [SN] | RAM, VRAM, VDP registers unchanged | — | — | — |
| SX-10 | the SX-01 / SX-04 inputs | SCREEN 5 / 6, called at the main-ROM SCALXY ($010E) | the main entry forwards in SCREEN 5-8 vs clips to the MSX1 255 / 191 | — | — | — |

## Related pages

[The concept page](../concepts/graphics-cursor.md); the MSX1 [SCALXY](../../bios/SCALXY.md);
[MAPXYC](MAPXYC.md).

## Tests that cover it

None yet.
