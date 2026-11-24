<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->
<!-- example: reference=VG-8020 disk=no -->

# `COS` — the cosine of an angle

> **Spec:** DRAFT 1 (2026-11-24) — 255 cases measured on the Philips VG-8020 (BASIC's reference) and on
> zerobas, by typed BASIC ([`ktrans.py`](../../probes/basic/spec/ktrans.py)); every rule is executable and
> every recorded output is read by one. Not yet reviewed ([the keyword plan](spec-plan.md)).
>
> **Status (2026-11-04):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. One recorded
> difference: the last digit or two of a result; huge angles give the
> reference's answers since D-TANBIG (below).
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`COS(x)` returns the cosine of the angle `x`, given in **radians**. The answer
lies between −1 and 1 and has 14 significant digits. It shares its calculation
with [`SIN`](SIN.md) and [`TAN`](TAN.md), and the `SIN` page has the longer
story. zerobas raises the same errors as the Philips VG-8020 in every case we
have measured, and reduces the angle as the reference does; only the last
digit or two of a result can differ.

## Syntax

```
COS(<numeric expression>)
```

One argument, always.

## Details

- **`COS(0)` is exactly 1**, on both machines, and the result is always double precision.
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

## The specification

Reference: the Philips VG-8020's MSX BASIC. Ours: zerobas on the diskless machine
(`C-BIOS_MSX1_EU_REPACK_NODISK`).

**How to read the rules below.** Every rule is a sentence AND a check
([`probes/basic/spec/cos_rules.py`](../../probes/basic/spec/cos_rules.py), model in
[`ktrans_model.py`](../../probes/basic/spec/ktrans_model.py), run by
[`tools/spec_rules.py`](../../tools/spec_rules.py); [docs/spec-method.md](../spec-method.md) §3a,
[the keyword plan](spec-plan.md)) over the measured cases it names.
- **reference:** ✓ means the check holds on EVERY case it selects of the VG-8020's run.
- **zerobas:** the cases where zerobas fails it, which are its differences.

The tables are generated from the checks, so a sentence here cannot say more than the data does.

**Bounds, not digits.** `COS`'s last digits are the reference's own approximation. Where a rule says "within B
units", the target is computed exactly (to 60 digits and more, in Python, from the argument's own bytes) and a unit is
one in the 14th significant digit of the target; B is the worst error MEASURED on the VG-8020, rounded up (the measured
worst is in the sentence), and a control shows that a tighter bound is false. Whether zerobas's digits equal the
reference's byte for byte is a separate observation, under *Differences*: a zerobas result inside the bound agrees
with the rule even where its digits differ.

**Evidence.** One probe, [`probes/basic/spec/ktrans.py`](../../probes/basic/spec/ktrans.py) (the maths region's
second, on the shared RAM-record harness [`ramrec.py`](../../probes/basic/spec/ramrec.py) and the frame of
[`kmath.py`](../../probes/basic/spec/kmath.py)), typed on both machines; run file
[`scratchpad/KTR_run1.out`](../../scratchpad/KTR_run1.out) (2026-11-24; zerobas's side on that day's build). The
argument is `READ` into a variable of the case's own type (`N%`, `N!` or `N#`) and that variable's own bytes are
recorded before the call. Each case is evaluated twice: `R=COS(N)`, with `R` a double whose 8 bytes are recorded,
and `Q=USR(COS(N))`, where `USR` is the probe's own 18-byte routine (POKEd above `CLEAR`'s limit) that copies
`VALTYP` and `DAC` -- `COS`'s result unconverted, by the convention [USR.md](USR.md) documents -- into the probe's
memory, so the result's TYPE and its own bytes are seen. Before every case `R` holds -12345 and the type cell 255, so
an error cannot read as a result; an apparatus row per argument (`R=N`, `Q=USR(N)`) must give back the argument's own
type and bytes on both machines, or the loader refuses the run.
- **[KTR TI COS *n*]** (integers), **[KTR TS1 / TS2 COS *n*]** (singles), **[KTR TD1 / TD2 COS *n*]** (doubles),
  *n* the `DATA` text. Integers: 0, 1, -1, 2, -2, 3, -3, 4, 5, -5, 7, 10, -10, 20, -20, 50, -50, 100, -100, 145, 146, -147, -148, -149, -150, -200, -297, -298, 1000, -1000, 12345, 32767, -32768. Singles: 0, -0, 1E-64, -1E-64, 1E-20, 1E-10, -1E-10, 1E-6, -1E-6, .001, -.001, .01, .1, -.1, .2, .25, .5, -.5, .693147, .7, .75, .9, .999999, 1, -1, 1.00001, 1.5, -1.5, 2, -2, 2.5, -2.5, 2.71828, 3, 5, 10, -10, 20, -20, 50, -50, 99, 100, -100, 145.062, 145.063, -147.3, -147.4, -149.66, -149.67, -297.03, -297.04, -1000, 1000, 12345.6, 99999.9, .785398, -.785398, 1.0472, .523599, 1.5708, -1.5708, 1.57079, 3.14159, -3.14159, 3.1416, 4.71239, 6.28318, 6.28319, 7, 10.5, 100.5, 1E5, 123456, 1E6, -1E6, 1E10, 1E12, 1E13, 5E13, 7E13, 1E14, 1E20, 1E38, -1E38, 9.99999E62, -9.99999E62, 1.23456E-5, 3.33333, .333333, -.333333, 4, 8, 16, 64, .0625, 1E30, -1E30, 1E-30, 1E-63, 1.73205, .57735, -.57735, -40000, -65535, -65536, -99999, -1E5, -999999. Doubles:
  0, -0, 1D-64, -1D-64, 1D-14, -1D-14, 1D-10, 1D-7, .001, -.001, .1, -.1, .5, -.5, .69314718055995, 1.0000000000001, .99999999999999, 1, -1, 2, -2, 2.302585092994, 2.718281828459, 2.7182818284590, 10, -10, 1.2345678901234, -1.2345678901234, 12.345678901234, 50, -50, 100, -100, 145.06286, 145.0628, 145.063, -147.3, -147.4, -149.668, -149.67, -297.033, -297.04, -1000, 1000, 1D10, 1D20, 1D-20, 9.9999999999999D62, -9.9999999999999D62, 32767.9, 123456789.01234, .78539816339745, -.78539816339745, .78539816339744, 1.0471975511966, .5235987755983, 1.5707963267949, -1.5707963267949, 1.5707963267948, 3.1415926535898, -3.1415926535898, 3.1415926535897, 4.7123889803847, 6.2831853071796, -6.2831853071796, 12.566370614359, 1000, -1000, 1D10, -1D10, 1D11, 1D12, 1D13, 7D13, 1D14, 1D38, 1.7320508075689, .57735026918963, -.57735026918963, 1D-5, -1D-5, .12345678901234, -.12345678901234, 1234.5678901234, 31415.926535898, 100, 3.3333333333333, 1D30, -1D30, 1D-30.
- **[KTR FX *i*]**: a fixed statement, `S$` = `"12"`; the list, with what each one separates, is `FX` in the probe:
  a string literal or variable as the argument, the result assigned to `R$`, `1/0`, no argument, an extra one, no
  `)`, no parenthesis; the literals `2.5`, `-2.5`, `7`, `7%`, `2.5!`, `2.5#`, `&H8000`, `-32768`, `-0`, `1/4`;
  spaces; `COS(COS(.5))`; and a single `N!` assigned 1 whose exponent byte is then POKEd to 0 or `&H80`
  (digit bytes `10 00 00`).

**Controls** ([`ktrans_controls.py`](../../probes/basic/spec/ktrans_controls.py)): each is a rival rule run over the reference's cases: “within 2.5 units of the TRUE cos(x)” is FALSE on 146 of the 221 cases it selects (e.g. KTR TI COS 1); “1/4 minus the FRACTION of p” is FALSE on 20 of the 232 cases it selects (e.g. KTR TS2 COS 1E13); “p + 1/4 in place of 1/4 - p” is FALSE on 2 of the 221 cases it selects (e.g. KTR TS2 COS 4.71239); “within 2 units of the reduced target” is FALSE on 2 of the 221 cases it selects (e.g. KTR TS1 COS .25).

<!-- RULES BEGIN -->
<!-- GENERATED by tools/spec_rules.py from probes/basic/spec/cos_rules.py -- do not edit; `python3 tools/spec_rules.py probes/basic/spec/cos_rules.py --write` -->

**11 rules; 11 hold on the reference. Of the 1275 recorded outputs (each case's error from `R=F(x)` and from `Q=USR(F(x))`, R's 8 bytes, the result's type as USR saw it and the result's own bytes): 1275 read by a rule's check, 0 declared NOT evidence (below), 0 unread.**

#### 1. COS(x)

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-COS-ONE** COS of zero is exactly the double 1 (41 10 00 00 00 00 00 00), whatever the zero's digit or sign bytes. | 8 | ✓ | ✓ |
| **R-COS-ZERO** The result is a DOUBLE. When the reduced angle is a whole or a half turn (g = frac(r14(1/4 - p)), p = x * 0.15915494309190 rounded to 14 significant digits; a whole turn when p is 0 or whole) it is a zero whose digit bytes are 2 pi's: 00 62 83 18 53 07 17 96 -- COS(x) from x = 7E13 up, where 1/4 - p rounds to a whole number. | 17 | ✓ | ✗ 17: KTR TS2 COS 7E13, KTR TS2 COS 1E14, KTR TS2 COS 1E20, KTR TS2 COS 1E38, KTR TS2 COS -1E38, KTR TS2 COS 9.99999E62 … (+11) |
| **R-COS-NEAR** Otherwise a double within 2.5 units of the 14th significant digit of sin(2 pi g) -- the sine of the REDUCED angle, not cos(x): COS(1.5707963267949#) is -6.2831853071796E-14 (g = -1E-14), COS(4.71239!) 1.0196154567834E-06, COS(1E13) .95105651629516 (1/4 - p rounds to -1591549430918.8, g = -.8). Measured worst 2.1 units. | 221 | ✓ | ✗ 2: KTR TS2 COS 4.71239, KTR TD2 COS 4.7123889803847 |
| **R-COS-EVEN** COS(-x) is COS(x), byte for byte (every x measured with its negation). | 57 | ✓ | ✓ |
| **R-COS-ODDBYTES** On a non-canonical single (exponent byte 0 or &H80, digit bytes 10 00 00) it gives what the rules above say for a zero argument. | 2 | ✓ | ✓ |
| **R-COS-NESTED** COS(COS(.5)) is COS of the double that COS(.5) returns (the KTR TS1 row): what the rules above say for that double. | 1 | ✓ | ✓ |

#### 2. COS(x): forms, errors and assignment

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-COS-TYPE** A string as the argument (a literal or a variable) is error 13 (Type mismatch), and so is assigning the result to a string variable: the result is a number. | 3 | ✓ | ✓ |
| **R-COS-OWNERR** An argument that fails to compute raises its own error (1/0: error 11). | 1 | ✓ | ✓ |
| **R-COS-SYNTAX** No argument, a second argument, no closing parenthesis, or the name without a parenthesis is error 2 (Syntax error). | 4 | ✓ | ✓ |
| **R-COS-FORMS** Spaces before the parenthesis and around the argument are allowed, and a literal's own type is the argument's (2.5 a single, 7 an integer, &H8000 the integer -32768, -32768 a single, -0 the integer 0, 1/4 a double); each gives what the rules above say for that value. | 12 | ✓ | ✓ |
| **R-COS-ASSIGN** `R=COS(x)` with R a double stores the result's 8 bytes as they are (a zero's digit bytes included), and an error stores nothing (R keeps its sentinel). Read in every case. | 255 | ✓ | ✓ |

<!-- RULES END -->

## Differences from the reference

- **Near a half or a whole turn zerobas keeps more of the angle** ([D-TRIGHALF](../../todo/open/D-TRIGHALF.md),
  TIER 1). The rule R-COS-NEAR's target is the sine of the reference's 14-digit reduced angle; where that angle is
  close to a half or whole turn the result is small and its LEADING digits are the reduction's last ones:
  SIN(3.1415926535898#) is -1.2566370614359E-13 on the VG-8020 and -1.5707963267949E-13 here, SIN(3.14159!)
  2.6535897144938E-06 there and 2.6535897459098E-06 here, COS(4.7123889803847#) 1.2566370614359E-13 there and
  1.5707963267949E-13 here, TAN(4.7123889803847#) -7957747154594.6 there and -6366197723675.8 here.
- **The last digit elsewhere, within the bound.** zerobas's digits may differ and do (`COS(1E10)` is .87326245480993
  there, .87326245480992 here, by Joost's 2026-07-13 ruling: zerobas's own approximation, never the reference's);
  zerobas's COS stays within 1.3 units of the reduced target away from the folds, so only the fold above is outside
  R-COS-NEAR.
- **The zeros' bytes** (invisible to PRINT; [D-TRANSZERO](../../todo/open/D-TRANSZERO.md)): the reference's zero
  result carries 2 pi's digits, 00 62 83 18 53 07 17 96; zerobas's other bytes (rule R-COS-ZERO).

The one rung not yet proven is **RAM usage**: `COS` uses the same amount of free memory on both machines, but the two write different work-area cells along the way — the VG-8020 a few that zerobas does not, and zerobas some scratch cells of its own for the calculation.

## On later generations (MSX2, MSX2+)

[A] Not measured yet: the probe has not run on the MSX2 / MSX2+ references (spec-method §4).

## Open (not measured)

- [A] Direct mode: every case ran inside a program.
- [A] An argument's own error was measured with one kind (`1/0`, error 11); that any error of the argument wins is assumed.
- [A] Which work-area cells the call writes (the RAM-usage rung).
- [A] Non-canonical bytes other than the two measured singles (exponent byte 0 or `&H80` with digit bytes `10 00 00`).
- [A] The reduction is a black-box model fitted to the measured results (431 nonzero SIN / COS values within 2.1
  units); its intermediate rounding is not observed directly, so a case where a different rounding of p or of
  1/4 - p decides the result may still separate it from the reference.
- [A] Whether the reference's error against the reduced target is ever more than the bound: the bound is the measured
  worst rounded up.

## What we found, and how

- **The transcendentals' rules are bounds, measured** (2026-11-24, D-KWSPEC's maths region, second unit). COS is a double always, COS(0) exactly 1. It is the sine of a quarter turn MINUS the angle's turns, rounded to 14 digits before the fraction is taken: g = frac(r14(1/4 - p)) -- the two rivals, the fraction of p taken first and p + 1/4, are each false on measured cases (1E13; 4.71239). COS is even, byte for byte.
- **Near π/2 the two machines give different small numbers, as ruled**
  (measured 2026-10-29, D-COSHALFPI). `COS(4*ATN(1#)/2)` is
  `-6.2831853071796E-14` on the VG-8020 and `-3.3808E-15` here. The angle in
  14 digits is 3.4E-15 past π/2, so the true cosine is -3.38076868E-15; the
  VG-8020's answers near the zeros of `SIN`, `COS` and `TAN` come in whole
  steps of 2π·1E-14 instead ([readings](../../scratchpad/coshalfpi_measure.out)).
  Found by a table-printing program written for the program ladder.
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
  its answer from the shared `sn_kernel`.

## Related concepts

- [Numbers](../concepts/numbers.md) — integers, single and double precision

## Tests that cover it

- `make math-acceptance` — about forty angles against the mathematically true
  value, the huge-angle rows, and the malformed calls.
- `make kwsweep` — the everyday row (`COS(0)`), the error rows for {2, 13},
  and the deliberately-broken-build check.
- `make kwram` — the RAM-usage comparison.
