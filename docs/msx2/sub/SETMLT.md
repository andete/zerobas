<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `SETMLT` (sub-ROM $00F1) — set the VDP to MULTI COLOUR (SCREEN 3), only

> **Spec:** DRAFT 0 (2026-11-23), from the published interface only; nothing measured yet. References to measure: HB-F900, NMS 8250, FS-A1WSX.

## Summary

`SETMLT` programs the VDP for SCREEN 3 from the same cells as [INIMLT](INIMLT.md), without the rest
of INIMLT's work. Shared facts: [the screen-modes page](../concepts/screen-modes.md).

## The specification

**Interface.**
- In: as INIMLT (MLTNAM .. MLTPAT) [P App. 1, SUB-ROM SETMLT].
- Out: none; all registers may change [P App. 1, SUB-ROM SETMLT].
- Interrupts on return: [A].

**Behaviour.**
- Sets the VDP to MULTI COLOUR [P App. 1, SUB-ROM SETMLT]; R#0-R#7, R#10 / R#11 and their copies
  [A]; nothing else [A].

## Differences from the reference

Not measured yet.

## Open (not measured)

Recorded per case: as [SETTXT](SETTXT.md#open-not-measured).

| case | inputs | state | what it separates | HB-F900 | NMS 8250 | FS-A1WSX |
|---|---|---|---|---|---|---|
| IE | the page's base case (its first row) | entered once with DI, once with EI | interrupt state on return: forced on, forced off, or kept (read twice, §3a) | ? | ? | ? |
| SM-ONLY | — | SCRMOD, name table, sprites garbage | "VDP only": VRAM block sums and a whole work-area diff $F380-$FFFF (only the register copies may differ) | ? | ? | ? |
| SM-BASE | cells default / moved | R#3 / R#10 copies garbage | R#3 / R#10 from MLTCOL, constant, or kept | ? | ? | ? |
| SM-R01 | — | RG0SAV / RG1SAV walking bits ≠ VDP; R#1 M1 set (from TEXT) | M1 cleared, M2 set; other bits kept | ? | ? | ? |
| SM-R89 | — | R#8 bits 1, 3, 5, 6, 7 and R#9 bits 1, 2, 3, 4, 5, 7, each walked alone, copies ≠ VDP | kept | ? | ? | ? |
| SM-MAIN | main-ROM $0081 | same | the *3 claim by a breakpoint on the sub-ROM entry and on EXTROM ($015F) as a call trace | ? | ? | ? |

## Related pages

[The screen-modes page](../concepts/screen-modes.md); [INIMLT](INIMLT.md); MSX1
[SETMLT](../../bios/SETMLT.md).

## Tests that cover it

none yet
