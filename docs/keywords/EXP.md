<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `EXP` — e raised to a power

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. Two recorded
> differences, both deliberate: the last printed digits, and very small
> results that the VG-8020 reports as `Overflow` (below).
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`EXP(x)` returns e (2.718…) raised to the power `x`; it is the inverse of
[`LOG`](LOG.md). The answer has 14 significant digits. zerobas raises the same
errors as the Philips VG-8020 for ordinary arguments, but its digits are
closer to the true value, and it returns 0 for a band of large negative
arguments where the VG-8020 stops with `Overflow`.

## Syntax

```
EXP(<numeric expression>)
```

One argument, always.

## Details

- **`EXP(0)` is exactly 1**, on both machines.
- **The result range is MSX's number range, about 1E-64 to 1E+63** — wider
  than many BASICs. `EXP(99)` is a normal number; the largest argument that
  still works is just over 145 (`EXP(145.062)` is 9.9913951180409E+62 on the
  reference), and from `EXP(145.063)` on it is `Overflow` (error 6).
- **Going the other way, the answer becomes 0.** `EXP(-147.3)` is still a
  tiny number; `EXP(-147.4)` and `EXP(-1000)` are 0 on both machines. In a
  band between those, zerobas and the VG-8020 part ways — see *Differences*.
- **A string argument** (`EXP("A")`) is `Type mismatch` (error 13).
- **No argument, two arguments, no parentheses or a missing `)`** —
  `EXP()`, `EXP(1,2)`, `PRINT EXP`, `EXP(1` — are all `Syntax error`
  (error 2).

| you write | you get |
|---|---|
| `EXP(0)` | 1 |
| `INT(EXP(1)*1000)` | 2718 |
| `EXP(-1000)` | 0 |
| `EXP(150)`, `EXP(1000)` | error 6, `Overflow` |
| `EXP("A")` | error 13, `Type mismatch` |
| `EXP()`, `EXP(1,2)` | error 2, `Syntax error` |

The set of errors `EXP` raises for the measured cases is {2, 6, 13}, the same
on both machines.

## Example

```
10 PRINT EXP(0);INT(EXP(1)*1000)
20 PRINT EXP(-1000)
30 ON ERROR GOTO 60
40 PRINT EXP(150)
50 END
60 PRINT "Error";ERR:RESUME NEXT
RUN
 1  2718
 0
Error 6
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_exp.out`](../../scratchpad/kwdoc_exp.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

**1. The last digits differ, and zerobas is the accurate one.** zerobas's
`EXP` is within half a unit of the 14th digit on every argument measured; the
VG-8020 is 2.5 units low at `EXP(1)`, and further off for larger arguments —
74 units at `EXP(100)`, 330 at `EXP(-50)`. Matching the reference here would
mean building its error in on purpose
([spec-basic-mathacc.md](../spec-basic-mathacc.md)).

**2. Large negative arguments.** For `x` between −149.668 and −297.033 the
true answer lies between 1E-65 and 1E-129 — too small to hold — and the
VG-8020 stops with `Overflow` (error 6), while zerobas returns 0. Just outside
that band both machines return 0 (measured at −147.4 and at −1000). The
extreme arguments `EXP(-1E30)` and `EXP(-1E38)` are error 6 on the references
too, and 0 here. Returning 0 throughout is deliberate: it is the reference's
own answer just either side of its band. An attempt to copy the reference's
error (D-EXPNEG, 2026-08-31) went against that recorded decision, turned the
tests red and was reverted in full; reopening it is Joost's call
([spec-basic-mathpack-slice2.md](../spec-basic-mathpack-slice2.md) §12.9,
[spec-basic-ngram14.md](../spec-basic-ngram14.md)).

The one rung not yet proven is **RAM usage**: `EXP` uses the same amount of
free memory on both machines, but the two write different work-area cells
along the way — the VG-8020 a few that zerobas does not, and zerobas some
scratch cells of its own for the calculation.

## What we found, and how

- **The overflow point was first guessed wrong** (corrected 2026-07-13). It
  was assumed to sit near `EXP(88)`, the limit of many other BASICs; measuring
  showed MSX's own number range ends at 1E+63, so `EXP` works up to 145.06.
  The same lesson came back in the error-set measurement (D-KWT6,
  2026-09-27): `EXP(99)` was expected to overflow and did not, so
  `EXP(150)` became the overflow case.
- **"Differs in the last digit only" turned out to be a big error on the
  reference's side** (D-MATHACC, 2026-09-01). Scored against a 60-digit true
  value instead of against each other, zerobas was within half a unit on all
  ten `EXP` rows and the references were up to 330 units off. The filed
  "fix" would have been a regression.
- **The reference's `Overflow` for tiny results is a band, not everything
  below a point** (D-EXPBAND, 2026-09-05). Measured on both references to
  within 0.02 in `x`; the band's four edges are now test rows, so its extent
  is checked rather than described.
- **Empty or malformed calls gave the wrong error** (fixed 2026-07-14,
  D-F2-4): a malformed `EXP` call ran the overflow check on a left-over value
  instead of reporting `Syntax error`
  ([spec-basic-malformed-call-syntax-error.md](../spec-basic-malformed-call-syntax-error.md)).

## Where it lives

- Main ROM: `evmc_exp` in [basic/expr.asm](../../basic/expr.asm) reads the
  argument and handles the far ends itself (`evmc_exp_huge`,
  `evmc_exp_overflow`).
- Sub-ROM: `fp_exp` in [sub/fp_exp.asm](../../sub/fp_exp.asm) does the
  calculation with this project's own polynomial, never the reference's.
- The design notes are in
  [spec-basic-mathpack-slice2.md](../spec-basic-mathpack-slice2.md) §12.

## Related concepts

- [Numbers](../concepts/numbers.md) — integers, single and double precision

## Tests that cover it

- `make math-acceptance` — values against the mathematically true answer, the
  range ends, the four edges of the band, and the empty and malformed calls.
- `make kwsweep` — the everyday row (`INT(EXP(1)*1000)`), the error rows for
  {2, 6, 13}, and the deliberately-broken-build check.
- `make kwram` — the RAM-usage comparison.
