<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `NWRVRM` ($0177) — write a VRAM byte (128 KB)

> **Spec:** DRAFT 1 (2026-11-23): the shared VRAM address matrix MEASURED on the HB-F900, NMS 8250 and FS-A1WSX
> (identical on all three) -- the address rule, the R#14 / $FFED writes and the SCREEN 0-4 ACPAGE quirk are in
> [README.md](README.md#the-shared-vram-address-matrix) "Measured"; this page's own cases beyond it are not measured yet.

## Summary

`NWRVRM` is the MSX2's [WRTVRM](../../bios/WRTVRM.md) for 128 KB of VRAM: it stores A at the VRAM
address in HL. Which 64 KB half, and whether the screen mode matters, is not published.

## The specification

**Interface.**
- In: HL = the VRAM address, A = the byte [P A1]. Out: none [P A1]. Changes: AF [P A1].
- A16, R#14 and its save cell, and SCREEN 0-4: one of the rival rules of the
  [shared VRAM address matrix](README.md#the-shared-vram-address-matrix) [A].
- Exactly one VRAM byte changes [A]. BC, DE, HL, IX, IY kept [A]. AF's value on return, the
  interrupt state, and where the address counter is left [A].

## Differences from the reference

Not measured yet.

## Open (not measured)

The [shared VA cases](README.md#the-shared-vram-address-matrix) VA-1 to VA-16 and VC-1 / VC-2 with A
$C7 (no marker equals it): the marked addresses show which rule's byte became $C7 and that no other
did; the block sums, that nothing else changed. Then one write to port $98 ($C9) shows where the
counter was left. Plus:

| case | inputs | state | separates | F900 | 8250 | WSX |
|---|---|---|---|---|---|---|
| WV-1 | HL $1234; A $00 and $FF (no marker equals either); F $00 / $FF | S-BASE, S-REGS | A kept or not; F on return; other registers kept | ? | ? | ? |
| WV-2 | HL $1234, A $C7 | S-BASE, interrupts on, then off | the interrupt state | ? | ? | ? |
| WV-3 | HL $1234, A $C7 | as NSETRD's SR-3 | no other VDP register or save cell written | ? | ? | ? |
| WV-4 | HL $1234, A $C7 | S-BASE | stack depth and time (README methods) | ? | ? | ? |

Also open: the display off (write timing).

## Related pages

[region page](README.md), [NSETWR](NSETWR.md), [NRDVRM](NRDVRM.md), [BIGFIL](BIGFIL.md); MSX1
[WRTVRM](../../bios/WRTVRM.md).

## Tests that cover it

None yet.
