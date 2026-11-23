<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `BLTDV` (sub-ROM $01A1) — save a VRAM rectangle to a disk file

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the HB-F900, NMS 8250 and FS-A1WSX ([xsubbltd.asm](../../../probes/bios/spec/xsubbltd.asm), [scratchpad/AE_xsubbltd_msx2.out](../../../scratchpad/AE_xsubbltd_msx2.out), decoded with the files read back from each machine's disk image by `scratchpad/xsubbltd.py` into [scratchpad/AE_xsubbltd_msx2_decoded.out](../../../scratchpad/AE_xsubbltd_msx2_decoded.out)). `[XD n]` = that run's case n.

## Summary

`BLTDV` writes the NX x NY rectangle at (SX, SY) to the file FNPTR names as an array — NX, NY, then the dots,
packed as the screen packs them, with no other header — the same form as a RAM array. ARG, not listed for it, is
obeyed: its direction bits reverse the read and its MXS bit reads the expansion RAM. VRAM is left as it was;
FNPTR's field is overwritten.

## The specification

The block, the array and the recording: [block-transfer.md](../concepts/block-transfer.md).

**How it was called** [M]: from H.STKE (every ROM, the disk ROM included, initialised; BASIC's work area set
up), through EXTROM with IX = the entry, A $5A, F $01 (carry set), BC $BC0C, DE $DE0E, interrupts ON, block
fields the call does not name filled with garbage ($51 + offset), and H.ERRO hooked to record E and abandon the
case. Drive A held an image the probe's script made. Calls from MSX-DOS, or with interrupts off, were not made.

### Interface

- **In:** HL = $F562; SX +0, SY +2, FNPTR +4, a dummy +6, NX +8, NY +10, CDUMMY +12 [P A3 §3]. **ARG (+13) is
  read too**, though not listed [M XD 20, 21; see Behaviour]. LOGOP (+14) is not listed; with garbage $5F there
  (cases XD 9, 13) the file held the plain dots [M]. FNPTR: a quoted name, then 0 [M XD 9].
- **Out:** carry reset [P A3 §3; M XD 9, 13, 20, 21: entered with carry set, F $54 after]; A $00, BC $0301, DE
  $0007, HL $0300 on all three references, IX by machine as BLTDM's [M XD 9, 13, 20, 21]. Interrupts ON after
  (entered on) [M]. The VDP command has ended at return (S#2's CE clear, the probe's wait found nothing running)
  [M XD 9, 13, 20, 21].

### Behaviour

- **The file is the array:** NX (2 bytes), NY (2 bytes), then the dots row by row; nothing else [M]. SCREEN 8,
  (8, 8) 8 x 4: 36 bytes, `08 00 04 00` + the 32 dots, **one byte a dot** — the handbook's "/ 2" for SCREEN 8
  does not hold [M XD 9]. SCREEN 5, 7 x 3: 15 bytes, `07 00 03 00` + 11 bytes `12 34 56 71 23 45 67 12 34 56
  70`: the dots are packed **continuously over the whole array**, two a byte, not padded per row, the last
  nibble 0 [M XD 13].
- **ARG's direction is obeyed:** ARG $04 (DIX) from SX 15 stored each row right to left (`17 16 .. 10`, ...) [M
  XD 20]. **ARG is loaded into R#45 as given:** $5E (MXC, MXS, DIY, DIX, EQ) left R#45 = $5E, SY advanced
  upwards (R#34 = 4 after SY 8) and the file 32 x $FF — the dots read from the expansion RAM, which these
  machines lack [M XD 21]. A caller that leaves garbage at $F56F therefore gets garbage (and a VDP left in
  expansion-RAM mode for its own CPU access) [M XD 21].
- **The VDP's command registers show a logical VRAM-to-CPU transfer:** R#32-R#35 = SX, SY advanced by NY,
  R#36-R#39 = the block's +4..+7 as masked by the VDP (FNPTR's field), R#40 = NX, R#42-43 = 0, R#44 = the last
  dot, R#45 = ARG [M XD 9, 13, 20, 21].
- **VRAM is not written:** the source rectangle and its surroundings read back unchanged [M XD 9, 13, 20, 21: a
  16 x 6 window over the source]. A whole-VRAM diff was not taken [A].
- **The block:** FNPTR's field (+4, +5) is overwritten with $8003; every other byte is left as given [M XD 9,
  13, 20, 21].
- The round trip is exact: [BLTVD](BLTVD.md) of DV1.PIC / DV5.PIC drew the rectangle back [M XD 10, 14].
- The three references agree in every case [M].

## Differences from the reference

C-BIOS's MSX2 / MSX2+ builds (CBIOS2_CUR_*) have no disk ROM and their machines no drive; C-BIOS's sub-ROM entry
is a stub that returns at once, and calling it is safe. Measured there with no disk mounted (every case of [XD
0-21] on all three C-BIOS builds):

| what | reference | C-BIOS |
|---|---|---|
| the file | DV1.PIC / DV5.PIC / DVX.PIC / DVG.PIC | **nothing written** (no drive) |
| block | FNPTR field := $8003 | **unchanged** |
| R#45 after ARG $5E | $5E [XD 21] | $00, as the probe set it before the call |
| registers on return | A $00, F $54 (carry clear), BC / DE / HL / IX the call's own (Interface) | **every register as entered** (A $5A, **F $01: carry still set**, BC $BC0C, DE $DE0E, HL as entered, IX = the entry) |

These are "no disk BASIC at all" readings, not a C-BIOS implementation to fix piecemeal: the whole call is
missing. Whether a C-BIOS without a disk should raise an error (as a diskless reference would) is open: no
diskless MSX2 reference was run.

## Open (not measured)

| case | inputs | state | what it separates |
|---|---|---|---|
| DV-02b | SX odd (SCREEN 5), SX mod 4 = 1, 3 (SCREEN 6) | — | a row starting mid-byte |
| DV-02c | — | SCREEN 6, 7 | bytes per dot there (SCREEN 5 and 8 measured) |
| DV-04b | ARG DIY alone; bits 0, 1, 7 | — | the order of the rows; the other bits ignored |
| DV-05 | a write-protected / full disk, then a valid call | — | the error; the directory left |
| DV-06 | SY 200 + NY 100; SY 1000 / 500 (SCREEN 7 / 8) + NY 50; SX 600 | ACPAGE 1, DPPAGE 2 | page crossing; the VRAM end; range check vs masking |
| DV-07 | name unquoted / without terminator; FNPTR inside the block / BUF | — | the name syntax (BLTDM: error 13) |
| DV-08 | HL ≠ $F562, a block at HL differing in every byte | — | HL read vs fixed (BLTDM reads HL) |
| DV-09 | — | SCREEN 1, 4; FS-A1WSX SCREEN 10-12 | refused vs run |
| DV-10 | — | a command running at entry (CE = 1) | waits vs overrides |
| DV-11 | — | a diskless MSX2 reference | error / crash |
| DV-12 | — | called from MSX-DOS with H.ERRO hooked | the error path outside BASIC |
| DV-13 | — | the whole VRAM, BUF and RAM below HIMEM after the call | what the call uses as a buffer |
| DV-14 | — | interrupts off at entry; the control call | the call's interrupt state vs the path's |

## Related pages

[BLTVD](BLTVD.md) (the inverse), [BLTMV](BLTMV.md), [BLTDM](BLTDM.md);
[block-transfer.md](../concepts/block-transfer.md).

## Tests that cover it

None yet.
