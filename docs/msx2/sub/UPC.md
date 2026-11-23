<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `UPC` (sub-ROM $00BD) — move the graphics position one pixel up

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the HB-F900, NMS 8250 and FS-A1WSX ([xsubmv.asm](../../../probes/bios/spec/xsubmv.asm), [scratchpad/AE_xsubmv_msx2.out](../../../scratchpad/AE_xsubmv_msx2.out), decoded by `scratchpad/xsubmv_decode.py`).
>
> Goldfish pass 1 (test writer) 2026-11-23: 11 findings, 6 measured, 1 moved to open (the separating cases in [xsubmv2.asm](../../../probes/bios/spec/xsubmv2.asm), [AE_xsubmv2_msx2.out](../../../scratchpad/AE_xsubmv2_msx2.out)).

## Summary

`UPC` (the C-BIOS peer's name; no published entry) does the MSX1 [UPC](../../bios/UPC.md) arithmetic in
every mode measured (SCREEN 2, 5, 6, 8; SCRMOD not read): CLOC - 1 within an 8-byte cell, the previous 256-byte
row at a cell's top. CMASK is not touched. In SCREEN 5-8, where CLOC holds X, that is not one line up.

## The specification

**Interface.**
- No published entry at $00BD [P TH A1 SUB-ROM, by absence]; the name and address are the C-BIOS
  peer's. A callable entry [M]: it changes CLOC / CMASK, A and F on all three references.
- Called through EXTROM, IX = $00BD [P TH A1 SUB-ROM, preamble].
- The step [M]: CLOC AND 7 /= 0 -> CLOC - 1; CLOC AND 7 = 0 -> CLOC - $F9 (up a 256-byte row, + 7). $0000 ->
  $FF07 (a10, a42), $0008 -> $FF0F (b41), $0010 -> $FF17 (b42): the - $F9 branch is pinned away from CLOC 0.
  CMASK kept and not read.
- No edge check [M]: from CLOC < 8 it wraps to $FFxx.
- Out [M]: A = the OLD CLOC AND 7 (0 on the - $F9 branch); F = the flags of `and a` on the returned A (S, Z, P = parity, H = 1, N = 0, C = 0, bits 5 / 3 copied from A): $00 -> $54, $02 / $04 / $07 -> $10. The
  carry is always clear.
- In SCREEN 5-8 (CLOC = X): X - 1 only when X AND 7 /= 0; X 0, 8, 16 ... go to $FF07, $FF0F, $FF17 ...
- Registers [M] ([xsubmv2.asm](../../../probes/bios/spec/xsubmv2.asm), every record on all three references): BC, DE and HL come back as given
  ($B0C1 / $D0E1 / $4A5B) through EXTROM. IX / IY carry EXTROM's own inputs and are not measured. Called with
  interrupts off, it returns through EXTROM with them ON (IFF2 = 1) in 206 of the 207 reference records; the one 0
  (HB-F900 b8, reproduced by every `--fresh` run) is [A] the Z80's `ld a, i` reading 0 when an interrupt is
  accepted during it, not a different state. Whether the move or EXTROM enables them is not separated (UC-90).
- VDP registers and VRAM: recorded by neither probe -- "none touched" stays [A] (UC-94).
- The state of the runs [M] (b records): ACPAGE 0 unless a row says ACPAGE 1; RG9SAV ($FFE8) $82 in SCREEN 5-8
  and $02 in SCREEN 2 on the NMS 8250 (bit 1 = its PAL bit), $80 / $00 on the HB-F900 and FS-A1WSX -- LN = 1 (212
  lines) in SCREEN 5-8. The a records did not log them; they start from the same CHGMOD [A].
- The model B / model C rules this page stated before measuring ([the concept page](../concepts/graphics-cursor.md#the-cursor-model--rival-rules-to-separate))
  are both REFUTED for this entry [M]: MAPXYC leaves CLOC = X and CMASK = Y's low byte in SCREEN 5-8 (the
  "before" column), and the step below is neither model's.

**Measured** [M] -- the same on all three references except where a line names one. Records: `aN` = [xsubmv.asm](../../../probes/bios/spec/xsubmv.asm) record N, `bN` = [xsubmv2.asm](../../../probes/bios/spec/xsubmv2.asm) record N, both counted from 0 ([AE_xsubmv_msx2.out](../../../scratchpad/AE_xsubmv_msx2.out), [AE_xsubmv2_msx2.out](../../../scratchpad/AE_xsubmv2_msx2.out); decoded by `scratchpad/xsubmv_decode.py` and [xsubmv2_decode.py](../../../scratchpad/xsubmv2_decode.py)). The start is set by MAPXYC, or by hand where the row says "planted". SCREEN 6's X 511 rows were printed as (255, 20) in the first draft: the decoder keeps only X's low byte.

| SCREEN | (X, Y) | CLOC / CMASK before | after | A | F | carry | record |
|---|---|---|---|---|---|---|---|
| 2 | (10, 20) | $022C / $F0 | $022B / $F0 | $04 | $10 | 0 | a2 |
| 2 | (0, 0) | $0000 / $F0 | $FF07 / $F0 | $00 | $54 | 0 | a10 |
| 2 | (255, 20) | $02FC / $0F | $02FB / $0F | $04 | $10 | 0 | a18 |
| 2 | (10, 191) | $072F / $F0 | $072E / $F0 | $07 | $10 | 0 | a26 |
| 5 | (10, 20) | $000A / $14 | $0009 / $14 | $02 | $10 | 0 | a34 |
| 5 | (0, 0) | $0000 / $00 | $FF07 / $00 | $00 | $54 | 0 | a42 |
| 5 | (255, 20) | $00FF / $14 | $00FE / $14 | $07 | $10 | 0 | a50 |
| 5 | (10, 211) | $000A / $D3 | $0009 / $D3 | $02 | $10 | 0 | a58 |
| 6 | (10, 20) | $000A / $14 | $0009 / $14 | $02 | $10 | 0 | a66 |
| 6 | (0, 0) | $0000 / $00 | $FF07 / $00 | $00 | $54 | 0 | a74 |
| 6 | (511, 20) | $01FF / $14 | $01FE / $14 | $07 | $10 | 0 | a82 |
| 6 | (10, 211) | $000A / $D3 | $0009 / $D3 | $02 | $10 | 0 | a90 |
| 8 | (10, 20) | $000A / $14 | $0009 / $14 | $02 | $10 | 0 | a98 |
| 8 | (0, 0) | $0000 / $00 | $FF07 / $00 | $00 | $54 | 0 | a106 |
| 8 | (255, 20) | $00FF / $14 | $00FE / $14 | $07 | $10 | 0 | a114 |
| 8 | (10, 211) | $000A / $D3 | $0009 / $D3 | $02 | $10 | 0 | a122 |
| 5 | (8, 20) | $0008 / $14 | $FF0F / $14 | $00 | $54 | 0 | b41 |
| 5 | (16, 20) | $0010 / $14 | $FF17 / $14 | $00 | $54 | 0 | b42 |

## Differences from the reference

C-BIOS's MSX2 / MSX2+ builds give the same CLOC / CMASK / A / F in every case, b41 and b42 included
([AE_xsubmv_msx2.out](../../../scratchpad/AE_xsubmv_msx2.out), [AE_xsubmv2_msx2.out](../../../scratchpad/AE_xsubmv2_msx2.out)).

## On the turbo R

Measured 2026-11-23 (D-TRSPEC) on the FS-A1GT / FS-A1ST: every case gives the same bytes as on the FS-A1WSX, on both models [M] ([AE_trall/xsubmv.out](../../../scratchpad/AE_trall/xsubmv.out), [AE_trall/xsubmv2.out](../../../scratchpad/AE_trall/xsubmv2.out); overview: [turbor/remeasured.md](../../turbor/remeasured.md)).

## Open (not measured)

The sets [PG], [LN], [MD], [SN] and [R9] are defined on [the concept page](../concepts/graphics-cursor.md#shared-measurement-setup-every-pages-matrix-assumes-it).

Every case runs on all three references; each machine's result is recorded on its own, and a rule that holds on one generation only names it ([the concept page](../concepts/graphics-cursor.md)). `—` = not measured yet; `n/a` = the mode does not exist on that machine.

| case | inputs | state | what it separates | HB-F900 | NMS 8250 | FS-A1WSX |
|---|---|---|---|---|---|---|
| UC-90 | entry A / F $00 and $FF; IX / IY; called with interrupts ON | SCREEN 2, 5 | whether A / F on entry matter; who enables the interrupts | — | — | — |
| UC-91 | CLOC / CMASK from MAPXYC | SCRMOD 3, 4, 7; [MD] | SCREEN 7 and the MSX1 modes 3 / 4: the same SCRMOD-blind step? | — | — | — |
| UC-92 | CLOC / CMASK from MAPXYC | SCRMOD 10-12 (FS-A1WSX) | the step in the YJK modes | n/a | n/a | — |
| UC-93 | CLOC $8000 and $8005 / CMASK $14 planted by hand | [PG] in SCREEN 5 / 6 | the - $F9 branch across $8000 ($7F07?) and with ACPAGE set | — | — | — |
| UC-94 | a step from MAPXYC (100, 50) | SCREEN 5; [SN] | RAM other than CLOC / CMASK, VRAM, the VDP registers and S#n unchanged | — | — | — |
| UC-95 | MAPXYC (10, 20) | SCREEN 5, called at the main-ROM UPC ($0102) | the main entry forwards to this step vs does its own | — | — | — |

## Related pages

[The concept page](../concepts/graphics-cursor.md); the MSX1 [UPC](../../bios/UPC.md); the other sub-ROM moves
[RIGHTC](RIGHTC.md), [LEFTC](LEFTC.md), [DOWNC](DOWNC.md), [TUPC](TUPC.md), [TDOWNC](TDOWNC.md), [TRIGHT](TRIGHT.md), [TLEFTC](TLEFTC.md); [MAPXYC](MAPXYC.md).

## Tests that cover it

None yet.
