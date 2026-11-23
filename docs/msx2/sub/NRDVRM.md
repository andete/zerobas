<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `NRDVRM` (sub-ROM $010D) — read a VRAM byte, 64 KB address

> **Spec:** DRAFT 1 (2026-11-23): the VRAM address and the data MEASURED on the HB-F900, NMS 8250 and FS-A1WSX ([xva2.asm](../../../probes/bios/spec/xva2.asm), [scratchpad/AE_xva2_msx2.out](../../../scratchpad/AE_xva2_msx2.out), decoded by [xva_decode.py](../../../scratchpad/xva_decode.py) (the address matrix) and [xva2_decode.py](../../../scratchpad/xva2_decode.py) (the data cases)).
>
> Goldfish pass 1 (test writer) 2026-11-23: 7 findings, 5 measured, 2 moved to open (the other two corrected in wording: the baseline call, the subject's Differences).

## Summary

`NRDVRM` returns in A the VRAM byte at HL, HL spanning 0-$FFFF. The handbook lists this entry
under the name RDVRM; this page uses NRDVRM, the name of the main ROM's full-address version at
$0174 [P A1 main NRDVRM, RDVRM], to keep it apart from the MSX1 [RDVRM](../../bios/RDVRM.md).
Their register lists differ (sub-ROM: AF; main ROM: F, with A the result) [P A1 RDVRM (sub),
NRDVRM]. They read the same byte with ACPAGE 0 and in SCREEN 5, but not in SCREEN 0-4 / 6 with ACPAGE
not 0 (below).

## The specification

Shared facts: [vdp-and-palette.md](../concepts/vdp-and-palette.md).

### Interface

- **In:** HL, the VRAM address (0 to $FFFF) [P A1 RDVRM (sub)].
- **Out:** A, the byte read. Only AF changes [P A1 RDVRM (sub)].

### Behaviour

- Whether MODE's $3FFF mask applies, and the interrupt state, are [A] — the same questions as
  [NWRVRM](NWRVRM.md). The address, R#14 and the counter afterwards are measured below.

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
- **The data.** With all 128 KB of VRAM holding an address-dependent pattern, A = the byte at that address [M VD 0-4:
  SCREEN 5 ACPAGE 0 / 1, SCREEN 1 ACPAGE 1, SCREEN 0 ACPAGE 1 ($D123 -> the byte of $0E123), SCREEN 8 ACPAGE 1], and no
  VRAM byte changes [M VD 0-4].
- **The VDP's address counter is left at the address + 2** ($1234 -> $1236): the read setting pre-fetches one byte,
  the call's read of port $98 takes it and fetches the next [M VA-1 - X 35, every case]. A port $98 access after the
  call therefore meets the address + 2 [A: the follow-up access itself was not run].
- **Registers.** A = the byte; F varies by case ($10, $14, $30, $34, $3C, $54; not decoded into a rule) [M]. BC, DE, HL,
  IY and the alternate set are kept [M VD 0-4: BC $5AA5, DE $A55A, IY $2468, BC' / DE' / HL' / AF' preset, all
  unchanged]; IX was the entry (EXTROM), so its keeping is not measured.

## Differences from the reference

C-BIOS's MSX2 / MSX2+ builds (the subject), in **SCREEN 0-4 with ACPAGE not 0** (all fourteen such cases), address
HL AND $3FFF in bank 0 (R#14 := 0) and set it with the WRITE bit (address byte $40 OR A13-A8, e.g. $41) in **five**
port $99 writes, leaving the counter at the address + 1 [VA-11 - 11h, X 25-28, 33, 34]. Where HL AND $3FFF happens
to be the reference's address — $C123 with ACPAGE 1 in SCREEN 1-4 ($00123) — the reads and writes agree by that
coincidence [VA-11, 11g, 11h, X 25; VD 2]; elsewhere they miss: SCREEN 0 ACPAGE 1 $D123 reads and writes $01123
instead of $0E123 [VD 3]. Every other measured case agrees with the reference, data included [VD 0, 1, 4]
([scratchpad/AE_xva2_msx2.out](../../../scratchpad/AE_xva2_msx2.out), `--side ours`).

## Open (not measured)

Recording as in [vdp-and-palette.md](../concepts/vdp-and-palette.md#how-every-case-is-recorded).
VRAM is preset by hand through the ports (never by NWRVRM, [spec-method §3a](../../spec-method.md)),
each 64 KB half and each 16 KB block with different address-dependent values. **Every case runs
through $010D and through the main ROM's NRDVRM $0174.** (Measured above: NR-01 in VA-1 / VA-2, NR-03 in X 32 / VD 1 —
$1234 in SCREEN 5 ACPAGE 1 reads the byte of $09234 —, NR-04 in VA-1 / VA-7, the data path in VD 0-4.)

| case | inputs | state | what it separates |
|---|---|---|---|
| NR-02 | HL $4123 | SCRMOD 1, MODE mask set / clear | MODE's mask applies vs not |
| NR-05 | HL $FFFF | SCREEN 7 / 8 ACPAGE 1 (SCREEN 5 ACPAGE 1 $FFFE measured: $07FFE, X 35) | A = the byte at $1FFFF; the counter afterwards $00000 vs $10000 vs $20000 |
| NR-06 | HL $2345, then a port $98 read and a port $98 write | — | where the next access lands: the counter is measured at HL + 2 after the call; whether a following access starts there |
| NR-07 | HL $4123 | MODE's size bits 16 KB / 64 KB by hand | the size bits steer the call vs not |
| NR-08 | — | entry F $00 / $FF; IX through a path that does not use it (SUBROM / CALSLT) | F's rule (the measured values are not decoded into one); IX kept (BC, DE, HL, IY, the alternates measured kept, VD 0-4) |
| NR-09 | — | interrupts on / off; the control call | the call's interrupt state vs the path's |
| NR-10 | HL $1234 | a VDP command running (CE = 1) | read during the command vs waits |
| NR-11 | HL $C123, $E123, $F123 | SCREEN 0 width 80, ACPAGE 2 and 3; SCREEN 6 ACPAGE 2 / 3; SCREEN 7 ACPAGE 3 | the page size at width 80 ($2000 from one case, X 26) and the rule's other untested corners |
| NR-12 | the matrix's address cases | through the main ROM's $0174 (the matrix ran NSETRD as its baseline) | $0174 = NSETRD's rule in every case, not only VD 0-4 |

## Related pages

[NWRVRM](NWRVRM.md); the MSX1 calls [RDVRM](../../bios/RDVRM.md), [WRTVRM](../../bios/WRTVRM.md).

## Tests that cover it

None yet.
