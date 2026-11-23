<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `SETMLT` (sub-ROM $00F1) — set the VDP to MULTI COLOUR (SCREEN 3), only

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the HB-F900, NMS 8250 and FS-A1WSX ([xmode.asm](../../../probes/bios/spec/xmode.asm), [scratchpad/AE_xmode_msx2.out](../../../scratchpad/AE_xmode_msx2.out), decoded by `scratchpad/xmode_decode.py`).

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

**Measured** [M] (the same on all three references, RG0SAV-RG7SAV := $A5, from SCREEN 0): the VDP is set to
MULTICOLOUR -- R#0 / R#2 / R#4 as CHGMOD's mode -- but **R#1's display bit is left clear** (R#1 $35 / $25: the $A5 copy's
bits, not a rebuilt value), the copies are not normalised, SCRMOD is NOT changed (stays 0), and the call returns with
interrupts ON; A $00, F $44.

## Differences from the reference

C-BIOS's MSX2 / MSX2+ builds set the mode bits the same but write R#3 / R#5 / R#6 / R#7 their own way (R#7 := $F4,
the border) and return other A / F ([scratchpad/AE_xmode_msx2.out](../../../scratchpad/AE_xmode_msx2.out)).

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
