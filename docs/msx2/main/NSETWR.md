<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `NSETWR` ($0171) — set the VDP to write VRAM at an address (128 KB)

> **Spec:** DRAFT 1 (2026-11-23): the shared VRAM address matrix MEASURED on the HB-F900, NMS 8250 and FS-A1WSX
> (identical on all three) -- the address rule, the R#14 / $FFED writes and the SCREEN 0-4 ACPAGE quirk are in
> [README.md](README.md#the-shared-vram-address-matrix) "Measured" (all sixteen VA cases, an interrupt during the call
> included); goldfish pass 1 measured this page's AF, registers, interrupt state, port and save-cell rows
> ([xva3.asm](../../../probes/bios/spec/xva3.asm), [scratchpad/AE_xva3_msx2.out](../../../scratchpad/AE_xva3_msx2.out), decoded by [xva3_decode.py](../../../scratchpad/xva3_decode.py));
> stack depth and time are open.
> Goldfish pass 1 (test writer) 2026-11-23: 10 findings, 8 measured, 0 moved to open.

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
- **Measured** [M] ([xva3.asm](../../../probes/bios/spec/xva3.asm), [scratchpad/AE_xva3_msx2.out](../../../scratchpad/AE_xva3_msx2.out); the same on all three references, entered with interrupts off
  and S-REGS): **A = the high address byte written to port $99** (A13-A8 OR $40, the write flag) and **F = the flags
  of an OR giving it** (H 0, N 0, C 0, P/V parity, S / Z, bits 5 and 3 of A) -- A $52 F $00 for HL $1234, $7F / $28
  for $FFFF, $40 / $00 for SCREEN 1 ACPAGE $40, whatever the entry A and F; BC, DE, HL, IX, IY, BC', DE', HL', AF'
  kept; **interrupts ON on return, entered off**; no port $98 / $9A / $9B write, no save cell changed, **VRAM
  unchanged** (128 KB sums, SW-2), no byte left in the port $99 latch. The pointer is left at the address.
- **Measured** [M] (VA-16, the same on all three references; [xva16.asm](../../../probes/bios/spec/xva16.asm), [scratchpad/AE_xva16_msx2.out](../../../scratchpad/AE_xva16_msx2.out)): entered with interrupts on, it
  returns with them on, and a VDP interrupt is never taken between its first and fourth port $99 write -- one
  arriving there waits until after the fourth, so the address is right however the interrupt falls. The call
  re-enables interrupts itself after the fourth write, inside the call (the rerun's stack depth), not by an EI just
  before its RET.

## Differences from the reference

C-BIOS's MSX2 / MSX2+ builds (the subject) give every case of the
[shared matrix](README.md#the-shared-vram-address-matrix) but these: with ACPAGE not 0 in SCREEN 0-4 they address
HL AND $3FFF with R#14 := 0 ($00123 for VA-11, any ACPAGE) where the references address ACPAGE x $100 + E ($0015A),
in five port $99 writes -- R#14, the low byte, the high byte OR $40, the high byte again -- the lone fifth byte ($41) stays in the port $99 latch and pairs with the caller's next port $99 byte (the probe's R#7 := $5A became an address setting, $01A41, R#7 not written); with
ACPAGE above 3 in SCREEN 5 / 6 or above 1 in SCREEN 7 / 8 they mask ACPAGE where the references add its high bits
(ACPAGE 4 + $C123: $0C123 against $0C223; SCREEN 8 ACPAGE 2 + $1234: $01234 against $01334; xva3); and with SCRMOD 10
(VA-14, the MSX2+ build) they take SCREEN 8's 64 KB page ($11234 for ACPAGE 1 + $1234) where the FS-A1WSX takes
SCREEN 5's 32 KB page ($09234; [xva14.asm](../../../probes/bios/spec/xva14.asm), [scratchpad/AE_xva14_msx2.out](../../../scratchpad/AE_xva14_msx2.out)). VA-16 (an interrupt during the
call): the same as the references.

## Open (not measured)

The [shared VA cases](README.md#the-shared-vram-address-matrix) VA-1 to VA-16 and VC-1 / VC-2, each
followed by two writes to port $98 ($C7, $C8, which no marker equals) and the shared read-back: the
marked addresses show which rule's byte became $C7 (and that none other did), the block sums that
nothing else changed. VC-1 / VC-2 and the 128 KB VRAM read-back have run (xva3; [README](README.md#the-shared-vram-address-matrix)
"Measured"); S-MARK's markers have not -- the address is read from the VDP instead. Plus:

| case | inputs | state | separates | F900 | 8250 | WSX |
|---|---|---|---|---|---|---|
| SW-1 | HL $C123, NSETRD then NSETWR on the same state | VA-3, then VA-4 | the two calls follow the same bank rule (same HL, both repaired states) | ? | ? | ? |
| SW-2 | HL $1234 / $C123 / SCREEN 1 ACPAGE 1, no port write after | S-BASE, VA-3, VA-11 | the call itself writes no VRAM byte (128 KB sum and XOR) | unchanged [M] | unchanged [M] | unchanged [M] |
| SW-3 | HL $1234; A $C7 / $00 / $FF, F $00 / $FF | S-BASE, S-REGS, interrupts off, then on | AF on return; other registers kept; the interrupt state | A $52 F $00; the rest kept; on, entered on or off [M] | the same [M] | the same [M] |
| SW-4 | HL $1234 | as NSETRD's SR-3 | no other VDP register or save cell written | four port $99 writes only; no save cell changed [M] | the same [M] | the same [M] |
| SW-5 | HL $1234 | S-BASE | stack depth and time (README methods) | ? | ? | ? |

Also open: the display off (write timing).

## Related pages

[region page](README.md), [NSETRD](NSETRD.md), [NWRVRM](NWRVRM.md), [BIGFIL](BIGFIL.md); MSX1
[SETWRT](../../bios/SETWRT.md).

## Tests that cover it

None yet.
