<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `SQR` — the square root of a number

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. One recorded
> difference: the last printed digit of some roots (below).
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`SQR(x)` returns the square root of `x`, which must not be negative.
`SQR(9)` is 3. The answer has 14 significant digits. zerobas raises the same
errors as the Philips VG-8020 in every case we have measured, and prints the
same value except, for some arguments, in the last digit — where zerobas is
the one that is correctly rounded.

## Syntax

```
SQR(<numeric expression>)
```

One argument, always.

## Details

- **Perfect squares are exact** on both machines: `SQR(16)` is 4,
  `SQR(100)` is 10, `SQR(0)` is 0, `SQR(.25)` is .5.
- **Other roots are rounded to 14 significant digits.** zerobas gives the
  correctly rounded answer; the VG-8020 is sometimes one unit low in the last
  digit (`SQR(2)` and `SQR(3)` are two such cases). See *Differences*.
- **A negative argument** (`SQR(-1)`) is `Illegal function call` (error 5).
- **A string argument** (`SQR("A")`) is `Type mismatch` (error 13).
- **No argument, two arguments, no parentheses or a missing `)`** —
  `SQR()`, `SQR(1,2)`, `PRINT SQR`, `SQR(1` — are all `Syntax error`
  (error 2).

| you write | you get |
|---|---|
| `SQR(9)` | 3 |
| `SQR(16)` | 4 |
| `SQR(0)` | 0 |
| `SQR(-1)` | error 5, `Illegal function call` |
| `SQR("A")` | error 13, `Type mismatch` |
| `SQR()`, `SQR(1,2)` | error 2, `Syntax error` |

The whole set of errors `SQR` can raise is {2, 5, 13}, the same on both
machines.

## Example

```
10 PRINT SQR(9);SQR(16);SQR(0)
20 PRINT SQR(.25);SQR(1E10)
30 ON ERROR GOTO 60
40 PRINT SQR(-1)
50 END
60 PRINT "Error";ERR:RESUME NEXT
RUN
 3  4  0
 .5  100000
Error 5
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_sqr.out`](../../scratchpad/kwdoc_sqr.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

**The last digit of a root that is not exact can differ, by design.** zerobas
computes the correctly rounded 14-digit square root; the VG-8020 is one unit
low in the last digit on some arguments (about 15 of the 72 measured when this
was built). Copying that would mean copying the reference's division, whose
rounding rule could not be recovered from what the machine prints. The
decision, signed off by Joost on 2026-07-13: keep zerobas correctly rounded and
record the difference
([spec-basic-math-pack.md](../spec-basic-math-pack.md) §10.3.1). A program
that prints such a root in full can show a different last digit, and one that
compares it with `=` against a typed-in constant could branch differently.

The one rung not yet proven is **RAM usage**: `SQR` uses the same amount of
free memory on both machines, but the two write different work-area cells
along the way — the VG-8020 a few that zerobas does not, and zerobas some
scratch cells of its own for the calculation.

## What we found, and how

- **Bit-for-bit copying was tried and abandoned** (2026-07-13). The plan was to
  reproduce the reference's own rounding by matching its division. A
  time-boxed attempt got to about 80 % agreement and stopped there: the
  deciding digit sits below the 14 the machine prints. Correct rounding was
  chosen instead, and it is never less accurate than the reference
  ([spec-basic-math-pack.md](../spec-basic-math-pack.md) §10.3.1).
- **One near-tie is a precision floor.** `SQR(99.99998)` is the only argument
  found where zerobas cannot round correctly; the reference gives the same
  answer there. It is pinned in the tests so it cannot drift.
- **Empty or malformed calls** (fixed 2026-07-13 and 2026-07-14, D-F2-3 and
  D-F2-4). `SQR()` printed 0, and `PRINT SQR` or `SQR(1,2)` gave a wrong
  value or a wrong error, where the VG-8020 says `Syntax error`:
  [spec-basic-malformed-call-syntax-error.md](../spec-basic-malformed-call-syntax-error.md).
- **The whole error set was measured on the reference** (D-KWT6, 2026-09-27):
  wrong type, no argument, an extra argument, `SQR(-1)` and `SQR(0)`; zerobas
  matched every case ([`t6enum_run.out`](../../scratchpad/t6enum_run.out)).

## Where it lives

- Main ROM: `evmc_sqr` in [basic/expr.asm](../../basic/expr.asm) reads the
  argument, rejects a negative one (`evmc_sqr_err`) and hands the rest on.
- Sub-ROM: `fp_sqrt` in [sub/fp_sqrt.asm](../../sub/fp_sqrt.asm) computes the
  root.
- The design notes are in [spec-basic-math-pack.md](../spec-basic-math-pack.md)
  §10.

## Tests that cover it

- `make math-acceptance` — roots against the mathematically true value, the
  known near-tie, the negative-argument error, and the empty and malformed
  calls.
- `make kwsweep` — the everyday row (`SQR(9)`), the error rows for {2, 5, 13},
  and the deliberately-broken-build check.
- `make kwram` — the RAM-usage comparison.
