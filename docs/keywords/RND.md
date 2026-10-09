<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `RND` — a pseudo-random number

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. No known divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`RND(x)` returns a pseudo-random number from 0 up to (but not including) 1,
with 14 significant digits. The numbers come from a fixed formula, so a
program can make the sequence repeat. zerobas produces **the same sequence,
digit for digit**, as the Philips VG-8020: the formula was worked out by
watching the reference's output, without reading its ROM.

## Syntax

```
RND(<numeric expression>)
```

One argument, always. What the argument does depends only on its sign.

## Details

- **A positive argument gives the next number.** Its value does not matter:
  `RND(1)`, `RND(7)` and `RND(.3)` all step the sequence once, identically.
- **`RND(0)` repeats the last number** without stepping.
- **A negative argument restarts the sequence** from a point chosen by the
  argument's digits, and returns the first number from there. The same
  argument always gives the same restart, so `RND(-1)` makes everything after
  it repeatable. Only the digits count, not the position of the decimal
  point: `RND(-1)`, `RND(-0.001)` and `RND(-1E9)` restart at the same place.
  A single-precision `-1/3` and a double-precision `-1/3` have different digits,
  so they restart at different places.
- **`RUN`, `NEW` and `CLEAR` reset the sequence** to its power-on start, so an
  unseeded program draws the same numbers every time it is run; `CLS` does
  not reset it.
- **There is no `RANDOMIZE`** in MSX1 BASIC: the VG-8020 answers it with
  `Syntax error`. Use `RND(-x)` with a changing `x` instead.
- **A string argument** (`RND("A")`) is `Type mismatch` (error 13).
- **No argument, two arguments, no parentheses or a missing `)`** —
  `RND()`, `RND(1,2)`, `PRINT RND`, `RND(1` — are all `Syntax error`
  (error 2), and the sequence is left untouched.

| you write | you get |
|---|---|
| `RND(1)<1` | −1 (true) |
| `INT(RND(-1)*10000)` | 438 |
| `RND(-1)=RND(-1)` | −1 (true) |
| `RND("A")` | error 13, `Type mismatch` |
| `RND()`, `RND(1,2)` | error 2, `Syntax error` |

The whole set of errors `RND` can raise is {2, 13}, the same on both machines.

## Example

Line 30 shows that restarting with `RND(-1)` repeats the sequence, line 40
that `RND(0)` repeats the last number. MSX prints a true comparison as −1.

```
10 A=RND(-1):B=RND(1):C=RND(1)
20 D=RND(-1):E=RND(1):F=RND(1)
30 PRINT A=D;B=E;C=F
40 PRINT RND(0)=F
50 PRINT INT(RND(-1)*10000)
60 PRINT RND(1)<1
70 ON ERROR GOTO 100
80 PRINT RND("A")
90 END
100 PRINT "Error";ERR:RESUME NEXT
RUN
-1 -1 -1
-1
 438
-1
Error 13
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_rnd.out`](../../scratchpad/kwdoc_rnd.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

None known.

The one rung not yet proven is **RAM usage**: `RND` uses the same amount of
free memory on both machines, and its state now lives at the same address as
the reference's (below), but the two still write different work-area cells
along the way — the VG-8020 a few that zerobas does not, and zerobas a few of
its own.

## What we found, and how

- **The generator was recovered from the outside** (2026-07-14). Capturing
  consecutive values, restarts and edge cases on the VG-8020 was enough to
  pin down the formula and its three constants exactly; zerobas reproduces
  every captured value, and the tests compare whole sequences digit for digit
  ([spec-basic-mathpack-slice2.md](../spec-basic-mathpack-slice2.md) §15).
- **A malformed call changed the sequence** (fixed 2026-07-14, D-F2-4).
  `RND(1.5,2)` stepped the sequence and `RND(-1.5` (missing `)`) restarted it,
  so every later number was different — where the VG-8020 stops with
  `Syntax error` and leaves the sequence alone. Now zerobas does the same
  ([spec-basic-malformed-call-syntax-error.md](../spec-basic-malformed-call-syntax-error.md)).
- **A test that only checked the range could not see the sequence**
  (D-KWBREADTH, 2026-09-13). `RND(1)<1` is true for any working generator. A
  row reading `INT(RND(-1)*10000)` — 438 on the VG-8020, on the CF-3300 and on
  zerobas — now checks the generator itself.
- **The state moved to the reference's own address** (D-ADDR29, 2026-09-25).
  MSX publishes the address of `RNDX`, where the generator keeps its state.
  Joost ruled on 2026-09-24 to rehome the published variables, *"`RNDX` now"*
  among them. In seven different states zerobas's bytes then matched the
  VG-8020's at that address every time
  ([spec-basic-addr29.md](../spec-basic-addr29.md),
  [`rndx_after.out`](../../scratchpad/rndx_after.out)).
- **The whole error set was measured on the reference** (D-KWT6, 2026-09-27):
  wrong type, no argument and an extra argument; zerobas matched every case
  ([`t6enum_b5.out`](../../scratchpad/t6enum_b5.out)).

## Where it lives

- Main ROM: dispatched by `evmc_total_scan` in
  [basic/expr.asm](../../basic/expr.asm) through `evmc_total_tab` in
  [basic/islands.asm](../../basic/islands.asm). `clear_vars` in
  [basic/vars.asm](../../basic/vars.asm) resets the state on `RUN`, `NEW` and
  `CLEAR`.
- Sub-ROM: `fp_rnd` in [sub/fp_rnd.asm](../../sub/fp_rnd.asm) steps,
  restarts or repeats the sequence.

## Tests that cover it

- `make math-acceptance` — whole sequences compared digit for digit with the
  VG-8020: from power-on, after restarts, `RND(0)`, positive arguments of
  different values, and the reset by `NEW`, `CLEAR` and `RUN`; plus the
  malformed calls, with a check that they leave the sequence alone.
- `make kwsweep` — the rows `RND(1)<1` and `INT(RND(-1)*10000)`, the error
  rows for {2, 13}, and the deliberately-broken-build check.
- `make kwram` — the RAM-usage comparison.
