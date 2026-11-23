<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `TRIGHT` (sub-ROM $00A1) — move the graphics position right, checking the edge

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the HB-F900, NMS 8250 and FS-A1WSX ([xsubmv.asm](../../../probes/bios/spec/xsubmv.asm), [scratchpad/AE_xsubmv_msx2.out](../../../scratchpad/AE_xsubmv_msx2.out), decoded by `scratchpad/xsubmv_decode.py`).
>
> Goldfish pass 1 (test writer) 2026-11-23: 13 findings, 9 measured, 1 moved to open (the separating cases in [xsubmv2.asm](../../../probes/bios/spec/xsubmv2.asm), [AE_xsubmv2_msx2.out](../../../scratchpad/AE_xsubmv2_msx2.out)).

## Summary

`TRIGHT` (the C-BIOS peer's name; no published entry, no MSX1 counterpart) is [RIGHTC](RIGHTC.md)'s
multicolour cell step with an edge stop, the same in every mode measured (SCREEN 2, 5, 6, 8; SCRMOD not read). The
edge is a CLOC low-byte test, not X 255 / 511.

## The specification

**Interface.**
- No published entry at $00A1 [P TH A1 SUB-ROM, by absence]; the name and address are the C-BIOS
  peer's. A callable entry [M]: it changes CLOC / CMASK, A and F on all three references.
- Called through EXTROM, IX = $00A1 [P TH A1 SUB-ROM, preamble].
- There is no MSX1 main-ROM TRIGHT ([the MSX1 BIOS index](../../bios/index.md) has none), hence no TR-95 row.
- CMASK bit 7 set [M]: CMASK := $0F, CLOC kept, and NO edge test -- $00FF / $C8 -> $00FF / $0F (b31), SCREEN 2
  $02F4 / $F0 -> $02F4 / $0F (b8). CMASK $80 steps in place, $40 moves on (b37, b38): bit 7, not bit 6.
- CMASK bit 7 clear [M]: when CLOC's low byte is >= $F8 (the + 8 would carry out of the low byte) it stops;
  otherwise CLOC + 8, CMASK := $F0. $00F7 -> $00FF / $F0 moves (b30); $00F8, $00FA, $00FE, $00FF stop (b29, b28,
  b27, a52); so do $01FF planted in SCREEN 5 (b32), $00FF in SCREEN 6 (X 255, b44), $01FF in SCREEN 6 (a84), and
  SCREEN 2 $02FC (a20) and $01FC planted (b56); SCREEN 2 $02EC / $0F -> $02F4 / $F0 (b9). Neither "X = 255 / 511"
  nor "the step would pass X 255" fits: SCREEN 6 X 255 stops, SCREEN 5 X 248 stops.
- The stop [M], every mode and CLOC: CLOC / CMASK kept, A = $F8, F = $69 (Z, C, bits 5 / 3), the carry set.
- Out on a move [M]: as RIGHTC -- A = the new CMASK, F = the flags of `and a` on the returned A (S, Z, P = parity, H = 1, N = 0, C = 0, bits 5 / 3 copied from A); the carry clear.
- Registers [M] ([xsubmv2.asm](../../../probes/bios/spec/xsubmv2.asm), every record on all three references): BC, DE and HL come back as given
  ($B0C1 / $D0E1 / $4A5B) through EXTROM. IX / IY carry EXTROM's own inputs and are not measured. Called with
  interrupts off, it returns through EXTROM with them ON (IFF2 = 1) in 206 of the 207 reference records; the one 0
  (HB-F900 b8, reproduced by every `--fresh` run) is [A] the Z80's `ld a, i` reading 0 when an interrupt is
  accepted during it, not a different state. Whether the move or EXTROM enables them is not separated (TR-90).
- VDP registers and VRAM: recorded by neither probe -- "none touched" stays [A] (TR-94).
- The state of the runs [M] (b records): ACPAGE 0 unless a row says ACPAGE 1; RG9SAV ($FFE8) $82 in SCREEN 5-8
  and $02 in SCREEN 2 on the NMS 8250 (bit 1 = its PAL bit), $80 / $00 on the HB-F900 and FS-A1WSX -- LN = 1 (212
  lines) in SCREEN 5-8. The a records did not log them; they start from the same CHGMOD [A].
- The model B / model C rules this page stated before measuring ([the concept page](../concepts/graphics-cursor.md#the-cursor-model--rival-rules-to-separate))
  are both REFUTED for this entry [M]: MAPXYC leaves CLOC = X and CMASK = Y's low byte in SCREEN 5-8 (the
  "before" column), and the step below is neither model's.

**Measured** [M] -- the same on all three references except where a line names one. Records: `aN` = [xsubmv.asm](../../../probes/bios/spec/xsubmv.asm) record N, `bN` = [xsubmv2.asm](../../../probes/bios/spec/xsubmv2.asm) record N, both counted from 0 ([AE_xsubmv_msx2.out](../../../scratchpad/AE_xsubmv_msx2.out), [AE_xsubmv2_msx2.out](../../../scratchpad/AE_xsubmv2_msx2.out); decoded by `scratchpad/xsubmv_decode.py` and [xsubmv2_decode.py](../../../scratchpad/xsubmv2_decode.py)). The start is set by MAPXYC, or by hand where the row says "planted". SCREEN 6's X 511 rows were printed as (255, 20) in the first draft: the decoder keeps only X's low byte.

| SCREEN | (X, Y) | CLOC / CMASK before | after | A | F | carry | record |
|---|---|---|---|---|---|---|---|
| 2 | (10, 20) | $022C / $F0 | $022C / $0F | $0F | $1C | 0 | a4 |
| 2 | (0, 0) | $0000 / $F0 | $0000 / $0F | $0F | $1C | 0 | a12 |
| 2 | (255, 20) | $02FC / $0F | $02FC / $0F | $F8 | $69 | 1 | a20 |
| 2 | (10, 191) | $072F / $F0 | $072F / $0F | $0F | $1C | 0 | a28 |
| 5 | (10, 20) | $000A / $14 | $0012 / $F0 | $F0 | $B4 | 0 | a36 |
| 5 | (0, 0) | $0000 / $00 | $0008 / $F0 | $F0 | $B4 | 0 | a44 |
| 5 | (255, 20) | $00FF / $14 | $00FF / $14 | $F8 | $69 | 1 | a52 |
| 5 | (10, 211) | $000A / $D3 | $000A / $0F | $0F | $1C | 0 | a60 |
| 6 | (10, 20) | $000A / $14 | $0012 / $F0 | $F0 | $B4 | 0 | a68 |
| 6 | (0, 0) | $0000 / $00 | $0008 / $F0 | $F0 | $B4 | 0 | a76 |
| 6 | (511, 20) | $01FF / $14 | $01FF / $14 | $F8 | $69 | 1 | a84 |
| 6 | (10, 211) | $000A / $D3 | $000A / $0F | $0F | $1C | 0 | a92 |
| 8 | (10, 20) | $000A / $14 | $0012 / $F0 | $F0 | $B4 | 0 | a100 |
| 8 | (0, 0) | $0000 / $00 | $0008 / $F0 | $F0 | $B4 | 0 | a108 |
| 8 | (255, 20) | $00FF / $14 | $00FF / $14 | $F8 | $69 | 1 | a116 |
| 8 | (10, 211) | $000A / $D3 | $000A / $0F | $0F | $1C | 0 | a124 |
| 2 | (252, 20) | $02F4 / $F0 | $02F4 / $0F | $0F | $1C | 0 | b8 |
| 2 | (251, 20) | $02EC / $0F | $02F4 / $F0 | $F0 | $B4 | 0 | b9 |
| 2 | (248, 20) | $02E4 / $F0 | $02E4 / $0F | $0F | $1C | 0 | b10 |
| 2 | planted | $01FC / $0F | $01FC / $0F | $F8 | $69 | 1 | b56 |
| 5 | (254, 3) | $00FE / $03 | $00FE / $03 | $F8 | $69 | 1 | b27 |
| 5 | (250, 20) | $00FA / $14 | $00FA / $14 | $F8 | $69 | 1 | b28 |
| 5 | (248, 20) | $00F8 / $14 | $00F8 / $14 | $F8 | $69 | 1 | b29 |
| 5 | (247, 20) | $00F7 / $14 | $00FF / $F0 | $F0 | $B4 | 0 | b30 |
| 5 | (255, 200) | $00FF / $C8 | $00FF / $0F | $0F | $1C | 0 | b31 |
| 5 | planted | $01FF / $14 | $01FF / $14 | $F8 | $69 | 1 | b32 |
| 5 | planted | $000A / $80 | $000A / $0F | $0F | $1C | 0 | b37 |
| 5 | planted | $000A / $40 | $0012 / $F0 | $F0 | $B4 | 0 | b38 |
| 6 | (255, 20) | $00FF / $14 | $00FF / $14 | $F8 | $69 | 1 | b44 |

## Differences from the reference

C-BIOS's MSX2 / MSX2+ builds (the subject) do NOTHING here: CLOC / CMASK unchanged, A as the caller left it
($A7), the carry never set, in every case and mode ([AE_xsubmv_msx2.out](../../../scratchpad/AE_xsubmv_msx2.out), [AE_xsubmv2_msx2.out](../../../scratchpad/AE_xsubmv2_msx2.out)).

## Open (not measured)

The sets [PG], [LN], [MD], [SN] and [R9] are defined on [the concept page](../concepts/graphics-cursor.md#shared-measurement-setup-every-pages-matrix-assumes-it).

Every case runs on all three references; each machine's result is recorded on its own, and a rule that holds on one generation only names it ([the concept page](../concepts/graphics-cursor.md)). `—` = not measured yet; `n/a` = the mode does not exist on that machine.

| case | inputs | state | what it separates | HB-F900 | NMS 8250 | FS-A1WSX |
|---|---|---|---|---|---|---|
| TR-90 | entry A / F $00 and $FF; IX / IY; called with interrupts ON | SCREEN 2, 5 | whether A / F on entry matter (the stop's $F8 / $69 constant?); who enables the interrupts | — | — | — |
| TR-91 | CLOC / CMASK from MAPXYC | SCRMOD 3, 4, 7; [MD] | SCREEN 7 (512 wide) and the MSX1 modes 3 / 4: the same low-byte edge? | — | — | — |
| TR-92 | CLOC / CMASK from MAPXYC | SCRMOD 10-12 (FS-A1WSX) | the step in the YJK modes | n/a | n/a | — |
| TR-93 | CLOC $80F8, $80F7 / CMASK $14 planted by hand | [PG] in SCREEN 5 / 6 | the low-byte edge with a page bit set | — | — | — |
| TR-94 | a step from MAPXYC (100, 50) | SCREEN 5; [SN] | RAM other than CLOC / CMASK, VRAM, the VDP registers and S#n unchanged | — | — | — |

## Related pages

[The concept page](../concepts/graphics-cursor.md); the MSX1 [RIGHTC](../../bios/RIGHTC.md) (the unchecked move); the other sub-ROM moves
[RIGHTC](RIGHTC.md), [LEFTC](LEFTC.md), [UPC](UPC.md), [DOWNC](DOWNC.md), [TUPC](TUPC.md), [TDOWNC](TDOWNC.md), [TLEFTC](TLEFTC.md); [MAPXYC](MAPXYC.md).

## Tests that cover it

None yet.
