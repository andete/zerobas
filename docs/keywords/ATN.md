<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->
<!-- example: reference=VG-8020 disk=no -->

# `ATN` — the arctangent of a number

> **Spec:** DRAFT 1 (2026-11-24) — 329 cases measured on the Philips VG-8020 (BASIC's reference) and on
> zerobas, by typed BASIC ([`ktrans.py`](../../probes/basic/spec/ktrans.py)); every rule is executable and
> every recorded output is read by one. Not yet reviewed ([the keyword plan](spec-plan.md)).
> Goldfish pass 1 (test writer) 2026-11-24: 6 findings, 5 measured, 1 moved to open (new cases: KTR TS3, TD3, FY).
>
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
on some arguments the last digit differs by one. One odd input differs
visibly: `PRINT ATN(x)` of a single whose bytes were POKEd to a signed zero
(`80 ...`) prints 0 there and `-.` here.

## Syntax

```
ATN(<numeric expression>)
```

One argument, always.

## Details

- **`ATN(0)` is exactly 0**, on both machines, and the result is always double precision.
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

## The specification

Reference: the Philips VG-8020's MSX BASIC. Ours: zerobas on the diskless machine
(`C-BIOS_MSX1_EU_REPACK_NODISK`).

**How to read the rules below.** Every rule is a sentence AND a check
([`probes/basic/spec/atn_rules.py`](../../probes/basic/spec/atn_rules.py), model in
[`ktrans_model.py`](../../probes/basic/spec/ktrans_model.py), run by
[`tools/spec_rules.py`](../../tools/spec_rules.py); [docs/spec-method.md](../spec-method.md) §3a,
[the keyword plan](spec-plan.md)) over the measured cases it names.
- **reference:** ✓ means the check holds on EVERY case it selects of the VG-8020's run.
- **zerobas:** the cases where zerobas fails it, which are its differences.

The tables are generated from the checks, so a sentence here cannot say more than the data does.

**Bounds, not digits.** `ATN`'s last digits are the reference's own approximation. Where a rule says "within B
units", the target is computed exactly (to 60 digits and more, in Python, from the argument's own bytes) and a unit is
one in the 14th significant digit of the target; B is the worst error MEASURED on the VG-8020, rounded up to a whole unit (the measured
worst is in the sentence), and a control with a bound just below that worst is FALSE, so the bound cannot be tightened past the measured worst. Whether zerobas's digits equal the
reference's byte for byte is a separate observation, under *Differences*: a zerobas result inside the bound agrees
with the rule even where its digits differ.

**Evidence.** One probe, [`probes/basic/spec/ktrans.py`](../../probes/basic/spec/ktrans.py) (the maths region's
second, on the shared RAM-record harness [`ramrec.py`](../../probes/basic/spec/ramrec.py) and the frame of
[`kmath.py`](../../probes/basic/spec/kmath.py)), typed on both machines; run file
[`scratchpad/KTR_run1.out`](../../scratchpad/KTR_run1.out) (2026-11-24, all groups; zerobas's side on that day's build). The
argument is `READ` into a variable of the case's own type (`N%`, `N!` or `N#`) and that variable's own bytes are
recorded before the call. Each case is evaluated twice: `R=ATN(N)`, with `R` a double whose 8 bytes are recorded,
and `Q=USR(ATN(N))`, where `USR` is the probe's own 18-byte routine (POKEd above `CLEAR`'s limit) that copies
`VALTYP` and `DAC` -- `ATN`'s result unconverted, by the convention [USR.md](USR.md) documents -- into the probe's
memory, so the result's TYPE and its own bytes are seen. Before every case `R` holds -12345 and the type cell 255, so
an error cannot read as a result; an apparatus row per argument (`R=N`, `Q=USR(N)`) must give back the argument's own
type and bytes on both machines, or the loader refuses the run.
- **[KTR TI ATN *n*]** (integers), **[KTR TS1 / TS2 ATN *n*]** (singles), **[KTR TD1 / TD2 ATN *n*]** (doubles),
  *n* the `DATA` text. Integers: 0, 1, -1, 2, -2, 3, -3, 4, 5, -5, 7, 10, -10, 20, -20, 50, -50, 100, -100, 145, 146, -147, -148, -149, -150, -200, -297, -298, 1000, -1000, 12345, 32767, -32768. Singles: 0, -0, 1E-64, -1E-64, 1E-20, 1E-10, -1E-10, 1E-6, -1E-6, .001, -.001, .01, .1, -.1, .2, .25, .5, -.5, .693147, .7, .75, .9, .999999, 1, -1, 1.00001, 1.5, -1.5, 2, -2, 2.5, -2.5, 2.71828, 3, 5, 10, -10, 20, -20, 50, -50, 99, 100, -100, 145.062, 145.063, -147.3, -147.4, -149.66, -149.67, -297.03, -297.04, -1000, 1000, 12345.6, 99999.9, .785398, -.785398, 1.0472, .523599, 1.5708, -1.5708, 1.57079, 3.14159, -3.14159, 3.1416, 4.71239, 6.28318, 6.28319, 7, 10.5, 100.5, 1E5, 123456, 1E6, -1E6, 1E10, 1E12, 1E13, 5E13, 7E13, 1E14, 1E20, 1E38, -1E38, 9.99999E62, -9.99999E62, 1.23456E-5, 3.33333, .333333, -.333333, 4, 8, 16, 64, .0625, 1E30, -1E30, 1E-30, 1E-63, 1.73205, .57735, -.57735, -40000, -65535, -65536, -99999, -1E5, -999999. Doubles:
  0, -0, 1D-64, -1D-64, 1D-14, -1D-14, 1D-10, 1D-7, .001, -.001, .1, -.1, .5, -.5, .69314718055995, 1.0000000000001, .99999999999999, 1, -1, 2, -2, 2.302585092994, 2.718281828459, 2.7182818284590, 10, -10, 1.2345678901234, -1.2345678901234, 12.345678901234, 50, -50, 100, -100, 145.06286, 145.0628, 145.063, -147.3, -147.4, -149.668, -149.67, -297.033, -297.04, -1000, 1000, 1D10, 1D20, 1D-20, 9.9999999999999D62, -9.9999999999999D62, 32767.9, 123456789.01234, .78539816339745, -.78539816339745, .78539816339744, 1.0471975511966, .5235987755983, 1.5707963267949, -1.5707963267949, 1.5707963267948, 3.1415926535898, -3.1415926535898, 3.1415926535897, 4.7123889803847, 6.2831853071796, -6.2831853071796, 12.566370614359, 1000, -1000, 1D10, -1D10, 1D11, 1D12, 1D13, 7D13, 1D14, 1D38, 1.7320508075689, .57735026918963, -.57735026918963, 1D-5, -1D-5, .12345678901234, -.12345678901234, 1234.5678901234, 31415.926535898, 100, 3.3333333333333, 1D30, -1D30, 1D-30.
- **[KTR FX *i*]**: a fixed statement, `S$` = `"12"`; the list, with what each one separates, is `FX` in the probe:
  a string literal or variable as the argument, the result assigned to `R$`, `1/0`, no argument, an extra one, no
  `)`, no parenthesis; the literals `2.5`, `-2.5`, `7`, `7%`, `2.5!`, `2.5#`, `&H8000`, `-32768`, `-0`, `1/4`;
  spaces; `ATN(ATN(.5))`; and a single `N!` assigned 1 whose exponent byte is then POKEd to 0 or `&H80`
  (digit bytes `10 00 00`).
- **[KTR TS3 ATN *n*]** (singles) and **[KTR TD3 ATN *n*]** (doubles), added by the goldfish pass to separate rival rules the first run could not tell apart: the angles where p has 13 integer digits, ties in p, p just below and above 1E-64, EXP's edges and its huge-negative threshold. Singles: 6E12, 7E12, -7E12, 9E12, 1.1E13, -1.1E13, 1.2E13, 1.3E13, -1.3E13, 1.5E13, -1.5E13, 1.7E13, 3E13, 6.3E13, 1.75, 2.75, 7.5, -7.5, 9.5, 13.5, 5E-64, -5E-64, 6E-64, 6.28318E-64, 6.28319E-64, -6.28319E-64, 7E-64, -65536.5, -65537, -70000, -80000, -90000, -99990, -99998, -75000, -75450, -75451, -75452, -75453, -76000, -75460, -75500, -75600, -75700, -75800, -75900. Doubles: -147.36, -147.365, -147.3654, -147.3655, -147.36544595, -147.36544596, -147.366, 145.06286085, 145.06286086, 145.0628609, 145.06287, 145.0629, 1.1D13, -1.1D13, 1.3D13, 1.5D13, 6.2831D-64, 6.2832D-64.
- **[KTR FY *i*]**: fixed statements that USE a non-canonical result (SIN(0), COS(7E13), TAN(1E13), EXP(-147.4), ATN of the single `80 10 00 00`) -- in `STR$` (PRINT's number format; its length and first bytes are recorded), `=0`, `<0`, `+1`, `*1E10`, negated, assigned to a single `Z!` and an integer `Z%` (read back through `USR`) -- and the non-canonical single `00 12 34 56` / `80 12 34 56` as the argument; `FY` in the probe.

**Controls** ([`ktrans_controls.py`](../../probes/basic/spec/ktrans_controls.py)): each is a rival rule run over the reference's cases: “within 2 units (zerobas's design target, Joost 2026-07-13)” is FALSE on 3 of the 302 cases it selects (e.g. KTR TS1 ATN .693147); “correctly rounded” is FALSE on 31 of the 302 cases it selects (e.g. KTR TI ATN 3); “within 2.5 units” is FALSE on 2 of the 302 cases it selects (e.g. KTR TS1 ATN .693147); “a signed zero (80 ...) gives a negative zero C0 00 ... -- zerobas's” is FALSE on 2 of the 2 cases it selects (e.g. KTR FX 137); “an exponent-0 single keeps its digit bytes, the sign dropped (the first run's rule)” is FALSE on 1 of the 2 cases it selects (e.g. KTR FY 52); “any exponent-0 single gives the constant 00 10 00 00 ... (review 2.6)” is FALSE on 1 of the 4 cases it selects (e.g. KTR FY 51); “times 1E10 gives a clean zero (8 zero bytes) -- zerobas's” is FALSE on 1 of the 1 cases it selects (e.g. KTR FY 36); “negation sets the sign bit” is FALSE on 1 of the 1 cases it selects (e.g. KTR FY 37); “a single takes the zero as 4 zero bytes -- zerobas's” is FALSE on 1 of the 1 cases it selects (e.g. KTR FY 38).

<!-- RULES BEGIN -->
<!-- GENERATED by tools/spec_rules.py from probes/basic/spec/atn_rules.py -- do not edit; `python3 tools/spec_rules.py probes/basic/spec/atn_rules.py --write` -->

**11 rules; 11 hold on the reference. Of the 1655 recorded outputs (each case's error from `R=F(x)` and from `Q=USR(F(x))`, R's 8 bytes, the result's type as USR saw it and the result's own bytes): 1655 read by a rule's check, 0 declared NOT evidence (below), 0 unread.**

#### 1. ATN(x)

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-ATN-ZERO** A zero argument gives a zero DOUBLE: ATN(0) is 8 zero bytes; a single whose exponent byte is 0 keeps its digit bytes (00 10 00 00 gives 00 10 00 00 00 00 00 00, 00 12 34 56 gives 00 12 34 56 00 00 00 00); with the sign bit set too (exponent byte &H80) it is 00 10 00 00 00 00 00 00 whatever the digits (80 10 00 00 and 80 12 34 56 alike). | 10 | ✓ | ✗ 2: KTR FX 137, KTR FY 52 |
| **R-ATN-NEAR** Any other argument gives a DOUBLE within 3 units of the 14th significant digit of atan x (between -pi/2 and pi/2): ATN(1) .78539816339745, ATN(1E-63) 1E-63, ATN(1E13) 1.5707963267948, ATN(1E38) 1.5707963267949. Measured worst 2.7 units (ATN(1.0471975511966#)). | 302 | ✓ | ✓ |
| **R-ATN-ODD** ATN(-x) is ATN(x) with the sign bit flipped (every x measured with its negation). | 65 | ✓ | ✓ |
| **R-ATN-ODDBYTES** On a non-canonical single (exponent byte 0 or &H80, digit bytes 10 00 00 or 12 34 56) it gives what the rules above say for a zero argument. | 4 | ✓ | ✗ 2: KTR FX 137, KTR FY 52 |
| **R-ATN-USE** The zero ATN gives for a signed zero single (80 10 00 00: 00 10 00 00 00 00 00 00) is an ordinary zero to the rest of BASIC (KTR FY, each the same machine's own zero): PRINT's number format (STR$) gives " 0", it equals 0 and is not below 0, plus 1 is exactly the double 1, and an integer variable takes it as 0; but times 1E10 and negated it comes back with the SAME bytes (exponent byte 0, no sign bit), and a single variable keeps exponent byte 0 and the digits rounded half up to 6 (00 10 00 00). | 8 | ✓ | ✗ 4: KTR FY 32, KTR FY 36, KTR FY 37, KTR FY 38 |
| **R-ATN-NESTED** ATN(ATN(.5)) is ATN of the double that ATN(.5) returns (the KTR TS1 row): what the rules above say for that double. | 1 | ✓ | ✓ |

#### 2. ATN(x): forms, errors and assignment

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-ATN-TYPE** A string as the argument (a literal or a variable) is error 13 (Type mismatch), and so is assigning the result to a string variable: the result is a number. | 3 | ✓ | ✓ |
| **R-ATN-OWNERR** An argument that fails to compute raises its own error (1/0: error 11). | 1 | ✓ | ✓ |
| **R-ATN-SYNTAX** No argument, a second argument, no closing parenthesis, or the name without a parenthesis is error 2 (Syntax error). | 4 | ✓ | ✓ |
| **R-ATN-FORMS** Spaces before the parenthesis and around the argument are allowed, and a literal's own type is the argument's (2.5 a single, 7 an integer, &H8000 the integer -32768, -32768 a single, -0 the integer 0, 1/4 a double); each gives what the rules above say for that value. | 12 | ✓ | ✓ |
| **R-ATN-ASSIGN** `R=ATN(x)` with R a double stores the result's 8 bytes as they are (a zero's digit bytes included), and an error stores nothing (R keeps its sentinel). Read in every case. | 321 | ✓ | ✗ 2: KTR TI ATN 0, KTR FX 133 |

<!-- RULES END -->

## Differences from the reference

- **The last digit of some results differs, and neither side is always right.** Both machines hold R-ATN-NEAR
  (within 3 units of the 14th digit of atan x): the VG-8020's worst is 2.7 units (ATN(1.0471975511966#)) and
  zerobas's 2.7 too (ATN(.693147!)) -- so the 2-unit target of Joost's 2026-07-13 sign-off (the reference's own worst
  case as it was then measured) is met by neither machine on the wider matrix; a control shows "within 2 units" is
  false on 3 of the reference's cases. `ATN(1)` prints .78539816339745 there and .78539816339746 here; the true
  value rounds to the former ([spec-basic-mathpack-slice2.md](../spec-basic-mathpack-slice2.md) §11.10,
  [spec-basic-mathacc.md](../spec-basic-mathacc.md)).
- **The zeros' bytes** ([D-TRANSZERO](../../todo/open/D-TRANSZERO.md)): ATN of a single whose exponent byte is
  &H80 (a zero with its sign bit set: 80 10 00 00, 80 12 34 56) is 00 10 00 00 00 00 00 00 there and
  C0 00 00 00 00 00 00 00 here (rules R-ATN-ZERO, R-ATN-ODDBYTES, KTR FX 137, FY 52). That one is NOT invisible: `STR$` -- PRINT's number
  format -- gives " 0" there and "-." here (rule R-ATN-USE, KTR FY 32), and times 1E10, negated or put in a single it
  gives other bytes here (FY 36-38; `=0` and `+1` agree). `R=ATN(0%)` and `R=ATN(-0)` store leftover digit bytes in
  R here (rule R-ATN-ASSIGN, KTR TI ATN 0, KTR FX 133), as D-SQRZERO.

The one rung not yet proven is **RAM usage**: `ATN` uses the same amount of free memory on both machines, but the two write different work-area cells along the way — the VG-8020 a few that zerobas does not, and zerobas some scratch cells of its own for the calculation.

## On later generations (MSX2, MSX2+)

[A] Not measured yet: the probe has not run on the MSX2 / MSX2+ references (spec-method §4).

## Open (not measured)

- [A] Direct mode: every case ran inside a program.
- [A] An argument's own error was measured with one kind (`1/0`, error 11); that any error of the argument wins is assumed.
- [A] Which work-area cells the call writes (the RAM-usage rung).
- [A] Non-canonical bytes other than the four measured singles (exponent byte 0 or `&H80` with digit bytes `10 00 00`
  or `12 34 56`), and doubles with exponent byte 0: whether the signed zero's result 00 10 00 00 ... is a constant
  or comes from some digit the two measured cases share.
- [A] A result inside a larger expression other than the measured `+1`, `*1E10`, negation, `=0` and `<0` (all on the
  signed zero's result); a NONZERO result assigned to a single or an integer.
- [A] Whether either machine's error is ever more than 3 units: 302 results measured; the bound is the measured
  worst (2.69) rounded up.

## What we found, and how

- **Goldfish pass 1** (2026-11-24, a fresh test-writer review of the six pages): "a zero argument keeps its digit
  bytes" holds only without the sign bit -- ATN of 80 12 34 56 is 00 10 00 00 00 00 00 00, like 80 10 00 00, while
  00 12 34 56 gives 00 12 34 56 00 00 00 00. Using these zeros (KTR FY) found zerobas's signed zero C0 00 ... prints
  as "-." -- a visible difference, added to D-TRANSZERO.
- **The transcendentals' rules are bounds, measured** (2026-11-24, D-KWSPEC's maths region, second unit). ATN is a double always; a zero argument gives a zero that keeps its digit bytes (without the sign bit; see above); ATN is odd, byte for byte; both machines are within 2.7 units of the 14th digit, so the 2-unit figure this page quoted is neither machine's measured worst.
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

## Related concepts

- [Numbers](../concepts/numbers.md) — integers, single and double precision

## Tests that cover it

- `make math-acceptance` — sixty arguments against the mathematically true
  value, each within 2 units, with the cases where zerobas and the VG-8020
  differ listed.
- `make kwsweep` — the everyday row (`INT(ATN(1)*1000)`), the error rows for
  {2, 13}, and the deliberately-broken-build check.
- `make kwram` — the RAM-usage comparison.
