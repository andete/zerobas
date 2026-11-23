<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `SETGRP` (sub-ROM $00ED) — set the VDP to GRAPHIC 2 (SCREEN 2), only

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the HB-F900, NMS 8250 and FS-A1WSX ([xmode.asm](../../probes/bios/spec/xmode.asm), [scratchpad/AE_xmode_msx2.out](../../scratchpad/AE_xmode_msx2.out), decoded by `scratchpad/xmode_decode.py`).

## Summary

`SETGRP` programs the VDP for SCREEN 2 from the same cells as [INIGRP](INIGRP.md), without the rest
of INIGRP's work. Shared facts: [the screen-modes page](../concepts/screen-modes.md).

## The specification

**Interface.**
- In: as INIGRP (GRPNAM .. GRPPAT) [P App. 1, SUB-ROM SETGRP].
- Out: none; all registers may change [P App. 1, SUB-ROM SETGRP].
- Interrupts on return: [A].

**Behaviour.**
- Sets the VDP to "the high-resolution mode" [P App. 1, SUB-ROM SETGRP], GRAPHIC 2 [P App. 1,
  main-ROM SETGRP]; R#0-R#7, R#10 / R#11 and their copies [A]; nothing else [A].

**Measured** [M] (the same on all three references, RG0SAV-RG7SAV := $A5, from SCREEN 0): the VDP is set to
GRAPHIC 2 -- R#0 / R#2 / R#4 as CHGMOD's mode -- but **R#1's display bit is left clear** (R#1 $35 / $25: the $A5 copy's
bits, not a rebuilt value), the copies are not normalised, SCRMOD is NOT changed (stays 0), and the call returns with
interrupts ON; A $00, F $44.

## Differences from the reference

C-BIOS's MSX2 / MSX2+ builds set the mode bits the same but write R#3 / R#5 / R#6 / R#7 their own way (R#7 := $F4,
the border) and return other A / F ([scratchpad/AE_xmode_msx2.out](../../scratchpad/AE_xmode_msx2.out)).

## Open (not measured)

Recorded per case: as [SETTXT](SETTXT.md#open-not-measured).

| case | inputs | state | what it separates | HB-F900 | NMS 8250 | FS-A1WSX |
|---|---|---|---|---|---|---|
| IE | the page's base case (its first row) | entered once with DI, once with EI | interrupt state on return: forced on, forced off, or kept (read twice, §3a) | ? | ? | ? |
| SG-ONLY | — | SCRMOD, name table, sprites garbage | "VDP only": VRAM block sums and a whole work-area diff $F380-$FFFF (only the register copies may differ) | ? | ? | ? |
| SG-BASE | cells default / moved / unaligned | R#3 / R#4 / R#10 / R#11 copies garbage | R#3 low bits $FF and R#4 low bits $03 forced vs from the cell | ? | ? | ? |
| SG-G3 | — | entered with R#0 M4 set (from SCREEN 4) | M4 cleared: GRAPHIC 2, not GRAPHIC 3 | ? | ? | ? |
| SG-R01 | — | RG0SAV / RG1SAV walking bits ≠ VDP | kept bits | ? | ? | ? |
| SG-R89 | — | R#8 bits 1, 3, 5, 6, 7 and R#9 bits 1, 2, 3, 4, 5, 7, each walked alone, copies ≠ VDP | kept | ? | ? | ? |
| SG-MAIN | main-ROM $007E | same | the *3 claim by a breakpoint on the sub-ROM entry and on EXTROM ($015F) as a call trace | ? | ? | ? |

## Related pages

[The screen-modes page](../concepts/screen-modes.md); [INIGRP](INIGRP.md); MSX1
[SETGRP](../../bios/SETGRP.md).

## Tests that cover it

none yet
