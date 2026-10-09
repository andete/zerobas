<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `CSNG` — convert a number to single precision

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. No known divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`CSNG(x)` returns `x` as a single-precision number, the type `A!` holds: six
significant digits. A double-precision value (MSX's default type, fourteen
digits) is rounded to six. zerobas behaves exactly like the Philips VG-8020 for
every case we have measured, errors included.

## Syntax

```
CSNG(<numeric expression>)
```

One argument, always.

## Details

- **A double is rounded to six digits**, not cut: `CSNG(1.2345678#)` is
  1.23457. This is the same rounding that happens when a double is stored
  into a single variable (`A!=1.2345678#`).
- **An integer or a single argument is returned unchanged**, now typed single:
  `CSNG(5)` is 5.
- **There is no range error**: `CSNG(1E38)` raises nothing on either
  machine.
- **A string argument** is `Type mismatch`.
- **No argument, or two** (`CSNG()`, `CSNG(1,1)`) is `Syntax error`.

| you write | you get |
|---|---|
| `CSNG(1.2345678#)` | 1.23457 |
| `CSNG(5)` | 5 (single precision) |
| `CSNG(1E38)` | no error |
| `CSNG("A")` | error 13, `Type mismatch` |
| `CSNG()`, `CSNG(1,1)` | error 2, `Syntax error` |

The whole set of errors `CSNG` can raise is {2, 13}, the same on both
machines.

## Example

```
10 ON ERROR GOTO 80
20 A#=1.23456789#
30 PRINT A#;CSNG(A#)
40 PRINT 2/3
50 PRINT CSNG(2/3)
60 PRINT CSNG("A")
70 END
80 PRINT "Error";ERR:RESUME NEXT
RUN
 1.23456789  1.23457
 .66666666666667
 .666667
Error 13
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_csng.out`](../../scratchpad/kwdoc_csng.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

None known.

The one rung not yet proven is **RAM usage**: `CSNG` uses the same amount of
free memory on both machines, but the two write different sets of work-area
cells while doing it. Nothing a program can observe through `FRE` differs.

## What we found, and how

- **`CSNG` shipped on 2026-07-12** with the first slice of the math pack,
  reusing the rounding that storing into a single variable already does, so
  the two cannot disagree
  ([spec-basic-math-pack.md](../spec-basic-math-pack.md) §9).
- **`CSNG()` printed 0** (fixed 2026-07-13, D-F2-3); the reference says
  `Syntax error`
  ([spec-basic-empty-expr-syntax-error.md](../spec-basic-empty-expr-syntax-error.md)).
- **A malformed call ran on a leftover value** (fixed 2026-07-14, D-F2-4),
  for all fifteen math functions at once; the reference says `Syntax error`
  ([spec-basic-malformed-call-syntax-error.md](../spec-basic-malformed-call-syntax-error.md)).
  For `CSNG` the extra-argument form `CSNG(1,1)` is measured; the bare `CSNG`
  and the unclosed `CSNG(2` are measured on sibling functions only.
- **The complete error set was measured** on 2026-09-27: {2, 13} on both
  machines, and `CSNG(1E38)` raises nothing on either
  ([`t6enum_b2.out`](../../scratchpad/t6enum_b2.out)).

See also [`CDBL`](CDBL.md) (to double precision) and [`CINT`](CINT.md) (to an
integer).

## Where it lives

`evmc_csng` in [basic/expr.asm](../../basic/expr.asm); the rounding is
`round_single_and_pack` in [basic/float-arith.asm](../../basic/float-arith.asm),
the same routine a store into a single variable uses.

## Tests that cover it

- `make math-acceptance` — rounding of doubles, integer arguments, and the
  empty form `CSNG()`.
- `make kwsweep` — the everyday row (`CSNG(1.5)`) and the error rows for
  {2, 13}.
- `make kwram` — the RAM-usage comparison.
