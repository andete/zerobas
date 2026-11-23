<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `NSETWR` ($0171) — set the VDP to write VRAM at an address (128 KB)

> **Spec:** DRAFT 1 (2026-11-23): the shared VRAM address matrix MEASURED on the HB-F900, NMS 8250 and FS-A1WSX
> (identical on all three) -- the address rule, the R#14 / $FFED writes and the SCREEN 0-4 ACPAGE quirk are in
> [README.md](README.md#the-shared-vram-address-matrix) "Measured" (all sixteen VA cases, an interrupt during the call
> included); this page's own cases beyond it are not measured yet, but for the interrupt state entered with interrupts on.

## Summary

`NSETWR` is the MSX2's [SETWRT](../../bios/SETWRT.md) for 128 KB of VRAM: it sets the VDP up so that
the next writes to port $98 store into VRAM from the address in HL onward. The handbook names the
entry **NSTWRT**; C-BIOS names it NSETWR. Where A16 comes from is not published.

## The specification

**Interface.**
- In: HL = the VRAM address [P A1]. Out: none [P A1]. Changes: AF [P A1].
- After it, a write to port $98 stores at the address, the address counting up after each write
  [P 4§2.2] [A].
- A16, R#14 and its save cell, and SCREEN 0-4: one of the rival rules of the
  [shared VRAM address matrix](README.md#the-shared-vram-address-matrix) [A]; that it follows the
  same rule as [NSETRD](NSETRD.md) [A].
- BC, DE, HL, IX, IY kept [A]. The interrupt state on return [A].
- **Measured** [M] (VA-16, the same on all three references; [xva16.asm](../../../probes/bios/spec/xva16.asm), [scratchpad/AE_xva16_msx2.out](../../../scratchpad/AE_xva16_msx2.out)): entered with interrupts on, it
  returns with them on, and a VDP interrupt is never taken between its first and fourth port $99 write -- one
  arriving there waits until after the fourth, so the address is right however the interrupt falls.

## Differences from the reference

C-BIOS's MSX2 / MSX2+ builds (the subject) give every case of the
[shared matrix](README.md#the-shared-vram-address-matrix) but two: with ACPAGE not 0 in SCREEN 0-4 they address HL
($00123 for VA-11, five port $99 writes) where the references address ACPAGE x $100 + E ($0015A); and with SCRMOD 10
(VA-14, the MSX2+ build) they take SCREEN 8's 64 KB page ($11234 for ACPAGE 1 + $1234) where the FS-A1WSX takes
SCREEN 5's 32 KB page ($09234; [xva14.asm](../../../probes/bios/spec/xva14.asm), [scratchpad/AE_xva14_msx2.out](../../../scratchpad/AE_xva14_msx2.out)). VA-16 (an interrupt during the
call): the same as the references.

## Open (not measured)

The [shared VA cases](README.md#the-shared-vram-address-matrix) VA-1 to VA-16 and VC-1 / VC-2, each
followed by two writes to port $98 ($C7, $C8, which no marker equals) and the shared read-back: the
marked addresses show which rule's byte became $C7 (and that none other did), the block sums that
nothing else changed. Plus:

| case | inputs | state | separates | F900 | 8250 | WSX |
|---|---|---|---|---|---|---|
| SW-1 | HL $C123, NSETRD then NSETWR on the same state | VA-3, then VA-4 | the two calls follow the same bank rule (same HL, both repaired states) | ? | ? | ? |
| SW-2 | HL $1234, no port write after | S-BASE | the call itself writes no VRAM byte (block sums and markers unchanged) | ? | ? | ? |
| SW-3 | HL $1234; A $A7 / $00, F $00 / $FF | S-BASE, S-REGS, interrupts off, then on | AF on return; other registers kept; the interrupt state | entered on: on [M] (VA-16); the rest ? | entered on: on [M] (VA-16); the rest ? | entered on: on [M] (VA-16); the rest ? |
| SW-4 | HL $1234 | as NSETRD's SR-3 | no other VDP register or save cell written | ? | ? | ? |
| SW-5 | HL $1234 | S-BASE | stack depth and time (README methods) | ? | ? | ? |

Also open: the display off (write timing).

## Related pages

[region page](README.md), [NSETRD](NSETRD.md), [NWRVRM](NWRVRM.md), [BIGFIL](BIGFIL.md); MSX1
[SETWRT](../../bios/SETWRT.md).

## Tests that cover it

None yet.
