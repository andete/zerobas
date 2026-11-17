<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# `CHPUT` ($00A2) — write one character to the screen

> **Spec:** DRAFT 1 (2026-11-17) — not yet reviewed. Measured on the Panasonic CF-3300 only; the
> primary reference for the main BIOS, the Philips VG-8020, is NOT yet measured, so the two
> differences below may be CF-3300-specific until it is.

## Summary

`CHPUT` puts the character in A on the text screen at the cursor and moves the cursor, or, for a
control code or an escape sequence, moves the cursor or edits the screen. It is what `PRINT` and
the MSX-DOS console end up calling. On the CF-3300, zerobas moves the cursor the same way for
every byte and every escape command but two: DEL and `ESC l` (below).

Split out of the BDOS [CONOUT](../bdos/CONOUT.md) page, whose third review showed its remaining
open questions were CHPUT's, not the BDOS's.

Reference: the Panasonic CF-3300's main BIOS. Ours: the C-BIOS repack's CHPUT (`cbios-repack`
patches, [cbios-repack-provenance.md](../cbios-repack-provenance.md)).

**Evidence.**
- **[XM n]**: case `n` of the BDOSXM matrix, [`scratchpad/XM_table.out`](../../scratchpad/XM_table.out).
  Read its header first: setup, units, the two skipped cases. The matrix reaches CHPUT through the
  MSX-DOS BDOS, so it reads CHPUT's cursor effect from the BDOS side:
  - **DIRIO output ($06, mode 1)** passes each byte to the screen with no BDOS processing of its
    own, so its cursor results are CHPUT's. **[A]**: the TAB case (see §4).
  - **CONOUT after ESC (mode 3)** gives the cursor effect of every `ESC v`.
- **[A]**: assumed, NOT measured.

The screen state throughout: under MSX-DOS 1, the 32-column text screen with LINLEN 29. The cursor
starts every case at CSRY 11, CSRX 21 (1-based), placed there by `ESC Y`. Only CSRX / CSRY were
read; VRAM was not.

## 1. One byte, the cursor after it

From CSRY 11, CSRX 21, every byte 0–254 [XM 256–510], the CF-3300:

| bytes | cursor after |
|---|---|
| 32–126, 128–254, and 28 (cursor right) | right one: CSRX 22 |
| 0–7, 14–27 (incl. 1, the graphic prefix, and 27, ESC — both pending) | unchanged |
| 8 (BS), 29 (cursor left), 127 (DEL) | left one: CSRX 20 |
| 10 (LF), 31 (cursor down) | down one: CSRY 12 |
| 30 (cursor up) | up one: CSRY 10 |
| 11 (home), 12 (clear) | CSRY 1, CSRX 1 |
| 13 (CR) | CSRX 1, same row |
| 9 (TAB) | CSRX 25: the next stop of 8 (columns 1, 9, 17, 25 …) |

**zerobas differs in one byte: DEL (127) leaves the cursor where it is** instead of moving it left
[XM 383; also through CONOUT XM 127, STROUT 639, after the prefix 1151; and BDOSXL rows 31, 115,
119]. Every other byte gives the same cursor.

## 2. `ESC v`, the cursor after it

From the same start, through CONOUT ESC then CONOUT v [XM 768–1023], the CF-3300:

| `ESC v` | cursor after |
|---|---|
| A / B / C / D | up / down / right / left one |
| E, H, j | CSRY 1, CSRX 1 |
| L, M | CSRX 1, same row |
| every other v (incl. Y, x, y, still waiting for parameters; K, J, l) | unchanged |

**zerobas differs in one command: `ESC l` moves the cursor to CSRX 1** instead of leaving it
[XM 876]. (`ESC TAB` ends at CSRX 25 on the CF-3300 and 23 on zerobas [XM 777]. That is the BDOS's
TAB expansion from a different count (D-CONCOL), not CHPUT.)

## 3. What the two differences are, stated as behaviour

- **DEL (127):** the reference moves the cursor one column left; whether it also erases a character
  is not read (VRAM). **[A]** At a row's first column: moves to the previous row's end? BDOSXL rows
  119 / 134 suggest it depends on the row, and CSRY was not read there.
- **`ESC l`:** the reference leaves the cursor in place; MSX documentation calls `ESC l` "erase the
  whole line". **[A]** what it erases (VRAM not read).

## 4. Open (the next measurements)

- **[A] What lands in VRAM.** Every claim above is the cursor only. A VRAM read of the cells
  around the cursor would show what DEL, `ESC l`, `ESC K` / `J` and a graphic character write.
- **[A] Does the graphic prefix 1 stay pending across a control code?** E.g. `1`, BEL, `A`: does the
  `A` become a graphic character? The cursor alone cannot tell; a VRAM read can.
- **[A] Does a TAB reach CHPUT as 9 from DIRIO-out**, or does the BDOS write spaces counted from the
  cursor? The cursors agree under both. A TAB as an `ESC Y` parameter through DIRIO, or an H.CHPU
  ($FDA4) trace, separates them.
- **[A] What CHPUT receives at all:** whether every byte reaches it unchanged (an H.CHPU trace
  logging each byte).
- **[A] Parameters:** every byte value as the `ESC Y` row and column parameter, and as `ESC x` /
  `ESC y`'s.
- **[A] Other states:** the screen's last row (scrolling), the last column (the wrap), SCREEN 0 at
  width 40 / 80 / 37, and the graphic modes.
- **[A] CHPUT called directly** (inter-slot from a program, or from BASIC), not through the BDOS:
  that would confirm the DIRIO-derived table on its own.
