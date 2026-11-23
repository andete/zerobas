<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `TDOWNC` (sub-ROM $00B1) — move the graphics position down, checking the edge

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the HB-F900, NMS 8250 and FS-A1WSX ([xsubmv.asm](../../../probes/bios/spec/xsubmv.asm), [scratchpad/AE_xsubmv_msx2.out](../../../scratchpad/AE_xsubmv_msx2.out), decoded by `scratchpad/xsubmv_decode.py`).
>
> Goldfish pass 1 (test writer) 2026-11-23: 18 findings, 11 measured, 2 moved to open (the separating cases in [xsubmv2.asm](../../../probes/bios/spec/xsubmv2.asm), [AE_xsubmv2_msx2.out](../../../scratchpad/AE_xsubmv2_msx2.out)).

## Summary

`TDOWNC` (the C-BIOS peer's name; no published entry) is NOT "[DOWNC](DOWNC.md) with a stop" in the bitmap
modes: in SCREEN 5-8 it steps CMASK (the Y) by + 1 and stops at Y >= 211, a fixed bound that ignores R#9 and
ACPAGE; in SCREEN 2 it is DOWNC's step with a stop where a row step would reach CLOC $0600.

## The specification

**Interface.**
- No published entry at $00B1 [P TH A1 SUB-ROM, by absence]; the name and address are the C-BIOS
  peer's. A callable entry [M]: it changes CLOC / CMASK, A and F on all three references.
- Called through EXTROM, IX = $00B1 [P TH A1 SUB-ROM, preamble].
- SCREEN 5-8 [M]: CMASK >= 211 ($D3) -> stop; otherwise CMASK + 1, CLOC kept. 190 -> 191, 191 -> 192 and
  210 -> 211 move (b15-b17; SCREEN 6 b45, SCREEN 8 b47 / b48); 211, and planted 212 and 255, stop (b14, b49, b50):
  a ">= 211" test, not "= 211" and not 191. Only CMASK is read.
- The bound is fixed [M]: with R#9 LN = 0 (192 lines; RG9SAV $00 / $02) it still moves at 191 and stops at 211
  (b18-b20); ACPAGE 1 changes nothing (b21).
- Out on a SCREEN 5-8 move [M]: A = the new CMASK; F = the flags of `and a` on the returned A (S, Z, P = parity, H = 1, N = 0, C = 0, bits 5 / 3 copied from A): $BF -> $B8, $C0 -> $94, $D3 -> $90, $08 -> $18.
- The SCREEN 5-8 stop [M]: CLOC / CMASK kept, A = CMASK (the Y, unchanged), the carry set; F = $41 at $D3 (b14,
  b46 -- SCREEN 8 re-measured, see below), $01 at $D4 (b49), and at $FF $29 on the NMS 8250 and HB-F900 but $09 on
  the FS-A1WSX (b50) -- the references disagree in bit 5. The F rule above 212 is not pinned (TD-07).
- SCREEN 2 [M]: DOWNC's step (A = the new CLOC AND 7, `and a` flags), except that a row step whose result would
  be $0600 or more stops: CLOC AND 7 = 7 with CLOC >= $0500 -- $052F, $062F, $072F, $07FF, $0F2F stop (b64, b52,
  b3 / b51, b4, b53); $002F -> $0128, $012F -> $0228, $042F -> $0528 move (b59 / b61, b60, b65). Inside a cell it
  moves at any high byte ($0728 -> $0729, b0). The bound is not "Y 191": (10, 7) and (10, 15) cross rows (b59, b60).
- The SCREEN 2 stop [M]: CLOC / CMASK kept, A = $00, F = $45, the carry set.
- SCREEN 8 (10, 211) [M]: a stop, A = $D3, F = $41, carry 1 (b46). The first draft's row for it came from a
  truncated record (a127: `@caplen 0600` ended at its A byte; the decoder padded with zeros) and is withdrawn.
- Registers [M] ([xsubmv2.asm](../../../probes/bios/spec/xsubmv2.asm), every record on all three references): BC, DE and HL come back as given
  ($B0C1 / $D0E1 / $4A5B) through EXTROM. IX / IY carry EXTROM's own inputs and are not measured. Called with
  interrupts off, it returns through EXTROM with them ON (IFF2 = 1) in 206 of the 207 reference records; the one 0
  (HB-F900 b8, reproduced by every `--fresh` run) is [A] the Z80's `ld a, i` reading 0 when an interrupt is
  accepted during it, not a different state. Whether the move or EXTROM enables them is not separated (TD-90).
- VDP registers and VRAM: recorded by neither probe -- "none touched" stays [A] (TD-94).
- The state of the runs [M] (b records): ACPAGE 0 unless a row says ACPAGE 1; RG9SAV ($FFE8) $82 in SCREEN 5-8
  and $02 in SCREEN 2 on the NMS 8250 (bit 1 = its PAL bit), $80 / $00 on the HB-F900 and FS-A1WSX -- LN = 1 (212
  lines) in SCREEN 5-8. The a records did not log them; they start from the same CHGMOD [A].
- The model B / model C rules this page stated before measuring ([the concept page](../concepts/graphics-cursor.md#the-cursor-model--rival-rules-to-separate))
  are both REFUTED for this entry [M]: MAPXYC leaves CLOC = X and CMASK = Y's low byte in SCREEN 5-8 (the
  "before" column), and the step below is neither model's.

**Measured** [M] -- the same on all three references except where a line names one. Records: `aN` = [xsubmv.asm](../../../probes/bios/spec/xsubmv.asm) record N, `bN` = [xsubmv2.asm](../../../probes/bios/spec/xsubmv2.asm) record N, both counted from 0 ([AE_xsubmv_msx2.out](../../../scratchpad/AE_xsubmv_msx2.out), [AE_xsubmv2_msx2.out](../../../scratchpad/AE_xsubmv2_msx2.out); decoded by `scratchpad/xsubmv_decode.py` and [xsubmv2_decode.py](../../../scratchpad/xsubmv2_decode.py)). The start is set by MAPXYC, or by hand where the row says "planted". SCREEN 6's X 511 rows were printed as (255, 20) in the first draft: the decoder keeps only X's low byte.

| SCREEN | (X, Y) | CLOC / CMASK before | after | A | F | carry | record |
|---|---|---|---|---|---|---|---|
| 2 | (10, 20) | $022C / $F0 | $022D / $F0 | $05 | $14 | 0 | a7 |
| 2 | (0, 0) | $0000 / $F0 | $0001 / $F0 | $01 | $10 | 0 | a15 |
| 2 | (255, 20) | $02FC / $0F | $02FD / $0F | $05 | $14 | 0 | a23 |
| 2 | (10, 191) | $072F / $F0 | $072F / $F0 | $00 | $45 | 1 | a31 |
| 5 | (10, 20) | $000A / $14 | $000A / $15 | $15 | $10 | 0 | a39 |
| 5 | (0, 0) | $0000 / $00 | $0000 / $01 | $01 | $10 | 0 | a47 |
| 5 | (255, 20) | $00FF / $14 | $00FF / $15 | $15 | $10 | 0 | a55 |
| 5 | (10, 211) | $000A / $D3 | $000A / $D3 | $D3 | $41 | 1 | a63 |
| 6 | (10, 20) | $000A / $14 | $000A / $15 | $15 | $10 | 0 | a71 |
| 6 | (0, 0) | $0000 / $00 | $0000 / $01 | $01 | $10 | 0 | a79 |
| 6 | (511, 20) | $01FF / $14 | $01FF / $15 | $15 | $10 | 0 | a87 |
| 6 | (10, 211) | $000A / $D3 | $000A / $D3 | $D3 | $41 | 1 | a95 |
| 8 | (10, 20) | $000A / $14 | $000A / $15 | $15 | $10 | 0 | a103 |
| 8 | (0, 0) | $0000 / $00 | $0000 / $01 | $01 | $10 | 0 | a111 |
| 8 | (255, 20) | $00FF / $14 | $00FF / $15 | $15 | $10 | 0 | a119 |
| 2 | (10, 184) | $0728 / $F0 | $0729 / $F0 | $01 | $10 | 0 | b0 |
| 2 | (10, 188) | $072C / $F0 | $072D / $F0 | $05 | $14 | 0 | b1 |
| 2 | (10, 190) | $072E / $F0 | $072F / $F0 | $07 | $10 | 0 | b2 |
| 2 | (10, 191) | $072F / $F0 | $072F / $F0 | $00 | $45 | 1 | b3 |
| 2 | (255, 191) | $07FF / $0F | $07FF / $0F | $00 | $45 | 1 | b4 |
| 2 | planted | $072F / $F0 | $072F / $F0 | $00 | $45 | 1 | b51 |
| 2 | planted | $062F / $F0 | $062F / $F0 | $00 | $45 | 1 | b52 |
| 2 | planted | $0F2F / $F0 | $0F2F / $F0 | $00 | $45 | 1 | b53 |
| 2 | (10, 7) | $002F / $F0 | $0128 / $F0 | $00 | $54 | 0 | b59 |
| 2 | (10, 15) | $012F / $F0 | $0228 / $F0 | $00 | $54 | 0 | b60 |
| 2 | planted | $002F / $F0 | $0128 / $F0 | $00 | $54 | 0 | b61 |
| 2 | planted | $002E / $F0 | $002F / $F0 | $07 | $10 | 0 | b62 |
| 2 | planted | $052F / $F0 | $052F / $F0 | $00 | $45 | 1 | b64 |
| 2 | planted | $042F / $F0 | $0528 / $F0 | $00 | $54 | 0 | b65 |
| 5 | (10, 211) | $000A / $D3 | $000A / $D3 | $D3 | $41 | 1 | b14 |
| 5 | (10, 190) | $000A / $BE | $000A / $BF | $BF | $B8 | 0 | b15 |
| 5 | (10, 191) | $000A / $BF | $000A / $C0 | $C0 | $94 | 0 | b16 |
| 5 | (10, 210) | $000A / $D2 | $000A / $D3 | $D3 | $90 | 0 | b17 |
| 5 | (10, 190) LN 0 | $000A / $BE | $000A / $BF | $BF | $B8 | 0 | b18 |
| 5 | (10, 191) LN 0 | $000A / $BF | $000A / $C0 | $C0 | $94 | 0 | b19 |
| 5 | (10, 211) LN 0 | $000A / $D3 | $000A / $D3 | $D3 | $41 | 1 | b20 |
| 5 | (10, 211) ACPAGE 1 | $000A / $D3 | $000A / $D3 | $D3 | $41 | 1 | b21 |
| 5 | planted | $000A / $D4 | $000A / $D4 | $D4 | $01 | 1 | b49 |
| 5 | planted | $000A / $FF | $000A / $FF | $FF | $29 | 1 | b50 |
| 5 | (10, 7) | $000A / $07 | $000A / $08 | $08 | $18 | 0 | b63 |
| 6 | (10, 191) | $000A / $BF | $000A / $C0 | $C0 | $94 | 0 | b45 |
| 8 | (10, 211) | $000A / $D3 | $000A / $D3 | $D3 | $41 | 1 | b46 |
| 8 | (10, 191) | $000A / $BF | $000A / $C0 | $C0 | $94 | 0 | b47 |
| 8 | (10, 210) | $000A / $D2 | $000A / $D3 | $D3 | $90 | 0 | b48 |

## Differences from the reference

C-BIOS's MSX2 / MSX2+ builds differ only at the SCREEN 2 stop: they move on ($072F -> $0828, $07FF -> $08F8,
$052F -> $0628 ...) where the references stop with the carry set -- a31, b3, b4, b51-b53, b64. In [xsubmv.asm](../../../probes/bios/spec/xsubmv.asm) that is 1
of the 15 cases captured (its 16th, SCREEN 8 (10, 211), lost its F byte to the capture length on both sides; b46
re-measures it: equal). SCREEN 5-8, the >= 211 stop with its A included, are equal; at planted CMASK $FF C-BIOS
gives F $29, which matches the NMS 8250 / HB-F900 but not the FS-A1WSX's $09 (b50) ([AE_xsubmv_msx2.out](../../../scratchpad/AE_xsubmv_msx2.out), [AE_xsubmv2_msx2.out](../../../scratchpad/AE_xsubmv2_msx2.out)).

## Open (not measured)

The sets [PG], [LN], [MD], [SN] and [R9] are defined on [the concept page](../concepts/graphics-cursor.md#shared-measurement-setup-every-pages-matrix-assumes-it).

Every case runs on all three references; each machine's result is recorded on its own, and a rule that holds on one generation only names it ([the concept page](../concepts/graphics-cursor.md)). `—` = not measured yet; `n/a` = the mode does not exist on that machine.

| case | inputs | state | what it separates | HB-F900 | NMS 8250 | FS-A1WSX |
|---|---|---|---|---|---|---|
| TD-07 | CMASK $D5, $E0, $F0, $FE planted | SCREEN 5 | the stop's F above 212 ($01 at $D4, $29 / $09 at $FF): which flags it keeps | — | — | — |
| TD-90 | entry A / F $00 and $FF; IX / IY; called with interrupts ON | SCREEN 2, 5 | whether A / F on entry matter (the stop's F); who enables the interrupts | — | — | — |
| TD-91 | CLOC / CMASK from MAPXYC | SCRMOD 3, 4, 7; [MD] | which branch SCREEN 3 / 4 / 7 take, and the SCREEN 3 bound | — | — | — |
| TD-92 | CLOC / CMASK from MAPXYC | SCRMOD 10-12 (FS-A1WSX) | the step and the bound in the YJK modes | n/a | n/a | — |
| TD-93 | CLOC $8005 / CMASK $D2, $D3 planted by hand | [PG] in SCREEN 5 / 6, ACPAGE 0 and 1 | CLOC not read with a page bit set | — | — | — |
| TD-94 | a step from MAPXYC (100, 50) | SCREEN 5; [SN] | RAM other than CLOC / CMASK, VRAM, the VDP registers and S#n unchanged | — | — | — |
| TD-95 | MAPXYC (10, 210), (10, 211) | SCREEN 5, called at the main-ROM TDOWNC ($010B) | the main entry forwards to this step vs does its own | — | — | — |

## Related pages

[The concept page](../concepts/graphics-cursor.md); the MSX1 [TDOWNC](../../bios/TDOWNC.md); the other sub-ROM moves
[RIGHTC](RIGHTC.md), [LEFTC](LEFTC.md), [UPC](UPC.md), [DOWNC](DOWNC.md), [TUPC](TUPC.md), [TRIGHT](TRIGHT.md), [TLEFTC](TLEFTC.md); [MAPXYC](MAPXYC.md).

## Tests that cover it

None yet.
