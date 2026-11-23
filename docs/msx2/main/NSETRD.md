<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `NSETRD` ($016E) — set the VDP to read VRAM at an address (128 KB)

> **Spec:** DRAFT 1 (2026-11-23): the shared VRAM address matrix MEASURED on the HB-F900, NMS 8250 and FS-A1WSX
> (identical on all three) -- the address rule, the R#14 / $FFED writes and the SCREEN 0-4 ACPAGE quirk are in
> [README.md](README.md#the-shared-vram-address-matrix) "Measured" (all sixteen VA cases, an interrupt during the call
> included); goldfish pass 1 measured this page's AF, registers, interrupt state, port and save-cell rows
> ([xva3.asm](../../../probes/bios/spec/xva3.asm), [scratchpad/AE_xva3_msx2.out](../../../scratchpad/AE_xva3_msx2.out), decoded by [xva3_decode.py](../../../scratchpad/xva3_decode.py));
> stack depth and time are open.
> Goldfish pass 1 (test writer) 2026-11-23: 10 findings, 8 measured, 0 moved to open.

## Summary

`NSETRD` is the MSX2's [SETRD](../../bios/SETRD.md) for 128 KB of VRAM: it sets the VDP up so that
the next reads of port $98 return VRAM from the address in HL onward. Which 64 KB half the address
lies in, and whether the screen mode matters, the published interface does not say.

## The specification

**Interface.**
- In: HL = the VRAM address [P A1]. Out: none [P A1]. Changes: AF [P A1].
- After it, a read of port $98 returns the byte at the address, and the address counts up after
  each read [P 4§2.2] [A] (the handbook says "enables VRAM to be read", not where the counter ends).
- Where A16 comes from, whether R#14 and its save cell are written or put back, and whether SCREEN
  0-4 mask the address to 16 KB: one of the rival rules of the
  [shared VRAM address matrix](README.md#the-shared-vram-address-matrix) [A].
- **Measured** [M] ([xva3.asm](../../../probes/bios/spec/xva3.asm), [scratchpad/AE_xva3_msx2.out](../../../scratchpad/AE_xva3_msx2.out); the same on all three references, entered with interrupts off
  and S-REGS): **A = the high address byte written to port $99** (A13-A8, bits 7-6 clear: the read flag) and **F =
  the flags of an AND giving it** (H 1, N 0, C 0, P/V parity, S / Z, bits 5 and 3 of A) -- A $12 F $14 for HL $1234,
  $3F / $3C for $FFFF, $00 / $54 for SCREEN 1 ACPAGE $40, whatever the entry A ($C7, $00, $FF) and F ($00, $FF);
  BC, DE, HL, IX, IY, BC', DE', HL', AF' kept; **interrupts ON on return, entered off**; no port $98 / $9A / $9B
  write, no save cell $FFE7-$FFF6 changed, VRAM unchanged (128 KB sums), no byte left in the port $99 latch. The
  pointer is left at the address + 1 (the VDP's pre-fetch).
- **Measured** [M] (VA-16, the same on all three references; [xva16.asm](../../../probes/bios/spec/xva16.asm), [scratchpad/AE_xva16_msx2.out](../../../scratchpad/AE_xva16_msx2.out)): entered with interrupts on, it
  returns with them on, and a VDP interrupt is never taken between its first and fourth port $99 write -- one
  arriving there waits until after the fourth, so the address is right however the interrupt falls. The call
  re-enables interrupts itself after the fourth write, inside the call (the rerun's stack depth), not by an EI just
  before its RET.

## Differences from the reference

C-BIOS's MSX2 / MSX2+ builds (the subject) give every case of the
[shared matrix](README.md#the-shared-vram-address-matrix) but these: with ACPAGE not 0 in SCREEN 0-4 they address
HL AND $3FFF with R#14 := 0 ($00123 for VA-11, any ACPAGE) where the references address ACPAGE x $100 + E ($0015A),
in five port $99 writes -- R#14, the low byte, the high byte OR $40, the high byte again -- a WRITE setting (the pointer shows no pre-fetch), and the lone fifth byte ($01) stays in the port $99 latch and pairs with the caller's next port $99 byte (the probe's R#7 := $5A became an address setting, $01A01, R#7 not written); with
ACPAGE above 3 in SCREEN 5 / 6 or above 1 in SCREEN 7 / 8 they mask ACPAGE where the references add its high bits
(ACPAGE 4 + $C123: $0C123 against $0C223; SCREEN 8 ACPAGE 2 + $1234: $01234 against $01334; xva3); and with SCRMOD 10
(VA-14, the MSX2+ build) they take SCREEN 8's 64 KB page ($11234 for ACPAGE 1 + $1234) where the FS-A1WSX takes
SCREEN 5's 32 KB page ($09234; [xva14.asm](../../../probes/bios/spec/xva14.asm), [scratchpad/AE_xva14_msx2.out](../../../scratchpad/AE_xva14_msx2.out)). VA-16 (an interrupt during the
call): the same as the references.

## On the turbo R

Measured 2026-11-23 (D-TRSPEC) on the FS-A1GT / FS-A1ST: xva14 gives the same bytes as on the FS-A1WSX, on both models, and xva3 differs only in case 0's port-log slots that the call does not use (power-on RAM). xva16 is timing: the FS-A1GT's calibration counts one more loop per frame than the A1ST and the A1WSX ($2A, not $29), so each step's interrupt lands one NOP elsewhere and the marks, logged writes and SP depths move -- the same SP depths ($1C-$26) as on the MSX2s, no new outcome [M] ([AE_trall/xva14.out](../../../scratchpad/AE_trall/xva14.out), [AE_trall/xva3.out](../../../scratchpad/AE_trall/xva3.out), [AE_trall/xva16.out](../../../scratchpad/AE_trall/xva16.out); overview: [turbor/remeasured.md](../../turbor/remeasured.md)).

## Open (not measured)

Every sentence above is [P] or [A]. The matrix: the [shared VA cases](README.md#the-shared-vram-address-matrix)
VA-1 to VA-16 and VC-1 / VC-2, each followed by two reads of port $98 (the first names the rule
through S-MARK, the second where the counter went), with the shared read-back. VC-1 / VC-2 and the 128 KB VRAM read-back have run (xva3; [README](README.md#the-shared-vram-address-matrix)
"Measured"); S-MARK's markers have not -- the address is read from the VDP instead. Plus:

| case | inputs | state | separates | F900 | 8250 | WSX |
|---|---|---|---|---|---|---|
| SR-1 | HL $1234; A $C7 / $00 / $FF, F $00 / $FF (xva3 cases 0-2) | S-BASE, S-REGS, interrupts off | AF on return: kept, a constant, from H, or from the bank; BC / DE / HL / IX / IY / alternates kept | A $12 F $14 (from the address byte); the rest kept [M] | A $12 F $14; the rest kept [M] | A $12 F $14; the rest kept [M] |
| SR-2 | HL $1234 | S-BASE, interrupts on, then off | the interrupt state on return: kept / always on / always off | on, entered on (VA-16) or off (xva3) [M] | on, either way [M] | on, either way [M] |
| SR-3 | HL $1234 | S-BASE (R#15-R#17 and $FFF0 as booted, not preset) | the call writes no VDP register but R#14 and the address (the port $99 log), and no save cell but perhaps $FFED | four port $99 writes only, no $98 / $9A / $9B write, no save cell changed [M] | the same [M] | the same [M] |
| SR-4 | HL $1234 | S-BASE, stack markers | the stack depth it uses (README methods) | ? | ? | ? |
| SR-5 | HL $1234 | S-BASE | the time it takes (README methods) | ? | ? | ? |

## Related pages

[region page](README.md), [NSETWR](NSETWR.md), [NRDVRM](NRDVRM.md), [NWRVRM](NWRVRM.md),
[BIGFIL](BIGFIL.md); MSX1 [SETRD](../../bios/SETRD.md).

## Tests that cover it

None yet.
