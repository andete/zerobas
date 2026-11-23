<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `CLS` (sub-ROM $0115) — clear the screen

> **Spec:** DRAFT 0 (2026-11-23), from the published interface only; nothing measured yet. References to measure: HB-F900, NMS 8250, FS-A1WSX.

## Summary

The sub-ROM's screen clear; the handbook names it **CLSSUB**. It clears the screen of the current
mode, including the bitmap modes 5-8. The main ROM's CLS ($00C3) always goes through the sub-ROM.
Shared facts: [the screen-modes page](../concepts/screen-modes.md).

## The specification

**Interface.**
- In: none [P App. 1, SUB-ROM CLSSUB] — unlike the main-ROM CLS, whose input is "set zero flag"
  [P App. 1, main-ROM CLS]. Whether the sub-ROM entry tests Z, [A].
- Out: none; all registers may change [P App. 1, SUB-ROM CLSSUB]. (The main-ROM CLS lists only
  AF, BC, DE [P App. 1].)
- Interrupts on return: [A].

**Behaviour.**
- SCREEN 0-3: as MSX1 [CLS](../../bios/CLS.md) (spaces + cursor home + key line; SCREEN 2 / 3 fills)
  [A].
- SCREEN 4: as SCREEN 2 [A].
- SCREEN 5-8: fills the active page with BAKCLR [A]; which page (ACPAGE or DPPAGE), how many lines
  (192, 212, or 256), whether by a VDP command (and what it leaves in R#32-R#46 and S#2), [A].
- TEXT 2: blink table cleared or not [A].

## Differences from the reference

Not measured yet.

## Open (not measured)

Recorded per case: registers, F set apart from A (§3a), interrupt state, CSRX / CSRY, LINTTB,
R#0-R#46, S#2, all copies, the palette, VRAM over 128 KB (block sums plus each page's first and last
line and the lines 192-255 of each page).

| case | inputs | state | what it separates | HB-F900 | NMS 8250 | FS-A1WSX |
|---|---|---|---|---|---|---|
| IE | the page's base case (its first row) | entered once with DI, once with EI | interrupt state on return: forced on, forced off, or kept (read twice, §3a) | ? | ? | ? |
| CL-Z | Z set / clear, A and carry set independently | SCREEN 0 and 5 | Z gate present in the sub-ROM entry or not | ? | ? | ? |
| CL-0..8 | FORCLR $3A, BAKCLR $C5, BDRCLR $F9 | SCRMOD 0..8, VDP in that mode, VRAM garbage; and SCRMOD 0 with RG0SAV / RG1SAV saying GRAPHIC 4 | per-mode fill: what, where; mode from SCRMOD vs the copies | ? | ? | ? |
| CL-OOR | — | SCRMOD 9, $FF | out-of-range rule | ? | ? | ? |
| CL-YJK | BAKCLR $C5 | SCRMOD 10, 11, 12, VDP in that mode where the machine has it | fill byte in the YJK modes vs out of range | ? | ? | ? |
| CL-BUSY | SCREEN 5, 8 | a long VDP command running (S#2 CE = 1) at entry | waits vs overwrites | ? | ? | ? |
| CL-AC | SCREEN 7 ACPAGE 1 / DPPAGE 0; SCREEN 5 ACPAGE 3 / DPPAGE 2 and 2 / 1 | — | clears ACPAGE vs DPPAGE vs page 0 | ? | ? | ? |
| CL-LN | SCREEN 5, 8 | R#9 bit 7 set / clear (copy ≠ VDP) | 192 vs 212 vs 256 lines | ? | ? | ? |
| CL-BK | SCREEN 5, 6, 7, 8 | BAKCLR $06, $C5, $0F, $FF | fill byte: nibble doubled vs 2-bit packed ($06 gives $66 vs $AA) vs whole byte | ? | ? | ? |
| CL-80 | SCREEN 0, LINL40 80 | blink table garbage | 1920 / 2160 cells cleared; blink table cleared or not | ? | ? | ? |
| CL-TBL | SCREEN 0, 1 | after INITXT / INIT32: TXTNAM / T32NAM, NAMBAS and RG2SAV / R#2 set to three different addresses | table from the cell vs NAMBAS vs R#2 | ? | ? | ? |
| CL-SPR | SCREEN 5 | sprite tables at $7400-$7FFF garbage | sprite / palette tables beyond line 212 kept | ? | ? | ? |
| CL-CMD | SCREEN 8, LOGOPR 0 (IMP) and 3 (XOR) | R#32-R#46 garbage; bitmap garbage | command registers after; LOGOPR used (XOR leaves garbage-dependent bytes) or not | ? | ? | ? |
| CL-PAL | each | palette non-default | untouched | ? | ? | ? |
| CL-MAIN | main-ROM $00C3, Z set | same | the *3 claim by a breakpoint on the sub-ROM entry and on EXTROM ($015F) as a call trace | ? | ? | ? |

## Related pages

[The screen-modes page](../concepts/screen-modes.md); [CLRTXT](CLRTXT.md); [SETPAG](SETPAG.md);
[CHGMOD](CHGMOD.md); MSX1 [CLS](../../bios/CLS.md).

## Tests that cover it

none yet
