<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `SIN` — the sine of an angle

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. Two recorded
> differences, both deliberate: the last printed digits, and meaningless huge
> angles (below).
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`SIN(x)` returns the sine of the angle `x`, given in **radians** (a full turn
is 2π, about 6.2832). The answer lies between −1 and 1 and has 14 significant
digits. zerobas raises the same errors as the Philips VG-8020 in every case we
have measured; the last digits of a result can differ, because zerobas
computes a more accurate sine than the reference does. [`COS`](COS.md) and
[`TAN`](TAN.md) share the same calculation and the same differences.

## Syntax

```
SIN(<numeric expression>)
```

One argument, always. An angle in degrees has to be converted to radians
first (multiply by π/180).

## Details

- **`SIN(0)` is exactly 0**, on both machines.
- **Every number is a legal angle.** There is no domain error and no overflow:
  `SIN(1E38)` answers without an error on both machines (but see
  *Differences* for what it answers).
- **A string argument** (`SIN("A")`) is `Type mismatch` (error 13).
- **No argument, two arguments, no parentheses or a missing `)`** —
  `SIN()`, `SIN(1,1)`, `PRINT SIN`, `SIN(1` — are all `Syntax error`
  (error 2).

| you write | you get |
|---|---|
| `SIN(0)` | 0 |
| `INT(SIN(1)*1000)` | 841 |
| `SIN(1E38)` | no error |
| `SIN("A")` | error 13, `Type mismatch` |
| `SIN()`, `SIN(1,1)` | error 2, `Syntax error` |

The whole set of errors `SIN` can raise is {2, 13}, the same on both machines.

## Example

```
10 PRINT SIN(0);INT(SIN(1)*1000)
20 ON ERROR GOTO 50
30 PRINT SIN("A")
40 END
50 PRINT "Error";ERR:RESUME NEXT
RUN
 0  841
Error 13
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_sin.out`](../../scratchpad/kwdoc_sin.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

**1. The last digits can differ, and zerobas is closer to the true value.**
The VG-8020's sine is an approximation that is up to 4 units high in the
14th digit, and it reduces large angles with a stored π of about 13
digits, so its error grows with the angle: `SIN(1000)` prints
`.82687954054849` where the true value is `.82687954053200` — wrong from the
11th digit. zerobas reduces the angle with more digits and stays within about
1 unit in the 14th digit for ordinary angles. Copying the reference's digits
would need its internal constants, which can only be read from its ROM — and
this project never does that. Be accurate and record the difference: that
approach was signed off by Joost on 2026-07-13
([spec-basic-mathpack-slice2.md](../spec-basic-mathpack-slice2.md) §2, §14).

**2. Huge angles.** From about 1E13 on, a 14-digit number cannot even say
which turn of the circle it is in, so no answer means anything. The VG-8020
returns 0 there. zerobas returns a value between −1 and 1 up to about
1.57E14, and 0 beyond that (`COS` gives 1 there, `TAN` 0).

The one rung not yet proven is **RAM usage**: `SIN` uses the same amount of
free memory on both machines, but the two write different work-area cells
along the way — the VG-8020 a few that zerobas does not, and zerobas some
scratch cells of its own for the calculation.

## What we found, and how

- **`SIN`, `COS` and `TAN` arrived together on 2026-07-14**, after the
  VG-8020 was measured from the outside: its `TAN` is exactly `SIN/COS`, its
  `COS` appears to share the sine's calculation, and its large-angle error
  grows with the angle. A review the same day found that nothing tested the huge-angle
  path; rows pinning it were added.
- **A bare `SIN` returned 0** (fixed 2026-07-14, D-F2-4). `PRINT SIN`,
  `SIN(1,2)` and `SIN(1` quietly produced a value where the VG-8020 says
  `Syntax error`
  ([spec-basic-malformed-call-syntax-error.md](../spec-basic-malformed-call-syntax-error.md)).
- **The first test row could not catch a broken `SIN`** (2026-09-14,
  D-KWTRIGVAL). It read `SIN(0)`, and 0 is also what a function that does
  nothing returns. A row reading `INT(SIN(1)*1000)` — 841 — now does the work;
  scaling to a whole number makes both machines print the same thing despite
  the last-digit difference.
- **The whole error set was measured on the reference** (D-KWT6, 2026-09-27):
  wrong type, no argument, an extra argument and `SIN(1E38)`; zerobas matched
  every case ([`t6enum_b2.out`](../../scratchpad/t6enum_b2.out)).

## Where it lives

- Main ROM: the five math functions with no error of their own (`ATN`, `SIN`,
  `COS`, `TAN`, `RND`) are dispatched by `evmc_total_scan` in
  [basic/expr.asm](../../basic/expr.asm) through the small table
  `evmc_total_tab` in [basic/islands.asm](../../basic/islands.asm).
- Sub-ROM: `fp_sin` in [sub/fp_sin.asm](../../sub/fp_sin.asm). One shared
  routine, `sincos_kernel`, reduces the angle and computes both sine and
  cosine with this project's own polynomials; `fp_sin`, `fp_cos` and `fp_tan`
  pick from its result.
- The design notes are in
  [spec-basic-mathpack-slice2.md](../spec-basic-mathpack-slice2.md) §14.

## Tests that cover it

- `make math-acceptance` — about forty angles against the mathematically true
  value, the huge-angle rows, and the malformed calls.
- `make kwsweep` — the everyday rows (`SIN(0)`, `INT(SIN(1)*1000)`), the error
  rows for {2, 13}, and the deliberately-broken-build check.
- `make kwram` — the RAM-usage comparison.
