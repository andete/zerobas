<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `RDRES` ($017A) — read the reset-status register (MSX2+)

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the FS-A1WSX (the only reference with the entry), the port also on the
> HB-F900 and NMS 8250 ([xrdres.asm](../../probes/bios/spec/xrdres.asm) on the FS-A1WSX row only,
> [scratchpad/AE_xrdres_msx2p.out](../../scratchpad/AE_xrdres_msx2p.out); the port by hand on all three:
> [xf4port.asm](../../probes/bios/spec/xf4port.asm), [scratchpad/AE_xf4port_msx2.out](../../scratchpad/AE_xf4port_msx2.out);
> across a soft reset: [xf4reset.asm](../../probes/bios/spec/xf4reset.asm),
> [scratchpad/AE_xf4reset_msx2.out](../../scratchpad/AE_xf4reset_msx2.out)).

## Summary

`RDRES` is an MSX2+ entry; the MSX2 handbook does not list it. It reads I/O port $F4 and returns its
**complement** in A. On the FS-A1WSX the port holds one bit, bit 7, so RDRES returns bit 7 as written
by [WRRES](WRRES.md) (which complements too) and 0 in bits 6-0. On the MSX2 references $017A is not an
entry and port $F4 is not there.

## The specification

**Interface.** None published in the MSX2 handbook (an MSX2+ addition) [A]. On the MSX2 the handbook's
I/O map lists $F4 as reserved [P A6].

**Measured on the FS-A1WSX** [M] (xrdres cases 0-4, 12, 14; every other register loaded with distinct values):
- **A := NOT (IN $F4):** port $7F (preset $00, $7F, $5A) gives A $80; port $FF (preset $80, $FF) gives A $00
  [M 0-4, 12, 14].
- **F:** H and N set, bits 5 and 3 copied from the new A, S / Z / P/V / C left as at entry -- the flags of a `CPL`:
  entry F $00 gives $12, entry F $FF gives $D7 (with A $00 or $80) [M 0-3].
- BC, DE, HL, IX, IY and the alternate set kept; the port not written (IN after = IN before); the interrupt state kept,
  off or on [M 0-4].
- **Round trip with WRRES:** WRRES v then RDRES gives v AND $80 (both complement; the port keeps bit 7 only) -- from
  the port readings after WRRES (xrdres cases 5-11, 13) and RDRES's rule above [M].

**The port** [M] (by hand, no BIOS call; [AE_xf4port](../../scratchpad/AE_xf4port_msx2.out)):
- **HB-F900, NMS 8250:** port $F4 reads $FF always -- after OUT $00, $FF, $A5, $5A, $80, $7F, $01, $FE alike: no
  register there [M].
- **FS-A1WSX:** port $F4 keeps **bit 7 only**: IN gives $FF after an OUT with bit 7 set ($FF, $A5, $80, $FE) and $7F
  after one with bit 7 clear ($00, $5A, $7F, $01); bits 6-0 always read 1. At the cartridge's INIT it reads $7F [M].
- **Across a soft reset** (JP $0000, [AE_xf4reset](../../scratchpad/AE_xf4reset_msx2.out)): on the FS-A1WSX the port
  reads $7F at INIT after a reset entered with $7F and also after one entered with $FF (OUT $80): the start-up sets
  bit 7 to 0 either way; the boot took 55, 52 and 57 JIFFY ticks to reach the cartridge in the three boots -- no
  difference that bit 7 made. The MSX2s read $FF at every boot [M].

## Differences from the reference

C-BIOS's MSX2+ build (the subject) gives the same A, F, registers, port and interrupt state in every case [M]. Its
MSX2 builds have no RDRES (as the MSX2 references). In the soft-reset chain C-BIOS's builds gave no reading (our
cartridge's magic in page 3 RAM did not survive, or INIT was not reached again after JP $0000) -- a reset question,
not RDRES's.

## Open (not measured)

- What bit 7 means to the firmware (the start-up screen): the reset chain showed no difference, and the start-up sets
  the bit back to 0 itself.
- The power-on value before the boot touches the port (INIT already sees the boot's value).
- Stack depth and time.

## Related pages

[region page](README.md), [WRRES](WRRES.md).

## Tests that cover it

None yet.
