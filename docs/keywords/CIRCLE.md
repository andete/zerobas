<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `CIRCLE` — draw a circle, an ellipse or an arc

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. One recorded
> difference: a negative radius (below).
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`CIRCLE (x,y),r,c` draws a circle of radius `r` around `(x,y)` on the graphics
screen. Optional arguments turn it into an arc (a start and an end angle) or
an ellipse (an aspect ratio). zerobas draws the same pixels as the Philips
VG-8020 — circles, ellipses, arcs and their radius lines — and raises the same
errors in every case we have measured, except for a negative radius, which is
a deliberate decision.

## Syntax

```
CIRCLE [STEP](<x>,<y>),<radius>[,[<colour>][,[<start>][,[<end>][,<aspect>]]]]
```

Any optional argument can be skipped with an empty comma:
`CIRCLE(100,100),20,,,,.5` is a default-colour ellipse.

## Details

- **A circle is pixel-round.** With the default aspect, a radius of 20 is
  41 pixels wide and 41 high. A radius of 0 sets just the centre.
- **The aspect squashes one axis.** Below 1 the circle keeps its width and
  gets flatter (`.5` halves the height); above 1 it keeps its height and gets
  narrower. A negative aspect is error 5.
- **Angles are in radians, counter-clockwise from 3 o'clock.** `0,1.57` draws
  the upper-right quarter; `0,3.14` the top half. If the end is smaller than
  the start, the arc runs through 0. A *negative* angle also draws a radius
  line from the centre to that end of the arc, so `-0.1,-1.57` draws a pie
  slice.
- **The angle limit is just above 2π.** An angle whose size is 6.283245 or
  more is `Illegal function call`; 6.28319 and everything near 2π below that
  boundary still draw. The boundary was measured on the VG-8020.
- **Off the screen is not an error.** A centre at `(300,300)` or `(-5,-5)`
  draws whatever part is visible. Large radii work too: a radius of 256 or
  more is drawn exactly as on the reference.
- **The colour defaults to the foreground colour** and is checked, 0 to 15;
  each pixel takes the SCREEN 2 colour clash as [`PSET`](PSET.md) does.
- **After `CIRCLE`, the last point is the centre**, so `STEP` and
  `LINE -(x,y)` continue from there.
- **A stray argument after a complete list** (`CIRCLE(50,50),20,5,0.1,6.2,1,`)
  draws the circle first and *then* raises `Syntax error`, as on both
  references.
- **SCREEN 3 works too;** in SCREEN 0 or 1 `CIRCLE` is
  `Illegal function call`, checked after the centre and radius.

| you write | you get |
|---|---|
| `CIRCLE(100,100),20` in SCREEN 0 or 1 | error 5, `Illegal function call` |
| `CIRCLE(99,99),5,16` (colour) | error 5, `Illegal function call` |
| `CIRCLE(99,99),5,1,7` (angle) | error 5, `Illegal function call` |
| `CIRCLE(99,99),5,1,,,-1` (aspect) | error 5, `Illegal function call` |
| `CIRCLE(32768,0),10`, `CIRCLE(0,0),32768` | error 6, `Overflow` |
| `CIRCLE(99,99),"A"` | error 13, `Type mismatch` |
| `CIRCLE(99,99)`, `CIRCLE STEP 1,1,5` | error 2, `Syntax error` |
| `CIRCLE(99,99),5,` (comma, nothing after) | error 24, `Missing operand` |

The errors measured for `CIRCLE` are {2, 5, 6, 13, 24}, the same on both
machines.

## Example

```
10 SCREEN 2
20 CIRCLE(50,50),10,15
30 A=POINT(60,50):B=POINT(50,50)
40 CIRCLE(150,50),10,7,0,1.57
50 C=POINT(160,50):D=POINT(140,50)
60 CIRCLE(100,120),20,13,,,.5
70 E=POINT(120,120):F=POINT(100,140)
80 ON ERROR GOTO 110
90 CIRCLE(99,99),5,16
100 SCREEN 0:PRINT A;B;C;D;E;F;G:END
110 G=ERR:RESUME NEXT
RUN
 15  4  7  4  13  4  5
```

The circle's rim is drawn and its centre is not (15, 4); the arc reaches its
right-hand point but not its left (7, 4); the flattened ellipse reaches out
20 to the side but not 20 down (13, 4).

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_circle.out`](../../scratchpad/kwdoc_circle.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

**A negative radius is error 5 here.** `CIRCLE(99,99),-5` is
`Illegal function call` on zerobas at once. The VG-8020 accepts it and keeps
drawing for a long time before it finishes, apparently treating the radius as
a very large positive number. When the graphics slice was designed the
reference seemed to hang, and Joost signed off on error 5 as a documented
deviation on 2026-07-21
([spec-basic-graphics-g4.md](../spec-basic-graphics-g4.md) §9). Re-measured on
2026-09-27 (D-CIRCNEGR), the reference does come back; matching it would mean
matching a very slow draw, so the item stays open in [TODO.md](../../TODO.md)
to be measured before anything is chosen.

The one rung not yet proven is **RAM usage**.

## What we found, and how

- **`CIRCLE` arrived on 2026-07-21** (graphics slice G4), its pixel sets for
  circles of six sizes and four aspect ratios fitted against captures from the
  VG-8020 until every one matched. One belief did not survive: a "round on the
  screen" default aspect — the measured default is round in *pixels*
  ([spec-basic-graphics-g4.md](../spec-basic-graphics-g4.md)).
- **A radius of 256 or more drew pixels the reference does not** (fixed
  2026-08-16, D-CIRCOVF). A 16-bit product overflowed. Which answer is right
  had to be measured first: no circle centred on the screen can show it, so
  the test moves the centre off screen until the large part comes into view
  ([circovf-msx1-oracle.md](../circovf-msx1-oracle.md)).
- **The radius line of an arc ended one pixel off** near angle 0, and drew in
  a different column on a large off-screen arc (fixed 2026-08-17, D-ARCMASK
  and D-SPOKELINE). The second one turned out to be about `LINE`: the
  reference moves a line's off-screen end onto the screen before drawing
  ([spokeline-msx1-characterization.md](../spokeline-msx1-characterization.md)).
- **A dangling comma drew the circle and reported nothing** (fixed
  2026-08-23, D-CIRCMISS); both references raise `Missing operand` and draw
  nothing. The opposite case, a stray argument after a complete list, draws
  and then raises — that one was fixed the next day (D-CIRCTC,
  [spec-basic-circle-restructure.md](../spec-basic-circle-restructure.md)).
- **An angle past 2π was drawn** (fixed 2026-09-30, D-CIRCANGLE). The
  reference refuses it with error 5. The boundary took five rounds of
  measurement to pin down, because it is not 2π itself but 6.283245.

## Where it lives

`ex_circle` in [basic/graphics.asm](../../basic/graphics.asm) is the entry; the
arguments are read by `circleparse_tenant` in
[sub/circleparse.asm](../../sub/circleparse.asm) (the angle check is
`cpt_angle_from_arga`), and the drawing is `gfx_circle_op` in
[sub/graphics.asm](../../sub/graphics.asm).

## Tests that cover it

- `make graphics-acceptance` — whole bitmaps against the VG-8020: circles,
  ellipses, arcs, radius lines, large radii and off-screen centres.
- `make lineerr-acceptance` — the error order shared with the other drawing
  statements.
- `make kwsweep` — one row per form (circle, arc, `STEP`, aspect, default
  colour) and one error row per code.
- `make kwram` — the RAM-usage comparison.
