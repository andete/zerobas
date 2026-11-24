<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->
<!-- example: reference=VG-8020 disk=no -->

# `EXP` — e raised to a power

> **Spec:** DRAFT 1 (2026-11-24) — 255 cases measured on the Philips VG-8020 (BASIC's reference) and on
> zerobas, by typed BASIC ([`ktrans.py`](../../probes/basic/spec/ktrans.py)); every rule is executable and
> every recorded output is read by one. Not yet reviewed ([the keyword plan](spec-plan.md)).
>
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

- **`EXP(0)` is exactly 1**, on both machines, and the result is always double precision.
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

## The specification

Reference: the Philips VG-8020's MSX BASIC. Ours: zerobas on the diskless machine
(`C-BIOS_MSX1_EU_REPACK_NODISK`).

**How to read the rules below.** Every rule is a sentence AND a check
([`probes/basic/spec/exp_rules.py`](../../probes/basic/spec/exp_rules.py), model in
[`ktrans_model.py`](../../probes/basic/spec/ktrans_model.py), run by
[`tools/spec_rules.py`](../../tools/spec_rules.py); [docs/spec-method.md](../spec-method.md) §3a,
[the keyword plan](spec-plan.md)) over the measured cases it names.
- **reference:** ✓ means the check holds on EVERY case it selects of the VG-8020's run.
- **zerobas:** the cases where zerobas fails it, which are its differences.

The tables are generated from the checks, so a sentence here cannot say more than the data does.

**Bounds, not digits.** `EXP`'s last digits are the reference's own approximation. Where a rule says "within B
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
recorded before the call. Each case is evaluated twice: `R=EXP(N)`, with `R` a double whose 8 bytes are recorded,
and `Q=USR(EXP(N))`, where `USR` is the probe's own 18-byte routine (POKEd above `CLEAR`'s limit) that copies
`VALTYP` and `DAC` -- `EXP`'s result unconverted, by the convention [USR.md](USR.md) documents -- into the probe's
memory, so the result's TYPE and its own bytes are seen. Before every case `R` holds -12345 and the type cell 255, so
an error cannot read as a result; an apparatus row per argument (`R=N`, `Q=USR(N)`) must give back the argument's own
type and bytes on both machines, or the loader refuses the run.
- **[KTR TI EXP *n*]** (integers), **[KTR TS1 / TS2 EXP *n*]** (singles), **[KTR TD1 / TD2 EXP *n*]** (doubles),
  *n* the `DATA` text. Integers: 0, 1, -1, 2, -2, 3, -3, 4, 5, -5, 7, 10, -10, 20, -20, 50, -50, 100, -100, 145, 146, -147, -148, -149, -150, -200, -297, -298, 1000, -1000, 12345, 32767, -32768. Singles: 0, -0, 1E-64, -1E-64, 1E-20, 1E-10, -1E-10, 1E-6, -1E-6, .001, -.001, .01, .1, -.1, .2, .25, .5, -.5, .693147, .7, .75, .9, .999999, 1, -1, 1.00001, 1.5, -1.5, 2, -2, 2.5, -2.5, 2.71828, 3, 5, 10, -10, 20, -20, 50, -50, 99, 100, -100, 145.062, 145.063, -147.3, -147.4, -149.66, -149.67, -297.03, -297.04, -1000, 1000, 12345.6, 99999.9, .785398, -.785398, 1.0472, .523599, 1.5708, -1.5708, 1.57079, 3.14159, -3.14159, 3.1416, 4.71239, 6.28318, 6.28319, 7, 10.5, 100.5, 1E5, 123456, 1E6, -1E6, 1E10, 1E12, 1E13, 5E13, 7E13, 1E14, 1E20, 1E38, -1E38, 9.99999E62, -9.99999E62, 1.23456E-5, 3.33333, .333333, -.333333, 4, 8, 16, 64, .0625, 1E30, -1E30, 1E-30, 1E-63, 1.73205, .57735, -.57735, -40000, -65535, -65536, -99999, -1E5, -999999. Doubles:
  0, -0, 1D-64, -1D-64, 1D-14, -1D-14, 1D-10, 1D-7, .001, -.001, .1, -.1, .5, -.5, .69314718055995, 1.0000000000001, .99999999999999, 1, -1, 2, -2, 2.302585092994, 2.718281828459, 2.7182818284590, 10, -10, 1.2345678901234, -1.2345678901234, 12.345678901234, 50, -50, 100, -100, 145.06286, 145.0628, 145.063, -147.3, -147.4, -149.668, -149.67, -297.033, -297.04, -1000, 1000, 1D10, 1D20, 1D-20, 9.9999999999999D62, -9.9999999999999D62, 32767.9, 123456789.01234, .78539816339745, -.78539816339745, .78539816339744, 1.0471975511966, .5235987755983, 1.5707963267949, -1.5707963267949, 1.5707963267948, 3.1415926535898, -3.1415926535898, 3.1415926535897, 4.7123889803847, 6.2831853071796, -6.2831853071796, 12.566370614359, 1000, -1000, 1D10, -1D10, 1D11, 1D12, 1D13, 7D13, 1D14, 1D38, 1.7320508075689, .57735026918963, -.57735026918963, 1D-5, -1D-5, .12345678901234, -.12345678901234, 1234.5678901234, 31415.926535898, 100, 3.3333333333333, 1D30, -1D30, 1D-30.
- **[KTR FX *i*]**: a fixed statement, `S$` = `"12"`; the list, with what each one separates, is `FX` in the probe:
  a string literal or variable as the argument, the result assigned to `R$`, `1/0`, no argument, an extra one, no
  `)`, no parenthesis; the literals `2.5`, `-2.5`, `7`, `7%`, `2.5!`, `2.5#`, `&H8000`, `-32768`, `-0`, `1/4`;
  spaces; `EXP(EXP(.5))`; and a single `N!` assigned 1 whose exponent byte is then POKEd to 0 or `&H80`
  (digit bytes `10 00 00`).

**Controls** ([`ktrans_controls.py`](../../probes/basic/spec/ktrans_controls.py)): each is a rival rule run over the reference's cases: “correctly rounded (within 0.5 units)” is FALSE on 37 of the 65 cases it selects (e.g. KTR TI EXP 1); “within 2 units” is FALSE on 6 of the 65 cases it selects (e.g. KTR TI EXP 1); “within 3 units (SMALL's bound) above 1 too” is FALSE on 44 of the 73 cases it selects (e.g. KTR TI EXP 2); “within 400 units” is FALSE on 2 of the 73 cases it selects (e.g. KTR TD1 EXP 145.06286); “within 500 units (POS's bound) below -1 too” is FALSE on 6 of the 31 cases it selects (e.g. KTR TI EXP -2); “a clean zero (8 zero bytes) below 1E-64” is FALSE on 6 of the 6 cases it selects (e.g. KTR TI EXP -148); “0 in the band, as above and below it -- zerobas's rule” is FALSE on 7 of the 7 cases it selects (e.g. KTR TI EXP -150); “0 for the huge negatives -- zerobas's rule” is FALSE on 10 of the 10 cases it selects (e.g. KTR TS2 EXP -1E6); “Overflow from 145.0628 (not 145.063) on” is FALSE on 2 of the 41 cases it selects (e.g. KTR TD1 EXP 145.06286); “a single argument gives a single result” is FALSE on 83 of the 109 cases it selects (e.g. KTR TS1 EXP 0).

<!-- RULES BEGIN -->
<!-- GENERATED by tools/spec_rules.py from probes/basic/spec/exp_rules.py -- do not edit; `python3 tools/spec_rules.py probes/basic/spec/exp_rules.py --write` -->

**16 rules; 16 hold on the reference. Of the 1275 recorded outputs (each case's error from `R=F(x)` and from `Q=USR(F(x))`, R's 8 bytes, the result's type as USR saw it and the result's own bytes): 1275 read by a rule's check, 0 declared NOT evidence (below), 0 unread.**

#### 1. EXP(x)

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-EXP-ZERO** EXP of zero is exactly the double 1 (41 10 00 00 00 00 00 00), whatever the zero's digit or sign bytes (00 10 00 00 and 80 10 00 00 give 1 too). | 8 | ✓ | ✓ |
| **R-EXP-SMALL** For 0 < |x| <= 1 the result is a DOUBLE (whatever the argument's type) within 3 units of the 14th significant digit of e^x (measured worst 2.5: EXP(1) is 2.7182818284588, e is 2.71828182845904...). | 65 | ✓ | ✓ |
| **R-EXP-POS** For 1 < x < 63 ln 10 (145.06286...) a double within 500 units of e^x: the error grows with x (EXP(10) 6.7 units low, EXP(100) 74, EXP(145.0628#) 472). | 70 | ✓ | ✓ |
| **R-EXP-NEG** For x < -1, while e^x >= 1E-64, a double within 40000 units of e^x -- an irregular error: EXP(-3) 5 units, EXP(-2) 5,930, EXP(-50) 331, EXP(-147.3) 27,178 (all high). | 28 | ✓ | ✓ |
| **R-EXP-OVER** From e^x >= 1E63 on (x >= 145.063: 145.06286# still gives 9.99...E62) it is error 6 (Overflow). | 39 | ✓ | ✓ |
| **R-EXP-TINY** Where 1E-65 <= e^x < 1E-64 (x from about -147.36 to -149.668) the result is a double whose exponent byte is 0 -- it reads as zero -- and whose digit bytes are the digits of e^x (within 40000 units; measured worst 39,525, EXP(-149.668#)): EXP(-147.4) is 00 96 60 36 12 55 89 73. | 6 | ✓ | ✗ 6: KTR TI EXP -148, KTR TI EXP -149, KTR TS1 EXP -147.4, KTR TS1 EXP -149.66, KTR TD1 EXP -147.4, KTR TD1 EXP -149.668 |
| **R-EXP-BAND** Where 1E-129 <= e^x < 1E-65 (x from -149.67 to -297.033) it is error 6 (Overflow), not 0. | 7 | ✓ | ✗ 7: KTR TI EXP -150, KTR TI EXP -200, KTR TI EXP -297, KTR TS1 EXP -149.67, KTR TS1 EXP -297.03, KTR TD1 EXP -149.67 … (+1) |
| **R-EXP-FLUSH** Below that, down to at least x = -65536 (e^x < 1E-129: -297.04, -298, -1000, -32768, -40000, -65535, -65536) it is a clean double zero, 8 zero bytes. | 13 | ✓ | ✗ 10: KTR TI EXP -298, KTR TS1 EXP -297.04, KTR TS1 EXP -1000, KTR TS2 EXP -40000, KTR TS2 EXP -65535, KTR TS2 EXP -65536 … (+4) |
| **R-EXP-HUGE** From x = -99999 down (measured -99999, -1E5, -999999, -1E6, -1E10, -1E30, -1E38, -9.99999E62 and -9.9999999999999D62) it is error 6 (Overflow) again. | 10 | ✓ | ✗ 10: KTR TS2 EXP -1E6, KTR TS2 EXP -1E38, KTR TS2 EXP -9.99999E62, KTR TS2 EXP -1E30, KTR TS2 EXP -99999, KTR TS2 EXP -1E5 … (+4) |
| **R-EXP-ODDBYTES** On a non-canonical single (exponent byte 0 or &H80, digit bytes 10 00 00) it gives what the rules above say for a zero argument. | 2 | ✓ | ✓ |
| **R-EXP-NESTED** EXP(EXP(.5)) is EXP of the double that EXP(.5) returns (the KTR TS1 row): what the rules above say for that double. | 1 | ✓ | ✓ |

#### 2. EXP(x): forms, errors and assignment

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-EXP-TYPE** A string as the argument (a literal or a variable) is error 13 (Type mismatch), and so is assigning the result to a string variable: the result is a number. | 3 | ✓ | ✓ |
| **R-EXP-OWNERR** An argument that fails to compute raises its own error (1/0: error 11). | 1 | ✓ | ✓ |
| **R-EXP-SYNTAX** No argument, a second argument, no closing parenthesis, or the name without a parenthesis is error 2 (Syntax error). | 4 | ✓ | ✓ |
| **R-EXP-FORMS** Spaces before the parenthesis and around the argument are allowed, and a literal's own type is the argument's (2.5 a single, 7 an integer, &H8000 the integer -32768, -32768 a single, -0 the integer 0, 1/4 a double); each gives what the rules above say for that value. | 12 | ✓ | ✗ 1: KTR FX 17 |
| **R-EXP-ASSIGN** `R=EXP(x)` with R a double stores the result's 8 bytes as they are (a zero's digit bytes included), and an error stores nothing (R keeps its sentinel). Read in every case. | 255 | ✓ | ✗ 3: KTR TI EXP -1000, KTR TI EXP -32768, KTR FX 16 |

<!-- RULES END -->

## Differences from the reference

- **The digits differ, and zerobas's are the accurate ones, by design** (Joost, 2026-07-13). Both machines hold
  R-EXP-SMALL / -POS / -NEG: zerobas within 1 unit of the 14th digit of e^x on every argument measured, the VG-8020
  within 2.5 for |x| <= 1, 472 above 1 and 39,525 below -1 (EXP(1) 2.7182818284588 there, 2.718281828459 here;
  EXP(-2) .13533528329591 there, .13533528323661 here, the true value .135335283236613). Matching the reference
  would mean building its error in on purpose ([spec-basic-mathacc.md](../spec-basic-mathacc.md)).
- **Large negative arguments: 0 here, Overflow there, deliberately** (rules R-EXP-BAND, R-EXP-HUGE: 17 cases). Where
  1E-129 <= e^x < 1E-65 (x from -149.67 to -297.033) and from x = -99999 down, the VG-8020 stops with `Overflow`
  (error 6) and zerobas returns 0 -- the reference's own answer just either side of its band. An attempt to copy the
  reference's error (D-EXPNEG, 2026-08-31) went against the recorded decision, turned the tests red and was reverted
  in full; reopening it is Joost's call ([spec-basic-mathpack-slice2.md](../spec-basic-mathpack-slice2.md) §12.9,
  [the standing item](../../todo/open/X-THE-NEGATIVE-EXP-DEVIATION-IS-WIDER.md)).
- **The zeros' bytes** (invisible to PRINT; [D-TRANSZERO](../../todo/open/D-TRANSZERO.md)): from 1E-65 to 1E-64
  (R-EXP-TINY, 6 cases) the reference returns exponent 0 with e^x's digits, zerobas 8 zero bytes; below 1E-129
  (R-EXP-FLUSH, 10 cases) zerobas leaves digit bytes behind where the reference returns 8 zero bytes; and
  `R=EXP(N%)` for N% = -1000 or -32768, `R=EXP(&H8000)` and `EXP(-32768)` (R-EXP-ASSIGN, R-EXP-FORMS: KTR TI EXP
  -1000, -32768, KTR FX 16, 17) store leftover digit bytes.

The one rung not yet proven is **RAM usage**: `EXP` uses the same amount of free memory on both machines, but the two write different work-area cells along the way — the VG-8020 a few that zerobas does not, and zerobas some scratch cells of its own for the calculation.

## On later generations (MSX2, MSX2+)

[A] Not measured yet: the probe has not run on the MSX2 / MSX2+ references (spec-method §4).

## Open (not measured)

- [A] Direct mode: every case ran inside a program.
- [A] An argument's own error was measured with one kind (`1/0`, error 11); that any error of the argument wins is assumed.
- [A] Which work-area cells the call writes (the RAM-usage rung).
- [A] Non-canonical bytes other than the two measured singles (exponent byte 0 or `&H80` with digit bytes `10 00 00`).
- [A] Where between x = -65536 (0) and -99999 (Overflow) the huge-negative Overflow starts, and why (a wrap of the
  result's decimal exponent past 16 bits fits the measured points, but is not established).
- [A] The overflow edge between 145.06286 (a number) and 145.063 (Overflow) to the last digit.
- [A] Whether the reference's error is ever larger than the bounds: 169 nonzero results measured; the bounds are the
  measured worst rounded up.

## What we found, and how

- **The transcendentals' rules are bounds, measured** (2026-11-24, D-KWSPEC's maths region, second unit). EXP is a double always; EXP(0) is exactly 1; the VG-8020's error is 2.5 units near 0, grows to 472 at the top of the range and is irregular below -1 (5,930 units at EXP(-2), 39,525 at -149.668#); below 1E-64 its result is a zero that keeps e^x's digits, then Overflow to 1E-129, then 0 down to -65536, and Overflow again from -99999 down.
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
