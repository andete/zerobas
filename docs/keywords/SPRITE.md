<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `SPRITE` — sprite shapes, and the collision switch

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. No known divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

Sprites are small shapes the video chip draws over the screen by itself. The
`SPRITE` keyword has two jobs: `SPRITE$(n)` holds the *shape* of sprite
pattern `n`, and `SPRITE ON` / `SPRITE OFF` / `SPRITE STOP` decide whether a
collision between two sprites calls the `ON SPRITE GOSUB` handler. Sprites are
placed on the screen with `PUT SPRITE`, which this page covers too. zerobas
behaves like the Philips VG-8020 in every case we have measured.

## Syntax

```
SPRITE$(<n>) = <string expression>
<string variable> = SPRITE$(<n>)
SPRITE ON | SPRITE OFF | SPRITE STOP
PUT SPRITE <plane>,[[STEP](<x>,<y>)][,[<colour>][,<pattern>]]
ON SPRITE GOSUB [<line number>]
```

## Details

### `SPRITE$` — the shape

- **A pattern is 8 bytes, or 32 for 16×16 sprites** (`SCREEN 2,2` or `,3`).
  The size set by `SCREEN` stays in force through later `SCREEN` statements
  that leave it out.
- **The string is fitted to that size:** a shorter one is padded with zero
  bytes, a longer one is cut, `""` clears the pattern. Reading it back always
  gives the full 8 or 32 bytes.
- **`n` is 0 to 255** in every sprite size; a fraction is truncated.
- **Writing needs a graphics screen:** in SCREEN 0 it is error 5. Reading is
  allowed in every mode.

### `PUT SPRITE` — the position

- **`plane` 0 to 31** is the sprite's slot; `colour` 0 to 15; `pattern` 0 to
  255 for 8×8 sprites, 0 to 63 for 16×16.
- **x and y are not clipped or checked**; they are stored modulo 256, so a
  sprite can be placed partly off the screen. A negative x is stored as
  x+32, with the "early clock" bit set in the plane's colour byte.
- **Anything left out stays as it was** in that plane: `PUT SPRITE 0,,5`
  changes only the colour.
- **`PUT SPRITE` needs no `SPRITE ON`.** In SCREEN 0 it is error 5.

### `SPRITE ON` / `OFF` / `STOP` — collisions

- **`ON SPRITE GOSUB 500` arms the handler; `SPRITE ON` enables it.** Neither
  alone is enough.
- **While two sprites overlap, the handler is called once per frame**, over
  and over, not once per collision. It runs between statements.
- **`SPRITE STOP` behaves exactly like `SPRITE OFF`**: on the VG-8020 a
  collision during `SPRITE STOP` is not remembered for later.
- **`ON SPRITE GOSUB` with no line number** removes the handler without
  disabling the trap; a later `ON SPRITE GOSUB 500` works again without a new
  `SPRITE ON`.
- **The collision flag is not consumed**: `VDP(8)` still shows it while the
  trap is enabled.
- These statements are accepted in every screen mode.

| you write | you get |
|---|---|
| `SPRITE$(256)="A"` or `SPRITE$(-1)` | error 5, `Illegal function call` |
| `SPRITE$(0)="A"` in SCREEN 0 | error 5, `Illegal function call` |
| `SPRITE$(0)=5` | error 13, `Type mismatch` |
| `SPRITE`, `SPRITE ON 1`, `SPRITE FOO` | error 2, `Syntax error` |
| `PUT SPRITE 32,…`, colour 16, pattern 256 (or 64 for 16×16) | error 5 |
| `PUT SPRITE 0` (no position at all) | error 2, `Syntax error` |
| `PUT SPRITE 0,(10,10),` (comma, nothing after) | error 24, `Missing operand` |
| `ON SPRITE GOSUB 777` with no line 777 | error 8, `Undefined line number` |

## Example

```
10 SCREEN 2
20 SPRITE$(0)=STRING$(8,255)
30 A=ASC(SPRITE$(0)):L=LEN(SPRITE$(0))
40 PUT SPRITE 0,(100,50),13,0
50 Y=VPEEK(6912):C=VPEEK(6915)
60 ON SPRITE GOSUB 140
70 PUT SPRITE 1,(104,50),15,0
80 SPRITE ON:T=TIME
90 IF H=0 AND TIME-T<60 THEN 90
100 SPRITE OFF
110 SCREEN 0
120 PRINT A;L;Y;C;H
130 END
140 H=1:RETURN
RUN
 255  8  50  13  1
```

Sprite 0 is a solid 8×8 block; its position and colour are read back from
the sprite attribute table at 6912 (`&H1B00`, as `BASE(13)` reports for
SCREEN 2). Sprite 1 overlaps it, so the handler at line 140 runs.

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_sprite.out`](../../scratchpad/kwdoc_sprite.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

None known.

The one rung not yet proven is **RAM usage**.

## What we found, and how

- **`SPRITE$` and `PUT SPRITE` arrived on 2026-07-22** (graphics slice G7),
  every rule above measured on the VG-8020 first
  ([spec-basic-graphics-g7.md](../spec-basic-graphics-g7.md)). `SPRITE ON`,
  `OFF` and `STOP` were accepted but did nothing until the collision trap
  arrived on 2026-07-25
  ([spec-traps-t4-sprite.md](../spec-traps-t4-sprite.md)).
- **A trailing argument on `PUT SPRITE`** (fixed 2026-08-24, D-SPRITE5): both
  references place the sprite and *then* raise `Syntax error`; zerobas raised
  it before placing ([spec-basic-sprite5.md](../spec-basic-sprite5.md)).
- **A dangling comma on `PUT SPRITE` was accepted** (fixed 2026-08-23,
  D-MISSOPFIX); both references raise `Missing operand`.
- **Every sprite test used pattern 0**, so a `SPRITE$` that ignored its index
  would have passed. A test now writes pattern 3, then pattern 0, and reads
  pattern 3 back.

## Where it lives

All in [basic/graphics.asm](../../basic/graphics.asm) and the graphics tenant
in [sub/graphics.asm](../../sub/graphics.asm):

- `ex_sprite` handles `SPRITE$(n)=` and `SPRITE ON/OFF/STOP`; `ev_f_sprite`
  reads `SPRITE$(n)`; the tenant's `gfx_spr_wpat` / `gfx_spr_rpat` move the
  bytes.
- `ex_put_sprite` parses `PUT SPRITE`; `gfx_spr_attr` writes the plane's
  attribute entry.
- `ex_on_sprite` in [basic/program.asm](../../basic/program.asm) arms the
  handler; the once-per-frame collision check is
  [basic/sprtrap-body.inc](../../basic/sprtrap-body.inc).

## Related concepts

- [Interrupts and traps](../concepts/interrupts-and-traps.md) — what runs between statements
- [Screen modes](../concepts/screen-modes.md) — the four MSX1 displays

## Tests that cover it

- `make graphics-acceptance` — the pattern and attribute tables read back
  against the VG-8020, sprite sizes included.
- `make sprite-trap-acceptance` — arming, enabling, `STOP`, disarming and the
  once-per-frame rate.
- `make kwsweep` — the pattern write, `SPRITE ON` and `SPRITE OFF`/`STOP`
  with two real overlapping sprites, the attribute bytes, and the error rows.
- `make kwram` — the RAM-usage comparison.
