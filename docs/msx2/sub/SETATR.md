<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `SETATR` (sub-ROM $0099) — set the graphics colour

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the HB-F900, NMS 8250 and FS-A1WSX ([xsubgc.asm](../../../probes/bios/spec/xsubgc.asm), [scratchpad/AE_xsubgc_msx2.out](../../../scratchpad/AE_xsubgc_msx2.out), decoded by `scratchpad/xsubgc_decode.py`; the separating cases [xsubgc2.asm](../../../probes/bios/spec/xsubgc2.asm), [scratchpad/AE_xsubgc2_msx2.out](../../../scratchpad/AE_xsubgc2_msx2.out), decoded by [scratchpad/xsubgc2_decode.py](../../../scratchpad/xsubgc2_decode.py) into [scratchpad/AE_xsubgc2_msx2_decoded.out](../../../scratchpad/AE_xsubgc2_msx2_decoded.out)). `[G1]` = the first run, `[G2 Ann]` = the second run's SETATR records.
>
> Goldfish pass 1 (test writer) 2026-11-23: 5 findings, 3 measured, 0 moved to open, 2 corrected (the probe header's ATRBYT label; stale cells).

## Summary

`SETATR` is assumed to be the sub-ROM's counterpart of the main ROM's [SETATR](../../bios/SETATR.md)
($011A): it sets ATRBYT, the colour the graphics calls draw with, and refuses an out-of-range
colour with the carry. The MSX1 range is 0-15; in SCREEN 6 a pixel holds 0-3 and in SCREEN 8 0-255,
so the range test is the open question.

## The specification

**Interface.**
- No published entry at $0099 [P TH A1 SUB-ROM, by absence]; a callable entry on all three references [M] (case SA-00).
- In: A, the colour. Out: ATRBYT ($F3F2) := A and the carry clear when A is in range; ATRBYT kept
  and the carry set otherwise [M, below; SCREEN 6 stores a transform of A]. ATRBYT's cell: [P TH A4].
- The range: 0-15 in SCREEN 2, 5, 7; none in SCREEN 6 and 8 [M, below]; SCREEN 3 / 4 [A].
- Other registers and the interrupt state kept [A, as MSX1].

**Measured** [M] (the same on all three references, except one undocumented flag bit, below). Each case: CHGMOD,
then FORCLR := 7 and ATRBYT := 5 by hand, SETATR, ATRBYT and F read at once [G2 A01-A17]. The range depends on the mode:
- **SCREEN 2, 5, 7: 0-15.** A $0F stored, carry clear (F $98); A $10 and $FF refused, ATRBYT kept at 5, carry set
  (F $41 for $10) [G2 A06-A09, A13, A14] (SCREEN 7: only A $10 run).
- **SCREEN 8: no test.** A $10, $80, $FF stored, carry clear (F $10, $90, $BC) [G2 A10-A12].
- **SCREEN 6: no test, and the value is transformed: ATRBYT := (A AND 3) x 5** -- the 2-bit colour copied into both
  halves of the nibble. A 1 -> $05, 2 -> $0A, 3 -> $0F, 4 -> $00, $0B -> $0F, $0E -> $0A, $0F -> $0F, $10 -> $00; the
  carry clear every time [G2 A01-A05, A15-A17]. This is why the first run's SCREEN 6 ATRBYT read $0F after SETATR $0B
  [G1] (that record was read at the end of the point, after SETC and READC; [G2] reads it right after SETATR).
- F beyond the carry: the values above. For A $FF in SCREEN 5 the NMS 8250 and HB-F900 give F $A9, the FS-A1WSX $89
  (bit 5, undocumented) [G2 A08].

## Differences from the reference

C-BIOS's MSX2 / MSX2+ builds store the same ATRBYT and set the same carry in every case, the SCREEN 6 transform
included. F: the MSX2+ build gives $A9 for A $FF in SCREEN 5 where the FS-A1WSX gives $89 (bit 5 only) [G2 A08]
([scratchpad/AE_xsubgc_msx2.out](../../../scratchpad/AE_xsubgc_msx2.out),
[scratchpad/AE_xsubgc2_msx2_decoded.out](../../../scratchpad/AE_xsubgc2_msx2_decoded.out)).

## Open (not measured)

The sets [PG], [LG], [LN], [MD], [SN] and [R9] are defined on [the concept page](../concepts/graphics-cursor.md#shared-measurement-setup-every-pages-matrix-assumes-it).

Every case runs on all three references; each machine's result is recorded on its own, and a rule that holds on one generation only names it ([the concept page](../concepts/graphics-cursor.md)). `—` = not measured yet; `n/a` = the mode does not exist on that machine.

| case | inputs | state | what it separates | HB-F900 | NMS 8250 | FS-A1WSX |
|---|---|---|---|---|---|---|
| SA-00 | A 5 | SCREEN 5 | a callable entry vs not | [M] callable | [M] callable | [M] callable |
| SA-01 | A 1, 2, 3, 4, 15, 16 | SCREEN 6, ATRBYT 5 and FORCLR 7 planted | the SCREEN 6 range: 4 vs 16 | [M] neither: no test, (A AND 3) x 5, carry clear [G2 A01-A05, A15-A17] | [M] same | [M] same |
| SA-02 | A 15, 16, $FF | SCREEN 5, 7, ATRBYT 5 planted | the 4-bit range | [M] 0-15; 16 / $FF kept 5, carry set [G2 A06-A09] | [M] same | [M] same (F $89 for $FF) |
| SA-03 | A 16, $80, $FF | SCREEN 8, ATRBYT 5 planted | all 256 accepted vs the 4-bit test applied anyway: **the case that shows whether the range depends on the mode** | [M] all accepted, carry clear [G2 A10-A12] | [M] same | [M] same |
| SA-04 | A 4, 16 | SCRMOD 2, 3, 4 | the MSX1 range through the sub-ROM in the MSX1-shaped modes (SA-04 alone does not show mode dependence: under a fixed 0-15 test every mode agrees; SA-01 / SA-03 do) | [M] SCREEN 2: 15 stored, 16 refused [G2 A13, A14]; 3 / 4 — | [M] same | [M] same |
| SA-05 | A 7, entry F $00 / $FF, garbage in all registers | each mode | F beyond the carry (MSX1: CP $10 then CCF); registers kept | — | — | — |
| SA-06 | A 5 | ATRBYT $77, the byte at $F3F3 $66 | which cell is written (the handbook's $F3F3 / $F3F2 conflict) | — | — | — |
| SA-07 | A 16, $FF | SCRMOD 10-12 (FS-A1WSX) | the range in the YJK modes | n/a | n/a | — |
| SA-08 | A 5; A 16 | SCREEN 5; [SN] | only ATRBYT changes in RAM; no VDP access | — | — | — |
| SA-09 | A 16, $80 | SCREEN 6, 8, called at the main-ROM SETATR ($011A) | the main entry forwards in SCREEN 5-8 vs the MSX1 0-15 test | — | — | — |

## Related pages

[The concept page](../concepts/graphics-cursor.md); the MSX1 [SETATR](../../bios/SETATR.md);
[SETC](SETC.md), [NVBXLN](NVBXLN.md), [NVBXFL](NVBXFL.md) (ATRBYT's readers).

## Tests that cover it

None yet.
