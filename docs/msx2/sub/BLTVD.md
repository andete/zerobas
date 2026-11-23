<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `BLTVD` (sub-ROM $019D) — draw an array from a disk file

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the HB-F900, NMS 8250 and FS-A1WSX ([xsubbltd.asm](../../../probes/bios/spec/xsubbltd.asm), [scratchpad/AE_xsubbltd_msx2.out](../../../scratchpad/AE_xsubbltd_msx2.out), decoded with the files read back from each machine's disk image by `scratchpad/xsubbltd.py` into [scratchpad/AE_xsubbltd_msx2_decoded.out](../../../scratchpad/AE_xsubbltd_msx2_decoded.out)). `[XD n]` = that run's case n.
>
> Goldfish pass 1 (test writer) 2026-11-23: 17 findings, 10 measured, 4 moved to open, 3 corrected in wording (cases XD 23-28 and 32 added for it).

## Summary

`BLTVD` reads an array — NX, NY, the dots — from the file FNPTR names and draws it at (DX, DY) with LOGOP, as
BLTVM draws one from RAM. A file BLTDV wrote and a RAM array saved as raw bytes both work. NX and NY are written
into the block from the file; FNPTR's field and the two bytes after the block are overwritten. Dots past the
right edge are dropped. A missing file goes to BASIC's error handler through H.ERRO with error 53, an unquoted
name with error 13.

## The specification

The block, the array and the recording: [block-transfer.md](../concepts/block-transfer.md).

**How it was called** [M]: from H.STKE (every ROM, the disk ROM included, initialised; BASIC's work area set
up), through EXTROM with IX = the entry, A $5A, F $01 (carry set), BC $BC0C, DE $DE0E, interrupts ON, block
fields the call does not name filled with garbage ($51 + offset), and H.ERRO hooked to record E and abandon the
case. Drive A held an image the probe's script made. Calls from MSX-DOS, or with interrupts off, were not made.
What each case records, and what it does not, is in [block-transfer.md](../concepts/block-transfer.md#how-the-disk-cases-are-recorded):
the block and the two bytes either side of it, LOGOPR, a 16 x 6 VRAM window, R#32-R#45 and S#2 — not the whole
VRAM, ACPAGE / DPPAGE, R#46 or the time taken.

### Interface

- **In:** HL = $F562; FNPTR +0, a dummy +2, DX +4, DY +6, CDUMMY +12, ARG +13, LOGOP +14 [P A3 §3]. DX, DY
  read [M XD 10, 19, 25, 26: DX 40 / 252 / 47, DY 8 / 100]; LOGOP read [M XD 11, 25]; ARG read [M XD 26].
  Whether HL or the fixed $F562 is read is [A] (VD-10). FNPTR: a quoted name, then 0 [M XD 10, 28]; the name
  unquoted (`DM3.BIN`, 0) gives error 13 (Type mismatch) through H.ERRO, nothing drawn [M XD 32].
- **Out, normal return:** carry reset [P A3 §3; M XD 10-12, 14, 19, 23-28: entered with carry set, F $54 after].
  Interrupts ON after (entered on) [M]. **The VDP command has ended at return:** S#2's CE bit was clear at the
  first read after the return, before the probe's own wait [M XD 10-12, 14, 19, 23-28, on all three].
- **Registers on return (not a contract):** A $00, BC $0300, DE $F2C4, HL $0300, IX $56D3 in every normal return
  on all three references [M XD 10-12, 14, 19, 23-28], from one entry state (A $5A, BC $BC0C, DE $DE0E); IY
  carries over from earlier calls (its value changes after an error path, not by machine). A caller should treat
  every register but F's carry as destroyed [A].
- **Out, on an error:** a missing file calls H.ERRO with E = 53 [M XD 15], an unquoted name with E = 13 [M XD
  32]; interrupts OFF; nothing drawn, NX / NY and FNPTR's field not written, $F571-$F572 not written [M XD 15,
  32].

### Behaviour

- **The file is an array:** NX (2), NY (2), then the dots. A file BLTDV wrote (DV1.PIC, SCREEN 8 8 x 4) was
  drawn exactly [M XD 10]; so were ARR.PIC, a 4 x 2 RAM array written to disk as raw bytes (no $FE header) [M
  XD 12], and LONGNAME.PIC, the same form under a 14-byte quoted name [M XD 28]. The SCREEN 5 DV5.PIC (7 x 3,
  packed over the array) was drawn as 7 dots a row; **the 8th dot of each row is left as it was** — 0 over a $00
  preset, 9 over a $99 preset [M XD 14, 27].
- **LOGOP is applied as given:** over a $55 preset, LOGOP 0 drew the dots as they are (IMP; AND / OR / EOR would
  not) [M XD 24] and LOGOP 3 drew each dot XOR $55 (EOR; OR, NOT or an off-by-one code would not) [M XD 25];
  over $FF, LOGOP 3 gave each dot XOR $FF [M XD 11]. The other codes and the T forms were not tried [A] (VD-06).
  LOGOPR ($FB02) is neither used nor written: preset to $0E (a no-op code), every case drew with the block's
  LOGOP and left LOGOPR $0E [M XD 10-12, 14, 19, 23-28].
- **ARG is obeyed:** ARG $04 (DIX) with DX 47 drew each row right to left, its first dot at x 47 [M XD 26].
  DIY, MXD and the other bits were not tried [A] (VD-08).
- **Past the right edge the dots are dropped:** DX 252 with NX 8: columns 252-255 of each row drawn with the
  row's first four dots [M XD 19]; nothing at x 0-15 of those rows or the rows below (a $99 window over x 0-15,
  Y 7-12, read back unchanged), no carry, no error [M XD 23]. R#44 ended at $43, the 4th dot of the last row,
  not $47: the call does not send the dots past the edge to the VDP at all [M XD 19, 23].
- **The block:** NX (+8) and NY (+10) := the file's NX, NY; FNPTR's field (+0, +1) := $8003, whatever the name's
  length — 9-byte names [M XD 10-12, 14, 19, 23-27] and a 14-byte one [M XD 28]; every other byte (CDUMMY,
  ARG, LOGOP, the dummy, DX, DY) left as given [M XD 10-12, 14, 19, 23-28]. What $8003 means is [A].
- **Past the block:** $F571-$F572 (in BUF, right after LOGOP) := $8003 [M XD 10-12, 14, 19, 23-28: preset $A4
  $A5]; $F55E-$F561 (before the block) are left [M].
- **The VDP's command registers after:** R#32-R#35 = the block's +0..+3 after the call, as masked by the VDP
  (FNPTR's field $8003 and the dummy: with the dummy $0123, R#34-R#35 = $23 $01) [M XD 10, 24], R#36 = DX, R#38 =
  DY advanced by NY [M XD 10, 25: 8 + 4, 100 + 4], R#40 = NX, R#44 = the last dot sent, R#45 = ARG [M XD 26: $04]
  — a CPU-to-VRAM transfer. R#46 (the command code) read $00 in every record, also where a command with a
  nonzero code must have run: it is not captured once the command has ended, so which command and code the call
  issued is not read [A] (VD-16).
- The three references agree in every case [M].

## Differences from the reference

C-BIOS's MSX2 / MSX2+ builds (CBIOS2_CUR_*) have no disk ROM and their machines no drive; C-BIOS's sub-ROM entry
is a stub that returns at once, and calling it is safe. Measured there with no disk mounted (every case of [XD
0-34] on all three C-BIOS builds):

| what | reference | C-BIOS |
|---|---|---|
| the window at (DX, DY) | the array drawn | **left as preset** (nothing drawn) |
| block | NX / NY from the file, FNPTR field := $8003 | **unchanged** |
| $F571-$F572 | := $8003 | **unchanged** |
| registers on return | A $00, F $54 (carry clear), BC / DE / HL / IX the call's own (Interface) | **every register as entered** (A $5A, **F $01: carry still set**, BC $BC0C, DE $DE0E, HL as entered, IX = the entry) |
| H.ERRO on a missing file / an unquoted name | reached, E = 53 [XD 15] / E = 13 [XD 32] | **never reached**: no error of any kind |

These are "no disk BASIC at all" readings, not a C-BIOS implementation to fix piecemeal: the whole call is
missing. Whether a C-BIOS without a disk should raise an error (as a diskless reference would) is open: no
diskless MSX2 reference was run.

## Open (not measured)

| case | inputs | state | what it separates |
|---|---|---|---|
| VD-02 | the data saved by BSAVE ... ,S | — | the other file layouts |
| VD-03 | name `"A:X.PIC"`, no 0 terminator, a string expression | — | the name syntax (unquoted: error 13, XD 32; BLTDV takes `"A:"`, XD 30) |
| VD-05 | a file shorter than its header claims | — | carry ("error in the parameters") vs error vs partial draw |
| VD-05b | a file with NX = 0 or NY = 0 in its header | — | nothing drawn vs a 0 taken as 512 / 1024 by the VDP; NX / NY written |
| VD-06 | LOGOP 1, 2, 4, 8-15, $13 | — | each operation, the T forms, the no-op codes, masking of bits 4-7 (0 and 3 measured, XD 24, 25) |
| VD-07 | DY ≥ 256 (page 1+); DY 1000 / DY 500 (SCREEN 7 / 8) + NY 50; DX 600 | — | page crossing; range check vs the VDP's masking; the VRAM end (the right edge: dropped, XD 23) |
| VD-08 | ARG DIY, bit 5 (MXD), bits 0, 1, 6, 7 | file data asymmetric in X and Y | the order of the rows; expansion RAM (DIX measured, XD 26) |
| VD-09 | FNPTR pointing inside the block / BUF | — | the name read before the block is reused vs after |
| VD-10 | HL ≠ $F562, a block at HL differing in every byte | — | HL read vs fixed (BLTDM reads HL) |
| VD-11 | — | SCREEN 1, 4; SCREEN 6, 7; FS-A1WSX SCREEN 10-12 | refused vs run; bytes per dot |
| VD-12 | — | a command running at entry (CE = 1) | waits vs overrides |
| VD-13 | — | a diskless MSX2 reference | error, carry, or crash |
| VD-14 | — | called from MSX-DOS with H.ERRO hooked | the error path outside BASIC |
| VD-15 | — | interrupts off; the control call; the whole VRAM diffed | the call's interrupt state vs the path's; nothing else written |
| VD-16 | — | R#46 read while the command runs (or the emulated time per case) | which command (LMMC / HMMC) and which code the call issues |
| VD-17 | — | ACPAGE ≠ DPPAGE, both ≠ 0 | absolute coordinates vs a page added; ACPAGE / DPPAGE written |
| VD-18 | — | the emulated time from just before to just after the call | the cost of the call (speed parity) |

## Related pages

[BLTDV](BLTDV.md) (the inverse), [BLTVM](BLTVM.md), [BLTMD](BLTMD.md);
[block-transfer.md](../concepts/block-transfer.md).

## Tests that cover it

None yet.
