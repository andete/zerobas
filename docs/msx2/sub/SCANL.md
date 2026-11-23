<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `SCANL` (sub-ROM $00C5) — scan left for the PAINT border, and paint

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the HB-F900, NMS 8250 and FS-A1WSX ([xsubscan.asm](../../../probes/bios/spec/xsubscan.asm), [scratchpad/AE_xsubscan_msx2.out](../../../scratchpad/AE_xsubscan_msx2.out); [xsubscan2.asm](../../../probes/bios/spec/xsubscan2.asm), [scratchpad/AE_xsubscan2_msx2.out](../../../scratchpad/AE_xsubscan2_msx2.out), decoded by [xsubscan2_decode.py](../../../scratchpad/xsubscan2_decode.py) into [AE_xsubscan2_msx2_decoded.out](../../../scratchpad/AE_xsubscan2_msx2_decoded.out)).
> Goldfish pass 1 (test writer) 2026-11-23: 7 findings, 4 measured, 0 moved to open.

## Summary

`SCANL` is the sub-ROM's counterpart of the main ROM's [SCANL](../../bios/SCANL.md) ($012F), PAINT's left-hand
scan. Measured in SCREEN 8: from the pixel left of the current position it finds the border to the left with the
VDP's SRCH command, then fills from the pixel after the border rightwards up to (not including) the start with HMMV in
ATRBYT. On MSX1, in SCREEN 2, the paint is joined to the run the last [SCANR](SCANR.md) found; whether the bitmap
modes carry such a join is open.

## The specification

**Interface.**
- No published entry at $00C5 [P TH A1 SUB-ROM, by absence]; the entry is callable [M xsubscan, SCREEN 8].
- In: CLOC / CMASK, BRDATR ($FCB2, [P TH A4]), ATRBYT; B and DE are not read [M, see Measured]. Out: HL the count,
  DE and CLOC the leftmost painted X, CMASK the Y; the run painted in ATRBYT [M].
- The join with SCANR's run: MSX1 SCREEN 2 keeps SCANR's length in RAM (measured on the MSX1 page);
  in SCREEN 5-8, the same cell, another, or none [A].
- The scan by SRCH, the paint by HMMV [M, the port log; the commands P TH 4 §6.5.4, §6.5.10]; HMMV takes no logical
  operation, so LOGOPR plays no part in SCREEN 8 [the command's definition, P; SL-07 open].

**Measured** [M] (the same on all three references; SCREEN 8, line 50 $00 with the border $0F at X 30 and 100
unless named, the start (60, 50) set by MAPXYC, ATRBYT $05, CSAVEA / CSAVEM preset to $1357 / $2468 in xsubscan2; every
OUT to $99 / $9B logged in xsubscan2):
- **The run.** It paints X 31-59 -- the start pixel NOT included -- between the border (30) and the start, and returns
  HL 29 (the run), CLOC 31 (the leftmost painted pixel) / CMASK 50, DE 31 [M xsubscan op 2; xsubscan2 case 11].
  CSAVEA / CSAVEM keep the markers $1357 / $2468 [M xsubscan2 cases 10, 11, 13, 15]. Interrupts ON.
- **B and DE are not read**: B 0 and 1 give the same result, and DE $5A5A in still comes back 31 [M xsubscan2 cases 11,
  15].
- **The stop is BRDATR only.** A $07 pixel at X 45 is painted over; on a line of $07 the run 31-59 is painted the same
  [M xsubscan2 cases 10, 13].
- **The commands, and the direction** [M xsubscan2 cases 10, 11, 13, 15, the logs]: a SRCH from (start X - 1, Y) for
  BRDATR with ARG $04 (leftwards, EQ clear), S#8 / S#9 read; a SRCH from the same pixel for ATRBYT with ARG $06
  (leftwards, EQ set), S#8 / S#9 read; then **HMMV with DX = the border + 1 (31), NX 29, NY 1, CLR = ATRBYT, ARG $00:
  the paint runs RIGHTWARDS** from the leftmost pixel. Each command after a wait for CE.

## Differences from the reference

C-BIOS's MSX2 / MSX2+ builds do nothing here: no VDP command, HL garbage, no paint [[scratchpad/AE_xsubscan_msx2.out](../../../scratchpad/AE_xsubscan_msx2.out); [scratchpad/AE_xsubscan2_msx2.out](../../../scratchpad/AE_xsubscan2_msx2.out) cases 10, 11, 13, 15].

## Open (not measured)

The sets [PG], [LG], [LN], [MD] and [SN] are defined on [the concept page](../concepts/graphics-cursor.md#shared-measurement-setup-every-pages-matrix-assumes-it).

Every case runs on all three references; each machine's result is recorded on its own, and a rule that holds on one generation only names it ([the concept page](../concepts/graphics-cursor.md)). `—` = not measured yet; `n/a` = the mode does not exist on that machine.

| case | inputs | state | what it separates | HB-F900 | NMS 8250 | FS-A1WSX |
|---|---|---|---|---|---|---|
| SL-00 | — | SCREEN 5, MAPXYC (30, 10) | a callable entry vs not (SCREEN 8: callable) | S8: callable | S8: callable | S8: callable |
| SL-01 | — | a border at X 12, the run 13-29 | HL, CLOC / CMASK, the painted span (SCREEN 8: start pixel excluded; HL, DE, CLOC = the leftmost) | S8 | S8 | S8 |
| SL-02 | — | no border to the left | the run to X 0 | — | — | — |
| SL-03 | SCANR first (run length K), then SCANL | SCREEN 5 | painted HL + K (joined) vs HL only | — | — | — |
| SL-04 | SCANR first, then the cell SR-15 found holding the run length overwritten with another K | SCREEN 5 | where the join's K is read from (located by the RAM diff, not assumed) | — | — | — |
| SL-05 | B 0 vs 1, DE garbage | the same | B and DE unused as inputs (DE is an output: the leftmost X) (SCREEN 8: both unused) | S8 | S8 | S8 |
| SL-06 | — | BRDATR vs ATRBYT vs $F3F3 as the border; a non-border non-zero pixel in the run | the border cell (SCREEN 8: $07 pixels are painted over -- not "non-zero" or "not the start colour") | S8 part | S8 part | S8 part |
| SL-07 | — | [LG] | LOGOPR applied | — | — | — |
| SL-08 | — | odd / even X at both run ends | per-pixel vs byte-wise paint | — | — | — |
| SL-09 | — | S#8 / S#9, R#44 garbage | SRCH used vs CPU scan (SCREEN 8: SRCH, port log) | S8: SRCH | S8: SRCH | S8: SRCH |
| SL-10 | — | [PG] | the page scanned and painted | — | — | — |
| SL-11 | garbage in all registers; DI / EI | SCREEN 5 | registers left; interrupts after | — | — | — |
| SL-12 | — | SCRMOD 2, 3, 4 with [MD]; 6, 7, 8; 10-12 (FS-A1WSX only) | per-mode colour width; the MSX1 rules; the YJK modes | — | — | — |
| SL-13 | — | SCREEN 2 with R#25 CMD set and clear | SRCH outside 5-8 on the V9958 -- per machine (on the V9938 there is no R#25: the MSX2 rows are the baseline) | — | — | — |
| SL-14 | — | a long LMMV running at entry; [SN] | waits for CE; S#2 on return; command residue and count; the paint direction (SCREEN 8: SRCH x 2 + HMMV rightwards from the border + 1) | S8: count, direction | S8: count, direction | S8: count, direction |
| SL-15 | the SL-01 inputs | SCREEN 5, called at the main-ROM SCANL ($012F) | the main entry forwards in SCREEN 5-8 | — | — | — |

## Related pages

[The concept page](../concepts/graphics-cursor.md); the MSX1 [SCANL](../../bios/SCANL.md);
[SCANR](SCANR.md), [SETC](SETC.md).

## Tests that cover it

None yet.
