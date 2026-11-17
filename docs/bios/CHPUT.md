<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# `CHPUT` ($00A2) — write one character to the screen

> **Spec:** DRAFT 2 (2026-11-17) — not yet reviewed. Measured on the Philips VG-8020 (the
> main-BIOS reference) by calling CHPUT directly, in SCREEN 0 at width 40. The cursor results
> agree with an earlier reading on the Panasonic CF-3300 through its BDOS.

## Summary

`CHPUT` writes the character in A to the text screen at the cursor and moves the cursor on. For a
control code or an escape sequence it moves the cursor or edits the screen instead. `PRINT` and
the MSX-DOS console both end up here.

zerobas does the same for every byte and every escape command MEASURED so far (§2–§4; the
parameters of `ESC Y` / `ESC x` / `ESC y` and the screen edges are not yet), with two exceptions:
- **DEL (127):** the reference moves back one column and blanks that cell (nothing shifts); zerobas
  blanks the cell under the cursor and stays.
- **`ESC l`:** both blank the line, but the reference leaves the cursor where it was, and zerobas
  moves it to the line's start.

Both are TODO **D-CHPUTDEL**.

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
| 8 (BS), 29 (cursor left) | left one: CSRX 20 | unchanged [XCH 8] |
| 127 (DEL) | left one: CSRX 20 | **the `P` (left of the cursor) blanked** [XCH 127] |
| 10 (LF), 31 (cursor down) | down one: CSRY 12 | unchanged |
| 30 (cursor up) | up one: CSRY 10 | unchanged |
| 11 (home) | CSRY 1, CSRX 1 | unchanged |
| 12 (clear) | CSRY 1, CSRX 1 | the three cells blanked [XCH 12]; **[A]** the rest of the screen |
| 13 (CR) | CSRX 1, same row | unchanged [XCH 13] |
| 9 (TAB) | CSRX 25 [XCH 9] | the two cells read (CSRX 21–22) blanked; **[A]** the stop rule (stops of 8? of 4? +4? — from CSRX 21 all give 25) and the cells at 23–24 |

The CF-3300 moves the cursor identically for 0–254 [XM 256–510].

### 3. `ESC v`, the cursor after it

From the same start, ESC then v [XCH 256–511]:

| `ESC v` | cursor after | the three cells |
|---|---|---|
| A / B / C / D | up / down / right / left one | unchanged |
| H | CSRY 1, CSRX 1 | unchanged [XCH 328] |
| E, j | CSRY 1, CSRX 1 | blanked [XCH 325, 362]: **[A]** a full clear (only three cells read) |
| L | CSRX 1, same row | blanked [XCH 332]: **[A]** insert a blank line or blank the current line (only row 11 read) |
| M | CSRX 1, same row | `P Q R` [XCH 333] — **NOT evidence**: the case before (ESC L) left that row's old contents one row down, so "delete line" and "do nothing" read the same; **[A]** |
| K, J | unchanged | `P` kept, the cursor's cell and the next blanked [XCH 330, 331]: **[A]** each one's extent |
| l | unchanged | blanked [XCH 364] |
| Y, x, y | unchanged | unchanged: **[A]** waiting for parameters, or ignored (the next case's setup hides which) |
| every other v, control codes included | unchanged | unchanged: **[A]** the escape ENDED, or the ESC still pending |

- **`ESC l` blanks the line, and the cursor stays** [XCH 364].
- **The CF-3300 agrees** [XM 768–1023], except `ESC TAB`: there the BDOS expanded the TAB before
  CHPUT saw it.

### 4. The graphic prefix

- **Prefix then a byte 64–95** writes that byte − 64 (a graphic code $00–$1F) and moves right
  [XCH 576–607; e.g. `1`, `A` writes $01, 577].
- **Prefix then a byte 32–63 or 96–255, DEL excepted,** writes the byte itself and moves right
  [XCH 544–575, 608–638, 640–767].
- **Prefix then DEL** acts as DEL [XCH 639].
- **A control code after the prefix acts as itself:** `1`, BS moves left and writes nothing
  [XCH 520]; `1`, TAB tabs [XCH 521]; `1`, clear clears [XCH 524].
- **[A]** Whether the prefix stays pending after such a control code, for the next byte (`1`,
  BEL, `A`).

## Differences from the reference

All [XCH]; nothing else in the 768 cases differs, A and the three cells included. (XCH 333,
`ESC M`, agrees by construction, not by evidence: see §3.)

| case | VG-8020 | zerobas |
|---|---|---|
| DEL [XCH 127; after the prefix 639] | CSRX 20; `P` blanked, `Q R` kept | CSRX 21; `Q` blanked, `P R` kept |
| `ESC l` [XCH 364] | CSRX 21; the line blanked | CSRX 1; the line blanked |

TODO **D-CHPUTDEL** fixes both in the C-BIOS repack's CHPUT.

## Open (not measured)

- **[A]** The registers other than A, and the flags.
- **[A]** The prefix pending across a control code (§4); the ESC pending across one (§3).
- **[A]** `ESC L` / `ESC M` / `ESC J` / `ESC K` / `ESC E` / `ESC j` / 12 beyond the three cells (§2, §3).
- **[A]** The TAB stop rule (§2).
- **[A]** The edges: BS / 29 / DEL at column 1, 30 / `ESC A` at row 1, TAB at a stop column and near
  the last column, LF / 31 / `ESC B` on the last row (the scroll), 28 at the last column, all with
  the function-key line on and off (CRTCNT).
- **[A]** The line-continuation table LINTTB: wrap marks, and what the scroll and `ESC L` / `ESC M` /
  clear do to it.
- **[A]** The cursor block's drawing (CSRSW), and whether BEL sounds.
- **[A]** Every byte as an `ESC Y` row / column parameter and as `ESC x` / `ESC y`'s.
- **[A]** The cursor at the screen's last column (the wrap), on its last row (the scroll), at
  other widths (32, 37, 80), and in the graphic modes.
- **[A]** Whether CHPUT goes through the hook H.CHPU ($FDA4), and with interrupts in which state.
- **[A]** `ESC K` / `ESC J`, cells beyond the three read.

## Tests that cover it

`biosl-acceptance` rung b1text: CHPUT's happy path, VG-8020 against zerobas (L3 in
tools/bios_levels.py). The matrix above is spec evidence, not yet a gate. It joins one through the
test audit ([docs/spec-method.md](../spec-method.md) §8) once this page is FINAL.
