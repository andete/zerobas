<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `NRDVRM` ($0174) — read a VRAM byte (128 KB)

> **Spec:** DRAFT 1 (2026-11-23): the shared VRAM address matrix MEASURED on the HB-F900, NMS 8250 and FS-A1WSX
> (identical on all three) -- the address rule, the R#14 / $FFED writes and the SCREEN 0-4 ACPAGE quirk are in
> [README.md](README.md#the-shared-vram-address-matrix) "Measured" (all sixteen VA cases, an interrupt during the call
> included); this page's own cases beyond it are not measured yet, but for the interrupt state entered with interrupts on.

## Summary

`NRDVRM` is the MSX2's [RDVRM](../../bios/RDVRM.md) for 128 KB of VRAM: it returns in A the VRAM byte
at the address in HL. Which 64 KB half, and whether the screen mode matters, is not published.

## The specification

**Interface.**
- In: HL = the VRAM address [P A1]. Out: A = the byte read [P A1]. Changes: F [P A1] (A is the
  output).
- A16, R#14 and its save cell, and SCREEN 0-4: one of the rival rules of the
  [shared VRAM address matrix](README.md#the-shared-vram-address-matrix) [A].
- BC, DE, HL, IX, IY kept [A]. VRAM not changed [A]. F's value on return, the interrupt state, and
  where the VDP's address counter is left [A].
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

The [shared VA cases](README.md#the-shared-vram-address-matrix) VA-1 to VA-16 and VC-1 / VC-2: A
names the rule through S-MARK; then one read of port $98 (where the counter was left) and the shared
read-back, whose sixteen 8 KB-block sums and markers show VRAM unchanged. Plus:

| case | inputs | state | separates | F900 | 8250 | WSX |
|---|---|---|---|---|---|---|
| RV-1 | HL $0012, $3312, $4112, $8012; F $00 / $FF; A $A7 / $00 | S-BASE, S-REGS | F's source. H AND $3F: $00 (Z), $33 (even parity), $01 (odd), $00 again for $80 — so "flags of H AND $3F" (RDVRM's MSX1 rule) gives S clear for $8012, "flags of H" gives S set; "flags of the byte read" follows the markers instead | ? | ? | ? |
| RV-2 | HL $1234 | S-BASE, interrupts on, then off | the interrupt state: kept / always on / off | entered on: on [M] (VA-16); entered off ? | entered on: on [M] (VA-16); entered off ? | entered on: on [M] (VA-16); entered off ? |
| RV-3 | HL $1234 | as NSETRD's SR-3 | no other VDP register or save cell written | ? | ? | ? |
| RV-4 | HL $1234 | S-BASE | stack depth and time (README methods) | ? | ? | ? |

Also open: the display off.

## Related pages

[region page](README.md), [NSETRD](NSETRD.md), [NWRVRM](NWRVRM.md); MSX1 [RDVRM](../../bios/RDVRM.md).

## Tests that cover it

None yet.
