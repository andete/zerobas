<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `PROMPT` (sub-ROM $0181) — display the prompt

> **Spec:** DRAFT 0 (2026-11-23), from the published interface only; nothing measured yet. References to measure: HB-F900, NMS 8250, FS-A1WSX.

## Summary

`PROMPT` displays BASIC's prompt. On an MSX2 the prompt can be changed with `SET PROMPT`, stored in
the clock chip's battery-backed memory; what the call prints, and where it takes it from, is open.
Shared facts: [the screen-modes page](../concepts/screen-modes.md).

## The specification

**Interface.**
- In: none. Out: none. Registers: all [P App. 1, SUB-ROM PROMPT].
- Interrupts on return: [A].

**Behaviour.**
- Displays the prompt [P App. 1, SUB-ROM PROMPT].
- `SET PROMPT` stores up to 6 characters [P Ch. 2 §2.10] in clock-chip block 3 with ID 2, two 4-bit
  registers per character [P Ch. 5 §6.7, Figure 5.34]; block 3 holds a title or a password instead
  when its ID is 0 or 1, the most recent `SET` winning [P Ch. 2 §2.10].
- Prints the block-3 prompt when ID = 2, else "Ok" [A]; followed by CR LF [A]; through CHPUT, so
  in the current mode at the cursor [A].

## Differences from the reference

Not measured yet.

## Open (not measured)

Recorded per case: the screen cells written (name table around the cursor), CSRX / CSRY, registers,
interrupt state, the clock chip's block 2 / 3 registers after (unchanged?), VRAM block sums.

| case | inputs | state | what it separates | HB-F900 | NMS 8250 | FS-A1WSX |
|---|---|---|---|---|---|---|
| IE | the page's base case (its first row) | entered once with DI, once with EI | interrupt state on return: forced on, forced off, or kept (read twice, §3a) | ? | ? | ? |
| PR-OK | — | block 3 ID = 0 with printable title "XYZ"; ID = 1 (password) | "Ok" vs block 3's text printed regardless of ID | ? | ? | ? |
| PR-SET | — | block 3 ID = 2, prompt "ABC" + 0 + printable garbage "QR", "ABC" + three printable "QRS", "ABCDEF", 6 × $00 (with PR-HOOK's CHPUT count) | prompt from the clock chip; length rule (stops at 0? always 6?) | ? | ? | ? |
| PR-NL | — | cursor at column 5, at column 1 | a leading newline when not at column 1; trailing CR LF | ? | ? | ? |
| PR-MODE | — | SCREEN 0, 1, 5 (bitmap) | printed via CHPUT / GRPPRT, or nothing in graphics | ? | ? | ? |
| PR-KEY | — | key line on, cursor on the last row | scroll behaviour | ? | ? | ? |
| PR-HOOK | — | H.CHPU / H.DSPC hooked to a counter | goes through CHPUT (hook count) vs writes VRAM directly | ? | ? | ? |
| PR-REG | registers distinct | — | registers kept | ? | ? | ? |

## Related pages

[The screen-modes page](../concepts/screen-modes.md) (the clock chip's settings); [SETSCR](SETSCR.md);
MSX1 [CHPUT](../../bios/CHPUT.md).

## Tests that cover it

none yet
