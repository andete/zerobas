<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `TLEFTC` (sub-ROM $00A9) — move the graphics position left, checking the edge

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the HB-F900, NMS 8250 and FS-A1WSX ([xsubmv.asm](../../../probes/bios/spec/xsubmv.asm), [scratchpad/AE_xsubmv_msx2.out](../../../scratchpad/AE_xsubmv_msx2.out), decoded by `scratchpad/xsubmv_decode.py`).
>
> Goldfish pass 1 (test writer) 2026-11-23: 12 findings, 7 measured, 1 moved to open (the separating cases in [xsubmv2.asm](../../../probes/bios/spec/xsubmv2.asm), [AE_xsubmv2_msx2.out](../../../scratchpad/AE_xsubmv2_msx2.out)).

## Summary

`TLEFTC` (the C-BIOS peer's name; no published entry, no MSX1 counterpart) reads SCRMOD, unlike
[TRIGHT](TRIGHT.md): in SCREEN 5-8 it steps CLOC (the X) by - 1 and stops at CLOC 0; in SCREEN 2 it is
[LEFTC](LEFTC.md)'s multicolour step with a stop at a 256-byte row's first cell.

## The specification

**Interface.**
- No published entry at $00A9 [P TH A1 SUB-ROM, by absence]; the name and address are the C-BIOS
  peer's. A callable entry [M]: it changes CLOC / CMASK, A and F on all three references.
- Called through EXTROM, IX = $00A9 [P TH A1 SUB-ROM, preamble].
- There is no MSX1 main-ROM TLEFTC ([the MSX1 BIOS index](../../bios/index.md) has none), hence no TL-95 row.
- SCREEN 5-8 [M]: CLOC = 0 -> stop; otherwise CLOC - 1 (16 bits: $0100 -> $00FF, b66 / b67), CMASK kept and not
  read ($80 / $40 planted: b39, b40). (0, 3) stops and (5, 0) moves (b25, b26): the stop is X / CLOC 0, not Y 0;
  and CLOC $0100 moves, so the whole word is tested, not its low byte.
  Out on a move: A = the NEW CLOC's high byte ($00FF gives $00, $01FE gives $01: b66, a85); F = the flags of `or a` on the returned A (S, Z, P = parity, H = 0, N = 0, C = 0, bits 5 / 3 copied from A): $00 -> $44,
  $01 -> $00. The stop: CLOC / CMASK kept, A = $FF, F = $AD, the carry set (a45, b25).
- SCREEN 2 [M]: LEFTC's step (A = the new CMASK, `and a` flags), except that CMASK bit 7 set with CLOC's low byte
  < 8 (the - 8 would borrow out of the low byte) stops: $0000 / $F0, $0204 / $F0, $0300 / $F0, $0304 / $F0 stop
  (a13, b13, b57, b58); $0204 / $0F -> $0204 / $F0 (b68) and $0214 / $F0 -> $020C / $0F (b12) move. The stop:
  A = $00, F = $45, the carry set.
- The first draft's "where it does not stop, as LEFTC" holds in SCREEN 2 only.
- Registers [M] ([xsubmv2.asm](../../../probes/bios/spec/xsubmv2.asm), every record on all three references): BC, DE and HL come back as given
  ($B0C1 / $D0E1 / $4A5B) through EXTROM. IX / IY carry EXTROM's own inputs and are not measured. Called with
  interrupts off, it returns through EXTROM with them ON (IFF2 = 1) in 206 of the 207 reference records; the one 0
  (HB-F900 b8, reproduced by every `--fresh` run) is [A] the Z80's `ld a, i` reading 0 when an interrupt is
  accepted during it, not a different state. Whether the move or EXTROM enables them is not separated (TL-90).
- VDP registers and VRAM: recorded by neither probe -- "none touched" stays [A] (TL-94).
- The state of the runs [M] (b records): ACPAGE 0 unless a row says ACPAGE 1; RG9SAV ($FFE8) $82 in SCREEN 5-8
  and $02 in SCREEN 2 on the NMS 8250 (bit 1 = its PAL bit), $80 / $00 on the HB-F900 and FS-A1WSX -- LN = 1 (212
  lines) in SCREEN 5-8. The a records did not log them; they start from the same CHGMOD [A].
- The model B / model C rules this page stated before measuring ([the concept page](../concepts/graphics-cursor.md#the-cursor-model--rival-rules-to-separate))
  are both REFUTED for this entry [M]: MAPXYC leaves CLOC = X and CMASK = Y's low byte in SCREEN 5-8 (the
  "before" column), and the step below is neither model's.

**Measured** [M] -- the same on all three references except where a line names one. Records: `aN` = [xsubmv.asm](../../../probes/bios/spec/xsubmv.asm) record N, `bN` = [xsubmv2.asm](../../../probes/bios/spec/xsubmv2.asm) record N, both counted from 0 ([AE_xsubmv_msx2.out](../../../scratchpad/AE_xsubmv_msx2.out), [AE_xsubmv2_msx2.out](../../../scratchpad/AE_xsubmv2_msx2.out); decoded by `scratchpad/xsubmv_decode.py` and [xsubmv2_decode.py](../../../scratchpad/xsubmv2_decode.py)). The start is set by MAPXYC, or by hand where the row says "planted". SCREEN 6's X 511 rows were printed as (255, 20) in the first draft: the decoder keeps only X's low byte.

| SCREEN | (X, Y) | CLOC / CMASK before | after | A | F | carry | record |
|---|---|---|---|---|---|---|---|
| 2 | (10, 20) | $022C / $F0 | $0224 / $0F | $0F | $1C | 0 | a5 |
| 2 | (0, 0) | $0000 / $F0 | $0000 / $F0 | $00 | $45 | 1 | a13 |
| 2 | (255, 20) | $02FC / $0F | $02FC / $F0 | $F0 | $B4 | 0 | a21 |
| 2 | (10, 191) | $072F / $F0 | $0727 / $0F | $0F | $1C | 0 | a29 |
| 5 | (10, 20) | $000A / $14 | $0009 / $14 | $00 | $44 | 0 | a37 |
| 5 | (0, 0) | $0000 / $00 | $0000 / $00 | $FF | $AD | 1 | a45 |
| 5 | (255, 20) | $00FF / $14 | $00FE / $14 | $00 | $44 | 0 | a53 |
| 5 | (10, 211) | $000A / $D3 | $0009 / $D3 | $00 | $44 | 0 | a61 |
| 6 | (10, 20) | $000A / $14 | $0009 / $14 | $00 | $44 | 0 | a69 |
| 6 | (0, 0) | $0000 / $00 | $0000 / $00 | $FF | $AD | 1 | a77 |
| 6 | (511, 20) | $01FF / $14 | $01FE / $14 | $01 | $00 | 0 | a85 |
| 6 | (10, 211) | $000A / $D3 | $0009 / $D3 | $00 | $44 | 0 | a93 |
| 8 | (10, 20) | $000A / $14 | $0009 / $14 | $00 | $44 | 0 | a101 |
| 8 | (0, 0) | $0000 / $00 | $0000 / $00 | $FF | $AD | 1 | a109 |
| 8 | (255, 20) | $00FF / $14 | $00FE / $14 | $00 | $44 | 0 | a117 |
| 8 | (10, 211) | $000A / $D3 | $0009 / $D3 | $00 | $44 | 0 | a125 |
| 2 | (3, 20) | $020C / $0F | $020C / $F0 | $F0 | $B4 | 0 | b11 |
| 2 | (4, 20) | $0214 / $F0 | $020C / $0F | $0F | $1C | 0 | b12 |
| 2 | (0, 20) | $0204 / $F0 | $0204 / $F0 | $00 | $45 | 1 | b13 |
| 2 | planted | $0300 / $F0 | $0300 / $F0 | $00 | $45 | 1 | b57 |
| 2 | planted | $0304 / $F0 | $0304 / $F0 | $00 | $45 | 1 | b58 |
| 2 | planted | $0204 / $0F | $0204 / $F0 | $F0 | $B4 | 0 | b68 |
| 5 | (0, 3) | $0000 / $03 | $0000 / $03 | $FF | $AD | 1 | b25 |
| 5 | (5, 0) | $0005 / $00 | $0004 / $00 | $00 | $44 | 0 | b26 |
| 5 | planted | $000A / $80 | $0009 / $80 | $00 | $44 | 0 | b39 |
| 5 | planted | $000A / $40 | $0009 / $40 | $00 | $44 | 0 | b40 |
| 5 | planted | $0100 / $14 | $00FF / $14 | $00 | $44 | 0 | b66 |
| 6 | planted | $0100 / $14 | $00FF / $14 | $00 | $44 | 0 | b67 |

## Differences from the reference

C-BIOS's MSX2 / MSX2+ builds (the subject) do NOTHING here: CLOC / CMASK unchanged, A as the caller left it
($A7), the carry never set, in every case and mode ([AE_xsubmv_msx2.out](../../../scratchpad/AE_xsubmv_msx2.out), [AE_xsubmv2_msx2.out](../../../scratchpad/AE_xsubmv2_msx2.out)).

## Open (not measured)

The sets [PG], [LN], [MD], [SN] and [R9] are defined on [the concept page](../concepts/graphics-cursor.md#shared-measurement-setup-every-pages-matrix-assumes-it).

Every case runs on all three references; each machine's result is recorded on its own, and a rule that holds on one generation only names it ([the concept page](../concepts/graphics-cursor.md)). `—` = not measured yet; `n/a` = the mode does not exist on that machine.

| case | inputs | state | what it separates | HB-F900 | NMS 8250 | FS-A1WSX |
|---|---|---|---|---|---|---|
| TL-90 | entry A / F $00 and $FF; IX / IY; called with interrupts ON | SCREEN 2, 5 | whether A / F on entry matter; who enables the interrupts | — | — | — |
| TL-91 | CLOC / CMASK from MAPXYC | SCRMOD 3, 4, 7; [MD] | which branch SCREEN 3 / 4 / 7 take | — | — | — |
| TL-92 | CLOC / CMASK from MAPXYC | SCRMOD 10-12 (FS-A1WSX) | the step in the YJK modes | n/a | n/a | — |
| TL-93 | CLOC $8000, $0000 / CMASK $14 planted by hand | [PG] in SCREEN 5 / 6, ACPAGE 0 and 1 | the CLOC = 0 stop with a page bit set ($8000 moves to $7FFF?) | — | — | — |
| TL-94 | a step from MAPXYC (100, 50) | SCREEN 5; [SN] | RAM other than CLOC / CMASK, VRAM, the VDP registers and S#n unchanged | — | — | — |

## Related pages

[The concept page](../concepts/graphics-cursor.md); the MSX1 [LEFTC](../../bios/LEFTC.md) (the unchecked move); the other sub-ROM moves
[RIGHTC](RIGHTC.md), [LEFTC](LEFTC.md), [UPC](UPC.md), [DOWNC](DOWNC.md), [TUPC](TUPC.md), [TDOWNC](TDOWNC.md), [TRIGHT](TRIGHT.md); [MAPXYC](MAPXYC.md).

## Tests that cover it

None yet.
