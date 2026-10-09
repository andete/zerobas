<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `PRESET` — erase one pixel on the graphics screen

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. No known divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`PRESET (x,y)` erases the pixel at `(x,y)` by drawing it in the background
colour. Given a colour, `PRESET (x,y),c` does exactly what
[`PSET`](PSET.md)`(x,y),c` does. The two statements differ only in the colour
they use when none is given: `PSET` uses the foreground colour, `PRESET` the
background colour. zerobas behaves like the Philips VG-8020 in every case we
have measured, errors included.

## Syntax

```
PRESET [STEP](<x>,<y>)[,<colour>]
```

The same shape as `PSET`: `x` 0 to 255, `y` 0 to 191, `STEP` makes the pair
an offset from the last point.

## Details

- **Without a colour, the background colour is used** — the one `COLOR` set.
  On a normal screen that clears the pixel's bit, so `POINT` then reads the
  background colour and the pixel's neighbours keep theirs.
- **With a colour, it is `PSET`.** `PRESET(3,3),9` sets the pixel in colour 9,
  colour clash and all; see [`PSET`](PSET.md) for how SCREEN 2's 8-pixel
  colour groups behave.
- **`STEP`, off-screen points, SCREEN 3, the colour range and the order of
  the checks** are all as for `PSET`: an off-screen point is skipped without
  an error, and in SCREEN 0 or 1 the statement is `Illegal function call`.

| you write | you get |
|---|---|
| `PRESET(10,10)` in SCREEN 0 or 1 | error 5, `Illegal function call` |
| `PRESET(10,10),16` | error 5, `Illegal function call` |
| `PRESET("A",10)`, `PRESET(10,10),"A"` | error 13, `Type mismatch` |
| `PRESET(10,10`, `PRESET STEP 1,1` | error 2, `Syntax error` |

The errors measured for `PRESET` on the reference are {2, 5, 13}, and
zerobas matches each one. An out-of-range coordinate (error 6) and a dangling
comma (error 24) were measured for `PSET`, not separately for `PRESET`.

## Example

```
10 SCREEN 2
20 PSET(10,10),15:PSET(20,10),15
30 PRESET(10,10)
40 PRESET(30,10),9
50 A=POINT(10,10):B=POINT(20,10)
60 C=POINT(30,10)
70 SCREEN 0:PRINT A;B;C
80 ON ERROR GOTO 110
90 PRESET(1,1)
100 END
110 PRINT "Error";ERR:RESUME NEXT
RUN
 4  15  9
Error 5
```

The erased pixel reads 4, the background; its neighbour keeps 15; the
`PRESET` with a colour drew in 9. Line 90 runs in SCREEN 0, where graphics
statements are refused.

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_preset.out`](../../scratchpad/kwdoc_preset.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

None known.

The one rung not yet proven is **RAM usage**.

## What we found, and how

- **`PRESET` arrived with `PSET` on 2026-07-21** (graphics slice G2). The
  measurement that shaped it: on the VG-8020 `PRESET(0,0),6` writes exactly
  the bytes `PSET(0,0),6` writes, so the two share one drawing routine and
  differ only in the default colour
  ([spec-basic-graphics-g2.md](../spec-basic-graphics-g2.md)).
- **The colour range and the order of the checks** were corrected for all the
  pixel statements together on 2026-08-11 (D-LINERR); the details are on the
  [`PSET`](PSET.md) page.
- **SCREEN 3 was refused** until 2026-08-22 (D-SCREEN3); both references
  draw there, and the erase works the same way.
- **The tests could not see a `PRESET` that did nothing useful.** The first
  test erased a pixel and read 4 — which a `PRESET` that never ran also reads
  if the pixel was never drawn. The rows now read two pixels, one the
  statement must change and one it must leave, and one row gives `PRESET` a
  colour so the colour argument is seen.

## Where it lives

`ex_preset` in [basic/graphics.asm](../../basic/graphics.asm), which differs
from `ex_pset` only in where the default colour comes from; the shared
`gfx_point_gate` and the graphics tenant in
[sub/graphics.asm](../../sub/graphics.asm) (`gfx_plot`, `gfx_color_rmw`) do
the rest.

## Tests that cover it

- `make graphics-acceptance` — erase-after-set and `PRESET` with a colour,
  pixel and colour tables read back on both machines.
- `make lineerr-acceptance` — the error order shared with `PSET`.
- `make kwsweep` — the default-colour, explicit-colour, `STEP` and SCREEN 3
  rows, and one error row per code.
- `make kwram` — the RAM-usage comparison.
