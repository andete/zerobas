<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# Screen modes on the MSX2 / MSX2+ — the sub-ROM's mode and text entries

> **Spec:** DRAFT 0 (2026-11-23), from the published interface only; nothing measured yet. References to measure: HB-F900, NMS 8250, FS-A1WSX.

## Summary

An MSX2 has a V9938 VDP ("MSX-VIDEO") with up to 128 KB of VRAM and ten display modes, reached with
`SCREEN 0` to `SCREEN 8`; an MSX2+ has the V9958 and adds `SCREEN 10` to `SCREEN 12`. The sub-ROM
(the MSX2's second BIOS ROM, called through `EXTROM` / `SUBROM`) carries the calls that switch modes,
set the colours, clear the screen and switch pages. This page holds the facts those calls share:
the mode table, which VDP registers carry what in each mode, the default table addresses, and the
work-area cells. Each call's page links here and states only its own behaviour.

The MSX1 four-mode page is [docs/concepts/screen-modes.md](../../concepts/screen-modes.md); the
MSX1 main-BIOS pages of the same names (e.g. [CHGMOD](../../bios/CHGMOD.md),
[INITXT](../../bios/INITXT.md)) are the finished models for what to measure.

**Sources.** [P §n] cites the MSX2 Technical Handbook (Konamiman's English edition): App. 1 the BIOS
listing, App. 4 the work area, App. 5 the VRAM map, Ch. 4 the VDP, Ch. 5 §6 the clock chip, Ch. 2
§2.10 `SET`. [A] is assumed. The MSX2+ modes have no handbook source; every statement about them is [A].

## Calling a sub-ROM entry

- A sub-ROM entry is called with IX = its sub-ROM address and `CALL EXTROM` (main ROM $015F); `SUBROM`
  ($015C) is the variant for a caller that pushes IX first [P App. 1, SUB-ROM; EXTROM / SUBROM].
- Through either, the alternate registers and IY are kept [P App. 1, EXTROM / SUBROM]. IX's value
  on return is [A].
- EXBRSA ($FAF8) holds the sub-ROM's slot address [P App. 4, "Work area added in MSX2"].
- Several main-ROM mode calls (CHGMOD, INITXT ... SETMLT, CLS, CLRSPR) are marked "always call
  SUB-ROM" [P App. 1, notation \*3]; DSPFNK and WRTVDP / GRPPRT "call SUB-ROM in screen modes 5 to 8"
  (\*2). Whether a main-ROM call and its sub-ROM namesake leave identical outputs is [A] and is a
  matrix row on each call's page.
- The interrupt state on return, and whether the call enables interrupts, is [A] for every entry.

## The modes

Mode bits: M3 = R#0 bit 1, M4 = R#0 bit 2, M5 = R#0 bit 3, M1 = R#1 bit 4, M2 = R#1 bit 3
[P Ch. 4 §3, Figures 4.11, 4.15, 4.21, 4.26, 4.31, 4.36, 4.39, 4.42, 4.45].

| SCREEN | VDP mode | R#0 M5 M4 M3 | R#1 M1 M2 | display | sprites | source |
|---|---|---|---|---|---|---|
| 0, width ≤ 40 | TEXT 1 | 0 0 0 | 1 0 | 40 × 24 characters, 6 × 8 | none | [P Ch. 4 §3.1, Table 4.4] |
| 0, width > 40 | TEXT 2 | 0 1 0 | 1 0 | 80 × 24 (or 26.5) characters, blink | none | [P Ch. 4 §3.2] |
| 1 | GRAPHIC 1 | 0 0 0 | 0 0 | 32 × 24 characters, colour per 8 codes | mode 1 | [P Ch. 4 §3.4] |
| 2 | GRAPHIC 2 | 0 0 1 | 0 0 | 256 × 192, colour per 8 dots | mode 1 | [P Ch. 4 §3.5] |
| 3 | MULTI COLOUR | 0 0 0 | 0 1 | 64 × 48 blocks | mode 1 | [P Ch. 4 §3.3] |
| 4 | GRAPHIC 3 | 0 1 0 | 0 0 | as GRAPHIC 2 | mode 2 | [P Ch. 4 §3.5] |
| 5 | GRAPHIC 4 | 0 1 1 | 0 0 | 256 × 212 (192), 16 colours, 4 bits / dot | mode 2 | [P Ch. 4 §3.6] |
| 6 | GRAPHIC 5 | 1 0 0 | 0 0 | 512 × 212 (192), 4 colours | mode 2 | [P Ch. 4 §3.7] |
| 7 | GRAPHIC 6 | 1 0 1 | 0 0 | 512 × 212 (192), 16 colours | mode 2 | [P Ch. 4 §3.8] |
| 8 | GRAPHIC 7 | 1 1 1 | 0 0 | 256 × 212 (192), 256 colours | mode 2 | [P Ch. 4 §3.9] |
| 10, 11 | GRAPHIC 7 + YJK with YAE (R#25) | 1 1 1 | 0 0 | 256 × 212, YJK + 16 palette colours | mode 2 | [A] |
| 12 | GRAPHIC 7 + YJK (R#25) | 1 1 1 | 0 0 | 256 × 212, YJK | mode 2 | [A] |

- What `SCREEN 0` chooses between TEXT 1 and TEXT 2 is the width: BASIC's "SCREEN 0 (WIDTH 80)" is
  TEXT 2 [P Ch. 4 §3, Table 4.4]. Which cell a BIOS call reads for that choice (LINL40? LINLEN?) is
  [A], on [INITXT](../sub/INITXT.md)'s page.
- `SCREEN 9` does not exist on the handbook's machines (Table 4.4 lists none) [P Ch. 4 §3]; what
  a mode call does with A = 9 or above 12 is [A].

## The VDP registers in the modes

The register functions are [P Ch. 4 §1.1, Table 4.1]; the bit positions are [P] where cited, else [A].

| register | carries | modes |
|---|---|---|
| R#0 | mode bits M3-M5; bit 4 line interrupt enable [P Ch. 4 §4]; bit 0 external video [A] | all |
| R#1 | M1, M2; bit 6 screen on [P Ch. 4 §4]; bit 5 frame interrupt, bit 1 sprite size, bit 0 magnify [A] | all |
| R#2 | name-table base (A16-A10, with fixed low bits per mode) [P Ch. 4 §3]; in GRAPHIC 4-7 the display page [P Ch. 4 §4, "Switching the display page"] | all |
| R#3 + R#10 | colour-table base, low / high; in TEXT 2 the blink-table base [P Ch. 4 §1.1, §3.2] | 0 (TEXT 2), 1, 2, 4 |
| R#4 | pattern-generator base [P Ch. 4 §3] | 0-4 |
| R#5 + R#11 | sprite attribute base, low / high; in sprite mode 2, R#5's bits 2-0 are 1 and the sprite colour table lies 512 bytes below [P Ch. 4 §5.3.2, Figure 4.66] | 1-8 |
| R#6 | sprite pattern-generator base [P Ch. 4 §5] | 1-8 |
| R#7 | TEXT 1 / 2: text colour (high nibble) and background (low) [P Ch. 4 §3.1.3, §3.2.3]; graphic modes: border; GRAPHIC 7: all 8 bits [P Ch. 4 §4, "Screen ON/OFF"] | all |
| R#8 | bit 5 colour 0 transparent / solid [P Ch. 4 §4]; bit 1 sprites off [P Ch. 4 §5.3.2]; bit 3 VRAM type, bit 7 mouse, bit 6 light pen [A] | all |
| R#9 | bit 7 192 / 212 lines [P Ch. 4 §4]; bit 3 interlace [P Ch. 4 §4]; bit 2 even / odd page alternation, bit 1 NTSC / PAL [A] | all |
| R#12, R#13 | TEXT 2 blink colour and period [P Ch. 4 §3.2.3]; R#13 also page alternation in GRAPHIC 4-7 [P Ch. 4 §4] | 0 (TEXT 2), 5-8 |
| R#14 | VRAM access address A16-A14 [P Ch. 4 §1.1, §2.2] | all |
| R#18 | display adjust (`SET ADJUST`) [P Ch. 4 §4] | all |
| R#19 | line-interrupt line [P Ch. 4 §4] | all |
| R#23 | vertical scroll [P Ch. 4 §1.1] | all |
| R#25-R#27 | V9958 only: YJK / YAE / wait / mask bits, horizontal scroll [A] | MSX2+ |
| R#32-R#46 | VDP command registers [P Ch. 4 §1.1, §6] | 5-8 |

## The default table addresses

The VRAM map BASIC uses [P App. 5]. Modes 0-3 have screen-table cells (below); modes 4-8 have none
in the work area, so where a mode call takes their addresses from is [A] (constants, or for SCREEN 4
the GRP\* cells).

| SCREEN | name | colour / blink | patterns | sprite attr. | sprite colour | sprite patterns | palette |
|---|---|---|---|---|---|---|---|
| 0 (40) | $0000 | — | $0800 | — | — | — | $0400 |
| 0 (80) | $0000 | blink $0800 | $1000 | — | — | — | $0F00 |
| 1 | $1800 | $2000 | $0000 | $1B00 | — | $3800 | $2020 |
| 2 | $1800 | $2000 | $0000 | $1B00 | — | $3800 | $1B80 |
| 3 | $0800 | — | $0000 | $1B00 | — | $3800 | $2020 |
| 4 | $1800 | $2000 | $0000 | $1E00 | $1C00 | $3800 | $1B80 |
| 5, 6 | $0000 | — | — | $7600 | $7400 | $7A00 | $7680 |
| 7, 8 | $0000 | — | — | $FA00 | $F800 | $F000 | $FA80 |

The "palette table" is the VRAM copy of the 16 palette entries that INIPLT saves and RSTPLT restores
[P App. 1, INIPLT / RSTPLT; App. 5]. App. 5 bounds each at 48 bytes ($0400-$042F), where 16 entries of
2 bytes need 32 [A: which bytes are written is measured]. App. 5 prints SCREEN 5 / 6's sprite
patterns at $7A00, but R#6 holds only A16-A11 [P Ch. 4 §3.4, §5], so the base a register can
address is 2 KB-aligned: $7800 in R#6 is [A], and the table's real start is a measured output.

## The work-area cells

| cell | address | holds | source |
|---|---|---|---|
| LINL40, LINL32, LINLEN, CRTCNT | $F3AE-$F3B1 | widths of SCREEN 0 / 1, current width, line count | [P App. 4] |
| TXTNAM .. TXTPAT | $F3B3-$F3BC | SCREEN 0 tables (TXTCOL, TXTATR, TXTPAT "unused") | [P App. 4] |
| T32NAM .. T32PAT | $F3BD-$F3C6 | SCREEN 1 tables | [P App. 4] |
| GRPNAM .. GRPPAT | $F3C7-$F3D0 | SCREEN 2 tables | [P App. 4] |
| MLTNAM .. MLTPAT | $F3D1-$F3DA | SCREEN 3 tables | [P App. 4] |
| CSRY, CSRX, CNSDFG | $F3DC-$F3DE | cursor, key-line flag | [P App. 4] |
| RG0SAV-RG7SAV | $F3DF-$F3E6 | copies of R#0-R#7 | [P App. 4] |
| R#8-R#23 copies (RG8SAV-RG23SAV) | $FFE7-$FFF6 | "register reservation area for new VDP" | [P App. 4, Figure A.5; Ch. 4 §2.1.1] |
| FORCLR, BAKCLR, BDRCLR | $F3E9-$F3EB | colours | [P App. 4] |
| NAMBAS, CGPBAS, PATBAS, ATRBAS | $F922-$F929 | current mode's tables | [P App. 4] |
| DPPAGE, ACPAGE | $FAF5, $FAF6 | display page, active page | [P App. 4] |
| MODE | $FAFC | VRAM size (bits 2-1), and bit 3: mask VRAM addresses to $3FFF in SCREEN 0-3 | [P App. 4] |
| LINTTB | $FBB2 | line-continuation table | [P App. 4] |
| SCRMOD, OLDSCR | $FCAF, $FCB0 | current mode, "screen mode reservation" | [P App. 4] |
| R#25-R#27 copies | — | MSX2+: where they are kept [A]; located before any YJK case by a whole-RAM diff around a sub-ROM WRTVDP to R#25 / R#26 / R#27 on the FS-A1WSX | [A] |

`VDP(n)` in BASIC reads these copies, not the VDP [P Ch. 4 §2.1.1]: a copy that does not match the
VDP is a state the calls can meet, so every matrix desyncs them.

## The clock chip's screen settings

`SET SCREEN` stores the text mode's number, width, colours, key-line switch and other settings in
the clock chip, and they are applied at start-up [P Ch. 2 §2.10]. Block 2 of the clock chip holds
them: register 0 an ID, register 1 / 2 the adjust X / Y (−8 to +7), 3 the screen mode (bit 0) and interlace (bit 1),
4 / 5 the width, 6 / 7 / 8 the three colours, 9 key on / off (bit 0) among others, 10 the beep, 11 the
title colour [P Ch. 5 §6.7, Figure 5.33]; block 3 holds a title, a password or a prompt by its ID
[P Ch. 5 §6.7, Figure 5.34]. The sub-ROM entries that read these (SDFSCR, SETSCR, PROMPT) are not in
the handbook's listing; their pages are [A] throughout.

## Measuring this region — the shared apparatus

Each call's matrix assumes the MSX1 pages' apparatus ([docs/spec-method.md](../../spec-method.md)
§3a), extended for the V9938 / V9958 [A]:
- **The VDP read back by the emulator's debugger**: R#0-R#27, R#32-R#46, S#0-S#9, the 16 palette
  entries, all 128 KB of VRAM (as 1 KB block sums plus windows over every table the call names).
- **Garbage that separates**: VRAM filled address-dependently over all 128 KB (so a write to the
  wrong 64 KB half shows); palette entries set to distinct non-default values; RG0SAV-RG23SAV given
  walking-bit values that differ from what the VDP holds; R#8 / R#9 bits that the call has no reason
  to change walked one at a time: R#8 bits 1, 3, 5, 6, 7 and R#9 bits 1, 2, 3, 4, 5, 7; R#15-R#19,
  R#23 (and R#25-R#27 on the MSX2+) garbaged before every mode call.
- **Interrupts**: every page's base case is entered once with DI and once with EI (row `IE`).
- **"Nothing else"** is a whole work-area diff, $F380-$FFFF, never a list of neighbouring cells.
- **A VDP command in progress** (S#2 CE = 1) at entry, for the calls that write VRAM in modes 5-8.
- **Main-ROM \*2 / \*3 claims** are pinned by a call trace: emulator breakpoints on the sub-ROM entry
  and on EXTROM ($015F), not by comparing outputs (equal outputs do not show which code ran).
- **The previous mode as an input**: each mode call entered from at least a text mode, a GRAPHIC 1-3
  mode and a GRAPHIC 4-7 mode, with SCRMOD / OLDSCR given values different from the mode the VDP is
  actually in.
- **No generation carries over (Joost, 2026-11-23)**: every case runs on all three references and each
  machine's reading is its own; a rule that holds on one generation only names it. The matrices have
  one result column per machine, all open (`?`) until measured.
- **The references**: Sony HB-F900 (MSX2, Japanese, NTSC), Philips NMS 8250 (MSX2, European, PAL),
  Panasonic FS-A1WSX (MSX2+, Japanese). The PAL / NTSC pair separates "R#9 bit 1 is one fixed
  constant" from "a constant per machine (its region)"; "kept" vs "written" needs the bit walked against
  each machine's own default (the R#9 rows). The subject is C-BIOS's MSX2 / MSX2+ builds.

## Related pages

Calls: [CHGMOD](../sub/CHGMOD.md), [CHGMDP](../sub/CHGMDP.md), [INITXT](../sub/INITXT.md),
[INIT32](../sub/INIT32.md), [INIGRP](../sub/INIGRP.md), [INIMLT](../sub/INIMLT.md),
[SETTXT](../sub/SETTXT.md), [SETT32](../sub/SETT32.md), [SETGRP](../sub/SETGRP.md),
[SETMLT](../sub/SETMLT.md), [CHGCLR](../sub/CHGCLR.md), [CLS](../sub/CLS.md),
[CLRTXT](../sub/CLRTXT.md), [DSPFNK](../sub/DSPFNK.md), [SETPAG](../sub/SETPAG.md),
[PROMPT](../sub/PROMPT.md), [SDFSCR](../sub/SDFSCR.md), [SETSCR](../sub/SETSCR.md).
Neighbouring MSX2 regions: [the VDP and palette](vdp-and-palette.md), [the clock and the rest](clock-and-misc.md).
MSX1: [screen modes](../../concepts/screen-modes.md), [the screen editor](../../concepts/screen-editor.md),
[the shared-state map](../../bios/shared-state.md).
