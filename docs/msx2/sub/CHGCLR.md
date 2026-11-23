<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `CHGCLR` (sub-ROM $0111) — set the screen colours

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the HB-F900, NMS 8250 and FS-A1WSX ([xsubcls.asm](../../../probes/bios/spec/xsubcls.asm), [scratchpad/AE_xsubcls_msx2.out](../../../scratchpad/AE_xsubcls_msx2.out), decoded by `scratchpad/xsubcls_decode.py`).

## Summary

`CHGCLR` puts the colour cells FORCLR, BAKCLR and BDRCLR on the screen for a given mode. On an MSX2
the modes 4-8 add their own border / colour rules (GRAPHIC 7's 8-bit border, GRAPHIC 5's 2-bit
colours, TEXT 2's blink colour). Shared facts: [the screen-modes page](../concepts/screen-modes.md).

## The specification

**Interface.**
- In: A = the mode; FORCLR ($F3E9), BAKCLR ($F3EA), BDRCLR ($F3EB) [P App. 1, SUB-ROM CHGCLR].
- Out: none; all registers may change [P App. 1, SUB-ROM CHGCLR].
- Interrupts on return: [A].

**Behaviour.**
- Text modes: R#7 := FORCLR · 16 + BAKCLR [A] (R#7 is the text colour register [P Ch. 4 §3.1.3,
  §3.2.3]).
- SCREEN 1: also fills the colour table at T32COL [A] (as MSX1 [CHGCLR](../../bios/CHGCLR.md)).
- Graphic modes: R#7 := BDRCLR [A]; in GRAPHIC 7 all 8 bits of R#7 are the border
  [P Ch. 4 §4, "Screen ON/OFF"]; GRAPHIC 5's border encoding [A].
- TEXT 2: R#12 (blink colours) written or not [A].
- Which it reads for the mode, A or SCRMOD, [A]: the handbook names A [P App. 1], while the MSX1
  main-ROM CHGCLR measured reads SCRMOD ([CHGCLR](../../bios/CHGCLR.md)).

**Measured** [M] (the same on all three references; FORCLR $3A, BAKCLR $C5, BDRCLR $F9): **FORCLR and BAKCLR are
masked to 4 bits** ($0A / $05) in SCREEN 0, 1, 2 and 5 -- not in SCREEN 8, where they stay $3A / $C5; R#7 := FORCLR x
16 + BAKCLR ($A5) in SCREEN 0, BDRCLR ($F9) in the others; in SCREEN 1 the colour table is filled with FORCLR x 16 +
BAKCLR ($A5). Interrupts ON on return.

## Differences from the reference

C-BIOS's MSX2 / MSX2+ builds (the subject) do not mask FORCLR / BAKCLR: R#7 in SCREEN 0 and SCREEN 1's colour table
read $E5 where the references give $A5; other A / F ([scratchpad/AE_xsubcls_msx2.out](../../../scratchpad/AE_xsubcls_msx2.out)).

## Open (not measured)

Recorded per case: registers (incl. A, F, BC, DE, HL), interrupt state, R#7, R#12, R#13, all copies,
the T32COL colour table byte for byte, the palette, VRAM block sums.

| case | inputs | state | what it separates | HB-F900 | NMS 8250 | FS-A1WSX |
|---|---|---|---|---|---|---|
| IE | the page's base case (its first row) | entered once with DI, once with EI | interrupt state on return: forced on, forced off, or kept (read twice, §3a) | ? | ? | ? |
| CC-AS | A = 0, SCRMOD = 5; A = 5, SCRMOD = 0; A = SCRMOD = 0 with RG0SAV / RG1SAV saying GRAPHIC 4 | VDP in the SCRMOD mode | mode from A vs SCRMOD vs the register copies' mode bits | ? | ? | ? |
| CC-0..8 | A = SCRMOD = 0..8 | FORCLR $3A, BAKCLR $C5, BDRCLR $F9 (bits above 3 set) | per mode: R#7 value, nibble masks, 8-bit in mode 8 | ? | ? | ? |
| CC-80 | A = 0 | VDP in TEXT 2 (LINL40 80), R#12 copy garbage | R#12 written (from what) vs kept | ? | ? | ? |
| CC-6 | A = 6 | BDRCLR 0..15 | GRAPHIC 5 border: low 2 bits, both pairs, or as is | ? | ? | ? |
| CC-1 | A = 1 | T32COL moved, $3FF0 (wrap); MODE bit 3 set, then clear; R#14 garbage | colour table fill and wrap in 16 KB vs 128 KB | ? | ? | ? |
| CC-4 | A = 4 | GRPCOL table garbage | SCREEN 4 colour table untouched (as SCREEN 2) | ? | ? | ? |
| CC-OOR | A = 9, $81, $FF | — | out-of-range rule | ? | ? | ? |
| CC-YJK | A = SCRMOD = 10, 11, 12 | VDP in that mode where the machine has it | R#7 rule in the YJK modes vs out of range | ? | ? | ? |
| CC-PAL | each A | palette non-default | palette untouched | ? | ? | ? |
| CC-MAIN | main-ROM $0062, A = 0..8 | same | main-ROM CHGCLR is marked *1, "same as MSX1" [P App. 1]: whether it reaches the sub-ROM in any mode, by a breakpoint on the sub-ROM entry and on EXTROM ($015F) as a call trace; outputs compared in every mode | ? | ? | ? |

## Related pages

[The screen-modes page](../concepts/screen-modes.md); [CHGMOD](CHGMOD.md); [CLS](CLS.md); MSX1
[CHGCLR](../../bios/CHGCLR.md).

## Tests that cover it

none yet
