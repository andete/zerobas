<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `ABS` — the absolute value of a number

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. No known divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`ABS(x)` returns `x` without its sign: `ABS(-5)` is 5, `ABS(5)` is 5. It works
on every numeric type and over the whole number range. zerobas behaves exactly
like the Philips VG-8020 for every case we have measured, errors included.

## Syntax

```
ABS(<numeric expression>)
```

One argument, always.

## Details

- **The result keeps the argument's type.** `ABS(-1.5)` is 1.5, `ABS` of a
  double-precision value is double precision, and so on.
- **One integer has no positive twin.** An integer (`A%`) runs from −32768 to
  32767, so `ABS` of an integer −32768 cannot stay an integer: the answer,
  32768, comes back as a non-integer number, as on the reference.
- **No range errors.** `ABS(-1E38)` is fine on both machines; only the type and
  the shape of the call can go wrong.
- **A space before the parenthesis is allowed**: `ABS (-7)` is 7.
- **A string argument** (`ABS("A")`) is `Type mismatch` (error 13).
- **No argument, two arguments, no parentheses or a missing `)`** —
  `ABS()`, `ABS(1,2)`, `PRINT ABS`, `ABS(1` — are all `Syntax error`
  (error 2).

| you write | you get |
|---|---|
| `ABS(-5)`, `ABS(5)` | 5 |
| `ABS(-1.5)` | 1.5 |
| `A%=-32768:PRINT ABS(A%)` | 32768 |
| `ABS(-1E38)` | no error |
| `ABS("A")` | error 13, `Type mismatch` |
| `ABS()`, `ABS(1,2)` | error 2, `Syntax error` |

The whole set of errors `ABS` can raise is {2, 13}, the same on both machines.

## Example

```
10 PRINT ABS(-5);ABS(3.5);ABS(0)
20 A%=-32768:PRINT ABS(A%)
30 PRINT ABS (-7)
40 ON ERROR GOTO 70
50 PRINT ABS("A")
60 END
70 PRINT "Error";ERR:RESUME NEXT
RUN
 5  3.5  0
 32768
 7
Error 13
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_abs.out`](../../scratchpad/kwdoc_abs.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

None known.

The one rung not yet proven is **RAM usage**: `ABS` uses the same amount of
free memory on both machines, but the VG-8020 writes a few work-area cells
along the way that zerobas does not. Nothing a program can observe through
`FRE` or the documented variables differs.

## What we found, and how

- **Empty or malformed calls returned a number** (fixed 2026-07-13 and
  2026-07-14, D-F2-3 and D-F2-4). `ABS()` printed 0, and `PRINT ABS` or
  `ABS(1,2)` quietly ran on whatever value was left over from earlier, where the
  VG-8020 says `Syntax error`. The two fixes cover all the math functions:
  [spec-basic-empty-expr-syntax-error.md](../spec-basic-empty-expr-syntax-error.md),
  [spec-basic-malformed-call-syntax-error.md](../spec-basic-malformed-call-syntax-error.md).
- **The −32768 edge was already right.** A sweep of every place zerobas
  negates a 16-bit number (D-NEG8K, 2026-08-11) found that `ABS` of integer
  −32768 already gave 32768; it was unary minus next to it that had the edge
  backwards. [fixpoint8000-msx1-sweep.md](../fixpoint8000-msx1-sweep.md).
- **Deep nesting gave a nonsense error.** `ABS(ABS(…))` sixteen levels deep
  answered `FIELD overflow` (error 50), while both references go 32 deep
  without trouble (fixed 2026-09-12, D-SPMERGE, which merged two stacks).
- **The space before the parenthesis was checked** (D-NUMSPACE, 2026-09-09):
  `ABS (-7)` was already accepted, as on both references
  ([`numspace_run.out`](../../scratchpad/numspace_run.out)).
- **The whole error set was measured on the reference** (D-KWT6, 2026-09-27):
  wrong type, no argument, an extra argument and `ABS(-1E38)`; zerobas matched
  every case ([`t6enum_run.out`](../../scratchpad/t6enum_run.out)).

## Where it lives

`evmc_abs` in [basic/expr.asm](../../basic/expr.asm), reached from the math
selector `ev_ff_mathconv`; the argument is read by `ev_mc_arg`, which all the
math functions share. The design notes are in
[spec-basic-math-pack.md](../spec-basic-math-pack.md) §9.

## Tests that cover it

- `make math-acceptance` — values and types against the VG-8020, including the
  integer −32768 case and the empty and malformed calls.
- `make kwsweep` — the everyday row (`ABS(-5)`), the error rows for {2, 13},
  and the deliberately-broken-build check.
- `make kwram` — the RAM-usage comparison.
