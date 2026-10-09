<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `LINE` — draw a line, a box or a filled box

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. No known divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`LINE (x1,y1)-(x2,y2),c` draws a straight line between two points on the
graphics screen. Add `,B` and it draws the outline of the box with those two
corners; add `,BF` and it fills the box. zerobas draws the same pixels and
writes the same colour bytes as the Philips VG-8020, including for lines that
run off the screen, and raises the same errors in every case we have measured.

This page is about the graphics statement. `LINE INPUT` is a different
statement that happens to start with the same word: when `INPUT` follows
`LINE`, the line is read from the keyboard or a file instead.

## Syntax

```
LINE [[STEP](<x1>,<y1>)]-[STEP](<x2>,<y2>)[,[<colour>][,B|,BF]]
```

The `-` and the second point are required. The colour may be skipped with an
empty comma (`LINE(0,0)-(9,9),,B`).

## Details

- **The first point is optional.** `LINE -(x2,y2)` continues from the last
  point, so a series of `LINE -` statements draws a connected path.
- **Two `STEP`s chain.** In `LINE STEP(a,b)-STEP(c,d)` the first offset counts
  from the last point and the second from the first end: after `PSET(10,10)`,
  `LINE STEP(2,2)-STEP(3,3)` draws from (12,12) to (15,15).
- **Direction does not matter.** `LINE(20,7)-(0,0)` draws exactly the pixels
  `LINE(0,0)-(20,7)` draws.
- **After `LINE`, the last point is the second point**, for boxes too.
- **Off-screen ends are moved onto the screen edge, not cut off.** Each end
  point is first pulled to the nearest edge (x to 0–255, y to 0–191) and the
  line is drawn between the results, so a steep line running off the top
  can land a column away from where the "ideal" line would cross the edge.
  A line that is entirely off screen therefore still lights one pixel:
  `LINE(300,300)-(400,400)` sets (255,191). No error either way. The last
  point keeps the original, unmoved coordinates.
- **A filled box writes whole 8-pixel groups as background colour.** Where a
  `,BF` fill covers all 8 pixels of a group, the VG-8020 stores it as
  "background = c" rather than as 8 set pixels. It looks the same, but a later
  `PSET` into that group behaves differently: after
  `LINE(0,0)-(7,7),15,BF:PSET(0,0),6`, only one pixel turns 6. zerobas
  stores it the same way.
- **The colour defaults to the foreground colour** and is checked, 0 to 15.
  Each pixel takes the SCREEN 2 colour clash exactly as [`PSET`](PSET.md)
  does.
- **SCREEN 3 works too;** in SCREEN 0 or 1 `LINE` is `Illegal function call`,
  checked after the two points and before the colour.

| you write | you get |
|---|---|
| `LINE(0,0)-(9,9)` in SCREEN 0 or 1 | error 5, `Illegal function call` |
| `LINE(0,0)-(1,1),16` | error 5, `Illegal function call` |
| `LINE(0,0)-(32768,0)` | error 6, `Overflow` |
| `LINE(0,0)-("A",1)` | error 13, `Type mismatch` |
| `LINE(0,0)-`, `LINE(5,5)`, `LINE -(9)` | error 2, `Syntax error` |
| `LINE(0,0)-(9,9),1,C`, `…,BX`, `…,,` | error 2, `Syntax error` |
| `LINE(0,0)-(9,9),` (comma, no colour) | error 24, `Missing operand` |

The whole set of errors `LINE` raises is {2, 5, 6, 13, 24}, the same on both
machines.

## Example

```
10 SCREEN 2
20 LINE(10,10)-(20,10),15
30 LINE(30,30)-(40,40),7,B
40 LINE(50,50)-(60,60),13,BF
50 A=POINT(15,10):B=POINT(40,35)
60 C=POINT(35,35):D=POINT(55,55)
70 LINE -(100,60),15
80 E=POINT(80,60)
90 SCREEN 0:PRINT A;B;C;D;E
100 ON ERROR GOTO 130
110 LINE(0,0)-(9,9)
120 END
130 PRINT "Error";ERR:RESUME NEXT
RUN
 15  7  4  13  15
Error 5
```

`B` is on the box's edge and `C` inside it, so the outline box reads 7 and 4;
the filled box reads 13 inside. Line 70 starts where the filled box ended,
at (60,60).

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_line.out`](../../scratchpad/kwdoc_line.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

None known.

The one rung not yet proven is **RAM usage**.

## What we found, and how

- **`LINE` arrived on 2026-07-21** (graphics slice G3). Its stepping rule was
  fitted to four bitmaps captured from the VG-8020 (shallow, steep, diagonal
  and falling lines) until it reproduced all four exactly
  ([spec-basic-graphics-g3.md](../spec-basic-graphics-g3.md)).
- **A type error in a coordinate was reported as error 5** (fixed 2026-08-11,
  D-LINERR). `LINE (0,0)-((A$<5),1)` is error 13 on both references; zerobas
  checked the screen mode too early. The same slice made the colour a real
  0–15 check instead of a silent mask
  ([spec-basic-lineerr.md](../spec-basic-lineerr.md)).
- **Off-screen lines were clipped, and the reference does not clip**
  (fixed 2026-08-17, D-SPOKELINE). It was found through a `CIRCLE` arc's
  radius line that came out one column off; measured on whole screens, the
  VG-8020 moves each end onto the screen and then draws. The three tests that
  were supposed to cover off-screen lines could not tell the two rules apart
  ([spokeline-msx1-characterization.md](../spokeline-msx1-characterization.md)).
- **A filled box stored its colour the wrong way** (fixed 2026-08-17,
  D-BFBYTE): as set pixels in the foreground, where the reference stores
  whole groups as background. `POINT` reads the same either way; the
  difference showed when a pixel was later drawn into the box.
- **The work area after an off-screen filled box** was measured the same day
  (D-DRAWCLAMP): the last point keeps the raw second corner, while the second
  pair of position cells (`GXPOS`/`GYPOS`) holds the bottom-right corner of the
  box as clamped to the screen. zerobas was changed to match
  ([drawclamp-msx1-characterization.md](../drawclamp-msx1-characterization.md)).

## Where it lives

`ex_line` in [basic/files.asm](../../basic/files.asm) looks at the token after
`LINE`: `INPUT` goes to `LINE INPUT`, anything else to `ex_line_gfx` in
[basic/graphics.asm](../../basic/graphics.asm), which parses the points,
colour and box suffix. The drawing is in [sub/graphics.asm](../../sub/graphics.asm):
`gfx_line_op`, the stepper `gfx_bres_init` / `gfx_bres_next`, the end-point
clamp `gfx_clamp_coords`, and `gfx_box_outline` / `gfx_box_fill`.

## Related concepts

- [Screen modes](../concepts/screen-modes.md) — the four MSX1 displays

## Tests that cover it

- `make graphics-acceptance` — whole bitmaps and colour tables against the
  VG-8020: segments, boxes, fills, the clash and the off-screen clamp rows.
- `make lineerr-acceptance` — the error order, the colour range and the work
  area after an error.
- `make unit-test` — host tests of the clamp and the box-fill splitter.
- `make kwsweep` — one row per form (segment, box, filled box, `STEP`,
  omitted start, default colour) and one error row per code.
- `make kwram` — the RAM-usage comparison.
