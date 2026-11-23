<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `DOGRPH` (sub-ROM $0085) — draw a line (assumed)

> **Spec:** DRAFT 0 (2026-11-23), from the published interface only; nothing measured yet. References to measure: HB-F900, NMS 8250, FS-A1WSX.

## Summary

`DOGRPH` is not in the handbook. Its place, just before GRPPRT and after the sub-ROM's BASIC graphics
entries, and its name suggest the line-drawing step of BASIC's LINE / DRAW: a line between two
points in ATRBYT with LOGOPR. Every part of that is assumed; the first measurements establish
whether the entry exists, which two points it joins, and what it leaves behind.

## The specification

**Interface.**
- No published entry at $0085 [P TH A1 SUB-ROM, by absence]; the name and address are the C-BIOS
  peer's. A callable entry is [A] (case DG-00).
- Called through EXTROM, IX = $0085 [P TH A1 SUB-ROM, preamble].
- The two points [A], rival readings: (BC, DE) to (GXPOS, GYPOS), as [NVBXLN](NVBXLN.md) takes a
  box; (GRPACX, GRPACY) to (BC, DE), the "last point" to a new one; or the reverse.
- The colour ATRBYT and the logical operation LOGOPR [A, by analogy with NVBXLN, P TH A1 SUB-ROM].
- In SCREEN 5-8 by the LINE command [A; the command P TH 4 §6.5.9]; in SCREEN 2-4 by the cursor
  calls [A].
- After: GRPACX / GRPACY := the end point [A]; registers all changed [A].

## Differences from the reference

Not measured yet.

## Open (not measured)

The sets [PG], [LG], [LN], [MD] and [SN] are defined on [the concept page](../concepts/graphics-cursor.md#shared-measurement-setup-every-pages-matrix-assumes-it).

Every case runs on all three references; each machine's result is recorded on its own, and a rule that holds on one generation only names it ([the concept page](../concepts/graphics-cursor.md)). `—` = not measured yet; `n/a` = the mode does not exist on that machine.

| case | inputs | state | what it separates | HB-F900 | NMS 8250 | FS-A1WSX |
|---|---|---|---|---|---|---|
| DG-00 | BC 10, DE 10 | SCREEN 5 | a callable entry vs an unused address | — | — | — |
| DG-01 | BC 10, DE 10 | GXPOS/GYPOS (60, 20), GRPACX/Y (100, 100), CLOC elsewhere | which two points are joined (the line's ends in VRAM) | — | — | — |
| DG-02 | the same | after the call | GRPACX / GRPACY, GXPOS / GYPOS, CLOC / CMASK changed to which point | — | — | — |
| DG-03 | (BC, DE) (60, 20), GXPOS/GYPOS (10, 10), GRPACX/Y (100, 100); then the same with (BC, DE) and GXPOS/GYPOS swapped | SCREEN 5, LOGOPR 3 | per rival: (BC, DE)→GXPOS/GYPOS draws (60, 20)-(10, 10) then (10, 10)-(60, 20); GRPACX/Y→(BC, DE) draws (100, 100)-(60, 20) then (100, 100)-(10, 10). The direction (which end LINE starts at) and both end pixels drawn once | — | — | — |
| DG-04 | steep, shallow, 45° lines | SCREEN 5 | the major axis (LINE's MAJ) and the stepping pattern | — | — | — |
| DG-05 | as DG-01 | [LG] | LOGOPR honoured, masked or ignored | — | — | — |
| DG-06 | ATRBYT 9 at $F3F2, 4 at $F3F3 | SCREEN 5 | the colour cell | — | — | — |
| DG-07 | ends off the screen | SCREEN 5, 6; [LN] | clipping | — | — | — |
| DG-08 | — | [PG] | the page | — | — | — |
| DG-09 | — | a command running at entry; [SN] | waits for CE; S#2 on return; the LINE residue and command count | — | — | — |
| DG-10 | — | SCRMOD 2, 3, 4 with [MD] | the MSX1-shaped modes: drawn through the cursor calls or nothing | — | — | — |
| DG-11 | garbage in all registers; DI / EI | SCREEN 5 | registers and interrupt state after | — | — | — |
| DG-12 | — | SCRMOD 10-12 (FS-A1WSX) | the YJK modes | n/a | n/a | — |
| DG-13 | as DG-01 | SCREEN 2 / 4 with R#25 CMD set and clear | lines outside 5-8 on the V9958 -- per machine (on the V9938 there is no R#25: the MSX2 rows are the baseline) | — | — | — |

## Related pages

[The concept page](../concepts/graphics-cursor.md); [NVBXLN](NVBXLN.md), [GRPPRT](GRPPRT.md),
[SETC](SETC.md).

## Tests that cover it

None yet.
