<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `CHGMOD` (sub-ROM $00D1) — change the screen mode

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the HB-F900, NMS 8250 and FS-A1WSX ([xmode.asm](../../../probes/bios/spec/xmode.asm), [scratchpad/AE_xmode_msx2.out](../../../scratchpad/AE_xmode_msx2.out), decoded by [scratchpad/xmode_decode.py](../../../scratchpad/xmode_decode.py) into [scratchpad/AE_xmode_msx2_decoded.out](../../../scratchpad/AE_xmode_msx2_decoded.out); round 2 [xmode2.asm](../../../probes/bios/spec/xmode2.asm), [scratchpad/AE_xmode2_msx2.out](../../../scratchpad/AE_xmode2_msx2.out), decoded by [scratchpad/xmode2_decode.py](../../../scratchpad/xmode2_decode.py) into [scratchpad/AE_xmode2_msx2_decoded.out](../../../scratchpad/AE_xmode2_msx2_decoded.out)).
>
> Goldfish pass 1 (test writer) 2026-11-23: 23 findings, 15 measured, 4 moved to open.

## Summary

`CHGMOD` switches the screen to the mode in A, 0 to 8. A = 9 and above -- 10 to 12 included, also on the MSX2+ --
return at once and change nothing. It does not touch the palette; [CHGMDP](CHGMDP.md) is the variant that also
resets it. The main ROM's CHGMOD ($005F) always goes through this entry. Mode table, registers and table addresses:
[the screen-modes page](../concepts/screen-modes.md).

## The specification

Case numbers: `[M xmode r]` is record r of round 1 (every case entered from SCREEN 0, the copies RG0SAV-RG7SAV :=
$A5, interrupts off); `[M xmode2 n]` is case n of round 2, which enters from another mode (a main CHGMOD into it
first), sets the copies to $00 or to $8F / $FF (RG0SAV / the rest), the colours to FORCLR / BAKCLR / BDRCLR = $0A /
$05 / $03 or $0E / $0C / $09, fills VRAM with $5A and the palette with 16 non-default entries, and records the VDP
(R#0-R#63, S#0-S#15, palette) before and after, BC..IY and the alternates, VRAM per 16 KB block (bytes no longer
$5A, and the last of them), 8 bytes at ATRBAS, and the colour / width cells. The three references agree on every
output of every case except the machine's own constants: R#9 bit 1 (PAL: $02 on the NMS 8250, $00 on the others),
the default BDRCLR (4 EU, 7 JP), the default LINL40 (37 EU, 39 JP), the font (one VRAM byte), MODE ($04, $44 on the
FS-A1WSX) and $FFF7-$FFFC.

**Interface.**
- In: A = the screen mode, 0 to 8 [P App. 1, SUB-ROM CHGMOD]. A 9 and above, 10-12 on the MSX2+ included: no
  mode change (below) [M xmode 9, 10, 23-25; xmode2 6].
- Out: none [P App. 1, SUB-ROM CHGMOD]. For A 0-8: A $00, F $40 whatever F was on entry ($00 or $FF) [M xmode2 0,
  1]; BC, DE, HL changed; IX = the entry $00D1 for A 2-8 but $000C for A 0 / 1 (IX is not kept); IY and the
  alternate registers kept [M xmode2 0-8].
- Interrupts on return: **as entered** for A 0-8 -- off after a DI entry, on after an EI entry [M xmode2 0, 1, 3].
- The palette is not initialised [P App. 1, main-ROM CHGMOD]: the 16 entries are left as found [M xmode2 0-8].

**Behaviour** (A 0-8). The registers are rebuilt from the copies, not from the VDP: in every case below the VDP
held other values than the copies on entry.
- **R#0** := RG0SAV AND $F1 OR the mode bits M3-M5 (RG0SAV := the same) [M xmode2 0, 1, 2, 4: copies $00, $8F;
  xmode 0-8: $A5]. Bits 7, 5 and 0 of the copy are kept; bits 6 and 4 were never set (open).
- **R#1** := RG1SAV AND $07 OR $60 OR M1 / M2 (RG1SAV := the same): screen on, frame interrupt on, bit 7 cleared
  [M xmode2 0, 1, 3, 4: copies $00 / $FF give $60 / $67 in SCREEN 5, $70 / $77 in SCREEN 0].
- **R#2-R#6**, per A ("copy": written from RG*n*SAV, with the VDP holding another value -- the copies $00, $FF and
  $A5 each came back for A 0, 5 and 8 [M xmode2 0, 1, 3, 4, 5; xmode 0-8]; for A 3 only $A5 [M xmode 3], and INIMLT
  gave $00 from $00 [M xmode2 22]):

| A | R#2 | R#3 | R#4 | R#5 | R#6 | R#7 | NAMBAS CGPBAS PATBAS ATRBAS |
|---|---|---|---|---|---|---|---|
| 0 (TEXT 1) | $00 | copy | $01 | copy | copy | FORCLR·16 + BAKCLR | $0000 $0800 (untouched) (untouched) |
| 0 (TEXT 2) | $03 | $27 (R#10 $00, as on entry) | $02 | copy | copy | FORCLR·16 + BAKCLR | $0000 $1000 (untouched) (untouched) |
| 1 | $06 | $80 | $00 | $36 | $07 | BDRCLR | $1800 $0000 $3800 $1B00 |
| 2 | $06 | $FF | $03 | $36 | $07 | BDRCLR | $1800 $0000 $3800 $1B00 |
| 3 | $02 | copy | $00 | $36 | $07 | BDRCLR | $0800 $0000 $3800 $1B00 |
| 4 | $06 | $FF | $03 | $3F | $07 | BDRCLR | $1800 $0000 $3800 $1E00 |
| 5 / 6 | $1F | copy | copy | $EF | $0F | BDRCLR | $0000 (untouched) $7800 $7600 |
| 7 / 8 | $1F | copy | copy | $F7 | $1E | BDRCLR | $0000 (untouched) $F000 $FA00 |

  R#0's mode bits: A 0 $00 (TEXT 2 $04), 1 $00, 2 $02, 3 $00, 4 $04, 5 $06, 6 $08, 7 $0A, 8 $0E; R#1's: $10 for
  A 0, $08 for A 3, else 0 [M xmode 0-8; xmode2 4]. R#7 [M xmode2 0-5, 7, 8, 30]; the round-1 values ($F4, $04 /
  $07) were FORCLR·16 + BAKCLR and the default BDRCLR. The VDP keeps only part of R#4 / R#6 ($3F) and R#0 ($7E): a
  copy of $FF reads back $3F from the VDP [M xmode2 29, the raw read-back].
- **TEXT 1 or TEXT 2** for A 0: TEXT 2 with LINL40 80, TEXT 1 with LINL40 33, 37, 39; LINLEN on entry does not
  choose (LINL40 37, LINLEN 80: TEXT 1) [M xmode2 3, 4, 33]. The threshold between 39 and 80 is open.
- **R#9**: bit 7 (212 lines) := 1 for A 5-8, := 0 for A 0-4; the other bits from RG9SAV, not from the VDP -- RG9SAV
  $00 with the VDP at $02 gives $80, clearing the NMS 8250's PAL bit; RG9SAV $08 gives $88 [M xmode2 0, 1, 3, 5].
  R#8 is not changed [M xmode2 0-8] (its bits were not walked).
- **R#11**: := 0 by A 4 after SCREEN 7 [M xmode2 7]; A 0 leaves R#11 and RG11SAV ($01 after SCREEN 8) [M xmode2 3;
  xmode 11]. A 1-3 after SCREEN 7 / 8: open.
- **Cells**: SCRMOD := A. OLDSCR := A for A 0 and 1; left as found by A 2-8 (OLDSCR 6 with SCRMOD 0 stays 6)
  [M xmode2 3, 8, 30; xmode 1]. LINLEN := LINL40 for A 0, := LINL32 for A 1 (LINL32 33, LINLEN 20: 33); left as found by
  A 2-8 (29 after SCREEN 1) [M xmode2 1, 2, 4, 8, 33; xmode 1]. NAMBAS..ATRBAS: the table above, "untouched" kept
  from the previous mode (CGPBAS $0000 after SCREEN 1; PATBAS / ATRBAS $F000 / $FA00 after SCREEN 8)
  [M xmode2 1, 3]. DPPAGE / ACPAGE ($0 / $0 on entry) stay 0.
- **VRAM** (bytes no longer $5A per 16 KB block; the counts are exact sums of the tables named) [M xmode2 0-8]:
  A 5 clears lines 0-211 of page 0 (27136 bytes) with **BAKCLR** by a VDP command (R#44 = $55 / $CC: BAKCLR in both
  nibbles), A 8 the same 54272 bytes with BAKCLR as a byte; then the sprite colour table (512) and, of the 32
  attribute entries, Y := **217**, the pattern := n with 8 × 8 sprites or 4n with 16 × 16 (R#1 bit 1, from the
  copy), the fourth byte := FORCLR, X untouched. Pages 1-3 and the sprite pattern table are not touched. A 4: name
  0..255 × 3, pattern and colour tables, the sprite colour table and the attributes (Y 217), 13661 bytes. A 1-3:
  Y **209** (A 1, 2); A 2 writes the name table 0..255 three times and fills the colour table with BAKCLR (its last byte $05 /
  $0C); A 1: name table, patterns, colour table := FORCLR·16 + BAKCLR ($A5), 2944 bytes. A 0: 960 name + 2048
  pattern bytes (1920 + 2048 in TEXT 2). Nothing above $3FFF for A 0-4.
- **A 9 and above** (9, $FF; 10, 11, 12 on all three, the MSX2+ included): nothing changes -- VDP registers, VRAM,
  palette, cells, SCRMOD; BC, DE, HL and A kept; F $4A (A 9), $8A ($FF), $0A (10-12); interrupts ON on return
  after a DI entry [M xmode 9, 10, 23-25; xmode2 6].

## Differences from the reference

C-BIOS's MSX2 / MSX2+ builds (the subject; [scratchpad/AE_xmode2_msx2_decoded.out](../../../scratchpad/AE_xmode2_msx2_decoded.out), `ours`):
- **Interrupts ON on return** for A 0-8 after a DI entry (the references return them as entered) [M xmode2 0, 2-5, 7, 8].
- **TEXT 2 (A 0, LINL40 80): R#3 is not set to the blink table** -- $FF (the copy) where the references write $27
  [M xmode2 4].
- **A 3: R#3 := $00 and RG3SAV := $00** where the references write R#3 from RG3SAV [M xmode 3].
- **A 4: other VRAM** -- 12896 bytes rewritten below $4000 (references 13661) and 384 bytes in $4000-$7FFF, which the
  references do not touch [M xmode2 7].
- LINLEN after A 0 on the HB-F900 / FS-A1WSX: 37 where the references have 39. This is C-BIOS's default LINL40
  (37), not the call: with LINL40 set, both give LINL40 [M xmode2 4, 33].

## On the turbo R

Measured 2026-11-23 (D-TRSPEC) on the FS-A1GT / FS-A1ST: every register, VRAM sum and work-area byte is the FS-A1WSX's, on both models. What differs is the machine and the timing, not the call: $FFF8 = $FF as the boot leaves it (the A1WSX $00; no screen-mode call touches it), VDP S#2 read at a random moment, R#36 = $80 before case 0 (the boot's last VDP command), power-on cells, and one JIFFY count in xmode2 case 27 [M] ([AE_trall/xmode.out](../../../scratchpad/AE_trall/xmode.out), [AE_trall/xmode2.out](../../../scratchpad/AE_trall/xmode2.out); overview: [turbor/remeasured.md](../../turbor/remeasured.md)).

## Open (not measured)

Recorded by round 2: A, F, both interrupt reads, BC, DE, HL, IX, IY and the alternates; the whole VDP (R#0-R#63,
S#0-S#15, the 16 palette entries) before and after; the copies RG0SAV-RG7SAV and $FFE7-$FFFC; SCRMOD, OLDSCR, LINLEN,
CRTCNT, LINL40, LINL32, FORCLR, BAKCLR, BDRCLR, NAMBAS..ATRBAS, DPPAGE, ACPAGE, MODE, CSRY / CSRX; VRAM as the
count of bytes changed per 16 KB block plus 8 bytes at ATRBAS. Not yet recorded: VRAM byte for byte (which value the
name / pattern tables get), and a whole work-area diff $F380-$FFFF.

| case | inputs | state | what it separates | HB-F900 | NMS 8250 | FS-A1WSX |
|---|---|---|---|---|---|---|
| IE | A 5 | entered once with DI, once with EI | interrupt state on return | as entered [M xmode2 0, 1] | as entered | as entered |
| CM-0..3 | A = 0, 1, 2, 3 | from SCREEN 0 | "= INITXT / INIT32 / INIGRP / INIMLT" | equal in one state except R#11 (left $01 by the INITXT record, which ran after SCREEN 8) [M xmode 0-3, 11-14]; from other states and with VRAM: open | same | same |
| CM-0W | A = 0 | LINL40 = 40, 41, 79; LINLEN ≠ LINL40 | the TEXT 1 / TEXT 2 threshold (80 → TEXT 2, ≤ 39 → TEXT 1 measured) | ? | ? | ? |
| CM-4 | A = 4 | GRP\* cells moved, ≠ App. 5 defaults | SCREEN 4 tables from the GRP\* cells vs constants ($1E00 / $1C00) | ? | ? | ? |
| CM-5..8 | A = 5, 6 with DPPAGE 2; A = 7, 8 with DPPAGE 1 | ACPAGE ≠ DPPAGE | R#2 := page 0 vs DPPAGE; DPPAGE / ACPAGE reset or kept (only DPPAGE 0 measured) | ? | ? | ? |
| CM-LN | A = 5, 8 | RG9SAV bit 7 set, VDP R#9 bit 7 clear | bit 7 := 1 from the call (measured with RG9SAV bit 7 clear) vs OR of the copy | $80 / $88 from $00 / $08 [M xmode2 0, 1, 5] | same | same |
| CM-R9 | every A | RG9SAV bits 1, 2, 4, 5 each walked alone; copy ≠ VDP | which R#9 bits come from the copy (bits 1, 3 measured: from the copy) | ? | ? | ? |
| CM-R8 | every A | R#8 bits 1, 3, 5, 6, 7 each walked alone; copy ≠ VDP | which R#8 bits kept vs rewritten | ? | ? | ? |
| CM-R01 | A = 0, 5 | RG0SAV bits 4 and 6 set (line interrupt, digitize: needs an H.KEYI guard) | R#0 bits 4 / 6 kept from the copy like bits 7, 5, 0 | ? | ? | ? |
| CM-RX | A = 0..8 | R#15-R#19, R#23 and their copies garbage (copy ≠ VDP); on the FS-A1WSX also R#25-R#27 garbage, YJK / YAE bits set | each kept vs reset; YJK / YAE cleared for A = 0..8 | ? | ? | ? |
| CM-BUSY | A = 0, 5 | a long VDP command running (S#2 CE = 1) at entry | waits for it vs aborts vs writes over it | ? | ? | ? |
| CM-PAL | A = 0, 2, 4, 5, 8 | 16 non-default entries | palette untouched vs reset | untouched [M xmode2 0-8] | untouched | untouched |
| CM-CLR | A = 5, 8 | BAKCLR $C5 (a high nibble) | the clear byte: BAKCLR AND $0F vs as is (only $05 / $0C measured) | ? | ? | ? |
| CM-BYTE | A = 0..4 | VRAM $5A, read byte for byte | the value of every cleared name / pattern / colour byte (counts only measured) | ? | ? | ? |
| CM-PREV | A = 2, 5 | entered from SCREEN 1; OLDSCR 6 with SCRMOD 0 | OLDSCR := previous SCRMOD vs previous text mode vs unchanged | unchanged by A 2-8 [M xmode2 1, 2, 30] | same | same |
| CM-R11 | A = 1, 2, 3 | from SCREEN 7 / 8 (R#11 = 1) | R#11 := 0 vs kept | ? | ? | ? |
| CM-SPR | A = 4..8 | R#1 bit 1 (16 × 16) set / clear in RG1SAV | pattern numbers step 1 vs 4 in the parked sprites | 1 / 4 by RG1SAV bit 1 [M xmode2 0, 1, 7] | same | same |
| CM-OOR | A = 13, $7F, $80 | any | out-of-range rule (MSX1: A − 1 as a signed byte); 9, 10-12, $FF measured: no change | ? | ? | ? |
| CM-YJK | A = 10, 11, 12 on the MSX2+ | R#25-R#27 garbage | measured: no change at all [M xmode 23-25], so SCREEN 10-12 are reached through another entry -- which one, open | ? | ? | ? |
| CM-MAIN | main-ROM $005F with each A, EXBRSA normal and altered to a slot with no sub-ROM | same set-up | the *3 claim by a breakpoint on the sub-ROM entry and on EXTROM ($015F) as a call trace (equal outputs alone cannot show it); EXBRSA read on the way or not | ? | ? | ? |
| CM-IX | each A, through SUBROM (IX pushed) | IX, IY, alternates distinct | IX on return by SUBROM; through EXTROM: IX not kept, IY / alternates kept [M xmode2 0-8] | ? | ? | ? |
| CM-MODE | A = 2, 5 | MODE ($FAFC) VRAM-size bits 01 / 11, mask bit set / clear | MODE read or written | ? | ? | ? |

## Related pages

[The screen-modes page](../concepts/screen-modes.md); [CHGMDP](CHGMDP.md); [INITXT](INITXT.md),
[INIT32](INIT32.md), [INIGRP](INIGRP.md), [INIMLT](INIMLT.md); MSX1 [CHGMOD](../../bios/CHGMOD.md).

## Tests that cover it

none yet
