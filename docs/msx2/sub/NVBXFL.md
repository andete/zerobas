<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `NVBXFL` (sub-ROM $00CD) — draw a filled box

> **Spec:** DRAFT 0 (2026-11-23), from the published interface only; nothing measured yet. References to measure: HB-F900, NMS 8250, FS-A1WSX.

## Summary

`NVBXFL` fills the rectangle from (BC, DE) to (GXPOS, GYPOS) with ATRBYT, combined with what is there
by LOGOPR. The handbook publishes its interface; how it fills -- the logical LMMV command, which works
per pixel and honours the logical operation, or the byte-wise HMMV, which does neither -- is what the
measurement has to show, together with the same open points as [NVBXLN](NVBXLN.md).

## The specification

**Interface.**
- Draws a painted box; in: start X in BC, Y in DE; end X in GXPOS ($FCB3), Y in GYPOS ($FCB5); the
  colour in ATRBYT, given as **$F3F3**; the logical operation code in LOGOPR ($FB02); out: none;
  registers: all [P TH A1 SUB-ROM: NVBXFL]. ATRBYT is $F3F2 in [P TH A4]; the cell read is [A].
- Called through EXTROM, IX = $00CD [P TH A1 SUB-ROM, preamble]; EXTROM keeps IY and the alternate
  registers [P TH A1 MAIN-ROM: EXTROM].
- The fill [A]: LMMV (per pixel, logical operation in R#46's low nibble) [P TH 4 §6.5.8 for the
  command; its use here A]; HMMV fills whole bytes and takes no logical operation [P TH 4 §6.2,
  §6.5.4 for the command]. LMMV with DIX / DIY from the corner order, or the corners sorted first [A].
- The modes, the page, clipping and the cells left: as open as [NVBXLN](NVBXLN.md)'s [A].

## Differences from the reference

Not measured yet.

## Open (not measured)

The sets [PG], [LG], [LN], [MD] and [SN] are defined on [the concept page](../concepts/graphics-cursor.md#shared-measurement-setup-every-pages-matrix-assumes-it).

Every case runs on all three references; each machine's result is recorded on its own, and a rule that holds on one generation only names it ([the concept page](../concepts/graphics-cursor.md)). `—` = not measured yet; `n/a` = the mode does not exist on that machine.

| case | inputs | state | what it separates | HB-F900 | NMS 8250 | FS-A1WSX |
|---|---|---|---|---|---|---|
| BF-01 | (10, 10)-(40, 30) | SCREEN 5, ATRBYT 9, $F3F3 4 | the colour cell | — | — | — |
| BF-02 | (11, 10)-(40, 30) | SCREEN 5: the left edge X 11 (odd) and the right edge X 40 (even) each share their byte with a pixel outside the box | per-pixel fill vs byte-wise (HMMV would paint pixels 10 and 41 too) | — | — | — |
| BF-03 | (10, 10)-(40, 30) | [LG] over a patterned area | logical operation honoured, ignored or masked; undefined codes | — | — | — |
| BF-04 | (40, 30)-(10, 10); (40, 10)-(10, 30) | SCREEN 5; [SN]: R#36-R#39, R#45 after, and a large box caught mid-fill (S#2 CE = 1) | the same area, both corners inclusive; and from DX / DY / DIX / DIY whether the corners were sorted or the direction bits used | — | — | — |
| BF-05 | (10, 10)-(10, 10); (10, 10)-(40, 10); (10, 10)-(10, 30) | SCREEN 5 | a 1 x 1, a one-line and a one-column box (NX / NY 1 vs 0 off-by-one) | — | — | — |
| BF-06 | (-5, 10)-(300, 250) | SCREEN 5, 6; [LN] | clipping vs wrap | — | — | — |
| BF-07 | (10, 10)-(40, 30) | [PG] | the page | — | — | — |
| BF-08 | (10, 10)-(40, 30) | SCREEN 6 ATRBYT 7, SCREEN 7 ATRBYT $1A, SCREEN 8 ATRBYT $C3 | the colour width; for HMMV the replicated byte | — | — | — |
| BF-09 | the same | a command running at entry; R#45 garbage | waits for CE; ARG rewritten | — | — | — |
| BF-10 | the same | [SN] | S#2 on return (returns before the fill ends, a large box); the command residue and count | — | — | — |
| BF-11 | the same | GRPACX/Y, CLOC / CMASK, GXPOS / GYPOS markers | cells changed | — | — | — |
| BF-12 | garbage in all registers; DI / EI | SCREEN 5 | what "all" covers; interrupts after | — | — | — |
| BF-13 | (10, 10)-(40, 30) | SCRMOD 2, 3, 4 with [MD]; 10-12 (FS-A1WSX only) | other modes | — | — | — |
| BF-14 | (10, 10)-(40, 30) | SCREEN 2 / 4 with R#25 CMD set and clear | filled boxes outside 5-8 on the V9958 -- per machine (on the V9938 there is no R#25: the MSX2 rows are the baseline) | — | — | — |

## Related pages

[The concept page](../concepts/graphics-cursor.md); [NVBXLN](NVBXLN.md); [SETATR](SETATR.md).

## Tests that cover it

None yet.
