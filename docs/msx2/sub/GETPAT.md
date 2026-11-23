<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `GETPAT` (sub-ROM $0105) — fetch a character's pattern

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the HB-F900, NMS 8250 and FS-A1WSX ([xspr2.asm](../../../probes/bios/spec/xspr2.asm), [scratchpad/AE_xspr2_msx2.out](../../../scratchpad/AE_xspr2_msx2.out), decoded by [xspr2_decode.py](../../../scratchpad/xspr2_decode.py)).
> Goldfish pass 1 (test writer) 2026-11-23: 6 findings, 3 measured, 1 moved to open ([xspr3.asm](../../../probes/bios/spec/xspr3.asm), [scratchpad/AE_xspr3_msx2.out](../../../scratchpad/AE_xspr3_msx2.out), decoded by [xspr3_decode.py](../../../scratchpad/xspr3_decode.py)).

## Summary

`GETPAT` copies the 8-byte pattern of character A into PATWRK ($FC40). The handbook does not say
where the pattern comes from; measured, it is the font that CGPNT ($F91F-$F921) names -- by default
the main ROM's -- and never VRAM.

## The specification

Shared facts: [vdp-and-palette.md](../concepts/vdp-and-palette.md).

### Interface

- **In:** A, the character code [P A1 GETPAT]; CGPNT ($F91F slot, $F920 address) [M, below].
- **Out:** PATWRK ($FC40, 8 bytes), the pattern [P A1 GETPAT, A4 PATWRK]. Any register may change
  [P A1 GETPAT].

### Behaviour

**Measured** [M] (the same on all three references, the Japanese machine included):

- PATWRK ($FC40-$FC47) := the 8 bytes at CGPNT's address + 8 x A, read from CGPNT's slot: with CGPNT pointed at
  a RAM copy in the page-3 RAM slot ($E000, holding $11 $22 ... $88 for $41), PATWRK = $11 $22 ... $88 and
  HL = $E210 ([AE_xspr3](../../../scratchpad/AE_xspr3_msx2.out)).
- VRAM is not read: with the VRAM pattern of $41 (CGPBAS + $208) := $C3 in SCREEN 1, PATWRK is still the ROM
  font's 'A' $20 50 88 88 F8 88 88 00 (AE_xspr3). SCREEN 5 gives the same bytes (AE_xspr3).
- Codes $00 and $FF give all-zero patterns (the ROM font's) ([AE_xspr2](../../../scratchpad/AE_xspr2_msx2.out)).
- Out: HL = CGPNT's address + 8 x (A + 1), one past the last byte read: $1DCF / $1BC7 / $23BF for A $41 / $00 /
  $FF with the default CGPNT, so the default font base is $1BBF (AE_xspr2); $E210 when moved (AE_xspr3).
  DE = $FC48 (one past PATWRK); BC = $0057; IX = $000C (CHANGED -- the other four sprite calls return IX = the
  entry address); IY kept (AE_xspr3).
- A and F are excused (no rule derived): with the default CGPNT A = $00, F = $08 / $08 / $30 for A $41 / $00 /
  $FF (AE_xspr2, AE_xspr3); with CGPNT moved A = $8B / $87 / $83 (NMS 8250 / HB-F900 / FS-A1WSX), F = $20
  (AE_xspr3). That the moved A is CGPNT's slot byte is [A] (the probe did not record the slot it wrote).

## Differences from the reference

C-BIOS's MSX2 / MSX2+ builds read the font CGPNT names (they copy $11 ... $88 when it is moved, and ignore VRAM),
with the same HL and DE; their default font is C-BIOS's own (ruled -- D-BIOSINT), so PATWRK differs for $41
([AE_xspr2](../../../scratchpad/AE_xspr2_msx2.out), [AE_xspr3](../../../scratchpad/AE_xspr3_msx2.out)). Besides:

- A $FF on the EU build returns A $55 and PATWRK $AA $55 $AA $55 ... (the references: A $00, all zero) -- C-BIOS's
  font has a pattern at $FF (AE_xspr2);
- F is $A0 in every case (the references $08 / $30 / $20); BC $00BF (default) / $0000 (moved), not $0057;
- IX is kept ($0105), where the references return $000C (AE_xspr3).

## Open (not measured)

Recording as in [vdp-and-palette.md](../concepts/vdp-and-palette.md#how-every-case-is-recorded);
the whole-RAM diff shows everything written besides PATWRK. Measured and removed: GP-01 (VRAM not read), GP-02
(answered by GP-01: no VRAM table is read), GP-03 (SCREEN 5), GP-04 (codes 0 and $FF), GP-08 (no VRAM read, so a
running command cannot matter).

| case | inputs | state | what it separates |
|---|---|---|---|
| GP-05 | A $41 | PATWRK and the 8 bytes after it preset to garbage | exactly 8 bytes written; nothing else in RAM |
| GP-06 | entry F $00 / $FF; AF' BC' DE' HL' garbage | interrupts on / off; the control call | the alternate registers and the interrupt state on return |
| GP-07 | A $A0 | the Japanese machine (HB-F900) vs the European | the national font is the source |
| GP-09 | A $41 | CGPNT := the main ROM's slot with address $E000 (the RAM copy still at $E000 in page 3); the slot written recorded | the slot byte used for the read (the main ROM slot's bytes there) vs ignored (the RAM copy); A on return = the slot byte vs another value |

## Related pages

The graphics character calls that use PATWRK; [vdp-and-palette.md](../concepts/vdp-and-palette.md).

## Tests that cover it

None yet.
