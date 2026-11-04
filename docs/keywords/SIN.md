<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `SIN` — the sine of an angle

> **Status (2026-11-04):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. One recorded
> difference: the last digit or two of a result; huge angles give the
> reference's answers since D-TANBIG (below).
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`SIN(x)` returns the sine of the angle `x`, given in **radians** (a full turn
is 2π, about 6.2832). The answer lies between −1 and 1 and has 14 significant
digits. zerobas raises the same errors as the Philips VG-8020 in every case we
have measured, and reduces the angle exactly as the reference does, so large
angles give the reference's answers too; only the last digit or two of a
result can differ. [`COS`](COS.md) and [`TAN`](TAN.md) share the same
calculation and the same differences.

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

**1. The last digit or two can differ.** Both machines first turn the angle
into a number of turns, `x` times 1/2π rounded to 14 digits, and keep only
its fraction. zerobas does this the same way, so it gives the reference's
answer even where that answer is far from the true sine: `SIN(1000)` prints
`.82687954054849` on both, where the true value is `.82687954053200`. What
remains different is the final approximation of the sine itself, which can
move the last one or two digits: `SIN(1E10)` is `-.48725012572533` on the
VG-8020 and `-.48725012572534` on zerobas.

**2. Huge angles.** From 1E13 on, the number of turns has no fraction digit
left, and both machines return 0. Until 2026-11-04 zerobas was more accurate
here on purpose and returned other values; it now follows the reference
(D-TANBIG).

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
  routine, `sn_kernel`, turns a number of turns into a sine with this
  project's own polynomials, after `tn_turns` has reduced the angle the
  reference's way; `fp_sin` and `fp_cos` run it once, `fp_tan` twice.
- The design notes are in
  [spec-basic-mathpack-slice2.md](../spec-basic-mathpack-slice2.md) §14.

## Related concepts

- [Numbers](../concepts/numbers.md) — integers, single and double precision

## Tests that cover it

- `make math-acceptance` — about forty angles against the mathematically true
  value, the huge-angle rows, and the malformed calls.
- `make kwsweep` — the everyday rows (`SIN(0)`, `INT(SIN(1)*1000)`), the error
  rows for {2, 13}, and the deliberately-broken-build check.
- `make kwram` — the RAM-usage comparison.
