<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `NSETRD` ($016E) — set the VDP to read VRAM at an address (128 KB)

> **Spec:** DRAFT 1 (2026-11-23): the shared VRAM address matrix MEASURED on the HB-F900, NMS 8250 and FS-A1WSX
> (identical on all three) -- the address rule, the R#14 / $FFED writes and the SCREEN 0-4 ACPAGE quirk are in
> [README.md](README.md#the-shared-vram-address-matrix) "Measured" (all sixteen VA cases, an interrupt during the call
> included); this page's own cases beyond it are not measured yet, but for the interrupt state entered with interrupts on.

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
- BC, DE, HL, IX, IY kept [A] (only AF is listed as changed). The interrupt state on return [A].
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

Every sentence above is [P] or [A]. The matrix: the [shared VA cases](README.md#the-shared-vram-address-matrix)
VA-1 to VA-16 and VC-1 / VC-2, each followed by two reads of port $98 (the first names the rule
through S-MARK, the second where the counter went), with the shared read-back. Plus:

| case | inputs | state | separates | F900 | 8250 | WSX |
|---|---|---|---|---|---|---|
| SR-1 | HL $1234; A $A7 / $00, F $00 / $FF | S-BASE, S-REGS, interrupts off | AF on return: kept, a constant, from H, or from the bank; BC / DE / HL / IX / IY / alternates kept | ? | ? | ? |
| SR-2 | HL $1234 | S-BASE, interrupts on | the interrupt state on return: kept / always on / always off (with SR-1's off) | on [M] (VA-16) | on [M] (VA-16) | on [M] (VA-16) |
| SR-3 | HL $1234 | S-BASE; R#15 := 2, R#16 := 5, R#17 := $8F, $FFF0 := $5A by hand | the call writes no VDP register but R#14 and the address (the port $99 log), and no save cell but perhaps $FFED | ? | ? | ? |
| SR-4 | HL $1234 | S-BASE, stack markers | the stack depth it uses (README methods) | ? | ? | ? |
| SR-5 | HL $1234 | S-BASE | the time it takes (README methods) | ? | ? | ? |

## Related pages

[region page](README.md), [NSETWR](NSETWR.md), [NRDVRM](NRDVRM.md), [NWRVRM](NWRVRM.md),
[BIGFIL](BIGFIL.md); MSX1 [SETRD](../../bios/SETRD.md).

## Tests that cover it

None yet.
