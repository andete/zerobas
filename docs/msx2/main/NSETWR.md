<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `NSETWR` ($0171) — set the VDP to write VRAM at an address (128 KB)

> **Spec:** DRAFT 0 (2026-11-23), from the published interface only; nothing measured yet. References to measure: HB-F900, NMS 8250, FS-A1WSX.

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

## Differences from the reference

Not measured yet.

## Open (not measured)

The [shared VA cases](README.md#the-shared-vram-address-matrix) VA-1 to VA-16 and VC-1 / VC-2, each
followed by two writes to port $98 ($C7, $C8, which no marker equals) and the shared read-back: the
marked addresses show which rule's byte became $C7 (and that none other did), the block sums that
nothing else changed. Plus:

| case | inputs | state | separates | F900 | 8250 | WSX |
|---|---|---|---|---|---|---|
| SW-1 | HL $C123, NSETRD then NSETWR on the same state | VA-3, then VA-4 | the two calls follow the same bank rule (same HL, both repaired states) | ? | ? | ? |
| SW-2 | HL $1234, no port write after | S-BASE | the call itself writes no VRAM byte (block sums and markers unchanged) | ? | ? | ? |
| SW-3 | HL $1234; A $A7 / $00, F $00 / $FF | S-BASE, S-REGS, interrupts off, then on | AF on return; other registers kept; the interrupt state | ? | ? | ? |
| SW-4 | HL $1234 | as NSETRD's SR-3 | no other VDP register or save cell written | ? | ? | ? |
| SW-5 | HL $1234 | S-BASE | stack depth and time (README methods) | ? | ? | ? |

Also open: the display off (write timing).

## Related pages

[region page](README.md), [NSETRD](NSETRD.md), [NWRVRM](NWRVRM.md), [BIGFIL](BIGFIL.md); MSX1
[SETWRT](../../bios/SETWRT.md).

## Tests that cover it

None yet.
