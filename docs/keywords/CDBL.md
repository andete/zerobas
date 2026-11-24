<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->
<!-- example: reference=VG-8020 disk=no -->

# `CDBL` — convert a number to double precision

> **Spec:** DRAFT 1 (2026-11-24) — 133 cases measured on the Philips VG-8020 (BASIC's reference) and on
> zerobas, by typed BASIC ([`kconv.py`](../../probes/basic/spec/kconv.py)); every rule is executable and
> every recorded output is read by one. Goldfish pass 1 (2026-11-24) acted on ([the keyword plan](spec-plan.md)).
>
> **Status (2026-11-24):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✗ (`CDBL("A"` is error 13 here, 2 there). Two differences, found by the spec probe (below).
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`CDBL(x)` returns `x` as a double-precision number, the type `A#` holds:
fourteen significant digits. It widens an integer or a single-precision value;
nothing is rounded. zerobas gives the same results as the Philips VG-8020; it differs only for
a single whose bytes were POKEd (below).

## Syntax

```
CDBL(<numeric expression>)
```

One argument, always.

## Details

- **Widening adds no digits.** A single holds six digits, and `CDBL` of it
  still holds those six: `CDBL` of a single 1/3 is .333333, not
  .33333333333333. MSX keeps numbers in decimal, so the six digits come
  across exactly, with no binary noise added.
- **What follows is calculated in double precision.** `CDBL(1)/3` gives
  fourteen digits.
- **It sidesteps the integer edge**: `-CDBL(-32768)` is 32768, where the
  integer −32768 has no positive partner.
- **There is no range error**: `CDBL(1E38)` raises nothing on either
  machine.
- **A string argument** is `Type mismatch`.
- **No argument, or two** (`CDBL()`, `CDBL(1,1)`) is `Syntax error`.

| you write | you get |
|---|---|
| `CDBL(1)/3` | .33333333333333 |
| `-CDBL(-32768)` | 32768 |
| `CDBL(1E38)` | no error |
| `CDBL("A")` | error 13, `Type mismatch` |
| `CDBL()`, `CDBL(1,1)` | error 2, `Syntax error` |

The whole set of errors `CDBL` can raise is {2, 13}, the same on both
machines.

## Example

```
10 ON ERROR GOTO 80
20 A!=1/3
30 PRINT A!;CDBL(A!)
40 PRINT CDBL(1)/3
50 PRINT -CDBL(-32768)
60 PRINT CDBL("A")
70 END
80 PRINT "Error";ERR:RESUME NEXT
RUN
 .333333  .333333
 .33333333333333
 32768
Error 13
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_cdbl.out`](../../scratchpad/kwdoc_cdbl.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## The specification

Reference: the Philips VG-8020's MSX BASIC. Ours: zerobas on the diskless machine
(`C-BIOS_MSX1_EU_REPACK_NODISK`).

**How to read the rules below.** Every rule is a sentence AND a check
([`probes/basic/spec/cdbl_rules.py`](../../probes/basic/spec/cdbl_rules.py), model in
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
recorded before the call, so the rules work from the exact value given. Each case is evaluated twice: `R=CDBL(N)`,
with `R` a double whose 8 bytes are recorded, and `Q=USR(CDBL(N))`, where `USR` is the probe's own 18-byte routine:
by the MSX convention ([USR.md](USR.md)) it receives `CDBL`'s result unconverted in `DAC` with its type in `VALTYP`,
and copies both into the probe's memory -- so the result's TYPE (2 integer, 4 single, 8 double) and its own bytes
are seen. Before every case `R` holds -12345 and the type cell 255, so an error, which assigns nothing and never
reaches `USR`, cannot read as a result. An apparatus row per argument (no function) must hand `USR` the argument's
own type and bytes on both machines, and every row's recorded argument must be its `DATA` text's value, or the
loader refuses the run.
- **[KCV CI CDBL *n*]**, **[KCV CS CDBL *n*]**, **[KCV CD CDBL *n*]**: the argument an integer, a single or a double, *n*
  the `DATA` text. Integers: 0, 1, -1, 2, -2, 7, -7, 255, 12345, -12345, 32767, -32767, -32768. Singles: 0, -0, 1, -1, .5, -.5, 1.5, -1.5, 2.5, -2.5, 3.5, -3.5, .4, -.4, .6, -.6, .9, -.9, .499999, -.499999, 1.49999, 2.50001, -2.50001, 99.5, -99.5, 12345.6, -12345.6, 32766.5, 32767, 32767.4, 32767.5, 32767.9, 32768, -32768, -32768.4, -32768.5, -32768.9, -32769, 65535, 123456, 1E10, -1E10, 1E-10, 1E-64, -1E-64, 9.99999E62, -9.99999E62, 1.23456, 3.33333. Doubles: 0, -0, 1, -1, .5, -.5, 1.5, -1.5, 2.5, -2.5, .49999999999999, -.49999999999999, .50000000000001, 32766.5, 32767.49999999, 32767.5, 32767.99999999, -32768.49999999, -32768.5, -32768.99999999, 1.2345649999999, 1.234565, 1.2345650000001, -1.234565, -1.2345650000001, 1.2345655, 1.2345665, 9.9999949999999, 9.999995, -9.999995, 99999.95, 999999.5, 9999995, 1.23456789012345, .33333333333333, .66666666666667, 123456789.12345, 1D-64, -1D-64, 9.99999D62, 9.9999949999999D62, 9.999995D62, -9.999995D62, 9.9999999999999D62.
- **[KCV FX *i*]**: a fixed statement, `S$` = `"12"` (`FX` in the probe): a string literal or variable as the
  argument, the result assigned to `R$`, `1/0`, no argument, an extra one, no `)`, no parenthesis, `CDBL("A"` and
  `CDBL("A",2)`; the literals `2.5`, `-2.5`, `7`, `7%`, `2.5!`, `2.5#`, `&H8000`, `-32768`, `-0`, `1/3`; spaces;
  `CDBL(CDBL(2.5))`; a single `N!` assigned 1 whose exponent byte is then POKEd to 0 or `&H80` (digit bytes
  `10 00 00`); `CDBL(1!/3)` and `CDBL` of a single holding `.1`.
- **[KCV FY *i*]** (goldfish pass 1, 2026-11-24): a double POKEd to exponent byte 0 or `&H80` with digit bytes left in it; `F(1/0` and `F(1/0,2)`; `CINT(32768` and `CSNG(9.999995D62` (no `)`); the result stored in `Z%` and `Z!`; `CINT(40000.5)`; `CSNG(-9.9999999999999D62)`; `CSNG(1/3)` alone and times `3!`; five doubles stored in `Z!` beside CSNG; `CDBL` of a single holding 1/3; the type of `1!/3` (a double).

**Controls** ([`kconv_controls.py`](../../probes/basic/spec/kconv_controls.py)): each is a rival rule run over the
reference's cases: “a single widened through binary floating point” is FALSE on 21 of the 110 cases R-CDBL-WIDEN selects (e.g. KCV CS CDBL .4); “an exponent-0 single made a clean zero -- zerobas's” is FALSE on 2 of the 4 cases R-CDBL-ODD selects (e.g. KCV FX 73); “R given only the result's first 6 digits (stored through a single)” is FALSE on 31 of the 141 cases R-CDBL-ASSIGN selects (e.g. KCV CD CDBL .49999999999999).

<!-- RULES BEGIN -->
<!-- GENERATED by tools/spec_rules.py from probes/basic/spec/cdbl_rules.py -- do not edit; `python3 tools/spec_rules.py probes/basic/spec/cdbl_rules.py --write` -->

**9 rules; 9 hold on the reference. Of the 705 recorded outputs (each case's error from `R=F(x)` and from `Q=USR(F(x))`, R's 8 bytes, the result's type as USR saw it and the result's own bytes): 705 read by a rule's check, 0 declared NOT evidence (below), 0 unread.**

#### 1. The value

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-CDBL-WIDEN** The result is a DOUBLE: an integer's exact value; a single's 6 decimal digits followed by 8 zeros (CDBL(.499999!) is .49999900000000, CDBL of a single holding .1 is .10000000000000 -- nothing invented); a double unchanged. | 110 | ✓ | ✓ |

#### 2. Forms and errors

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-CDBL-TYPE** A string as the argument (a literal or a variable) is error 13 (Type mismatch), and so is assigning the result to a string variable. | 3 | ✓ | ✓ |
| **R-CDBL-OWNERR** An argument that fails to compute raises its own error (1/0: error 11). | 1 | ✓ | ✓ |
| **R-CDBL-SYNTAX** No argument, a second argument, no closing parenthesis, or the name without a parenthesis is error 2 (Syntax error). | 4 | ✓ | ✓ |
| **R-CDBL-ORDER** The argument is evaluated first -- its own error wins: CDBL(1/0 and CDBL(1/0,2) are error 11 --, then the `)` is required, before the type is checked or the conversion done: CDBL("A" and CDBL("A",2) are error 2, not 13. | 4 | ✓ | ✗ 2: KCV FX 58, KCV FX 59 |
| **R-CDBL-FORMS** Spaces before the parenthesis and around the argument are allowed; a literal's own type is the argument's (2.5 a single, 7 an integer, &H8000 the integer -32768, -32768 a single, -0 the integer 0, 1/3 a double -- kmath's measured literal types); CDBL(CDBL(2.5)) is CDBL of that result. | 13 | ✓ | ✓ |
| **R-CDBL-ODD** A single whose exponent byte is 0 or &H80 with digit bytes 10 00 00 is widened as any single: 00 10 00 00 00 00 00 00 and 80 10 00 00 00 00 00 00; such a double is returned as it is. | 4 | ✓ | ✗ 4: KCV FX 73, KCV FX 74, KCV FY 12, KCV FY 13 |

#### 3. The result stored

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-CDBL-STORE** Stored in a variable, CDBL's result is converted for it as any number is: `Z%=CDBL(2.7)` holds 2, `Z!=CDBL(1.234565#)` holds 1.23457. | 2 | ✓ | ✓ |
| **R-CDBL-ASSIGN** `R=CDBL(x)` with R a double stores the result as a double: an integer by its value, a single's 4 bytes then four zero bytes (an exponent-0 one too), a double's 8; after an error R keeps its sentinel -12345. Read in every case. | 141 | ✓ | ✓ |

<!-- RULES END -->

## Differences from the reference

- **`CDBL("A"` (no `)`) and `CDBL("A",2)` are error 13 here, error 2 on the VG-8020** (rule R-CDBL-ORDER, KCV FX 58, 59) -- [D-ARGTYPEORDER](../../todo/open/D-ARGTYPEORDER.md). The reference requires the `)` before it refuses the string.
- **A POKEd zero single** ([D-CONVZERO](../../todo/open/D-CONVZERO.md)): `CDBL` of a single whose exponent byte is 0 or `&H80` with digit bytes left in it is that single followed by four zero bytes on the reference and eight zero bytes here (rule R-CDBL-ODD, KCV FX 73, 74; a double such as that is returned as eight zero bytes too, KCV FY 12, 13). Only a POKE makes such a single.

The one rung not yet proven is **RAM usage**: `CDBL` uses the same amount of
free memory on both machines, but the two write different sets of work-area
cells while doing it. Nothing a program can observe through `FRE` differs.

## On later generations (MSX2, MSX2+)

[A] Not measured yet: the probe has not run on the MSX2 / MSX2+ references (spec-method §4).

## Open (not measured)

- [A] Direct mode: every case ran inside a program.
- [A] An argument's own error was measured with one kind (`1/0`, error 11).
- [A] Which work-area cells the call writes (the RAM-usage rung).
- [A] Non-canonical bytes other than the two measured singles: a double, non-BCD digit nibbles.
- [A] DAC's bytes beyond the result's own (an integer result leaves other bytes in DAC+0/+1: the reference the argument's, zerobas zeros) are not evidence -- a USR routine reading them is outside the contract.
- [A] A non-canonical result USED (`+1`, a comparison, `STR$`), and the late Overflow of D-CSNGOVERUSR in other enclosing forms (`PRINT`, `+0`, `ABS(...)`).
- [A] Nesting depth, and the type of mixed-type arithmetic (the operators' region).

## What we found, and how

- **The spec probe** (D-KWSPEC, 2026-11-24): a single is widened by its 6 decimal digits followed by 8 zeros (`CDBL` of a single holding .1 is .10000000000000) on every measured argument; a binary widening is refuted by the controls. One difference beyond D-ARGTYPEORDER: a POKEd zero single (D-CONVZERO).
- **`CDBL` shipped on 2026-07-12** with the first slice of the math pack,
  reusing the float pack's existing widening rather than a routine of its
  own ([spec-basic-math-pack.md](../spec-basic-math-pack.md) §9).
- **`CDBL()` printed 0** (fixed 2026-07-13, D-F2-3); the reference says
  `Syntax error`
  ([spec-basic-empty-expr-syntax-error.md](../spec-basic-empty-expr-syntax-error.md)).
- **A malformed call ran on a leftover value** (fixed 2026-07-14, D-F2-4),
  for all fifteen math functions at once; the reference says `Syntax error`
  ([spec-basic-malformed-call-syntax-error.md](../spec-basic-malformed-call-syntax-error.md)).
  For `CDBL` the extra-argument form `CDBL(1,1)` is measured; the bare `CDBL` and the unclosed `CDBL(5` are measured by the spec probe too (error 2 on both, R-CDBL-SYNTAX).
- **`-CDBL(-32768)` was the control** in the 2026-08-11 sweep of the
  integer −32768 (D-NEG8K): it already printed 32768 on both machines, which
  is what pinned the fault on the integer negate and not on minus in general
  ([fixpoint8000-msx1-sweep.md](../fixpoint8000-msx1-sweep.md)).
- **The complete error set was measured** on 2026-09-27: {2, 13} on both
  machines, and `CDBL(1E38)` raises nothing on either
  ([`t6enum_b2.out`](../../scratchpad/t6enum_b2.out)).

See also [`CSNG`](CSNG.md) (to single precision) and [`CINT`](CINT.md) (to an
integer).

## Where it lives

`evmc_cdbl` in [basic/expr.asm](../../basic/expr.asm): the argument is widened
and packed as a double by `round_and_finalize` in
[basic/float-arith.asm](../../basic/float-arith.asm).

## Related concepts

- [Numbers](../concepts/numbers.md) — integers, single and double precision

## Tests that cover it

- `make math-acceptance` — single, integer and double arguments, and the
  empty form `CDBL()`.
- `make float-acceptance` — `-CDBL(-32768)`.
- `make kwsweep` — the everyday row (`CDBL(1)/3`) and the error rows for
  {2, 13}.
- `make kwram` — the RAM-usage comparison.
