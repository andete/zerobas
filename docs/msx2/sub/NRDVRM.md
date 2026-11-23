<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `NRDVRM` (sub-ROM $010D) — read a VRAM byte, 64 KB address

> **Spec:** DRAFT 0 (2026-11-23), from the published interface only; nothing measured yet. References to measure: HB-F900, NMS 8250, FS-A1WSX.

## Summary

`NRDVRM` returns in A the VRAM byte at HL, HL spanning 0-$FFFF. The handbook lists this entry
under the name RDVRM; this page uses NRDVRM, the name of the main ROM's full-address version at
$0174 [P A1 main NRDVRM, RDVRM], to keep it apart from the MSX1 [RDVRM](../../bios/RDVRM.md).
Their register lists differ (sub-ROM: AF; main ROM: F, with A the result) [P A1 RDVRM (sub),
NRDVRM]; whether they behave alike is [A].

## The specification

Shared facts: [vdp-and-palette.md](../concepts/vdp-and-palette.md).

### Interface

- **In:** HL, the VRAM address (0 to $FFFF) [P A1 RDVRM (sub)].
- **Out:** A, the byte read. Only AF changes [P A1 RDVRM (sub)].

### Behaviour

- Which 64 KB of the 128 KB HL addresses, whether MODE's $3FFF mask applies, R#14 and the address
  counter afterwards, and the interrupt state are [A] — the same questions as [NWRVRM](NWRVRM.md).

## Differences from the reference

Not measured yet.

## Open (not measured)

Recording as in [vdp-and-palette.md](../concepts/vdp-and-palette.md#how-every-case-is-recorded).
VRAM is preset by hand through the ports (never by NWRVRM, [spec-method §3a](../../spec-method.md)),
each 64 KB half and each 16 KB block with different address-dependent values. **Every case runs
through $010D and through the main ROM's NRDVRM $0174.**

| case | inputs | state | what it separates |
|---|---|---|---|
| NR-01 | HL $0123, $4123, $C123 | SCRMOD 5 | 16-bit addressing vs AND $3FFF |
| NR-02 | HL $4123 | SCRMOD 1, MODE mask set / clear | MODE's mask applies vs not |
| NR-03 | HL $1234 | SCREEN 5, ACPAGE 1, DPPAGE 2 | the byte of $1234 vs $9234 vs $11234 |
| NR-04 | HL $1234 | R#14 preset 6; ACPAGE 0, then 1 | R#14 rewritten vs kept; crossed with ACPAGE |
| NR-05 | HL $FFFF | — | A = the byte at $0FFFF vs $1FFFF; the counter afterwards (snapshot) $10000 vs $00000 |
| NR-06 | HL $2345, then a port $98 write | — | the counter left at HL + 1 (read-ahead taken), seen by where the write lands |
| NR-07 | HL $4123 | MODE's size bits 16 KB / 64 KB by hand | the size bits steer the call vs not |
| NR-08 | — | entry F $00 / $FF; all registers incl. AF' BC' DE' HL' IX IY garbage | F's rule; registers kept |
| NR-09 | — | interrupts on / off; the control call | the call's interrupt state vs the path's |
| NR-10 | HL $1234 | a VDP command running (CE = 1) | read during the command vs waits |

## Related pages

[NWRVRM](NWRVRM.md); the MSX1 calls [RDVRM](../../bios/RDVRM.md), [WRTVRM](../../bios/WRTVRM.md).

## Tests that cover it

None yet.
