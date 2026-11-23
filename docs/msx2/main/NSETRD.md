<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `NSETRD` ($016E) — set the VDP to read VRAM at an address (128 KB)

> **Spec:** DRAFT 0 (2026-11-23), from the published interface only; nothing measured yet. References to measure: HB-F900, NMS 8250, FS-A1WSX.

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

## Differences from the reference

Not measured yet.

## Open (not measured)

Every sentence above is [P] or [A]. The matrix: the [shared VA cases](README.md#the-shared-vram-address-matrix)
VA-1 to VA-16 and VC-1 / VC-2, each followed by two reads of port $98 (the first names the rule
through S-MARK, the second where the counter went), with the shared read-back. Plus:

| case | inputs | state | separates | F900 | 8250 | WSX |
|---|---|---|---|---|---|---|
| SR-1 | HL $1234; A $A7 / $00, F $00 / $FF | S-BASE, S-REGS, interrupts off | AF on return: kept, a constant, from H, or from the bank; BC / DE / HL / IX / IY / alternates kept | ? | ? | ? |
| SR-2 | HL $1234 | S-BASE, interrupts on | the interrupt state on return: kept / always on / always off (with SR-1's off) | ? | ? | ? |
| SR-3 | HL $1234 | S-BASE; R#15 := 2, R#16 := 5, R#17 := $8F, $FFF0 := $5A by hand | the call writes no VDP register but R#14 and the address (the port $99 log), and no save cell but perhaps $FFED | ? | ? | ? |
| SR-4 | HL $1234 | S-BASE, stack markers | the stack depth it uses (README methods) | ? | ? | ? |
| SR-5 | HL $1234 | S-BASE | the time it takes (README methods) | ? | ? | ? |

## Related pages

[region page](README.md), [NSETWR](NSETWR.md), [NRDVRM](NRDVRM.md), [NWRVRM](NWRVRM.md),
[BIGFIL](BIGFIL.md); MSX1 [SETRD](../../bios/SETRD.md).

## Tests that cover it

None yet.
