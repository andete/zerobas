<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `LOG` — the natural logarithm of a number

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. One recorded
> difference, deliberate: the last printed digits of some results (below).
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`LOG(x)` returns the natural logarithm of `x` (base e), which must be greater
than 0. It is the inverse of [`EXP`](EXP.md): `LOG(1)` is 0. The answer has 14
significant digits. zerobas raises the same errors as the Philips VG-8020 in
every case we have measured; the last digits of a result can differ, because
neither machine is exact there and zerobas's own calculation is closer to the
true value.

## Syntax

```
LOG(<numeric expression>)
```

One argument, always. For a logarithm in another base, divide:
`LOG(x)/LOG(10)`.

## Details

- **`LOG(1)` is exactly 0**, on both machines.
- **Zero or a negative argument** is `Illegal function call` (error 5):
  `LOG(0)` and `LOG(-1)` both.
- **A string argument** (`LOG("A")`) is `Type mismatch` (error 13).
- **No argument, two arguments, no parentheses or a missing `)`** —
  `LOG()`, `LOG(1,2)`, `PRINT LOG`, `LOG(1` — are all `Syntax error`
  (error 2).

| you write | you get |
|---|---|
| `LOG(1)` | 0 |
| `LOG(0)`, `LOG(-1)` | error 5, `Illegal function call` |
| `LOG("A")` | error 13, `Type mismatch` |
| `LOG()`, `LOG(1,2)` | error 2, `Syntax error` |

The whole set of errors `LOG` can raise is {2, 5, 13}, the same on both
machines.

## Example

```
10 PRINT LOG(1);INT(LOG(10)*1000)
20 ON ERROR GOTO 60
30 PRINT LOG(0)
40 PRINT LOG(-1)
50 END
60 PRINT "Error";ERR:RESUME NEXT
RUN
 0  2302
Error 5
Error 5
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_log.out`](../../scratchpad/kwdoc_log.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

**The last digits of a result can differ.** The VG-8020's `LOG` has a small
downward bias, up to 5 units in the 14th digit, and missed the true value on
19 of the 35 arguments in zerobas's test set. zerobas uses its own
calculation, never the reference's, and stays within 2 units of the true value
(26 of those 35 exactly right). Reproducing the reference's digits would need
its internal constants, which can only be read from its ROM — something this
project does not do. The approach — be accurate and record the difference
rather than imitate — was signed off by Joost on 2026-07-13
([spec-basic-mathpack-slice2.md](../spec-basic-mathpack-slice2.md) §2).

The one rung not yet proven is **RAM usage**: `LOG` uses the same amount of
free memory on both machines, but the two write different work-area cells
along the way — the VG-8020 a few that zerobas does not, and zerobas some
scratch cells of its own for the calculation.

## What we found, and how

- **`LOG()` gave the wrong error** (fixed 2026-07-14, D-F2-4). Empty, bare
  (`PRINT LOG`) or two-argument calls answered `Illegal function call`: the
  domain check ran on a left-over value before anything noticed the call was
  malformed. The VG-8020 says `Syntax error`, and so does zerobas now
  ([spec-basic-malformed-call-syntax-error.md](../spec-basic-malformed-call-syntax-error.md)).
- **The format's far corners were measured** (2026-09-05, with D-EXPBAND):
  `LOG(1E-64)` and `LOG(9.9E62)`, the smallest and largest numbers MSX can
  hold, are handled the same way on both references, and are now test rows.
- **The whole error set was measured on the reference** (D-KWT6, 2026-09-27):
  wrong type, no argument, an extra argument, `LOG(0)` and `LOG(-1)`; zerobas
  matched every case ([`t6enum_run.out`](../../scratchpad/t6enum_run.out)).

## Where it lives

- Main ROM: `evmc_log` in [basic/expr.asm](../../basic/expr.asm) reads the
  argument and rejects zero and negative values before anything is computed.
- Sub-ROM: `fp_log` in [sub/fp_log.asm](../../sub/fp_log.asm) does the
  calculation, with this project's own polynomial.
- The design notes are in
  [spec-basic-mathpack-slice2.md](../spec-basic-mathpack-slice2.md) §12.

## Related concepts

- [Numbers](../concepts/numbers.md) — integers, single and double precision

## Tests that cover it

- `make math-acceptance` — values against the mathematically true answer, the
  range corners, the domain error, and the empty and malformed calls.
- `make kwsweep` — the everyday row (`LOG(1)`), the error rows for {2, 5, 13},
  and the deliberately-broken-build check.
- `make kwram` — the RAM-usage comparison.
