<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `TAN` — the tangent of an angle

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error not yet proven. Three
> recorded differences: the last printed digits and meaningless huge angles
> (both deliberate), and `TAN(1E38)`, which is an error on the VG-8020 and a
> number here (open).
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`TAN(x)` returns the tangent of the angle `x`, given in **radians**; it is
`SIN(x)/COS(x)`. The answer has 14 significant digits. It shares its
calculation with [`SIN`](SIN.md) and [`COS`](COS.md), and the `SIN` page has
the longer story. zerobas raises the same errors as the Philips VG-8020 in
every case we have measured but one, and its digits are closer to the true
value.

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
| `TAN(1E38)` | error 6, `Overflow`, on the VG-8020 — a number here (see *Differences*) |
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

**1. `TAN(1E38)` is `Overflow` on the VG-8020 and a number here** (open,
D-TANBIG, a TIER 6 item in [TODO.md](../../TODO.md)). Found on 2026-09-27 when
the reference's error set was measured. `SIN(1E38)` and `COS(1E38)` raise no
error on either machine, so it is `TAN`'s own path. The filing suspects the
reference's `SIN/COS` division overflowing after its rough reduction of the
angle; that is not measured. The next step is to find the smallest angle at
which the reference starts to raise the error. Until this is fixed, `TAN` cannot reach "every error".

**2. The last digits can differ, and zerobas is closer to the true value.**
The VG-8020 computes `SIN(x)/COS(x)` from its own sine and cosine and inherits
their error, up to 12 units in the 14th digit in ordinary use and far more
near `π/2` and for large angles. zerobas's tangent stays within a few units in
the well-behaved range. The approach — be accurate and record the difference —
was signed off by Joost on 2026-07-13; details on the [`SIN`](SIN.md) page.

**3. Huge angles.** From about 1E13 on, an angle held in 14 digits no longer
says which turn of the circle it is in. zerobas returns a meaningless finite
value up to about 1.57E14 and 0 beyond that; see [`SIN`](SIN.md) for the
VG-8020's behaviour there.

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

## Where it lives

- Main ROM: dispatched by `evmc_total_scan` in
  [basic/expr.asm](../../basic/expr.asm) through `evmc_total_tab` in
  [basic/islands.asm](../../basic/islands.asm).
- Sub-ROM: `fp_tan` in [sub/fp_sin.asm](../../sub/fp_sin.asm) divides the sine
  by the cosine from the shared `sincos_kernel`.
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
