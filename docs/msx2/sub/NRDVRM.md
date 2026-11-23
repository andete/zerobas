<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `NRDVRM` (sub-ROM $010D) — read a VRAM byte, 64 KB address

> **Spec:** DRAFT 1 (2026-11-23): the VRAM address MEASURED on the HB-F900, NMS 8250 and FS-A1WSX ([xva2.asm](../../../probes/bios/spec/xva2.asm), [scratchpad/AE_xva2_msx2.out](../../../scratchpad/AE_xva2_msx2.out), decoded by `scratchpad/xva_decode.py`).

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

**Measured** [M] over the [main ROM's VRAM address matrix](../main/README.md#the-shared-vram-address-matrix)
(the same on all three references): R#14 := the bank and the 14-bit address, four port $99 writes, $FFED not
written -- and the address is the main ROM's in every case **except SCREEN 0-4 with ACPAGE not 0**. There the main
ROM uses ACPAGE x $100 + E; this sub-ROM entry PAGES WITHIN 64 KB: **(HL + ACPAGE x page size) AND $FFFF**, the
page size $4000 in SCREEN 1, 2 and 4 (ACPAGE 1: $C123 -> $00123, $1234 -> $05234, $0000 -> $04000; ACPAGE 2 / 3:
$C123 -> $04123 / $08123) and $1000 in SCREEN 0 at width 40 (ACPAGE 1: $C123 -> $0D123). In SCREEN 5-8 it is the
main ROM's 17-bit rule (ACPAGE 3, $C123 -> $14123; SCREEN 7 / 8: ACPAGE x $10000 + HL).

## Differences from the reference

C-BIOS's MSX2 / MSX2+ builds (the subject) give every measured address but the SCREEN 0-4, ACPAGE-not-0 ones
([scratchpad/AE_xva2_msx2.out](../../../scratchpad/AE_xva2_msx2.out)).

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
