<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `FIX` — drop the fraction of a number

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. No known divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`FIX(x)` cuts off the fraction of `x`, toward zero: `FIX(1.7)` is 1 and
`FIX(-1.7)` is −1. Its sibling [`INT`](INT.md) rounds down instead, so the two
differ only for negative numbers with a fraction (`INT(-1.7)` is −2). zerobas
behaves exactly like the Philips VG-8020 for every case we have measured,
errors included.

## Syntax

```
FIX(<numeric expression>)
```

One argument, always.

## Details

- **Toward zero, on both sides.** `FIX(2.7)` is 2 and `FIX(-2.7)` is −2;
  `FIX(-1.5)` is −1.
- **The result keeps the argument's precision and range.** `FIX` does not
  convert to an integer (`A%`), so numbers far outside −32768 to 32767 work:
  `FIX(-1E38)` raises no error. Use [`CINT`](CINT.md) when you need the 16-bit
  integer type.
- **A string argument** (`FIX("A")`) is `Type mismatch` (error 13).
- **No argument, two arguments, no parentheses or a missing `)`** —
  `FIX()`, `FIX(1,1)`, `PRINT FIX`, `FIX(1` — are all `Syntax error`
  (error 2).

| you write | you get |
|---|---|
| `FIX(2.7)` | 2 |
| `FIX(-2.7)` | −2 |
| `FIX(-1.5)` | −1 |
| `FIX(-1E38)` | no error |
| `FIX("A")` | error 13, `Type mismatch` |
| `FIX()`, `FIX(1,1)` | error 2, `Syntax error` |

The whole set of errors `FIX` can raise is {2, 13}, the same on both machines.

## Example

```
10 PRINT FIX(1.7);FIX(-1.7)
20 PRINT FIX(-2.7);INT(-2.7)
30 PRINT FIX(12345678.9#)
40 ON ERROR GOTO 70
50 PRINT FIX("A")
60 END
70 PRINT "Error";ERR:RESUME NEXT
RUN
 1 -1
-2 -3
 12345678
Error 13
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_fix.out`](../../scratchpad/kwdoc_fix.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

None known.

The one rung not yet proven is **RAM usage**: `FIX` uses the same amount of
free memory on both machines, but the two write different work-area cells
along the way — the VG-8020 a few that zerobas does not, and zerobas two of
its own. Nothing a program can observe through `FRE` or the documented
variables differs.

## What we found, and how

- **The tests could not see the result's precision** (found 2026-07-12, in the
  review of the first math slice). The double-precision path was never
  exercised; zerobas turned out to be right, and cases such as
  `FIX(12345678.9#)` and `FIX(-12345678.9#)` were added so it is proven rather
  than trusted ([spec-basic-math-pack.md](../spec-basic-math-pack.md) §9.5).
- **Empty or malformed calls returned a number** (fixed 2026-07-13 and
  2026-07-14, D-F2-3 and D-F2-4). `FIX()` printed 0, and `PRINT FIX` or
  `FIX(1,1)` quietly ran on whatever value was left over from earlier, where the
  VG-8020 says `Syntax error`:
  [spec-basic-empty-expr-syntax-error.md](../spec-basic-empty-expr-syntax-error.md),
  [spec-basic-malformed-call-syntax-error.md](../spec-basic-malformed-call-syntax-error.md).
- **A test on one sign could not tell `FIX` from `INT`** (D-KWBREADTH,
  2026-09-13). A row now reads `FIX(-2.7);FIX(2.7)`, toward zero on both
  sides, which is exactly where the two keywords part ways.
- **The whole error set was measured on the reference** (D-KWT6, 2026-09-27):
  wrong type, no argument, an extra argument and `FIX(-1E38)`; zerobas matched
  every case ([`t6enum_b2.out`](../../scratchpad/t6enum_b2.out)).

## Where it lives

`evmc_fix` in [basic/expr.asm](../../basic/expr.asm), reached from the math
selector `ev_ff_mathconv`; the work is `fp_trunc` in
[basic/float-arith.asm](../../basic/float-arith.asm), which [`INT`](INT.md)
also uses. The design notes are in
[spec-basic-math-pack.md](../spec-basic-math-pack.md) §9.

## Tests that cover it

- `make math-acceptance` — values and result types against the VG-8020,
  `FIX` against `INT` on both signs, and the empty and malformed calls.
- `make kwsweep` — the everyday rows (`FIX(-1.7)`, `FIX(-2.7);FIX(2.7)`), the
  error rows for {2, 13}, and the deliberately-broken-build check.
- `make kwram` — the RAM-usage comparison.
