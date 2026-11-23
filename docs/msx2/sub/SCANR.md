<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `SCANR` (sub-ROM $00C1) — scan right for the PAINT border

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the HB-F900, NMS 8250 and FS-A1WSX ([xsubscan.asm](../../../probes/bios/spec/xsubscan.asm), [scratchpad/AE_xsubscan_msx2.out](../../../scratchpad/AE_xsubscan_msx2.out); [xsubscan2.asm](../../../probes/bios/spec/xsubscan2.asm), [scratchpad/AE_xsubscan2_msx2.out](../../../scratchpad/AE_xsubscan2_msx2.out), decoded by [xsubscan2_decode.py](../../../scratchpad/xsubscan2_decode.py) into [AE_xsubscan2_msx2_decoded.out](../../../scratchpad/AE_xsubscan2_msx2_decoded.out)).
> Goldfish pass 1 (test writer) 2026-11-23: 7 findings, 5 measured, 1 moved to open.

## Summary

`SCANR` is the sub-ROM's counterpart of the main ROM's [SCANR](../../bios/SCANR.md) ($012C), PAINT's right-hand
scan. Measured in SCREEN 8: from the current position (CLOC / CMASK) it skips border-colour pixels, counting DE down,
then finds the next border pixel to the right with the VDP's SRCH command and fills the run between with HMMV in
ATRBYT. Unlike the MSX1 call it paints whatever B holds. The other modes, the page and LOGOPR's part are open.

## The specification

**Interface.**
- No published entry at $00C1 [P TH A1 SUB-ROM, by absence]; the entry is callable [M xsubscan, SCREEN 8].
- In: CLOC / CMASK (the start, as MAPXYC leaves them), DE (the skip count), the border colour BRDATR ($FCB2: "the
  border colour used by PAINT" [P TH A4]), ATRBYT ($F3F2); B is NOT read [M, see Measured]. Out: HL the run's length,
  DE the counted-down skip, CLOC / CMASK the stopping pixel, CSAVEA ($F942) the run's start X and $F944 (CSAVEM) its Y
  [M]; [P TH A4] calls CSAVEA / CSAVEM a reservation area.
- The scan: SRCH [M, the port log; the command P TH 4 §6.5.10]. The paint: HMMV [M; the command P TH 4 §6.5.4],
  which takes no logical operation, so LOGOPR plays no part in SCREEN 8 [the command's definition, P; SR-06 open].
- The right edge: X 255 (SCREEN 5 / 8) or 511 (6 / 7) [A]; MSX1: interrupts on after [A here].

**Measured** [M] (the same on all three references; SCREEN 8, line 50 $00 with the border $0F at X 30 and 100
unless named, the start (60, 50) set by MAPXYC, ATRBYT $05, CSAVEA / CSAVEM preset to $1357 / $2468 in xsubscan2;
every OUT to $99 / $9B logged in xsubscan2):
- **The run.** With DE 1 it paints X 60-99 -- the start pixel included, up to the border -- and returns HL 40 (the
  run), CLOC 100 / CMASK 50 (the border pixel), DE 1, CSAVEA 60, $F944 50 ($F945 kept) [M xsubscan op 3; xsubscan2
  case 1]. Interrupts ON [M every case].
- **B is not read**: B 0, 1 and $80 give the same run, HL and paint [M xsubscan2 cases 0-2].
- **The stop is BRDATR only.** A $07 pixel at X 80 inside the run is painted over (the run still ends at 100, HL
  40); a line of $07 is painted from 60 to 99 like a line of $00 [M xsubscan2 cases 9, 12].
- **The skip.** Starting on 3 border pixels (X 60-62): with DE 4 it paints X 63-99 and returns HL 37, DE 1 (4 - 3),
  CSAVEA 63, CLOC 100 [M xsubscan2 case 5]. With DE 3 or 2 it returns HL 0, DE 0, CLOC / CMASK and CSAVEA / CSAVEM
  unchanged, nothing painted [M cases 3, 4]; so does DE 0 on one border pixel [M case 14] and DE 0 on none [M xsubscan
  op 0]. With no border pixel at the start, DE 2, $7FFF and $8000 paint the run and come back unchanged [M xsubscan2
  cases 6-8] -- DE is not signed -- while DE $FFFF returns at once with DE 0 [M xsubscan op 4]. A rule that fits
  every case: return (HL 0, DE 0) when DE <= the number of border pixels skipped, or when start X + DE passes 65535;
  otherwise DE -= the number skipped. The second clause rests on the one DE $FFFF case (SR-17).
- **The commands** [M xsubscan2, the logs]: a SRCH from the start (R#32-R#35 = CLOC, CMASK) for BRDATR with ARG $02
  (EQ set, rightwards), then S#8 / S#9 read; if the skip did not exhaust DE, a SRCH for BRDATR with ARG $00 (EQ clear)
  from the first non-border pixel, S#8 / S#9 read; a SRCH for ATRBYT with ARG $02 from the same pixel, S#8 / S#9 read;
  then HMMV with DX / DY = the first non-border pixel, NX = the run, NY 1, CLR = ATRBYT, ARG $00 (the paint runs
  rightwards); each command after a wait for CE. What the third SRCH decides is open (SR-18).

## Differences from the reference

C-BIOS's MSX2 / MSX2+ builds (the subject) do nothing here: no VDP command, HL garbage ($D800), DE, CLOC and CSAVEA /
CSAVEM unchanged, no paint [[scratchpad/AE_xsubscan_msx2.out](../../../scratchpad/AE_xsubscan_msx2.out); [scratchpad/AE_xsubscan2_msx2.out](../../../scratchpad/AE_xsubscan2_msx2.out) every case].

## Open (not measured)

The sets [PG], [LG], [LN], [MD] and [SN] are defined on [the concept page](../concepts/graphics-cursor.md#shared-measurement-setup-every-pages-matrix-assumes-it).

Every case runs on all three references; each machine's result is recorded on its own, and a rule that holds on one generation only names it ([the concept page](../concepts/graphics-cursor.md)). `—` = not measured yet; `n/a` = the mode does not exist on that machine.

| case | inputs | state | what it separates | HB-F900 | NMS 8250 | FS-A1WSX |
|---|---|---|---|---|---|---|
| SR-00 | B 0, DE 0 | SCREEN 5, MAPXYC (10, 10) | a callable entry vs not (SCREEN 8: callable) | S8: callable | S8: callable | S8: callable |
| SR-01 | B 1, DE 5 | SCREEN 5, a row: 3 border pixels, a 20-pixel run, a border | skip, count, paint; HL, DE, CLOC / CMASK, CSAVEA / CSAVEM (SCREEN 8 measured, xsubscan2 case 5) | S8 | S8 | S8 |
| SR-02 | B 0, B 1, B $80 at DE 1 | the same | paint gated by B as a whole byte vs one bit vs always (SCREEN 8: always) | S8: always | S8: always | S8: always |
| SR-03 | DE 2 with 3 border pixels first; DE 0 starting on a border pixel; DE $FFFF | SCREEN 5 | the skip exhausted on a border pixel; DE 0; DE counted down past 0 (SCREEN 8: HL 0, DE 0, nothing painted) | S8 | S8 | S8 |
| SR-04 | B 1 | no border to the right | the run ends at X 255 / 511 (SCREEN 5 / 7) | — | — | — |
| SR-05 | B 1 | BRDATR 9 vs ATRBYT 9 vs $F3F3 9 (one at a time); a non-border non-zero pixel in the run | which cell is the border (SCREEN 8: a $07 pixel in the run, and a run of $07, are painted over -- the stop is not "non-zero" or "not the start colour") | S8 part | S8 part | S8 part |
| SR-06 | B 1 | [LG] | LOGOPR applied to the painted run | — | — | — |
| SR-07 | B 1 | run starting / ending on odd X | per-pixel paint vs byte-wise | — | — | — |
| SR-08 | B 1 | S#8 / S#9 garbage, R#44 garbage | SRCH used vs CPU scan (SCREEN 8: SRCH, port log) | S8: SRCH | S8: SRCH | S8: SRCH |
| SR-09 | B 1 | [PG] | the page scanned and the page painted | — | — | — |
| SR-10 | B 1 | SCREEN 6 (2-bit), 8 (BRDATR $C3) | the colour width compared | — | — | — |
| SR-11 | garbage in all registers; DI / EI | SCREEN 5 | registers left; interrupts after | — | — | — |
| SR-12 | — | SCRMOD 2, 3, 4 with [MD]; 10-12 (FS-A1WSX only) | the MSX1 rules through the sub-ROM; the YJK modes | — | — | — |
| SR-13 | B 1 | SCREEN 2 with R#25 CMD set and clear | SRCH outside 5-8 on the V9958 -- per machine (on the V9938 there is no R#25: the MSX2 rows are the baseline) | — | — | — |
| SR-14 | B 1 | a long LMMV running at entry; [SN] | waits for CE; S#2 on return; command residue and count (SCREEN 8: SRCH x 3 + HMMV, a CE wait before each) | S8: count | S8: count | S8: count |
| SR-15 | B 1 | [SN] whole-RAM diff | every cell written: the run's start (CSAVEA / CSAVEM?) and length (the cell SCANL's join reads) | — | — | — |
| SR-16 | the SR-01 inputs | SCREEN 5, called at the main-ROM SCANR ($012C) | the main entry forwards in SCREEN 5-8 | — | — | — |
| SR-17 | DE $FFC4 and $FFC3 from start X 60 (60 + DE = $10000 and $FFFF); DE $FFFF from start X 0 | SCREEN 8, no border at the start | the DE clause: "start X + DE passes 65535" vs "DE $FFFF only" vs another bound | — | — | — |
| SR-18 | B 1, DE 1 | SCREEN 8, part of the run (or all of it) already ATRBYT | what the third SRCH (for ATRBYT) decides: HL, the HMMV's DX / NX, CLOC | — | — | — |

## Related pages

[The concept page](../concepts/graphics-cursor.md); the MSX1 [SCANR](../../bios/SCANR.md) and
[PNTINI](../../bios/PNTINI.md); [SCANL](SCANL.md), [READC](READC.md), [SETC](SETC.md).

## Tests that cover it

None yet.
