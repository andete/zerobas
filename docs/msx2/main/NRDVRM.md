<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `NRDVRM` ($0174) — read a VRAM byte (128 KB)

> **Spec:** DRAFT 0 (2026-11-23), from the published interface only; nothing measured yet. References to measure: HB-F900, NMS 8250, FS-A1WSX.

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

## Differences from the reference

Not measured yet.

## Open (not measured)

The [shared VA cases](README.md#the-shared-vram-address-matrix) VA-1 to VA-16 and VC-1 / VC-2: A
names the rule through S-MARK; then one read of port $98 (where the counter was left) and the shared
read-back, whose sixteen 8 KB-block sums and markers show VRAM unchanged. Plus:

| case | inputs | state | separates | F900 | 8250 | WSX |
|---|---|---|---|---|---|---|
| RV-1 | HL $0012, $3312, $4112, $8012; F $00 / $FF; A $A7 / $00 | S-BASE, S-REGS | F's source. H AND $3F: $00 (Z), $33 (even parity), $01 (odd), $00 again for $80 — so "flags of H AND $3F" (RDVRM's MSX1 rule) gives S clear for $8012, "flags of H" gives S set; "flags of the byte read" follows the markers instead | ? | ? | ? |
| RV-2 | HL $1234 | S-BASE, interrupts on, then off | the interrupt state: kept / always on / off | ? | ? | ? |
| RV-3 | HL $1234 | as NSETRD's SR-3 | no other VDP register or save cell written | ? | ? | ? |
| RV-4 | HL $1234 | S-BASE | stack depth and time (README methods) | ? | ? | ? |

Also open: the display off.

## Related pages

[region page](README.md), [NSETRD](NSETRD.md), [NWRVRM](NWRVRM.md); MSX1 [RDVRM](../../bios/RDVRM.md).

## Tests that cover it

None yet.
