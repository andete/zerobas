<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `WRRES` ($017D) — write the reset-status register (MSX2+)

> **Spec:** DRAFT 0 (2026-11-23), from the published interface only; nothing measured yet. References to measure: HB-F900, NMS 8250, FS-A1WSX.

## Summary

`WRRES` is an MSX2+ entry; the MSX2 handbook does not list it. It is assumed to store A in the
status register that survives a soft reset, the one [RDRES](RDRES.md) reads; one bit is assumed to
decide whether the start-up screen is shown after a reset. The port, any inversion and the bits'
meanings are assumed until measured.

## The specification

**Interface.** None published in the MSX2 handbook (an MSX2+ addition) [A].
- In: A = the value [A]. Out: none [A]. Changes: AF at most [A].
- The register is I/O port $F4 [A]; on the MSX2 the handbook's I/O map lists $F4 as reserved
  [P A6].
- Whether the port gets A or its complement [A]. Bit 7 decides whether a reset shows the start-up
  screen [A]. The interrupt state [A].

## Differences from the reference

Not measured yet.

## Open (not measured)

**On the MSX2 references** $017D is not an MSX2 entry: the call is not made there, and the clean
room bars reading its bytes; the port's own behaviour there is [RDRES](RDRES.md)'s RR-1, RR-2 and
RR-7. Records: port $F4 read by hand after the call, every register, the interrupt state (twice);
for the reset cases, whether the start-up screen appears (a screenshot, and the time to the
cartridge's INIT).

| case | inputs | state | separates | F900 | 8250 | WSX |
|---|---|---|---|---|---|---|
| WR-1 | A $00 | port $F4 := $5A by hand | the port gets A vs NOT A vs is unchanged | — (not an MSX2 entry) | — (same) | ? |
| WR-2 | A $A5, then $5A, then $FF | — | inversion and which bits the hardware keeps | — | — | ? |
| WR-3 | A $80 / $00, then a soft reset | — | which value of bit 7 skips the start-up screen | — | — | ? |
| WR-4 | A $7F / $FF, then a soft reset | — | whether any other bit changes the boot | — | — | ? |
| WR-5 | A $A7, entry F $00 / $FF | S-REGS | A and F on return (kept, complemented); other registers kept | — | — | ? |
| WR-6 | A $A5 | interrupts on / off | the interrupt state | — | — | ? |
| WR-7 | A $A5, then RDRES; again with A $80 | — | the round trip (the same runs as [RDRES](RDRES.md)'s RR-4) | — | — | ? |
| WR-8 | A $A5, then a power cycle | — | the register's power-on value (what RDRES reads at first boot) | — | — | ? |
| WR-9 | A $A5 | — | stack depth and time ([README](README.md#the-shared-vram-address-matrix) methods) | — | — | ? |

## Related pages

[region page](README.md), [RDRES](RDRES.md).

## Tests that cover it

None yet.
