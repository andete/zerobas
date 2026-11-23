<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `NVBXFL` (sub-ROM $00CD) — draw a filled box

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the HB-F900, NMS 8250 and FS-A1WSX ([xsubbox.asm](../../../probes/bios/spec/xsubbox.asm), [scratchpad/AE_xsubbox_msx2.out](../../../scratchpad/AE_xsubbox_msx2.out), decoded by [xsubbox_decode.py](../../../scratchpad/xsubbox_decode.py); [xsubbox2.asm](../../../probes/bios/spec/xsubbox2.asm), [scratchpad/AE_xsubbox2_msx2.out](../../../scratchpad/AE_xsubbox2_msx2.out), decoded by [xsubbox2_decode.py](../../../scratchpad/xsubbox2_decode.py) into [AE_xsubbox2_msx2_decoded.out](../../../scratchpad/AE_xsubbox2_msx2_decoded.out)).
> Goldfish pass 1 (test writer) 2026-11-23: 7 findings, 4 measured, 0 moved to open.

## Summary

`NVBXFL` fills the rectangle from (BC, DE) to (GXPOS, GYPOS) with ATRBYT, combined with what is there
by LOGOPR. The handbook publishes its interface; how it fills -- the logical LMMV command, which works
per pixel and honours the logical operation, or the byte-wise HMMV, which does neither -- is what the
measurement has to show, together with the same open points as [NVBXLN](NVBXLN.md).

## The specification

**Interface.**
- Draws a painted box; in: start X in BC, Y in DE; end X in GXPOS ($FCB3), Y in GYPOS ($FCB5); the
  colour in ATRBYT, given as **$F3F3**; the logical operation code in LOGOPR ($FB02); out: none;
  registers: all [P TH A1 SUB-ROM: NVBXFL]. ATRBYT is $F3F2 in [P TH A4]; the call reads $F3F2 [M xsubbox cases 2,
  6: SCREEN 8 and 5].
- Called through EXTROM, IX = $00CD [P TH A1 SUB-ROM, preamble]; EXTROM keeps IY and the alternate
  registers [P TH A1 MAIN-ROM: EXTROM].
- The fill: one LMMV (per pixel, logical operation in R#46's low nibble) [M xsubbox2 cases 7-9, 13, the port log;
  the command P TH 4 §6.5.8], with DIX / DIY from the corner order -- the corners are NOT sorted (see Measured).
- The modes, the page, clipping and the cells left: as open as [NVBXLN](NVBXLN.md)'s [A].

**Measured** [M] (the same pixels on all three references; SCREEN 8 and SCREEN 5; every OUT to $99 / $9B logged in
xsubbox2):
- **The pixels.** The box (BC, DE)-(GXPOS, GYPOS) filled, both corners inclusive, in either corner order [M xsubbox
  cases 2, 3, 6; xsubbox2 cases 7, 8]. Per pixel: in SCREEN 5 the box (11, 10)-(20, 15) leaves pixels 10 and 21, which
  share their bytes with 11 and 20, untouched [M xsubbox2 case 9]. **The colour is ATRBYT at $F3F2**, not the
  handbook's $F3F3: with $F3F2 $05 and $F3F3 $0A every drawn pixel is $05 [M xsubbox cases 2, 6]. LOGOPR is honoured:
  XOR over $0C gives $09 [M xsubbox2 case 13].
- **The command.** One LMMV: DX / DY = (BC, DE), NX = |GXPOS - BC| + 1, NY = |GYPOS - DE| + 1, CLR = ATRBYT, ARG = DIX
  / DIY pointing from (BC, DE) towards (GXPOS, GYPOS) ($00 for (10, 10)-(20, 15), $0C for (20, 15)-(10, 10)), CMD = $80
  OR LOGOPR; then a wait for CE [M xsubbox2 cases 7-9, 13, the logs].
- **Then, on the HB-F900 and NMS 8250 only**, a second command: R#32-R#35 := the LMMV's NY and NX words (SX = NY,
  SY = NX: (6, 11) for the 11 x 6 box), R#44 := the LMMV's command byte ($80 OR LOGOPR), R#45 := $04, R#46 := $60 -- a
  SRCH [M xsubbox2 cases 7-9, 13, the $99 log]. It writes no VRAM in the windows read; what it leaves in S#2 / S#8-S#9
  is unmeasured. The FS-A1WSX issues the LMMV alone [M the same cases].
- **After.** GRPACX / GRPACY kept (markers 77 / 33) and GXPOS / GYPOS kept [M xsubbox2 cases 7-9, 13; xsubbox cases 2,
  3, 6]. The residue R#44 / R#45 is the last command's: $80 (or $83) / $04 on the MSX2s (the SRCH), $05 / $00 forward
  and $05 / $0C reversed on the FS-A1WSX (the LMMV); on all three R#36 = BC and R#38 = the row past the last one
  filled (16 forward, 9 reversed) [M xsubbox cases 2, 3, 6]. A /
  F are not defined outputs: A $00, F $54 on the MSX2s; A $0C / $0E, F $88 on the FS-A1WSX [M the same cases; A].

## Differences from the reference

C-BIOS's MSX2 / MSX2+ builds fill the same pixels, LOGOPR honoured, but sort the corners first: one LMMV from (min X,
min Y) with ARG $00, so after the reversed case R#36 / R#38 hold (10, 16) where the references hold (20, 9) and R#45
$00 where the FS-A1WSX holds $0C; no second (SRCH) command, so R#44 / R#45 differ from the MSX2s' $80 / $04 too; A
out the command byte ($80 / $83), F $80 [[scratchpad/AE_xsubbox_msx2.out](../../../scratchpad/AE_xsubbox_msx2.out) cases 2, 3; [scratchpad/AE_xsubbox2_msx2.out](../../../scratchpad/AE_xsubbox2_msx2.out) cases 7, 8, 13].

## On the turbo R

Measured 2026-11-23 (D-TRSPEC) on the FS-A1GT / FS-A1ST: every case gives the same bytes as on the FS-A1WSX, on both models except A and F in xsubbox cases 3 and 6 and xsubbox2 cases 7-9: A is a VDP S#2 read there, as on the A1WSX, and its value depends on the moment (timing; the A1GT and A1ST differ the same way) [M] ([AE_trall/xsubbox.out](../../../scratchpad/AE_trall/xsubbox.out), [AE_trall/xsubbox2.out](../../../scratchpad/AE_trall/xsubbox2.out); overview: [turbor/remeasured.md](../../turbor/remeasured.md)).

## Open (not measured)

The sets [PG], [LG], [LN], [MD] and [SN] are defined on [the concept page](../concepts/graphics-cursor.md#shared-measurement-setup-every-pages-matrix-assumes-it).

Every case runs on all three references; each machine's result is recorded on its own, and a rule that holds on one generation only names it ([the concept page](../concepts/graphics-cursor.md)). `—` = not measured yet; `n/a` = the mode does not exist on that machine.

| case | inputs | state | what it separates | HB-F900 | NMS 8250 | FS-A1WSX |
|---|---|---|---|---|---|---|
| BF-01 | (10, 10)-(40, 30) | SCREEN 5, ATRBYT 9, $F3F3 4 | the colour cell | $F3F2 (S5, S8) | $F3F2 (S5, S8) | $F3F2 (S5, S8) |
| BF-02 | (11, 10)-(40, 30) | SCREEN 5: the left edge X 11 (odd) and the right edge X 40 (even) each share their byte with a pixel outside the box | per-pixel fill vs byte-wise (HMMV would paint pixels 10 and 41 too) | per pixel [M xsubbox2 9] | per pixel | per pixel |
| BF-03 | (10, 10)-(40, 30) | [LG] over a patterned area | logical operation honoured, ignored or masked; undefined codes (XOR measured: honoured) | S8: XOR | S8: XOR | S8: XOR |
| BF-04 | (40, 30)-(10, 10); (40, 10)-(10, 30) | SCREEN 5; [SN]: R#36-R#39, R#45 after, and a large box caught mid-fill (S#2 CE = 1) | the same area, both corners inclusive; sorted corners vs direction bits (measured S8: direction bits, port log) | S8: DIX/DIY | S8: DIX/DIY | S8: DIX/DIY |
| BF-05 | (10, 10)-(10, 10); (10, 10)-(40, 10); (10, 10)-(10, 30) | SCREEN 5 | a 1 x 1, a one-line and a one-column box (NX / NY 1 vs 0 off-by-one) | — | — | — |
| BF-06 | (-5, 10)-(300, 250) | SCREEN 5, 6; [LN] | clipping vs wrap | — | — | — |
| BF-07 | (10, 10)-(40, 30) | [PG] | the page | — | — | — |
| BF-08 | (10, 10)-(40, 30) | SCREEN 6 ATRBYT 7, SCREEN 7 ATRBYT $1A, SCREEN 8 ATRBYT $C3 | the colour width; for HMMV the replicated byte | — | — | — |
| BF-09 | the same | a command running at entry; R#45 garbage | waits for CE; ARG rewritten | — | — | — |
| BF-10 | the same | [SN] | S#2 on return (returns before the fill ends, a large box); the command residue and count (measured S8: LMMV + SRCH on the MSX2s, LMMV alone on the FS-A1WSX); S#2 / S#8-S#9 after the SRCH | count only | count only | count only |
| BF-11 | the same | GRPACX/Y, CLOC / CMASK, GXPOS / GYPOS markers | cells changed (measured S8: GRPACX/Y and GXPOS/GYPOS kept; CLOC / CMASK open) | S8 part | S8 part | S8 part |
| BF-12 | garbage in all registers; DI / EI | SCREEN 5 | what "all" covers; interrupts after | — | — | — |
| BF-13 | (10, 10)-(40, 30) | SCRMOD 2, 3, 4 with [MD]; 10-12 (FS-A1WSX only) | other modes | — | — | — |
| BF-14 | (10, 10)-(40, 30) | SCREEN 2 / 4 with R#25 CMD set and clear | filled boxes outside 5-8 on the V9958 -- per machine (on the V9938 there is no R#25: the MSX2 rows are the baseline) | — | — | — |

## Related pages

[The concept page](../concepts/graphics-cursor.md); [NVBXLN](NVBXLN.md); [SETATR](SETATR.md).

## Tests that cover it

None yet.
