<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# Bit block transfer — shared facts for the BLT sub-ROM calls

> **Concept page, DRAFT 0 (2026-11-23),** from the published interface only; nothing measured yet.
> Tags and references as in [vdp-and-palette.md](vdp-and-palette.md#sources-and-tags).

The seven calls [BLTVV](../sub/BLTVV.md), [BLTVM](../sub/BLTVM.md), [BLTMV](../sub/BLTMV.md),
[BLTVD](../sub/BLTVD.md), [BLTDV](../sub/BLTDV.md), [BLTMD](../sub/BLTMD.md) and
[BLTDM](../sub/BLTDM.md) are the machine-code side of BASIC's `COPY` [P A3]. The name reads
destination first: BLT**V**M copies memory to VRAM, BLT**D**V VRAM to disk [P A3 §1-§3].

## The parameter block

Every call is entered with HL = $F562, the block's start, and the fields set there [P A3]. Whether
the calls read HL or the fixed address is [A]. The block lies inside BUF ($F55E, 258 bytes, the
line-input buffer) [P A4 BUF]. What BASIC's own line input does to it is a property of BASIC, not
of these calls: a machine-code probe cannot reach it, so it is outside these pages' measurable
set [A].

| address | size | BLTVV | BLTVM | BLTMV | BLTVD | BLTDV | BLTMD | BLTDM |
|---|---|---|---|---|---|---|---|---|
| $F562 | 2 | SX | DPTR (source in RAM) | SX | FNPTR | SX | FNPTR | SPTR |
| $F564 | 2 | SY | dummy | SY | dummy | SY | "SY", dummy | EPTR |
| $F566 | 2 | DX | DX | DPTR (destination in RAM) | DX | FNPTR | SPTR | FNPTR |
| $F568 | 2 | DY | DY | dummy | DY | dummy | EPTR | — |
| $F56A | 2 | NX | (from the data) | NX | (from the file) | NX | — | — |
| $F56C | 2 | NY | (from the data) | NY | (from the file) | NY | — | — |
| $F56E | 1 | CDUMMY | CDUMMY | CDUMMY | CDUMMY | CDUMMY | — | — |
| $F56F | 1 | ARG | ARG | ARG | ARG | — | — | — |
| $F570 | 1 | LOGOP | LOGOP | — | LOGOP | — | — | — |

All from [P A3 §1-§3]; "—" means the handbook names no field there for that call. "dummy" and
CDUMMY are "not required to be set". Whether a call ever WRITES a field (BLTVM / BLTVD filling NX
/ NY from the data, a coordinate left advanced as the VDP leaves it) is [A].

## Coordinates, ARG and LOGOP

- Commands see VRAM as one coordinate space without page division: 256 or 512 dots wide; Y runs
  0-1023 in SCREEN 5 / 6 (four pages of 256 lines) and 0-511 in SCREEN 7 / 8 (two pages)
  [P 4§6.1, Fig 4.72]. The VDP's SX / DX / NX take 9 bits and SY / DY / NY 10 [P 4§6.5.7, Fig 4.91].
  Whether a call range-checks a larger value or lets the VDP drop the high bits is [A].
- A rectangle is a vertex (SX, SY) plus NX x NY, extended in the directions DIX / DIY give
  [P 4§6.4, Fig 4.73].
- ARG is "the same as VDP R#45" [P A3 §1]: bit 2 DIX and bit 3 DIY (the direction, X and Y),
  bit 4 MXS and bit 5 MXD (source / destination in expansion RAM); bit 7 is 0
  [P 4§6.5.7, Fig 4.91].
- LOGOP is the VDP's logical-operation code: 0 IMP, 1 AND, 2 OR, 3 EOR, 4 NOT; 8-12 the same with
  T (a source dot of colour 0 leaves the destination); 5-7 and 13-15 have no operation
  [P 4§6.3, Table 4.6]. In BASIC the codes are PSET, PRESET, XOR, OR, AND and their T forms
  [P 2§2.4, Table 2.7]. LOGOPR ($FB02) is the graphics calls' own cell [P A4 LOGOPR]; whether a
  BLT call reads or writes it is [A].
- The VDP has high-speed commands, in byte units, and logical ones, in dot units [P 4§6.2,
  Table 4.5]; only the logical ones carry the operation in R#46's low bits (LMMM: [P 4§6.5.7,
  Fig 4.91]; HMMM is started by writing $D0 [P 4§6.5.3]). Which a call issues is [A].
- VDP commands are guaranteed only in GRAPHIC 4-7 (SCREEN 5-8) [P 4§6.2]. What a BLT call does in
  SCREEN 0-4 is [A]. The FS-A1WSX (MSX2+) has a later VDP with further modes (SCREEN 10-12) and
  registers the MSX2 handbook does not cover; how the calls behave there is [A].
- A command sets S#2's CE bit while it runs [P 4§6.2]; at its end the VDP leaves SY / DY advanced
  by the lines done (back for DIY = 1) and NY reduced when it met the screen edge, the other
  command registers unchanged [P 4§6.7, Table 4.7]. Whether a call returns before the command
  ends is [A].

## The array format (RAM and disk)

- An array begins with 4 bytes: NX (2 bytes), then NY (2 bytes); the dots follow [P A3 §2].
- Its size, rounded up, is NX x NY / 4 + 4 in SCREEN 6 and NX x NY / 2 + 4 in SCREEN 5, 7 and
  — as the handbook prints it — also SCREEN 8 [P A3 §2]. SCREEN 8 shows 256 colours at once
  [P 4§3.9], which needs a byte per dot [A]; whether "/ 2" there is a misprint the reference
  corrects is [A].
- "Rounded up" over the whole array, or per row, and how a row starting mid-byte is packed, are
  [A].

## The disk forms

- FNPTR points at a file name written as BASIC writes it: a quoted string, then a 0 byte (the
  handbook's example: `"B:TEST.PIC"`) [P A3 §3].
- On an error, control jumps to the BASIC interpreter's error handler; a program calling from
  MSX-DOS or a cartridge sets the hook H.ERRO ($FFB1) to handle it [P A3 §3]. That the hook is
  reached before BASIC state is changed, which errors occur with which numbers, and what is left
  open (the file, the FCB) are [A].
- The file's layout (a BSAVE-style header, or the 4-byte array header only) is not given [A].
  Calls made with no disk BASIC present (a diskless machine) are [A].

## How every BLT case is recorded

The probes run under openMSX; the emulator's debugger may read the VDP's registers, which the
CPU cannot (registers are readable state; ROM bytes are not, [allowed-sources](../../allowed-sources.md)).
Every case runs on all three references, one record column per machine; the FS-A1WSX's result is
its own reading, never assumed from the MSX2 machines (see
[vdp-and-palette.md](vdp-and-palette.md#sources-and-tags)). Unless a row says otherwise, every
case of every BLT page:
- presets ALL of VRAM (and the expansion RAM where the machine has it) with address-dependent
  garbage distinct per page, and records it whole after the call by debugger read — so "does not
  touch VRAM" is checked, not assumed;
- presets $F55E-$F572 (the block and its neighbours) with distinct garbage around the case's
  fields, and records it after — so every field the call writes back shows;
- presets LOGOPR ($FB02), ACPAGE / DPPAGE (different from each other) and records them after;
- records R#32-R#46, S#2 and R#14 by debugger snapshot, every register, F, and the interrupt
  state (read twice);
- records the emulated time between a probe point just before the call and one just after (the
  only witness for which command was used when the dots agree);
- runs a **control call** through the same EXTROM path — a sub-ROM entry with no VDP or disk
  effect (GSPSIZ) — so the interrupt state the path leaves is told from the call's own;
- for the disk calls, uses a disk image the probe made, reads the resulting file back byte for
  byte, and hooks H.ERRO to record E and return.

## States the measurements must desync (shared)

- **HL ≠ $F562,** with a valid block at $F562 and one at HL that differs in EVERY byte, the
  dummies and CDUMMY included.
- **The block crossing a page or the screen edge** on the source side and on the destination side
  (SY in another page than DY), with ACPAGE ≠ DPPAGE, both ≠ 0 (the coordinates are absolute
  [P 4§6.1], so a call that adds either disagrees); the VRAM end in SCREEN 5 / 6 (Y 1023) and
  7 / 8 (Y 511).
- **Values past the VDP's bits:** DX / SX ≥ 512, DY / SY ≥ 1024, and SCREEN 5's DX ≥ 256: a
  range check (carry, nothing done) vs the VDP's masking (drawn at the value mod 512 / 1024).
- **Overlap of source and destination,** with each DIX / DIY, and data asymmetric in both X and Y
  so a mirrored copy cannot pass as a straight one.
- **LOGOP:** each code 0-15, values with bits 4-7 set ($13, $40), T forms with a source holding
  colour 0 and others.
- **ARG:** bits 4-5 (expansion RAM), and bits 0, 1, 6, 7 set.
- **Mid-byte rows:** odd X on the screen side in SCREEN 5 and 6 (2 and 4 dots a byte).
- **Screen mode:** SCREEN 5, 6, 7, 8; SCREEN 1 and 4; on the FS-A1WSX also SCREEN 10-12.
- **A command already running** (CE = 1) at entry.
- **After a disk error,** a second, valid call (a leaked FCB or open file shows there).

## Related pages

[vdp-and-palette.md](vdp-and-palette.md); the MSX1 VRAM copies
[LDIRVM](../../bios/LDIRVM.md) / [LDIRMV](../../bios/LDIRMV.md).
