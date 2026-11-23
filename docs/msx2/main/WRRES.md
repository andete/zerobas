<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `WRRES` ($017D) — write the reset-status register (MSX2+)

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the FS-A1WSX (the only reference with the entry), the port also on the
> HB-F900 and NMS 8250 ([xrdres.asm](../../../probes/bios/spec/xrdres.asm) on the FS-A1WSX row only,
> [scratchpad/AE_xrdres_msx2p.out](../../../scratchpad/AE_xrdres_msx2p.out); the port by hand on all three:
> [xf4port.asm](../../../probes/bios/spec/xf4port.asm), [scratchpad/AE_xf4port_msx2.out](../../../scratchpad/AE_xf4port_msx2.out);
> across a soft reset: [xf4reset.asm](../../../probes/bios/spec/xf4reset.asm),
> [scratchpad/AE_xf4reset_msx2.out](../../../scratchpad/AE_xf4reset_msx2.out)).
> Goldfish pass 1 (test writer) 2026-11-23: 5 findings, 2 measured (the port write, the round trip: xrdres cases
> 15-20), 2 moved to open, 1 wording corrected.

## Summary

`WRRES` is an MSX2+ entry; the MSX2 handbook does not list it. It writes the **complement** of A to I/O
port $F4 and returns that complement in A. On the FS-A1WSX the port keeps only bit 7, so WRRES with
bit 7 of A set leaves the port reading $7F, with it clear $FF, whatever it read before; [RDRES](RDRES.md)
complements back. The MSX2 handbook does not list $017D, and on the MSX2 references port $F4 is not there; the
address was not called on them.

## The specification

**Interface.** None published in the MSX2 handbook (an MSX2+ addition) [A]. On the MSX2 the handbook's
I/O map lists $F4 as reserved [P A6].

**Measured on the FS-A1WSX** [M] (xrdres cases 5-11, 13, 15-18; the port preset by hand first, IN $F4 read before
and after the call):
- **The port gets NOT A:** with the port preset to the OTHER reading, A $00 and $7F turn $7F into $FF, A $80 and $FF
  turn $FF into $7F (cases 15-18) -- the call writes the port [M 15-18]. In cases 5-11 and 13 the preset already gave
  the reading the call leaves (A $00, $7F, $5A -> $FF; A $80, $FF, $A5 -> $7F): they pin the value, not the write
  [M 5-11, 13].
- **A := NOT A** on return ($00 -> $FF, $80 -> $7F, $FF -> $00, $7F -> $80, $A5 -> $5A, $5A -> $A5) [M 5-11, 13].
- **F:** the flags of a `CPL` -- H and N set, bits 5 and 3 from the new A, S / Z / P/V / C as at entry: $3A, $1A, $32
  from entry $00, $D7 from entry $FF [M 5-10, 15-18]. (Here the new A varies in bits 5 / 3 -- $FF / $7F / $5A / $A5
  -- so "from the new A" is pinned, unlike RDRES's.)
- BC, DE, HL, IX, IY and the alternate set kept; the interrupt state kept, off or on [M 5-11].

**The port** [M] (by hand, no BIOS call; [AE_xf4port](../../../scratchpad/AE_xf4port_msx2.out)):
- **HB-F900, NMS 8250:** port $F4 reads $FF always -- after OUT $00, $FF, $A5, $5A, $80, $7F, $01, $FE alike: no
  register there [M].
- **FS-A1WSX:** port $F4 keeps **bit 7 only**: IN gives $FF after an OUT with bit 7 set ($FF, $A5, $80, $FE) and $7F
  after one with bit 7 clear ($00, $5A, $7F, $01); bits 6-0 always read 1. At the cartridge's INIT it reads $7F [M].
- **Round trip:** WRRES then RDRES back to back, from the opposite port reading, gives A = the value written: WRRES $80
  over $FF -> RDRES $80 (port $7F), WRRES $00 over $7F -> RDRES $00 (port $FF) [M 19, 20]; in general bit 7 of the
  value, bits 6-0 0.
- **Across a soft reset** (JP $0000, [AE_xf4reset](../../../scratchpad/AE_xf4reset_msx2.out)): on the FS-A1WSX the port
  reads $7F at INIT after a reset entered with $7F and also after one entered with $FF (OUT $80): the start-up sets
  bit 7 to 0 either way; the boot took 55, 52 and 57 JIFFY ticks to reach the cartridge in the three boots -- no
  difference that bit 7 made. The MSX2s read $FF at every boot [M].

## Differences from the reference

C-BIOS's MSX2+ build (the subject) gives the same port value, A, F, registers and interrupt state in every case,
cases 15-20 included [M]. Its MSX2 builds have no WRRES: C-BIOS's source assembles the $017D jump only for the V9958
build [A, read in C-BIOS's `src/main.asm`, not run]. (The one byte that differs in every record is the probe's
slot readout, ($FFFF) -- the machines' slot layouts, not WRRES.) The soft-reset chain gave no C-BIOS reading (see
[RDRES](RDRES.md)).

## On the turbo R

Measured 2026-11-23 (D-TRSPEC) on the FS-A1GT and FS-A1ST (`biosl_run.py --row turbor`); overview: [turbor/remeasured.md](../../turbor/remeasured.md).

- **WRRES** [M] ([AE_trall/xrdres.out](../../../scratchpad/AE_trall/xrdres.out) cases 5-11, 13, 15-18): port bit 7 := A's bit 7, NOT its complement -- A $00, $7F, $5A give $20, A $80, $FF, $A5 give $A0 (cases 5-11 and 13 start from the other reading, so they show the write; on the turbo R cases 15-18 start from the reading the call leaves and pin only the value). A and F come back as entered (the A1WSX: A := NOT A, a CPL's F); the other registers as on the A1WSX.
- **The port and a soft reset** [M]: [RDRES](RDRES.md)'s turbo R section -- with bit 7 = 1 (WRRES A $80 .. $FF) a JP $0000 boots again into the cartridge in 51 frames, VRAM kept; with bit 7 = 0 (WRRES A $00 .. $7F) it never comes back (both machines stop with interrupts off) ([AE_xtrreset1_tr.out](../../../scratchpad/AE_xtrreset1_tr.out), [AE_xtrreset0_tr.out](../../../scratchpad/AE_xtrreset0_tr.out); the port written by hand, as WRRES writes it).

## Open (not measured)

- WR-3 / WR-4: which value of bit 7 (if any) skips the start-up screen -- the reset chain (port set by hand, the same
  bit WRRES sets) showed no difference in the time to reach the cartridge, and the start-up resets bit 7 to 0.
- WR-8: the power-on value; stack depth and time.
- What a HARDWARE reset (the reset button) and a power cycle leave in bit 7 -- the events a reset-status register
  exists to tell apart. Only a soft reset (JP $0000) was measured; the harness has no reset-button or power-cycle
  step inside one run.
- $017D on the MSX2 references: not called (it is not an entry there, and what the bytes do is unknown).

## Related pages

[region page](README.md), [RDRES](RDRES.md).

## Tests that cover it

None yet.
