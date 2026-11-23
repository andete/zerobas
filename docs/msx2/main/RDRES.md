<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `RDRES` ($017A) — read the reset-status register (MSX2+)

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the FS-A1WSX (the only reference with the entry), the port also on the
> HB-F900 and NMS 8250 ([xrdres.asm](../../../probes/bios/spec/xrdres.asm) on the FS-A1WSX row only,
> [scratchpad/AE_xrdres_msx2p.out](../../../scratchpad/AE_xrdres_msx2p.out); the port by hand on all three:
> [xf4port.asm](../../../probes/bios/spec/xf4port.asm), [scratchpad/AE_xf4port_msx2.out](../../../scratchpad/AE_xf4port_msx2.out);
> across a soft reset: [xf4reset.asm](../../../probes/bios/spec/xf4reset.asm),
> [scratchpad/AE_xf4reset_msx2.out](../../../scratchpad/AE_xf4reset_msx2.out)).
> Goldfish pass 1 (test writer) 2026-11-23: 5 findings, 1 measured (the round trip, xrdres cases 19-20), 2 moved to
> open, 2 claims narrowed to what the cases separate.

## Summary

`RDRES` is an MSX2+ entry; the MSX2 handbook does not list it. It reads I/O port $F4 and returns its
**complement** in A. On the FS-A1WSX the port holds one bit, bit 7, so RDRES returns bit 7 as written
by [WRRES](WRRES.md) (which complements too) and 0 in bits 6-0. The MSX2 handbook does not list
$017A, and on the MSX2 references port $F4 is not there; the address was not called on them.

## The specification

**Interface.** None published in the MSX2 handbook (an MSX2+ addition) [A]. On the MSX2 the handbook's
I/O map lists $F4 as reserved [P A6].

**Measured on the FS-A1WSX** [M] (xrdres cases 0-4, 12, 14; every other register loaded with distinct values):
- **A bit 7 = NOT (bit 7 of IN $F4), A bits 6-0 = 0:** port $7F (preset $00, $7F, $5A) gives A $80; port $FF (preset
  $80, $FF) gives A $00 [M 0-4, 12, 14]. "A := NOT (IN $F4)" fits too, but bits 6-0 of the port always read 1 on the
  FS-A1WSX, so no case can tell it from "bits 6-0 := 0": a test pins bit 7 and bits 6-0 = 0 [A].
- **F:** H and N set, bits 5 and 3 = 0, S / Z / P/V / C left as at entry: entry F $00 gives $12, entry F $FF gives $D7
  (with A $00 or $80) [M 0-3]. That is the flags of a `CPL`, but the new A is only ever $00 / $80, so "bits 5 / 3 from
  the new A" and "bits 5 / 3 := 0" cannot be told apart here [A] (WRRES, whose new A varies, pins the CPL rule).
- BC, DE, HL, IX, IY and the alternate set kept; the interrupt state kept, off or on [M 0-4]. IN $F4 after = IN before
  [M 0-4, 12, 14]: the port is not written -- or written back with the bit it holds; no case separates the two, and
  nothing a caller sees does.
- **Round trip with WRRES:** WRRES v then RDRES gives v AND $80 -- measured back to back with the port preset to the
  opposite reading: WRRES $80 over $FF -> RDRES $80, WRRES $00 over $7F -> RDRES $00 [M 19, 20].

**The port** [M] (by hand, no BIOS call; [AE_xf4port](../../../scratchpad/AE_xf4port_msx2.out)):
- **HB-F900, NMS 8250:** port $F4 reads $FF always -- after OUT $00, $FF, $A5, $5A, $80, $7F, $01, $FE alike: no
  register there [M].
- **FS-A1WSX:** port $F4 keeps **bit 7 only**: IN gives $FF after an OUT with bit 7 set ($FF, $A5, $80, $FE) and $7F
  after one with bit 7 clear ($00, $5A, $7F, $01); bits 6-0 always read 1. At the cartridge's INIT it reads $7F [M].
- **Across a soft reset** (JP $0000, [AE_xf4reset](../../../scratchpad/AE_xf4reset_msx2.out)): on the FS-A1WSX the port
  reads $7F at INIT after a reset entered with $7F and also after one entered with $FF (OUT $80): the start-up sets
  bit 7 to 0 either way; the boot took 55, 52 and 57 JIFFY ticks to reach the cartridge in the three boots -- no
  difference that bit 7 made. The MSX2s read $FF at every boot [M].

## Differences from the reference

C-BIOS's MSX2+ build (the subject) gives the same A, F, registers, port and interrupt state in every case, the
round trip included [M]. Its MSX2 builds have no RDRES: C-BIOS's source assembles the $017A jump only for the V9958
build [A, read in C-BIOS's `src/main.asm`, not run]. In the soft-reset chain C-BIOS's builds gave no reading (our
cartridge's magic in page 3 RAM did not survive, or INIT was not reached again after JP $0000) -- a reset question,
not RDRES's.

## On the turbo R

Measured 2026-11-23 (D-TRSPEC) on the FS-A1GT and FS-A1ST (`biosl_run.py --row turbor`); overview: [turbor/remeasured.md](../../turbor/remeasured.md).

- **Port $F4** [M] (by hand, [AE_trall/xf4port.out](../../../scratchpad/AE_trall/xf4port.out)): reads bit 7 = the bit last written, bit 5 = 1, bits 6 and 4-0 = 0 -- $A0 / $20 (the FS-A1WSX: $FF / $7F). At the cartridge's INIT it reads $A0 (bit 7 = 1; the A1WSX $7F).
- **RDRES** [M] ([AE_trall/xrdres.out](../../../scratchpad/AE_trall/xrdres.out) cases 0-4, 12, 14): A := the port as read ($A0 / $20), not its complement, and F as entered ($00 stays $00, $FF stays $FF); the other registers as on the A1WSX. The round trip (cases 19, 20): WRRES $80 then RDRES gives $A0, WRRES $00 gives $20.
- **Across a soft reset** [M] ([AE_trall/xf4reset.out](../../../scratchpad/AE_trall/xf4reset.out)): no reading on either model. The chain never reaches the cartridge again within 120 s; at the dump the capture, JIFFY, SCNCNT, NEWKEY and the hooks read $FF -- not even the first boot's record survived. What the machine does instead is not measured (it needs a probe that logs to VRAM).

## Open (not measured)

- What bit 7 means to the firmware (the start-up screen): the reset chain showed no difference, and the start-up sets
  the bit back to 0 itself.
- The power-on value before the boot touches the port (INIT already sees the boot's value).
- Stack depth and time.
- What a HARDWARE reset (the reset button) and a power cycle leave in bit 7 -- the events a reset-status register
  exists to tell apart. Only a soft reset (JP $0000) was measured; the harness has no reset-button or power-cycle
  step inside one run.
- $017A on the MSX2 references: not called (it is not an entry there, and what the bytes do is unknown).

## Related pages

[region page](README.md), [WRRES](WRRES.md).

## Tests that cover it

None yet.
