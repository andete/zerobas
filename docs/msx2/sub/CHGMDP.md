<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `CHGMDP` (sub-ROM $01B5) — change the screen mode and reset the palette

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the HB-F900, NMS 8250 and FS-A1WSX ([xmode.asm](../../../probes/bios/spec/xmode.asm), [scratchpad/AE_xmode_msx2.out](../../../scratchpad/AE_xmode_msx2.out), decoded by [scratchpad/xmode_decode.py](../../../scratchpad/xmode_decode.py) into [scratchpad/AE_xmode_msx2_decoded.out](../../../scratchpad/AE_xmode_msx2_decoded.out); round 2 [xmode2.asm](../../../probes/bios/spec/xmode2.asm), [scratchpad/AE_xmode2_msx2.out](../../../scratchpad/AE_xmode2_msx2.out), decoded by [scratchpad/xmode2_decode.py](../../../scratchpad/xmode2_decode.py) into [scratchpad/AE_xmode2_msx2_decoded.out](../../../scratchpad/AE_xmode2_msx2_decoded.out)).
>
> Goldfish pass 1 (test writer) 2026-11-23: 7 findings, 5 measured, 1 moved to open.

## Summary

`CHGMDP` is [CHGMOD](CHGMOD.md) plus a palette reset: it switches to the mode in A, sets the 16 palette entries to
the default palette and saves them (32 bytes) at the new mode's palette table in VRAM. Shared facts:
[the screen-modes page](../concepts/screen-modes.md).

## The specification

Case numbers as on [CHGMOD](CHGMOD.md#the-specification): `[M xmode r]` round 1, `[M xmode2 n]` round 2 (palette
:= 16 non-default entries and VRAM := $5A before the call). The three references agree on every output.

**Interface.**
- In: A = the screen mode, 0 to 8 [P App. 1, SUB-ROM CHGMDP]; A 0, 5 and 8 measured [M xmode2 9-11; xmode 22].
- Out: A $07, F $10, BC $0001, DE $1007; IX the entry ($01B5) for A 5 / 8, $000C for A 0; IY and the alternates kept
  [M xmode2 9-11]. Registers: all may change [P App. 1, SUB-ROM CHGMDP].
- Interrupts on return: **ON**, after a DI entry and after an EI entry [M xmode2 9-11; xmode 22] -- unlike CHGMOD,
  which returns them as entered.

**Behaviour.**
- The mode: as CHGMOD with the same A -- the same VDP registers, copies and cells [M xmode2 9 vs 0, 11 vs 5 (equal
  but for the inputs the cases set differently: colours, RG9SAV); xmode 22 vs 5].
- The palette: all 16 entries := the default palette, the same for A 0, 5 and 8 (SCREEN 8 included): entries 0-15
  (R·16 + B, G) = 00 00, 00 00, 11 06, 33 07, 17 01, 27 03, 51 01, 27 06, 71 01, 73 03, 61 06, 64 06, 11 04, 65 02,
  55 05, 77 07 [M xmode2 9-11].
- Saved in VRAM at the **new** mode's palette table [P App. 1, INIPLT; App. 5]: $0400 for A 0, $7680 for A 5,
  $FA80 for A 8 hold the 16 entries, 2 bytes each in the order above (the first 6 entries read back), and exactly
  **32** bytes are written there (VRAM counts: CHGMOD's + 32) [M xmode2 9-11]. App. 5's 48-byte bound is not filled.
- So "CHGMDP = CHGMOD then INIPLT" holds for the VDP, the cells, VRAM and the palette; the outputs that differ are the
  registers on return and the interrupt state (CHGMOD: as entered; CHGMDP: on) [M xmode2 9-11 vs 0, 5].

## Differences from the reference

C-BIOS's MSX2 / MSX2+ builds set the same mode, palette and VRAM palette table; they return other registers (F $A8,
BC $0010, DE $8800) [M xmode2 9-11]. In round 1 their R#17 (the indirect-register pointer, internal) was $18 where the
references leave $2C; R#16 was $00 on both [M xmode 22].

## On the turbo R

Measured 2026-11-23 (D-TRSPEC) on the FS-A1GT / FS-A1ST: every register, VRAM sum and work-area byte is the FS-A1WSX's, on both models. What differs is the machine and the timing, not the call: $FFF8 = $FF as the boot leaves it (the A1WSX $00; no screen-mode call touches it), VDP S#2 read at a random moment, R#36 = $80 before case 0 (the boot's last VDP command), power-on cells, and one JIFFY count in xmode2 case 27 [M] ([AE_trall/xmode.out](../../../scratchpad/AE_trall/xmode.out), [AE_trall/xmode2.out](../../../scratchpad/AE_trall/xmode2.out); overview: [turbor/remeasured.md](../../turbor/remeasured.md)).

## Open (not measured)

Recorded per case: as [CHGMOD](CHGMOD.md#open-not-measured) (the palette and the palette table included).

| case | inputs | state | what it separates | HB-F900 | NMS 8250 | FS-A1WSX |
|---|---|---|---|---|---|---|
| IE | A 0 | entered once with DI, once with EI | interrupt state on return | on / on [M xmode2 9, 10] | on / on | on / on |
| CP-EQ | A = 1, 2, 3, 4, 6, 7 | same set-up as CHGMOD's cases | = CHGMOD + INIPLT, output for output (A 0, 5, 8 measured: equal but for registers and interrupts) | ? | ? | ? |
| CP-PAL | A = 0, 5, 8 | palette entries distinct non-defaults | the reset palette's 16 values | the default palette above [M xmode2 9-11] | same | same |
| CP-SAVE | A = 0 at 80 columns (table $0F00), 1, 2 | VRAM at every App. 5 palette address $5A | saved at the new mode's address vs the old one's (A 0 / 5 / 8: the new one) | ? | ? | ? |
| CP-OOR | A = 9, $FF | palette non-default | CHGMOD's out-of-range rule (no change), palette reset anyway? | ? | ? | ? |
| CP-YJK | A = 10..12 on the MSX2+ | — | palette in YJK modes (CHGMOD ignores 10-12) | ? | ? | ? |

## Related pages

[The screen-modes page](../concepts/screen-modes.md); [CHGMOD](CHGMOD.md); [INIPLT](INIPLT.md).

## Tests that cover it

none yet
