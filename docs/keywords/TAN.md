<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->
<!-- example: reference=VG-8020 disk=no -->

# `TAN` — the tangent of an angle

> **Spec:** DRAFT 1 (2026-11-24) — 255 cases measured on the Philips VG-8020 (BASIC's reference) and on
> zerobas, by typed BASIC ([`ktrans.py`](../../probes/basic/spec/ktrans.py)); every rule is executable and
> every recorded output is read by one. Not yet reviewed ([the keyword plan](spec-plan.md)).
>
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

- **`TAN(0)` is exactly 0**, on both machines, and the result is always double precision.
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

## The specification

Reference: the Philips VG-8020's MSX BASIC. Ours: zerobas on the diskless machine
(`C-BIOS_MSX1_EU_REPACK_NODISK`).

**How to read the rules below.** Every rule is a sentence AND a check
([`probes/basic/spec/tan_rules.py`](../../probes/basic/spec/tan_rules.py), model in
[`ktrans_model.py`](../../probes/basic/spec/ktrans_model.py), run by
[`tools/spec_rules.py`](../../tools/spec_rules.py); [docs/spec-method.md](../spec-method.md) §3a,
[the keyword plan](spec-plan.md)) over the measured cases it names.
- **reference:** ✓ means the check holds on EVERY case it selects of the VG-8020's run.
- **zerobas:** the cases where zerobas fails it, which are its differences.

The tables are generated from the checks, so a sentence here cannot say more than the data does.

**Bounds, not digits.** `TAN`'s last digits are the reference's own approximation. Where a rule says "within B
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
recorded before the call. Each case is evaluated twice: `R=TAN(N)`, with `R` a double whose 8 bytes are recorded,
and `Q=USR(TAN(N))`, where `USR` is the probe's own 18-byte routine (POKEd above `CLEAR`'s limit) that copies
`VALTYP` and `DAC` -- `TAN`'s result unconverted, by the convention [USR.md](USR.md) documents -- into the probe's
memory, so the result's TYPE and its own bytes are seen. Before every case `R` holds -12345 and the type cell 255, so
an error cannot read as a result; an apparatus row per argument (`R=N`, `Q=USR(N)`) must give back the argument's own
type and bytes on both machines, or the loader refuses the run.
- **[KTR TI TAN *n*]** (integers), **[KTR TS1 / TS2 TAN *n*]** (singles), **[KTR TD1 / TD2 TAN *n*]** (doubles),
  *n* the `DATA` text. Integers: 0, 1, -1, 2, -2, 3, -3, 4, 5, -5, 7, 10, -10, 20, -20, 50, -50, 100, -100, 145, 146, -147, -148, -149, -150, -200, -297, -298, 1000, -1000, 12345, 32767, -32768. Singles: 0, -0, 1E-64, -1E-64, 1E-20, 1E-10, -1E-10, 1E-6, -1E-6, .001, -.001, .01, .1, -.1, .2, .25, .5, -.5, .693147, .7, .75, .9, .999999, 1, -1, 1.00001, 1.5, -1.5, 2, -2, 2.5, -2.5, 2.71828, 3, 5, 10, -10, 20, -20, 50, -50, 99, 100, -100, 145.062, 145.063, -147.3, -147.4, -149.66, -149.67, -297.03, -297.04, -1000, 1000, 12345.6, 99999.9, .785398, -.785398, 1.0472, .523599, 1.5708, -1.5708, 1.57079, 3.14159, -3.14159, 3.1416, 4.71239, 6.28318, 6.28319, 7, 10.5, 100.5, 1E5, 123456, 1E6, -1E6, 1E10, 1E12, 1E13, 5E13, 7E13, 1E14, 1E20, 1E38, -1E38, 9.99999E62, -9.99999E62, 1.23456E-5, 3.33333, .333333, -.333333, 4, 8, 16, 64, .0625, 1E30, -1E30, 1E-30, 1E-63, 1.73205, .57735, -.57735, -40000, -65535, -65536, -99999, -1E5, -999999. Doubles:
  0, -0, 1D-64, -1D-64, 1D-14, -1D-14, 1D-10, 1D-7, .001, -.001, .1, -.1, .5, -.5, .69314718055995, 1.0000000000001, .99999999999999, 1, -1, 2, -2, 2.302585092994, 2.718281828459, 2.7182818284590, 10, -10, 1.2345678901234, -1.2345678901234, 12.345678901234, 50, -50, 100, -100, 145.06286, 145.0628, 145.063, -147.3, -147.4, -149.668, -149.67, -297.033, -297.04, -1000, 1000, 1D10, 1D20, 1D-20, 9.9999999999999D62, -9.9999999999999D62, 32767.9, 123456789.01234, .78539816339745, -.78539816339745, .78539816339744, 1.0471975511966, .5235987755983, 1.5707963267949, -1.5707963267949, 1.5707963267948, 3.1415926535898, -3.1415926535898, 3.1415926535897, 4.7123889803847, 6.2831853071796, -6.2831853071796, 12.566370614359, 1000, -1000, 1D10, -1D10, 1D11, 1D12, 1D13, 7D13, 1D14, 1D38, 1.7320508075689, .57735026918963, -.57735026918963, 1D-5, -1D-5, .12345678901234, -.12345678901234, 1234.5678901234, 31415.926535898, 100, 3.3333333333333, 1D30, -1D30, 1D-30.
- **[KTR FX *i*]**: a fixed statement, `S$` = `"12"`; the list, with what each one separates, is `FX` in the probe:
  a string literal or variable as the argument, the result assigned to `R$`, `1/0`, no argument, an extra one, no
  `)`, no parenthesis; the literals `2.5`, `-2.5`, `7`, `7%`, `2.5!`, `2.5#`, `&H8000`, `-32768`, `-0`, `1/4`;
  spaces; `TAN(TAN(.5))`; and a single `N!` assigned 1 whose exponent byte is then POKEd to 0 or `&H80`
  (digit bytes `10 00 00`).

**Controls** ([`ktrans_controls.py`](../../probes/basic/spec/ktrans_controls.py)): each is a rival rule run over the reference's cases: “within 3 units of the reduced quotient” is FALSE on 7 of the 210 cases it selects (e.g. KTR TI TAN -297); “the own SIN / COS correctly rounded -- zerobas's rule” is FALSE on 84 of the 199 cases it selects (e.g. KTR TI TAN 1); “within 6 units of the TRUE tan(x)” is FALSE on 135 of the 210 cases it selects (e.g. KTR TI TAN 3); “the zero 8 zero bytes -- zerobas's” is FALSE on 19 of the 19 cases it selects (e.g. KTR TI TAN 0).

<!-- RULES BEGIN -->
<!-- GENERATED by tools/spec_rules.py from probes/basic/spec/tan_rules.py -- do not edit; `python3 tools/spec_rules.py probes/basic/spec/tan_rules.py --write` -->

**12 rules; 12 hold on the reference. Of the 1275 recorded outputs (each case's error from `R=F(x)` and from `Q=USR(F(x))`, R's 8 bytes, the result's type as USR saw it and the result's own bytes): 1275 read by a rule's check, 0 declared NOT evidence (below), 0 unread.**

#### 1. TAN(x)

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-TAN-POLE** When COS's reduced angle is a whole or a half turn (COS(x) is the 2-pi-digit zero, COS's page) TAN is error 6 (Overflow): every x from 7E13 up (1E14, 1E20, 1E38, 9.99999E62, the negatives too). | 17 | ✓ | ✓ |
| **R-TAN-ZERO** Otherwise, when SIN's is (SIN(x) the 2-pi-digit zero), TAN is that zero too: 00 62 83 18 53 07 17 96 -- TAN(0), TAN(1E-64), TAN(3.1415926535897#), TAN(1E13), TAN(5E13). | 19 | ✓ | ✗ 19: KTR TI TAN 0, KTR TS1 TAN 0, KTR TS1 TAN -0, KTR TS1 TAN 1E-64, KTR TS1 TAN -1E-64, KTR TS2 TAN 1E13 … (+13) |
| **R-TAN-NEAR** Otherwise a DOUBLE within 6 units of the 14th significant digit of sin(2 pi f) / sin(2 pi g) -- the reduced angles of SIN and COS (their pages): TAN(1.5707963267949#) is -15915494309189 (g is -1E-14 turns), TAN(1) 1.5574077246549. Measured worst 5.2 units. | 210 | ✓ | ✗ 11: KTR TS2 TAN 3.14159, KTR TS2 TAN -3.14159, KTR TS2 TAN 3.1416, KTR TS2 TAN 4.71239, KTR TS2 TAN 6.28318, KTR TD1 TAN 2.718281828459 … (+5) |
| **R-TAN-OWN** And within 3 units of SIN(x) / COS(x) as the same machine computes them (the case's SIN and COS rows): the quotient of the two, not always rounded correctly (measured worst 2.8, TAN(12345%)). | 199 | ✓ | ✓ |
| **R-TAN-ODD** TAN(-x) is TAN(x) with the sign bit flipped (a zero the same bytes, an error the same error). | 57 | ✓ | ✓ |
| **R-TAN-ODDBYTES** On a non-canonical single (exponent byte 0 or &H80, digit bytes 10 00 00) it gives what the rules above say for a zero argument. | 2 | ✓ | ✗ 2: KTR FX 113, KTR FX 114 |
| **R-TAN-NESTED** TAN(TAN(.5)) is TAN of the double that TAN(.5) returns (the KTR TS1 row): what the rules above say for that double. | 1 | ✓ | ✓ |

#### 2. TAN(x): forms, errors and assignment

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-TAN-TYPE** A string as the argument (a literal or a variable) is error 13 (Type mismatch), and so is assigning the result to a string variable: the result is a number. | 3 | ✓ | ✓ |
| **R-TAN-OWNERR** An argument that fails to compute raises its own error (1/0: error 11). | 1 | ✓ | ✓ |
| **R-TAN-SYNTAX** No argument, a second argument, no closing parenthesis, or the name without a parenthesis is error 2 (Syntax error). | 4 | ✓ | ✓ |
| **R-TAN-FORMS** Spaces before the parenthesis and around the argument are allowed, and a literal's own type is the argument's (2.5 a single, 7 an integer, &H8000 the integer -32768, -32768 a single, -0 the integer 0, 1/4 a double); each gives what the rules above say for that value. | 12 | ✓ | ✗ 1: KTR FX 110 |
| **R-TAN-ASSIGN** `R=TAN(x)` with R a double stores the result's 8 bytes as they are (a zero's digit bytes included), and an error stores nothing (R keeps its sentinel). Read in every case. | 255 | ✓ | ✓ |

<!-- RULES END -->

## Differences from the reference

- **Near a half or a whole turn zerobas keeps more of the angle** ([D-TRIGHALF](../../todo/open/D-TRIGHALF.md),
  TIER 1). The rule R-TAN-NEAR's target is the sine of the reference's 14-digit reduced angle; where that angle is
  close to a half or whole turn the result is small and its LEADING digits are the reduction's last ones:
  SIN(3.1415926535898#) is -1.2566370614359E-13 on the VG-8020 and -1.5707963267949E-13 here, SIN(3.14159!)
  2.6535897144938E-06 there and 2.6535897459098E-06 here, COS(4.7123889803847#) 1.2566370614359E-13 there and
  1.5707963267949E-13 here, TAN(4.7123889803847#) -7957747154594.6 there and -6366197723675.8 here.
- **The last digit elsewhere** ([D-SINDIGITS](../../todo/open/D-SINDIGITS.md)). Inside the bound zerobas's digits may
  differ and do (`SIN(1E10)` is -.48725012572533 there, -.48725012572534 here); outside it, zerobas's sine is up to 6.1
  units off the reduced target where the reference's worst is 1.9 (SIN(2.718281828459#) .41078129050281 here,
  .41078129050287 there), and TAN inherits it (6.4 units, TAN(3.3333333333333#)).
- **The zeros' bytes** (invisible to PRINT; [D-TRANSZERO](../../todo/open/D-TRANSZERO.md)): the reference's zero
  result carries 2 pi's digits, 00 62 83 18 53 07 17 96; zerobas's other bytes (rule R-TAN-ZERO).
- **The quotient's rounding.** zerobas divides its sine by its cosine correctly rounded; the VG-8020's quotient is
  within 2.8 units of its own SIN(x) / COS(x), not always the rounded one (R-TAN-OWN holds on both; a control shows
  "correctly rounded" is false on 84 of the reference's cases). `TAN(1000)` is 1.4703241557953 there and
  1.4703241557954 here.

The one rung not yet proven is **RAM usage**: `TAN` uses the same amount of free memory on both machines, but the two write different work-area cells along the way — the VG-8020 a few that zerobas does not, and zerobas some scratch cells of its own for the calculation.

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

- **The transcendentals' rules are bounds, measured** (2026-11-24, D-KWSPEC's maths region, second unit). TAN is a double always; error 6 exactly where COS's reduced angle is a whole or half turn (7E13 up), the 2-pi-digit zero where SIN's is; within 5.2 units of the reduced quotient and 2.8 of the machine's own SIN/COS. TAN is odd, byte for byte.
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
