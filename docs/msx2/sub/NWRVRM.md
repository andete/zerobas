<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `NWRVRM` (sub-ROM $0109) — write a VRAM byte, 64 KB address

> **Spec:** DRAFT 1 (2026-11-23): the VRAM address MEASURED on the HB-F900, NMS 8250 and FS-A1WSX ([xva2.asm](../../../probes/bios/spec/xva2.asm), [scratchpad/AE_xva2_msx2.out](../../../scratchpad/AE_xva2_msx2.out), decoded by `scratchpad/xva_decode.py`).

## Summary

`NWRVRM` writes A to the VRAM byte at HL, where HL spans the whole 0-$FFFF range rather than the
MSX1 call's 16 KB. The handbook lists this sub-ROM entry under the name WRTVRM; the main ROM's
full-address version at $0177 is NWRVRM [P A1 main NWRVRM, WRTVRM], the name this page uses to
keep it apart from the MSX1 [WRTVRM](../../bios/WRTVRM.md). Whether the two behave alike is [A].

## The specification

Shared facts — VRAM, MODE, the pages: [vdp-and-palette.md](../concepts/vdp-and-palette.md).

### Interface

- **In:** HL, the VRAM address (0 to $FFFF); A, the byte [P A1 WRTVRM (sub)].
- **Out:** none. Only AF changes [P A1 WRTVRM (sub)].

### Behaviour

- VRAM holds 128 KB [P 4§1.2]; which 64 KB HL addresses — always the first, or the half ACPAGE /
  R#14's bit A16 selects — is [A].
- Whether MODE's mask bit (addresses ANDed with $3FFF in SCREEN 0-3 [P A4 MODE]) applies here is [A].
- R#14's value after the call, the VDP's address counter, and the interrupt state are [A].

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

Recording as in [vdp-and-palette.md](../concepts/vdp-and-palette.md#how-every-case-is-recorded),
with VRAM recorded whole (both 64 KB halves preset with different address-dependent garbage).
**Every case runs twice: through the sub-ROM entry $0109 and through the main ROM's NWRVRM $0177**,
so "the two behave alike" becomes a measured row.

| case | inputs | state | what it separates |
|---|---|---|---|
| NW-01 | HL $0123, $4123, $C123 | SCRMOD 5, MODE 128 KB | 16-bit addressing vs the MSX1 AND $3FFF |
| NW-02 | HL $4123 | SCRMOD 1, MODE mask bit set / clear | MODE's mask applies vs not |
| NW-03 | HL $1234 | SCREEN 5, ACPAGE 1, DPPAGE 2 | lands at $1234 (no page) vs $9234 (+ page x $8000) vs $11234 (A16 when ACPAGE ≠ 0) |
| NW-04 | HL $1234 | R#14 preset 6 (A16-A14 = 110) by hand, ACPAGE 0; then also ACPAGE 1 | R#14 rewritten vs kept; ACPAGE crossed with R#14 |
| NW-05 | HL $FFFF, then a write to port $98 | — | the call's byte at $0FFFF vs $1FFFF; where the next port write lands: the counter at $10000 (carry into A16) vs $00000 |
| NW-06 | A $00, $FF, $5A | entry F $00 / $FF; all registers incl. AF' BC' DE' HL' IX IY garbage | F's rule; registers kept |
| NW-07 | — | interrupts on / off; the control call | the call's interrupt state vs the path's (IFF1 at each port write, from the log) |
| NW-08 | HL $2345, then a port $98 write | — | the address counter (snapshot) left at HL + 1; the follow-up write lands there |
| NW-09 | HL $4123 | MODE's size bits set to 16 KB / 64 KB by hand (the cell only; VRAM stays 128 KB) | the size bits steer the call vs not |
| NW-10 | HL $1234 | a VDP command running (CE = 1) | written during the command vs waits |

## Related pages

[NRDVRM](NRDVRM.md); the MSX1 calls [WRTVRM](../../bios/WRTVRM.md), [RDVRM](../../bios/RDVRM.md).

## Tests that cover it

None yet.
