<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# Screen modes — the four MSX1 displays

> **Status (2026-10-09):** every keyword that sets up or draws on the screen
> (`SCREEN`, `WIDTH`, `COLOR`, `BASE`, `VDP`, `SPRITE`, `PSET`, `LINE` and the
> rest) is at level 3 with no known everyday difference from the VG-8020; RAM
> usage is not yet proven for any of them. Open, both TIER 6: `CIRCLE` with a
> negative radius (D-CIRCNEGR) and `CLS` with a stray argument (D-BAREEXTRA).
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

An MSX1 has one video chip, a TMS9918-family VDP with its own 16 KB of video
memory (VRAM), and four ways of using it, chosen with `SCREEN`:

| mode | what it is | size | text | drawing | sprites |
|---|---|---|---|---|---|
| `SCREEN 0` | text | up to 40 columns × 24 rows | yes | no | no |
| `SCREEN 1` | text | up to 32 columns × 24 rows | yes | no | yes |
| `SCREEN 2` | high-resolution graphics | 256 × 192 pixels | — | yes | yes |
| `SCREEN 3` | multicolour graphics | 64 × 48 blocks of 4 × 4 | — | yes | yes |

You type, `PRINT` and edit in a text mode, and draw in a graphics mode; when
a program ends or stops on an error, the machine goes back to the last text
mode for the message and the prompt. zerobas behaves like the Philips VG-8020
in every case measured.

## How it works

### The text modes

- **`SCREEN 0`** takes `WIDTH 1` to `40`. The text area is centred: a
  narrower width leaves a margin on both sides. The VG-8020 powers on at
  width 37, and so does zerobas; the National CF-3300 starts at 39.
- **`SCREEN 1`** takes `WIDTH 1` to `32` and powers on at 29, on the VG-8020
  and on zerobas.
- **Each text mode remembers its width**: `LINL40` (`&HF3AE`) and `LINL32`
  (`&HF3AF`); the width in force is `LINLEN` (`&HF3B0`). A `WIDTH` given in a
  graphics mode takes 1 to 40 and is kept for `SCREEN 0`.
- **The function-key line** labels F1 to F5 on the bottom row of both text
  modes; while it is on (`KEY ON`, the power-on state) that row is not part of
  the text screen. Its labels follow the width.
- **Changing to a text mode clears the screen**, as does a `WIDTH` to a new
  value. The current mode is in `SCRMOD` (`&HFCAF`), 0 to 3.

### The graphics modes

Both graphics modes use the same coordinates, x 0 to 255 and y 0 to 191, and
the same statements. A point off the screen is skipped without an error by
`PSET`; `LINE` moves each end onto the screen edge; `POINT` answers −1.

- **`SCREEN 2`** stores one bit per pixel in the pattern table and one colour
  byte — foreground in the high four bits, background in the low four — for
  each row of 8 pixels. Setting a pixel in a new colour therefore recolours
  every set pixel in its 8-pixel group: the *colour clash*, reproduced
  exactly. `SCREEN 2` clears every group to the background colour.
- **`SCREEN 3`** has no pattern bits: each 4 × 4 block of coordinates is one
  dot with its own colour, so there is no clash. `PSET(0,0),7` colours the
  whole block, and `POINT(3,3)` reads 7. An unset dot or pixel reads back as
  the background colour, in both modes.

### What each mode allows

| | `SCREEN 0` | `SCREEN 1` | `SCREEN 2` | `SCREEN 3` |
|---|---|---|---|---|
| `PSET`, `PRESET`, `LINE`, `CIRCLE`, `PAINT`, `DRAW` | error 5 | error 5 | draws | draws |
| `POINT` | no error, no meaning | not measured | the pixel's colour | the block's colour |
| `PUT SPRITE`, `SPRITE$(n)=` (reading `SPRITE$` works everywhere) | error 5 | works | works | works |
| `WIDTH` | 1–40 | 1–32 | 1–40, kept for `SCREEN 0` | 1–40, kept for `SCREEN 0` |
| `VPEEK`, `VPOKE`, `BASE`, `VDP` | every mode | | | |

Drawing statements check the mode *after* their coordinates (`PSET("A",1)` in
`SCREEN 0` is `Type mismatch`). What `PRINT` does in a graphics mode has not
been measured; the example switches back to `SCREEN 0` before printing.

### The tables in video memory: `BASE(n)`

The chip draws from up to five tables in VRAM. `BASE(n)` gives their
addresses: `n \ 5` is the mode and `n MOD 5` the table. The power-on values
are the same on the VG-8020 and on zerobas:

| table (`n MOD 5`) | `SCREEN 0` | `SCREEN 1` | `SCREEN 2` | `SCREEN 3` |
|---|---|---|---|---|
| 0 — names (what goes where) | `&H0000` | `&H1800` | `&H1800` | `&H0800` |
| 1 — colours | — | `&H2000` | `&H2000` | — |
| 2 — patterns (the font, pixels or blocks) | `&H0800` | `&H0000` | `&H0000` | `&H0000` |
| 3 — sprite attributes | — | `&H1B00` | `&H1B00` | `&H1B00` |
| 4 — sprite patterns | — | `&H3800` | `&H3800` | `&H3800` |

(— : the slot reads 0.) In `SCREEN 2` the byte for pixel (x,y) is at
`(y\8)*256 + (x\8)*8 + (y MOD 8)` from the pattern table, and its colour byte
at the same offset from the colour table; the leftmost pixel is the byte's
top bit. A table can be moved by assigning to `BASE(n)`, below 16384 and on
the step the chip requires ([`BASE`](../keywords/BASE.md)).

### Colours

`COLOR fg,bg,border` takes palette numbers 0 to 15 and stores them in
`FORCLR` (`&HF3E9`), `BAKCLR` (`&HF3EA`) and `BDRCLR` (`&HF3EB`); a rejected
`COLOR` changes nothing. The foreground is also the drawing colour (`ATRBYT`)
for statements given none; `PRESET` defaults to the background.

### Sprites

Sprites are shapes the chip draws over the screen by itself, in every mode
but `SCREEN 0`. Each of the 32 planes has a 4-byte entry in the sprite
attribute table — y, x, pattern number, colour — set by `PUT SPRITE`; the
shapes come from `SPRITE$(n)`. `SCREEN`'s second argument sets the size of
all of them:

| `SCREEN m,s` | shape | `SPRITE$` length | pattern numbers |
|---|---|---|---|
| `s = 0` | 8 × 8 | 8 bytes | 0–255 |
| `s = 1` | 8 × 8, magnified | 8 bytes | 0–255 |
| `s = 2` | 16 × 16 | 32 bytes | 0–63 |
| `s = 3` | 16 × 16, magnified | 32 bytes | 0–63 |

The size is the two low bits of VDP register 1 (bit 1: 16 × 16, bit 0: the
magnify bit) and lasts through later `SCREEN` statements that leave it out.
Entering `SCREEN 1` or `2` puts every plane at y = 209, which hides it and
the planes after it. Two sprites touching set the collision flag in `VDP(8)`,
which `ON SPRITE GOSUB` watches ([`SPRITE`](../keywords/SPRITE.md)).

### The VDP registers: `VDP(n)`

The chip's eight control registers are write-only, so `VDP(0)`–`VDP(7)` read
the copies in `RG0SAV`–`RG7SAV` (`&HF3DF`–`&HF3E6`); a write updates copy and
chip. `VDP(8)`, read-only, is the status register as copied at the last frame
interrupt (`STATFL`, `&HF3E7`).

Measured: register 1 reads 240 in `SCREEN 0`, and clearing its bit 5 stops
the frame interrupt (`TIME` stops, and the keyboard); registers 2 to 6 hold
the table addresses (in `SCREEN 0`, `BASE(3)=&H1F00` sets register 5 to
`&H3E`); register 7 holds colours, the backdrop among them. Assigning a table of the
*current* mode in `SCREEN 1` or `2` reprograms the chip from the next mode's
slots, a VG-8020 quirk zerobas reproduces ([`VDP`](../keywords/VDP.md)).

## Example

```
10 COLOR 15,4:SCREEN 2,2
20 PSET(0,0),15
30 P=VPEEK(BASE(12)):C=VPEEK(BASE(11))
40 A=POINT(0,0):B=POINT(1,0)
50 M=PEEK(&HFCAF):S=VDP(1) AND 3
60 L=LEN(SPRITE$(0))
70 SCREEN 3:PSET(0,0),7
80 D=POINT(3,3):E=POINT(8,8)
90 SCREEN 0,0
100 PRINT M;S;L;D;E
110 PRINT P;C;A;B
120 PRINT BASE(10);BASE(11);BASE(12)
RUN
 2  2  32  7  4
 128  244  15  4
 6144  8192  0
```

The pixel at (0,0) sets the top bit of the first pattern byte (128) and makes
its colour byte `&HF4` (244: foreground 15, background 4); its neighbour reads
the background. In `SCREEN 3` that dot covers (3,3), and an untouched block
reads 4. `SCREEN 0` clears the screen, leaving only the program's output.
Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_screen-modes.out`](../../scratchpad/kwdoc_screen-modes.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

None known in the measured behaviour of the four modes.

- **Style differences between the references** (the power-on width, the F6
  text) follow the VG-8020 on both builds. Joost, 2026-09-04: *"when there is
  stylish differences (color, screen) between the oracles, pick the VG8020"*.
- **Open, TIER 6:** `CIRCLE(99,99),-5` is error 5 here and draws on the
  VG-8020 (D-CIRCNEGR); `CLS 1` clears the screen before its `Syntax error`,
  where the VG-8020 leaves it (D-BAREEXTRA).
- **Not measured:** the contents of the `SCREEN 3` name table, text colours in
  `SCREEN 1`, `PRINT` in a graphics mode, and `CIRCLE`'s shape in `SCREEN 3`.
- **RAM usage**: free memory moves alike, but the work-area cells written
  differ, so that rung is not proven for any screen keyword.

## What we found, and how

- **zerobas started at width 39** (fixed 2026-09-24, D-BOOTWIDTH). Before
  that, the screen-reading tests had to set `WIDTH 40` first: the centred
  text area put every column one place off between the machines.
- **`SCREEN 3` refused to draw, and `POINT` there gave a plausible wrong
  colour** — 1 where both references read 4 (fixed 2026-08-22, D-SCREEN3);
  `PAINT` followed the same day (D-PAINTMC)
  ([spec-basic-screen3.md](../spec-basic-screen3.md)).
- **`BASE` answered 0 for everything** until 2026-07-22 (slice G8), though the
  table behind it already matched the VG-8020's byte for byte
  ([spec-basic-graphics-g8.md](../spec-basic-graphics-g8.md)).
- **`SCREEN 2:WIDTH 29` stored the width for `SCREEN 1`** (fixed 2026-07-28,
  D-WID); every graphics mode keeps `SCREEN 0`'s width
  ([spec-basic-width-domain.md](../spec-basic-width-domain.md)).
- **The prompt dropped `SCREEN 1` back to `SCREEN 0`** (fixed 2026-09-26,
  D-SCR1PROMPT), and an error in a graphics program printed its message into
  the graphics screen (fixed 2026-09-27, D-GFXERRMSG). The VG-8020 returns to
  the last text mode for both.
- **A `VDP` write is proven by its effect on the chip**, not by reading the
  copy back: clearing the interrupt bit freezes `TIME` on both machines
  (Joost, 2026-09-14: *"if you choose a clever write, you can see the effects
  in the visual appearance of the screen"*).

## How zerobas does it

Mode changes go through the published BIOS calls: `SCREEN` and `WIDTH` call
`CHGMOD`, `COLOR` calls `CHGCLR`, `CLS` calls `CLS`, and the return to text
for a message or the prompt calls `TOTEXT`
([basic/screen.asm](../../basic/screen.asm), `txt_mode` in
[basic/repl.asm](../../basic/repl.asm)). C-BIOS's `DSPFNK` leaves the bottom
row blank, so zerobas draws the function-key line itself, from a sub-ROM
tenant (D-FNKLINE, Joost 2026-09-17). The `BASE` table is the published work
area at `&HF3B3`, two bytes per slot.

The main ROM parses each drawing statement
([basic/graphics.asm](../../basic/graphics.asm)) and hands the work, in RAM
cells, to a sub-ROM page-0 tenant, [sub/graphics.asm](../../sub/graphics.asm)
([rom-layout.md](rom-layout.md)). The BIOS is switched out while it runs, so
it drives the VDP ports directly. A VRAM address takes two port writes, which
the frame interrupt's status read would split, so each address-and-byte step
runs with interrupts off; between steps they are on, and `PLAY` keeps playing
through a long `CIRCLE`, as the VG-8020's frame counter keeps counting. The
sprite collision check runs every frame from the interrupt hook
([basic/sprtrap-body.inc](../../basic/sprtrap-body.inc)).

## Related pages

- Concepts: [screen-editor.md](screen-editor.md), [rom-layout.md](rom-layout.md),
  [memory-map.md](memory-map.md), [interrupts-and-traps.md](interrupts-and-traps.md).
- Keywords: [`SCREEN`](../keywords/SCREEN.md), [`WIDTH`](../keywords/WIDTH.md), [`COLOR`](../keywords/COLOR.md),
  [`KEY`](../keywords/KEY.md), [`BASE`](../keywords/BASE.md), [`VDP`](../keywords/VDP.md),
  [`VPEEK`](../keywords/VPEEK.md), [`SPRITE`](../keywords/SPRITE.md), [`PSET`](../keywords/PSET.md),
  [`POINT`](../keywords/POINT.md), [`LINE`](../keywords/LINE.md), [`CIRCLE`](../keywords/CIRCLE.md),
  [`PAINT`](../keywords/PAINT.md), [`DRAW`](../keywords/DRAW.md).
- More keywords: [`PRESET`](../keywords/PRESET.md), [`VPOKE`](../keywords/VPOKE.md).

## Tests that cover it

- `make graphics-acceptance` — pixels, colour bytes, `BASE`, `VDP`, sprites.
- `make graphics-floor-acceptance` — VDP access with interrupts running.
- `make screenerr-acceptance`, `make width-acceptance` — `SCREEN` and `WIDTH`.
- `make lineerr-acceptance`, `make sprite-trap-acceptance` — drawing errors; `ON SPRITE GOSUB`.
- `make kwsweep`, `make kwram` — every screen keyword's forms, and RAM usage.
