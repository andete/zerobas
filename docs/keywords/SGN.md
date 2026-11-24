<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->
<!-- example: reference=VG-8020 disk=no -->

# `SGN` — the sign of a number

> **Spec:** DRAFT 1 (2026-11-24) — 160 cases measured on the Philips VG-8020 (BASIC's reference) and on
> zerobas, by typed BASIC ([`kmath.py`](../../probes/basic/spec/kmath.py)); every rule is executable and
> every recorded output is read by one. Not yet reviewed ([the keyword plan](spec-plan.md)).
>
> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. No known divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`SGN(x)` tells you the sign of `x`: −1 when it is negative, 0 when it is zero,
1 when it is positive. zerobas behaves exactly like the Philips VG-8020 for
every case we have measured, errors included.

## Syntax

```
SGN(<numeric expression>)
```

One argument, always.

## Details

- **Three possible answers**, whatever the size or type of the argument:
  `SGN(-5)` is −1, `SGN(0)` is 0, `SGN(2.5)` is 1, `SGN(-1E38)` is −1.
- **The result is an integer** in every case, whatever the argument's type
  (measured through the result's own type), so `SGN(2.5)+0.5` is 1.5, not 3.
- **A space before the parenthesis is allowed**: `SGN (7)` is 1.
- **A string argument** (`SGN("A")`) is `Type mismatch` (error 13).
- **No argument, two arguments, no parentheses or a missing `)`** —
  `SGN()`, `SGN(1,2)`, `PRINT SGN`, `SGN(1` — are all `Syntax error`
  (error 2).

| you write | you get |
|---|---|
| `SGN(-5)`, `SGN(-1E38)` | −1 |
| `SGN(0)` | 0 |
| `SGN(5)`, `SGN(2.5)` | 1 |
| `SGN("A")` | error 13, `Type mismatch` |
| `SGN()`, `SGN(1,2)` | error 2, `Syntax error` |

The whole set of errors `SGN` can raise is {2, 13}, the same on both machines.

## Example

```
10 PRINT SGN(-5);SGN(0);SGN(5)
20 PRINT SGN(-2.5);SGN(2.5)
30 PRINT SGN (7)
40 ON ERROR GOTO 70
50 PRINT SGN("A")
60 END
70 PRINT "Error";ERR:RESUME NEXT
RUN
-1  0  1
-1  1
 1
Error 13
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_sgn.out`](../../scratchpad/kwdoc_sgn.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## The specification

Reference: the Philips VG-8020's MSX BASIC. Ours: zerobas on the diskless machine
(`C-BIOS_MSX1_EU_REPACK_NODISK`).

**How to read the rules below.** Every rule is a sentence AND a check
([`probes/basic/spec/sgn_rules.py`](../../probes/basic/spec/sgn_rules.py), model in
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
recorded before the call, so the rules work from the exact value given. Each case is evaluated twice: `R=SGN(N)`,
with `R` a double whose 8 bytes are recorded, and `Q=USR(SGN(N))`, where `USR` is the probe's own 18-byte routine
(POKEd above `CLEAR`'s limit): by the MSX convention ([USR.md](USR.md)) it receives `SGN`'s result unconverted
in `DAC` with its type in `VALTYP`, and copies both into the probe's memory -- so the result's TYPE (2 integer, 4
single, 8 double) and its own bytes are seen, not only its value. Before every case `R` holds -12345 and the type cell
255, so an error, which assigns nothing and never reaches `USR`, cannot read as a result. An apparatus row per
argument (no function: `R=N`, `Q=USR(N)`) must hand `USR` the argument's own type and bytes on both machines, or the
loader refuses the run.
- **[KMA MI SGN *n*]**, **[KMA MS SGN *n*]**, **[KMA MD SGN *n*]**: the argument an integer, a single or a
  double, *n* the `DATA` text. Integers: 0, 1, -1, 2, -2, 3, 4, 5, -5, 9, 10, 16, 100, 255, 12345, -12345, 32767, -32767, -32768. Singles: 0, -0, 1, -1, .5, -.5, .4, -.4, .6, -.6, .9, -.9, .1, -.1, 1.5, -1.5, 1.9, -1.9, 2.5, -2.5, 2, 3, 4, 5, 9, 10, 16, .25, 2.25, 1.44, 99.9998, .999999, -.999999, 99999.5, -99999.5, 99999.9, -99999.9, 12345.6, -12345.6, 32767, 32767.5, -32767.5, 32768, -32768, -32768.5, -32769, 65535.5, 123456, -123456, 999999, -999999, 1E6, -1E6, 1E10, -1E10, 1E-10, -1E-10, 1E-6, -1E-6, 1.23456E-5, 1E-63, -1E-63, 1E-64, -1E-64, 9.99999E62, -9.99999E62. Doubles:
  0, -0, 1, -1, .5, -.5, .9, -.9, 1.5, -1.5, 2.5, -2.5, 2, 3, 5, 10, .25, 2.25, 99.99998, 32767.9, -32768.1, 32768, -32768, -32769, 65536.5, 1234567.5, -1234567.5, 12345678.9, -12345678.9, -9999999.5, .99999999999999, -.99999999999999, 1.9999999999999, -1.9999999999999, 9999999999999.5, -9999999999999.5, 1234567890123.4, -1234567890123.4, 12345678901234, -12345678901234, 1D14, -1D14, 1D20, -1D20, 1D-10, -1D-10, 1D-14, -1D-14, 1D-64, -1D-64, 9.9999999999999D62, -9.9999999999999D62.
- **[KMA FX *i*]**: a fixed statement, `S$` = `"12"`; the list, with what each one separates, is `FX` in the probe:
  a string literal or variable as the argument, the result assigned to `R$`, `1/0`, no argument, an extra one, no
  `)`, no parenthesis; the literals `2.5`, `-2.5`, `7`, `7%`, `2.5!`, `2.5#`, `&H8000`, `-32768`, `-0`, `1/4`;
  spaces; `SGN(SGN(2.25))`; and a single `N!` assigned 1 whose exponent byte is then POKEd to 0 or `&H80`
  (digit bytes `10 00 00`).

**Controls** ([`kmath_controls.py`](../../probes/basic/spec/kmath_controls.py)): each is a rival rule run over the reference's cases: “the result in the argument's own type” is FALSE on 118 of the 137 cases it selects (e.g. KMA MS SGN 0); “any exponent 0 a zero, the sign bit ignored” is FALSE on 1 of the 2 cases it selects (e.g. KMA FX 45).

<!-- RULES BEGIN -->
<!-- GENERATED by tools/spec_rules.py from probes/basic/spec/sgn_rules.py -- do not edit; `python3 tools/spec_rules.py probes/basic/spec/sgn_rules.py --write` -->

**7 rules; 7 hold on the reference. Of the 800 recorded outputs (each case's error from `R=F(x)` and from `Q=USR(F(x))`, R's 8 bytes, the result's type as USR saw it and the result's own bytes): 800 read by a rule's check, 0 declared NOT evidence (below), 0 unread.**

#### 1. SGN(x)

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-SGN-ALL** The result is always an INTEGER: -1 for a negative argument, 0 for zero, 1 for a positive one, in every argument type and size (1E-64 is 1, -9.99999E62 -1, -32768% -1). | 137 | ✓ | ✓ |
| **R-SGN-ODD** Only an exponent byte of exactly 0 is a zero: 00 10 00 00 gives 0, but 80 10 00 00 (the sign bit set, exponent 0) gives -1. | 2 | ✓ | ✓ |
| **R-SGN-TYPE** A string as the argument (a literal or a variable) is error 13 (Type mismatch), and so is assigning the result to a string variable: the result is a number. | 3 | ✓ | ✓ |
| **R-SGN-OWNERR** An argument that fails to compute raises its own error (1/0: error 11). | 1 | ✓ | ✓ |
| **R-SGN-SYNTAX** No argument, a second argument, no closing parenthesis, or the name without a parenthesis is error 2 (Syntax error). | 4 | ✓ | ✓ |
| **R-SGN-FORMS** Spaces before the parenthesis and around the argument are allowed, and a literal's own type is the argument's: 2.5 and -2.5 are singles, 7 an integer, 7% / 2.5! / 2.5# what they say, &H8000 the integer -32768, -32768 a single (a minus on the single 32768), -0 the integer 0, 1/4 a double; SGN of SGN(2.25) is SGN of that result. Each gives what the rules above say for that type and value. | 13 | ✓ | ✓ |
| **R-SGN-ASSIGN** `R=SGN(x)` with R a double stores the result's value -- a single's own 4 bytes then four zero bytes, its exponent byte and digit bytes as they are (so FIX(.5!)'s exponent-0 result keeps its digit bytes in R: 00 50 00 00 00 00 00 00) -- and an error stores nothing (R keeps its sentinel). Read in every case. | 160 | ✓ | ✓ |

<!-- RULES END -->

## Differences from the reference

None: zerobas agrees in every case measured.

The one rung not yet proven is **RAM usage**: `SGN` uses the same amount of
free memory on both machines, but the VG-8020 writes a few work-area cells
along the way that zerobas does not. Nothing a program can observe through
`FRE` or the documented variables differs.

## On later generations (MSX2, MSX2+)

[A] Not measured yet: the probe has not run on the MSX2 / MSX2+ references (spec-method §4).

## Open (not measured)

- [A] Direct mode: every case ran inside a program.
- [A] An argument's own error was measured with one kind (`1/0`, error 11); that any error of the argument wins is assumed.
- [A] Which work-area cells the call writes (the RAM-usage rung).
- [A] Non-canonical bytes other than the two measured singles (exponent byte 0 or `&H80` with digit bytes `10 00 00`): a double, non-BCD digit nibbles, `&H80` with zero digit bytes.

## What we found, and how

- **Empty or malformed calls returned a number** (fixed 2026-07-13 and
  2026-07-14, D-F2-3 and D-F2-4). `SGN()` printed 0, and `PRINT SGN` or
  `SGN(1,2)` quietly ran on whatever value was left over from earlier, where the
  VG-8020 says `Syntax error`:
  [spec-basic-empty-expr-syntax-error.md](../spec-basic-empty-expr-syntax-error.md),
  [spec-basic-malformed-call-syntax-error.md](../spec-basic-malformed-call-syntax-error.md).
- **A test that only looked at one sign could not catch much** (D-KWBREADTH,
  2026-09-13). The first test row read `SGN(-3)` alone, and a row that reads
  one sign passes on an implementation that never gives the other two. A row
  reading `SGN(-5);SGN(0);SGN(5)` now covers all three answers.
- **The space before the parenthesis was checked** (D-NUMSPACE, 2026-09-09):
  `SGN (7)` was already accepted, as on both references
  ([`numspace_run.out`](../../scratchpad/numspace_run.out)).
- **The whole error set was measured on the reference** (D-KWT6, 2026-09-27):
  wrong type, no argument, an extra argument and `SGN(-1E38)`; zerobas matched
  every case ([`t6enum_run.out`](../../scratchpad/t6enum_run.out)).

## Where it lives

`evmc_sgn` in [basic/expr.asm](../../basic/expr.asm), reached from the math
selector `ev_ff_mathconv`; the argument is read by `ev_mc_arg`, which all the
math functions share. Its sibling is [`ABS`](ABS.md). The design notes are in
[spec-basic-math-pack.md](../spec-basic-math-pack.md) §9.

## Tests that cover it

- `make math-acceptance` — values and result types against the VG-8020,
  including the empty and malformed calls.
- `make kwsweep` — the everyday rows (`SGN(-3)` and all three signs), the error
  rows for {2, 13}, and the deliberately-broken-build check.
- `make kwram` — the RAM-usage comparison.
