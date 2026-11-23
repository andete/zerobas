<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `SETPAG` (sub-ROM $013D) — switch the display and active pages

> **Spec:** DRAFT 0 (2026-11-23), from the published interface only; nothing measured yet. References to measure: HB-F900, NMS 8250, FS-A1WSX.

## Summary

`SETPAG` makes DPPAGE the displayed page and ACPAGE the page drawing goes to, in the bitmap modes
(SCREEN 5-8). The display page is the name-table base in R#2. Shared facts:
[the screen-modes page](../concepts/screen-modes.md).

## The specification

**Interface.**
- In: DPPAGE ($FAF5) the display page, ACPAGE ($FAF6) the active page [P App. 1, SUB-ROM SETPAG].
- Out: none. Registers: AF [P App. 1, SUB-ROM SETPAG].
- Interrupts on return: [A].

**Behaviour.**
- In GRAPHIC 4-7 the display page is switched by R#2, the name-table base [P Ch. 4 §4, "Switching
  the display page"]; the base steps by 32 KB in GRAPHIC 4 / 5 [P Ch. 4 §3.6.2], by 64 KB in GRAPHIC
  6 / 7 [A].
- R#2's low bits (set to 1 for an odd page in alternation [P Ch. 4 §4, "Automatic alternate screen
  display"]) are kept / forced [A]; RG2SAV updated [A].
- ACPAGE: only stored for the drawing calls, or also applied (R#45, NAMBAS?) [A].
- In SCREEN 0-4: [A].

## Differences from the reference

Not measured yet.

## Open (not measured)

Recorded per case: A, F, BC, DE, HL, IX, IY and the alternate set (the handbook says only AF changes), interrupt state, R#2,
RG2SAV, R#13, R#45, DPPAGE, ACPAGE, NAMBAS..ATRBAS, VRAM block sums.

| case | inputs | state | what it separates | HB-F900 | NMS 8250 | FS-A1WSX |
|---|---|---|---|---|---|---|
| IE | the page's base case (its first row) | entered once with DI, once with EI | interrupt state on return: forced on, forced off, or kept (read twice, §3a) | ? | ? | ? |
| SP-5 | DPPAGE 0..3, ACPAGE ≠ DPPAGE | SCREEN 5, 6 | R#2 = page · 32 KB bits; low bits $1F set | ? | ? | ? |
| SP-7 | DPPAGE 0, 1, 2, 3 | SCREEN 7, 8, and 10-12 | 64 KB step; page 2 / 3 masked, wrapped or refused | ? | ? | ? |
| SP-OOR | DPPAGE 4, $FF | SCREEN 5 | masked to 2 bits vs written raw | ? | ? | ? |
| SP-LOW | DPPAGE 1 | SCREEN 0, 1, 2, 4 | nothing vs R#2 rewritten | ? | ? | ? |
| SP-R2 | — | RG2SAV ≠ R#2; RG2SAV low bits 0 (alternation odd-page form) | R#2 from DPPAGE + fixed bits vs from RG2SAV's bits | ? | ? | ? |
| SP-AC | ACPAGE 0..3 | SCREEN 5 | ACPAGE stored only vs written to NAMBAS / R#45 / R#14 | ? | ? | ? |
| SP-REG | BC, DE, HL distinct | SCREEN 5 | "registers: AF" holds | ? | ? | ? |
| SP-R13 | — | R#13 garbage | alternation rate untouched | ? | ? | ? |

## Related pages

[The screen-modes page](../concepts/screen-modes.md); [CLS](CLS.md); [CHGMOD](CHGMOD.md).

## Tests that cover it

none yet
