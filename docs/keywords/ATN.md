<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `ATN` — the arctangent of a number

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. One recorded
> difference, deliberate: the last printed digit of some results (below).
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`ATN(x)` returns the angle, in **radians**, whose tangent is `x`. The answer
lies between −π/2 and π/2 and has 14 significant digits. It is the inverse of
[`TAN`](TAN.md), and `4*ATN(1)` gives π. zerobas
raises the same errors as the Philips VG-8020 in every case we have measured;
on some arguments the last digit differs by one.

## Syntax

```
ATN(<numeric expression>)
```

One argument, always.

## Details

- **`ATN(0)` is exactly 0**, on both machines.
- **Every number is a legal argument.** For very large ones the angle
  approaches π/2: `ATN(1E38)` is 1.5707963267949, without an error.
- **A string argument** (`ATN("A")`) is `Type mismatch` (error 13).
- **No argument, two arguments, no parentheses or a missing `)`** —
  `ATN()`, `ATN(1,1)`, `PRINT ATN`, `ATN(1` — are all `Syntax error`
  (error 2).

| you write | you get |
|---|---|
| `ATN(0)` | 0 |
| `INT(ATN(1)*1000)` | 785 |
| `ATN(1E38)` | 1.5707963267949 |
| `ATN("A")` | error 13, `Type mismatch` |
| `ATN()`, `ATN(1,1)` | error 2, `Syntax error` |

The whole set of errors `ATN` can raise is {2, 13}, the same on both machines.

## Example

```
10 PRINT ATN(0);INT(ATN(1)*1000)
20 PRINT INT(4*ATN(1)*1000)
30 ON ERROR GOTO 60
40 PRINT ATN("A")
50 END
60 PRINT "Error";ERR:RESUME NEXT
RUN
 0  785
 3141
Error 13
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_atn.out`](../../scratchpad/kwdoc_atn.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

**The last digit of some results differs by one, and neither side is always
right.** `ATN(1)` prints `.78539816339746` on zerobas and `.78539816339745` on
the VG-8020; the true value rounds to the latter. Measured over 26 arguments,
zerobas is one unit further from the true value on 5 of them, one or two units
closer on 5, identical on 15, and on the remaining one both are off by the
same amount in opposite directions. Unlike the reference's other transcendental
functions, its `ATN` is already close to correctly rounded, so zerobas cannot
simply be more accurate everywhere without extra-precision arithmetic it does
not have. Joost signed off on 2026-07-13 on keeping zerobas's `ATN` within 2
units of the true value — the reference's own worst case — and recording the
difference ([spec-basic-mathpack-slice2.md](../spec-basic-mathpack-slice2.md)
§11.10, [spec-basic-mathacc.md](../spec-basic-mathacc.md)).

The one rung not yet proven is **RAM usage**: `ATN` uses the same amount of
free memory on both machines, but the two write different work-area cells
along the way — the VG-8020 a few that zerobas does not, and zerobas some
scratch cells of its own for the calculation.

## What we found, and how

- **`ATN` was the first transcendental function** (2026-07-13), chosen first
  because the reference's own `ATN` is the most accurate of the group, so the
  target was known to be reachable. Building it showed the 14-digit
  calculation gathers up to 2 units of rounding error, which led to the
  sign-off above.
- **"zerobas's `ATN(1)` is one digit off; fix it" was a spot finding**
  (D-MATHACC, 2026-09-01). True of the filed argument and of eleven more, but
  widening the measurement to 26 arguments, scored against a 60-digit true
  value, showed five worse, five better, and no bias — nothing to fix. The
  test's own reference calculation also failed first: it printed a plausible
  but wrong `ATN(100)` until it was corrected.
- **The test row compares `INT(ATN(1)*1000)`, not `ATN(1)`** (2026-09-12,
  D-KWDRAIN): the raw value differs in its last digit, by the decision above,
  and a row that is always red would bury real findings under a known one.
- **Malformed calls returned a value** (fixed 2026-07-14, D-F2-4):
  `PRINT ATN`, `ATN(1,2)` and `ATN(1` now give `Syntax error`, as on the
  VG-8020
  ([spec-basic-malformed-call-syntax-error.md](../spec-basic-malformed-call-syntax-error.md)).
- **The whole error set was measured on the reference** (D-KWT6, 2026-09-27):
  wrong type, no argument, an extra argument and `ATN(1E38)`; zerobas matched
  every case ([`t6enum_b2.out`](../../scratchpad/t6enum_b2.out)).

## Where it lives

- Main ROM: dispatched by `evmc_total_scan` in
  [basic/expr.asm](../../basic/expr.asm) through `evmc_total_tab` in
  [basic/islands.asm](../../basic/islands.asm).
- Sub-ROM: `fp_atan` in [sub/fp_atan.asm](../../sub/fp_atan.asm), with this
  project's own polynomial, never the reference's.
- The design notes are in
  [spec-basic-mathpack-slice2.md](../spec-basic-mathpack-slice2.md) §11.

## Tests that cover it

- `make math-acceptance` — sixty arguments against the mathematically true
  value, each within 2 units, with the cases where zerobas and the VG-8020
  differ listed.
- `make kwsweep` — the everyday row (`INT(ATN(1)*1000)`), the error rows for
  {2, 13}, and the deliberately-broken-build check.
- `make kwram` — the RAM-usage comparison.
