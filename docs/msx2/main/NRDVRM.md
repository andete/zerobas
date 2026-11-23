<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `NRDVRM` ($0174) — read a VRAM byte (128 KB)

> **Spec:** DRAFT 1 (2026-11-23): the shared VRAM address matrix MEASURED on the HB-F900, NMS 8250 and FS-A1WSX
> (identical on all three) -- the address rule, the R#14 / $FFED writes and the SCREEN 0-4 ACPAGE quirk are in
> [README.md](README.md#the-shared-vram-address-matrix) "Measured" (all sixteen VA cases, an interrupt during the call
> included); goldfish pass 1 measured this page's AF, registers, interrupt state, port and save-cell rows
> ([xva3.asm](../../../probes/bios/spec/xva3.asm), [scratchpad/AE_xva3_msx2.out](../../../scratchpad/AE_xva3_msx2.out), decoded by [xva3_decode.py](../../../scratchpad/xva3_decode.py));
> stack depth and time are open.
> Goldfish pass 1 (test writer) 2026-11-23: 12 findings, 10 measured, 1 moved to open.

## Summary

`NRDVRM` is the MSX2's [RDVRM](../../bios/RDVRM.md) for 128 KB of VRAM: it returns in A the VRAM byte
at the address in HL. Which 64 KB half, and whether the screen mode matters, is not published.

## The specification

**Interface.**
- In: HL = the VRAM address [P A1]. Out: A = the byte read [P A1]. Changes: F [P A1] (A is the
  output).
- A16, R#14 and its save cell, and SCREEN 0-4: one of the rival rules of the
  [shared VRAM address matrix](README.md#the-shared-vram-address-matrix) [A].
- **Measured** [M] ([xva3.asm](../../../probes/bios/spec/xva3.asm), [scratchpad/AE_xva3_msx2.out](../../../scratchpad/AE_xva3_msx2.out); the same on all three references, entered with interrupts off
  and S-REGS): A = the byte read; **F = the flags of an AND giving the high address byte written to port $99** (H 1,
  N 0, C 0, P/V parity, S / Z, bits 5 and 3) -- not the flags of H AND $3F: in SCREEN 1 with ACPAGE 3 and HL $C123
  the high byte written is $03 and F = $14 (parity even), where H AND $3F = $01 would give $10 (xva case 19, xva3
  case 16 with entry F $FF); $14 for HL $1234, $3C for $FFFF, $54 for SCREEN 1 ACPAGE $40. BC, DE, HL, IX, IY, BC',
  DE', HL', AF' kept; **interrupts ON on return, entered off**; no port $98 / $9A / $9B write, no save cell changed,
  **VRAM unchanged** (128 KB sums). The pointer is left at the address + 2 (the pre-fetch, then the read).
- **Measured** [M] (VA-16, the same on all three references; [xva16.asm](../../../probes/bios/spec/xva16.asm), [scratchpad/AE_xva16_msx2.out](../../../scratchpad/AE_xva16_msx2.out)): entered with interrupts on, it
  returns with them on, and a VDP interrupt is never taken between its first and fourth port $99 write -- one
  arriving there waits until after the fourth, so the address is right however the interrupt falls. The call
  re-enables interrupts itself after the fourth write, inside the call (the rerun's stack depth), not by an EI just
  before its RET; whether its port $98 read comes before or after that is not measured (the port log sees OUTs only).

## Differences from the reference

C-BIOS's MSX2 / MSX2+ builds (the subject) give every case of the
[shared matrix](README.md#the-shared-vram-address-matrix) but these: with ACPAGE not 0 in SCREEN 0-4 they address
HL AND $3FFF with R#14 := 0 ($00123 for VA-11, any ACPAGE) where the references address ACPAGE x $100 + E ($0015A),
in five port $99 writes -- R#14, the low byte, the high byte OR $40, the high byte again -- a WRITE setting, then the read (the port $98 read clears the lone fifth byte $01 from the latch in the emulated VDP: a register write after the call took effect); with
ACPAGE above 3 in SCREEN 5 / 6 or above 1 in SCREEN 7 / 8 they mask ACPAGE where the references add its high bits
(ACPAGE 4 + $C123: $0C123 against $0C223; SCREEN 8 ACPAGE 2 + $1234: $01234 against $01334; xva3); and with SCRMOD 10
(VA-14, the MSX2+ build) they take SCREEN 8's 64 KB page ($11234 for ACPAGE 1 + $1234) where the FS-A1WSX takes
SCREEN 5's 32 KB page ($09234; [xva14.asm](../../../probes/bios/spec/xva14.asm), [scratchpad/AE_xva14_msx2.out](../../../scratchpad/AE_xva14_msx2.out)). VA-16 (an interrupt during the
call): the same as the references.

## On the turbo R

Measured 2026-11-23 (D-TRSPEC) on the FS-A1GT / FS-A1ST: xva14 gives the same bytes as on the FS-A1WSX, on both models, and xva3 differs only in case 0's port-log slots that the call does not use (power-on RAM). xva16 is timing: the FS-A1GT's calibration counts one more loop per frame than the A1ST and the A1WSX ($2A, not $29), so each step's interrupt lands one NOP elsewhere and the marks, logged writes and SP depths move -- the same SP depths ($1C-$26) as on the MSX2s, no new outcome [M] ([AE_trall/xva14.out](../../../scratchpad/AE_trall/xva14.out), [AE_trall/xva3.out](../../../scratchpad/AE_trall/xva3.out), [AE_trall/xva16.out](../../../scratchpad/AE_trall/xva16.out); overview: [turbor/remeasured.md](../../turbor/remeasured.md)).

## Open (not measured)

The [shared VA cases](README.md#the-shared-vram-address-matrix) VA-1 to VA-16 and VC-1 / VC-2: A
names the rule through S-MARK; then one read of port $98 (where the counter was left) and the shared
read-back, whose sixteen 8 KB-block sums and markers show VRAM unchanged. VC-1 / VC-2 and the 128 KB VRAM read-back have run (xva3; [README](README.md#the-shared-vram-address-matrix)
"Measured"); S-MARK's markers have not -- the address is read from the VDP instead. Plus:

| case | inputs | state | separates | F900 | 8250 | WSX |
|---|---|---|---|---|---|---|
| RV-1 | HL $1234 / $FFFF; SCREEN 1 ACPAGE 3 (HL $C123, high byte written $03, H AND $3F $01); F $00 / $FF; A $C7 / $00 / $FF | S-BASE, S-REGS | F's source: the flags of H AND $3F (RDVRM's MSX1 rule), of H, of the byte read, or of the high byte written | flags of the high byte written: $14 / $3C; ACPAGE 3 $14 [M] | the same [M] | the same [M] |
| RV-2 | HL $1234 | S-BASE, interrupts on, then off | the interrupt state: kept / always on / off | on, entered on or off [M] | on, either way [M] | on, either way [M] |
| RV-3 | HL $1234 | as NSETRD's SR-3 | no other VDP register or save cell written | four port $99 writes only; no save cell changed [M] | the same [M] | the same [M] |
| RV-5 | HL $1234, interrupts on, an H.TIMI handler that reads VRAM | VA-16's sweep | whether the port $98 read lies inside the window with interrupts off (VA-16's port log sees OUTs only) | ? | ? | ? |
| RV-4 | HL $1234 | S-BASE | stack depth and time (README methods) | ? | ? | ? |

Also open: the display off.

## Related pages

[region page](README.md), [NSETRD](NSETRD.md), [NWRVRM](NWRVRM.md); MSX1 [RDVRM](../../bios/RDVRM.md).

## Tests that cover it

None yet.
