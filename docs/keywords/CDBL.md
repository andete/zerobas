<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `CDBL` — convert a number to double precision

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. No known divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`CDBL(x)` returns `x` as a double-precision number, the type `A#` holds:
fourteen significant digits. It widens an integer or a single-precision value;
nothing is rounded. zerobas behaves exactly like the Philips VG-8020 for every
case we have measured, errors included.

## Syntax

```
CDBL(<numeric expression>)
```

One argument, always.

## Details

- **Widening adds no digits.** A single holds six digits, and `CDBL` of it
  still holds those six: `CDBL` of a single 1/3 is .333333, not
  .33333333333333. MSX keeps numbers in decimal, so the six digits come
  across exactly, with no binary noise added.
- **What follows is calculated in double precision.** `CDBL(1)/3` gives
  fourteen digits.
- **It sidesteps the integer edge**: `-CDBL(-32768)` is 32768, where the
  integer −32768 has no positive partner.
- **There is no range error**: `CDBL(1E38)` raises nothing on either
  machine.
- **A string argument** is `Type mismatch`.
- **No argument, or two** (`CDBL()`, `CDBL(1,1)`) is `Syntax error`.

| you write | you get |
|---|---|
| `CDBL(1)/3` | .33333333333333 |
| `-CDBL(-32768)` | 32768 |
| `CDBL(1E38)` | no error |
| `CDBL("A")` | error 13, `Type mismatch` |
| `CDBL()`, `CDBL(1,1)` | error 2, `Syntax error` |

The whole set of errors `CDBL` can raise is {2, 13}, the same on both
machines.

## Example

```
10 ON ERROR GOTO 80
20 A!=1/3
30 PRINT A!;CDBL(A!)
40 PRINT CDBL(1)/3
50 PRINT -CDBL(-32768)
60 PRINT CDBL("A")
70 END
80 PRINT "Error";ERR:RESUME NEXT
RUN
 .333333  .333333
 .33333333333333
 32768
Error 13
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_cdbl.out`](../../scratchpad/kwdoc_cdbl.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

None known.

The one rung not yet proven is **RAM usage**: `CDBL` uses the same amount of
free memory on both machines, but the two write different sets of work-area
cells while doing it. Nothing a program can observe through `FRE` differs.

## What we found, and how

- **`CDBL` shipped on 2026-07-12** with the first slice of the math pack,
  reusing the float pack's existing widening rather than a routine of its
  own ([spec-basic-math-pack.md](../spec-basic-math-pack.md) §9).
- **`CDBL()` printed 0** (fixed 2026-07-13, D-F2-3); the reference says
  `Syntax error`
  ([spec-basic-empty-expr-syntax-error.md](../spec-basic-empty-expr-syntax-error.md)).
- **A malformed call ran on a leftover value** (fixed 2026-07-14, D-F2-4),
  for all fifteen math functions at once; the reference says `Syntax error`
  ([spec-basic-malformed-call-syntax-error.md](../spec-basic-malformed-call-syntax-error.md)).
  For `CDBL` the extra-argument form `CDBL(1,1)` is measured; the bare `CDBL`
  and the unclosed `CDBL(2` are measured on sibling functions only.
- **`-CDBL(-32768)` was the control** in the 2026-08-11 sweep of the
  integer −32768 (D-NEG8K): it already printed 32768 on both machines, which
  is what pinned the fault on the integer negate and not on minus in general
  ([fixpoint8000-msx1-sweep.md](../fixpoint8000-msx1-sweep.md)).
- **The complete error set was measured** on 2026-09-27: {2, 13} on both
  machines, and `CDBL(1E38)` raises nothing on either
  ([`t6enum_b2.out`](../../scratchpad/t6enum_b2.out)).

See also [`CSNG`](CSNG.md) (to single precision) and [`CINT`](CINT.md) (to an
integer).

## Where it lives

`evmc_cdbl` in [basic/expr.asm](../../basic/expr.asm): the argument is widened
and packed as a double by `round_and_finalize` in
[basic/float-arith.asm](../../basic/float-arith.asm).

## Tests that cover it

- `make math-acceptance` — single, integer and double arguments, and the
  empty form `CDBL()`.
- `make float-acceptance` — `-CDBL(-32768)`.
- `make kwsweep` — the everyday row (`CDBL(1)/3`) and the error rows for
  {2, 13}.
- `make kwram` — the RAM-usage comparison.
