<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `INT` — round a number down to a whole number

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. No known divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`INT(x)` returns the largest whole number that is not bigger than `x`: it
rounds **down**, toward minus infinity. `INT(1.7)` is 1 and `INT(-1.5)` is −2.
Its sibling [`FIX`](FIX.md) instead cuts the fraction off toward zero; the two
differ only for negative numbers with a fraction. zerobas behaves exactly like
the Philips VG-8020 for every case we have measured, errors included.

## Syntax

```
INT(<numeric expression>)
```

One argument, always.

## Details

- **It rounds down, not toward zero.** `INT(-1.5)` is −2, `INT(-0.5)` is −1,
  while `INT(1.9)` is 1 and `INT(-1)` stays −1.
- **The result keeps the argument's precision and range.** `INT` does not
  convert to an integer (`A%`), so numbers far outside −32768 to 32767 work:
  `INT(12345678.9#)` is 12345678 and `INT(-9999999.5#)` is −10000000. Use
  [`CINT`](CINT.md) when you need the 16-bit integer type.
- **No range errors.** `INT(-1E38)` is fine on both machines.
- **A space before the parenthesis is allowed**: `INT (7.9)` is 7.
- **A string argument** (`INT("A")`) is `Type mismatch` (error 13).
- **No argument, two arguments, no parentheses or a missing `)`** —
  `INT()`, `INT(1,2)`, `PRINT INT`, `INT(1` — are all `Syntax error`
  (error 2).

| you write | you get |
|---|---|
| `INT(1.7)`, `INT(1.9)` | 1 |
| `INT(-1.5)` | −2 |
| `INT(-0.5)` | −1 |
| `INT(12345678.9#)` | 12345678 |
| `INT(-1E38)` | no error |
| `INT("A")` | error 13, `Type mismatch` |
| `INT()`, `INT(1,2)` | error 2, `Syntax error` |

The whole set of errors `INT` can raise is {2, 13}, the same on both machines.

## Example

```
10 PRINT INT(1.7);INT(-1.5);INT(-0.5)
20 PRINT INT(12345678.9#)
30 PRINT INT (7.9);INT(-2.5)-FIX(-2.5)
40 ON ERROR GOTO 70
50 PRINT INT("A")
60 END
70 PRINT "Error";ERR:RESUME NEXT
RUN
 1 -2 -1
 12345678
 7 -1
Error 13
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_int.out`](../../scratchpad/kwdoc_int.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

None known.

The one rung not yet proven is **RAM usage**: `INT` uses the same amount of
free memory on both machines, but the two write different work-area cells
along the way — the VG-8020 a few that zerobas does not, and zerobas two of
its own. Nothing a program can observe through `FRE` or the documented
variables differs.

## What we found, and how

- **The tests could not see the result's precision** (found 2026-07-12, in the
  review of the first math slice). The double-precision path through `INT` was
  never exercised. zerobas turned out to be right — `INT(12345678.9#)` is
  12345678 and `INT(-9999999.5#)` is −10000000 on both machines — and those
  cases are now in the tests, so the behaviour is proven rather than trusted
  ([spec-basic-math-pack.md](../spec-basic-math-pack.md) §9.5).
- **Empty or malformed calls returned a number** (fixed 2026-07-13 and
  2026-07-14, D-F2-3 and D-F2-4). `INT()` printed 0, and `PRINT INT` or
  `INT(1,2)` quietly ran on whatever value was left over from earlier, where the
  VG-8020 says `Syntax error`:
  [spec-basic-empty-expr-syntax-error.md](../spec-basic-empty-expr-syntax-error.md),
  [spec-basic-malformed-call-syntax-error.md](../spec-basic-malformed-call-syntax-error.md).
- **The space before the parenthesis was checked** (D-NUMSPACE, 2026-09-09):
  `INT (7.9)` was already accepted, as on both references
  ([`numspace_run.out`](../../scratchpad/numspace_run.out)).
- **The whole error set was measured on the reference** (D-KWT6, 2026-09-27):
  wrong type, no argument, an extra argument and `INT(-1E38)`; zerobas matched
  every case ([`t6enum_run.out`](../../scratchpad/t6enum_run.out)).

## Where it lives

`evmc_int` in [basic/expr.asm](../../basic/expr.asm), reached from the math
selector `ev_ff_mathconv`; it truncates with `fp_trunc` in
[basic/float-arith.asm](../../basic/float-arith.asm) and subtracts 1 when a
negative number lost a fraction. [`FIX`](FIX.md) is the same code without that
last step. The design notes are in
[spec-basic-math-pack.md](../spec-basic-math-pack.md) §9.

## Tests that cover it

- `make math-acceptance` — values and result types against the VG-8020,
  `INT` against `FIX` on both signs, and the empty and malformed calls.
- `make kwsweep` — the everyday row (`INT(1.7)`), the error rows for {2, 13},
  and the deliberately-broken-build check.
- `make kwram` — the RAM-usage comparison.
