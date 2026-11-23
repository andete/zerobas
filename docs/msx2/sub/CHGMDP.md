<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `CHGMDP` (sub-ROM $01B5) — change the screen mode and reset the palette

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the HB-F900, NMS 8250 and FS-A1WSX ([xmode.asm](../../../probes/bios/spec/xmode.asm), [scratchpad/AE_xmode_msx2.out](../../../scratchpad/AE_xmode_msx2.out), decoded by `scratchpad/xmode_decode.py`).

## Summary

`CHGMDP` is [CHGMOD](CHGMOD.md) plus a palette reset: it switches to the mode in A and initialises
the 16 palette entries. Shared facts: [the screen-modes page](../concepts/screen-modes.md).

## The specification

**Interface.**
- In: A = the screen mode, 0 to 8 [P App. 1, SUB-ROM CHGMDP]; 10-12 on an MSX2+ [A].
- Out: none. Registers: all [P App. 1, SUB-ROM CHGMDP].
- Interrupts on return: [A].

**Behaviour.**
- Changes the VDP mode; the palette is initialised [P App. 1, SUB-ROM CHGMDP].
- Equals CHGMOD then INIPLT [A]; INIPLT also saves the palette in VRAM [P App. 1, INIPLT] — at the
  NEW mode's palette-table address [A] ([P App. 5] gives one per mode).
- The initial palette's values [A].

**Measured** [M] (the same on all three references, A 5): the mode as CHGMOD 5, plus R#16 (the palette
pointer) moved -- the palette is written; out A $07, F $10, interrupts ON.

## Differences from the reference

C-BIOS's MSX2 / MSX2+ builds set the same mode; their R#16 and F on return differ ([scratchpad/AE_xmode_msx2.out](../../../scratchpad/AE_xmode_msx2.out)).

## Open (not measured)

Recorded per case: as [CHGMOD](CHGMOD.md#open-not-measured), plus all 16 palette entries and every
mode's palette table as App. 5 bounds it ($0400-$042F: 48 bytes, although 16 entries of 2 bytes need 32; which bytes are written is part of the measurement).

| case | inputs | state | what it separates | HB-F900 | NMS 8250 | FS-A1WSX |
|---|---|---|---|---|---|---|
| IE | the page's base case (its first row) | entered once with DI, once with EI | interrupt state on return: forced on, forced off, or kept (read twice, §3a) | ? | ? | ? |
| CP-EQ | A = 0..8 | same set-up as CHGMOD's cases | = CHGMOD + INIPLT, output for output | ? | ? | ? |
| CP-PAL | A = 0, 5, 8 | palette entries distinct non-defaults | the reset palette's 16 values; SCREEN 8 differs? | ? | ? | ? |
| CP-SAVE | A = 5, entered from SCREEN 0 width 80 (old table $0F00); also A = 0 (40, 80), 1, 2, 7 | VRAM at every App. 5 palette address garbage | saved at the new mode's address ($7680) vs the old mode's vs not saved | ? | ? | ? |
| CP-OOR | A = 9, $FF | — | CHGMOD's out-of-range rule, palette reset anyway? | ? | ? | ? |
| CP-YJK | A = 10..12 (on the MSX2s: out of range), after locating the R#25-R#27 copies | — | palette in YJK modes | ? | ? | ? |

## Related pages

[The screen-modes page](../concepts/screen-modes.md); [CHGMOD](CHGMOD.md); [INIPLT](INIPLT.md).

## Tests that cover it

none yet
