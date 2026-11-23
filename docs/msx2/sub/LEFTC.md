<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `LEFTC` (sub-ROM $00AD) — move the graphics position one pixel left

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the HB-F900, NMS 8250 and FS-A1WSX ([xsubmv.asm](../../../probes/bios/spec/xsubmv.asm), [scratchpad/AE_xsubmv_msx2.out](../../../scratchpad/AE_xsubmv_msx2.out), decoded by `scratchpad/xsubmv_decode.py`).
>
> Goldfish pass 1 (test writer) 2026-11-23: 8 findings, 5 measured, 1 moved to open (the separating cases in [xsubmv2.asm](../../../probes/bios/spec/xsubmv2.asm), [AE_xsubmv2_msx2.out](../../../scratchpad/AE_xsubmv2_msx2.out)).

## Summary

`LEFTC` (the C-BIOS peer's name; no published entry) does NOT move one pixel left on the MSX2 / MSX2+
references: in every mode measured (SCREEN 2, 5, 6, 8; SCRMOD not read) it does the multicolour cell step of the
MSX1 [LEFTC](../../bios/LEFTC.md), the mirror of [RIGHTC](RIGHTC.md), with no edge check.

## The specification

**Interface.**
- No published entry at $00AD [P TH A1 SUB-ROM, by absence]; the name and address are the C-BIOS
  peer's. A callable entry [M]: it changes CLOC / CMASK, A and F on all three references.
- Called through EXTROM, IX = $00AD [P TH A1 SUB-ROM, preamble].
- The step [M], keyed on CMASK bit 7 alone: set -> CLOC - 8, CMASK := $0F; clear -> CMASK := $F0, CLOC kept.
  CMASK $80 moves back and $40 steps in place (b35, b36): bit 7, not bit 6.
- No edge check [M]: CLOC - 8 wraps below 0 -- $0000 / $F0 -> $FFF8 / $0F in SCREEN 2 (a9) and $0000 / $C8 ->
  $FFF8 / $0F in SCREEN 5 (b43).
- Out [M]: A = the new CMASK; F = the flags of `and a` on the returned A (S, Z, P = parity, H = 1, N = 0, C = 0, bits 5 / 3 copied from A): $0F -> $1C, $F0 -> $B4. The carry is always clear.
- In SCREEN 5-8 (CLOC = X, CMASK = Y) that is X - 8 with Y := $0F, or Y := $F0 -- not a pixel step.
- Registers [M] ([xsubmv2.asm](../../../probes/bios/spec/xsubmv2.asm), every record on all three references): BC, DE and HL come back as given
  ($B0C1 / $D0E1 / $4A5B) through EXTROM. IX / IY carry EXTROM's own inputs and are not measured. Called with
  interrupts off, it returns through EXTROM with them ON (IFF2 = 1) in 206 of the 207 reference records; the one 0
  (HB-F900 b8, reproduced by every `--fresh` run) is [A] the Z80's `ld a, i` reading 0 when an interrupt is
  accepted during it, not a different state. Whether the move or EXTROM enables them is not separated (LC-90).
- VDP registers and VRAM: recorded by neither probe -- "none touched" stays [A] (LC-94).
- The state of the runs [M] (b records): ACPAGE 0 unless a row says ACPAGE 1; RG9SAV ($FFE8) $82 in SCREEN 5-8
  and $02 in SCREEN 2 on the NMS 8250 (bit 1 = its PAL bit), $80 / $00 on the HB-F900 and FS-A1WSX -- LN = 1 (212
  lines) in SCREEN 5-8. The a records did not log them; they start from the same CHGMOD [A].
- The model B / model C rules this page stated before measuring ([the concept page](../concepts/graphics-cursor.md#the-cursor-model--rival-rules-to-separate))
  are both REFUTED for this entry [M]: MAPXYC leaves CLOC = X and CMASK = Y's low byte in SCREEN 5-8 (the
  "before" column), and the step below is neither model's.

**Measured** [M] -- the same on all three references except where a line names one. Records: `aN` = [xsubmv.asm](../../../probes/bios/spec/xsubmv.asm) record N, `bN` = [xsubmv2.asm](../../../probes/bios/spec/xsubmv2.asm) record N, both counted from 0 ([AE_xsubmv_msx2.out](../../../scratchpad/AE_xsubmv_msx2.out), [AE_xsubmv2_msx2.out](../../../scratchpad/AE_xsubmv2_msx2.out); decoded by `scratchpad/xsubmv_decode.py` and [xsubmv2_decode.py](../../../scratchpad/xsubmv2_decode.py)). The start is set by MAPXYC, or by hand where the row says "planted". SCREEN 6's X 511 rows were printed as (255, 20) in the first draft: the decoder keeps only X's low byte.

| SCREEN | (X, Y) | CLOC / CMASK before | after | A | F | carry | record |
|---|---|---|---|---|---|---|---|
| 2 | (10, 20) | $022C / $F0 | $0224 / $0F | $0F | $1C | 0 | a1 |
| 2 | (0, 0) | $0000 / $F0 | $FFF8 / $0F | $0F | $1C | 0 | a9 |
| 2 | (255, 20) | $02FC / $0F | $02FC / $F0 | $F0 | $B4 | 0 | a17 |
| 2 | (10, 191) | $072F / $F0 | $0727 / $0F | $0F | $1C | 0 | a25 |
| 5 | (10, 20) | $000A / $14 | $000A / $F0 | $F0 | $B4 | 0 | a33 |
| 5 | (0, 0) | $0000 / $00 | $0000 / $F0 | $F0 | $B4 | 0 | a41 |
| 5 | (255, 20) | $00FF / $14 | $00FF / $F0 | $F0 | $B4 | 0 | a49 |
| 5 | (10, 211) | $000A / $D3 | $0002 / $0F | $0F | $1C | 0 | a57 |
| 6 | (10, 20) | $000A / $14 | $000A / $F0 | $F0 | $B4 | 0 | a65 |
| 6 | (0, 0) | $0000 / $00 | $0000 / $F0 | $F0 | $B4 | 0 | a73 |
| 6 | (511, 20) | $01FF / $14 | $01FF / $F0 | $F0 | $B4 | 0 | a81 |
| 6 | (10, 211) | $000A / $D3 | $0002 / $0F | $0F | $1C | 0 | a89 |
| 8 | (10, 20) | $000A / $14 | $000A / $F0 | $F0 | $B4 | 0 | a97 |
| 8 | (0, 0) | $0000 / $00 | $0000 / $F0 | $F0 | $B4 | 0 | a105 |
| 8 | (255, 20) | $00FF / $14 | $00FF / $F0 | $F0 | $B4 | 0 | a113 |
| 8 | (10, 211) | $000A / $D3 | $0002 / $0F | $0F | $1C | 0 | a121 |
| 5 | planted | $000A / $80 | $0002 / $0F | $0F | $1C | 0 | b35 |
| 5 | planted | $000A / $40 | $000A / $F0 | $F0 | $B4 | 0 | b36 |
| 5 | (0, 200) | $0000 / $C8 | $FFF8 / $0F | $0F | $1C | 0 | b43 |

## Differences from the reference

C-BIOS's MSX2 / MSX2+ builds differ in the 4 SCREEN 2 cases (a1, a9, a17, a25): CLOC as the references, but
CMASK and A are SCREEN 2 bit masks ($E1, $1E) with their flags ($B4, $1C) where the references use $0F / $F0.
SCREEN 5-8 (b35, b36, b43 included) are equal ([AE_xsubmv_msx2.out](../../../scratchpad/AE_xsubmv_msx2.out), [AE_xsubmv2_msx2.out](../../../scratchpad/AE_xsubmv2_msx2.out)).

## On the turbo R

Measured 2026-11-23 (D-TRSPEC) on the FS-A1GT / FS-A1ST: every case gives the same bytes as on the FS-A1WSX, on both models [M] ([AE_trall/xsubmv.out](../../../scratchpad/AE_trall/xsubmv.out), [AE_trall/xsubmv2.out](../../../scratchpad/AE_trall/xsubmv2.out); overview: [turbor/remeasured.md](../../turbor/remeasured.md)).

## Open (not measured)

The sets [PG], [LN], [MD], [SN] and [R9] are defined on [the concept page](../concepts/graphics-cursor.md#shared-measurement-setup-every-pages-matrix-assumes-it).

Every case runs on all three references; each machine's result is recorded on its own, and a rule that holds on one generation only names it ([the concept page](../concepts/graphics-cursor.md)). `—` = not measured yet; `n/a` = the mode does not exist on that machine.

| case | inputs | state | what it separates | HB-F900 | NMS 8250 | FS-A1WSX |
|---|---|---|---|---|---|---|
| LC-90 | entry A / F $00 and $FF; IX / IY; called with interrupts ON | SCREEN 2, 5 | whether A / F on entry matter; who enables the interrupts | — | — | — |
| LC-91 | CLOC / CMASK from MAPXYC | SCRMOD 3, 4, 7; [MD] | SCREEN 7 and the MSX1 modes 3 / 4: the same SCRMOD-blind step? | — | — | — |
| LC-92 | CLOC / CMASK from MAPXYC | SCRMOD 10-12 (FS-A1WSX) | the step in the YJK modes | n/a | n/a | — |
| LC-93 | CLOC $8004 / CMASK $F0 planted by hand | [PG] in SCREEN 5 / 6 | the 16-bit subtract across $8000 with ACPAGE set | — | — | — |
| LC-94 | a step from MAPXYC (100, 50) | SCREEN 5; [SN] | RAM other than CLOC / CMASK, VRAM, the VDP registers and S#n unchanged | — | — | — |
| LC-95 | MAPXYC (10, 20) | SCREEN 5, called at the main-ROM LEFTC ($00FF) | the main entry forwards to this step vs does its own | — | — | — |

## Related pages

[The concept page](../concepts/graphics-cursor.md); the MSX1 [LEFTC](../../bios/LEFTC.md); the other sub-ROM moves
[RIGHTC](RIGHTC.md), [UPC](UPC.md), [DOWNC](DOWNC.md), [TUPC](TUPC.md), [TDOWNC](TDOWNC.md), [TRIGHT](TRIGHT.md), [TLEFTC](TLEFTC.md); [MAPXYC](MAPXYC.md).

## Tests that cover it

None yet.
