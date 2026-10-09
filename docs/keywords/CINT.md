<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `CINT` — convert a number to an integer

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. No known divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`CINT(x)` turns a number into an integer, the 16-bit type that `A%` holds,
range −32768 to 32767. On MSX it **truncates toward zero**: it drops the
fraction and does not round. zerobas behaves exactly like the Philips VG-8020
for every case we have measured, errors included.

## Syntax

```
CINT(<numeric expression>)
```

One argument, always.

## Details

- **The fraction is dropped, toward zero.** `CINT(2.9)` is 2, `CINT(-2.9)` is
  −2, `CINT(3.7)` is 3. For a positive number that is the same answer as
  [`FIX`](FIX.md) and [`INT`](INT.md); for a negative one with a fraction,
  `INT` goes down (`INT(-2.5)` is −3) where `CINT` and `FIX` go toward zero
  (`CINT(-2.5)` is −2).
- **The range check looks at what is left after truncating.**
  `CINT(32767.6)` is 32767 and `CINT(-32768.6)` is −32768, both legal; only
  when the integer part itself is outside −32768 to 32767 (`CINT(32768)`,
  `CINT(-32769)`, `CINT(40000.5)`) is it `Overflow`.
- **The result is an integer**, so it prints without a fraction and stores
  into `A%` unchanged: `A%=CINT(3.7)` makes `A%` 3.
- **A string argument** is `Type mismatch`.
- **No argument, two arguments, no parentheses or a missing `)`** —
  `CINT()`, `CINT(1,1)`, `PRINT CINT`, `CINT(2` — are all `Syntax error`.

| you write | you get |
|---|---|
| `CINT(2.9)`, `CINT(2.5)` | 2 |
| `CINT(-2.9)` | −2 |
| `CINT(32767.6)` | 32767 |
| `CINT(-32768.6)` | −32768 |
| `CINT(32768)`, `CINT(-32769)` | error 6, `Overflow` |
| `CINT("A")` | error 13, `Type mismatch` |
| `CINT()`, `CINT(1,1)` | error 2, `Syntax error` |

The whole set of errors `CINT` can raise is {2, 6, 13}, the same on both
machines.

## Example

```
10 ON ERROR GOTO 80
20 PRINT CINT(2.9);CINT(-2.9)
30 PRINT CINT(32767.6);CINT(-32768.6)
40 A%=CINT(3.7):PRINT A%
50 PRINT CINT(32768)
60 PRINT CINT("A")
70 END
80 PRINT "Error";ERR:RESUME NEXT
RUN
 2 -2
 32767 -32768
 3
Error 6
Error 13
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_cint.out`](../../scratchpad/kwdoc_cint.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

None known.

The one rung not yet proven is **RAM usage**: `CINT` uses the same amount of
free memory on both machines, but the two write different sets of work-area
cells while doing it. Nothing a program can observe through `FRE` differs.

## What we found, and how

- **`CINT` does not round, and our own design said it did** (corrected
  2026-07-12, when `CINT` first shipped with the math pack). The design text,
  written from general BASIC knowledge, said "rounds half-up". Measuring the
  VG-8020 showed `CINT(2.9)` is 2 and `CINT(32767.6)` is 32767 — plain
  truncation — so `CINT` became the same strict integer conversion the `\`
  and `MOD` operators already used. The correction is recorded in
  [spec-basic-math-pack.md](../spec-basic-math-pack.md) §9.
- **`CINT()` printed 0** (fixed 2026-07-13, D-F2-3). An empty argument was
  read as zero; the reference says `Syntax error`
  ([spec-basic-empty-expr-syntax-error.md](../spec-basic-empty-expr-syntax-error.md)).
- **A malformed call gave the wrong error** (fixed 2026-07-14, D-F2-4).
  `PRINT CINT`, `CINT(1,2)` and `CINT(2` ran the conversion on a leftover
  value and could answer `Overflow` or a number, where the reference says
  `Syntax error`. The fix covered all fifteen math functions at once
  ([spec-basic-malformed-call-syntax-error.md](../spec-basic-malformed-call-syntax-error.md)).
- **The complete error set was measured** on 2026-09-27, every way of getting
  the argument wrong in turn: {2, 6, 13}, identical on both machines
  ([`t6enum_b2.out`](../../scratchpad/t6enum_b2.out)).

### Related, but not about `CINT`

`CINT(-32768)` is the easiest way to get the integer −32768, and negating it
exposed two arithmetic faults: `-CINT(-32768)` printed −32768 where the
reference prints 32768, and `0-CINT(-32768)` had the opposite problem. Both
were in the minus operators and were fixed on 2026-08-11 (D-NEG8K,
[fixpoint8000-msx1-sweep.md](../fixpoint8000-msx1-sweep.md)).

## Where it lives

`evmc_cint` in [basic/expr.asm](../../basic/expr.asm); the conversion itself
is `fac_to_int_strict_reset` in
[basic/float-arith.asm](../../basic/float-arith.asm), shared with `\`, `MOD`
and the logical operators.

## Related concepts

- [Numbers](../concepts/numbers.md) — integers, single and double precision

## Tests that cover it

- `make math-acceptance` — truncation in both directions, the range edges,
  `Overflow`, storing into `A%`, and the malformed-call forms.
- `make kwsweep` — the everyday row (`CINT(1.7)`) and the error rows for
  {2, 6, 13}.
- `make kwram` — the RAM-usage comparison.
