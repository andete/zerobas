<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `PSET` — set one pixel on the graphics screen

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. No known divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`PSET (x,y),c` sets the pixel at `(x,y)` to colour `c` on a graphics screen
(SCREEN 2 or SCREEN 3). Leave the colour out and the current foreground colour
is used. It is the basic drawing statement; [`PRESET`](PRESET.md) is its twin
with a different default colour, and [`POINT`](POINT.md) reads a pixel back.
zerobas draws the same bytes into video memory as the Philips VG-8020,
colour clash included, and raises the same errors in every case we have
measured.

## Syntax

```
PSET [STEP](<x>,<y>)[,<colour>]
```

`x` runs 0 to 255 and `y` 0 to 191, in SCREEN 2 and in SCREEN 3 alike. With
`STEP`, the pair is an offset from the *last point* — the last point any
graphics statement used.

## Details

- **The colour clash is real, and reproduced.** SCREEN 2 stores one
  foreground colour per row of 8 pixels (x 0–7, 8–15, …). Setting a second
  pixel in the same group with another colour recolours the pixels already set
  there: `PSET(0,0),15:PSET(1,0),6` leaves *both* pixels in colour 6, on both
  machines.
- **A colour equal to the group's background clears the pixel** instead of
  setting it, and leaves the group's colours alone.
- **Off-screen points are skipped silently.** `PSET(300,100)` or `PSET(-1,0)`
  draws nothing and raises no error; nothing is drawn at the edge either. The
  last point still moves to the unclipped `(300,100)`, so a following
  `STEP` counts from there.
- **SCREEN 3** (multicolour) uses the same 0–255 × 0–191 coordinates; each
  4×4 block of them is one dot of one colour, so `PSET(0,0),7` makes
  `POINT(3,3)` read 7. There is no colour clash in that mode.
- **The colour is checked, 0 to 15.** A fractional colour is truncated
  (`,1.6` is colour 1).
- **The screen mode is checked after the coordinates.** In SCREEN 0 or 1,
  `PSET` is `Illegal function call` — but a fault inside the coordinates
  (a string, an overflow) is reported first, and the last point has already
  moved to `(x,y)` when the error is raised. Both reference machines do it in
  that order.

| you write | you get |
|---|---|
| `PSET(10,10),16` or `,-1` | error 5, `Illegal function call` |
| `PSET(10,10)` in SCREEN 0 or 1 | error 5, `Illegal function call` |
| `PSET(99999,1)` | error 6, `Overflow` |
| `PSET(10,10),"A"`, `PSET STEP("A",1)` | error 13, `Type mismatch` |
| `PSET(10)`, `PSET(10,10`, `PSET STEP 1,1` | error 2, `Syntax error` |
| `PSET(10,10),` (comma, no colour) | error 24, `Missing operand` |

The whole set of errors `PSET` can raise is {2, 5, 6, 13, 24}, the same on
both machines.

## Example

```
10 SCREEN 2
20 PSET(10,10),15
30 PSET STEP(10,0),7
40 A=POINT(10,10):B=POINT(20,10)
50 PSET(0,0),15:PSET(1,0),6
60 C=POINT(0,0):D=POINT(1,0)
70 ON ERROR GOTO 100
80 PSET(5,5),16
90 SCREEN 0:PRINT A;B;C;D;E:END
100 E=ERR:RESUME NEXT
RUN
 15  7  6  6  5
```

`C` and `D` are both 6: the second `PSET` recoloured the first pixel, which
shares its 8-pixel group.

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_pset.out`](../../scratchpad/kwdoc_pset.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

None known.

The one rung not yet proven is **RAM usage**.

## What we found, and how

- **`PSET` arrived on 2026-07-21** (graphics slice G2) after the VG-8020 was
  measured byte by byte: which bit, which colour byte, what happens when two
  colours meet in one group. The test reads back both the pixel and the colour
  tables, so a wrong colour cannot hide behind a right pixel
  ([spec-basic-graphics-g2.md](../spec-basic-graphics-g2.md)).
- **A colour of 16 used to draw in colour 0** (fixed 2026-08-11, D-LINERR).
  The code masked the colour to its low four bits, with a comment pointing at
  a measurement that did not exist. Measured, both references raise error 5
  for any colour outside 0–15
  ([spec-basic-lineerr.md](../spec-basic-lineerr.md)).
- **The screen-mode check moved** (same day, D-LINERR): it used to run before
  anything else; both references check the coordinates first and the mode
  after them, as described above.
- **SCREEN 3 was refused** (fixed 2026-08-22, D-SCREEN3). zerobas raised
  error 5 where both references draw
  ([spec-basic-screen3.md](../spec-basic-screen3.md)).
- **A dangling comma was accepted without an error** (fixed 2026-08-23,
  D-MISSOPFIX). Both references answer `PSET(10,10),` with
  `Missing operand`. The same sweep found that rule broken in sixteen places
  across the language, `POKE` and `VPOKE` among them.
- **An error in a graphics program showed no message** (fixed 2026-09-27,
  D-GFXERRMSG). `SCREEN 2:PSET(10,10),16` without `ON ERROR` printed its
  message into the graphics screen, so the user saw only the prompt. The
  VG-8020 returns to the text screen first and then prints
  `Illegal function call in 10`; zerobas now does the same.

## Where it lives

`ex_pset` in [basic/graphics.asm](../../basic/graphics.asm) parses the point
and colour; `gfx_point_gate` (shared with `PRESET`, `LINE`, `CIRCLE` and
`PAINT`) moves the last point and checks the screen mode. The pixel itself is
written by the graphics tenant in [sub/graphics.asm](../../sub/graphics.asm):
`gfx_plot` and `gfx_color_rmw` for SCREEN 2, `gfx_rmw_at_mc` for SCREEN 3.

## Tests that cover it

- `make graphics-acceptance` — pixel and colour tables read back on both
  machines: single pixels, the clash, off-screen points, `STEP`.
- `make lineerr-acceptance` — the error order, the colour range and the last
  point after an error.
- `make kwsweep` — the everyday rows (explicit colour, default colour, `STEP`,
  SCREEN 3) and one error row per code in {2, 5, 6, 13, 24}.
- `make kwram` — the RAM-usage comparison.
