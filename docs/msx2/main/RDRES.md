<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `RDRES` ($017A) — read the reset-status register (MSX2+)

> **Spec:** DRAFT 0 (2026-11-23), from the published interface only; nothing measured yet. References to measure: HB-F900, NMS 8250, FS-A1WSX.

## Summary

`RDRES` is an MSX2+ entry; the MSX2 handbook does not list it. It is assumed to return in A the
value of a status register that survives a soft reset, the one [WRRES](WRRES.md) writes. Which port
it is, whether the value is inverted, and which bits mean what, are assumed until measured.

## The specification

**Interface.** None published in the MSX2 handbook (an MSX2+ addition) [A].
- Out: A = the register's value [A]. Changes: AF only [A].
- The register is I/O port $F4 [A]; on the MSX2 the handbook's I/O map lists $F4 as reserved
  [P A6].
- Whether A is the port as read or its complement [A]. The interrupt state [A].

## Differences from the reference

Not measured yet.

## Open (not measured)

**On the MSX2 references** $017A is not an MSX2 entry: the call is not made there (what it would
run is unknown), and the clean room bars reading the bytes at $017A-$017F. Only the port rows run
on them. Port $F4 is read and written by the probe directly (I/O ports are readable state), so the
call's A can be compared with the port itself. Records: A, F, every other register, the interrupt
state (twice), port $F4 read by hand before and after.

| case | inputs | state | separates | F900 | 8250 | WSX |
|---|---|---|---|---|---|---|
| RR-1 | — | port $F4 := $00 by hand (`OUT`), read back by hand | the port alone: which bits the hardware keeps, whether it reads back at all | ? | ? | ? |
| RR-2 | — | as RR-1 with $A5, $5A, $FF | the same with mixed bits | ? | ? | ? |
| RR-3 | call RDRES | port $F4 := $00, $A5, $5A, $FF by hand | A = port as read vs its complement vs masked | — (not an MSX2 entry) | — (same) | ? |
| RR-4 | WRRES A $A5, then RDRES; again with A $80 | — | the round trip gives back A (both invert or neither) | — | — | ? |
| RR-5 | entry A $A7, F $00 / $FF | S-REGS | F on return; every other register kept | — | — | ? |
| RR-6 | — | interrupts on / off | the interrupt state | — | — | ? |
| RR-7 | — | port $F4 set by hand, then a soft reset (jump to $0000), read by hand at the cartridge's INIT | the register survives a reset; what the boot leaves there | ? | ? | ? |
| RR-8 | — | — | stack depth and time ([README](README.md#the-shared-vram-address-matrix) methods) | — | — | ? |

## Related pages

[region page](README.md), [WRRES](WRRES.md).

## Tests that cover it

None yet.
