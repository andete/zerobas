<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `WRRES` ($017D) — write the reset-status register (MSX2+)

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the FS-A1WSX (the only reference with the entry), the port also on the
> HB-F900 and NMS 8250 ([xrdres.asm](../../probes/bios/spec/xrdres.asm) on the FS-A1WSX row only,
> [scratchpad/AE_xrdres_msx2p.out](../../scratchpad/AE_xrdres_msx2p.out); the port by hand on all three:
> [xf4port.asm](../../probes/bios/spec/xf4port.asm), [scratchpad/AE_xf4port_msx2.out](../../scratchpad/AE_xf4port_msx2.out);
> across a soft reset: [xf4reset.asm](../../probes/bios/spec/xf4reset.asm),
> [scratchpad/AE_xf4reset_msx2.out](../../scratchpad/AE_xf4reset_msx2.out)).

## Summary

`WRRES` is an MSX2+ entry; the MSX2 handbook does not list it. It writes the **complement** of A to I/O
port $F4 and returns that complement in A. On the FS-A1WSX the port keeps only bit 7, so WRRES with
bit 7 of A set leaves the port reading $7F, with it clear $FF; [RDRES](RDRES.md) complements back. On
the MSX2 references $017D is not an entry and port $F4 is not there.

## The specification

**Interface.** None published in the MSX2 handbook (an MSX2+ addition) [A]. On the MSX2 the handbook's
I/O map lists $F4 as reserved [P A6].

**Measured on the FS-A1WSX** [M] (xrdres cases 5-11, 13; the port preset by hand to the opposite bit 7 first):
- **The port gets NOT A:** A $00, $7F, $5A give a port reading $FF afterwards; A $80, $FF, $A5 give $7F [M 5-11, 13].
- **A := NOT A** on return ($00 -> $FF, $80 -> $7F, $FF -> $00, $7F -> $80, $A5 -> $5A, $5A -> $A5) [M 5-11, 13].
- **F:** the flags of a `CPL` -- H and N set, bits 5 and 3 from the new A, S / Z / P/V / C as at entry: $3A, $1A, $32
  from entry $00, $D7 from entry $FF [M 5-10].
- BC, DE, HL, IX, IY and the alternate set kept; the interrupt state kept, off or on [M 5-11].

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

C-BIOS's MSX2+ build (the subject) gives the same port value, A, F, registers and interrupt state in every case [M].
Its MSX2 builds have no WRRES (as the MSX2 references). The soft-reset chain gave no C-BIOS reading (see
[RDRES](RDRES.md)).

## Open (not measured)

- WR-3 / WR-4: which value of bit 7 (if any) skips the start-up screen -- the reset chain (port set by hand, the same
  bit WRRES sets) showed no difference in the time to reach the cartridge, and the start-up resets bit 7 to 0.
- WR-8: the power-on value; stack depth and time.

## Related pages

[region page](README.md), [RDRES](RDRES.md).

## Tests that cover it

None yet.
