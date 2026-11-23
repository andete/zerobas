<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `BLTDV` (sub-ROM $01A1) — save a VRAM rectangle to a disk file

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the HB-F900, NMS 8250 and FS-A1WSX ([xsubbltd.asm](../../../probes/bios/spec/xsubbltd.asm), [scratchpad/AE_xsubbltd_msx2.out](../../../scratchpad/AE_xsubbltd_msx2.out), decoded with the files read back from each machine's disk image by `scratchpad/xsubbltd.py` into [scratchpad/AE_xsubbltd_msx2_decoded.out](../../../scratchpad/AE_xsubbltd_msx2_decoded.out)). `[XD n]` = that run's case n.
>
> Goldfish pass 1 (test writer) 2026-11-23: 15 findings, 9 measured, 4 moved to open, 2 corrected in wording (cases XD 22, 29-31 added for it).

## Summary

`BLTDV` writes the NX x NY rectangle at (SX, SY) to the file FNPTR names as an array — NX, NY, then the dots,
packed as the screen packs them, with no other header — the same form as a RAM array. ARG, not listed for it, is
obeyed: its direction bits reverse the read and its MXS bit reads the expansion RAM. LOGOP is not. FNPTR's field
and the two bytes after the block are overwritten. An unquoted name goes to BASIC's error handler through H.ERRO
with error 13.

## The specification

The block, the array and the recording: [block-transfer.md](../concepts/block-transfer.md).

**How it was called** [M]: from H.STKE (every ROM, the disk ROM included, initialised; BASIC's work area set
up), through EXTROM with IX = the entry, A $5A, F $01 (carry set), BC $BC0C, DE $DE0E, interrupts ON, block
fields the call does not name filled with garbage ($51 + offset), and H.ERRO hooked to record E and abandon the
case. Drive A held an image the probe's script made. Calls from MSX-DOS, or with interrupts off, were not made.
What each case records, and what it does not, is in [block-transfer.md](../concepts/block-transfer.md#how-the-disk-cases-are-recorded):
the block and the two bytes either side of it, LOGOPR, a 16 x 6 VRAM window over the source, R#32-R#45 and S#2 —
not the whole VRAM, ACPAGE / DPPAGE, R#46 or the time taken.

### Interface

- **In:** HL = $F562; SX +0, SY +2, FNPTR +4, a dummy +6, NX +8, NY +10, CDUMMY +12 [P A3 §3]. SX, SY, NX, NY
  read [M XD 9, 29: (8, 8) 8 x 4 and (9, 9) 4 x 2]. **ARG (+13) is read too**, though not listed [M XD 20, 21;
  see Behaviour]. **LOGOP (+14) is not used:** with $5F there (a no-op code) and with $03 (EOR) the file held
  the plain dots [M XD 9, 13, 29]. Whether HL or the fixed $F562 is read is [A] (DV-08). FNPTR: a quoted name,
  then 0 [M XD 9]; a drive prefix (`"A:DVA.PIC"`) writes DVA.PIC to drive A [M XD 30].
- **Out, normal return:** carry reset [P A3 §3; M XD 9, 13, 20-22, 29, 30: entered with carry set, F $54 after].
  Interrupts ON after (entered on) [M]. **The VDP command has ended at return:** S#2's CE bit was clear at the
  first read after the return, before the probe's own wait [M XD 9, 13, 20-22, 29, 30, on all three].
- **Registers on return (not a contract):** A $00, BC $0301, DE $0007, HL $0300 on all three references, IX by
  machine ($F197 NMS 8250, $F196 HB-F900, $F185 FS-A1WSX, as BLTDM's) [M XD 9, 13, 20-22, 29, 30], from one
  entry state (A $5A, BC $BC0C, DE $DE0E). A caller should treat every register but F's carry as destroyed [A].
- **Out, on an error:** the name unquoted (`DM3.BIN`, 0) calls H.ERRO with E = 13 (Type mismatch), interrupts
  OFF; no file written, no VDP command started (R#36-R#45 as the probe's CHGMOD left them, R#32-R#35 as the
  case before), the block, FNPTR's field and $F571-$F572 not written [M XD 31]. A full or write-protected disk
  was not tried [A] (DV-05).

### Behaviour

- **The file is the array:** NX (2 bytes), NY (2 bytes), then the dots row by row; nothing else [M]. SCREEN 8,
  (8, 8) 8 x 4: 36 bytes, `08 00 04 00` + the 32 dots, **one byte a dot** — the handbook's "/ 2" for SCREEN 8
  does not hold [M XD 9]. SCREEN 5, 7 x 3: 15 bytes, `07 00 03 00` + 11 bytes `12 34 56 71 23 45 67 12 34 56
  70`: the dots are packed **continuously over the whole array**, two a byte, not padded per row, the last
  nibble 0 [M XD 13] — also right after a call that wrote 32 x $FF to a file (DV6.PIC, the same rectangle, the
  same 15 bytes), so it is a 0, not what an earlier write left in a buffer [M XD 22].
- **ARG's direction is obeyed:** ARG $04 (DIX) from SX 15 stored each row right to left (`17 16 .. 10`, ...) [M
  XD 20]. **ARG is loaded into R#45 as given:** $5E (MXC, MXS, DIY, DIX, EQ) left R#45 = $5E, SY advanced
  upwards (R#34 = 4 after SY 8) and the file 32 x $FF — the dots read from the expansion RAM, which these
  machines lack [M XD 21]. A caller that leaves garbage at $F56F therefore gets garbage (and a VDP left in
  expansion-RAM mode for its own CPU access) [M XD 21].
- **The VDP's command registers show a VRAM-to-CPU transfer:** R#32-R#35 = SX, SY advanced by NY [M XD 9, 29:
  8 + 4, 9 + 2], R#36-R#39 = the block's +4..+7 after the call as masked by the VDP (FNPTR's field $8003 and the
  dummy: with the dummy $0123, R#38-R#39 = $23 $01) [M XD 9, 29], R#40 = NX, R#42-43 = 0, R#44 = the last dot,
  R#45 = ARG [M XD 9, 13, 20, 21, 29]. R#46 (the command code) read $00 in every record: it is not captured once
  the command has ended, so which command the call issued is not read [A] (DV-15).
- **The source is read back as it was:** the 16 x 6 window over the source rectangle held the source dots and
  CHGMOD's fill after the call [M XD 9, 13, 20-22, 29, 30]. The window was not preset, so a call that wrote back
  the same data would pass: "VRAM is not written" is [A] (DV-13).
- **The block:** FNPTR's field (+4, +5) is overwritten with $8003, with or without a drive prefix (9- and
  11-byte names) [M XD 9, 30]; every other byte is left as given [M XD 9, 13, 20-22, 29, 30].
- **Past the block:** $F571-$F572 (in BUF, right after the block) := $8003 [M XD 9, 13, 20-22, 29, 30: preset
  $A4 $A5]; $F55E-$F561 and LOGOPR ($FB02) are left [M].
- The round trip is exact: [BLTVD](BLTVD.md) of DV1.PIC / DV5.PIC drew the rectangle back [M XD 10, 14].
- The three references agree in every case [M].

## Differences from the reference

C-BIOS's MSX2 / MSX2+ builds (CBIOS2_CUR_*) have no disk ROM and their machines no drive; C-BIOS's sub-ROM entry
is a stub that returns at once, and calling it is safe. Measured there with no disk mounted (every case of [XD
0-34] on all three C-BIOS builds):

| what | reference | C-BIOS |
|---|---|---|
| the file | DV1.PIC / DV5.PIC / DVX.PIC / DVG.PIC / DV6.PIC / DVP.PIC / DVA.PIC | **nothing written** (no drive) |
| block | FNPTR field := $8003 | **unchanged** |
| $F571-$F572 | := $8003 | **unchanged** |
| H.ERRO on an unquoted name | reached, E = 13 [XD 31] | **never reached**: no error of any kind |
| R#45 after ARG $5E | $5E [XD 21] | $00, as the probe set it before the call |
| registers on return | A $00, F $54 (carry clear), BC / DE / HL / IX the call's own (Interface) | **every register as entered** (A $5A, **F $01: carry still set**, BC $BC0C, DE $DE0E, HL as entered, IX = the entry) |

These are "no disk BASIC at all" readings, not a C-BIOS implementation to fix piecemeal: the whole call is
missing. Whether a C-BIOS without a disk should raise an error (as a diskless reference would) is open: no
diskless MSX2 reference was run.

## On the turbo R

Measured 2026-11-23 (D-TRSPEC) on the FS-A1GT / FS-A1ST: A, F, the block and the files are the FS-A1WSX's, on both models; what differs is IX's low byte after the call (ROM-internal: it differs between every machine, the A1GT and A1ST included), VDP S#2 (read at a random moment) and case 16's unwritten window (power-on RAM) [M] ([AE_trall/xsubbltd.out](../../../scratchpad/AE_trall/xsubbltd.out); overview: [turbor/remeasured.md](../../turbor/remeasured.md)).

## Open (not measured)

| case | inputs | state | what it separates |
|---|---|---|---|
| DV-02b | SX odd (SCREEN 5), SX mod 4 = 1, 3 (SCREEN 6) | — | a row starting mid-byte |
| DV-02c | — | SCREEN 6, 7 | bytes per dot there (SCREEN 5 and 8 measured) |
| DV-04b | ARG DIY alone; bits 0, 1, 7 | — | the order of the rows; the other bits ignored |
| DV-05 | a write-protected / full disk, then a valid call | — | the error; the directory left |
| DV-05b | — | no disk in drive A / a drive that does not exist (`"C:X.PIC"`) | the error number |
| DV-05c | a name that exists (BLTDV over DV1.PIC with a smaller rectangle) | — | replaced vs overwritten in place (BLTDM: the old file's tail does not survive) |
| DV-05d | NX = 0 or NY = 0 | — | an empty array vs 512 / 1024 vs an error |
| DV-06 | SY 200 + NY 100; SY 1000 / 500 (SCREEN 7 / 8) + NY 50; SX 600 | ACPAGE 1, DPPAGE 2 | page crossing; the VRAM end; range check vs masking; ACPAGE / DPPAGE added or written |
| DV-07 | name without terminator, a string expression; FNPTR inside the block / BUF | — | the name syntax (unquoted: error 13, XD 31) |
| DV-08 | HL ≠ $F562, a block at HL differing in every byte | — | HL read vs fixed (BLTDM reads HL) |
| DV-09 | — | SCREEN 1, 4; FS-A1WSX SCREEN 10-12 | refused vs run |
| DV-10 | — | a command running at entry (CE = 1) | waits vs overrides |
| DV-11 | — | a diskless MSX2 reference | error / crash |
| DV-12 | — | called from MSX-DOS with H.ERRO hooked | the error path outside BASIC |
| DV-13 | — | the whole VRAM preset and diffed, BUF and RAM below HIMEM after the call | VRAM not written; what the call uses as a buffer |
| DV-14 | — | interrupts off at entry; the control call | the call's interrupt state vs the path's |
| DV-15 | — | R#46 read while the command runs, or the emulated time per case | which command (LMCM / a byte command) the call issues |
| DV-16 | — | the emulated time from just before to just after the call | the cost of the call (speed parity) |

## Related pages

[BLTVD](BLTVD.md) (the inverse), [BLTMV](BLTMV.md), [BLTDM](BLTDM.md);
[block-transfer.md](../concepts/block-transfer.md).

## Tests that cover it

None yet.
