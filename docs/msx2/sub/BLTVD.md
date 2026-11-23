<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `BLTVD` (sub-ROM $019D) — draw an array from a disk file

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the HB-F900, NMS 8250 and FS-A1WSX ([xsubbltd.asm](../../../probes/bios/spec/xsubbltd.asm), [scratchpad/AE_xsubbltd_msx2.out](../../../scratchpad/AE_xsubbltd_msx2.out), decoded with the files read back from each machine's disk image by `scratchpad/xsubbltd.py` into [scratchpad/AE_xsubbltd_msx2_decoded.out](../../../scratchpad/AE_xsubbltd_msx2_decoded.out)). `[XD n]` = that run's case n.

## Summary

`BLTVD` reads an array — NX, NY, the dots — from the file FNPTR names and draws it at (DX, DY) with LOGOP, as
BLTVM draws one from RAM. A file BLTDV wrote and a RAM array saved as raw bytes both work. NX and NY are written
into the block from the file; FNPTR's field is overwritten. A missing file goes to BASIC's error handler through
H.ERRO with error 53.

## The specification

The block, the array and the recording: [block-transfer.md](../concepts/block-transfer.md).

**How it was called** [M]: from H.STKE (every ROM, the disk ROM included, initialised; BASIC's work area set
up), through EXTROM with IX = the entry, A $5A, F $01 (carry set), BC $BC0C, DE $DE0E, interrupts ON, block
fields the call does not name filled with garbage ($51 + offset), and H.ERRO hooked to record E and abandon the
case. Drive A held an image the probe's script made. Calls from MSX-DOS, or with interrupts off, were not made.

### Interface

- **In:** HL = $F562; FNPTR +0, a dummy +2, DX +4, DY +6, CDUMMY +12, ARG +13, LOGOP +14 [P A3 §3; M XD 10].
  FNPTR: a quoted name, then 0 [M XD 10].
- **Out, normal return:** carry reset [P A3 §3; M XD 10-12, 14, 19: entered with carry set, F $54 after]; A $00,
  BC $0300, DE $F2C4, HL $0300, IX $56D3 on all three references [M]. Interrupts ON after (entered on) [M]. The
  VDP command has ended at return [M XD 10-12, 14, 19: S#2's CE clear].
- **Out, on an error:** a missing file calls H.ERRO with E = 53, interrupts OFF; nothing drawn, NX / NY not
  written [M XD 15].

### Behaviour

- **The file is an array:** NX (2), NY (2), then the dots. A file BLTDV wrote (DV1.PIC, SCREEN 8 8 x 4) was
  drawn exactly [M XD 10]; so was ARR.PIC, a 4 x 2 RAM array written to disk as raw bytes (no $FE header) [M XD
  12]; the SCREEN 5 DV5.PIC (7 x 3, packed over the array) was drawn as 7 dots a row, the 8th dot of each row
  reading 0 — the preset, so "left" and "written 0" are not separated [M XD 14; A].
- **LOGOP is applied:** EOR (3) over $FF gave each dot XOR $FF [M XD 11]; LOGOP 0 drew the dots as they are [M
  XD 10]. Other codes, the T forms and ARG's bits were not tried [A].
- **Past the right edge:** DX 252 with NX 8: columns 252-255 of each row drawn with the row's first four dots,
  no carry, no error [M XD 19]; where the other four dots went (wrapped, or dropped by the VDP) was not read
  [A].
- **The block:** NX (+8) and NY (+10) := the file's NX, NY; FNPTR's field (+0, +1) := $8003; every other byte
  (CDUMMY, ARG, LOGOP, the dummy, DX, DY) left as given [M XD 10-12, 14, 19].
- The VDP's command registers after: R#32-R#35 = the block's +0..+3 as masked, R#36 = DX, R#38 = DY advanced by
  NY, R#40 = NX, R#44 = the last dot, R#45 = ARG — a logical CPU-to-VRAM transfer [M XD 10-12, 14, 19].
- The three references agree in every case [M].

## Differences from the reference

C-BIOS's MSX2 / MSX2+ builds (CBIOS2_CUR_*) have no disk ROM and their machines no drive; C-BIOS's sub-ROM entry
is a stub that returns at once, and calling it is safe. Measured there with no disk mounted (every case of [XD
0-21] on all three C-BIOS builds):

| what | reference | C-BIOS |
|---|---|---|
| the window at (DX, DY) | the array drawn | **left as preset** (nothing drawn) |
| block | NX / NY from the file, FNPTR field := $8003 | **unchanged** |
| registers on return | A $00, F $54 (carry clear), BC / DE / HL / IX the call's own (Interface) | **every register as entered** (A $5A, **F $01: carry still set**, BC $BC0C, DE $DE0E, HL as entered, IX = the entry) |
| H.ERRO on a missing file | reached, E = 53 [XD 15] | **never reached**: no error of any kind |

These are "no disk BASIC at all" readings, not a C-BIOS implementation to fix piecemeal: the whole call is
missing. Whether a C-BIOS without a disk should raise an error (as a diskless reference would) is open: no
diskless MSX2 reference was run.

## Open (not measured)

| case | inputs | state | what it separates |
|---|---|---|---|
| VD-02 | the data saved by BSAVE ... ,S | — | the other file layouts |
| VD-03 | name `"A:X.PIC"`, unquoted, no 0 terminator | — | the name syntax (BLTDM: unquoted gives error 13) |
| VD-05 | a file shorter than its header claims | — | carry ("error in the parameters") vs error vs partial draw |
| VD-06 | LOGOP 1, 2, 4, 8-15, $13 | LOGOPR preset different | each operation, the no-op codes, masking; LOGOPR used / written |
| VD-07 | DY 1000 / DY 500 (SCREEN 7 / 8) + NY 50; DX 600; the dots past DX 255 | — | clip / wrap / range check / the VRAM end |
| VD-08 | ARG DIX, DIY, bit 5 | file data asymmetric in X and Y | direction; expansion RAM |
| VD-09 | FNPTR pointing inside the block / BUF | — | the name read before the block is reused vs after |
| VD-10 | HL ≠ $F562, a block at HL differing in every byte | — | HL read vs fixed (BLTDM reads HL) |
| VD-11 | — | SCREEN 1, 4; SCREEN 6, 7; FS-A1WSX SCREEN 10-12 | refused vs run; bytes per dot |
| VD-12 | — | a command running at entry (CE = 1) | waits vs overrides |
| VD-13 | — | a diskless MSX2 reference | error, carry, or crash |
| VD-14 | — | called from MSX-DOS with H.ERRO hooked | the error path outside BASIC |
| VD-15 | — | interrupts off; the control call; the whole VRAM diffed | the call's interrupt state vs the path's; nothing else written |

## Related pages

[BLTDV](BLTDV.md) (the inverse), [BLTVM](BLTVM.md), [BLTMD](BLTMD.md);
[block-transfer.md](../concepts/block-transfer.md).

## Tests that cover it

None yet.
