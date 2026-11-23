<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `CHGMOD` (sub-ROM $00D1) — change the screen mode

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the HB-F900, NMS 8250 and FS-A1WSX ([xmode.asm](../../../probes/bios/spec/xmode.asm), [scratchpad/AE_xmode_msx2.out](../../../scratchpad/AE_xmode_msx2.out), decoded by `scratchpad/xmode_decode.py`).

## Summary

`CHGMOD` switches the screen to the mode in A, 0 to 8 (what A = 10 to 12 does is measured on
each machine, MSX2+ included, not assumed). It does not touch the palette; [CHGMDP](CHGMDP.md) is the variant that also resets it. The
main ROM's CHGMOD ($005F) always goes through this entry. Mode table, registers and table addresses:
[the screen-modes page](../concepts/screen-modes.md).

## The specification

**Interface.**
- In: A = the screen mode, 0 to 8 [P App. 1, SUB-ROM CHGMOD]. 10-12 on an MSX2+ [A].
- Out: none; all registers may change [P App. 1, SUB-ROM CHGMOD]. Through EXTROM, IY and the
  alternate registers are kept [P App. 1, EXTROM].
- The palette is not initialised [P App. 1, main-ROM CHGMOD].
- Interrupts on return: [A].

**Behaviour.**
- For A = 0-3 it does what [INITXT](INITXT.md), [INIT32](INIT32.md), [INIGRP](INIGRP.md),
  [INIMLT](INIMLT.md) do [A] (the MSX1 main ROM's CHGMOD does exactly that, measured:
  [CHGMOD](../../bios/CHGMOD.md)).
- For A = 4-8 it sets the VDP to the mode of the [mode table](../concepts/screen-modes.md#the-modes)
  [P Ch. 4 §3.5-§3.9, Figures 4.31, 4.36, 4.39, 4.42, 4.45]; where it takes the table addresses from, whether it clears the
  screen, parks the sprites (Y 217 in modes 4-8 [P App. 1, CLRSPR]) and what it writes to SCRMOD,
  OLDSCR, NAMBAS..ATRBAS, DPPAGE / ACPAGE: [A].
- For A outside 0-8 (0-8, 10-12 on an MSX2+): [A].
- Work-area cells and VDP registers it reads / writes: RG0SAV-RG7SAV, the R#8-R#23 copies, R#0-R#23
  [A]; the screen-table cells of modes 0-3 [P App. 1, INITXT .. INIMLT inputs].

**Measured** [M] (the same on all three references, entered with interrupts off and RG0SAV-RG7SAV := $A5):
A 0-8 set the mode -- the VDP registers and table cells below, SCRMOD := A, LINLEN 37 / 39 (EU / JP), CRTCNT 24 --
and return **with interrupts as entered (off)**, A $00, F $40. **A 9, $FF -- and 10, 11, 12, also on the FS-A1WSX
(MSX2+) -- change nothing** (SCRMOD stays, A kept) and return with interrupts ON: SCREEN 10-12 are not CHGMOD's.

| A | R#0 | R#1 | R#2 | R#3 | R#4 | R#5 | R#6 | NAMBAS CGPBAS PATBAS ATRBAS |
|---|---|---|---|---|---|---|---|---|
| 0 | $20 | $75 | $00 | (kept) | $01 | (kept) | (kept) | $0000 $0800 (kept) (kept) |
| 1 | $20 | $65 | $06 | $80 | $00 | $36 | $07 | $1800 $0000 $3800 $1B00 |
| 2 | $22 | $65 | $06 | $FF | $03 | $36 | $07 | $1800 $0000 $3800 $1B00 |
| 3 | $20 | $6D | $02 | (kept) | $00 | $36 | $07 | $0800 $0000 $3800 $1B00 |
| 4 | $24 | $65 | $06 | $FF | $03 | $3F | $07 | $1800 $0000 $3800 $1E00 |
| 5 / 6 | $26 / $28 | $65 | $1F | (kept) | $25 | $EF | $0F | $0000 $0800 $7800 $7600 |
| 7 / 8 | $2A / $2E | $65 | $1F | (kept) | $25 | $F7 | $1E | $0000 $0800 $F000 $FA00 |

("kept": the call left the register as it found it -- the probe's $A5 copy or the previous mode's value.)

Machine values, not the call's: R#7 (the border: JP $07, EU $04), R#9 (PAL $02 on the NMS 8250, NTSC $00).

## Differences from the reference

C-BIOS's MSX2 / MSX2+ builds (the subject) set the same registers and cells, but return with interrupts ON for A 0-8
(the references keep them off), A = R#1's value and F $A0; for A 3 they write R#3 := $00 where the references leave
it ([scratchpad/AE_xmode_msx2.out](../../../scratchpad/AE_xmode_msx2.out)).

## Open (not measured)

Every output is recorded in every case: all registers incl. IX / IY / alternates, interrupt state
(read twice), R#0-R#27, the copies RG0SAV-RG23SAV, SCRMOD, OLDSCR, NAMBAS..ATRBAS, DPPAGE, ACPAGE,
LINLEN, CSRX / CSRY, CNSDFG, the 16 palette entries, and VRAM (block sums over 128 KB plus windows on
every default and moved table). Each case is also run as the direct call it should equal, from the
same set-up.

| case | inputs | state | what it separates | HB-F900 | NMS 8250 | FS-A1WSX |
|---|---|---|---|---|---|---|
| IE | the page's base case (its first row) | entered once with DI, once with EI | interrupt state on return: forced on, forced off, or kept (read twice, §3a) | ? | ? | ? |
| CM-0..3 | A = 0, 1, 2, 3 | cells moved; copies $A5 / $5A | "= INITXT / INIT32 / INIGRP / INIMLT" vs a private path (compare with the direct sub-ROM calls) | ? | ? | ? |
| CM-0W | A = 0 | LINL40 = 39, 40, 41, 80; LINLEN ≠ LINL40 | TEXT 1 vs TEXT 2 chosen by LINL40, by LINLEN, or never | ? | ? | ? |
| CM-4 | A = 4 | GRP\* cells moved, ≠ App. 5 defaults | SCREEN 4 tables from the GRP\* cells vs constants ($1E00 / $1C00) | ? | ? | ? |
| CM-5..8 | A = 5, 6 with DPPAGE 2, R#2 on page 1, RG2SAV on page 3; A = 7, 8 with DPPAGE 1, R#2 on page 0, RG2SAV with other low bits | ACPAGE ≠ DPPAGE | R#2 := page 0 vs DPPAGE vs kept from R#2 vs from RG2SAV; DPPAGE / ACPAGE reset or kept | ? | ? | ? |
| CM-LN | A = 5, 8 | R#9 bit 7 (212 lines) set / clear in VDP, other value in the copy | lines from the copy, the VDP, or a constant | ? | ? | ? |
| CM-R9 | every A | R#9 bits 1, 2, 3, 4, 5, 7 each walked alone; copy ≠ VDP | which R#9 bits are kept and from where (copy or VDP) | ? | ? | ? |
| CM-R8 | every A | R#8 bits 1, 3, 5, 6, 7 each walked alone; copy ≠ VDP | which R#8 bits kept vs rewritten | ? | ? | ? |
| CM-R01 | A = 4..8 | RG0SAV / RG1SAV walking bits ($01 .. $80 and complements), ≠ VDP | which R#0 / R#1 bits kept (bit 0 / bit 4 interrupt enables, R#1 bits 0, 1, 5, 6) | ? | ? | ? |
| CM-RX | A = 0..8 | R#15-R#19, R#23 and their copies garbage (copy ≠ VDP); on the FS-A1WSX also R#25-R#27 garbage, YJK / YAE bits set | each kept vs reset; YJK / YAE cleared for A = 0..8 | ? | ? | ? |
| CM-BUSY | A = 0, 5 | a long VDP command running (S#2 CE = 1) at entry | waits for it vs aborts vs writes over it | ? | ? | ? |
| CM-PAL | A = 0, 5, 8 | palette entries non-default | palette untouched [P] vs reset | ? | ? | ? |
| CM-CLR | A = 4..8, BAKCLR $06 and $C5 | VRAM address-dependent garbage over 128 KB | screen cleared (to 0, to BAKCLR as nibble / packed / byte) and which 64 KB half; sprite table at Y 217 vs 209 (A = 4, GRAPHIC 2-like) vs 208 / 216 vs untouched | ? | ? | ? |
| CM-PREV | A = 2, 5 | entered from SCREEN 0 (TEXT 2), 3, 7; SCRMOD ≠ actual VDP mode | OLDSCR := previous SCRMOD vs previous text mode vs unchanged | ? | ? | ? |
| CM-SPR | A = 4..8 | R#1 bit 1 (16 × 16) set / clear | pattern numbers step 1 vs 4 in the parked sprites | ? | ? | ? |
| CM-OOR | A = 9, 13, $7F, $80, $FF | any | out-of-range rule (MSX1: A − 1 as a signed byte); 9 on MSX2 vs MSX2+ | ? | ? | ? |
| CM-YJK | A = 10, 11, 12 (on the MSX2s: out of range), after locating the R#25-R#27 copies (concept page) | R#25-R#27 and their copies garbage | R#25 YJK / YAE bits; SCRMOD value stored | ? | ? | ? |
| CM-MAIN | main-ROM $005F with each A, EXBRSA normal and altered to a slot with no sub-ROM | same set-up | the *3 claim by a breakpoint on the sub-ROM entry and on EXTROM ($015F) as a call trace (equal outputs alone cannot show it); EXBRSA read on the way or not | ? | ? | ? |
| CM-IX | each A, through EXTROM and through SUBROM (IX pushed) | IX, IY, alternates distinct | IX on return by either path; IY / alternates kept [P] | ? | ? | ? |
| CM-MODE | A = 2, 5 | MODE ($FAFC) VRAM-size bits 01 / 11, mask bit set / clear | MODE read or written | ? | ? | ? |

## Related pages

[The screen-modes page](../concepts/screen-modes.md); [CHGMDP](CHGMDP.md); [INITXT](INITXT.md),
[INIT32](INIT32.md), [INIGRP](INIGRP.md), [INIMLT](INIMLT.md); MSX1 [CHGMOD](../../bios/CHGMOD.md).

## Tests that cover it

none yet
