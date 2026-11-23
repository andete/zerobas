<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `SETSCR` (sub-ROM $0189) — start-up screen from the clock chip (interface unpublished)

> **Spec:** DRAFT 0 (2026-11-23), from the published interface only; nothing measured yet. References to measure: HB-F900, NMS 8250, FS-A1WSX.

## Summary

An entry at sub-ROM $0189 named SETSCR by other open implementations, presumably the start-up
counterpart of [SDFSCR](SDFSCR.md): apply the clock chip's screen settings and show the start-up
screen (title or banner). The MSX2 Technical Handbook does not list it; everything is unknown until
measured. Shared facts: [the screen-modes page](../concepts/screen-modes.md#the-clock-chips-screen-settings).

## The specification

**Interface.**
- Not published [P App. 1, SUB-ROM: not listed].
- In / out / registers / interrupts: [A].

**Behaviour.**
- At start-up the `SET SCREEN` settings are applied, and a `SET TITLE` title (up to 6 characters,
  in one of 4 title colours) is shown on the initial screen; a 6-character title waits for a key
  [P Ch. 2 §2.10]. The title lives in clock-chip block 3 with ID 0, its colour in block 2 register 11
  [P Ch. 5 §6.7]. That SETSCR does this, [A].
- Whether it also asks for a `SET PASSWORD` password (block 3, ID 1) [P Ch. 2 §2.10] — [A].

## Differences from the reference

Not measured yet.

## Open (not measured)

Recorded per case: as [SDFSCR](SDFSCR.md#open-not-measured), plus the whole name table / bitmap
after, the palette, whether it returns at all without a key (with a timeout), and the keyboard
buffer.

| case | inputs | state | what it separates | HB-F900 | NMS 8250 | FS-A1WSX |
|---|---|---|---|---|---|---|
| IE | the page's base case (its first row) | entered once with DI, once with EI | interrupt state on return: forced on, forced off, or kept (read twice, §3a) | ? | ? | ? |
| SS-EX | — | all three machines | an entry at all | ? | ? | ? |
| SS-EQ | — | the SD-BLK2 settings | = SDFSCR + something, setting for setting | ? | ? | ? |
| SS-TITLE | — | block 3 ID 0: "" , "MSX", "ABCDEF"; title colour 1..4 | title shown; colour; a key wait at 6 characters | ? | ? | ? |
| SS-PW | — | block 3 ID 1 (password set) | asks for the password vs ignores it | ? | ? | ? |
| SS-KEY | key in the buffer / none | title "ABCD", "ABCDE", "ABCDEF" | key wait only at 6 characters [P] vs from another length | ? | ? | ? |
| SS-PROMPT | — | block 3 ID 2 (a prompt stored) | no title shown vs block 3 printed as a title | ? | ? | ? |
| SS-MODE | — | block 2 mode 0 / 1, width 40 / 80 | final mode and width | ? | ? | ? |

## Related pages

[The screen-modes page](../concepts/screen-modes.md); [SDFSCR](SDFSCR.md); [PROMPT](PROMPT.md).

## Tests that cover it

none yet
