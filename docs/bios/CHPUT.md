<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# `CHPUT` ($00A2) — write one character to the screen

> **Spec:** DRAFT 3 (2026-11-17) — one review pass, answered by a second measurement round.
> Measured on the Philips VG-8020 (the main-BIOS reference) by calling CHPUT directly, in
> SCREEN 0 at width 40. The cursor results agree with an earlier reading on the Panasonic
> CF-3300 through its BDOS.

## Summary

`CHPUT` writes the character in A to the text screen at the cursor and moves the cursor on. For a
control code or an escape sequence it moves the cursor or edits the screen instead. `PRINT` and
the MSX-DOS console both end up here.

zerobas does the same for every byte and every escape command measured, with these exceptions:
- **DEL (127):** the reference moves back one column and blanks that cell (nothing shifts; at
  column 1 it wraps to the row above); zerobas blanks the cell under the cursor and stays.
- **`ESC l`:** both blank the line, but the reference leaves the cursor where it was, and zerobas
  moves it to the line's start.

- **`ESC Y` out of range:** the reference clamps to the screen; zerobas stores any position
  (TODO **D-CHPUTESCY**).
- **The function-key line:** with it on, the reference keeps the cursor off the key row; zerobas
  writes over it (TODO **D-CHPUTKEYROW**).

DEL and `ESC l` are TODO **D-CHPUTDEL**.

## The specification

Reference: the Philips VG-8020's main BIOS. Second: the Panasonic CF-3300's. Ours: the C-BIOS
repack's CHPUT (the `cbios-repack` patches).
The region's shared facts (the screen, the cursor cells) are on
[the screen editor page](../concepts/screen-editor.md).

**Evidence.**
- **[XCH n]**: case `n` of the XCHPUT matrix, [`scratchpad/XCH_table.out`](../../scratchpad/XCH_table.out)
  (read its header: setup, columns). Program `probes/bios/spec/xchput.asm`, run through
  `probes/bios/biosl_run.py` on its NODISK row, the VG-8020 against zerobas; the raw run is
  [`scratchpad/XCH_run1.out`](../../scratchpad/XCH_run1.out).
  - Before every case the cursor is at CSRY 11, CSRX 21 (1-based), in SCREEN 0 width 40, on a
    `Q` with `P` left of it and `R` right of it.
  - Each case records CSRX, CSRY, the A CHPUT returned, and those three cells (VRAM).
  - Modes: 0 = the byte alone (cases 0–255); 1 = ESC, then the byte (256–511); 2 = the graphic
    prefix 1, then the byte (512–767).
- **[X2 Gn.i]**: case `i` of group `n` of the round-2 rung XCHPUT2,
  [`scratchpad/XCH2_table.out`](../../scratchpad/XCH2_table.out) (each group's setup is in
  `probes/bios/spec/xchput2.asm`'s header; raw run [`scratchpad/XCH2_run1.out`](../../scratchpad/XCH2_run1.out)):
  G1 TAB from every column, G2 the screen's corners with the key line off and on, G3 ESC / the
  prefix then a control code then `A`, G4 the line and screen edits on a full pattern, G5 every
  byte as `ESC Y`'s parameters, G6 every byte after `ESC x` / `ESC y`.
- **[XM n]**: the CF-3300 reading through its BDOS, [`scratchpad/XM_table.out`](../../scratchpad/XM_table.out)
  (DIRIO output, mode 1; ESC + byte, mode 3), under MSX-DOS with LINLEN 29 (its table's header).
- **[A]**: assumed, NOT measured.

### 1. Interface

In: A = the character. Out:
- **A unchanged**, for every byte [XCH 0–767]: the rung passes v to CHPUT in A and records the A
  CHPUT RETURNS. In modes 1 and 2 only the second call's A is recorded. **[A]** The A after the
  ESC / prefix call itself.
- **[A]** The other registers and the flags.

### 2. One byte, the cursor and the cells after it

From CSRY 11, CSRX 21 [XCH 0–255]:

| bytes | cursor after | the cells |
|---|---|---|
| 32–126, 128–255, 28 (cursor right) | right one: CSRX 22 | a printable byte replaces the `Q` [XCH 65]; 28 writes nothing |
| 0–7, 14–27 (1, the graphic prefix, and 27, ESC, are left pending) | unchanged | unchanged [XCH 7] |
| 8 (BS), 29 (cursor left) | left one: CSRX 20; at column 1, the row above's column 40; at the top-left, stays [X2 G2.00, G2.20, G2.21] | unchanged [XCH 8] |
| 127 (DEL) | as BS [X2 G2.22] | **the cell it moves onto (left of the cursor) blanked** [XCH 127] |
| 10 (LF), 31 (cursor down) | down one: CSRY 12; on the last text row LF scrolls the screen up [X2 G2.26, G2.36] | unchanged |
| 30 (cursor up) | up one: CSRY 10 | unchanged |
| 11 (home) | CSRY 1, CSRX 1 | unchanged |
| 12 (clear) | CSRY 1, CSRX 1 | the whole screen cleared [X2 G4.7] |
| 13 (CR) | CSRX 1, same row | unchanged [XCH 13] |
| 9 (TAB) | the next stop of 8: CSRX 9, 17, 25, 33 from columns before them; from CSRX 33 on, the next row's column 1 [X2 G1.00–G1.39] | spaces written up to the stop [X2 G1] |

The CF-3300 moves the cursor identically for 0–254 [XM 256–510].

### 3. `ESC v`, the cursor after it

From the same start, ESC then v [XCH 256–511]:

| `ESC v` | cursor after | the three cells |
|---|---|---|
| A / B / C / D | up / down / right / left one | unchanged |
| H | CSRY 1, CSRX 1 | unchanged [XCH 328] |
| E, j | CSRY 1, CSRX 1 | the whole screen cleared [X2 G4.4, G4.5] |
| L | CSRX 1, same row | a blank line INSERTED: the rows below move down, the last one drops off [X2 G4.0] |
| M | CSRX 1, same row | the line DELETED: the rows below move up, a blank last row [X2 G4.1] |
| K | unchanged | erased from the cursor to the line's end [X2 G4.3] |
| J | unchanged | erased from the cursor to the screen's end [X2 G4.2] |
| l | unchanged | the whole line erased [X2 G4.6] |
| Y r c | row r − 32, column c − 32; out-of-range values CLAMPED to the last row / column 40 (r or c below 32 included; byte 1 aside) [X2 G5] | unchanged |
| x v, y v | unchanged [X2 G6] | unchanged |
| a control code | unchanged — the code itself does NOTHING (12 does not clear, 13 does not return) and the escape ends: a following `A` is printed [X2 G3.00–G3.31] | unchanged |

- **`ESC l` blanks the line, and the cursor stays** [XCH 364].
- **The CF-3300 agrees** [XM 768–1023], except `ESC TAB`: there the BDOS expanded the TAB before
  CHPUT saw it.

### 4. The graphic prefix

- **Prefix then a byte 64–95** writes that byte − 64 (a graphic code $00–$1F) and moves right
  [XCH 576–607; e.g. `1`, `A` writes $01, 577].
- **Prefix then a byte 32–63 or 96–255, DEL excepted,** writes the byte itself and moves right
  [XCH 544–575, 608–638, 640–767].
- **Prefix then DEL** acts as DEL [XCH 639].
- **A control code after the prefix acts as itself and cancels the prefix:** `1`, BS moves left
  and writes nothing [XCH 520]; `1`, TAB tabs [XCH 521]; `1`, clear clears [XCH 524]; a following
  `A` is a plain `A` [X2 G3.32–G3.63].
- **After ESC, byte 1 still acts as the prefix:** ESC, 1, `A` writes $01 [X2 G3.01].

## Differences from the reference

All [XCH]; nothing else in the 768 cases differs, A and the three cells included. (XCH 333,
`ESC M`, agrees by construction, not by evidence: see §3.)

| case | VG-8020 | zerobas |
|---|---|---|
| DEL [XCH 127; after the prefix 639] | CSRX 20; `P` blanked, `Q R` kept | CSRX 21; `Q` blanked, `P R` kept |
| `ESC l` [XCH 364; X2 G4.6] | CSRX 21; the line blanked | CSRX 1; the line blanked |
| DEL at column 1 [X2 G2.22, G2.62] | the row above's column 40 | stays; in the last cell of the last row it scrolls the screen [X2 G2.32] |
| `ESC Y` out of range [X2 G5: 446 of 512] | clamped to the screen | the byte − 32 stored as is (CSRY 225, 255, 25 ...) |
| key line on [X2 G2.40–G2.79] | the cursor stays off the key row (row 24) | the cursor goes onto row 24; the key line is written over |
| LINTTB [X2 G2, every case] | 24, 23, …, 1 down the rows | 1 on every row (both: non-zero = the row starts a logical line) |

TODO items: **D-CHPUTDEL** (DEL, `ESC l`), **D-CHPUTESCY**, **D-CHPUTKEYROW**, **D-LINTTBVAL**.

## Open (not measured)

- **[A]** The registers other than A, and the flags.
- **[A]** LINTTB beyond a clear: what a wrap, the scroll and `ESC L` / `ESC M` do to it; and what the
  VG-8020's values 24 … 1 mean.
- **[A]** What `ESC x` / `ESC y` actually change (G6 read the cursor and $FCA9–$FCAA only).
- **[A]** The cursor block's drawing (CSRSW), and whether BEL sounds.
- **[A]** The cursor at the screen's last column (the wrap), on its last row (the scroll), at
  other widths (32, 37, 80), and in the graphic modes.
- **[A]** Whether CHPUT goes through the hook H.CHPU ($FDA4), and with interrupts in which state.
- **[A]** `ESC K` / `ESC J`, cells beyond the three read.

## Tests that cover it

`biosl-acceptance` rung b1text: CHPUT's happy path, VG-8020 against zerobas (L3 in
tools/bios_levels.py). The matrix above is spec evidence, not yet a gate. It joins one through the
test audit ([docs/spec-method.md](../spec-method.md) §8) once this page is FINAL.
