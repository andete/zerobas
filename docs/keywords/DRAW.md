<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `DRAW` — draw with a string of pen commands

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. No known divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`DRAW "R10D10"` moves an invisible pen over the graphics screen, drawing as it
goes: here 10 pixels right, then 10 down, starting at the last point. The
string is a small command language with directions, moves, colour, scale,
rotation and sub-strings. zerobas draws the same pixels as the Philips
VG-8020 and raises the same errors in every case we have measured.

## Syntax

```
DRAW <string expression>
```

The commands, each a letter followed by an optional number:

| command | meaning |
|---|---|
| `U` `D` `L` `R` | up, down, left, right `n` pixels (`n` defaults to 1) |
| `E` `F` `G` `H` | diagonally up-right, down-right, down-left, up-left, `n` in each axis |
| `M x,y` | line to the point `(x,y)`; with a sign on `x` (`M+20,-5`) it is relative |
| `B` before a command | move without drawing |
| `N` before a command | draw, then return to where the pen was |
| `C n` | colour 0–15 |
| `S n` | scale, in quarters: `S4` is 1:1, `S8` doubles, `S0` means 4 |
| `A n` | rotate later relative moves by 0, 90, 180 or 270 degrees (`n` 0–3) |
| `X var$;` | run the commands in a string variable, then continue |
| `=var;` | use a variable as a command's number: `R=L;` |

## Details

- **Scale and angle are remembered between statements — and between
  programs.** `S` and `A` survive `RUN`, `NEW`, `CLEAR`, `CLS`, `COLOR` and
  `SCREEN`; only switching the machine off resets them. A program that
  depends on them should set them itself, which is why the example starts with
  `S4A0`.
- **The pen colour is shared with the other graphics statements.** A `DRAW`
  without `C` draws in the colour the previous graphics statement used, and a
  `C` in a `DRAW` stays in force for the next `DRAW`. A `LINE` without a
  colour sets it back to the foreground colour.
- **Rotation applies to relative moves only** — the eight letters and a
  signed `M` — never to an absolute `M`.
- **Large counts wrap the way the reference's do.** Once an `S` has run, the
  distance is the count times the scale in 16-bit arithmetic, divided by 4.
  From power-on, before any `S`, the count is used as it is.
- **Off-screen moves are not errors.** Each segment's ends are moved onto the
  screen edge before drawing, exactly as [`LINE`](LINE.md) does; the pen
  position keeps the real, unmoved coordinates.
- **Spaces are ignored anywhere in the string**, `;` may end a command, and
  lower-case letters work. A leading `;`, a doubled `;;`, or a `,` between
  commands is an error.
- **The screen mode is checked first.** In SCREEN 0 or 1 `DRAW` is error 5 —
  even `DRAW 5`, which is error 13 in SCREEN 2.

| you write | you get |
|---|---|
| `DRAW"Q"`, `DRAW"BQ"` (unknown letter) | error 5, `Illegal function call` |
| `DRAW"M"`, `DRAW"M+5"`, `DRAW"X"` (missing part) | error 5, `Illegal function call` |
| `DRAW"C16"`, `DRAW"S256"`, `DRAW"A4"` | error 5, `Illegal function call` |
| `DRAW"U="` (no `;`) | error 5, `Illegal function call` |
| any `DRAW` in SCREEN 0 or 1 | error 5, `Illegal function call` |
| `DRAW 5` in SCREEN 2 | error 13, `Type mismatch` |
| `DRAW"XA;"`, `DRAW"U=A$;"` (wrong variable type) | error 13, `Type mismatch` |
| `DRAW` alone, in SCREEN 2 | error 24, `Missing operand` |

The errors measured for `DRAW` are {5, 13, 24}, the same on both machines.
Not measured: how deep `X` sub-strings may nest, or what a string that runs
itself (`A$="XA$;"`) does on the reference.

## Example

```
10 SCREEN 2
20 PSET(10,10),15
30 DRAW"S4A0C15R10D10"
40 A=POINT(15,10):B=POINT(20,15)
50 DRAW"BM100,100C7U10"
60 C=POINT(100,95):D=POINT(60,60)
70 M$="R5":DRAW"C13BM50,150XM$;"
80 E=POINT(53,150)
90 ON ERROR GOTO 120
100 DRAW"Q"
110 SCREEN 0:PRINT A;B;C;D;E;F:END
120 F=ERR:RESUME NEXT
RUN
 15  15  7  4  13  5
```

The pen draws right and down from (10,10); `BM` jumps to (100,100) without
leaving a trace at (60,60); `XM$;` runs the commands held in `M$`.

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_draw.out`](../../scratchpad/kwdoc_draw.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

None known.

The one rung not yet proven is **RAM usage**.

## What we found, and how

- **`DRAW` arrived on 2026-07-22** (graphics slice G6), after its language
  was measured on the reference: the scale rule, the persistence of `S` and
  `A`, and the shared colour, which took three rounds to pin down
  ([spec-basic-graphics-g6.md](../spec-basic-graphics-g6.md)).
- **`DRAW A$` was a `Type mismatch`** (fixed 2026-08-11, D-DRAWERR): `DRAW`
  accepted a string written in quotes and nothing else. The same sweep found
  that spaces were accepted only *between* commands, so `DRAW"R 10"` was an
  error where both references draw
  ([spec-basic-lineerr.md](../spec-basic-lineerr.md) §11).
- **The power-on scale is not `S4`** (fixed 2026-08-11, D-DSCALE). It is a
  separate "never set" state in which the scale arithmetic does not run, and
  only a very large count can tell the two apart: `DRAW"BU40000"` from
  power-on moves the full 40000. The same work found a second rounding
  difference at one exact 16-bit value.
- **Off-screen moves were clipped instead of clamped** (fixed 2026-08-17,
  D-DRAWCLAMP), the same correction `LINE` had received that day. The one test
  that was meant to cover it drew a horizontal line, for which both rules give
  the same pixels
  ([drawclamp-msx1-characterization.md](../drawclamp-msx1-characterization.md)).
- **A bare `DRAW` in SCREEN 2 was error 13** (fixed 2026-08-26, D-DRAWOP);
  both references say `Missing operand` (24). An earlier test had run it in
  SCREEN 0, where the mode check answers first, and so could not see it.
- **The tests themselves met the persistence rule.** A test that set `A1`
  rotated every later test in the same run; every `DRAW` test now starts with
  `A0S4`.

## Where it lives

`ex_draw` in [basic/graphics.asm](../../basic/graphics.asm) checks the mode
and evaluates the string; the command language runs in the graphics tenant,
`gfx_draw_op` in [sub/graphics.asm](../../sub/graphics.asm), with the moves in
`gdrw_move_rel` / `gdrw_move_abs` and the scale in `gdrw_scale`.

## Tests that cover it

- `make graphics-acceptance` — pixels against the VG-8020 for the commands,
  the colour rule and off-screen moves.
- `make lineerr-acceptance` — the error order and the scale state.
- `make kwsweep` — one row per command form (ten of them) and the error rows
  for {5, 13}.
- `make kwram` — the RAM-usage comparison.
