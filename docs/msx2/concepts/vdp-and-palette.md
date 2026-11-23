<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# The MSX2 VDP, sprites and the palette — shared facts for the sub-ROM calls

> **Concept page, DRAFT 0 (2026-11-23),** from the published interface only; nothing measured yet.
> It holds the facts several sub-ROM pages share, so each call page links here instead of
> restating them ([spec-method §1](../../spec-method.md)). Per-call state never goes here.

Pages that rely on it: [CLRSPR](../sub/CLRSPR.md), [CALPAT](../sub/CALPAT.md),
[CALATR](../sub/CALATR.md), [GSPSIZ](../sub/GSPSIZ.md), [GETPAT](../sub/GETPAT.md),
[NWRVRM](../sub/NWRVRM.md), [NRDVRM](../sub/NRDVRM.md), [WRTVDP](../sub/WRTVDP.md),
[VDPSTA](../sub/VDPSTA.md), [INIPLT](../sub/INIPLT.md), [RSTPLT](../sub/RSTPLT.md),
[GETPLT](../sub/GETPLT.md), [SETPLT](../sub/SETPLT.md); the block transfers have
[their own page](block-transfer.md).

## Sources and tags

`[P x]` cites the **MSX2 Technical Handbook** (ASCII), in Konamiman's public English translation
(github.com/Konamiman/MSX2-Technical-Handbook, `md/`):
- `4§n` — chapter 4 (the VDP), section n; `2§n` — chapter 2 (BASIC 2.0);
- `A1 NAME` — Appendix 1, the BIOS listing, entry NAME (sub-ROM part unless "main" is said);
- `A3 §n` — Appendix 3, bit block transfer; `A4 NAME` — Appendix 4, the work area, cell NAME;
  `A5 SCREEN n` — Appendix 5, the VRAM map.

`[A]` marks an assumption: not measured, not in the handbook. Clean room as for the MSX1 pages
([allowed-sources.md](../../allowed-sources.md)): C-BIOS's source is consulted only for WHICH
entries it implements, never as the reference.

**References to measure:** Sony HB-F900 (MSX2, Japanese), Philips NMS 8250 (MSX2, European),
Panasonic FS-A1WSX (MSX2+). **Subject:** C-BIOS's MSX2 and MSX2+ sub-ROMs. The FS-A1WSX has the
MSX2+ VDP, with registers and screen modes (SCREEN 10-12) the MSX2 handbook does not cover; every
statement below about the register set is the handbook's MSX2 VDP.

**No generation's behaviour is assumed to carry over (Joost, 2026-11-23).** Every case runs on all
three references and its record has one column per machine; the FS-A1WSX's result is its own
reading, and a rule that holds on one generation only names that generation. Where the MSX2+ may
differ (its VDP's registers, SCREEN 10-12, a changed sub-ROM), a page has a row whose expected
value is open per machine.

## Calling a sub-ROM entry

The caller puts the entry address in IX and calls EXTROM; a caller that must keep IX pushes it and
jumps to SUBROM instead [P A1 SUB-ROM]. EXBRSA ($FAF8) holds the sub-ROM's slot address
[P A4 EXBRSA]. The "Registers" line of each A1 entry names the registers the call may change;
whether IX, IY, the alternate set and the interrupt state survive is [A]. Each page's matrix
records them (see *How every case is recorded*), and a **control call** — a sub-ROM entry with no
VDP effect (GSPSIZ), made through the same EXTROM path — tells the path's effect from the call's.

## VDP registers and their RAM copies

- Control registers R#0-R#23 and R#32-R#46; R#24-R#31 do not exist [P 4§1.1, Table 4.1] (on the
  MSX2 VDP). R#0, R#1, R#8 and R#9 are the mode registers #0-#3 [P 4§1.1, Table 4.1]; the screen
  mode bits are in R#0 / R#1 [A: the handbook's per-mode settings figures]. Registers are
  write-only; BASIC's `VDP(n)` reads the RAM copy, not the VDP [P 4§2.1.1].
- The RAM copies: R#0-R#7 at RG0SAV-RG7SAV ($F3DF-$F3E6), R#8-R#23 at $FFE7-$FFF6 [P 4§2.1.1].
  The byte after them, $FFF7, holds the main ROM's slot address [P A4, Figure A.5]. No copy of
  R#32-R#46 is named [P 4§2.1.1].
- A register is written directly through port #1 (the data, then a byte 10 followed by the
  register number in five bits) or indirectly through R#17 and port #3 [P 4§2.1.1, Fig 4.2-4.4].
  Five bits reach R#0-R#31 only, so R#32-R#46 cannot be named that way as printed; the width the
  VDP decodes is [A].
- Status registers S#0-S#9, read-only, read through port #1 after selecting S#n with R#15; the
  handbook says to disable interrupts while doing so and to set R#15 back to 0 afterwards
  [P 4§1.1 Table 4.2, 4§2.1.3]. STATFL ($F3E7) stores S#0's contents [P A4 STATFL].
- Reading has side effects: reading S#5 resets S#3-S#6 [P 4§5.3.3]; S#7 carries the colour a
  command fetched and its TR bit (S#2 bit 7) governs the transfer [P 4§6.5.6]; S#2 bit 0 is CE,
  1 while a command runs [P 4§6.2]. That reading S#0 clears its interrupt flag is [A].

## VRAM

- 128 KB of VRAM plus an optional 64 KB of expansion RAM; a 17-bit address counter. R#14 holds
  A16-A14; R#45 bit 6 selects the expansion RAM, which an MSX2 does not use [P 4§1.2, 4§2.2].
- MODE ($FAFC): bits 2-1 the VRAM size (00 16 KB, 01 64 KB, 11 128 KB, as the translation prints
  it); bit 3 whether VRAM addresses are ANDed with $3FFF in SCREEN 0-3 (never in SCREEN 4-8)
  [P A4 MODE].
- DPPAGE ($FAF5) the display page, ACPAGE ($FAF6) the active page [P A4]. In SCREEN 5-8 the
  addresses BASE returns are offsets from the active page's start [P 2§2.5].

## Sprites: mode 1 and mode 2

- Sprite mode 1 in SCREEN 1-3, sprite mode 2 in SCREEN 4-8 [P 4§5.1]. Sizes 8 x 8 and 16 x 16 (R#1
  bit 1), magnification R#1 bit 0, in both modes [P 4§5.2.2, 4§5.3.2].
- Pattern table: 256 patterns of 8 bytes; a 16 x 16 sprite uses four consecutive ones; base from
  R#6 (A16-A11) [P 4§5.2.2, Fig 4.60].
- Attribute table: 32 planes x 4 bytes, base from R#5 (A14-A10) and R#11 (A16-A15)
  [P 4§5.2.2, Fig 4.61]. Mode 1: Y, X, pattern, EC + colour; Y = 208 ($D0) hides that plane and
  all after it [P 4§5.2.2]. Mode 2: Y, X, pattern, and the fourth byte unused; the stop value is
  216 ($D8) [P 4§5.3.2, Fig 4.66].
- **Mode 2 colour table:** 512 bytes immediately below the attribute table, 16 bytes per plane, one
  per sprite line: bit 7 EC, bit 6 CC, bit 5 IC, bit 4 0, bits 3-0 the colour [P 4§5.3.2,
  Fig 4.67]. Nothing names a separate base cell for it [P 4§5.3.2].
- Mode 2 shows eight sprites per line (mode 1 four); R#8 bit 1 = 1 hides all sprites
  [P 4§5.3.1, 4§5.3.2].
- Default VRAM tables per mode, including the sprite colour table, are listed in [P A5].
- The cells the sprite calls read: SCRMOD ($FCAF), RG1SAV ($F3E0), PATBAS ($F926), ATRBAS ($F928),
  FORCLR ($F3E9) [P A4]. ATRBAS / PATBAS are 16-bit cells; how a sub-ROM call forms a 17-bit VRAM
  address from them (ACPAGE? the copies of R#11 / R#6?) is [A].

## The palette

- Sixteen palette registers P#0-P#15, 9 bits each: 3 bits of red, green and blue [P 4§1.1].
- Written by setting the number in R#16 (low four bits), then two bytes to port #2: first red in
  bits 6-4 and blue in bits 2-0, then green in bits 2-0; R#16 then steps to the next register
  [P 4§2.1.2, Fig 4.5]. Port #2 is listed for writing only, so **the VDP's palette cannot be read
  back by the CPU** [P 4§1.3, Table 4.3]: a call that returns a palette entry must read a copy.
- The BIOS interface packs an entry as one byte of red (high nibble) and blue (low nibble), plus
  green in the low nibble of a second byte [P A1 GETPLT, SETPLT]. Which bit of each nibble is
  ignored, and by whom (the call, or the VDP), is [A].
- The power-on palette is Table 2.5 of [P 2§2.2] (red / blue / green brightness 0-7 per entry;
  entry 0 transparent, 1 black, 15 white 7/7/7).
- Colour 0 is transparent unless R#8 bit 5 is set [P 4§4 "colour code 0", 2§2.2]. SCREEN 8 has no
  palette: BASIC's `COLOR=(...)` does nothing there [P 2§2.2].
- **The VRAM save area ("palette table"):** BASIC's `COLOR=RESTORE` loads the palette from it
  [P 2§2.2]. Its place depends on the screen mode — six places [P A5]:

  | SCREEN | palette table |
  |---|---|
  | 0, width 40 (TEXT 1) | $0400-$042F |
  | 0, width 80 (TEXT 2) | $0F00-$0F2F |
  | 1, 3 | $2020-$204F |
  | 2, 4 | $1B80-$1BAF |
  | 5, 6 | $7680-$76AF |
  | 7, 8 | $FA80-$FAAF |

  48 bytes each. The handbook does not give the layout inside the 48 bytes (16 entries x 2 bytes
  would fill 32), nor whether in SCREEN 5-8 the table moves with ACPAGE / DPPAGE, nor what decides
  between the two SCREEN 0 places (LINLEN? LINL40? the VDP mode copies? SCRMOD alone?) [A].

## How every case is recorded

The probes run under openMSX. Registers, RAM, VRAM and I/O are readable state; ROM bytes never are
([allowed-sources.md](../../allowed-sources.md)). Unless a row says otherwise, every case:
- presets AF, BC, DE, HL, IX, IY **and AF', BC', DE', HL'** to garbage unlike the inputs, two sets
  ([spec-method §3a](../../spec-method.md)), and records them all after the call;
- **diffs the whole of RAM** before and after (so a palette copy, a register copy at RG0SAV + C, or
  a STATFL write is found wherever it lies);
- snapshots by the emulator's debugger: R#0-R#46 (and the FS-A1WSX's further registers), S#0-S#9,
  the 16 palette registers, the VRAM address counter and its read / write mode;
- logs every write to ports $98-$9B with the CPU's IFF1 at that moment (the call's own interrupt
  discipline, and "the call masks a value" vs "the VDP ignores the bits");
- records VRAM by block sums plus windows round every table touched, or whole where the page says;
- reads the interrupt state twice after the call, and runs the control call.

## States the measurements must desync

These recur across the pages; each page's matrix says which ones it uses.
- **The VDP vs its RAM copies:** every register preset different from its copy (RGnSAV, $FFE7+),
  so "reads the copy" and "the call wrote it" differ; R#17 and R#15 preset distinctive.
- **SCRMOD vs the mode bits in the copies** (RG0SAV / RG1SAV / $FFE7, R#8's copy), and the VDP's
  own registers vs both; **sprite mode vs SCRMOD** (SCRMOD 4 with mode-1 register copies).
- **ATRBAS / PATBAS vs the copies of R#5 / R#11 ($FFEA) / R#6**, and the default tables vs moved
  ones.
- **ACPAGE vs DPPAGE vs R#14 vs the copy of R#2 (the displayed page)**, each different and non-zero,
  in SCREEN 5-8; MODE's VRAM size and mask bit.
- **LINLEN vs LINL40** and the TEXT 1 / TEXT 2 copies of the mode bits, for SCREEN 0.
- **Palette in the VDP vs the VRAM table (per mode, per page) vs the power-on table:** three or
  more different palettes, set by port #2 directly and by VRAM writes through the ports.
- **A VDP command running** (CE = 1) at entry.
- **Interrupt state** on entry (on and off), and a frame interrupt due during the call.

## Related pages

[block-transfer.md](block-transfer.md); the MSX1 pages these extend:
[CLRSPR](../../bios/CLRSPR.md), [WRTVDP](../../bios/WRTVDP.md), [RDVRM](../../bios/RDVRM.md);
[screen modes](../../concepts/screen-modes.md).
