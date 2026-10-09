<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `VPEEK` — read one byte of video memory

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. No known divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`VPEEK(a)` returns the byte, 0 to 255, at address `a` of the video memory
(VRAM) — the separate 16 KB the video chip draws the screen from. It is the
reading half of [`VPOKE`](VPOKE.md), as `PEEK` is of `POKE`. zerobas behaves
like the Philips VG-8020 in every case we have measured, errors included.

## Syntax

```
VPEEK(<address>)
```

One argument. The address runs 0 to 16383 (`&H3FFF`).

## Details

- **What lives where depends on the screen mode.** The tables the chip reads
  — names (which character or pattern goes where), patterns, colours, sprite
  attributes and sprite patterns — sit at the addresses `BASE(n)` reports.
  Measured on both machines: in SCREEN 2 the sprite attribute table is at
  `&H1B00` (6912), so `VPEEK(6912)` is the y position of sprite plane 0 after
  a `PUT SPRITE`; in SCREEN 0 the name table starts at 0.
- **Two range checks, in this order:**
  1. outside −32768 to 32767 → `Overflow` (error 6);
  2. inside that range but outside 0 to 16383 → `Illegal function call`
     (error 5). Negative addresses fall here.
- **A wrong address is a clean error.** `PRINT VPEEK(-1)` prints the error
  message and nothing else.

| you write | you get |
|---|---|
| `VPEEK(16383)` | the last byte of VRAM |
| `VPEEK(16384)`, `VPEEK(-1)` | error 5, `Illegal function call` |
| `VPEEK(70000)` | error 6, `Overflow` |
| `VPEEK("A")` | error 13, `Type mismatch` |
| `VPEEK()` | error 2, `Syntax error` |

The whole set of errors `VPEEK` can raise is {2, 5, 6, 13}, the same on both
machines.

## Example

```
10 VPOKE 16383,7:A=VPEEK(16383)
20 VPOKE 16383,255:B=VPEEK(16383)
30 PRINT A;B
40 ON ERROR GOTO 80
50 PRINT VPEEK(16384)
60 PRINT VPEEK(70000)
70 END
80 PRINT "Error";ERR:RESUME NEXT
RUN
 7  255
Error 5
Error 6
```

Address 16383 is the last byte of an MSX1's video memory; one past it is
error 5, and a number too large for an integer is error 6.

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_vpeek.out`](../../scratchpad/kwdoc_vpeek.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

None known.

The one rung not yet proven is **RAM usage**.

## What we found, and how

- **Out-of-range addresses used to be accepted** (fixed 2026-07-19, D-F2-2).
  Measuring the VG-8020 showed the address range is the 16 KB of video
  memory, with the two checks above. The same measurement corrected `VPOKE`,
  which had been given the 64 KB range of ordinary memory
  ([spec-basic-df2-2-intarg-coercion.md](../spec-basic-df2-2-intarg-coercion.md)).
- **`PRINT VPEEK(-1)` printed the error and then ` 32`** (fixed 2026-07-28,
  D-CUR-D). After an error, zerobas returned into the statement and carried
  on printing a value; the reference stops. Nine statements shared the
  fault, and one fix in the error path cured them all
  ([spec-basic-abort-depth.md](../spec-basic-abort-depth.md)).
- **The test reads back a byte it wrote**, so a `VPEEK` that returned a
  constant could not pass.

## Where it lives

`ev_ff_vpeek` in [basic/expr.asm](../../basic/expr.asm) reads the byte through
the BIOS; the address check is `get_vram_arg` in
[basic/interp.asm](../../basic/interp.asm), shared with `VPOKE`.

## Related concepts

- [Screen modes](../concepts/screen-modes.md) — the four MSX1 displays

## Tests that cover it

- `make intarg-acceptance` — the address range and its two errors.
- `make abort-acceptance` — `PRINT VPEEK(-1)` stops at the error.
- `make kwsweep` — the round trip through `VPOKE`, and the error rows for
  {2, 5, 6, 13}.
- `make kwram` — the RAM-usage comparison.
