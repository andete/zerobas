<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->
<!-- example: reference=VG-8020 disk=no -->

# `SQR` — the square root of a number

> **Spec:** DRAFT 1 (2026-11-24) — 176 cases measured on the Philips VG-8020 (BASIC's reference) and on
> zerobas, by typed BASIC ([`kmath.py`](../../probes/basic/spec/kmath.py)); every rule is executable and
> every recorded output is read by one. Not yet reviewed ([the keyword plan](spec-plan.md)).
> Goldfish pass 1 (test writer) 2026-11-24: 19 findings, 10 measured (or checked on the run), 2 moved to open; 2 fixed in the checks, 5 were wording.
>
> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. One recorded
> difference: the last printed digit of some roots (below); one more,
> invisible to PRINT, in the bytes of `SQR(0%)`; and the error code of a
> malformed call.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`SQR(x)` returns the square root of `x`, which must not be negative.
`SQR(9)` is 3. The answer has 14 significant digits. zerobas raises the same
errors as the Philips VG-8020 in every case we have measured but one (a call
both unclosed and given a string, below), and prints the same value except,
for some arguments, in the last digit — where zerobas is the one that is
correctly rounded (one measured exception, `SQR(99.99998)`, where the two give
the same digit and neither is).

## Syntax

```
SQR(<numeric expression>)
```

One argument, always.

## Details

- **The result is always double precision**, whatever the argument's type:
  `SQR(4%)` is the double 2, `SQR(2.25!)` the double 1.5.
- **Perfect squares are exact** on both machines: `SQR(16)` is 4,
  `SQR(100)` is 10, `SQR(0)` is 0, `SQR(.25)` is .5, `SQR(1E-10)` is 1E-05 --
  any root that fits in 14 significant digits.
- **Other roots carry 14 significant digits, the last one approximate.**
  zerobas gives the correctly rounded answer; the VG-8020's is within 3 units
  of the 14th digit, below or above (`SQR(2)` is 1.4142135623730 there, where
  the true root is 1.41421356237309505…; `SQR(.4!)` is 2.4 units high). See
  *Differences*.
- **A negative argument** (`SQR(-1)`) is `Illegal function call` (error 5),
  however small (`SQR(-1E-64)`) or large (`SQR(-1E38)`).
- **Stored in a variable** the double is converted: `T%=SQR(3)` is 1 (the
  fraction dropped, not rounded), `T%=SQR(1E10)` is `Overflow` (error 6),
  `T!=SQR(2)` is 1.41421.
- **A string argument** (`SQR("A")`) is `Type mismatch` (error 13).
- **No argument, two arguments, no parentheses or a missing `)`** —
  `SQR()`, `SQR(1,2)`, `PRINT SQR`, `SQR(5` — are all `Syntax error`
  (error 2).
- **The argument is worked out first, the `)` checked next, the type last.**
  `SQR(1/0` (no `)`) is `Division by zero` (error 11), but `SQR("A"` and
  `SQR("A",2)` are `Syntax error` on the VG-8020 -- and `Type mismatch` here
  (see *Differences*).

| you write | you get |
|---|---|
| `SQR(9)` | 3 |
| `SQR(16)` | 4 |
| `SQR(0)` | 0 |
| `SQR(-1)` | error 5, `Illegal function call` |
| `SQR("A")` | error 13, `Type mismatch` |
| `SQR()`, `SQR(1,2)` | error 2, `Syntax error` |

The whole set of errors `SQR` can raise is {2, 5, 13}, the same on both
machines.

## Example

```
10 PRINT SQR(9);SQR(16);SQR(0)
20 PRINT SQR(.25);SQR(1E10)
30 ON ERROR GOTO 60
40 PRINT SQR(-1)
50 END
60 PRINT "Error";ERR:RESUME NEXT
RUN
 3  4  0
 .5  100000
Error 5
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_sqr.out`](../../scratchpad/kwdoc_sqr.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## The specification

Reference: the Philips VG-8020's MSX BASIC. Ours: zerobas on the diskless machine
(`C-BIOS_MSX1_EU_REPACK_NODISK`).

**How to read the rules below.** Every rule is a sentence AND a check
([`probes/basic/spec/sqr_rules.py`](../../probes/basic/spec/sqr_rules.py), model in
[`kmath_model.py`](../../probes/basic/spec/kmath_model.py), run by
[`tools/spec_rules.py`](../../tools/spec_rules.py); [docs/spec-method.md](../spec-method.md) §3a,
[the keyword plan](spec-plan.md)) over the measured cases it names.
- **reference:** ✓ means the check holds on EVERY case it selects of the VG-8020's run.
- **zerobas:** the cases where zerobas fails it, which are its differences.

The tables are generated from the checks, so a sentence here cannot say more than the data does.

**Evidence.** One probe, [`probes/basic/spec/kmath.py`](../../probes/basic/spec/kmath.py) (the maths region's first,
on the shared RAM-record harness [`ramrec.py`](../../probes/basic/spec/ramrec.py)), typed on both machines; run file
[`scratchpad/KMA_run1.out`](../../scratchpad/KMA_run1.out) (2026-11-24; zerobas's side on that day's build). The
argument is `READ` into a variable of the case's own type (`N%`, `N!` or `N#`) and that variable's own bytes are
recorded before the call, so the rules work from the exact value given. Each case is evaluated twice: `R=SQR(N)`,
with `R` a double whose 8 bytes are recorded, and `Q=USR(SQR(N))`, where `USR` is the probe's own 18-byte routine
(POKEd above `CLEAR`'s limit): by the MSX convention ([USR.md](USR.md)) it receives `SQR`'s result unconverted
in `DAC` with its type in `VALTYP`, and copies both into the probe's memory -- so the result's TYPE (2 integer, 4
single, 8 double) and its own bytes are seen, not only its value. Before every case `R` holds -12345 and the type cell
255, so an error, which assigns nothing and never reaches `USR`, cannot read as a result. An apparatus row per
argument (no function: `R=N`, `Q=USR(N)`) must hand `USR` the argument's own type and bytes on both machines, or the
loader refuses the run.
- **[KMA MI SQR *n*]**, **[KMA MS SQR *n*]**, **[KMA MD SQR *n*]**: the argument an integer, a single or a
  double, *n* the `DATA` text. Integers: 0, 1, -1, 2, -2, 3, 4, 5, -5, 9, 10, 16, 100, 255, 12345, -12345, 32767, -32767, -32768. Singles: 0, -0, 1, -1, .5, -.5, .4, -.4, .6, -.6, .9, -.9, .1, -.1, 1.5, -1.5, 1.9, -1.9, 2.5, -2.5, 2, 3, 4, 5, 9, 10, 16, .25, 2.25, 1.44, 99.9998, .999999, -.999999, 99999.5, -99999.5, 99999.9, -99999.9, 12345.6, -12345.6, 32767, 32767.5, -32767.5, 32768, -32768, -32768.5, -32769, 65535.5, 123456, -123456, 999999, -999999, 1E6, -1E6, 1E10, -1E10, 1E-10, -1E-10, 1E-6, -1E-6, 1.23456E-5, 1E-63, -1E-63, 1E-64, -1E-64, 9.99999E62, -9.99999E62. Doubles:
  0, -0, 1, -1, .5, -.5, .9, -.9, 1.5, -1.5, 2.5, -2.5, 2, 3, 5, 10, .25, 2.25, 99.99998, 32767.9, -32768.1, 32768, -32768, -32769, 65536.5, 1234567.5, -1234567.5, 12345678.9, -12345678.9, -9999999.5, .99999999999999, -.99999999999999, 1.9999999999999, -1.9999999999999, 9999999999999.5, -9999999999999.5, 1234567890123.4, -1234567890123.4, 12345678901234, -12345678901234, 1D14, -1D14, 1D20, -1D20, 1D-10, -1D-10, 1D-14, -1D-14, 1D-64, -1D-64, 9.9999999999999D62, -9.9999999999999D62.
- **[KMA FX *i*]**: a fixed statement, `S$` = `"12"`; the list, with what each one separates, is `FX` in the probe:
  a string literal or variable as the argument, the result assigned to `R$`, `1/0`, no argument, an extra one, no
  `)`, no parenthesis; the literals `2.5`, `-2.5`, `7`, `7%`, `2.5!`, `2.5#`, `&H8000`, `-32768`, `-0`, `1/4`;
  spaces; `SQR(SQR(2.25))`; and a single `N!` assigned 1 whose exponent byte is then POKEd to 0 or `&H80`
  (digit bytes `10 00 00`).
- **[KMA FY *i*]**, **[KMA FZ *i*]** (goldfish pass 1, 2026-11-24): more fixed statements, on a two-line frame
  (`FY` and `FZ` in the probe): the order of the checks (`SQR(1/0`, `SQR("A"`, `SQR(1/0,2)`, `SQR("A",2)`); the
  forms this page quotes (`PRINT SQR`, `SQR(1,2)`, `SQR(-1E38)`); the result stored in an integer `T%` or a single
  `T!` (holding -7 before) and read back through `USR(T%)` / `USR(T!)`; and (FZ) `SQR` nested 16
  and 32 deep. Two apparatus checks run before any rule, and the loader refuses the run if either fails: every
  literal the FX / FY forms use, alone (`R=<literal>`, `Q=USR(<literal>)`, KMA FY 70-92), has the type and bytes the
  FORMS rule gives it; and every matrix row's recorded argument is its `DATA` text's value in its type, on both
  machines -- so the six rows of one text (the apparatus row and the five functions) saw the same argument, no
  function changed its argument variable, and the two machines `READ` the text alike.

**Controls** ([`kmath_controls.py`](../../probes/basic/spec/kmath_controls.py)): each is a rival rule run over the reference's cases: “the correctly rounded root -- zerobas's rule” is FALSE on 30 of the 137 cases it selects (e.g. KMA MI SQR 2); “the root truncated at 14 digits” is FALSE on 30 of the 137 cases it selects (e.g. KMA MI SQR 5); “within 1 unit of the 14th digit (not 3)” is FALSE on 10 of the 61 cases it selects (e.g. KMA MI SQR 255); “a single argument gives a single result (the cases with no error)” is FALSE on 40 of 40 cases it selects (e.g. KMA MS SQR 0); “80 10 00 00 a zero (the sign bit of an exponent-0 number ignored)” is FALSE on 1 of the 2 cases it selects (e.g. KMA FX 114); “R's earlier digit bytes kept under exponent 0 -- zerobas's SQR(0%)” is FALSE on 1 of the 2 cases it selects (e.g. KMA FX 118); “an integer target rounds (CINT-style) instead of truncating” is FALSE on 1 of the 5 cases it selects (e.g. KMA FY 66); “the argument's type checked before the `)` (13) -- zerobas's rule” is FALSE on 2 of the 4 cases it selects (e.g. KMA FY 29).

**The table's case counts overlap**, unlike the sibling pages': R-SQR-NEG, -ZERO, -EXACT and -NEAR select the fixed
statements' value forms too (by what the model says for them), so R-SQR-FORMS's cases are counted twice;
R-SQR-ASSIGN reads every case that assigns R. The counts therefore add to more than the 176 cases.

<!-- RULES BEGIN -->
<!-- GENERATED by tools/spec_rules.py from probes/basic/spec/sqr_rules.py -- do not edit; `python3 tools/spec_rules.py probes/basic/spec/sqr_rules.py --write` -->

**13 rules; 13 hold on the reference. Of the 880 recorded outputs (each case's error from `R=F(x)` and from `Q=USR(F(x))`, R's 8 bytes, the result's type as USR saw it and the result's own bytes): 880 read by a rule's check, 0 declared NOT evidence (below), 0 unread.**

#### 1. SQR(x)

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-SQR-NEG** A negative argument is error 5 (Illegal function call), in every type and size (-1%, -32768%, -1E-64, -9.9999999999999D62) -- and so is 80 10 00 00 (a single with the sign bit set and exponent 0). | 58 | ✓ | ✓ |
| **R-SQR-ZERO** Zero gives a DOUBLE zero; a single zero whose digit bytes are not 0 (exponent byte 0, digits 10 00 00) gives a double with those digit bytes kept (00 10 00 00 00 00 00 00). | 7 | ✓ | ✓ |
| **R-SQR-EXACT** The result is always a DOUBLE, whatever the argument's type (SQR(4%) is the double 2). When the exact root has at most 14 significant digits it is that root, exactly: SQR(2.25) 1.5, SQR(1.44!) 1.2, SQR(1E-10) 1E-05, SQR(1D20) 1E+10, SQR(1D-64) 1E-32. | 26 | ✓ | ✓ |
| **R-SQR-NEAR** Otherwise the result is a double within 3 units of the 14th significant digit of the exact root (the unit sized from the exact root's decade) -- NOT always the correctly rounded root: SQR(2) is 1.4142135623730 (the exact root is 1.41421356237309505...), SQR(.4!) 2.4 units high. The measured errors run from -1.9 units (SQR(1234567890123.4#)) to +2.5 (SQR(.999999!) and SQR(999999!)); their rule is the reference's own algorithm, which the printed digits do not reveal. A bound, not the reference's digits: any root within it passes, zerobas's correctly rounded one included (the Differences and Open below). | 61 | ✓ | ✓ |
| **R-SQR-LET** A zero root assigned to R is 8 zero bytes whatever R held before: `R=0:R=SQR(0%)` and `R=-12345:R=SQR(0!)` both leave R 00 00 00 00 00 00 00 00. | 2 | ✓ | ✓ |
| **R-SQR-TYPE** A string as the argument (a literal or a variable) is error 13 (Type mismatch), and so is assigning the result to a string variable: the result is a number. | 3 | ✓ | ✓ |
| **R-SQR-OWNERR** An argument that fails to compute raises its own error (1/0: error 11). | 1 | ✓ | ✓ |
| **R-SQR-SYNTAX** No argument, a second argument, no closing parenthesis, or the name without a parenthesis is error 2 (Syntax error); so are `PRINT SQR` and `SQR(1,2)`, the forms this page quotes. | 6 | ✓ | ✓ |
| **R-SQR-ORDER** The argument is evaluated before the call's shape is checked, and its type after: SQR(1/0 (no `)`) and SQR(1/0,2) raise the argument's own error 11, but SQR("A" (no `)`) and SQR("A",2) are error 2 (Syntax error), not 13 -- the `)` is required before the string is refused. | 4 | ✓ | ✗ 2: KMA FY 29, KMA FY 31 |
| **R-SQR-NEST** SQR nested 16 and 32 deep (SQR(SQR(...(1)...))) gives what the rules above give applied that many times, with no error. | 2 | ✓ | ✓ |
| **R-SQR-FORMS** Spaces before the parenthesis and around the argument are allowed, and a literal's own type is the argument's: 2.5 and -2.5 are singles, 7 an integer, 7% / 2.5! / 2.5# what they say, &H8000 the integer -32768, -32768 a single (a minus on the single 32768), -0 the integer 0, 1/4 a double; SQR of SQR(2.25) is SQR of that result. Each gives what the rules above say for that type and value; so does SQR(-1E38), a single. These types are MEASURED: each literal alone, `R=<literal>` / `Q=USR(<literal>)`, gives that type and value on both machines (KMA FY 70-92; the loader refuses a run where it does not). | 14 | ✓ | ✓ |
| **R-SQR-ASSIGN** `R=SQR(x)` with R a double stores the result's value -- an integer by its value, a single's own 4 bytes then four zero bytes, its exponent byte and digit bytes as they are (SQR's result is always a double: R holds its 8 bytes) -- and an error stores nothing (R keeps its sentinel). Read in every case that assigns R. | 169 | ✓ | ✗ 2: KMA MI SQR 0, KMA FX 110 |
| **R-SQR-TARGET** Stored in an INTEGER variable, SQR's result loses its fraction -- truncated, not rounded (SQR(3) stores 1) -- and a value outside -32768..32767 is error 6 (Overflow), the variable unchanged; stored in a SINGLE, a single keeps its own 4 bytes (an exponent-0 one its digit bytes too), an integer becomes its value, a double is cut to 6 digits (SQR(2): 1.41421). Read back through USR(T%) / USR(T!). | 5 | ✓ | ✓ |

<!-- RULES END -->

## Differences from the reference

- **The last digit of a root that is not exact differs, by design** -- in 35 of the 176 measured cases (KMA MI SQR 2,
  3, 255, 12345; KMA MS SQR .4, .6, .9, 1.5, 1.9, 2, 2.5, 3, .999999 ...; KMA MD SQR .9, 1.5, 2, 2.5, 3,
  1234567890123.4 ...; KMA FX 100, 102, 103, 105, 106, 112). zerobas computes the correctly rounded 14-digit root;
  the VG-8020's root is within 3 units of the 14th digit of the exact one (measured from 1.9 units low to 2.5 units
  high, so not "one unit low" as this page said before 2026-11-24). Both hold R-SQR-NEAR; the controls show the
  reference is neither correctly rounded nor truncated. The control "correctly rounded" is FALSE on 30 matrix
  cases, not 29: the 30th, `SQR(99.99998)` (KMA MD SQR 99.99998), is the precision floor below, where the two
  machines give the SAME digit and neither is the correctly rounded one -- so it is not a difference. Copying it would mean copying the reference's algorithm,
  whose rule the printed digits do not reveal. The decision, signed off by Joost on 2026-07-13: keep zerobas
  correctly rounded and record the difference ([spec-basic-math-pack.md](../spec-basic-math-pack.md) §10.3.1). A
  program that prints such a root in full can show a different last digit, and one that compares it with `=`
  against a typed-in constant could branch differently.
- **`SQR(0%)` stores a zero with leftover digit bytes here** (rule R-SQR-ASSIGN, KMA MI SQR 0, KMA FX 110 `SQR(-0)`):
  after `R=-12345`, `R=SQR(N%)` with N% = 0 leaves R as 00 12 34 50 00 00 00 00 and `R=SQR(-0)` 00 13 40 50 00 00 00 00
  (exponent 0, so the value is 0) where the reference stores 8 zero bytes --
  [D-SQRZERO](../../todo/open/D-SQRZERO.md). The digits are not simply R's earlier ones (FX 110's are not); after
  `R=0`, and for `SQR(0!)`, the two agree (R-SQR-LET holds, KMA FX 117, 118), and so does `T!=SQR(0)` (KMA FY 69).
- **`SQR("A"` (no `)`) and `SQR("A",2)` are error 13 here, error 2 on the VG-8020** (rule R-SQR-ORDER, KMA FY 29, 31)
  -- [D-ARGTYPEORDER](../../todo/open/D-ARGTYPEORDER.md).

The one rung not yet proven is **RAM usage**: `SQR` uses the same amount of
free memory on both machines, but the two write different work-area cells
along the way — the VG-8020 a few that zerobas does not, and zerobas some
scratch cells of its own for the calculation.

## On later generations (MSX2, MSX2+)

[A] Not measured yet: the probe has not run on the MSX2 / MSX2+ references (spec-method §4).

## Open (not measured)

- [A] Direct mode: every case ran inside a program.
- [A] An argument's own error was measured with one kind (`1/0`, error 11); that any error of the argument wins is assumed.
- [A] Which work-area cells the call writes (the RAM-usage rung).
- [A] Non-canonical bytes other than the two measured singles (exponent byte 0 or `&H80` with digit bytes `10 00 00`): a double, non-BCD digit nibbles, `&H80` with zero digit bytes.
- [A] Stored in an INTEGER variable, a NEGATIVE result with a fraction: truncated toward zero or rounded down is not
  separated (no such case; the conversion region, [CINT](CINT.md)). Stored in a SINGLE, a double that needs its 7th
  digit rounded or cut is not separated either (`SQR(2)`'s 7th digit is 3).
- [A] Whether the reference's root is ever more than 3 units of the 14th digit away: 61 non-exact roots measured; the bound is the measured range rounded up.
- [A] R-SQR-NEAR does not pin the reference's own digits: an implementation anywhere within 3 units of the exact root
  passes it, whether or not it matches the VG-8020 -- zerobas's correctly rounded root does. The reference's bytes are
  recorded for all 61 roots ([`KMA_run1.out`](../../scratchpad/KMA_run1.out)) but no rule reads them byte for byte:
  the 2026-07-13 ruling keeps zerobas correctly rounded (Differences). A rule holding zerobas to correct rounding
  (within 0.5 unit, `SQR(99.99998)` the declared exception) would pin OUR side; it is not written.

## What we found, and how

- **"One unit low" was a reading of a few cases** (corrected 2026-11-24, D-KWSPEC's
  maths probe). Over 61 roots that are not exact, the reference's last digit
  is between 1.9 units low (`SQR(1234567890123.4#)`) and 2.5 units high
  (`SQR(.999999!)`, `SQR(999999!)`); the rule on this page is now that bound.
- **Bit-for-bit copying was tried and abandoned** (2026-07-13). The plan was to
  reproduce the reference's own rounding by matching its division. A
  time-boxed attempt got to about 80 % agreement and stopped there: the
  deciding digit sits below the 14 the machine prints. Correct rounding was
  chosen instead, and it is never less accurate than the reference
  ([spec-basic-math-pack.md](../spec-basic-math-pack.md) §10.3.1).
- **One near-tie is a precision floor.** `SQR(99.99998)` is the only argument
  found where zerobas cannot round correctly; the reference gives the same
  answer there. It is pinned in the tests so it cannot drift.
- **Empty or malformed calls** (fixed 2026-07-13 and 2026-07-14, D-F2-3 and
  D-F2-4). `SQR()` printed 0, and `PRINT SQR` or `SQR(1,2)` gave a wrong
  value or a wrong error, where the VG-8020 says `Syntax error`:
  [spec-basic-malformed-call-syntax-error.md](../spec-basic-malformed-call-syntax-error.md).
- **The whole error set was measured on the reference** (D-KWT6, 2026-09-27):
  wrong type, no argument, an extra argument, `SQR(-1)` and `SQR(0)`; zerobas
  matched every case ([`t6enum_run.out`](../../scratchpad/t6enum_run.out)).

## Where it lives

- Main ROM: `evmc_sqr` in [basic/expr.asm](../../basic/expr.asm) reads the
  argument, rejects a negative one (`evmc_sqr_err`) and hands the rest on.
- Sub-ROM: `fp_sqrt` in [sub/fp_sqrt.asm](../../sub/fp_sqrt.asm) computes the
  root.
- The design notes are in [spec-basic-math-pack.md](../spec-basic-math-pack.md)
  §10.

## Related concepts

- [Numbers](../concepts/numbers.md) — integers, single and double precision

## Tests that cover it

- `make math-acceptance` — roots against the mathematically true value, the
  known near-tie, the negative-argument error, and the empty and malformed
  calls.
- `make kwsweep` — the everyday row (`SQR(9)`), the error rows for {2, 5, 13},
  and the deliberately-broken-build check.
- `make kwram` — the RAM-usage comparison.
