<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `COS` — the cosine of an angle

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. Two recorded
> differences, both deliberate: the last printed digits, and meaningless huge
> angles (below).
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`COS(x)` returns the cosine of the angle `x`, given in **radians**. The answer
lies between −1 and 1 and has 14 significant digits. It shares its calculation
with [`SIN`](SIN.md) and [`TAN`](TAN.md), and the `SIN` page has the longer
story. zerobas raises the same errors as the Philips VG-8020 in every case we
have measured; the last digits of a result can differ, because zerobas's
cosine is the more accurate one.

## Syntax

```
COS(<numeric expression>)
```

One argument, always.

## Details

- **`COS(0)` is exactly 1**, on both machines.
- **Every number is a legal angle.** There is no domain error and no overflow:
  `COS(1E38)` answers without an error on both machines.
- **A string argument** (`COS("A")`) is `Type mismatch` (error 13).
- **No argument, two arguments, no parentheses or a missing `)`** —
  `COS()`, `COS(1,1)`, `PRINT COS`, `COS(1` — are all `Syntax error`
  (error 2).

| you write | you get |
|---|---|
| `COS(0)` | 1 |
| `COS(1E38)` | no error |
| `COS("A")` | error 13, `Type mismatch` |
| `COS()`, `COS(1,1)` | error 2, `Syntax error` |

The whole set of errors `COS` can raise is {2, 13}, the same on both machines.

## Example

```
10 PRINT COS(0);INT(COS(1)*1000)
20 ON ERROR GOTO 50
30 PRINT COS("A")
40 END
50 PRINT "Error";ERR:RESUME NEXT
RUN
 1  540
Error 13
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_cos.out`](../../scratchpad/kwdoc_cos.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

**1. The last digits can differ, and zerobas is closer to the true value.**
The VG-8020's cosine behaves as if it were the sine of `π/2 − x`, and near
`π/2`, where the cosine itself is close to 0, that costs it most of its
digits: at `COS(1.5707)` its answer is wrong from roughly the 10th significant
digit. zerobas reduces the angle with more digits and stays within about
1E-14 of the true value, near `π/2` included. The approach — be accurate and record the difference rather
than imitate digits that can only be recovered from the reference's ROM — was
signed off by Joost on 2026-07-13; details on the [`SIN`](SIN.md) page.

**2. Huge angles.** From about 1E13 on, an angle held in 14 digits no longer
says which turn of the circle it is in, so no answer means anything. The
VG-8020 was measured returning 0 for `COS` from about 1E14. zerobas returns a
value between −1 and 1 up to about 1.57E14, and exactly 1 beyond that.

The one rung not yet proven is **RAM usage**: `COS` uses the same amount of
free memory on both machines, but the two write different work-area cells
along the way — the VG-8020 a few that zerobas does not, and zerobas some
scratch cells of its own for the calculation.

## What we found, and how

- **`COS` arrived with `SIN` and `TAN` on 2026-07-14**, built on one shared
  calculation; a review the same day added the rows that pin the huge-angle
  answers ([spec-basic-mathpack-slice2.md](../spec-basic-mathpack-slice2.md)
  §14).
- **Malformed calls returned a value** (fixed 2026-07-14, D-F2-4):
  `PRINT COS`, `COS(1,2)` and `COS(1` now give `Syntax error`, as on the
  VG-8020
  ([spec-basic-malformed-call-syntax-error.md](../spec-basic-malformed-call-syntax-error.md)).
- **`COS(0)` was a fair test where `SIN(0)` was not.** A function that does
  nothing returns 0, which is the right answer for `SIN(0)` and `TAN(0)`, but
  not for `COS(0)`, which is 1. `COS` needed no extra row when the sine and
  tangent did (2026-09-14).
- **The whole error set was measured on the reference** (D-KWT6, 2026-09-27):
  wrong type, no argument, an extra argument and `COS(1E38)`; zerobas matched
  every case ([`t6enum_b2.out`](../../scratchpad/t6enum_b2.out)).

## Where it lives

- Main ROM: dispatched by `evmc_total_scan` in
  [basic/expr.asm](../../basic/expr.asm) through `evmc_total_tab` in
  [basic/islands.asm](../../basic/islands.asm).
- Sub-ROM: `fp_cos` in [sub/fp_sin.asm](../../sub/fp_sin.asm), which picks
  its answer from the shared `sincos_kernel`.

## Related concepts

- [Numbers](../concepts/numbers.md) — integers, single and double precision

## Tests that cover it

- `make math-acceptance` — about forty angles against the mathematically true
  value, the huge-angle rows, and the malformed calls.
- `make kwsweep` — the everyday row (`COS(0)`), the error rows for {2, 13},
  and the deliberately-broken-build check.
- `make kwram` — the RAM-usage comparison.
