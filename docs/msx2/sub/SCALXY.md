<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `SCALXY` (sub-ROM $008D) — clip a graphics coordinate

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the HB-F900, NMS 8250 and FS-A1WSX ([xsubgc.asm](../../../probes/bios/spec/xsubgc.asm), [scratchpad/AE_xsubgc_msx2.out](../../../scratchpad/AE_xsubgc_msx2.out), decoded by `scratchpad/xsubgc_decode.py`; the separating cases [xsubgc2.asm](../../../probes/bios/spec/xsubgc2.asm), [scratchpad/AE_xsubgc2_msx2.out](../../../scratchpad/AE_xsubgc2_msx2.out), decoded by [scratchpad/xsubgc2_decode.py](../../../scratchpad/xsubgc2_decode.py) into [scratchpad/AE_xsubgc2_msx2_decoded.out](../../../scratchpad/AE_xsubgc2_msx2_decoded.out)). `[G1]` = the first run, `[G2 Xnn]` / `[G2 STATE]` = the second run's SCALXY / state records.
>
> Goldfish pass 1 (test writer) 2026-11-23: 9 findings, 6 measured, 0 moved to open, 3 corrected in wording / stale cells; one suggested separating case (X 254 for the SCREEN 2 order) does not separate (below).

## Summary

`SCALXY` is assumed to be the sub-ROM's counterpart of the main ROM's [SCALXY](../../bios/SCALXY.md)
($010E): it clips X (BC) and Y (DE) to the screen and reports whether it had to. In the bitmap modes
the screen is 256 or 512 pixels wide and 192 or 212 lines high, so the bounds depend on the mode
and possibly on R#9's line count; none of that is published.

## The specification

**Interface.**
- No published entry: nothing at $008D in the handbook's sub-ROM listing [P TH A1 SUB-ROM, by
  absence]. Note that **$008D in the main ROM is GRPPRT** [P TH A1 MAIN-ROM: GRPPRT]: a caller that
  confuses the two slots draws a character instead. A callable entry here on all three references [M] (case SX-00).
- In: X in BC, Y in DE, both signed 16-bit. Out: BC, DE clipped; the carry set and A = $80 when nothing was
  clipped, the carry clear and A = 0 when something was [M, below].
- Bounds: X 0..255 in SCREEN 5 / 8, 0..511 in SCREEN 6 / 7; Y 0..211 at LN 0 and 1 [M, below]. Screen sizes:
  [P TH 4 §3.6-§3.9].
- SCREEN 2, 3 and 4 divide by 4 (the multicolour grid) [M, below]; SCREEN 5-8 do not.
- Cells and VDP registers: none written [A].

**Measured** [M] (the same on all three references; BC = X, DE = Y, signed; entry A $5A; CHGMOD's state, R#9 LN 1
in SCREEN 5-8 [G2 STATE]):
- **X bound:** SCREEN 5 / 8 255 -- 256, 511, 600, $7FFF give 255 [G2 X01-X03, X11, X28, X29]; SCREEN 6 / 7 511 --
  511 kept, 512, 600, $7FFF give 511 [G2 X16-X19, X24-X27]. (The first run's X 300 in SCREEN 6 / 7 was inside the
  bound [G1].)
- **Y bound 211 in SCREEN 5-8, whatever R#9's LN:** Y 192 kept and 212 / 300 give 211 at LN 1 [G2 X04, X09, X10,
  X12, X13, X20, X30] and with R#9 := $00 (LN 0) written through WRTVDP [G2 X49-X52].
- **Negative to 0:** X or Y -5 (and -3) [G2 X05, X06, X21, X22, X31, X48].
- **Carry and A: carry set and A $80 iff nothing was clipped; carry clear and A $00 when anything was** -- X alone
  (600, 5) clears it [G2 X03, X15, X19, X27, X29], as do Y alone, negatives and both [G2 X04-X07]. Entry F has no
  part [G2 X14, X15].
- **F's other bits (SCREEN 5-8):** $81 unclipped. Clipped: $80, except when X is over its bound, where F is $40 for
  X = bound + 1 (256 / 512) [G2 X02, X17, X25, X28], $00 for X 600 or $7FFF [G2 X03, X11, X18, X19, X26, X27, X29]
  and $80 for 511 in SCREEN 5 [G2 X01]; X and Y both over give X's value ($00 for (600, 300) [G2 X07]; $00 for (300,
  250) in SCREEN 5 / 8, $80 in SCREEN 6 / 7 where X 300 is inside [G1]). No rule beyond this table is claimed [A].
- **SCREEN 2, 3 and 4: divided by 4, bounded to 0..63 x 0..47**: (254, 5) -> (63, 1) carry set; (256, 5) -> (63, 1)
  carry clear; (5, 191) -> (1, 47) set; (5, 192) -> (1, 47) clear; (300, 250) -> (63, 47); (100, 100) -> (25, 25);
  negatives, -3 included, -> 0 with the carry clear [G1; G2 X32-X47]. "Clip to 255 x 191, then divide" and "divide
  rounding down, then clip to 63 x 47" are the same function, so no order is named; a divide truncating toward 0
  (-3 -> 0, unclipped) is excluded by X45-X47. (X 254, suggested to separate the orders, gives 63 unclipped under
  both.) F: $01 unclipped, $00 clipped, $44 when Y is negative [G1; G2 X32-X47].

## Differences from the reference

C-BIOS's MSX2 / MSX2+ builds give the same BC, DE, carry and A in SCREEN 3 and 5-8. F differs: in SCREEN 5-8 bits 7
and 6 are always clear ($01 unclipped, $00 clipped, where the references give $81 and $80 / $40 / $00); in SCREEN 3 F
matches. **In SCREEN 2 and 4 they do not divide**: they clip to 255 x 191 ((300, 250) -> (255, 191), (100, 100) kept,
(254, 5) kept) and give F $81 unclipped, $80 clipped where the references give $01 / $00 / $44 [G1; G2 X32-X39, X43-X46]
([scratchpad/AE_xsubgc_msx2.out](../../../scratchpad/AE_xsubgc_msx2.out),
[scratchpad/AE_xsubgc2_msx2_decoded.out](../../../scratchpad/AE_xsubgc2_msx2_decoded.out)).

## On the turbo R

Measured 2026-11-23 (D-TRSPEC) on the FS-A1GT / FS-A1ST: xsubgc gives the same bytes as on the FS-A1WSX, on both models; xsubgc2 too, except R#36 = $80 (the boot's last VDP command) and VDP S#2 (read at a random moment) in its state records [M] ([AE_trall/xsubgc.out](../../../scratchpad/AE_trall/xsubgc.out), [AE_trall/xsubgc2.out](../../../scratchpad/AE_trall/xsubgc2.out); overview: [turbor/remeasured.md](../../turbor/remeasured.md)).

## Open (not measured)

The sets [PG], [LG], [LN], [MD], [SN] and [R9] are defined on [the concept page](../concepts/graphics-cursor.md#shared-measurement-setup-every-pages-matrix-assumes-it).

Every case runs on all three references; each machine's result is recorded on its own, and a rule that holds on one generation only names it ([the concept page](../concepts/graphics-cursor.md)). `—` = not measured yet; `n/a` = the mode does not exist on that machine.

| case | inputs | state | what it separates | HB-F900 | NMS 8250 | FS-A1WSX |
|---|---|---|---|---|---|---|
| SX-00 | X 10, Y 10 | SCREEN 5 | a callable entry vs not | [M] callable | [M] callable | [M] callable |
| SX-01 | X 255, 256, 511, 512 | SCREEN 5, 6, 7, 8 | the X bound per mode (255 vs 511) | [M] 255 (5, 8), 511 (6, 7) [G2 X01-X03, X16-X19, X24-X29] | [M] same | [M] same |
| SX-02 | Y 191, 192, 211, 212 | SCREEN 5; [LN]; with [R9] located, R#9 and its copy set apart both ways | Y bound 191 vs 211; fixed vs following R#9 vs following its RAM copy | [M] 211 at LN 1 and at LN 0 (both set through WRTVDP) [G2 X09-X13, X49-X52]; R#9 and its copy apart — | [M] same | [M] same |
| SX-03 | X -1, Y -1 ($FFFF) | each mode | negative to 0 (MSX1) | [M] -5 / -3 to 0 in SCREEN 2, 3, 5, 6, 8 [G2 X05, X06, X21, X22, X31, X36, X37, X45-X48]; SCREEN 4 / 7 — | [M] same | [M] same |
| SX-04 | X 600, Y 5 (X only); X 5, Y 300 (Y only); X 600, Y 300 (both); X 5, Y 5 (neither) | SCREEN 5, 6, 8 | the carry and A for each: set / $80 only when nothing is clipped (MSX1) | [M] as MSX1 in SCREEN 5 / 6 / 8, X alone included [G2 X03-X08, X19-X23, X29, X30] | [M] same | [M] same |
| SX-05 | X 100, Y 100 | SCREEN 2, 3, 4, 5 | the divide by 4 only in SCREEN 3; SCREEN 4 as 2 | [M] divide in 2, 3 and 4; none in 5 [G1; G2 X32-X47] | [M] same | [M] same |
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
