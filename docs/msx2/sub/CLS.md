<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `CLS` (sub-ROM $0115) — clear the screen

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the HB-F900, NMS 8250 and FS-A1WSX ([xsubcls.asm](../../../probes/bios/spec/xsubcls.asm), [scratchpad/AE_xsubcls_msx2.out](../../../scratchpad/AE_xsubcls_msx2.out), decoded by [xsubcls_decode.py](../../../scratchpad/xsubcls_decode.py) into [scratchpad/AE_xsubcls_msx2_decoded.out](../../../scratchpad/AE_xsubcls_msx2_decoded.out)). `[XC n]` = that run's case n (0-36; 21-36 added 2026-11-23).
>
> Goldfish pass 1 (test writer) 2026-11-23: 7 findings, 5 measured, 0 moved to open, 2 corrected in wording (cases XC 21-26, 33, 36 added for it).

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

**Measured** [M] (the same on all three references; FORCLR $3A, BDRCLR $F9, BAKCLR as said; per case three 16-byte
windows preset $5A -- the ones read are named below):
- SCREEN 0 / 1: the name table := spaces ($20), its start and last 16 bytes ($0000 / $03B0, $1800 / $1AF0), the 16
  past it left [XC 5-8].
- SCREEN 2: the patterns := $00 and the colour table := **BAKCLR, the whole byte** ($06 / $C5) -- read at the start
  of both [XC 9, 10] and at their last 16 bytes ($17F0, $37F0) [XC 21]; $3800 just past the colour table left; the
  name table left [XC 9, 10].
- SCREEN 3: the patterns := **(BAKCLR << 4) OR BAKCLR** ($66 / $D5 -- shifted, the high nibble not masked) [XC 11,
  12]; the fill ends at $05FF: $05F0 filled, $0600 and $07F0 left [XC 22]; the name table ($0800) left.
- SCREEN 5 / 7: the bitmap := **(BAKCLR rotated by 4) OR BAKCLR** ($66 / $DD) [XC 13, 14, 17, 18]. SCREEN 6: that
  value OR itself rotated by 2 -- BAKCLR $00 / $01 / $02 / $03 / $06 / $C5 give $00 / $55 / $AA / $FF / $FF / $FF
  [XC 15, 16, 23-26]: the rule, not a constant $FF; right as a 2-bit colour for BAKCLR 0-3 only. SCREEN 8: BAKCLR
  ($06 / $C5) [XC 19, 20].
- 212 lines in SCREEN 5-8 (the bytes after $69FF / $D3FF untouched) [XC 13-20].
- The mode is SCRMOD's: with the VDP and the register copies in SCREEN 5 and SCRMOD 0, CLS wrote spaces at $0000 /
  $03B0 and left the bitmap at $69F0 [XC 36].
- Interrupts: SCREEN 2-8 return with them ON from a DI entry [XC 9-20]. SCREEN 0 KEEPS the entry state: off from a
  DI entry [XC 5, 6], on from an EI entry [XC 33]; SCREEN 1 returns off from a DI entry [XC 7, 8] (EI entry not run).

## Differences from the reference

C-BIOS's MSX2 / MSX2+ builds (the subject) clear the same areas and take the mode from SCRMOD too, but: SCREEN 5 / 7
with BAKCLR $C5 fill $55 (the references $DD), SCREEN 6 fills $A2 / $51 for $06 / $C5 and $51 / $A2 / $F3 for $01 /
$02 / $03 (the references $FF / $FF and $55 / $AA / $FF); in SCREEN 0 / 1 they return with interrupts ON; other
A / F ([scratchpad/AE_xsubcls_msx2.out](../../../scratchpad/AE_xsubcls_msx2.out)).

## Open (not measured)

Recorded per case: registers, F set apart from A (§3a), interrupt state, CSRX / CSRY, LINTTB,
R#0-R#46, S#2, all copies, the palette, VRAM over 128 KB (block sums plus each page's first and last
line and the lines 192-255 of each page).

| case | inputs | state | what it separates | HB-F900 | NMS 8250 | FS-A1WSX |
|---|---|---|---|---|---|---|
| IE | the page's base case (its first row) | entered once with DI, once with EI | **decided for SCREEN 0** (DI -> off [XC 5, 6], EI -> on [XC 33]: kept); SCREEN 1 and 2-8 from an EI entry still open (DI entry gives off / on) | kept (S0) | kept (S0) | kept (S0) |
| CL-Z | Z set / clear, A and carry set independently | SCREEN 0 and 5 | Z gate present in the sub-ROM entry or not | ? | ? | ? |
| CL-0..8 | FORCLR $3A, BAKCLR $C5, BDRCLR $F9 | SCRMOD 0..8, VDP in that mode, VRAM garbage | per-mode fill: what, where -- **0-3, 5-8 decided** [XC 5-26]; SCREEN 4 open. Mode from SCRMOD vs the copies **decided: SCRMOD** [XC 36] | ? | ? | ? |
| CL-OOR | — | SCRMOD 9, $FF | out-of-range rule | ? | ? | ? |
| CL-YJK | BAKCLR $C5 | SCRMOD 10, 11, 12, VDP in that mode where the machine has it | fill byte in the YJK modes vs out of range | ? | ? | ? |
| CL-BUSY | SCREEN 5, 8 | a long VDP command running (S#2 CE = 1) at entry | waits vs overwrites | ? | ? | ? |
| CL-AC | SCREEN 7 ACPAGE 1 / DPPAGE 0; SCREEN 5 ACPAGE 3 / DPPAGE 2 and 2 / 1 | — | clears ACPAGE vs DPPAGE vs page 0 | ? | ? | ? |
| CL-LN | SCREEN 5, 8 | R#9 bit 7 set / clear (copy ≠ VDP) | 192 vs 212 vs 256 lines | ? | ? | ? |
| CL-BK | SCREEN 5, 6, 7, 8 | BAKCLR $06, $C5 (measured [XC 13-20]), $00-$03 in SCREEN 6 (measured [XC 23-26]); $0F, $FF still open | fill byte: nibble doubled vs 2-bit packed vs whole byte -- decided per mode (Measured); $0F / $FF only confirm | ✓ | ✓ | ✓ |
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
