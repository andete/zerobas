<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `DOGRPH` (sub-ROM $0085) — draw a line

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the HB-F900, NMS 8250 and FS-A1WSX ([xsubbox.asm](../../../probes/bios/spec/xsubbox.asm), [scratchpad/AE_xsubbox_msx2.out](../../../scratchpad/AE_xsubbox_msx2.out), decoded by [xsubbox_decode.py](../../../scratchpad/xsubbox_decode.py); [xsubbox2.asm](../../../probes/bios/spec/xsubbox2.asm), [scratchpad/AE_xsubbox2_msx2.out](../../../scratchpad/AE_xsubbox2_msx2.out), decoded by [xsubbox2_decode.py](../../../scratchpad/xsubbox2_decode.py) into [AE_xsubbox2_msx2_decoded.out](../../../scratchpad/AE_xsubbox2_msx2_decoded.out)).
> Goldfish pass 1 (test writer) 2026-11-23: 6 findings, 4 measured, 0 moved to open.

## Summary

`DOGRPH` is not in the handbook. On all three references it is a callable entry that draws a line joining the
points (BC, DE) and (GXPOS, GYPOS) in ATRBYT with LOGOPR, by one VDP LINE command, and leaves the cursor cells
alone. The modes other than SCREEN 8, clipping, the page and the register contract are still open.

## The specification

**Interface.**
- No published entry at $0085 [P TH A1 SUB-ROM, by absence]; the name and address are the C-BIOS
  peer's. The entry is callable [M xsubbox case 4; xsubbox2 cases 10-12, 14, 15; SCREEN 8].
- Called through EXTROM, IX = $0085 [P TH A1 SUB-ROM, preamble].
- In: BC, DE one end; GXPOS ($FCB3), GYPOS ($FCB5) the other; the colour ATRBYT at $F3F2; the logical operation
  LOGOPR ($FB02) [M, see Measured]. GRPACX / GRPACY are not read [M].
- In SCREEN 5-7 by the LINE command [A; measured in SCREEN 8 only]; in SCREEN 2-4 [A] (DG-10).
- Registers after: A = the command byte (see Measured); the rest [A] (DG-11).

**Measured** [M] (the same on all three references, SCREEN 8; every OUT to $99 / $9B logged in xsubbox2):
- **The points.** With BC / DE, GXPOS / GYPOS and GRPACX / GRPACY all different, the line drawn **joins (BC, DE) and
  (GXPOS, GYPOS)**: (20, 15)-(23, 9) [M xsubbox case 4]; (11, 14)-(21, 11) and the same pair swapped give the same
  pixels, both ends inside the window with 2 pixels to spare and no pixel past either end [M xsubbox2 cases 10, 11];
  likewise (11, 11)-(21, 14) and its swap [M xsubbox2 cases 14, 15]. GRPACX / GRPACY are neither used nor updated
  (10 / 10, then markers 77 / 33); GXPOS / GYPOS kept [M the same cases].
- **The command.** One LINE, after a wait for CE (none after it): it starts at the end with the SMALLER Y and runs
  down (DIY 0), DIX towards the other end, whichever register pair holds which end -- (23, 9) with ARG $05, (21, 11)
  with ARG $04, (11, 11) with ARG $00; MAJ = the longer axis, NX the longer and NY the shorter difference [M xsubbox
  case 4 residue; xsubbox2 cases 10, 11, 14, 15, the $9B log]. Which end starts when both Y are equal is open (DG-14).
- **The colour is ATRBYT at $F3F2**, not the handbook's $F3F3 (a cell named for [NVBXLN](NVBXLN.md)): with $F3F2 $05
  and $F3F3 $0A every drawn pixel is $05; CLR = $05 [M xsubbox case 4; xsubbox2 case 10].
- **LOGOPR** goes into R#46: CMD = $70 OR LOGOPR; OR over $08 draws $0D [M xsubbox2 case 12]. **A = that command byte**
  ($70; $72 under OR), F $20 / $24 [M xsubbox case 4; xsubbox2 cases 10, 12].

## Differences from the reference

C-BIOS's MSX2 / MSX2+ builds draw NOTHING for the same inputs: no VDP command is issued (empty port log); A $00 ($02
under OR), F $68 [[scratchpad/AE_xsubbox_msx2.out](../../../scratchpad/AE_xsubbox_msx2.out) case 4; [scratchpad/AE_xsubbox2_msx2.out](../../../scratchpad/AE_xsubbox2_msx2.out) cases 10-12, 14, 15].

## Open (not measured)

The sets [PG], [LG], [LN], [MD] and [SN] are defined on [the concept page](../concepts/graphics-cursor.md#shared-measurement-setup-every-pages-matrix-assumes-it).

Every case runs on all three references; each machine's result is recorded on its own, and a rule that holds on one generation only names it ([the concept page](../concepts/graphics-cursor.md)). `—` = not measured yet; `n/a` = the mode does not exist on that machine.

| case | inputs | state | what it separates | HB-F900 | NMS 8250 | FS-A1WSX |
|---|---|---|---|---|---|---|
| DG-00 | BC 10, DE 10 | SCREEN 5 | a callable entry vs an unused address (SCREEN 8: callable) | S8: callable | S8: callable | S8: callable |
| DG-01 | BC 10, DE 10 | GXPOS/GYPOS (60, 20), GRPACX/Y (100, 100), CLOC elsewhere | which two points are joined (SCREEN 8: (BC, DE) and (GXPOS, GYPOS)) | S8: BC/DE-GX/GY | S8: BC/DE-GX/GY | S8: BC/DE-GX/GY |
| DG-02 | the same | after the call | GRPACX / GRPACY, GXPOS / GYPOS, CLOC / CMASK changed to which point (SCREEN 8: the first two kept; CLOC / CMASK open) | S8 part | S8 part | S8 part |
| DG-03 | (BC, DE) (60, 20), GXPOS/GYPOS (10, 10), GRPACX/Y (100, 100); then the same with (BC, DE) and GXPOS/GYPOS swapped | SCREEN 5, LOGOPR 3 | the direction (which end LINE starts at) and both end pixels drawn once (SCREEN 8: the smaller-Y end, from the $9B log) | S8: smaller Y | S8: smaller Y | S8: smaller Y |
| DG-04 | steep, shallow, 45° lines | SCREEN 5 | the major axis (LINE's MAJ) and the stepping pattern | — | — | — |
| DG-05 | as DG-01 | [LG] | LOGOPR honoured, masked or ignored | — | — | — |
| DG-06 | ATRBYT 9 at $F3F2, 4 at $F3F3 | SCREEN 5 | the colour cell (SCREEN 8: $F3F2) | S8: $F3F2 | S8: $F3F2 | S8: $F3F2 |
| DG-07 | ends off the screen | SCREEN 5, 6; [LN] | clipping | — | — | — |
| DG-08 | — | [PG] | the page | — | — | — |
| DG-09 | — | a command running at entry; [SN] | waits for CE; S#2 on return; the LINE residue and command count (SCREEN 8: one LINE, a CE wait before it only) | S8: count | S8: count | S8: count |
| DG-10 | — | SCRMOD 2, 3, 4 with [MD] | the MSX1-shaped modes: drawn through the cursor calls or nothing | — | — | — |
| DG-11 | garbage in all registers; DI / EI | SCREEN 5 | registers and interrupt state after | — | — | — |
| DG-12 | — | SCRMOD 10-12 (FS-A1WSX) | the YJK modes | n/a | n/a | — |
| DG-13 | as DG-01 | SCREEN 2 / 4 with R#25 CMD set and clear | lines outside 5-8 on the V9958 -- per machine (on the V9938 there is no R#25: the MSX2 rows are the baseline) | — | — | — |
| DG-14 | (BC, DE) (10, 12), GXPOS/GYPOS (20, 12); then swapped | SCREEN 8, port log | a horizontal line: which end starts (DIX) when the Y are equal | — | — | — |

## Related pages

[The concept page](../concepts/graphics-cursor.md); [NVBXLN](NVBXLN.md), [GRPPRT](GRPPRT.md),
[SETC](SETC.md).

## Tests that cover it

None yet.
