<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `SDFSCR` (sub-ROM $0185) — restore the screen settings from the clock chip (interface unpublished)

> **Spec:** DRAFT 0 (2026-11-23), from the published interface only; nothing measured yet. References to measure: HB-F900, NMS 8250, FS-A1WSX.

## Summary

An entry at sub-ROM $0185 named SDFSCR by other open implementations, presumably applying the
`SET SCREEN` settings kept in the clock chip. The MSX2 Technical Handbook's sub-ROM listing does not
list it: inputs and behaviour are unknown until measured. Shared facts:
[the screen-modes page](../concepts/screen-modes.md#the-clock-chips-screen-settings).

## The specification

**Interface.**
- Not published: the handbook lists PROMPT ($0181) and then NEWPAD ($01AD) [P App. 1, SUB-ROM].
- In / out / registers / interrupts: [A]; whether an entry flag (carry, Z) is an input is a matrix
  row (SD-CY).

**Behaviour.**
- `SET SCREEN`'s settings — text mode number, width, the three colours, key-line switch, key click,
  printer option, cassette speed, display mode — are applied at start-up [P Ch. 2 §2.10]; they live
  in clock-chip block 2 [P Ch. 5 §6.7, Figure 5.33]. That SDFSCR is the routine that applies them,
  [A].
- Which of them it applies (colours, width, mode, interlace, adjust R#18, key click, beep), and
  whether it switches the screen mode or only sets the cells, [A].

## Differences from the reference

Not measured yet.

## Open (not measured)

Recorded per case: registers, interrupt state, SCRMOD, LINL40, LINL32, LINLEN, FORCLR / BAKCLR /
BDRCLR, CNSDFG, CLIKSW, a whole work-area diff $F380-$FFFF, R#0-R#27, all copies (R#9 interlace, R#18 adjust), the PSG's beep-related
cells, the screen (name table sum), the clock chip's registers (unchanged?).

| case | inputs | state | what it separates | HB-F900 | NMS 8250 | FS-A1WSX |
|---|---|---|---|---|---|---|
| IE | the page's base case (its first row) | entered once with DI, once with EI | interrupt state on return: forced on, forced off, or kept (read twice, §3a) | ? | ? | ? |
| SD-EX | — | all three machines, SCREEN 0 | an entry at all | ? | ? | ? |
| SD-BLK2 | — | block 2: mode 1, width 30, colours 6 / 7 / 8, key off, adjust (+3, −2), interlace 1 | which settings it applies, to cells and / or VDP | ? | ? | ? |
| SD-CY | carry set / clear, Z set / clear | key bit on in block 2 | a flag selects the key line / a mode change | ? | ? | ? |
| SD-WIDTH | — | width 80 (Hi 5 / Lo 0), 255 (Hi $F / Lo $F), 41 | TEXT 2 selected; out-of-range width | ? | ? | ? |
| SD-ONE | — | from the SD-BLK2 baseline, each of key click, beep tone, beep volume, printer mode, cassette speed changed alone | the cell each lands in (CLIKSW, the beep cells, the printer and cassette-speed cells, via the work-area diff) or ignored | ? | ? | ? |
| SD-ID | — | block 2 ID (register 0) garbage | ID checked before applying vs applied anyway | ? | ? | ? |
| SD-NOCLK | — | clock chip unresponsive (if the emulator can) | defaults vs garbage | ? | ? | ? |
| SD-PREV | — | entered in SCREEN 5 | switches to text or only stores cells | ? | ? | ? |

## Related pages

[The screen-modes page](../concepts/screen-modes.md); [SETSCR](SETSCR.md); [PROMPT](PROMPT.md);
[INITXT](INITXT.md).

## Tests that cover it

none yet
