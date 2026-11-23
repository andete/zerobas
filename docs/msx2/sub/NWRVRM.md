<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `NWRVRM` (sub-ROM $0109) — write a VRAM byte, 64 KB address

> **Spec:** DRAFT 1 (2026-11-23): the VRAM address and the data MEASURED on the HB-F900, NMS 8250 and FS-A1WSX ([xva2.asm](../../../probes/bios/spec/xva2.asm), [scratchpad/AE_xva2_msx2.out](../../../scratchpad/AE_xva2_msx2.out), decoded by [xva_decode.py](../../../scratchpad/xva_decode.py) (the address matrix) and [xva2_decode.py](../../../scratchpad/xva2_decode.py) (the data cases)).
>
> Goldfish pass 1 (test writer) 2026-11-23: 6 findings, 4 measured, 2 moved to open (the other two corrected in wording: the baseline call, the subject's Differences).

## Summary

`NWRVRM` writes A to the VRAM byte at HL, where HL spans the whole 0-$FFFF range rather than the
MSX1 call's 16 KB. The handbook lists this sub-ROM entry under the name WRTVRM; the main ROM's
full-address version at $0177 is NWRVRM [P A1 main NWRVRM, WRTVRM], the name this page uses to
keep it apart from the MSX1 [WRTVRM](../../bios/WRTVRM.md). The two write the same byte with ACPAGE 0 and in
SCREEN 5, but not in SCREEN 0-4 / 6 with ACPAGE not 0 (below).

## The specification

Shared facts — VRAM, MODE, the pages: [vdp-and-palette.md](../concepts/vdp-and-palette.md).

### Interface

- **In:** HL, the VRAM address (0 to $FFFF); A, the byte [P A1 WRTVRM (sub)].
- **Out:** none. Only AF changes [P A1 WRTVRM (sub)].

### Behaviour

- VRAM holds 128 KB [P 4§1.2]; which address HL names is measured below (ACPAGE's page, not R#14).
- Whether MODE's mask bit (addresses ANDed with $3FFF in SCREEN 0-3 [P A4 MODE]) applies here is [A].
- The interrupt state after the call is [A]; R#14 and the address counter are measured below.

**Measured** [M] (the same on all three references; through EXTROM). `[VA-n]` = the
[main ROM's VRAM address matrix](../main/README.md#the-shared-vram-address-matrix) cases as xva2 runs them, `[X n]` =
xva2's cases 25-35 (goldfish pass 1), `[VD n]` = its data cases. The in-run baseline of the matrix is the main ROM's
**NSETRD / NSETWR ($016E / $0171)**; the main ROM's NRDVRM $0174 / NWRVRM $0177 themselves ran only in VD 0-4,
where they address the same bytes as NSETRD / NSETWR's rule.

- **The address.** R#14 := A16-A14 and the 14-bit address, four port $99 writes, $FFED not written [M VA-1 - X 35].
  With P = ACPAGE's page size — $1000 in SCREEN 0 at width 40, $4000 in SCREEN 1-4, $8000 in SCREEN 5 / 6,
  $10000 in SCREEN 7 / 8 — the address is **(ACPAGE x P AND $10000) OR ((ACPAGE x P + HL) AND $FFFF)**, ACPAGE x P
  taken mod $20000: the page base's own A16 is kept, and the sum with HL wraps within its 64 KB. Every measured case
  fits it:
  - SCREEN 0 / 40: ACPAGE 1 $C123 -> $0D123, $D123 -> $0E123, $F123 -> $00123; ACPAGE 2 / 3 $C123 -> $0E123 /
    $0F123 [M VA-11f, X 27, 28, 33, 34]. $D123 and $F123 separate "+ ACPAGE x $1000" from "OR $1000": OR would give
    $0D123 and $0F123.
  - SCREEN 0 / 80: ACPAGE 1 $C123 -> $0E123 [M X 26] — P = $2000 there, from this one case [A beyond it].
  - SCREEN 1-4: ACPAGE 1 $C123 -> $00123 in SCREEN 1, 2, 3 and 4, $1234 -> $05234, $0000 -> $04000; SCREEN 1
    ACPAGE 2 / 3 $C123 -> $04123 / $08123 [M VA-11 - 11h, X 25].
  - SCREEN 5 / 6: ACPAGE 1 $1234 -> $09234, $FFFE -> $07FFE (no carry into A16), SCREEN 6 ACPAGE 1 $C123 ->
    $04123; ACPAGE 2 $C123 -> $1C123, ACPAGE 3 -> $14123 [M X 29, 32, 35, VA-3 - 5].
  - SCREEN 7 / 8: ACPAGE 1 $1234 -> $11234; SCREEN 7 ACPAGE 2 -> $01234, SCREEN 8 ACPAGE 3 -> $11234 [M VA-7, X 30,
    31].
  - ACPAGE 0: HL [M VA-1, 2, 8-10].
- **Against the main ROM.** NSETRD / NSETWR give the same address with ACPAGE 0 and in SCREEN 5 [M VA-1 - 6, X 32,
  35], and SCREEN 7 / 8 ACPAGE 1 [M VA-7]. They differ in SCREEN 0-4 with ACPAGE not 0 (the main ROM: ACPAGE x
  $100 + E, e.g. $0015A), SCREEN 6 ACPAGE 1 ($0015A), SCREEN 7 ACPAGE 2 ($01334) and SCREEN 8 ACPAGE 3 ($11334)
  [M VA-11 - 11h, X 25-31, 33, 34] — what those main-ROM readings mean is the main ROM's pages' business.
- **The data.** With all 128 KB of VRAM holding an address-dependent pattern, exactly ONE byte changes, at that address,
  to A [M VD 0-4: SCREEN 5 ACPAGE 0 / 1, SCREEN 1 ACPAGE 1, SCREEN 0 ACPAGE 1 ($D123 -> $0E123), SCREEN 8 ACPAGE 1].
- **The VDP's address counter is left at the address + 1** [M VA-1 - X 35, every case].
- **Registers.** A kept ($C7), F $02 [M VA-1 - X 35, VD 0-4]. BC, DE, HL, IY and the alternate set are kept [M VD 0-4];
  IX was the entry (EXTROM), so its keeping is not measured. (The main ROM's NWRVRM $0177 returns F $42 [M VD 0-4].)

## Differences from the reference

C-BIOS's MSX2 / MSX2+ builds (the subject), in **SCREEN 0-4 with ACPAGE not 0** (all fourteen such cases), address
HL AND $3FFF in bank 0 (R#14 := 0), in five port $99 writes [VA-11 - 11h, X 25-28, 33, 34]. Where HL AND $3FFF
happens to be the reference's address — $C123 with ACPAGE 1 in SCREEN 1-4 ($00123) — the write lands right by that
coincidence [VA-11, 11g, 11h, X 25; VD 2]; elsewhere it misses: SCREEN 0 ACPAGE 1 $D123 writes $01123 instead of
$0E123 [VD 3]. Every other measured case agrees with the reference, data included [VD 0, 1, 4]
([scratchpad/AE_xva2_msx2.out](../../../scratchpad/AE_xva2_msx2.out), `--side ours`).

## Open (not measured)

Recording as in [vdp-and-palette.md](../concepts/vdp-and-palette.md#how-every-case-is-recorded),
with VRAM recorded whole (both 64 KB halves preset with different address-dependent garbage).
**Every case runs twice: through the sub-ROM entry $0109 and through the main ROM's NWRVRM $0177**,
so "the two behave alike" becomes a measured row. (Measured above: NW-01 in VA-1 / VA-2, NW-03 in X 32 / VD 1 —
$1234 in SCREEN 5 ACPAGE 1 lands at $09234 —, NW-04 in VA-1 / VA-7, the data path in VD 0-4.)

| case | inputs | state | what it separates |
|---|---|---|---|
| NW-02 | HL $4123 | SCRMOD 1, MODE mask bit set / clear | MODE's mask applies vs not |
| NW-05 | HL $FFFF, then a write to port $98 | SCREEN 7 / 8 ACPAGE 1 (SCREEN 5 ACPAGE 1 $FFFE measured: $07FFE, X 35) | the call's byte at $1FFFF; where the next port write lands: the counter at $00000 vs $10000 vs $20000 |
| NW-06 | A $00, $FF, $5A | entry F $00 / $FF; IX through a path that does not use it | F's rule ($02 measured with A $C7 only); A kept for other values; IX kept (BC, DE, HL, IY, the alternates measured kept, VD 0-4) |
| NW-07 | — | interrupts on / off; the control call | the call's interrupt state vs the path's (IFF1 at each port write, from the log) |
| NW-08 | HL $2345, then a port $98 write | — | the counter is measured at HL + 1; whether the follow-up write lands there |
| NW-09 | HL $4123 | MODE's size bits set to 16 KB / 64 KB by hand (the cell only; VRAM stays 128 KB) | the size bits steer the call vs not |
| NW-10 | HL $1234 | a VDP command running (CE = 1) | written during the command vs waits |
| NW-11 | HL $C123, $E123, $F123 | SCREEN 0 width 80, ACPAGE 2 and 3; SCREEN 6 ACPAGE 2 / 3; SCREEN 7 ACPAGE 3 | the page size at width 80 ($2000 from one case, X 26) and the rule's other untested corners |
| NW-12 | the matrix's address cases | through the main ROM's $0177 (the matrix ran NSETWR as its baseline) | $0177 = NSETWR's rule in every case, not only VD 0-4 |

## Related pages

[NRDVRM](NRDVRM.md); the MSX1 calls [WRTVRM](../../bios/WRTVRM.md), [RDVRM](../../bios/RDVRM.md).

## Tests that cover it

None yet.
