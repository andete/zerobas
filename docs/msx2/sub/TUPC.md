<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `TUPC` (sub-ROM $00B9) — move the graphics position up, checking the edge

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the HB-F900, NMS 8250 and FS-A1WSX ([xsubmv.asm](../../../probes/bios/spec/xsubmv.asm), [scratchpad/AE_xsubmv_msx2.out](../../../scratchpad/AE_xsubmv_msx2.out), decoded by `scratchpad/xsubmv_decode.py`).
>
> Goldfish pass 1 (test writer) 2026-11-23: 12 findings, 8 measured, 1 moved to open (the separating cases in [xsubmv2.asm](../../../probes/bios/spec/xsubmv2.asm), [AE_xsubmv2_msx2.out](../../../scratchpad/AE_xsubmv2_msx2.out)).

## Summary

`TUPC` (the C-BIOS peer's name; no published entry) is NOT "[UPC](UPC.md) with a stop" in the bitmap modes:
in SCREEN 5-8 it steps CMASK (the Y) by - 1 and stops at Y 0; in SCREEN 2 it is UPC's step with a stop at the top
256-byte row. So, unlike UPC, it reads SCRMOD.

## The specification

**Interface.**
- No published entry at $00B9 [P TH A1 SUB-ROM, by absence]; the name and address are the C-BIOS
  peer's. A callable entry [M]: it changes CLOC / CMASK, A and F on all three references.
- Called through EXTROM, IX = $00B9 [P TH A1 SUB-ROM, preamble].
- SCREEN 5-8 [M]: CMASK = 0 -> stop; otherwise CMASK - 1, CLOC kept. Only CMASK is read: (10, 0) stops and
  (0, 3) moves (b22, b23), so the stop is Y 0, not X 0 or CLOC 0. ACPAGE 1 changes nothing (b24).
  Out on a move: A = the new CMASK; F = the flags of `or a` on the returned A (S, Z, P = parity, H = 0, N = 0, C = 0, bits 5 / 3 copied from A): $13 -> $00, $02 -> $00, $D2 -> $84.
- SCREEN 2 [M]: UPC's step (A = the old CLOC AND 7, `and a` flags), except that CLOC AND 7 = 0 with CLOC's high
  byte 0 stops: $0000, $0010, $0020 stop (a14, b6, b5); $0100 -> $0007 and $0300 -> $0207 move (b54, b55);
  $0004 -> $0003 (b7). The test is the high byte, not "CLOC = 0".
- The stop [M], every mode: CLOC / CMASK kept, A = $00, F = $45 (Z, P, C), the carry set.
- Where it moves the carry is clear [M].
- Registers [M] ([xsubmv2.asm](../../../probes/bios/spec/xsubmv2.asm), every record on all three references): BC, DE and HL come back as given
  ($B0C1 / $D0E1 / $4A5B) through EXTROM. IX / IY carry EXTROM's own inputs and are not measured. Called with
  interrupts off, it returns through EXTROM with them ON (IFF2 = 1) in 206 of the 207 reference records; the one 0
  (HB-F900 b8, reproduced by every `--fresh` run) is [A] the Z80's `ld a, i` reading 0 when an interrupt is
  accepted during it, not a different state. Whether the move or EXTROM enables them is not separated (TU-90).
- VDP registers and VRAM: recorded by neither probe -- "none touched" stays [A] (TU-94).
- The state of the runs [M] (b records): ACPAGE 0 unless a row says ACPAGE 1; RG9SAV ($FFE8) $82 in SCREEN 5-8
  and $02 in SCREEN 2 on the NMS 8250 (bit 1 = its PAL bit), $80 / $00 on the HB-F900 and FS-A1WSX -- LN = 1 (212
  lines) in SCREEN 5-8. The a records did not log them; they start from the same CHGMOD [A].
- The model B / model C rules this page stated before measuring ([the concept page](../concepts/graphics-cursor.md#the-cursor-model--rival-rules-to-separate))
  are both REFUTED for this entry [M]: MAPXYC leaves CLOC = X and CMASK = Y's low byte in SCREEN 5-8 (the
  "before" column), and the step below is neither model's.

**Measured** [M] -- the same on all three references except where a line names one. Records: `aN` = [xsubmv.asm](../../../probes/bios/spec/xsubmv.asm) record N, `bN` = [xsubmv2.asm](../../../probes/bios/spec/xsubmv2.asm) record N, both counted from 0 ([AE_xsubmv_msx2.out](../../../scratchpad/AE_xsubmv_msx2.out), [AE_xsubmv2_msx2.out](../../../scratchpad/AE_xsubmv2_msx2.out); decoded by `scratchpad/xsubmv_decode.py` and [xsubmv2_decode.py](../../../scratchpad/xsubmv2_decode.py)). The start is set by MAPXYC, or by hand where the row says "planted". SCREEN 6's X 511 rows were printed as (255, 20) in the first draft: the decoder keeps only X's low byte.

| SCREEN | (X, Y) | CLOC / CMASK before | after | A | F | carry | record |
|---|---|---|---|---|---|---|---|
| 2 | (10, 20) | $022C / $F0 | $022B / $F0 | $04 | $10 | 0 | a6 |
| 2 | (0, 0) | $0000 / $F0 | $0000 / $F0 | $00 | $45 | 1 | a14 |
| 2 | (255, 20) | $02FC / $0F | $02FB / $0F | $04 | $10 | 0 | a22 |
| 2 | (10, 191) | $072F / $F0 | $072E / $F0 | $07 | $10 | 0 | a30 |
| 5 | (10, 20) | $000A / $14 | $000A / $13 | $13 | $00 | 0 | a38 |
| 5 | (0, 0) | $0000 / $00 | $0000 / $00 | $00 | $45 | 1 | a46 |
| 5 | (255, 20) | $00FF / $14 | $00FF / $13 | $13 | $00 | 0 | a54 |
| 5 | (10, 211) | $000A / $D3 | $000A / $D2 | $D2 | $84 | 0 | a62 |
| 6 | (10, 20) | $000A / $14 | $000A / $13 | $13 | $00 | 0 | a70 |
| 6 | (0, 0) | $0000 / $00 | $0000 / $00 | $00 | $45 | 1 | a78 |
| 6 | (511, 20) | $01FF / $14 | $01FF / $13 | $13 | $00 | 0 | a86 |
| 6 | (10, 211) | $000A / $D3 | $000A / $D2 | $D2 | $84 | 0 | a94 |
| 8 | (10, 20) | $000A / $14 | $000A / $13 | $13 | $00 | 0 | a102 |
| 8 | (0, 0) | $0000 / $00 | $0000 / $00 | $00 | $45 | 1 | a110 |
| 8 | (255, 20) | $00FF / $14 | $00FF / $13 | $13 | $00 | 0 | a118 |
| 8 | (10, 211) | $000A / $D3 | $000A / $D2 | $D2 | $84 | 0 | a126 |
| 2 | (8, 0) | $0020 / $F0 | $0020 / $F0 | $00 | $45 | 1 | b5 |
| 2 | (4, 0) | $0010 / $F0 | $0010 / $F0 | $00 | $45 | 1 | b6 |
| 2 | (0, 4) | $0004 / $F0 | $0003 / $F0 | $04 | $10 | 0 | b7 |
| 2 | planted | $0100 / $F0 | $0007 / $F0 | $00 | $54 | 0 | b54 |
| 2 | planted | $0300 / $F0 | $0207 / $F0 | $00 | $54 | 0 | b55 |
| 5 | (10, 0) | $000A / $00 | $000A / $00 | $00 | $45 | 1 | b22 |
| 5 | (0, 3) | $0000 / $03 | $0000 / $02 | $02 | $00 | 0 | b23 |
| 5 | (10, 0) ACPAGE 1 | $000A / $00 | $000A / $00 | $00 | $45 | 1 | b24 |

## Differences from the reference

C-BIOS's MSX2 / MSX2+ builds give the same CLOC / CMASK / A / F in every case, the b records included
([AE_xsubmv_msx2.out](../../../scratchpad/AE_xsubmv_msx2.out), [AE_xsubmv2_msx2.out](../../../scratchpad/AE_xsubmv2_msx2.out)).

## On the turbo R

Measured 2026-11-23 (D-TRSPEC) on the FS-A1GT / FS-A1ST: every case gives the same bytes as on the FS-A1WSX, on both models [M] ([AE_trall/xsubmv.out](../../../scratchpad/AE_trall/xsubmv.out), [AE_trall/xsubmv2.out](../../../scratchpad/AE_trall/xsubmv2.out); overview: [turbor/remeasured.md](../../turbor/remeasured.md)).

## Open (not measured)

The sets [PG], [LN], [MD], [SN] and [R9] are defined on [the concept page](../concepts/graphics-cursor.md#shared-measurement-setup-every-pages-matrix-assumes-it).

Every case runs on all three references; each machine's result is recorded on its own, and a rule that holds on one generation only names it ([the concept page](../concepts/graphics-cursor.md)). `—` = not measured yet; `n/a` = the mode does not exist on that machine.

| case | inputs | state | what it separates | HB-F900 | NMS 8250 | FS-A1WSX |
|---|---|---|---|---|---|---|
| TU-90 | entry A / F $00 and $FF; IX / IY; called with interrupts ON | SCREEN 2, 5 | whether A / F on entry matter; who enables the interrupts | — | — | — |
| TU-91 | CLOC / CMASK from MAPXYC | SCRMOD 3, 4, 7; [MD] | which branch SCREEN 3 / 4 / 7 take (the SCREEN 2 one or the Y one) | — | — | — |
| TU-92 | CLOC / CMASK from MAPXYC | SCRMOD 10-12 (FS-A1WSX) | the step in the YJK modes | n/a | n/a | — |
| TU-93 | CLOC $8005 / CMASK $00 and $01 planted by hand | [PG] in SCREEN 5 / 6, ACPAGE 0 and 1 | CLOC not read with a page bit set; the stop still Y 0 | — | — | — |
| TU-94 | a step from MAPXYC (100, 50) | SCREEN 5; [SN] | RAM other than CLOC / CMASK, VRAM, the VDP registers and S#n unchanged | — | — | — |
| TU-95 | MAPXYC (10, 1), (10, 0) | SCREEN 5, called at the main-ROM TUPC ($0105) | the main entry forwards to this step vs does its own | — | — | — |

## Related pages

[The concept page](../concepts/graphics-cursor.md); the MSX1 [TUPC](../../bios/TUPC.md); the other sub-ROM moves
[RIGHTC](RIGHTC.md), [LEFTC](LEFTC.md), [UPC](UPC.md), [DOWNC](DOWNC.md), [TDOWNC](TDOWNC.md), [TRIGHT](TRIGHT.md), [TLEFTC](TLEFTC.md); [MAPXYC](MAPXYC.md).

## Tests that cover it

None yet.
