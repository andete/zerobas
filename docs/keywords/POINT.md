<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `POINT` — the colour of one pixel

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. No known divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`POINT(x,y)` returns the colour number, 0 to 15, of the pixel at `(x,y)` on
the graphics screen — the reading half of [`PSET`](PSET.md). A point off the
screen returns −1. zerobas returns the same values as the Philips VG-8020 for
every case we have measured.

## Syntax

```
POINT([STEP](<x>,<y>))
```

A function: it is used inside an expression, `C=POINT(10,20)`. `STEP` makes
the pair an offset from the last point drawn.

## Details

- **A set pixel returns its group's foreground colour; an unset pixel returns
  the group's background colour.** In SCREEN 2 colours belong to rows of
  8 pixels, so after `PSET(50,50),9`, `POINT(50,50)` is 9 and its unset
  neighbour `POINT(51,50)` is 4, the background.
- **Off the screen, the answer is −1**, not an error: `POINT(300,300)` is −1.
- **`POINT STEP(0,0)`** reads the pixel at the last point; after
  `PSET(50,50),9` it is 9.
- **`POINT` does not move the last point.** Neither of the two last-point
  pairs in the work area changes, on screen, off screen or through `STEP` —
  measured on both reference machines.
- **SCREEN 3** works too: there each 4×4 block of coordinates is one dot, so
  every point of a block reads the block's colour.
- **No screen-mode check.** Unlike the drawing statements, `POINT` raises no
  error in SCREEN 0; what it returns there depends on what is on the screen
  and is not meaningful.

| you write | you get |
|---|---|
| `POINT(300,300)` | −1 |
| `POINT(1)` | error 2, `Syntax error` |
| `POINT("A",1)` | error 13, `Type mismatch` |

The errors measured for `POINT` on the reference are {2, 13}, the same on
both machines.

## Example

```
10 SCREEN 2
20 PSET(50,50),9
30 A=POINT(50,50):B=POINT(51,50)
40 C=POINT(300,300)
50 D=POINT STEP(0,0)
60 SCREEN 0
70 PRINT A;B;C;D
80 ON ERROR GOTO 110
90 PRINT POINT("A",1)
100 END
110 PRINT "Error";ERR:RESUME NEXT
RUN
 9  4 -1  9
Error 13
```

`D` is 9 because the `POINT(300,300)` before it did not move the last point
away from `(50,50)`.

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_point.out`](../../scratchpad/kwdoc_point.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

None known.

The one rung not yet proven is **RAM usage**.

## What we found, and how

- **`POINT` arrived on 2026-07-21** with `PSET` (graphics slice G2), with its
  off-screen −1 and its acceptance of `STEP` measured on the VG-8020 first
  ([spec-basic-graphics-g2.md](../spec-basic-graphics-g2.md) §5).
- **`POINT` used to move half of the last point** (fixed 2026-08-11,
  D-GIRDOM). The design said "read-only", which was taken to mean one of the
  two last-point pairs; zerobas passed its coordinates through the other pair,
  so `V=POINT(20,21)` changed a value a program can read. Both references move
  neither ([spec-basic-lineerr.md](../spec-basic-lineerr.md) §10).
- **In SCREEN 3, `POINT` returned a plausible wrong colour** with no error,
  because it read multicolour memory as if it were SCREEN 2 (fixed
  2026-08-22, D-SCREEN3): an empty screen read 1 where both references read 4
  ([spec-basic-screen3.md](../spec-basic-screen3.md)).
- **A `POINT` that always answered 15 would have passed the first test**, which
  read back a pixel it had just set. The test now also reads a pixel nothing
  drew.

## Where it lives

`ev_f_point` in [basic/graphics.asm](../../basic/graphics.asm) parses the
point and answers −1 off screen; `gfx_point` in
[sub/graphics.asm](../../sub/graphics.asm) reads the pattern and colour bytes
(`gfx_point_mc` in SCREEN 3).

## Tests that cover it

- `make graphics-acceptance` — `POINT` values, off-screen −1, `STEP`, and the
  SCREEN 3 fills, which are all read back through `POINT`.
- `make lineerr-acceptance` — the work area after `POINT`, on and off screen.
- `make kwsweep` — a set and an unset pixel, and the error rows for {2, 13}.
- `make kwram` — the RAM-usage comparison.
