<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `SGN` — the sign of a number

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. No known divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`SGN(x)` tells you the sign of `x`: −1 when it is negative, 0 when it is zero,
1 when it is positive. zerobas behaves exactly like the Philips VG-8020 for
every case we have measured, errors included.

## Syntax

```
SGN(<numeric expression>)
```

One argument, always.

## Details

- **Three possible answers**, whatever the size or type of the argument:
  `SGN(-5)` is −1, `SGN(0)` is 0, `SGN(2.5)` is 1, `SGN(-1E38)` is −1.
- **The result is an integer**, so `SGN(2.5)+0.5` is 1.5, not 3.
- **A space before the parenthesis is allowed**: `SGN (7)` is 1.
- **A string argument** (`SGN("A")`) is `Type mismatch` (error 13).
- **No argument, two arguments, no parentheses or a missing `)`** —
  `SGN()`, `SGN(1,2)`, `PRINT SGN`, `SGN(1` — are all `Syntax error`
  (error 2).

| you write | you get |
|---|---|
| `SGN(-5)`, `SGN(-1E38)` | −1 |
| `SGN(0)` | 0 |
| `SGN(5)`, `SGN(2.5)` | 1 |
| `SGN("A")` | error 13, `Type mismatch` |
| `SGN()`, `SGN(1,2)` | error 2, `Syntax error` |

The whole set of errors `SGN` can raise is {2, 13}, the same on both machines.

## Example

```
10 PRINT SGN(-5);SGN(0);SGN(5)
20 PRINT SGN(-2.5);SGN(2.5)
30 PRINT SGN (7)
40 ON ERROR GOTO 70
50 PRINT SGN("A")
60 END
70 PRINT "Error";ERR:RESUME NEXT
RUN
-1  0  1
-1  1
 1
Error 13
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_sgn.out`](../../scratchpad/kwdoc_sgn.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

None known.

The one rung not yet proven is **RAM usage**: `SGN` uses the same amount of
free memory on both machines, but the VG-8020 writes a few work-area cells
along the way that zerobas does not. Nothing a program can observe through
`FRE` or the documented variables differs.

## What we found, and how

- **Empty or malformed calls returned a number** (fixed 2026-07-13 and
  2026-07-14, D-F2-3 and D-F2-4). `SGN()` printed 0, and `PRINT SGN` or
  `SGN(1,2)` quietly ran on whatever value was left over from earlier, where the
  VG-8020 says `Syntax error`:
  [spec-basic-empty-expr-syntax-error.md](../spec-basic-empty-expr-syntax-error.md),
  [spec-basic-malformed-call-syntax-error.md](../spec-basic-malformed-call-syntax-error.md).
- **A test that only looked at one sign could not catch much** (D-KWBREADTH,
  2026-09-13). The first test row read `SGN(-3)` alone, and a row that reads
  one sign passes on an implementation that never gives the other two. A row
  reading `SGN(-5);SGN(0);SGN(5)` now covers all three answers.
- **The space before the parenthesis was checked** (D-NUMSPACE, 2026-09-09):
  `SGN (7)` was already accepted, as on both references
  ([`numspace_run.out`](../../scratchpad/numspace_run.out)).
- **The whole error set was measured on the reference** (D-KWT6, 2026-09-27):
  wrong type, no argument, an extra argument and `SGN(-1E38)`; zerobas matched
  every case ([`t6enum_run.out`](../../scratchpad/t6enum_run.out)).

## Where it lives

`evmc_sgn` in [basic/expr.asm](../../basic/expr.asm), reached from the math
selector `ev_ff_mathconv`; the argument is read by `ev_mc_arg`, which all the
math functions share. Its sibling is [`ABS`](ABS.md). The design notes are in
[spec-basic-math-pack.md](../spec-basic-math-pack.md) §9.

## Tests that cover it

- `make math-acceptance` — values and result types against the VG-8020,
  including the empty and malformed calls.
- `make kwsweep` — the everyday rows (`SGN(-3)` and all three signs), the error
  rows for {2, 13}, and the deliberately-broken-build check.
- `make kwram` — the RAM-usage comparison.
