<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `VPOKE` — write one byte of video memory

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. No known divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`VPOKE a,v` writes the byte `v` (0 to 255) to address `a` of the video memory
(VRAM), the 16 KB the video chip draws the screen from. What the write does
depends on which table lives at that address in the current screen mode.
[`VPEEK`](VPEEK.md) reads the byte back. zerobas behaves like the Philips
VG-8020 in every case we have measured, errors included.

## Syntax

```
VPOKE <address>,<value>
```

Both arguments are required. The address runs 0 to 16383 (`&H3FFF`), the
value 0 to 255.

## Details

- **The address is checked like `VPEEK`'s:** outside −32768 to 32767 is
  `Overflow` (error 6); inside that but outside 0 to 16383 is
  `Illegal function call` (error 5).
- **The value is a byte, and it is checked too.** `VPOKE a,256` and
  `VPOKE a,-1` are error 5 and leave the byte as it was; nothing wraps.
- **A missing value is an error, not a zero.** `VPOKE 0,` is
  `Missing operand` (error 24) and writes nothing.
- **The tables move with the screen mode.** `BASE(n)` reports where each one
  is; in SCREEN 0 the name table (which character shows where) starts at
  address 0, so a `VPOKE` there changes what is on the screen.

| you write | you get |
|---|---|
| `VPOKE 16384,1` | error 5, `Illegal function call` |
| `VPOKE 16000,256`, `VPOKE 16000,-1` | error 5, `Illegal function call`, byte unchanged |
| `VPOKE 70000,1` | error 6, `Overflow` |
| `VPOKE "A",1` | error 13, `Type mismatch` |
| `VPOKE 1` | error 2, `Syntax error` |
| `VPOKE`, `VPOKE 0,` | error 24, `Missing operand` |

The whole set of errors `VPOKE` can raise is {2, 5, 6, 13, 24}, the same on
both machines.

## Example

```
10 VPOKE 16383,7
20 PRINT VPEEK(16383)
30 ON ERROR GOTO 80
40 VPOKE 16384,1
50 VPOKE 16383,256
60 PRINT VPEEK(16383)
70 END
80 PRINT "Error";ERR:RESUME NEXT
RUN
 7
Error 5
Error 5
 7
```

The first error is the address, one past the end of video memory; the second
is the value. The byte at 16383 is still 7 afterwards.

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_vpoke.out`](../../scratchpad/kwdoc_vpoke.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

None known.

The one rung not yet proven is **RAM usage**.

## What we found, and how

- **The address had the wrong range** (fixed 2026-07-19, D-F2-2). zerobas
  accepted any address up to 65535, the range of ordinary memory; the
  VG-8020 allows only the 16 KB of video memory
  ([spec-basic-df2-2-intarg-coercion.md](../spec-basic-df2-2-intarg-coercion.md)).
- **`VPOKE 0,` wrote a zero** (fixed 2026-08-23, D-MISSOPFIX). A forgotten
  value silently overwrote the byte; both references raise
  `Missing operand` and leave it alone. `POKE` had the same fault three ways.
- **The value wrapped** (fixed 2026-09-08, D-RAWVAL). zerobas read the value
  with the rules for an *address*, so `,256` wrote 0 and `,-1` wrote 255 with
  no error; both references raise error 5. Every earlier test of `VPOKE`,
  `POKE` and `OUT` had been about the first argument only, and a review had
  recorded this exact suspicion as "no finding"
  ([spec-basic-rawval.md](../spec-basic-rawval.md)).
- **The tests read the byte back**, at address 0, at the last address 16383
  and with the largest value 255, so a `VPOKE` that parsed and wrote nothing
  — or wrote to the wrong place — fails.

## Where it lives

`ex_vpoke` in [basic/interp.asm](../../basic/interp.asm) hands over to
`do_vpoke` in [basic/vdpio.asm](../../basic/vdpio.asm), which checks the
address with `get_vram_arg` (shared with `VPEEK`), reads the value with
`vdp_comma_byte`, and writes through the BIOS.

## Related concepts

- [Screen modes](../concepts/screen-modes.md) — the four MSX1 displays

## Tests that cover it

- `make intarg-acceptance` — the address and value ranges.
- `make kwsweep` — the round trips through `VPEEK` and the error rows for
  {2, 5, 6, 13, 24}.
- `make kwram` — the RAM-usage comparison.
