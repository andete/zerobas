<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `SETTXT` (sub-ROM $00E5) — set the VDP to the text mode, only

> **Spec:** DRAFT 0 (2026-11-23), from the published interface only; nothing measured yet. References to measure: HB-F900, NMS 8250, FS-A1WSX.

## Summary

`SETTXT` programs the VDP for the SCREEN 0 text mode from the same cells as [INITXT](INITXT.md),
without the rest of INITXT's work (no clear, no cursor, no width). Shared facts:
[the screen-modes page](../concepts/screen-modes.md).

## The specification

**Interface.**
- In: as INITXT (TXTNAM, TXTCGP, LINL40) [P App. 1, SUB-ROM SETTXT].
- Out: none; all registers may change [P App. 1, SUB-ROM SETTXT].
- Interrupts on return: [A].

**Behaviour.**
- Sets the VDP to "the text mode (40x24)" [P App. 1, SUB-ROM SETTXT]; "set only VDP" [P App. 1,
  main-ROM SETTXT]. TEXT 2 for LINL40 > 40 [A].
- Writes R#0-R#7 (and TEXT 2's R#3 / R#10 / R#12 / R#13?) and their copies; no VRAM, no work area
  besides the copies [A].

## Differences from the reference

Not measured yet.

## Open (not measured)

Recorded per case: registers, interrupt state, R#0-R#27, all register copies, SCRMOD, OLDSCR, LINLEN,
CSRX / CSRY, NAMBAS..ATRBAS, the palette, VRAM (128 KB block sums), and in the -ONLY cases the whole work-area diff $F380-$FFFF (only the register copies may differ).

| case | inputs | state | what it separates | HB-F900 | NMS 8250 | FS-A1WSX |
|---|---|---|---|---|---|---|
| IE | the page's base case (its first row) | entered once with DI, once with EI | interrupt state on return: forced on, forced off, or kept (read twice, §3a) | ? | ? | ? |
| ST-W | LINL40 = 40, 41, 80 | LINLEN ≠ LINL40 | TEXT 2 selected here or only by INITXT; LINLEN read or not | ? | ? | ? |
| ST-ONLY | — | SCRMOD 5, cursor / LINLEN / VRAM garbage | "VDP only": VRAM block sums and a whole work-area diff $F380-$FFFF (only the register copies may differ): SCRMOD, cursor, LINLEN, VRAM all untouched | ? | ? | ? |
| ST-BASE | TXTNAM / TXTCGP moved | — | R#2 / R#4 from the cells | ? | ? | ? |
| ST-R01 | — | RG0SAV / RG1SAV walking bits ≠ VDP | kept bits; R#1 bit 6 (screen on) set, cleared or kept | ? | ? | ? |
| ST-R7 | FORCLR $3A, BAKCLR $C5, BDRCLR $F9 (all distinct) | R#7 copy garbage | R#7 written by SETTXT or left to INITXT | ? | ? | ? |
| ST-R89 | — | R#8 bits 1, 3, 5, 6, 7 and R#9 bits 1, 2, 3, 4, 5, 7, each walked alone, copies ≠ VDP | kept | ? | ? | ? |
| ST-BASES | — | NAMBAS..ATRBAS garbage | written here vs by INITXT | ? | ? | ? |
| ST-MAIN | main-ROM $0078 | same | the *3 claim by a breakpoint on the sub-ROM entry and on EXTROM ($015F) as a call trace | ? | ? | ? |

## Related pages

[The screen-modes page](../concepts/screen-modes.md); [INITXT](INITXT.md); MSX1
[SETTXT](../../bios/SETTXT.md).

## Tests that cover it

none yet
