<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `CHKNEW` ($0165) — is the screen in one of the MSX2's new modes?

> **Spec:** DRAFT 0 (2026-11-23), from the published interface only; nothing measured yet. References to measure: HB-F900, NMS 8250, FS-A1WSX.

## Summary

`CHKNEW` is an MSX2 jump-table entry the handbook does not list. C-BIOS describes it as "is the
current screen mode a bitmap mode?". Which modes count, what it reads to decide, and how it
answers (a flag, A) are all assumed until measured.

## The specification

**Interface.** None published (absent from App. 1's MSX2 entries) [A].
- It answers in a flag whether the current screen mode is a bitmap mode (SCREEN 5-8) [A]; the
  flag (carry or zero), its sense, and which modes count are [A].
- It reads SCRMOD ($FCAF) [A], rather than the VDP's mode bits or their save cells.
- Registers other than AF kept; interrupt state unchanged [A].

## Differences from the reference

Not measured yet.

## Open (not measured)

Records: A, F (C, Z, S, P/V separately), every other register, the interrupt state (twice),
the work area $F380-$FFFF diff, the VDP registers. Entry A and F loaded separately ($A7 / $00; F
$00 / $FF), so "kept", "constant" and "computed" differ.

| case | inputs | state | separates | F900 | 8250 | WSX |
|---|---|---|---|---|---|---|
| CN-1..9 | — | SCRMOD 0, 1, 2, 3, 4, 5, 6, 7, 8 (each set up with its real VDP mode) | which modes count: 4+ vs 5+; which flag and its sense | ? | ? | ? |
| CN-10 | — | SCRMOD 0 with LINLEN / LINL40 80 (TEXT2) vs 40 | width 80 counted as new or not | ? | ? | ? |
| CN-11 | — | SCRMOD 5 written, VDP and RG0SAV / RG1SAV left in SCREEN 1's mode | SCRMOD vs the register save cells vs the VDP | ? | ? | ? |
| CN-12 | — | SCRMOD 1, VDP and RG0SAV / RG1SAV in SCREEN 5's mode bits | the same, the other way round | ? | ? | ? |
| CN-13 | — | RG0SAV / RG1SAV in SCREEN 5's bits, the VDP's own R#0 / R#1 in SCREEN 1's | save cells vs the VDP (if CN-11/12 show the registers decide) | ? | ? | ? |
| CN-14 | — | SCRMOD 9, $10, $FF | an out-of-range SCRMOD: a compare (>= 5) vs a table | ? | ? | ? |
| CN-15 | — | SCRMOD 10, 11, 12 (the MSX2+ modes, set up for real on the WSX; on the MSX2s the SCRMOD value alone, VDP left in SCREEN 1) | MSX2+ modes counted as new; on an MSX2, the bare value's answer (the CN-14 question) | ? | ? | ? |
| CN-16 | — | S-REGS, interrupts on / off | A kept or set; other registers; the interrupt state | ? | ? | ? |
| CN-17 | — | — | stack depth and time ([README](README.md#the-shared-vram-address-matrix) methods) | ? | ? | ? |

## Related pages

[region page](README.md); [screen modes](../../concepts/screen-modes.md).

## Tests that cover it

None yet.
