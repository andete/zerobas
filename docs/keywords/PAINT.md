<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `PAINT` — fill an area with a colour

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. No known divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`PAINT (x,y),c` fills the area around the point `(x,y)` with colour `c`,
spreading until it meets pixels of the border colour. The border colour
defaults to the fill colour, so the everyday use is: draw a shape in a colour,
then `PAINT` inside it in the same colour. zerobas fills the same pixels,
writes the same video-memory bytes and raises the same errors as the Philips
VG-8020 in every case we have measured — including the surprising SCREEN 2
case below.

## Syntax

```
PAINT [STEP](<x>,<y>)[,[<colour>][,<border>]]
```

`PAINT(x,y),,b` keeps the default colour and names a border.

## Details

- **Colour defaults to the foreground colour; the border defaults to the
  fill colour.** The fill spreads up, down, left and right, never diagonally.
- **In SCREEN 2, a border colour different from the fill colour is not a
  border at all.** SCREEN 2 keeps one foreground colour per row of 8 pixels,
  and on both reference machines a `PAINT` whose border differs from its fill
  covers the *whole screen*, walls of any colour included. Use the same colour
  for the shape and the fill.
- **In SCREEN 3 (multicolour) a separate border colour works**: a box drawn in
  15 stops a fill in 11.
- **When there is nothing to do, nothing happens** — but the rule differs by
  mode, and both halves are measured: in SCREEN 2 a start point that already
  shows the fill colour fills nothing; in SCREEN 3 a start point that shows the
  *border* colour fills nothing, while one already in the fill colour floods
  as usual.
- **The start point must be on the screen.** Unlike [`PSET`](PSET.md), an
  off-screen start is error 5; (255,191) is the last point accepted. The last
  point moves to the start point either way, before the error.
- **A fill can run out of memory** (error 7, `Out of memory`) — on the
  reference only when free memory is cut very low with `CLEAR`. Both machines
  keep the fill's work list in the free memory below the stack.
- **SCREEN 0 or 1** is `Illegal function call`.

| you write | you get |
|---|---|
| `PAINT(1,1)` in SCREEN 0 or 1 | error 5, `Illegal function call` |
| `PAINT(1,1),16` (colour) | error 5, `Illegal function call` |
| `PAINT(300,100)` (start off screen) | error 5, `Illegal function call` |
| border 256 in SCREEN 2, or 16 in SCREEN 3 | error 5, `Illegal function call` |
| a coordinate past 32767 | error 6, `Overflow` |
| `PAINT("A",1)`, `PAINT(1,1),"A"`, `PAINT(1,1),1,"A"` | error 13, `Type mismatch` |
| `PAINT(1)` | error 2, `Syntax error` |
| `PAINT(1,1),1,1,1` (a fourth argument) | fills first, then error 2 |
| `PAINT(1,1),` (comma, nothing after) | error 24, `Missing operand`, nothing filled |

The errors measured for `PAINT` are {2, 5, 6, 13, 24}, the same on both
machines.

## Example

```
10 SCREEN 2
20 LINE(10,10)-(20,20),11,B
30 PAINT(15,15),11
40 A=POINT(15,15):B=POINT(5,5)
50 ON ERROR GOTO 80
60 PAINT(300,100),11
70 SCREEN 0:PRINT A;B;E:END
80 E=ERR:RESUME NEXT
RUN
 11  4  5
```

Inside the box is filled (11), outside is not (4), and an off-screen start
point is refused.

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_paint.out`](../../scratchpad/kwdoc_paint.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

None known.

The one rung not yet proven is **RAM usage**.

## What we found, and how

- **`PAINT` arrived on 2026-07-22** (graphics slice G5). Measuring the VG-8020
  first is what showed the SCREEN 2 rule above; a textbook flood fill would
  have stopped at walls the reference fills straight through
  ([spec-basic-graphics-g5.md](../spec-basic-graphics-g5.md)).
- **An off-screen start point** (2026-08-11, D-PAINTSEED): the error code was
  right, but both references move the last point *before* raising it, and
  zerobas did not ([spec-basic-lineerr.md](../spec-basic-lineerr.md) §9).
- **SCREEN 3 arrived on 2026-08-22** (D-PAINTMC), with its own border range
  (D-PAINTBORD) and the two mirror-image "nothing to do" rules
  (D-PAINTS2SEED) — each measured on both references before it was built
  ([spec-basic-paintmc.md](../spec-basic-paintmc.md)).
- **Commas** (2026-08-23 and 24, D-PAINTMISS and D-PAINT4): a dangling comma
  filled the shape and reported nothing; a fourth argument raised its error
  before filling. The references do the opposite in both cases.
- **The right colours, the wrong bytes** (fixed 2026-08-25, D-PAINTVRAM).
  Every `POINT` reading agreed, but reading video memory directly showed the
  references store a fully covered 8-pixel group as "background = colour",
  and zerobas stored 8 set pixels. Both tables now match byte for byte.
- **The SCREEN 2 whole-screen rule was only half implemented** (fixed
  2026-09-05, D-NTFLOOD). zerobas still stopped at walls drawn in the border
  colour; two walls in two different colours showed the references cross
  both.
- **The fill's work list moved** (2026-09-27, D-PAINTSP). It was a fixed
  table; it now grows down below the stack, as on the reference. Joost ruled
  on 2026-09-27: *"re-architect: grow below SP"*. Its first version kept too
  large a safety margin and ran out of memory on a simple fill the VG-8020
  completes; the test caught that before it shipped.

## Where it lives

`ex_paint` in [basic/graphics.asm](../../basic/graphics.asm) reads the
arguments and checks the start point; the fill is `gfx_paint_op` and
`gfx_paint_flood` in [sub/graphics.asm](../../sub/graphics.asm), with the
border test in `gfx_paint_inside` / `gfx_paint_passable`.

## Tests that cover it

- `make graphics-acceptance` — fills in SCREEN 2 and SCREEN 3 read back
  against the VG-8020, including the whole-screen rule and the start-point
  rules.
- `make lineerr-acceptance` — the off-screen start point and the work area.
- `make kwsweep` — the fill, a non-default colour, a separate border
  (in SCREEN 3), and one error row per code.
- `make kwram` — the RAM-usage comparison.
