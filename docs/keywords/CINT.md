<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->
<!-- example: reference=VG-8020 disk=no -->

# `CINT` — convert a number to an integer

> **Spec:** DRAFT 1 (2026-11-24) — 133 cases measured on the Philips VG-8020 (BASIC's reference) and on
> zerobas, by typed BASIC ([`kconv.py`](../../probes/basic/spec/kconv.py)); every rule is executable and
> every recorded output is read by one. Not yet reviewed ([the keyword plan](spec-plan.md)).
>
> **Status (2026-11-24):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✗ (`CINT("A"` is error 13 here, 2 there). One difference, found by the spec probe (below).
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`CINT(x)` turns a number into an integer, the 16-bit type that `A%` holds,
range −32768 to 32767. On MSX it **truncates toward zero**: it drops the
fraction and does not round. zerobas gives the same results as the Philips
VG-8020; it differs only in one error code (below).

## Syntax

```
CINT(<numeric expression>)
```

One argument, always.

## Details

- **The fraction is dropped, toward zero.** `CINT(2.9)` is 2, `CINT(-2.9)` is
  −2, `CINT(3.7)` is 3. For a positive number that is the same answer as
  [`FIX`](FIX.md) and [`INT`](INT.md); for a negative one with a fraction,
  `INT` goes down (`INT(-2.5)` is −3) where `CINT` and `FIX` go toward zero
  (`CINT(-2.5)` is −2).
- **The range check looks at what is left after truncating.**
  `CINT(32767.6)` is 32767 and `CINT(-32768.6)` is −32768, both legal; only
  when the integer part itself is outside −32768 to 32767 (`CINT(32768)`,
  `CINT(-32769)`, `CINT(40000.5)`) is it `Overflow`.
- **The result is an integer**, so it prints without a fraction and stores
  into `A%` unchanged: `A%=CINT(3.7)` makes `A%` 3.
- **A string argument** is `Type mismatch`.
- **No argument, two arguments, no parentheses or a missing `)`** —
  `CINT()`, `CINT(1,1)`, `PRINT CINT`, `CINT(2` — are all `Syntax error`.

| you write | you get |
|---|---|
| `CINT(2.9)`, `CINT(2.5)` | 2 |
| `CINT(-2.9)` | −2 |
| `CINT(32767.6)` | 32767 |
| `CINT(-32768.6)` | −32768 |
| `CINT(32768)`, `CINT(-32769)` | error 6, `Overflow` |
| `CINT("A")` | error 13, `Type mismatch` |
| `CINT()`, `CINT(1,1)` | error 2, `Syntax error` |

The whole set of errors `CINT` can raise is {2, 6, 13}, the same on both
machines.

## Example

```
10 ON ERROR GOTO 80
20 PRINT CINT(2.9);CINT(-2.9)
30 PRINT CINT(32767.6);CINT(-32768.6)
40 A%=CINT(3.7):PRINT A%
50 PRINT CINT(32768)
60 PRINT CINT("A")
70 END
80 PRINT "Error";ERR:RESUME NEXT
RUN
 2 -2
 32767 -32768
 3
Error 6
Error 13
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_cint.out`](../../scratchpad/kwdoc_cint.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## The specification

Reference: the Philips VG-8020's MSX BASIC. Ours: zerobas on the diskless machine
(`C-BIOS_MSX1_EU_REPACK_NODISK`).

**How to read the rules below.** Every rule is a sentence AND a check
([`probes/basic/spec/cint_rules.py`](../../probes/basic/spec/cint_rules.py), model in
[`kconv_model.py`](../../probes/basic/spec/kconv_model.py), run by
[`tools/spec_rules.py`](../../tools/spec_rules.py); [docs/spec-method.md](../spec-method.md) §3a,
[the keyword plan](spec-plan.md)) over the measured cases it names.
- **reference:** ✓ means the check holds on EVERY case it selects of the VG-8020's run.
- **zerobas:** the cases where zerobas fails it, which are its differences.

The tables are generated from the checks, so a sentence here cannot say more than the data does.

**Evidence.** One probe, [`probes/basic/spec/kconv.py`](../../probes/basic/spec/kconv.py) (the conversion region's
first, on kmath's frame and record, [`kmath.py`](../../probes/basic/spec/kmath.py), and the shared RAM-record
harness [`ramrec.py`](../../probes/basic/spec/ramrec.py)), typed on both machines; run file
[`scratchpad/KCV_run1.out`](../../scratchpad/KCV_run1.out) (2026-11-24; zerobas's side on that day's build). The
argument is `READ` into a variable of the case's own type (`N%`, `N!` or `N#`) and that variable's own bytes are
recorded before the call, so the rules work from the exact value given. Each case is evaluated twice: `R=CINT(N)`,
with `R` a double whose 8 bytes are recorded, and `Q=USR(CINT(N))`, where `USR` is the probe's own 18-byte routine:
by the MSX convention ([USR.md](USR.md)) it receives `CINT`'s result unconverted in `DAC` with its type in `VALTYP`,
and copies both into the probe's memory -- so the result's TYPE (2 integer, 4 single, 8 double) and its own bytes
are seen. Before every case `R` holds -12345 and the type cell 255, so an error, which assigns nothing and never
reaches `USR`, cannot read as a result. An apparatus row per argument (no function) must hand `USR` the argument's
own type and bytes on both machines, and every row's recorded argument must be its `DATA` text's value, or the
loader refuses the run.
- **[KCV CI CINT *n*]**, **[KCV CS CINT *n*]**, **[KCV CD CINT *n*]**: the argument an integer, a single or a double, *n*
  the `DATA` text. Integers: 0, 1, -1, 2, -2, 7, -7, 255, 12345, -12345, 32767, -32767, -32768. Singles: 0, -0, 1, -1, .5, -.5, 1.5, -1.5, 2.5, -2.5, 3.5, -3.5, .4, -.4, .6, -.6, .9, -.9, .499999, -.499999, 1.49999, 2.50001, -2.50001, 99.5, -99.5, 12345.6, -12345.6, 32766.5, 32767, 32767.4, 32767.5, 32767.9, 32768, -32768, -32768.4, -32768.5, -32768.9, -32769, 65535, 123456, 1E10, -1E10, 1E-10, 1E-64, -1E-64, 9.99999E62, -9.99999E62, 1.23456, 3.33333. Doubles: 0, -0, 1, -1, .5, -.5, 1.5, -1.5, 2.5, -2.5, .49999999999999, -.49999999999999, .50000000000001, 32766.5, 32767.49999999, 32767.5, 32767.99999999, -32768.49999999, -32768.5, -32768.99999999, 1.2345649999999, 1.234565, 1.2345650000001, -1.234565, -1.2345650000001, 1.2345655, 1.2345665, 9.9999949999999, 9.999995, -9.999995, 99999.95, 999999.5, 9999995, 1.23456789012345, .33333333333333, .66666666666667, 123456789.12345, 1D-64, -1D-64, 9.99999D62, 9.9999949999999D62, 9.999995D62, -9.999995D62, 9.9999999999999D62.
- **[KCV FX *i*]**: a fixed statement, `S$` = `"12"` (`FX` in the probe): a string literal or variable as the
  argument, the result assigned to `R$`, `1/0`, no argument, an extra one, no `)`, no parenthesis, `CINT("A"` and
  `CINT("A",2)`; the literals `2.5`, `-2.5`, `7`, `7%`, `2.5!`, `2.5#`, `&H8000`, `-32768`, `-0`, `1/3`; spaces;
  `CINT(CINT(2.5))`; a single `N!` assigned 1 whose exponent byte is then POKEd to 0 or `&H80` (digit bytes
  `10 00 00`); `CINT(32767.5)` and `CINT(-32768.5)` as literals.

**Controls** ([`kconv_controls.py`](../../probes/basic/spec/kconv_controls.py)): each is a rival rule run over the
reference's cases: “rounded half away from zero” is FALSE on 39 of the 89 cases R-CINT-TRUNC selects (e.g. KCV CS CINT .5); “floor (as INT)” on 26 of 89 (KCV CS CINT -.5); “the range tested on the value before truncation” on 12 of the 106 cases R-CINT-TRUNC and R-CINT-RANGE select (KCV CS CINT 32767.4).

<!-- RULES BEGIN -->
<!-- GENERATED by tools/spec_rules.py from probes/basic/spec/cint_rules.py -- do not edit; `python3 tools/spec_rules.py probes/basic/spec/cint_rules.py --write` -->

**9 rules; 9 hold on the reference. Of the 665 recorded outputs (each case's error from `R=F(x)` and from `Q=USR(F(x))`, R's 8 bytes, the result's type as USR saw it and the result's own bytes): 665 read by a rule's check, 0 declared NOT evidence (below), 0 unread.**

#### 1. The value

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-CINT-TRUNC** The result is an INTEGER: the argument with its fraction dropped, toward zero -- CINT(2.5) is 2, CINT(-2.5) -2, CINT(.9) 0, CINT(-.9) 0, CINT(32767.9) 32767, CINT(-32768.9) -32768: no rounding. An integer is returned as it is; a single or double whose exponent byte is 0 or &H80 is 0. | 89 | ✓ | ✓ |
| **R-CINT-RANGE** When the truncated value is outside -32768..32767 -- 32768, -32769, 65535, 1E10, 9.99999E62 -- it is error 6 (Overflow), from `R=CINT(x)` and from `USR(CINT(x))` alike, before anything is assigned. | 17 | ✓ | ✓ |

#### 2. Forms and errors

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-CINT-TYPE** A string as the argument (a literal or a variable) is error 13 (Type mismatch), and so is assigning the result to a string variable. | 3 | ✓ | ✓ |
| **R-CINT-OWNERR** An argument that fails to compute raises its own error (1/0: error 11). | 1 | ✓ | ✓ |
| **R-CINT-SYNTAX** No argument, a second argument, no closing parenthesis, or the name without a parenthesis is error 2 (Syntax error). | 4 | ✓ | ✓ |
| **R-CINT-ORDER** The `)` is required before the argument's type is checked: CINT("A" (no `)`) and CINT("A",2) are error 2 (Syntax error), not 13. | 2 | ✓ | ✗ 2: KCV FX 8, KCV FX 9 |
| **R-CINT-FORMS** Spaces before the parenthesis and around the argument are allowed; a literal's own type is the argument's (2.5 a single, 7 an integer, &H8000 the integer -32768, -32768 a single, -0 the integer 0, 1/3 a double -- kmath's measured literal types); CINT(CINT(2.5)) is CINT of that result, and the literals 32767.5 and -32768.5 give 32767 and -32768. | 15 | ✓ | ✓ |
| **R-CINT-ODD** A single whose exponent byte is 0 or &H80 with digit bytes 10 00 00 is 0. | 2 | ✓ | ✓ |

#### 3. The result stored

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-CINT-ASSIGN** `R=CINT(x)` with R a double stores the result as a double: an integer by its value, a single's 4 bytes then four zero bytes (an exponent-0 one too), a double's 8; after an error R keeps its sentinel -12345. Read in every case. | 133 | ✓ | ✓ |

<!-- RULES END -->

## Differences from the reference

- **`CINT("A"` (no `)`) and `CINT("A",2)` are error 13 here, error 2 on the VG-8020** (rule R-CINT-ORDER, KCV FX 8, 9) -- [D-ARGTYPEORDER](../../todo/open/D-ARGTYPEORDER.md). The reference requires the `)` before it refuses the string.

The one rung not yet proven is **RAM usage**: `CINT` uses the same amount of
free memory on both machines, but the two write different sets of work-area
cells while doing it. Nothing a program can observe through `FRE` differs.

## On later generations (MSX2, MSX2+)

[A] Not measured yet: the probe has not run on the MSX2 / MSX2+ references (spec-method §4).

## Open (not measured)

- [A] Direct mode: every case ran inside a program.
- [A] An argument's own error was measured with one kind (`1/0`, error 11).
- [A] Which work-area cells the call writes (the RAM-usage rung).
- [A] Non-canonical bytes other than the two measured singles: a double, non-BCD digit nibbles.

## What we found, and how

- **The spec probe** (D-KWSPEC, 2026-11-24): truncation toward zero and the range checked after it hold on every measured argument, in every type (`CINT(32767.9)` 32767, `CINT(-32768.9)` -32768, `CINT(32768)` Overflow); rounding, floor and a range test before truncation are each refuted by the controls. One difference: `CINT("A"` shares D-ARGTYPEORDER.
- **`CINT` does not round, and our own design said it did** (corrected
  2026-07-12, when `CINT` first shipped with the math pack). The design text,
  written from general BASIC knowledge, said "rounds half-up". Measuring the
  VG-8020 showed `CINT(2.9)` is 2 and `CINT(32767.6)` is 32767 — plain
  truncation — so `CINT` became the same strict integer conversion the `\`
  and `MOD` operators already used. The correction is recorded in
  [spec-basic-math-pack.md](../spec-basic-math-pack.md) §9.
- **`CINT()` printed 0** (fixed 2026-07-13, D-F2-3). An empty argument was
  read as zero; the reference says `Syntax error`
  ([spec-basic-empty-expr-syntax-error.md](../spec-basic-empty-expr-syntax-error.md)).
- **A malformed call gave the wrong error** (fixed 2026-07-14, D-F2-4).
  `PRINT CINT`, `CINT(1,2)` and `CINT(2` ran the conversion on a leftover
  value and could answer `Overflow` or a number, where the reference says
  `Syntax error`. The fix covered all fifteen math functions at once
  ([spec-basic-malformed-call-syntax-error.md](../spec-basic-malformed-call-syntax-error.md)).
- **The complete error set was measured** on 2026-09-27, every way of getting
  the argument wrong in turn: {2, 6, 13}, identical on both machines
  ([`t6enum_b2.out`](../../scratchpad/t6enum_b2.out)).

### Related, but not about `CINT`

`CINT(-32768)` is the easiest way to get the integer −32768, and negating it
exposed two arithmetic faults: `-CINT(-32768)` printed −32768 where the
reference prints 32768, and `0-CINT(-32768)` had the opposite problem. Both
were in the minus operators and were fixed on 2026-08-11 (D-NEG8K,
[fixpoint8000-msx1-sweep.md](../fixpoint8000-msx1-sweep.md)).

## Where it lives

`evmc_cint` in [basic/expr.asm](../../basic/expr.asm); the conversion itself
is `fac_to_int_strict_reset` in
[basic/float-arith.asm](../../basic/float-arith.asm), shared with `\`, `MOD`
and the logical operators.

## Related concepts

- [Numbers](../concepts/numbers.md) — integers, single and double precision

## Tests that cover it

- `make math-acceptance` — truncation in both directions, the range edges,
  `Overflow`, storing into `A%`, and the malformed-call forms.
- `make kwsweep` — the everyday row (`CINT(1.7)`) and the error rows for
  {2, 6, 13}.
- `make kwram` — the RAM-usage comparison.
