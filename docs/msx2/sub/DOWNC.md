<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `DOWNC` (sub-ROM $00B5) — move the graphics position one pixel down

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the HB-F900, NMS 8250 and FS-A1WSX ([xsubmv.asm](../../../probes/bios/spec/xsubmv.asm), [scratchpad/AE_xsubmv_msx2.out](../../../scratchpad/AE_xsubmv_msx2.out), decoded by `scratchpad/xsubmv_decode.py`).
>
> Goldfish pass 1 (test writer) 2026-11-23: 9 findings, 4 measured, 1 moved to open (the separating cases in [xsubmv2.asm](../../../probes/bios/spec/xsubmv2.asm), [AE_xsubmv2_msx2.out](../../../scratchpad/AE_xsubmv2_msx2.out)).

## Summary

`DOWNC` (the C-BIOS peer's name; no published entry) does the MSX1 [DOWNC](../../bios/DOWNC.md) arithmetic
in every mode measured (SCREEN 2, 5, 6, 8; SCRMOD not read), the mirror of [UPC](UPC.md): CLOC + 1 within an
8-byte cell, the next 256-byte row past a cell's bottom. CMASK is not touched.

## The specification

**Interface.**
- No published entry at $00B5 [P TH A1 SUB-ROM, by absence]; the name and address are the C-BIOS
  peer's. A callable entry [M]: it changes CLOC / CMASK, A and F on all three references.
- Called through EXTROM, IX = $00B5 [P TH A1 SUB-ROM, preamble].
- The step [M]: CLOC + 1; when the result AND 7 = 0, + $F8 more (down a 256-byte row, back to the cell's top).
  $00FF -> $01F8 (a51), $01FF -> $02F8 (a83), $072F -> $0828 (a27); otherwise + 1 ($000A -> $000B). CMASK kept and
  not read.
- No edge check [M]: SCREEN 2 (10, 191) moves on to $0828 (a27).
- Out [M]: A = the new CLOC AND 7 taken BEFORE the + $F8 (0 at a row step); F = the flags of `and a` on the returned A (S, Z, P = parity, H = 1, N = 0, C = 0, bits 5 / 3 copied from A): $00 -> $54, $01 / $03 /
  $05 -> $10 / $14 / $14. The carry is always clear.
- In SCREEN 5-8 (CLOC = X): X + 1, except X AND 7 = 7, where CLOC gains $F9 in all ($00FF -> $01F8).
- Registers [M] ([xsubmv2.asm](../../../probes/bios/spec/xsubmv2.asm), every record on all three references): BC, DE and HL come back as given
  ($B0C1 / $D0E1 / $4A5B) through EXTROM. IX / IY carry EXTROM's own inputs and are not measured. Called with
  interrupts off, it returns through EXTROM with them ON (IFF2 = 1) in 206 of the 207 reference records; the one 0
  (HB-F900 b8, reproduced by every `--fresh` run) is [A] the Z80's `ld a, i` reading 0 when an interrupt is
  accepted during it, not a different state. Whether the move or EXTROM enables them is not separated (DC-90).
- VDP registers and VRAM: recorded by neither probe -- "none touched" stays [A] (DC-94).
- The state of the runs [M] (b records): ACPAGE 0 unless a row says ACPAGE 1; RG9SAV ($FFE8) $82 in SCREEN 5-8
  and $02 in SCREEN 2 on the NMS 8250 (bit 1 = its PAL bit), $80 / $00 on the HB-F900 and FS-A1WSX -- LN = 1 (212
  lines) in SCREEN 5-8. The a records did not log them; they start from the same CHGMOD [A].
- The model B / model C rules this page stated before measuring ([the concept page](../concepts/graphics-cursor.md#the-cursor-model--rival-rules-to-separate))
  are both REFUTED for this entry [M]: MAPXYC leaves CLOC = X and CMASK = Y's low byte in SCREEN 5-8 (the
  "before" column), and the step below is neither model's.

**Measured** [M] -- the same on all three references except where a line names one. Records: `aN` = [xsubmv.asm](../../../probes/bios/spec/xsubmv.asm) record N, `bN` = [xsubmv2.asm](../../../probes/bios/spec/xsubmv2.asm) record N, both counted from 0 ([AE_xsubmv_msx2.out](../../../scratchpad/AE_xsubmv_msx2.out), [AE_xsubmv2_msx2.out](../../../scratchpad/AE_xsubmv2_msx2.out); decoded by `scratchpad/xsubmv_decode.py` and [xsubmv2_decode.py](../../../scratchpad/xsubmv2_decode.py)). The start is set by MAPXYC, or by hand where the row says "planted". SCREEN 6's X 511 rows were printed as (255, 20) in the first draft: the decoder keeps only X's low byte.

| SCREEN | (X, Y) | CLOC / CMASK before | after | A | F | carry | record |
|---|---|---|---|---|---|---|---|
| 2 | (10, 20) | $022C / $F0 | $022D / $F0 | $05 | $14 | 0 | a3 |
| 2 | (0, 0) | $0000 / $F0 | $0001 / $F0 | $01 | $10 | 0 | a11 |
| 2 | (255, 20) | $02FC / $0F | $02FD / $0F | $05 | $14 | 0 | a19 |
| 2 | (10, 191) | $072F / $F0 | $0828 / $F0 | $00 | $54 | 0 | a27 |
| 5 | (10, 20) | $000A / $14 | $000B / $14 | $03 | $14 | 0 | a35 |
| 5 | (0, 0) | $0000 / $00 | $0001 / $00 | $01 | $10 | 0 | a43 |
| 5 | (255, 20) | $00FF / $14 | $01F8 / $14 | $00 | $54 | 0 | a51 |
| 5 | (10, 211) | $000A / $D3 | $000B / $D3 | $03 | $14 | 0 | a59 |
| 6 | (10, 20) | $000A / $14 | $000B / $14 | $03 | $14 | 0 | a67 |
| 6 | (0, 0) | $0000 / $00 | $0001 / $00 | $01 | $10 | 0 | a75 |
| 6 | (511, 20) | $01FF / $14 | $02F8 / $14 | $00 | $54 | 0 | a83 |
| 6 | (10, 211) | $000A / $D3 | $000B / $D3 | $03 | $14 | 0 | a91 |
| 8 | (10, 20) | $000A / $14 | $000B / $14 | $03 | $14 | 0 | a99 |
| 8 | (0, 0) | $0000 / $00 | $0001 / $00 | $01 | $10 | 0 | a107 |
| 8 | (255, 20) | $00FF / $14 | $01F8 / $14 | $00 | $54 | 0 | a115 |
| 8 | (10, 211) | $000A / $D3 | $000B / $D3 | $03 | $14 | 0 | a123 |

## Differences from the reference

C-BIOS's MSX2 / MSX2+ builds give the same CLOC / CMASK / A / F in every case ([AE_xsubmv_msx2.out](../../../scratchpad/AE_xsubmv_msx2.out)).

## Open (not measured)

The sets [PG], [LN], [MD], [SN] and [R9] are defined on [the concept page](../concepts/graphics-cursor.md#shared-measurement-setup-every-pages-matrix-assumes-it).

Every case runs on all three references; each machine's result is recorded on its own, and a rule that holds on one generation only names it ([the concept page](../concepts/graphics-cursor.md)). `—` = not measured yet; `n/a` = the mode does not exist on that machine.

| case | inputs | state | what it separates | HB-F900 | NMS 8250 | FS-A1WSX |
|---|---|---|---|---|---|---|
| DC-90 | entry A / F $00 and $FF; IX / IY; called with interrupts ON | SCREEN 2, 5 | whether A / F on entry matter; who enables the interrupts | — | — | — |
| DC-91 | CLOC / CMASK from MAPXYC | SCRMOD 3, 4, 7; [MD] | SCREEN 7 and the MSX1 modes 3 / 4: the same SCRMOD-blind step? | — | — | — |
| DC-92 | CLOC / CMASK from MAPXYC | SCRMOD 10-12 (FS-A1WSX) | the step in the YJK modes | n/a | n/a | — |
| DC-93 | CLOC $FFFF, $7FFF / CMASK $14 planted by hand | [PG] in SCREEN 5 / 6 | the 16-bit carry of the + $F8 branch ($FFFF -> $00F8?) | — | — | — |
| DC-94 | a step from MAPXYC (100, 50) | SCREEN 5; [SN] | RAM other than CLOC / CMASK, VRAM, the VDP registers and S#n unchanged | — | — | — |
| DC-95 | MAPXYC (10, 20) | SCREEN 5, called at the main-ROM DOWNC ($0108) | the main entry forwards to this step vs does its own | — | — | — |

## Related pages

[The concept page](../concepts/graphics-cursor.md); the MSX1 [DOWNC](../../bios/DOWNC.md); the other sub-ROM moves
[RIGHTC](RIGHTC.md), [LEFTC](LEFTC.md), [UPC](UPC.md), [TUPC](TUPC.md), [TDOWNC](TDOWNC.md), [TRIGHT](TRIGHT.md), [TLEFTC](TLEFTC.md); [MAPXYC](MAPXYC.md).

## Tests that cover it

None yet.
