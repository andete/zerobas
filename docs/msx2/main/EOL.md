<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `EOL` ($0168) — clear to the end of a line

> **Spec:** DRAFT 0 (2026-11-23), from the published interface only; nothing measured yet. References to measure: HB-F900, NMS 8250, FS-A1WSX.

## Summary

`EOL` clears the text screen from a given position to the end of the line. The position comes in
HL, H the column and L the row, the same coordinates as the cursor's. Whether the cursor moves, and
whether "the line" is one screen row or the whole logical line, is not published.

## The specification

**Interface.**
- In: H = the cursor's X coordinate, L = its Y coordinate [P A1]. Out: none [P A1]. Changes: all
  registers [P A1].
- It clears from (H, L) to the end of the line [P A1]; with spaces, in the name table, like CHPUT's
  `ESC K` [A].
- The coordinates count from 1, as CSRX / CSRY [A]. CSRX / CSRY afterwards (moved to H, L or
  kept) [A]. Whether a continued logical line's next rows are cleared too [A]. LINTTB, the key line,
  and the interrupt state [A].

## Differences from the reference

Not measured yet.

## Open (not measured)

Every case fills the name table with an address-dependent, non-space pattern and puts the cursor
(CSRX / CSRY) somewhere other than (H, L). Records: the whole name table (or its sums plus windows
on rows L-1, L, L+1, L+2), CSRX, CSRY, LINTTB, CRTCNT, CNSDFG, the key line's row, every register,
the interrupt state (twice), and the colour / pattern tables' sums.

| case | inputs | state | separates | F900 | 8250 | WSX |
|---|---|---|---|---|---|---|
| EL-1 | H 5, L 3 | SCREEN 1, width 32, cursor at (20, 10) | uses HL vs the cursor; 1-based (clears from column 5) vs 0-based (from 6) | ? | ? | ? |
| EL-2 | H 1, L 1 | SCREEN 0 width 40 | the whole first row; the left edge | ? | ? | ? |
| EL-3 | H 30, L 3 | SCREEN 0 width 80 (TEXT2) | the MSX2 80-column layout (name table stride) | ? | ? | ? |
| EL-4 | H 5, L 3 | SCREEN 0, LINLEN 30 < screen width 40 | the name-table column the clear starts at (recorded, not assumed): from column 4, or 4 + a centring margin; and where it ends: LINLEN, the screen width, or the margin's end | ? | ? | ? |
| EL-5 | H 5, L 3 | row 3 continued into row 4 (LINTTB) | one screen row vs the whole logical line; LINTTB rewritten | ? | ? | ? |
| EL-6 | H 0, L 3 / H 41, L 3 | SCREEN 0 width 40 | out-of-range columns: nothing, the whole row, or past the row | ? | ? | ? |
| EL-7 | H 40, L 3 / H 80, L 3 (TEXT2) | SCREEN 0 | H at the last column: exactly one cell cleared | ? | ? | ? |
| EL-8 | H 5, L 24 | CRTCNT 24, key line OFF | the last row cleared, nothing scrolled | ? | ? | ? |
| EL-9 | H 5, L 0 / L 24 / L 25 | CRTCNT 24, key line ON | the key line's row and beyond the screen | ? | ? | ? |
| EL-10 | H 5, L 3 | after the call | CSRX / CSRY: kept at (20, 10) vs moved to (5, 3) | ? | ? | ? |
| EL-11 | H 5, L 3 | SCREEN 5 (a bitmap mode) | what it does in graphics modes (nothing / VRAM change / something else) | ? | ? | ? |
| EL-12 | H 5, L 3 | S-REGS, interrupts on / off | registers out (all may change: record which do); the interrupt state | ? | ? | ? |
| EL-13 | H 5, L 3 | cursor shown (CSRSW) at the cleared position | the cursor's drawn character restored or cleared | ? | ? | ? |
| EL-14 | H 5, L 3 | — | stack depth and time ([README](README.md#the-shared-vram-address-matrix) methods) | ? | ? | ? |

Also open: SCREEN 2-4.

## Related pages

[region page](README.md); [CHPUT](../../bios/CHPUT.md) (`ESC K`), [screen editor](../../concepts/screen-editor.md),
[screen modes](../../concepts/screen-modes.md).

## Tests that cover it

None yet.
