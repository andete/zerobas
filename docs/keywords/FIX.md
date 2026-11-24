<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->
<!-- example: reference=VG-8020 disk=no -->

# `FIX` — drop the fraction of a number

> **Spec:** DRAFT 1 (2026-11-24) — 183 cases measured on the Philips VG-8020 (BASIC's reference) and on
> zerobas, by typed BASIC ([`kmath.py`](../../probes/basic/spec/kmath.py)); every rule is executable and
> every recorded output is read by one. Not yet reviewed ([the keyword plan](spec-plan.md)).
> Goldfish pass 1 (test writer) 2026-11-24: 9 findings, 9 measured (or checked on the run), 0 moved to open.
>
> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. Three differences:
> two invisible to PRINT (the bytes a variable stores, a product's bytes) and
> one the error code of a malformed call (below).
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`FIX(x)` cuts off the fraction of `x`, toward zero: `FIX(1.7)` is 1 and
`FIX(-1.7)` is −1. Its sibling [`INT`](INT.md) rounds down instead, so the two
differ only for negative numbers with a fraction (`INT(-1.7)` is −2). zerobas
gives the same values and errors as the Philips VG-8020 in every case we have
measured, except the bytes a variable stores for a zero result and the error
of a call that is both unclosed and given a string (below).

## Syntax

```
FIX(<numeric expression>)
```

One argument, always.

## Details

- **Toward zero, on both sides.** `FIX(2.7)` is 2 and `FIX(-2.7)` is −2;
  `FIX(-1.5)` is −1.
- **The result keeps the argument's type, precision and range.** `FIX` does
  not convert to an integer (`A%`), so numbers far outside −32768 to 32767
  work: `FIX(-1E38)` is -1E38, no error; `FIX(2.5)` is the single 2,
  `FIX(2.5#)` the double 2, `FIX(7%)` the integer 7.
- **A result below 1 in size is a zero that keeps the argument's digits** in
  its bytes: `FIX(.5)` is exponent byte 0, then the digits 50 00 00 -- 0 to
  arithmetic, comparisons, `SGN` and `STR$` (`FIX(.5)+1` is 1, `FIX(.5)=0` is
  true, `FIX(-.5)<0` false, `STR$(FIX(.5))` " 0"), visible only through
  `VARPTR` or `USR` -- and in the bytes of a product: `FIX(.5!)*3` is a zero
  whose digit bytes are 30 00 ... on the VG-8020 (see *Differences*). Use
  [`CINT`](CINT.md) when you need the 16-bit integer type; stored in an integer
  variable the result simply becomes that integer (`T%=FIX(-32768.5)` is
  -32768, `T%=FIX(.5)` 0).
- **A string argument** (`FIX("A")`) is `Type mismatch` (error 13).
- **No argument, two arguments, no parentheses or a missing `)`** —
  `FIX()`, `FIX(1,2)`, `PRINT FIX`, `FIX(5` — are all `Syntax error`
  (error 2).
- **The argument is worked out first, the `)` checked next, the type last.**
  `FIX(1/0` (no `)`) is `Division by zero` (error 11), but `FIX("A"` and
  `FIX("A",2)` are `Syntax error` on the VG-8020 -- and `Type mismatch` here
  (see *Differences*).

| you write | you get |
|---|---|
| `FIX(2.7)` | 2 |
| `FIX(-2.7)` | −2 |
| `FIX(-1.5)` | −1 |
| `FIX(-1E38)` | no error |
| `FIX("A")` | error 13, `Type mismatch` |
| `FIX()`, `FIX(1,2)` | error 2, `Syntax error` |

The whole set of errors `FIX` can raise is {2, 13}, the same on both machines.

## Example

```
10 PRINT FIX(1.7);FIX(-1.7)
20 PRINT FIX(-2.7);INT(-2.7)
30 PRINT FIX(12345678.9#)
40 ON ERROR GOTO 70
50 PRINT FIX("A")
60 END
70 PRINT "Error";ERR:RESUME NEXT
RUN
 1 -1
-2 -3
 12345678
Error 13
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_fix.out`](../../scratchpad/kwdoc_fix.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## The specification

Reference: the Philips VG-8020's MSX BASIC. Ours: zerobas on the diskless machine
(`C-BIOS_MSX1_EU_REPACK_NODISK`).

**How to read the rules below.** Every rule is a sentence AND a check
([`probes/basic/spec/fix_rules.py`](../../probes/basic/spec/fix_rules.py), model in
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
recorded before the call, so the rules work from the exact value given. Each case is evaluated twice: `R=FIX(N)`,
with `R` a double whose 8 bytes are recorded, and `Q=USR(FIX(N))`, where `USR` is the probe's own 18-byte routine
(POKEd above `CLEAR`'s limit): by the MSX convention ([USR.md](USR.md)) it receives `FIX`'s result unconverted
in `DAC` with its type in `VALTYP`, and copies both into the probe's memory -- so the result's TYPE (2 integer, 4
single, 8 double) and its own bytes are seen, not only its value. Before every case `R` holds -12345 and the type cell
255, so an error, which assigns nothing and never reaches `USR`, cannot read as a result. An apparatus row per
argument (no function: `R=N`, `Q=USR(N)`) must hand `USR` the argument's own type and bytes on both machines, or the
loader refuses the run.
- **[KMA MI FIX *n*]**, **[KMA MS FIX *n*]**, **[KMA MD FIX *n*]**: the argument an integer, a single or a
  double, *n* the `DATA` text. Integers: 0, 1, -1, 2, -2, 3, 4, 5, -5, 9, 10, 16, 100, 255, 12345, -12345, 32767, -32767, -32768. Singles: 0, -0, 1, -1, .5, -.5, .4, -.4, .6, -.6, .9, -.9, .1, -.1, 1.5, -1.5, 1.9, -1.9, 2.5, -2.5, 2, 3, 4, 5, 9, 10, 16, .25, 2.25, 1.44, 99.9998, .999999, -.999999, 99999.5, -99999.5, 99999.9, -99999.9, 12345.6, -12345.6, 32767, 32767.5, -32767.5, 32768, -32768, -32768.5, -32769, 65535.5, 123456, -123456, 999999, -999999, 1E6, -1E6, 1E10, -1E10, 1E-10, -1E-10, 1E-6, -1E-6, 1.23456E-5, 1E-63, -1E-63, 1E-64, -1E-64, 9.99999E62, -9.99999E62. Doubles:
  0, -0, 1, -1, .5, -.5, .9, -.9, 1.5, -1.5, 2.5, -2.5, 2, 3, 5, 10, .25, 2.25, 99.99998, 32767.9, -32768.1, 32768, -32768, -32769, 65536.5, 1234567.5, -1234567.5, 12345678.9, -12345678.9, -9999999.5, .99999999999999, -.99999999999999, 1.9999999999999, -1.9999999999999, 9999999999999.5, -9999999999999.5, 1234567890123.4, -1234567890123.4, 12345678901234, -12345678901234, 1D14, -1D14, 1D20, -1D20, 1D-10, -1D-10, 1D-14, -1D-14, 1D-64, -1D-64, 9.9999999999999D62, -9.9999999999999D62.
- **[KMA FX *i*]**: a fixed statement, `S$` = `"12"`; the list, with what each one separates, is `FX` in the probe:
  a string literal or variable as the argument, the result assigned to `R$`, `1/0`, no argument, an extra one, no
  `)`, no parenthesis; the literals `2.5`, `-2.5`, `7`, `7%`, `2.5!`, `2.5#`, `&H8000`, `-32768`, `-0`, `1/4`;
  spaces; `FIX(FIX(2.25))`; and a single `N!` assigned 1 whose exponent byte is then POKEd to 0 or `&H80`
  (digit bytes `10 00 00`).
- **[KMA FY *i*]**, **[KMA FZ *i*]** (goldfish pass 1, 2026-11-24): more fixed statements, on a two-line frame
  (`FY` and `FZ` in the probe): the order of the checks (`FIX(1/0`, `FIX("A"`, `FIX(1/0,2)`, `FIX("A",2)`); the
  forms this page quotes (`PRINT FIX`, `FIX(1,2)`, `FIX(-1E38)`); the result stored in an integer `T%` or a single
  `T!` (holding -7 before) and read back through `USR(T%)` / `USR(T!)`; `FIX(.5!)`'s exponent-0 zero used in `+1`, `*3`, `=0`, `>0`, `FIX(-.5!)<0`, `SGN` and `STR$` (KMA FY 35-42); and (FZ) `FIX` nested 16
  and 32 deep. Two apparatus checks run before any rule, and the loader refuses the run if either fails: every
  literal the FX / FY forms use, alone (`R=<literal>`, `Q=USR(<literal>)`, KMA FY 70-92), has the type and bytes the
  FORMS rule gives it; and every matrix row's recorded argument is its `DATA` text's value in its type, on both
  machines -- so the six rows of one text (the apparatus row and the five functions) saw the same argument, no
  function changed its argument variable, and the two machines `READ` the text alike.

**Controls** ([`kmath_controls.py`](../../probes/basic/spec/kmath_controls.py)): each is a rival rule run over the reference's cases: “below 1 a canonical zero (8 / 4 zero bytes)” is FALSE on 35 of the 137 cases it selects (e.g. KMA MS FIX .5); “rounding half away from zero (CINT-style)” is FALSE on 68 of the 137 cases it selects (e.g. KMA MS FIX .5); “INT's floor in FIX's place” is FALSE on 33 of the 137 cases it selects (e.g. KMA MS FIX -.5); “a single exponent-0 zero stored in R as 8 zero bytes -- zerobas's LET” is FALSE on 24 of the 160 cases it selects (e.g. KMA MS FIX .5); “FIX(.5!) read as its digits, .5” is FALSE on 7 of the 8 cases it selects (e.g. KMA FY 35); “a single exponent-0 zero stored as zero bytes -- zerobas's LET” is FALSE on 2 of 2 cases it selects (e.g. KMA FX 115); “the argument's type checked before the `)` (13) -- zerobas's rule” is FALSE on 2 of the 4 cases it selects (e.g. KMA FY 22); “a single exponent-0 zero stored in T! as zero bytes -- zerobas's LET” is FALSE on 1 of the 4 cases it selects (e.g. KMA FY 62).

<!-- RULES BEGIN -->
<!-- GENERATED by tools/spec_rules.py from probes/basic/spec/fix_rules.py -- do not edit; `python3 tools/spec_rules.py probes/basic/spec/fix_rules.py --write` -->

**14 rules; 14 hold on the reference. Of the 915 recorded outputs (each case's error from `R=F(x)` and from `Q=USR(F(x))`, R's 8 bytes, the result's type as USR saw it and the result's own bytes): 915 read by a rule's check, 0 declared NOT evidence (below), 0 unread.**

#### 1. FIX(x)

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-FIX-INT** An integer is returned unchanged, as an integer (-32768% included). | 19 | ✓ | ✓ |
| **R-FIX-WHOLE** A single or a double of 1 or more in size keeps its type, its sign and its exponent byte; the digits after the decimal point become 0 -- toward zero on both sides (FIX(-2.5) is -2, FIX(-32768.5!) -32768, FIX(-9999999999999.5#) -9999999999999); a whole number is unchanged. | 79 | ✓ | ✓ |
| **R-FIX-SMALL** Below 1 in size (zero included) the result is a zero of the argument's type whose exponent byte is 0 -- the sign dropped -- and whose digit bytes are the argument's, unchanged: FIX(-.5!) is 00 50 00 00, FIX(1D-64) 00 10 00 00 00 00 00 00. It is 0 to arithmetic, comparison, SGN and STR$ (R-FIX-ZEROUSE). | 39 | ✓ | ✓ |
| **R-FIX-ODD** The same on a non-canonical single: exponent byte 0 or &H80 with digit bytes 10 00 00 both give 00 10 00 00. | 2 | ✓ | ✓ |
| **R-FIX-ZEROUSE** The exponent-0 zero FIX(.5!) returns (00 50 00 00) is 0 to arithmetic, comparison, SGN and STR$: FIX(.5!)+1 is 1 (a double), FIX(.5!)=0 is true, >0 and <0 false (FIX(-.5!)<0 too: the sign is dropped), SGN gives 0, STR$ gives " 0". FIX(.5!)*3 is a double whose exponent byte is 0 (the value 0) and whose digit bytes are 30 00 00 00 00 00 00 -- the other operand's (one case). | 8 | ✓ | ✗ 1: KMA FY 36 |
| **R-FIX-LET** The assignment, not FIX, decides what a variable keeps: the POKEd single 00 10 00 00 assigned to R (`R=N!`) leaves R 00 10 00 00 00 00 00 00, and `N!=FIX(N!)` with N! = .5 keeps 00 50 00 00 in the single N! and then in R. | 2 | ✓ | ✗ 2: KMA FX 115, KMA FX 116 |
| **R-FIX-TYPE** A string as the argument (a literal or a variable) is error 13 (Type mismatch), and so is assigning the result to a string variable: the result is a number. | 3 | ✓ | ✓ |
| **R-FIX-OWNERR** An argument that fails to compute raises its own error (1/0: error 11). | 1 | ✓ | ✓ |
| **R-FIX-SYNTAX** No argument, a second argument, no closing parenthesis, or the name without a parenthesis is error 2 (Syntax error); so are `PRINT FIX` and `FIX(1,2)`, the forms this page quotes. | 6 | ✓ | ✓ |
| **R-FIX-ORDER** The argument is evaluated before the call's shape is checked, and its type after: FIX(1/0 (no `)`) and FIX(1/0,2) raise the argument's own error 11, but FIX("A" (no `)`) and FIX("A",2) are error 2 (Syntax error), not 13 -- the `)` is required before the string is refused. | 4 | ✓ | ✗ 2: KMA FY 22, KMA FY 24 |
| **R-FIX-NEST** FIX nested 16 and 32 deep (FIX(FIX(...(-2.5)...))) gives what the rules above give applied that many times, with no error. | 2 | ✓ | ✓ |
| **R-FIX-FORMS** Spaces before the parenthesis and around the argument are allowed, and a literal's own type is the argument's: 2.5 and -2.5 are singles, 7 an integer, 7% / 2.5! / 2.5# what they say, &H8000 the integer -32768, -32768 a single (a minus on the single 32768), -0 the integer 0, 1/4 a double; FIX of FIX(2.25) is FIX of that result. Each gives what the rules above say for that type and value; so does FIX(-1E38), a single. These types are MEASURED: each literal alone, `R=<literal>` / `Q=USR(<literal>)`, gives that type and value on both machines (KMA FY 70-92; the loader refuses a run where it does not). | 14 | ✓ | ✓ |
| **R-FIX-ASSIGN** `R=FIX(x)` with R a double stores the result's value -- an integer by its value, a single's own 4 bytes then four zero bytes, its exponent byte and digit bytes as they are (so FIX(.5!)'s exponent-0 result keeps its digit bytes in R: 00 50 00 00 00 00 00 00) -- and an error stores nothing (R keeps its sentinel). Read in every case that assigns R. | 177 | ✓ | ✗ 24: KMA MS FIX .5, KMA MS FIX -.5, KMA MS FIX .4, KMA MS FIX -.4, KMA MS FIX .6, KMA MS FIX -.6 … (+18) |
| **R-FIX-TARGET** Stored in an INTEGER variable, FIX's result loses its fraction -- truncated, not rounded (SQR(3) stores 1) -- and a value outside -32768..32767 is error 6 (Overflow), the variable unchanged; stored in a SINGLE, a single keeps its own 4 bytes (an exponent-0 one its digit bytes too), an integer becomes its value, a double is cut to 6 digits (SQR(2): 1.41421). Read back through USR(T%) / USR(T!). | 4 | ✓ | ✗ 1: KMA FY 62 |

<!-- RULES END -->

## Differences from the reference

- **A zero result with digit bytes is stored in a variable as zero bytes here** (rule R-FIX-ASSIGN, 24 cases:
  `R=FIX(.5!)`, `R=FIX(-1E-64!)` ...) -- [D-ZEROLET](../../todo/open/D-ZEROLET.md). `FIX`'s own result agrees in every
  case (R-FIX-SMALL, R-FIX-ODD); the difference is the assignment of a single whose exponent byte is 0 -- to a
  double, or to a single (rule R-FIX-TARGET, KMA FY 62 `T!=FIX(.5!)`; rule R-FIX-LET, KMA FX 115 `R=N!` of a POKEd
  single, KMA FX 116 `N!=FIX(N!)`).
- **`FIX(.5!)*3` is a zero with digit bytes 30 00 ... on the VG-8020, 8 zero bytes here** (rule R-FIX-ZEROUSE, KMA FY
  36) -- [D-ZEROMUL](../../todo/open/D-ZEROMUL.md). The value is 0 on both; it is the multiply's, not `FIX`'s.
- **`FIX("A"` (no `)`) and `FIX("A",2)` are error 13 here, error 2 on the VG-8020** (rule R-FIX-ORDER, KMA FY 22, 24)
  -- [D-ARGTYPEORDER](../../todo/open/D-ARGTYPEORDER.md).

The one rung not yet proven is **RAM usage**: `FIX` uses the same amount of
free memory on both machines, but the two write different work-area cells
along the way — the VG-8020 a few that zerobas does not, and zerobas two of
its own. Nothing a program can observe through `FRE` or the documented
variables differs.

## On later generations (MSX2, MSX2+)

[A] Not measured yet: the probe has not run on the MSX2 / MSX2+ references (spec-method §4).

## Open (not measured)

- [A] Direct mode: every case ran inside a program.
- [A] An argument's own error was measured with one kind (`1/0`, error 11); that any error of the argument wins is assumed.
- [A] Which work-area cells the call writes (the RAM-usage rung).
- [A] Non-canonical bytes other than the two measured singles (exponent byte 0 or `&H80` with digit bytes `10 00 00`): a double, non-BCD digit nibbles, `&H80` with zero digit bytes.
- [A] Why `FIX(.5!)+1` is a DOUBLE on both machines (KMA FY 35), and an exponent-0 zero in the operators not measured
  here (`-`, `/`, `^`, `\`, `MOD`): the operators region's. PRINT itself is not read (STR$ is).
- [A] Stored in an INTEGER variable, a NEGATIVE result with a fraction: truncated toward zero or rounded down is not
  separated (no such case; the conversion region, [CINT](CINT.md)). Stored in a SINGLE, a double that needs its 7th
  digit rounded or cut is not separated either (`SQR(2)`'s 7th digit is 3).

## What we found, and how

- **The tests could not see the result's precision** (found 2026-07-12, in the
  review of the first math slice). The double-precision path was never
  exercised; zerobas turned out to be right, and cases such as
  `FIX(12345678.9#)` and `FIX(-12345678.9#)` were added so it is proven rather
  than trusted ([spec-basic-math-pack.md](../spec-basic-math-pack.md) §9.5).
- **Empty or malformed calls returned a number** (fixed 2026-07-13 and
  2026-07-14, D-F2-3 and D-F2-4). `FIX()` printed 0, and `PRINT FIX` or
  `FIX(1,1)` quietly ran on whatever value was left over from earlier, where the
  VG-8020 says `Syntax error`:
  [spec-basic-empty-expr-syntax-error.md](../spec-basic-empty-expr-syntax-error.md),
  [spec-basic-malformed-call-syntax-error.md](../spec-basic-malformed-call-syntax-error.md).
- **A test on one sign could not tell `FIX` from `INT`** (D-KWBREADTH,
  2026-09-13). A row now reads `FIX(-2.7);FIX(2.7)`, toward zero on both
  sides, which is exactly where the two keywords part ways.
- **The whole error set was measured on the reference** (D-KWT6, 2026-09-27):
  wrong type, no argument, an extra argument and `FIX(-1E38)`; zerobas matched
  every case ([`t6enum_b2.out`](../../scratchpad/t6enum_b2.out)).

## Where it lives

`evmc_fix` in [basic/expr.asm](../../basic/expr.asm), reached from the math
selector `ev_ff_mathconv`; the work is `fp_trunc` in
[basic/float-arith.asm](../../basic/float-arith.asm), which [`INT`](INT.md)
also uses. The design notes are in
[spec-basic-math-pack.md](../spec-basic-math-pack.md) §9.

## Related concepts

- [Numbers](../concepts/numbers.md) — integers, single and double precision

## Tests that cover it

- `make math-acceptance` — values and result types against the VG-8020,
  `FIX` against `INT` on both signs, and the empty and malformed calls.
- `make kwsweep` — the everyday rows (`FIX(-1.7)`, `FIX(-2.7);FIX(2.7)`), the
  error rows for {2, 13}, and the deliberately-broken-build check.
- `make kwram` — the RAM-usage comparison.
