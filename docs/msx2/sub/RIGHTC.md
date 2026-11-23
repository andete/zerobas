<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `RIGHTC` (sub-ROM $00A5) — move the graphics position one pixel right

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the HB-F900, NMS 8250 and FS-A1WSX ([xsubmv.asm](../../../probes/bios/spec/xsubmv.asm), [scratchpad/AE_xsubmv_msx2.out](../../../scratchpad/AE_xsubmv_msx2.out), decoded by `scratchpad/xsubmv_decode.py`).
>
> Goldfish pass 1 (test writer) 2026-11-23: 6 findings, 4 measured, 1 moved to open (the separating cases in [xsubmv2.asm](../../../probes/bios/spec/xsubmv2.asm), [AE_xsubmv2_msx2.out](../../../scratchpad/AE_xsubmv2_msx2.out)).

## Summary

`RIGHTC` (the C-BIOS peer's name; no published entry) does NOT move one pixel right on the MSX2 / MSX2+
references. In every mode measured -- SCREEN 2, 5, 6 and 8, SCRMOD not read -- it does the multicolour cell step
of the MSX1 [RIGHTC](../../bios/RIGHTC.md): within a cell's nibble pair, or on to the next 8-byte cell, with no
edge check.

## The specification

**Interface.**
- No published entry at $00A5 [P TH A1 SUB-ROM, by absence]; the name and address are the C-BIOS
  peer's. A callable entry [M]: it changes CLOC / CMASK, A and F on all three references.
- Called through EXTROM, IX = $00A5 [P TH A1 SUB-ROM, preamble].
- The step [M], keyed on CMASK bit 7 alone: set -> CMASK := $0F, CLOC kept; clear -> CLOC + 8, CMASK := $F0.
  CMASK $80 steps in place and $40 moves on (b33, b34), so the key is bit 7, not bit 6 or "CMASK >= $40".
  Every mode the same (a0-a120 step 8).
- No edge check [M]: $00FF -> $0107, $01FF -> $0207, $02FC -> $0304 (a48, a80, a16): a 16-bit add.
- Out [M]: A = the new CMASK; F = the flags of `and a` on the returned A (S, Z, P = parity, H = 1, N = 0, C = 0, bits 5 / 3 copied from A): $0F -> $1C, $F0 -> $B4. The carry is always clear.
- In SCREEN 5-8, where CLOC holds X and CMASK Y, this is X + 8 with Y overwritten by $F0, or Y := $0F -- not a
  pixel step.
- Registers [M] ([xsubmv2.asm](../../../probes/bios/spec/xsubmv2.asm), every record on all three references): BC, DE and HL come back as given
  ($B0C1 / $D0E1 / $4A5B) through EXTROM. IX / IY carry EXTROM's own inputs and are not measured. Called with
  interrupts off, it returns through EXTROM with them ON (IFF2 = 1) in 206 of the 207 reference records; the one 0
  (HB-F900 b8, reproduced by every `--fresh` run) is [A] the Z80's `ld a, i` reading 0 when an interrupt is
  accepted during it, not a different state. Whether the move or EXTROM enables them is not separated (RC-90).
- VDP registers and VRAM: recorded by neither probe -- "none touched" stays [A] (RC-94).
- The state of the runs [M] (b records): ACPAGE 0 unless a row says ACPAGE 1; RG9SAV ($FFE8) $82 in SCREEN 5-8
  and $02 in SCREEN 2 on the NMS 8250 (bit 1 = its PAL bit), $80 / $00 on the HB-F900 and FS-A1WSX -- LN = 1 (212
  lines) in SCREEN 5-8. The a records did not log them; they start from the same CHGMOD [A].
- The model B / model C rules this page stated before measuring ([the concept page](../concepts/graphics-cursor.md#the-cursor-model--rival-rules-to-separate))
  are both REFUTED for this entry [M]: MAPXYC leaves CLOC = X and CMASK = Y's low byte in SCREEN 5-8 (the
  "before" column), and the step below is neither model's.

**Measured** [M] -- the same on all three references except where a line names one. Records: `aN` = [xsubmv.asm](../../../probes/bios/spec/xsubmv.asm) record N, `bN` = [xsubmv2.asm](../../../probes/bios/spec/xsubmv2.asm) record N, both counted from 0 ([AE_xsubmv_msx2.out](../../../scratchpad/AE_xsubmv_msx2.out), [AE_xsubmv2_msx2.out](../../../scratchpad/AE_xsubmv2_msx2.out); decoded by `scratchpad/xsubmv_decode.py` and [xsubmv2_decode.py](../../../scratchpad/xsubmv2_decode.py)). The start is set by MAPXYC, or by hand where the row says "planted". SCREEN 6's X 511 rows were printed as (255, 20) in the first draft: the decoder keeps only X's low byte.

| SCREEN | (X, Y) | CLOC / CMASK before | after | A | F | carry | record |
|---|---|---|---|---|---|---|---|
| 2 | (10, 20) | $022C / $F0 | $022C / $0F | $0F | $1C | 0 | a0 |
| 2 | (0, 0) | $0000 / $F0 | $0000 / $0F | $0F | $1C | 0 | a8 |
| 2 | (255, 20) | $02FC / $0F | $0304 / $F0 | $F0 | $B4 | 0 | a16 |
| 2 | (10, 191) | $072F / $F0 | $072F / $0F | $0F | $1C | 0 | a24 |
| 5 | (10, 20) | $000A / $14 | $0012 / $F0 | $F0 | $B4 | 0 | a32 |
| 5 | (0, 0) | $0000 / $00 | $0008 / $F0 | $F0 | $B4 | 0 | a40 |
| 5 | (255, 20) | $00FF / $14 | $0107 / $F0 | $F0 | $B4 | 0 | a48 |
| 5 | (10, 211) | $000A / $D3 | $000A / $0F | $0F | $1C | 0 | a56 |
| 6 | (10, 20) | $000A / $14 | $0012 / $F0 | $F0 | $B4 | 0 | a64 |
| 6 | (0, 0) | $0000 / $00 | $0008 / $F0 | $F0 | $B4 | 0 | a72 |
| 6 | (511, 20) | $01FF / $14 | $0207 / $F0 | $F0 | $B4 | 0 | a80 |
| 6 | (10, 211) | $000A / $D3 | $000A / $0F | $0F | $1C | 0 | a88 |
| 8 | (10, 20) | $000A / $14 | $0012 / $F0 | $F0 | $B4 | 0 | a96 |
| 8 | (0, 0) | $0000 / $00 | $0008 / $F0 | $F0 | $B4 | 0 | a104 |
| 8 | (255, 20) | $00FF / $14 | $0107 / $F0 | $F0 | $B4 | 0 | a112 |
| 8 | (10, 211) | $000A / $D3 | $000A / $0F | $0F | $1C | 0 | a120 |
| 5 | planted | $000A / $80 | $000A / $0F | $0F | $1C | 0 | b33 |
| 5 | planted | $000A / $40 | $0012 / $F0 | $F0 | $B4 | 0 | b34 |

## Differences from the reference

C-BIOS's MSX2 / MSX2+ builds differ in the 4 SCREEN 2 cases (a0, a8, a16, a24): CLOC as the references, but
CMASK and A are SCREEN 2 bit masks ($78, $87) with their flags ($3C, $94), where the references use the
multicolour nibbles $0F / $F0. SCREEN 5-8, the planted bit-7 / bit-6 cases (b33, b34) included, are equal
([AE_xsubmv_msx2.out](../../../scratchpad/AE_xsubmv_msx2.out), [AE_xsubmv2_msx2.out](../../../scratchpad/AE_xsubmv2_msx2.out)).

## On the turbo R

Measured 2026-11-23 (D-TRSPEC) on the FS-A1GT / FS-A1ST: every case gives the same bytes as on the FS-A1WSX, on both models [M] ([AE_trall/xsubmv.out](../../../scratchpad/AE_trall/xsubmv.out), [AE_trall/xsubmv2.out](../../../scratchpad/AE_trall/xsubmv2.out); overview: [turbor/remeasured.md](../../turbor/remeasured.md)).

## Open (not measured)

The sets [PG], [LN], [MD], [SN] and [R9] are defined on [the concept page](../concepts/graphics-cursor.md#shared-measurement-setup-every-pages-matrix-assumes-it).

Every case runs on all three references; each machine's result is recorded on its own, and a rule that holds on one generation only names it ([the concept page](../concepts/graphics-cursor.md)). `—` = not measured yet; `n/a` = the mode does not exist on that machine.

| case | inputs | state | what it separates | HB-F900 | NMS 8250 | FS-A1WSX |
|---|---|---|---|---|---|---|
| RC-90 | entry A / F $00 and $FF; IX / IY; called with interrupts ON | SCREEN 2, 5 | whether A / F on entry matter; who enables the interrupts (the move or EXTROM) | — | — | — |
| RC-91 | CLOC / CMASK from MAPXYC | SCRMOD 3, 4, 7; [MD] | SCREEN 7 (512 wide) and the MSX1 modes 3 / 4: the same SCRMOD-blind step? | — | — | — |
| RC-92 | CLOC / CMASK from MAPXYC | SCRMOD 10-12 (FS-A1WSX) | the step in the YJK modes | n/a | n/a | — |
| RC-93 | CLOC $8000 + offset planted by hand | [PG] in SCREEN 5 / 6 | the 16-bit add across $FFF8 and with ACPAGE set | — | — | — |
| RC-94 | a step from MAPXYC (100, 50) | SCREEN 5; [SN] | RAM other than CLOC / CMASK, VRAM, the VDP registers and S#n unchanged | — | — | — |
| RC-95 | MAPXYC (10, 20) | SCREEN 5, called at the main-ROM RIGHTC ($00FC) | the main entry forwards to this step vs does its own | — | — | — |

## Related pages

[The concept page](../concepts/graphics-cursor.md); the MSX1 [RIGHTC](../../bios/RIGHTC.md); the other sub-ROM moves
[LEFTC](LEFTC.md), [UPC](UPC.md), [DOWNC](DOWNC.md), [TUPC](TUPC.md), [TDOWNC](TDOWNC.md), [TRIGHT](TRIGHT.md), [TLEFTC](TLEFTC.md); [MAPXYC](MAPXYC.md).

## Tests that cover it

None yet.
