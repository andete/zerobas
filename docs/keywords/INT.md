<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->
<!-- example: reference=VG-8020 disk=no -->

# `INT` — round a number down to a whole number

> **Spec:** DRAFT 1 (2026-11-24) — 182 cases measured on the Philips VG-8020 (BASIC's reference) and on
> zerobas, by typed BASIC ([`kmath.py`](../../probes/basic/spec/kmath.py)); every rule is executable and
> every recorded output is read by one. Not yet reviewed ([the keyword plan](spec-plan.md)).
> Goldfish pass 1 (test writer) 2026-11-24: 10 findings, 9 measured (or checked on the run), 0 moved to open; 1 was wording.
>
> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. Four differences,
> three invisible to PRINT (a result's type, a variable's bytes, a product's
> bytes) and one the error code of a malformed call (below).
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`INT(x)` returns the largest whole number that is not bigger than `x`: it
rounds **down**, toward minus infinity. `INT(1.7)` is 1 and `INT(-1.5)` is −2.
Its sibling [`FIX`](FIX.md) instead cuts the fraction off toward zero; the two
differ only for negative numbers with a fraction. zerobas gives the same values
and errors as the Philips VG-8020 in every case we have measured, except the
result's TYPE for a negative number with a fraction, and the error of a call
that is both unclosed and given a string (below).

## Syntax

```
INT(<numeric expression>)
```

One argument, always.

## Details

- **It rounds down, not toward zero.** `INT(-1.5)` is −2, `INT(-0.5)` is −1,
  while `INT(1.9)` is 1 and `INT(-1)` stays −1.
- **The result keeps the argument's precision and range** -- with one
  exception. `INT` does not convert to an integer (`A%`), so numbers far
  outside −32768 to 32767 work: `INT(12345678.9#)` is 12345678 and
  `INT(-9999999.5#)` is −10000000. Use [`CINT`](CINT.md) when you need the
  16-bit integer type.
- **The exception: a negative number with a fraction.** On the VG-8020 its
  result is not of the argument's type: between −1 and 0 (`INT(-.5)`) it is
  the INTEGER −1, and from −1 down (`INT(-1.5)`, `INT(-32768.5)`) it is a
  DOUBLE. The value is what you expect; only the type differs, and zerobas
  keeps the argument's type there (see *Differences*).
- **Below 1 (and not negative) the result is a zero that keeps the
  argument's digits** in its bytes, as for [`FIX`](FIX.md): `INT(.5)` is 0 to
  arithmetic, comparisons, `SGN` and `STR$` (`INT(.5)+1` is 1, `INT(.5)=0` is
  true, `STR$(INT(.5))` is " 0"), visible only through `VARPTR` or `USR` --
  and in the bytes of a product: `INT(.5!)*3` is a zero whose digit bytes are
  30 00 ... on the VG-8020 (see *Differences*).
- **No range errors.** `INT(-1E38)` is -1E38 on both machines. Stored in an
  integer variable the result must fit: `T%=INT(-32768.5)` is `Overflow`
  (error 6), `T%=INT(-.5)` is -1.
- **A space before the parenthesis is allowed**: `INT (7.9)` is 7.
- **A string argument** (`INT("A")`) is `Type mismatch` (error 13).
- **No argument, two arguments, no parentheses or a missing `)`** —
  `INT()`, `INT(1,2)`, `PRINT INT`, `INT(5` — are all `Syntax error`
  (error 2).
- **The argument is worked out first, the `)` checked next, the type last.**
  `INT(1/0` (no `)`) is `Division by zero` (error 11), but `INT("A"` and
  `INT("A",2)` are `Syntax error` on the VG-8020 -- and `Type mismatch` here
  (see *Differences*).

| you write | you get |
|---|---|
| `INT(1.7)`, `INT(1.9)` | 1 |
| `INT(-1.5)` | −2 |
| `INT(-0.5)` | −1 |
| `INT(12345678.9#)` | 12345678 |
| `INT(-1E38)` | no error |
| `INT("A")` | error 13, `Type mismatch` |
| `INT()`, `INT(1,2)` | error 2, `Syntax error` |

The whole set of errors `INT` can raise is {2, 13}, the same on both machines.

## Example

```
10 PRINT INT(1.7);INT(-1.5);INT(-0.5)
20 PRINT INT(12345678.9#)
30 PRINT INT (7.9);INT(-2.5)-FIX(-2.5)
40 ON ERROR GOTO 70
50 PRINT INT("A")
60 END
70 PRINT "Error";ERR:RESUME NEXT
RUN
 1 -2 -1
 12345678
 7 -1
Error 13
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_int.out`](../../scratchpad/kwdoc_int.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## The specification

Reference: the Philips VG-8020's MSX BASIC. Ours: zerobas on the diskless machine
(`C-BIOS_MSX1_EU_REPACK_NODISK`).

**How to read the rules below.** Every rule is a sentence AND a check
([`probes/basic/spec/int_rules.py`](../../probes/basic/spec/int_rules.py), model in
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
recorded before the call, so the rules work from the exact value given. Each case is evaluated twice: `R=INT(N)`,
with `R` a double whose 8 bytes are recorded, and `Q=USR(INT(N))`, where `USR` is the probe's own 18-byte routine
(POKEd above `CLEAR`'s limit): by the MSX convention ([USR.md](USR.md)) it receives `INT`'s result unconverted
in `DAC` with its type in `VALTYP`, and copies both into the probe's memory -- so the result's TYPE (2 integer, 4
single, 8 double) and its own bytes are seen, not only its value. Before every case `R` holds -12345 and the type cell
255, so an error, which assigns nothing and never reaches `USR`, cannot read as a result. An apparatus row per
argument (no function: `R=N`, `Q=USR(N)`) must hand `USR` the argument's own type and bytes on both machines, or the
loader refuses the run.
- **[KMA MI INT *n*]**, **[KMA MS INT *n*]**, **[KMA MD INT *n*]**: the argument an integer, a single or a
  double, *n* the `DATA` text. Integers: 0, 1, -1, 2, -2, 3, 4, 5, -5, 9, 10, 16, 100, 255, 12345, -12345, 32767, -32767, -32768. Singles: 0, -0, 1, -1, .5, -.5, .4, -.4, .6, -.6, .9, -.9, .1, -.1, 1.5, -1.5, 1.9, -1.9, 2.5, -2.5, 2, 3, 4, 5, 9, 10, 16, .25, 2.25, 1.44, 99.9998, .999999, -.999999, 99999.5, -99999.5, 99999.9, -99999.9, 12345.6, -12345.6, 32767, 32767.5, -32767.5, 32768, -32768, -32768.5, -32769, 65535.5, 123456, -123456, 999999, -999999, 1E6, -1E6, 1E10, -1E10, 1E-10, -1E-10, 1E-6, -1E-6, 1.23456E-5, 1E-63, -1E-63, 1E-64, -1E-64, 9.99999E62, -9.99999E62. Doubles:
  0, -0, 1, -1, .5, -.5, .9, -.9, 1.5, -1.5, 2.5, -2.5, 2, 3, 5, 10, .25, 2.25, 99.99998, 32767.9, -32768.1, 32768, -32768, -32769, 65536.5, 1234567.5, -1234567.5, 12345678.9, -12345678.9, -9999999.5, .99999999999999, -.99999999999999, 1.9999999999999, -1.9999999999999, 9999999999999.5, -9999999999999.5, 1234567890123.4, -1234567890123.4, 12345678901234, -12345678901234, 1D14, -1D14, 1D20, -1D20, 1D-10, -1D-10, 1D-14, -1D-14, 1D-64, -1D-64, 9.9999999999999D62, -9.9999999999999D62.
- **[KMA FX *i*]**: a fixed statement, `S$` = `"12"`; the list, with what each one separates, is `FX` in the probe:
  a string literal or variable as the argument, the result assigned to `R$`, `1/0`, no argument, an extra one, no
  `)`, no parenthesis; the literals `2.5`, `-2.5`, `7`, `7%`, `2.5!`, `2.5#`, `&H8000`, `-32768`, `-0`, `1/4`;
  spaces; `INT(INT(2.25))`; and a single `N!` assigned 1 whose exponent byte is then POKEd to 0 or `&H80`
  (digit bytes `10 00 00`).
- **[KMA FY *i*]**, **[KMA FZ *i*]** (goldfish pass 1, 2026-11-24): more fixed statements, on a two-line frame
  (`FY` and `FZ` in the probe): the order of the checks (`INT(1/0`, `INT("A"`, `INT(1/0,2)`, `INT("A",2)`); the
  forms this page quotes (`PRINT INT`, `INT(1,2)`, `INT(-1E38)`); the result stored in an integer `T%` or a single
  `T!` (holding -7 before) and read back through `USR(T%)` / `USR(T!)`; `INT(.5!)`'s exponent-0 zero used in `+1`, `*3`, `=0`, `>0`, `<0`, `SGN` and `STR$` (KMA FY 43-50); and (FZ) `INT` nested 16
  and 32 deep. Two apparatus checks run before any rule, and the loader refuses the run if either fails: every
  literal the FX / FY forms use, alone (`R=<literal>`, `Q=USR(<literal>)`, KMA FY 70-92), has the type and bytes the
  FORMS rule gives it; and every matrix row's recorded argument is its `DATA` text's value in its type, on both
  machines -- so the six rows of one text (the apparatus row and the five functions) saw the same argument, no
  function changed its argument variable, and the two machines `READ` the text alike.

**Controls** ([`kmath_controls.py`](../../probes/basic/spec/kmath_controls.py)): each is a rival rule run over the reference's cases: “the argument's own type -- zerobas's rule” is FALSE on 24 of the 137 cases it selects (e.g. KMA MS INT -.5); “toward zero (FIX) in INT's place” is FALSE on 33 of the 137 cases it selects (e.g. KMA MS INT -.5); “always a double, no integer -1 above -1” is FALSE on 16 of the 33 cases it selects (e.g. KMA MS INT -.5); “an integer whenever the result fits -32768..32767” is FALSE on 8 of the 33 cases it selects (e.g. KMA MS INT -1.5); “INT(.5!) read as its digits, .5” is FALSE on 7 of the 8 cases it selects (e.g. KMA FY 43); “a single exponent-0 zero stored in T! as zero bytes -- zerobas's LET” is FALSE on 1 of the 5 cases it selects (e.g. KMA FY 59); “the argument's type checked before the `)` (13) -- zerobas's rule” is FALSE on 2 of the 4 cases it selects (e.g. KMA FY 15).

<!-- RULES BEGIN -->
<!-- GENERATED by tools/spec_rules.py from probes/basic/spec/int_rules.py -- do not edit; `python3 tools/spec_rules.py probes/basic/spec/int_rules.py --write` -->

**13 rules; 13 hold on the reference. Of the 910 recorded outputs (each case's error from `R=F(x)` and from `Q=USR(F(x))`, R's 8 bytes, the result's type as USR saw it and the result's own bytes): 910 read by a rule's check, 0 declared NOT evidence (below), 0 unread.**

#### 1. INT(x)

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-INT-INT** An integer is returned unchanged, as an integer (-32768% included). | 19 | ✓ | ✓ |
| **R-INT-DOWN** A single or a double that is zero, positive, or negative and whole gives what FIX gives (FIX's page, its first three rules): its own type, the digits after the point 0 -- so INT(.5!) is 00 50 00 00, a zero with its digit bytes. | 85 | ✓ | ✓ |
| **R-INT-NEGFRAC** A negative single or double with digits after the point gives the next whole number DOWN, and NOT in the argument's type: between -1 and 0 (-.5, -1E-64) it is the INTEGER -1 (FF FF); from -1 down it is a DOUBLE -- INT(-1.5!) is the double -2, INT(-32768.5!) the double -32769, INT(-9999999999999.5#) -10000000000000. | 33 | ✓ | ✗ 24: KMA MS INT -.5, KMA MS INT -.4, KMA MS INT -.6, KMA MS INT -.9, KMA MS INT -.1, KMA MS INT -1.5 … (+18) |
| **R-INT-ODD** On a non-canonical single: 00 10 00 00 gives 00 10 00 00; 80 10 00 00 (negative, exponent 0) is a negative number above -1 and gives the integer -1. | 2 | ✓ | ✗ 1: KMA FX 68 |
| **R-INT-ZEROUSE** The exponent-0 zero INT(.5!) returns (00 50 00 00) is 0 to arithmetic, comparison, SGN and STR$: INT(.5!)+1 is 1 (a double), INT(.5!)=0 is true, >0 and <0 false, SGN gives 0, STR$ gives " 0". INT(.5!)*3 is a double whose exponent byte is 0 (the value 0) and whose digit bytes are 30 00 00 00 00 00 00 -- the other operand's (one case). | 8 | ✓ | ✗ 1: KMA FY 44 |
| **R-INT-TYPE** A string as the argument (a literal or a variable) is error 13 (Type mismatch), and so is assigning the result to a string variable: the result is a number. | 3 | ✓ | ✓ |
| **R-INT-OWNERR** An argument that fails to compute raises its own error (1/0: error 11). | 1 | ✓ | ✓ |
| **R-INT-SYNTAX** No argument, a second argument, no closing parenthesis, or the name without a parenthesis is error 2 (Syntax error); so are `PRINT INT` and `INT(1,2)`, the forms this page quotes. | 6 | ✓ | ✓ |
| **R-INT-ORDER** The argument is evaluated before the call's shape is checked, and its type after: INT(1/0 (no `)`) and INT(1/0,2) raise the argument's own error 11, but INT("A" (no `)`) and INT("A",2) are error 2 (Syntax error), not 13 -- the `)` is required before the string is refused. | 4 | ✓ | ✗ 2: KMA FY 15, KMA FY 17 |
| **R-INT-NEST** INT nested 16 and 32 deep (INT(INT(...(-2.5)...))) gives what the rules above give applied that many times, with no error. | 2 | ✓ | ✗ 2: KMA FZ 4, KMA FZ 5 |
| **R-INT-FORMS** Spaces before the parenthesis and around the argument are allowed, and a literal's own type is the argument's: 2.5 and -2.5 are singles, 7 an integer, 7% / 2.5! / 2.5# what they say, &H8000 the integer -32768, -32768 a single (a minus on the single 32768), -0 the integer 0, 1/4 a double; INT of INT(2.25) is INT of that result. Each gives what the rules above say for that type and value; so does INT(-1E38), a single. These types are MEASURED: each literal alone, `R=<literal>` / `Q=USR(<literal>)`, gives that type and value on both machines (KMA FY 70-92; the loader refuses a run where it does not). | 14 | ✓ | ✗ 1: KMA FX 55 |
| **R-INT-ASSIGN** `R=INT(x)` with R a double stores the result's value -- an integer by its value, a single's own 4 bytes then four zero bytes, its exponent byte and digit bytes as they are (so INT(.5!)'s exponent-0 result keeps its digit bytes in R: 00 50 00 00 00 00 00 00) -- and an error stores nothing (R keeps its sentinel). Read in every case that assigns R. | 177 | ✓ | ✗ 13: KMA MS INT .5, KMA MS INT .4, KMA MS INT .6, KMA MS INT .9, KMA MS INT .1, KMA MS INT .25 … (+7) |
| **R-INT-TARGET** Stored in an INTEGER variable, INT's result loses its fraction -- truncated, not rounded (SQR(3) stores 1) -- and a value outside -32768..32767 is error 6 (Overflow), the variable unchanged; stored in a SINGLE, a single keeps its own 4 bytes (an exponent-0 one its digit bytes too), an integer becomes its value, a double is cut to 6 digits (SQR(2): 1.41421). Read back through USR(T%) / USR(T!). | 5 | ✓ | ✗ 1: KMA FY 59 |

<!-- RULES END -->

## Differences from the reference

- **The result's type, for a negative argument with a fraction** (rule R-INT-NEGFRAC, 24 cases; R-INT-ODD, KMA FX 68;
  R-INT-FORMS, KMA FX 55 `INT(-2.5)`): the VG-8020 returns the integer -1 between -1 and 0 and a double below -1;
  zerobas keeps the argument's type -- [D-INTNEGTYPE](../../todo/open/D-INTNEGTYPE.md). The values agree. Nested, it
  carries through: `INT(INT(...(-2.5)...))` 16 and 32 deep is the double -3 there, the single -3 here (rule
  R-INT-NEST, KMA FZ 4, 5).
- **A zero result with digit bytes is stored in a variable as zero bytes here** (rule R-INT-ASSIGN, 13 cases:
  `R=INT(.5!)` and the like) -- [D-ZEROLET](../../todo/open/D-ZEROLET.md). `INT`'s own result agrees (R-INT-DOWN); it
  is the assignment of a single, to a double or to a single (rule R-INT-TARGET, KMA FY 59 `T!=INT(.5!)`).
- **`INT(.5!)*3` is a zero with digit bytes 30 00 ... on the VG-8020, 8 zero bytes here** (rule R-INT-ZEROUSE, KMA FY
  44) -- [D-ZEROMUL](../../todo/open/D-ZEROMUL.md). The value is 0 on both; it is the multiply's, not `INT`'s.
- **`INT("A"` (no `)`) and `INT("A",2)` are error 13 here, error 2 on the VG-8020** (rule R-INT-ORDER, KMA FY 15, 17)
  -- [D-ARGTYPEORDER](../../todo/open/D-ARGTYPEORDER.md).

The one rung not yet proven is **RAM usage**: `INT` uses the same amount of
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
- [A] Why `INT(.5!)+1` is a DOUBLE on both machines (KMA FY 43), and an exponent-0 zero in the operators not measured
  here (`-`, `/`, `^`, `\`, `MOD`): the operators region's.
- [A] Stored in an INTEGER variable, a NEGATIVE result with a fraction: truncated toward zero or rounded down is not
  separated (no such case; the conversion region, [CINT](CINT.md)). Stored in a SINGLE, a double that needs its 7th
  digit rounded or cut is not separated either (`SQR(2)`'s 7th digit is 3).

## What we found, and how

- **The result's type was assumed, not measured** (2026-11-24, D-KWSPEC's
  maths probe). This page said the result keeps the argument's type; read
  through a `USR` routine, the reference's `INT` of a negative number with a
  fraction is the integer −1 or a double
  ([D-INTNEGTYPE](../../todo/open/D-INTNEGTYPE.md)).
- **The tests could not see the result's precision** (found 2026-07-12, in the
  review of the first math slice). The double-precision path through `INT` was
  never exercised. zerobas turned out to be right — `INT(12345678.9#)` is
  12345678 and `INT(-9999999.5#)` is −10000000 on both machines — and those
  cases are now in the tests, so the behaviour is proven rather than trusted
  ([spec-basic-math-pack.md](../spec-basic-math-pack.md) §9.5).
- **Empty or malformed calls returned a number** (fixed 2026-07-13 and
  2026-07-14, D-F2-3 and D-F2-4). `INT()` printed 0, and `PRINT INT` or
  `INT(1,2)` quietly ran on whatever value was left over from earlier, where the
  VG-8020 says `Syntax error`:
  [spec-basic-empty-expr-syntax-error.md](../spec-basic-empty-expr-syntax-error.md),
  [spec-basic-malformed-call-syntax-error.md](../spec-basic-malformed-call-syntax-error.md).
- **The space before the parenthesis was checked** (D-NUMSPACE, 2026-09-09):
  `INT (7.9)` was already accepted, as on both references
  ([`numspace_run.out`](../../scratchpad/numspace_run.out)).
- **The whole error set was measured on the reference** (D-KWT6, 2026-09-27):
  wrong type, no argument, an extra argument and `INT(-1E38)`; zerobas matched
  every case ([`t6enum_run.out`](../../scratchpad/t6enum_run.out)).

## Where it lives

`evmc_int` in [basic/expr.asm](../../basic/expr.asm), reached from the math
selector `ev_ff_mathconv`; it truncates with `fp_trunc` in
[basic/float-arith.asm](../../basic/float-arith.asm) and subtracts 1 when a
negative number lost a fraction. [`FIX`](FIX.md) is the same code without that
last step. The design notes are in
[spec-basic-math-pack.md](../spec-basic-math-pack.md) §9.

## Related concepts

- [Numbers](../concepts/numbers.md) — integers, single and double precision

## Tests that cover it

- `make math-acceptance` — values and result types against the VG-8020,
  `INT` against `FIX` on both signs, and the empty and malformed calls.
- `make kwsweep` — the everyday row (`INT(1.7)`), the error rows for {2, 13},
  and the deliberately-broken-build check.
- `make kwram` — the RAM-usage comparison.
