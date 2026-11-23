<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `CHKSLZ` ($0162) — find the sub-ROM's slot

> **Spec:** DRAFT 0 (2026-11-23), from the published interface only; nothing measured yet. References to measure: HB-F900, NMS 8250, FS-A1WSX.

## Summary

`CHKSLZ` is an MSX2 jump-table entry the handbook does not list. C-BIOS names it "search slots for
the subrom". Everything on this page is assumed until measured: what it searches for, what it
returns, and whether it writes EXBRSA ([region page](README.md#the-sub-rom)).

## The specification

**Interface.** None published (absent from App. 1's MSX2 entries) [A].
- It looks through the slots for the sub-ROM, recognised by the "CD" ID at the start of its header,
  and records the slot in EXBRSA [A]. (That a header's ID "CD" marks a sub-ROM is [P 5§7.3.1].)
- Outputs in registers, the slots it leaves selected and the interrupt state [A].

## Differences from the reference

Not measured yet.

## Open (not measured)

Records: every register, the interrupt state (twice), port $A8 and the secondary slot registers
(read through page-3 RAM's $FFFF where the slot is expanded), EXBRSA, EXPTBL / SLTTBL, $F380-$FFFF
work-area diff, page 0-2 slots after.

| case | inputs | state | separates | F900 | 8250 | WSX |
|---|---|---|---|---|---|---|
| CZ-1 | — | EXBRSA := $A5 | writes EXBRSA (to the sub-ROM's slot) vs returns it only (EXBRSA stays $A5) | ? | ? | ? |
| CZ-2 | — | EXBRSA := $00 (the "no sub-ROM" value) | the same from $00: whether $00 is overwritten or kept | ? | ? | ? |
| CZ-3 | — | EXBRSA := the sub-ROM's real ID | the result as a register / flag (A, Z, C) when EXBRSA already agrees | ? | ? | ? |
| CZ-4 | — | S-REGS, entry F $00 / $FF | every register out: the slot ID in A? flags as "found"? | ? | ? | ? |
| CZ-5 | — | a RAM page 0 made to start with "CD", planted in a slot BEFORE the sub-ROM's in slot order (0-0 ... 3-3), then in one AFTER it (a RAM cartridge in a free slot where the machine has no RAM there: a configured machine, said so) | before: first "CD" found (a search) vs the true sub-ROM; after: unchanged either way, so the pair parts "search in order" from "fixed slot" | ? | ? | ? |
| CZ-6 | — | EXPTBL's expanded flag for the sub-ROM's primary slot cleared | searches by EXPTBL vs by probing hardware | ? | ? | ? |
| CZ-7 | — | interrupts on / off | the interrupt state on return | ? | ? | ? |
| CZ-8 | — | after the call | the page 0-2 slots and SLTTBL restored | ? | ? | ? |
| CZ-9 | — | a reference CONFIGURED with its sub-ROM in another slot (same ROM images; a different machine, said so) | the result follows the sub-ROM, not a slot constant | ? | ? | ? |
| CZ-10 | — | a reference configured WITHOUT a sub-ROM, if it boots at all (if not, the row is dropped, with that reason) | what "not found" returns, and EXBRSA after | ? | ? | ? |
| CZ-11 | — | — | stack depth and time (README methods) | ? | ? | ? |

## Related pages

[region page](README.md), [EXTROM](EXTROM.md), [SUBROM](SUBROM.md); [slots](../../concepts/slots.md).

## Tests that cover it

None yet.
