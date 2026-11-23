<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `INITXT` (sub-ROM $00D5) — set up the text screen (SCREEN 0)

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the HB-F900, NMS 8250 and FS-A1WSX ([xmode.asm](../../../probes/bios/spec/xmode.asm), [scratchpad/AE_xmode_msx2.out](../../../scratchpad/AE_xmode_msx2.out), decoded by [scratchpad/xmode_decode.py](../../../scratchpad/xmode_decode.py) into [scratchpad/AE_xmode_msx2_decoded.out](../../../scratchpad/AE_xmode_msx2_decoded.out); round 2 [xmode2.asm](../../../probes/bios/spec/xmode2.asm), [scratchpad/AE_xmode2_msx2.out](../../../scratchpad/AE_xmode2_msx2.out), decoded by [scratchpad/xmode2_decode.py](../../../scratchpad/xmode2_decode.py) into [scratchpad/AE_xmode2_msx2_decoded.out](../../../scratchpad/AE_xmode2_msx2_decoded.out)).
>
> Goldfish pass 1 (test writer) 2026-11-23: 13 findings, 10 measured, 3 moved to open.

## Summary

`INITXT` switches to the SCREEN 0 text screen: it programs the VDP from the SCREEN 0 table cells,
sets the width from LINL40, clears the screen and homes the cursor. The handbook describes it as
TEXT 1, 40 × 24; LINL40 80 gives TEXT 2 (80 columns), measured. It does not touch the palette. Shared facts: [the screen-modes page](../concepts/screen-modes.md).

## The specification

Case numbers as on [CHGMOD](CHGMOD.md#the-specification): `[M xmode r]` round 1 (every case after a main CHGMOD 0,
copies RG0SAV-RG7SAV := $A5), `[M xmode2 n]` round 2 (entered from another mode with no CHGMOD 0 in between, the
copies $00 or $8F / $FF, FORCLR / BAKCLR / BDRCLR $0A / $05 / $03 or $0E / $0C / $09, the widths and SCRMOD / OLDSCR
given other values, A / F on entry $FF / $FF unless stated, VRAM := $5A and a non-default palette where VRAM is
read). The three references agree on every output except the machine's own constants: R#9 bit 1 (PAL, $02 on the
NMS 8250), the default LINL40 (37 EU, 39 JP) and BDRCLR (4 EU, 7 JP), the font, MODE and $FFF7-$FFFC. The VDP keeps
only some bits of what is written: R#0 $7E, R#1 $7F, R#2 $7F, R#4 $3F, R#6 $3F, R#10 $07, R#11 $03 (a raw OUT of
$FF read back) [M xmode2 29]; the copies keep all 8.

**Interface.**
- In: TXTNAM ($F3B3) the name table, TXTCGP ($F3B7) the pattern generator table, LINL40 ($F3AE) the line length [P App.
  1, SUB-ROM INITXT]; FORCLR / BAKCLR and the copies RG1SAV, RG3SAV, RG5SAV, RG6SAV, RG9SAV (below). Not inputs: A, F,
  LINLEN, SCRMOD, OLDSCR [M xmode2 18, 33].
- Out: A $00, F $40 (A / F $FF on entry) [M xmode2 18, 19, 33; xmode 11]; BC, DE, HL changed; IX $000C (not kept);
  IY and the alternates kept [M xmode2 18].
- The palette is not initialised [P App. 1, main-ROM INITXT]: the 16 entries are left as found [M xmode2 18, 19].
- Interrupts on return: **as entered** (off after DI, on after EI) [M xmode2 18, 19].

**Behaviour.**
- **TEXT 1 or TEXT 2 by LINL40**: LINL40 80 gives TEXT 2, LINL40 33 / 37 / 39 TEXT 1; LINLEN on entry does not count
  (LINLEN 80 with LINL40 37: TEXT 1) [M xmode2 18, 19, 33; xmode 11]. The threshold between 39 and 80 is open (IT-W).
- **LINLEN := LINL40** (33 from LINLEN 20; 80; 37 from 80) [M xmode2 18, 19, 33]. **SCRMOD := 0, OLDSCR := 0** (from
  7 / 6) [M xmode2 18]. Cursor home (CSRY / CSRX 1 / 1) [M xmode2 18].
- The VDP registers and copies, from SCREEN 5 / 8 (the copies differ from the VDP on entry in every case):

| | R#0 | R#1 | R#2 | R#3 | R#4 | R#5 | R#6 | R#7 | NAMBAS CGPBAS |
|---|---|---|---|---|---|---|---|---|---|
| TEXT 1 | RG0SAV AND $F1 | RG1SAV AND $07 OR $70 | $00 | RG3SAV | $01 | RG5SAV | RG6SAV | FORCLR·16 + BAKCLR | $0000 $0800 |
| TEXT 2 | RG0SAV AND $F1 OR $04 | RG1SAV AND $07 OR $70 | $03 | $27 | $02 | RG5SAV | RG6SAV | FORCLR·16 + BAKCLR | $0000 $1000 |

  Copies $00: `00 70 00 00 01 00 00 A5` (FORCLR / BAKCLR $0A / $05) [M xmode2 18]; copies $8F / $FF, LINL40 80:
  `04 77 03 27 02 FF 3F EC` (RG0SAV $85, RG6SAV $FF) [M xmode2 19]; copies $A5: `20 75 00 A5 01 A5 25 F4` [M xmode 11].
  TXTNAM / TXTCGP were at their defaults, so "from the cells" vs "constants" is open (IT-BASE).
- **R#9** bit 7 := 0 (212 → 192 lines: $82 → $02), the other bits kept [M xmode2 18]. **R#11 and PATBAS / ATRBAS are
  not written**: R#11 / RG11SAV $01 and PATBAS / ATRBAS $F000 / $FA00 stay after SCREEN 8, $7800 / $7600 after
  SCREEN 5 [M xmode2 18, 19; xmode 11]. R#10 $00 as on entry.
- **VRAM**: 960 name-table + 2048 pattern bytes rewritten in TEXT 1, 1920 + 2048 in TEXT 2 (the bytes no longer
  $5A); nothing above $3FFF, so a previous page 1-3 is left as it was [M xmode2 18, 19].

## Differences from the reference

C-BIOS's MSX2 / MSX2+ builds ([scratchpad/AE_xmode2_msx2_decoded.out](../../../scratchpad/AE_xmode2_msx2_decoded.out), `ours`):
- **Interrupts ON on return** after a DI entry [M xmode2 18, 33].
- **TEXT 2: R#3 is not set to the blink table** -- the copy ($FF) where the references write $27 [M xmode2 19].
- LINLEN after INITXT on the HB-F900 / FS-A1WSX is 37 where the references have 39: C-BIOS's default LINL40, not the
  call (with LINL40 set, both give LINL40) [M xmode2 18, 19; xmode 11].
- Other A / F / IX on return (A $70 / $77 = R#1, F $A0, IX $005C): not part of the contract (all registers may change).

## Open (not measured)

Recorded per case: as [CHGMOD](CHGMOD.md#open-not-measured); still to record: LINTTB, the key line's row, the blink
table byte for byte, and the name table to 2160 cells (27 rows of 80).

| case | inputs | state | what it separates | HB-F900 | NMS 8250 | FS-A1WSX |
|---|---|---|---|---|---|---|
| IE | the page's base case | entered once with DI, once with EI | interrupt state on return | as entered [M xmode2 18, 19] | as entered | as entered |
| IT-W | LINL40 = 0, 1, 40, 41, 79, 81, 255 | LINLEN, LINL32 other values | the TEXT 1 / TEXT 2 threshold (≤ 39 TEXT 1, 80 TEXT 2 measured); LINLEN := LINL40 as is (33, 37, 80 measured) vs clamped | ? | ? | ? |
| IT-BASE | TXTNAM, TXTCGP moved; TXTCOL moved (TEXT 2) | defaults vs moved | R#2 / R#4 / R#3 / R#10 from the cells vs App. 5 constants; blink base from TXTCOL or fixed $0800 | ? | ? | ? |
| IT-BLINK | LINL40 = 80 | R#12 / R#13 and copies garbage; blink-table VRAM garbage | blink registers written vs kept (R#12 / R#13 were $00 before and after); blink table cleared vs untouched | ? | ? | ? |
| IT-LN | LINL40 = 80 | R#9 bit 7 set / clear, copy ≠ VDP | 24 vs 26.5 lines; bit 7 := 0 measured only with VDP and copy both $82 | ? | ? | ? |
| IT-R9 | LINL40 = 40, 80 | R#9 bits 1, 2, 3, 4, 5 each walked alone, copy ≠ VDP | which R#9 bits kept, from the copy or the VDP | ? | ? | ? |
| IT-R8 | LINL40 = 40 | R#8 bits 1, 3, 5, 6, 7 each walked alone, copy ≠ VDP | which R#8 bits kept | ? | ? | ? |
| IT-R01 | — | RG0SAV bits 4, 6 set | R#0 bits 4 / 6 kept like 7, 5, 0 ($00, $8F, $A5 measured) | ? | ? | ? |
| IT-COL | FORCLR / BAKCLR | BDRCLR distinct | R#7 = FORCLR·16 + BAKCLR in 8 bits (measured: $A5, $EC, $F4) | as stated [M xmode2 18, 19] | same | same |
| IT-PAL | — | palette non-default | palette untouched | untouched [M xmode2 18, 19] | untouched | untouched |
| IT-KEY | CNSDFG 0 / $FF; CRTCNT 13, 24 | LINL40 40 and 80 | key-line row and placement at 80 columns | ? | ? | ? |
| IT-PREV | — | entered from SCREEN 5 / 8 with no CHGMOD 0 between, SCRMOD / OLDSCR / LINLEN garbage | the work-area writes are INITXT's own | measured [M xmode2 18, 19] | same | same |
| IT-DP | — | from SCREEN 5 with DPPAGE 1 (R#2 page bits set) | R#2 := $00 vs page bits kept; R#11 kept | ? | ? | ? |
| IT-MAIN | main-ROM $006C | same set-ups | the *3 claim by a breakpoint on the sub-ROM entry and on EXTROM ($015F) as a call trace | ? | ? | ? |
| IT-HIGH | TXTNAM = $3C00, LINL40 = 80 | name table crossing $4000; MODE bit 3 set, then clear; R#14 garbage | masked to 16 KB by MODE bit 3 vs always vs never; R#14 written | ? | ? | ? |

## Related pages

[The screen-modes page](../concepts/screen-modes.md); [SETTXT](SETTXT.md) (VDP only);
[CHGMOD](CHGMOD.md); [CLS](CLS.md); [DSPFNK](DSPFNK.md); MSX1 [INITXT](../../bios/INITXT.md).

## Tests that cover it

none yet
