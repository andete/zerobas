<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `MAPXYC` (sub-ROM $0091) — turn coordinates into a graphics position

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the HB-F900, NMS 8250 and FS-A1WSX ([xsubgc.asm](../../../probes/bios/spec/xsubgc.asm), [scratchpad/AE_xsubgc_msx2.out](../../../scratchpad/AE_xsubgc_msx2.out), decoded by `scratchpad/xsubgc_decode.py`; the separating cases [xsubgc2.asm](../../../probes/bios/spec/xsubgc2.asm), [scratchpad/AE_xsubgc2_msx2.out](../../../scratchpad/AE_xsubgc2_msx2.out), decoded by [scratchpad/xsubgc2_decode.py](../../../scratchpad/xsubgc2_decode.py) into [scratchpad/AE_xsubgc2_msx2_decoded.out](../../../scratchpad/AE_xsubgc2_msx2_decoded.out)). `[G1]` = the first run, `[G2 Pnn]` / `[G2 STATE]` = the second run's records.
>
> Goldfish pass 1 (test writer) 2026-11-23: 7 findings, 4 measured, 1 moved to open (a hidden copy of Y: MX-13), 2 corrected in wording / stale cells.

## Summary

`MAPXYC` is assumed to be the sub-ROM's counterpart of the main ROM's [MAPXYC](../../bios/MAPXYC.md)
($0111): it turns X (BC) and Y (DE) into the current graphics position, CLOC and CMASK, for the
mode in SCRMOD -- in SCREEN 5-8 by a cursor model the handbook does not publish. Measured: in SCREEN 5-8
the position is the coordinates themselves (CLOC = X, CMASK = Y's low byte); in SCREEN 2-4 the multicolour
byte and nibble.

## The specification

**Interface.**
- No published entry: the handbook's sub-ROM listing has nothing at $0091 [P TH A1 SUB-ROM, by
  absence]; the name is the C-BIOS peer's. That the references have a callable entry here is [A]
  (case MX-00).
- Called through EXTROM with IX = $0091 [P TH A1 SUB-ROM, preamble].
- In: X in C (or BC), Y in E (or DE), as the MSX1 call takes them [A]; SCRMOD, and in SCREEN 2 /
  3 GRPCGP / MLTCGP as the MSX1 call reads them [A]. In SCREEN 6 / 7 X runs to 511, and B
  takes part [M, below].
- Out: CLOC ($F92A) and CMASK ($F92C); in SCREEN 5-8 model C of
  [the concept page](../concepts/graphics-cursor.md#the-cursor-model--rival-rules-to-separate) [M, below].
  F: measured below; A, HL and the other registers: [A] (MSX1 leaves HL = CLOC).
- Pixel layout per mode: [the concept page](../concepts/graphics-cursor.md#the-bitmap-modes-pixel-layout)
  [P TH 4 §3.6-§3.9].
- Whether ACPAGE enters CLOC (a page's $8000 / $10000 offset) is [A].
- VDP registers: none written [A] (the MSX1 call writes none, measured there).

**Measured** [M] (the same on all three references):
- **Precondition of every case:** as CHGMOD leaves it -- LOGOPR 0, ACPAGE 0, DPPAGE 0, GRPCGP = MLTCGP = $0000, R#9
  LN 1 in SCREEN 5-8 (LN 0 in 2-4), S#2 CE 0 (no command running) [G2 STATE].
- **SCREEN 5-8: CLOC := BC verbatim, CMASK := E (Y's low byte)** -- model C of the concept page. (10, 20) gives
  $000A / $14 in all four modes [G1]; X 511 in SCREEN 6 / 7 gives $01FF [G1]. Nothing is clipped or masked to the
  mode's width: SCREEN 5 (300, 7) $012C / $07 [G2 P36], (511, 211) $01FF / $D3 [G2 P37]; SCREEN 8 (300, 7) $012C
  [G2 P40]; SCREEN 7 (600, 7) $0258 [G2 P41]. Y's high byte is not in CMASK: Y $0107 gives $07 [G2 P38], Y 255 $FF
  [G2 P39]. (SCREEN 5 / 8 at the last pixel: (255, 211) $00FF / $D3 [G1].)
- **SCREEN 2, 3 and 4: the MULTICOLOUR form**, all three modes alike [G1; G2 P12-P29]:
  CLOC := MLTCGP + 8 x ((X AND 63) >> 1) + 256 x ((Y AND 63) >> 3) + (Y AND 7); CMASK := $F0 for even X, $0F for
  odd. The base is MLTCGP, not GRPCGP: with GRPCGP $0800 and MLTCGP $1000 planted, (0, 0) gives $1000 and (10, 20)
  $122C [G2 P16, P17] (SCREEN 3 / 4: [G2 P27, P29]). The steps and wraps, all with MLTCGP $1000 (the planted cell
  survives the later CHGMODs): X 2 +$08, Y 1 +$01, Y 4 +$04, Y 8 +$100 [G2 P18-P21]; X 64 and X 128 +$000 (X wraps
  at 64) [G2 P22, P23]; Y 48 +$600 (no clip at 47), Y 64 +$000 (Y wraps at 64) [G2 P24, P25]; (255, 191) $07FF [G1,
  G2 P13]. (The review's rival "the whole address AND $07FF" gives $02FF for (255, 191), not $07FF.)
- **F is computed, not passed through:** entry F $00 and $FF give the same F in SCREEN 2, 5, 6, 8 [G2 P14 / P15,
  P30 / P31, P32 / P33, P34 / P35]. SCREEN 5: $42; SCREEN 6-8: $02 (both what CP 5 on SCRMOD gives -- that it IS
  that compare is [A]). SCREEN 2-4: $44 when (Y >> 3) AND 7 is 0, $04 when it is 6, $00 when it is 1, 2 or 7: the
  Z and P/V of that row number, S / H / N / C clear [G1; G2 P12-P29].

## Differences from the reference

C-BIOS's MSX2 / MSX2+ builds give the same CLOC, CMASK and F in every case of both runs, the multicolour form in
SCREEN 2 / 4 and MLTCGP as the base included ([scratchpad/AE_xsubgc_msx2.out](../../../scratchpad/AE_xsubgc_msx2.out),
[scratchpad/AE_xsubgc2_msx2_decoded.out](../../../scratchpad/AE_xsubgc2_msx2_decoded.out)).

## On the turbo R

Measured 2026-11-23 (D-TRSPEC) on the FS-A1GT / FS-A1ST: xsubgc gives the same bytes as on the FS-A1WSX, on both models; xsubgc2 too, except R#36 = $80 (the boot's last VDP command) and VDP S#2 (read at a random moment) in its state records [M] ([AE_trall/xsubgc.out](../../../scratchpad/AE_trall/xsubgc.out), [AE_trall/xsubgc2.out](../../../scratchpad/AE_trall/xsubgc2.out); overview: [turbor/remeasured.md](../../turbor/remeasured.md)).

## Open (not measured)

The sets [PG], [LG], [LN], [MD], [SN] and [R9] are defined on [the concept page](../concepts/graphics-cursor.md#shared-measurement-setup-every-pages-matrix-assumes-it).

Every case runs on all three references; each machine's result is recorded on its own, and a rule that holds on one generation only names it ([the concept page](../concepts/graphics-cursor.md)). `—` = not measured yet; `n/a` = the mode does not exist on that machine.

| case | inputs | state | what it separates | HB-F900 | NMS 8250 | FS-A1WSX |
|---|---|---|---|---|---|---|
| MX-00 | any | SCRMOD 5 | a callable entry vs an unused address (RET / garbage) | [M] callable | [M] callable | [M] callable |
| MX-01 | X 0, Y 0 | SCREEN 5, ACPAGE 0 | baseline: B gives CLOC 0 / CMASK $F0, C gives 0 / 0 | [M] 0 / 0: C [G1] | [M] 0 / 0: C | [M] 0 / 0: C |
| MX-02 | X 1, Y 0; X 2, Y 0 | SCREEN 5 | B: CMASK $0F then $F0 with CLOC 0 then 1; C: CLOC 1 then 2 | [M] X 1: CLOC 1, CMASK 0: C [G1] | [M] same | [M] same |
| MX-03 | X 0, Y 1; X 0, Y 211 | SCREEN 5 | B: CLOC 128 / 27008; C: CLOC 0, CMASK 1 / 211 | [M] C (shown by (10, 20) -> $000A / $14 [G1]; these two inputs not run) | [M] same | [M] same |
| MX-04 | X 255, Y 211 | SCREEN 5 / 8 | the last pixel: B's $69FF (5) vs $D3FF (8) | [M] $00FF / $D3 in both: C [G1] | [M] same | [M] same |
| MX-05 | X 4, 5, 6, 7; Y 3 | SCREEN 6 | B: masks $C0 / $30 / $0C / $03 at CLOC 385; M: $08 / $04 / $02 / $01 | — | — | — |
| MX-06 | X 300, Y 3 | SCREEN 6 / 7 | B (B taking part) vs X AND 255 (B ignored) | [M] B takes part: X 511 $01FF (6, 7) [G1], X 300 $012C (7) [G2 P09] | [M] same | [M] same |
| MX-07 | X 0, Y 0 | SCREEN 5 and 6 over [PG] | the page in CLOC ($8000 x ACPAGE, ACPAGE 2 wrapping to 0) vs not. In SCREEN 7 / 8 CLOC cannot show the page (concept page); SETC's SC-08 and READC's RD-06 do | — | — | — |
| MX-08 | X 256..511 / Y 212..255 / X, Y $FFFF | SCREEN 5, 8; [LN] | out-of-range coordinates: wrapped, clipped, or computed through | [M] X verbatim (300, 511; 600 in SCREEN 7), Y's low byte ($0107 -> $07) [G2 P36-P41]; $FFFF and LN 0 — | [M] same | [M] same |
| MX-09 | X 100, Y 50 | SCRMOD 2, 3, 4; [MD] | the MSX1 rules ([MAPXYC](../../bios/MAPXYC.md)) through the sub-ROM entry; SCREEN 4 as 2 or as 3 | [M] all three the multicolour form, SCREEN 4 as 3 (at (10, 20), (0, 0)) [G2 P12-P29]; [MD] — | [M] same | [M] same |
| MX-10 | X 100, Y 50 | SCRMOD 10, 11, 12 (FS-A1WSX) | as SCREEN 8 (byte per pixel) vs something else | n/a | n/a | — |
| MX-11 | entry A, F, HL, IX, IY garbage | each mode | A / F / HL / D left (MSX1: HL = CLOC, D = X in SCREEN 2) | [M] F computed (entry $00 / $FF alike) [G2 P14-P15, P30-P35]; A / HL / D — | [M] same | [M] same |
| MX-12 | X 100, Y 50 | R#9 LN 0 vs 1 | whether the 192 / 212-line choice affects the mapping | — | — | — |
| MX-13 | X 100, Y 50; then X 37, Y 120 | SCREEN 5, 7; GRPACX/Y and GXPOS/GYPOS set to two other points; [SN] | the whole-RAM diff: a hidden coordinate copy (model C's Y high byte -- D is not in CMASK: Y $0107 gives $07 [G2 P38] -- or X above 255) and where it lives; GRPACX/Y and GXPOS/GYPOS untouched | — | — | — |
| MX-14 | X 100, Y 50 | SCREEN 5; [SN] | VRAM, the VDP registers and S#n unchanged ("touches no VDP register") | — | — | — |
| MX-15 | X 100, Y 50 | SCREEN 5, called at the main-ROM MAPXYC ($0111) | the main entry forwards to the sub-ROM in SCREEN 5-8 vs runs the MSX1 rule | — | — | — |
| MX-16 | X 100, Y 50 | SCREEN 5 with R#25 / R#26 / R#27 non-zero (V9958 scroll) | whether the MSX2+ sub-ROM folds a scroll offset into CLOC -- per machine (on the V9938 there is no R#25: the MSX2 rows are the baseline) | — | — | — |
| MX-17 | X 0, 2, 64, 128; Y 1, 4, 8, 48, 64 | SCRMOD 2 with GRPCGP $0800, MLTCGP $1000 planted | the multicolour base (GRPCGP vs MLTCGP) and its wrap (X at 64, Y at 48 or 64) | [M] base MLTCGP; X wraps at 64, Y at 64 [G2 P16-P25] | [M] same | [M] same |

## Related pages

[The concept page](../concepts/graphics-cursor.md); the MSX1 [MAPXYC](../../bios/MAPXYC.md); the
sub-ROM cursor moves [RIGHTC](RIGHTC.md), [LEFTC](LEFTC.md), [UPC](UPC.md), [DOWNC](DOWNC.md),
[TUPC](TUPC.md), [TDOWNC](TDOWNC.md), [TRIGHT](TRIGHT.md), [TLEFTC](TLEFTC.md); [SCALXY](SCALXY.md)
(its usual predecessor); [READC](READC.md), [SETC](SETC.md).

## Tests that cover it

None yet.
