<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `SETATR` (sub-ROM $0099) — set the graphics colour

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the HB-F900, NMS 8250 and FS-A1WSX ([xsubgc.asm](../../probes/bios/spec/xsubgc.asm), [scratchpad/AE_xsubgc_msx2.out](../../scratchpad/AE_xsubgc_msx2.out), decoded by `scratchpad/xsubgc_decode.py`).

## Summary

`SETATR` is assumed to be the sub-ROM's counterpart of the main ROM's [SETATR](../../bios/SETATR.md)
($011A): it sets ATRBYT, the colour the graphics calls draw with, and refuses an out-of-range
colour with the carry. The MSX1 range is 0-15; in SCREEN 6 a pixel holds 0-3 and in SCREEN 8 0-255,
so the range test is the open question.

## The specification

**Interface.**
- No published entry at $0099 [P TH A1 SUB-ROM, by absence]; a callable entry is [A] (case SA-00).
- In: A, the colour. Out: ATRBYT ($F3F2) := A and the carry clear when A is in range; ATRBYT kept
  and the carry set otherwise [A, as MSX1]. ATRBYT's cell: [P TH A4].
- The range [A]: 0-15 in SCREEN 5 / 7; 0-3 or 0-15 in SCREEN 6 (the border and sprites still take 4
  bits there, [P TH 4 §3.7.3]); 0-255 in SCREEN 8; 0-15 in SCREEN 2-4.
- Other registers and the interrupt state kept [A, as MSX1].

**Measured** [M] (the same on all three references): A $0B gives ATRBYT $0B in SCREEN 2, 5, 7 and 8, and
**$0F in SCREEN 6** (not $0B, nor $0B AND 3).

## Differences from the reference

C-BIOS's MSX2 / MSX2+ builds store the same ([scratchpad/AE_xsubgc_msx2.out](../../scratchpad/AE_xsubgc_msx2.out)).

## Open (not measured)

The sets [PG], [LG], [LN], [MD], [SN] and [R9] are defined on [the concept page](../concepts/graphics-cursor.md#shared-measurement-setup-every-pages-matrix-assumes-it).

Every case runs on all three references; each machine's result is recorded on its own, and a rule that holds on one generation only names it ([the concept page](../concepts/graphics-cursor.md)). `—` = not measured yet; `n/a` = the mode does not exist on that machine.

| case | inputs | state | what it separates | HB-F900 | NMS 8250 | FS-A1WSX |
|---|---|---|---|---|---|---|
| SA-00 | A 5 | SCREEN 5 | a callable entry vs not | — | — | — |
| SA-01 | A 3, 4, 15, 16 | SCREEN 6 | the SCREEN 6 range: 4 vs 16 | — | — | — |
| SA-02 | A 15, 16, $FF | SCREEN 5, 7 | the 4-bit range | — | — | — |
| SA-03 | A 16, $80, $FF | SCREEN 8 | all 256 accepted vs the 4-bit test applied anyway: **the case that shows whether the range depends on the mode** | — | — | — |
| SA-04 | A 4, 16 | SCRMOD 2, 3, 4 | the MSX1 range through the sub-ROM in the MSX1-shaped modes (SA-04 alone does not show mode dependence: under a fixed 0-15 test every mode agrees; SA-01 / SA-03 do) | — | — | — |
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
