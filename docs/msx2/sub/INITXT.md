<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `INITXT` (sub-ROM $00D5) — set up the text screen (SCREEN 0)

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the HB-F900, NMS 8250 and FS-A1WSX ([xmode.asm](../../probes/bios/spec/xmode.asm), [scratchpad/AE_xmode_msx2.out](../../scratchpad/AE_xmode_msx2.out), decoded by `scratchpad/xmode_decode.py`).

## Summary

`INITXT` switches to the SCREEN 0 text screen: it programs the VDP from the SCREEN 0 table cells,
sets the width from LINL40, clears the screen and homes the cursor. The handbook describes it as
TEXT 1, 40 × 24; whether a LINL40 above 40 gives TEXT 2 (80 columns) is the main open question. It
does not touch the palette. Shared facts: [the screen-modes page](../concepts/screen-modes.md).

## The specification

**Interface.**
- In: TXTNAM ($F3B3) the name table, TXTCGP ($F3B7) the pattern generator table, LINL40 ($F3AE) the
  line length [P App. 1, SUB-ROM INITXT].
- Out: none; all registers may change [P App. 1, SUB-ROM INITXT].
- The palette is not initialised; INIPLT afterwards does that [P App. 1, main-ROM INITXT].
- Interrupts on return: [A].

**Behaviour.**
- Sets the VDP to TEXT 1 (40 × 24) [P App. 1, SUB-ROM INITXT]; TEXT 2 when LINL40 > 40 [A]
  (BASIC's SCREEN 0 at WIDTH 80 is TEXT 2 [P Ch. 4 §3, Table 4.4]).
- In TEXT 2: R#3 / R#10 the blink table, R#12 / R#13 the blink colour and period [P Ch. 4 §3.2];
  which values, and whether the blink table is cleared, [A].
- R#7 := FORCLR · 16 + BAKCLR [A] (the TEXT colour register [P Ch. 4 §3.1.3]).
- SCRMOD / OLDSCR := 0, LINLEN := LINL40, cursor home, screen cleared, key line drawn when CNSDFG
  is set, LINTTB reset [A] (all measured on the MSX1 main-ROM INITXT: [INITXT](../../bios/INITXT.md)).
- R#8 / R#9 and their copies: [A].

**Measured** [M] (the same on all three references, entered with interrupts off and RG0SAV-RG7SAV := $A5): the
same VDP registers and table cells as [CHGMOD](CHGMOD.md) with A 0 -- see its table -- interrupts as entered
(off), A $00, F $40.

## Differences from the reference

C-BIOS's MSX2 / MSX2+ builds set the same, but return with interrupts ON ([scratchpad/AE_xmode_msx2.out](../../scratchpad/AE_xmode_msx2.out)).

## Open (not measured)

Recorded per case: as [CHGMOD](CHGMOD.md#open-not-measured), plus LINTTB, CRTCNT, the key line's
row, the blink table (byte for byte), and the name table to 2160 cells (27 rows of 80).

| case | inputs | state | what it separates | HB-F900 | NMS 8250 | FS-A1WSX |
|---|---|---|---|---|---|---|
| IE | the page's base case (its first row) | entered once with DI, once with EI | interrupt state on return: forced on, forced off, or kept (read twice, §3a) | ? | ? | ? |
| IT-W | LINL40 = 0, 1, 39, 40, 41, 79, 80, 81, 255 | LINLEN, LINL32 other values | TEXT 1 / TEXT 2 threshold (> 40? ≥ 41? > 32?); LINLEN := LINL40 as is vs clamped | ? | ? | ? |
| IT-BASE | TXTNAM, TXTCGP moved; TXTCOL moved (TEXT 2) | defaults vs moved | R#2 / R#4 / R#3 / R#10 from the cells vs App. 5 constants; blink base from TXTCOL or fixed $0800 | ? | ? | ? |
| IT-BLINK | LINL40 = 80 | R#12 / R#13 and copies garbage; blink-table VRAM garbage | blink registers written vs kept; blink table cleared vs untouched | ? | ? | ? |
| IT-LN | LINL40 = 80 | R#9 bit 7 set / clear, copy ≠ VDP | 24 vs 26.5 lines kept or forced; CRTCNT changed? | ? | ? | ? |
| IT-R9 | LINL40 = 40, 80 | R#9 bits 1, 2, 3, 4, 5, 7 each walked alone, copy ≠ VDP | which R#9 bits kept | ? | ? | ? |
| IT-R8 | LINL40 = 40 | R#8 bits 1, 3, 5, 6, 7 each walked alone, copy ≠ VDP | which R#8 bits kept | ? | ? | ? |
| IT-R01 | — | RG0SAV / RG1SAV walking bits, ≠ VDP | which R#0 / R#1 bits kept (MSX1: R#0 bit 0; R#1 bits 7, 5, 2-0) | ? | ? | ? |
| IT-COL | FORCLR / BAKCLR = $3A / $C5, 15 / 4 | BDRCLR distinct | R#7 from FORCLR / BAKCLR in 8 bits vs BDRCLR | ? | ? | ? |
| IT-PAL | — | palette non-default | palette untouched | ? | ? | ? |
| IT-KEY | CNSDFG 0 / $FF; CRTCNT 13, 24 | LINL40 40 and 80 | key-line row and placement at 80 columns | ? | ? | ? |
| IT-PREV | — | entered from SCREEN 5 / 7 with DPPAGE 1 | R#2 page bits cleared; VRAM above $3FFF touched? MODE mask bit | ? | ? | ? |
| IT-MAIN | main-ROM $006C | same set-ups | the *3 claim by a breakpoint on the sub-ROM entry and on EXTROM ($015F) as a call trace | ? | ? | ? |
| IT-HIGH | TXTNAM = $3C00, LINL40 = 80 | name table crossing $4000; MODE bit 3 set, then clear; R#14 garbage | masked to 16 KB by MODE bit 3 vs always vs never; R#14 written | ? | ? | ? |

## Related pages

[The screen-modes page](../concepts/screen-modes.md); [SETTXT](SETTXT.md) (VDP only);
[CHGMOD](CHGMOD.md); [CLS](CLS.md); [DSPFNK](DSPFNK.md); MSX1 [INITXT](../../bios/INITXT.md).

## Tests that cover it

none yet
