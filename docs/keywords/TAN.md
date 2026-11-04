<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `TAN` — the tangent of an angle

> **Status (2026-11-04):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. One recorded
> difference: the last digit or two of a result. `TAN(1E38)` is `Overflow` on
> both machines since D-TANBIG.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`TAN(x)` returns the tangent of the angle `x`, given in **radians**; it is
`SIN(x)/COS(x)`. The answer has 14 significant digits. It shares its
calculation with [`SIN`](SIN.md) and [`COS`](COS.md), and the `SIN` page has
the longer story. zerobas raises the same errors as the Philips VG-8020 in
every case we have measured, and reduces the angle as the reference does;
only the last digit or two of a result can differ.

## Syntax

```
TAN(<numeric expression>)
```

One argument, always.

## Details

- **`TAN(0)` is exactly 0**, on both machines.
- **Close to a right angle the answer is huge, not an error.** At `π/2`
  itself the tangent is infinite, but no 14-digit number is exactly `π/2`, so
  both machines return a very large finite value:
  `TAN(1.5707963267949)` is −15915494309189 on the VG-8020.
- **A string argument** (`TAN("A")`) is `Type mismatch` (error 13).
- **No argument, two arguments, no parentheses or a missing `)`** —
  `TAN()`, `TAN(1,1)`, `PRINT TAN`, `TAN(1` — are all `Syntax error`
  (error 2).

| you write | you get |
|---|---|
| `TAN(0)` | 0 |
| `INT(TAN(1)*1000)` | 1557 |
| `TAN(1E38)` | error 6, `Overflow` — the reduced cosine is exactly 0 |
| `TAN("A")` | error 13, `Type mismatch` |
| `TAN()`, `TAN(1,1)` | error 2, `Syntax error` |

The VG-8020's set of errors for `TAN` is {2, 6, 13}; zerobas raises 2 and 13
in the same cases, but not yet 6.

## Example

```
10 PRINT TAN(0);INT(TAN(1)*1000)
20 ON ERROR GOTO 50
30 PRINT TAN("A")
40 END
50 PRINT "Error";ERR:RESUME NEXT
RUN
 0  1557
Error 13
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_tan.out`](../../scratchpad/kwdoc_tan.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

**1. The last digit or two can differ.** `TAN` is `SIN(x)/COS(x)` on both
machines, from the same reduction (see [`SIN`](SIN.md)), so large angles give
the reference's answer. The sine and cosine approximations, and the division,
can move the last digit or two: `TAN(1000)` is `1.4703241557953` on the
VG-8020 and `1.4703241557954` on zerobas.

**2. `TAN` is `Overflow` where the cosine is exactly 0** (fixed 2026-11-04,
D-TANBIG). From `7E13` on, and for `1E38`, the reduced sine and cosine are
both 0 and the VG-8020 stops with `Overflow`. zerobas used to return a number
there and now gives the same error.

**RAM usage** is not proven yet either: `TAN` uses the same amount of free
memory on both machines, but the two write different work-area cells along
the way — the VG-8020 a few that zerobas does not, and zerobas some scratch
cells of its own for the calculation.

## What we found, and how

- **On the VG-8020, `TAN(x)` is `SIN(x)/COS(x)` to the last digit** — measured
  from the outside before zerobas's version was written (2026-07-14), which is
  why the three functions share one calculation here.
- **Malformed calls returned a value** (fixed 2026-07-14, D-F2-4):
  `PRINT TAN`, `TAN(1,2)` and `TAN(1` now give `Syntax error`, as on the
  VG-8020
  ([spec-basic-malformed-call-syntax-error.md](../spec-basic-malformed-call-syntax-error.md)).
- **The first test row could not catch a broken `TAN`** (2026-09-14,
  D-KWTRIGVAL). It read `TAN(0)`, and 0 is what a function that does nothing
  returns. A row reading `INT(TAN(1)*1000)` — 1557 — now does the work.
- **Measuring the reference's error set found `TAN(1E38)`** (D-KWT6,
  2026-09-27). Wrong type, no argument and an extra argument agreed; the huge
  angle did not ([`t6enum_b2.out`](../../scratchpad/t6enum_b2.out)).
- **The error led to the reference's whole reduction** (D-TANBIG,
  2026-11-04). Bisecting the error found it between `5E13` and `7E13`, and
  the sine and cosine quantised in steps from `1E12`. One black-box rule fits
  all 19 measured rows, `SIN(1000)` and `COS(π/2)` included
  ([`tanbig_model.py`](../../scratchpad/tanbig_model.py),
  [`tanbig_signs.out`](../../scratchpad/tanbig_signs.out)); zerobas now uses it
  ([`tanbig_after.out`](../../scratchpad/tanbig_after.out)).

## Where it lives

- Main ROM: dispatched by `evmc_total_scan` in
  [basic/expr.asm](../../basic/expr.asm) through `evmc_total_tab` in
  [basic/islands.asm](../../basic/islands.asm).
- Sub-ROM: `fp_tan` in [sub/fp_sin.asm](../../sub/fp_sin.asm) divides the sine
  by the cosine, each from its own run of the shared `sn_kernel`.
- The design notes are in
  [spec-basic-mathpack-slice2.md](../spec-basic-mathpack-slice2.md) §14.

## Related concepts

- [Numbers](../concepts/numbers.md) — integers, single and double precision

## Tests that cover it

- `make math-acceptance` — 27 angles in the well-behaved range
  against the mathematically true value, pinned values near `π/2` and for
  large angles, and the malformed calls.
- `make kwsweep` — the everyday rows (`TAN(0)`, `INT(TAN(1)*1000)`), the error
  rows for {2, 13}, and the deliberately-broken-build check.
- `make kwram` — the RAM-usage comparison.
