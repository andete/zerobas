<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `NWRVRM` ($0177) — write a VRAM byte (128 KB)

> **Spec:** DRAFT 1 (2026-11-23): the shared VRAM address matrix MEASURED on the HB-F900, NMS 8250 and FS-A1WSX
> (identical on all three) -- the address rule, the R#14 / $FFED writes and the SCREEN 0-4 ACPAGE quirk are in
> [README.md](README.md#the-shared-vram-address-matrix) "Measured" (all sixteen VA cases, an interrupt during the call
> included); goldfish pass 1 measured this page's AF, registers, interrupt state, port and save-cell rows
> ([xva3.asm](../../../probes/bios/spec/xva3.asm), [scratchpad/AE_xva3_msx2.out](../../../scratchpad/AE_xva3_msx2.out), decoded by [xva3_decode.py](../../../scratchpad/xva3_decode.py));
> stack depth and time are open.
> Goldfish pass 1 (test writer) 2026-11-23: 12 findings, 10 measured, 0 moved to open.

## Summary

`NWRVRM` is the MSX2's [WRTVRM](../../bios/WRTVRM.md) for 128 KB of VRAM: it stores A at the VRAM
address in HL. Which 64 KB half, and whether the screen mode matters, is not published.

## The specification

**Interface.**
- In: HL = the VRAM address, A = the byte [P A1]. Out: none [P A1]. Changes: AF [P A1].
- A16, R#14 and its save cell, and SCREEN 0-4: one of the rival rules of the
  [shared VRAM address matrix](README.md#the-shared-vram-address-matrix) [A].
- **Measured** [M] ([xva3.asm](../../../probes/bios/spec/xva3.asm), [scratchpad/AE_xva3_msx2.out](../../../scratchpad/AE_xva3_msx2.out); the same on all three references, entered with interrupts off
  and S-REGS): **A and F kept** (entry A $00 F $FF, A $FF F $00 and A $C7 F $00 come back as they went in -- xva's
  constant-looking F $02 was its entry F); BC, DE, HL, IX, IY, BC', DE', HL', AF' kept; **interrupts ON on return,
  entered off**; one port $98 write (the byte); no port $9A / $9B write, no save cell changed; **exactly one VRAM byte
  changes**, the one at the address (128 KB sum and XOR, VA-1, VA-3, VA-11). The pointer is left at the address + 1.
- **Measured** [M] (VA-16, the same on all three references; [xva16.asm](../../../probes/bios/spec/xva16.asm), [scratchpad/AE_xva16_msx2.out](../../../scratchpad/AE_xva16_msx2.out)): entered with interrupts on, it
  returns with them on, and a VDP interrupt is never taken between its first and fourth port $99 write -- one
  arriving there waits until after the fourth, so the address is right however the interrupt falls. The call
  re-enables interrupts itself after the fourth write, inside the call (the rerun's stack depth), not by an EI just
  before its RET -- and before its port $98 write: at every interrupt taken after the fourth write the port $98 log was still empty, so an interrupt routine can run between the address setting and the data byte.

## Differences from the reference

C-BIOS's MSX2 / MSX2+ builds (the subject) give every case of the
[shared matrix](README.md#the-shared-vram-address-matrix) but these: with ACPAGE not 0 in SCREEN 0-4 they address
HL AND $3FFF with R#14 := 0 ($00123 for VA-11, any ACPAGE) where the references address ACPAGE x $100 + E ($0015A),
in five port $99 writes -- R#14, the low byte, the high byte OR $40, the high byte again -- then the byte (the port $98 write clears the lone fifth byte $41 from the latch in the emulated VDP: a register write after the call took effect); with
ACPAGE above 3 in SCREEN 5 / 6 or above 1 in SCREEN 7 / 8 they mask ACPAGE where the references add its high bits
(ACPAGE 4 + $C123: $0C123 against $0C223; SCREEN 8 ACPAGE 2 + $1234: $01234 against $01334; xva3); and with SCRMOD 10
(VA-14, the MSX2+ build) they take SCREEN 8's 64 KB page ($11234 for ACPAGE 1 + $1234) where the FS-A1WSX takes
SCREEN 5's 32 KB page ($09234; [xva14.asm](../../../probes/bios/spec/xva14.asm), [scratchpad/AE_xva14_msx2.out](../../../scratchpad/AE_xva14_msx2.out)). VA-16 (an interrupt during the
call): the same as the references.

## On the turbo R

Measured 2026-11-23 (D-TRSPEC) on the FS-A1GT / FS-A1ST: xva14 gives the same bytes as on the FS-A1WSX, on both models, and xva3 differs only in case 0's port-log slots that the call does not use (power-on RAM). xva16 is timing: the FS-A1GT's calibration counts one more loop per frame than the A1ST and the A1WSX ($2A, not $29), so each step's interrupt lands one NOP elsewhere and the marks, logged writes and SP depths move -- the same SP depths ($1C-$26) as on the MSX2s, no new outcome [M] ([AE_trall/xva14.out](../../../scratchpad/AE_trall/xva14.out), [AE_trall/xva3.out](../../../scratchpad/AE_trall/xva3.out), [AE_trall/xva16.out](../../../scratchpad/AE_trall/xva16.out); overview: [turbor/remeasured.md](../../turbor/remeasured.md)).

## Open (not measured)

The [shared VA cases](README.md#the-shared-vram-address-matrix) VA-1 to VA-16 and VC-1 / VC-2 with A
$C7 (no marker equals it): the marked addresses show which rule's byte became $C7 and that no other
did; the block sums, that nothing else changed. Then one write to port $98 ($C9) shows where the
counter was left. VC-1 / VC-2 and the 128 KB VRAM read-back have run (xva3; [README](README.md#the-shared-vram-address-matrix)
"Measured"); S-MARK's markers have not -- the address is read from the VDP instead. Plus:

| case | inputs | state | separates | F900 | 8250 | WSX |
|---|---|---|---|---|---|---|
| WV-1 | HL $1234; A $00 / $FF / $C7; F $FF / $00 / $00 | S-BASE, S-REGS | A kept or not; F on return; other registers kept | A and F kept; the rest kept [M] | the same [M] | the same [M] |
| WV-2 | HL $1234, A $C7 | S-BASE, interrupts on, then off | the interrupt state | on, entered on or off [M] | on, either way [M] | on, either way [M] |
| WV-3 | HL $1234, A $C7 | as NSETRD's SR-3 | no other VDP register or save cell written | four port $99 writes, one $98 write; no save cell changed [M] | the same [M] | the same [M] |
| WV-4 | HL $1234, A $C7 | S-BASE | stack depth and time (README methods) | ? | ? | ? |

Also open: the display off (write timing).

## Related pages

[region page](README.md), [NSETWR](NSETWR.md), [NRDVRM](NRDVRM.md), [BIGFIL](BIGFIL.md); MSX1
[WRTVRM](../../bios/WRTVRM.md).

## Tests that cover it

None yet.
