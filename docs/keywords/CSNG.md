<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->
<!-- example: reference=VG-8020 disk=no -->

# `CSNG` — convert a number to single precision

> **Spec:** DRAFT 1 (2026-11-24) — 132 cases measured on the Philips VG-8020 (BASIC's reference) and on
> zerobas, by typed BASIC ([`kconv.py`](../../probes/basic/spec/kconv.py)); every rule is executable and
> every recorded output is read by one. Goldfish pass 1 (2026-11-24) acted on ([the keyword plan](spec-plan.md)).
>
> **Status (2026-11-24):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✗ (`CSNG("A"` is error 13 here, 2 there). Three differences, found by the spec probe (below).
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`CSNG(x)` returns `x` as a single-precision number, the type `A!` holds: six
significant digits. A double-precision value (MSX's default type, fourteen
digits) is rounded to six. zerobas gives the same results as the Philips VG-8020; it differs only at
edges a program rarely meets (below).

## Syntax

```
CSNG(<numeric expression>)
```

One argument, always.

## Details

- **A double is rounded to six digits**, not cut: `CSNG(1.2345678#)` is
  1.23457 -- half up on the 7th digit, by size (`CSNG(-1.234565#)` is -1.23457). This is the same rounding that happens when a double is stored
  into a single variable (`A!=1.2345678#`).
- **An integer or a single argument is returned unchanged**, now typed single:
  `CSNG(5)` is 5.
- **A double that rounds past the largest number is `Overflow`**: `CSNG(9.999995D62)` is
  error 6, where `CSNG(9.9999949999999D62)` is 9.99999E+62; `CSNG(1E38)` raises nothing.
- **A string argument** is `Type mismatch`.
- **No argument, or two** (`CSNG()`, `CSNG(1,1)`) is `Syntax error`.

| you write | you get |
|---|---|
| `CSNG(1.2345678#)` | 1.23457 |
| `CSNG(5)` | 5 (single precision) |
| `CSNG(1E38)` | no error |
| `CSNG(9.999995D62)` | error 6, `Overflow` |
| `CSNG("A")` | error 13, `Type mismatch` |
| `CSNG()`, `CSNG(1,1)` | error 2, `Syntax error` |

The whole set of errors `CSNG` can raise is {2, 6, 13}, the same on both
machines.

## Example

```
10 ON ERROR GOTO 80
20 A#=1.23456789#
30 PRINT A#;CSNG(A#)
40 PRINT 2/3
50 PRINT CSNG(2/3)
60 PRINT CSNG("A")
70 END
80 PRINT "Error";ERR:RESUME NEXT
RUN
 1.23456789  1.23457
 .66666666666667
 .666667
Error 13
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_csng.out`](../../scratchpad/kwdoc_csng.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## The specification

Reference: the Philips VG-8020's MSX BASIC. Ours: zerobas on the diskless machine
(`C-BIOS_MSX1_EU_REPACK_NODISK`).

**How to read the rules below.** Every rule is a sentence AND a check
([`probes/basic/spec/csng_rules.py`](../../probes/basic/spec/csng_rules.py), model in
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
recorded before the call, so the rules work from the exact value given. Each case is evaluated twice: `R=CSNG(N)`,
with `R` a double whose 8 bytes are recorded, and `Q=USR(CSNG(N))`, where `USR` is the probe's own 18-byte routine:
by the MSX convention ([USR.md](USR.md)) it receives `CSNG`'s result unconverted in `DAC` with its type in `VALTYP`,
and copies both into the probe's memory -- so the result's TYPE (2 integer, 4 single, 8 double) and its own bytes
are seen. Before every case `R` holds -12345 and the type cell 255, so an error, which assigns nothing and never
reaches `USR`, cannot read as a result. An apparatus row per argument (no function) must hand `USR` the argument's
own type and bytes on both machines, and every row's recorded argument must be its `DATA` text's value, or the
loader refuses the run.
- **[KCV CI CSNG *n*]**, **[KCV CS CSNG *n*]**, **[KCV CD CSNG *n*]**: the argument an integer, a single or a double, *n*
  the `DATA` text. Integers: 0, 1, -1, 2, -2, 7, -7, 255, 12345, -12345, 32767, -32767, -32768. Singles: 0, -0, 1, -1, .5, -.5, 1.5, -1.5, 2.5, -2.5, 3.5, -3.5, .4, -.4, .6, -.6, .9, -.9, .499999, -.499999, 1.49999, 2.50001, -2.50001, 99.5, -99.5, 12345.6, -12345.6, 32766.5, 32767, 32767.4, 32767.5, 32767.9, 32768, -32768, -32768.4, -32768.5, -32768.9, -32769, 65535, 123456, 1E10, -1E10, 1E-10, 1E-64, -1E-64, 9.99999E62, -9.99999E62, 1.23456, 3.33333. Doubles: 0, -0, 1, -1, .5, -.5, 1.5, -1.5, 2.5, -2.5, .49999999999999, -.49999999999999, .50000000000001, 32766.5, 32767.49999999, 32767.5, 32767.99999999, -32768.49999999, -32768.5, -32768.99999999, 1.2345649999999, 1.234565, 1.2345650000001, -1.234565, -1.2345650000001, 1.2345655, 1.2345665, 9.9999949999999, 9.999995, -9.999995, 99999.95, 999999.5, 9999995, 1.23456789012345, .33333333333333, .66666666666667, 123456789.12345, 1D-64, -1D-64, 9.99999D62, 9.9999949999999D62, 9.999995D62, -9.999995D62, 9.9999999999999D62.
- **[KCV FX *i*]**: a fixed statement, `S$` = `"12"` (`FX` in the probe): a string literal or variable as the
  argument, the result assigned to `R$`, `1/0`, no argument, an extra one, no `)`, no parenthesis, `CSNG("A"` and
  `CSNG("A",2)`; the literals `2.5`, `-2.5`, `7`, `7%`, `2.5!`, `2.5#`, `&H8000`, `-32768`, `-0`, `1/3`; spaces;
  `CSNG(CSNG(2.5))`; a single `N!` assigned 1 whose exponent byte is then POKEd to 0 or `&H80` (digit bytes
  `10 00 00`); `CSNG(1/3)*3`.
- **[KCV FY *i*]** (goldfish pass 1, 2026-11-24): a double POKEd to exponent byte 0 or `&H80` with digit bytes left in it; `F(1/0` and `F(1/0,2)`; `CINT(32768` and `CSNG(9.999995D62` (no `)`); the result stored in `Z%` and `Z!`; `CINT(40000.5)`; `CSNG(-9.9999999999999D62)`; `CSNG(1/3)` alone and times `3!`; five doubles stored in `Z!` beside CSNG; `CDBL` of a single holding 1/3; the type of `1!/3` (a double).

**Controls** ([`kconv_controls.py`](../../probes/basic/spec/kconv_controls.py)): each is a rival rule run over the
reference's cases: “the 7th digit and beyond dropped (truncation)” is FALSE on 20 of the 103 cases R-CSNG-ROUND selects (e.g. KCV CD CSNG .49999999999999); “rounded half to even” is FALSE on 2 of the 103 cases R-CSNG-ROUND selects (e.g. KCV CD CSNG 1.234565); “no carry into the exponent (truncation)” is FALSE on 4 of the 4 cases R-CSNG-OVER selects (e.g. KCV CD CSNG 9.999995D62); “an exponent-0 single made a clean zero -- zerobas's” is FALSE on 4 of the 4 cases R-CSNG-ODD selects (e.g. KCV FX 48); “an exponent-0 single stored in R as 8 zero bytes -- D-ZEROLET” is FALSE on 4 of the 147 cases R-CSNG-ASSIGN selects (e.g. KCV FX 48).

<!-- RULES BEGIN -->
<!-- GENERATED by tools/spec_rules.py from probes/basic/spec/csng_rules.py -- do not edit; `python3 tools/spec_rules.py probes/basic/spec/csng_rules.py --write` -->

**12 rules; 12 hold on the reference. Of the 735 recorded outputs (each case's error from `R=F(x)` and from `Q=USR(F(x))`, R's 8 bytes, the result's type as USR saw it and the result's own bytes): 735 read by a rule's check, 0 declared NOT evidence (below), 0 unread.**

#### 1. The value

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-CSNG-ROUND** The result is a SINGLE. An integer gives its exact value; a single is returned unchanged; a double's 14 digits are cut to 6 and the magnitude rounded half up on the 7th digit (1.2345649999999 -> 1.23456, 1.234565 -> 1.23457, -1.234565 -> -1.23457, .49999999999999 -> .5), a carry moving into the exponent (9.999995 -> 10, 999999.5 -> 1000000). | 103 | ✓ | ✓ |
| **R-CSNG-OVER** A double that rounds past the largest exponent -- 9.999995D62, 9.9999999999999D62 and their negatives -- is error 6 (Overflow), from `R=CSNG(x)` and from `USR(CSNG(x))` alike: USR is not reached (its type cell stays 255). | 4 | ✓ | ✗ 4: KCV CD CSNG 9.999995D62, KCV CD CSNG -9.999995D62, KCV CD CSNG 9.9999999999999D62, KCV FY 21 |
| **R-CSNG-LET** Storing a double in a single variable rounds it the same way: `Z!=1.2345649999999#` is 1.23456, `Z!=1.234565#` 1.23457, `Z!=-1.234565#` -1.23457, `Z!=9.9999949999999D62` 9.99999E+62; `Z!=9.999995D62` is error 6 and Z! keeps the value it had. | 5 | ✓ | ✓ |
| **R-CSNG-USE** CSNG(1/3) is the single .333333; in arithmetic it counts with its 6 digits: CSNG(1/3)*3 and CSNG(1/3)*3! are .999999 -- a DOUBLE, even the product of two singles (the operators' region states why). | 3 | ✓ | ✓ |

#### 2. Forms and errors

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-CSNG-TYPE** A string as the argument (a literal or a variable) is error 13 (Type mismatch), and so is assigning the result to a string variable. | 3 | ✓ | ✓ |
| **R-CSNG-OWNERR** An argument that fails to compute raises its own error (1/0: error 11). | 1 | ✓ | ✓ |
| **R-CSNG-SYNTAX** No argument, a second argument, no closing parenthesis, or the name without a parenthesis is error 2 (Syntax error). | 4 | ✓ | ✓ |
| **R-CSNG-ORDER** The argument is evaluated first -- its own error wins: CSNG(1/0 and CSNG(1/0,2) are error 11 --, then the `)` is required, before the type is checked or the conversion done: CSNG("A" and CSNG("A",2) are error 2, not 13, and CSNG(9.999995D62 is 2, not 6. | 5 | ✓ | ✗ 2: KCV FX 33, KCV FX 34 |
| **R-CSNG-FORMS** Spaces before the parenthesis and around the argument are allowed; a literal's own type is the argument's (2.5 a single, 7 an integer, &H8000 the integer -32768, -32768 a single, -0 the integer 0, 1/3 a double -- kmath's measured literal types); CSNG(CSNG(2.5)) is CSNG of that result. | 13 | ✓ | ✓ |
| **R-CSNG-ODD** A single whose exponent byte is 0 or &H80 with digit bytes 10 00 00 is returned as it is -- 00 10 00 00 and 80 10 00 00, a single, not made a clean zero; such a double gives its first 4 bytes. | 4 | ✓ | ✗ 4: KCV FX 48, KCV FX 49, KCV FY 6, KCV FY 7 |

#### 3. The result stored

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-CSNG-STORE** Stored in a variable, CSNG's result is converted for it as any number is: `Z%=CSNG(2.7)` holds 2, `Z!=CSNG(1.234565#)` holds 1.23457. | 2 | ✓ | ✓ |
| **R-CSNG-ASSIGN** `R=CSNG(x)` with R a double stores the result as a double: an integer by its value, a single's 4 bytes then four zero bytes (an exponent-0 one too), a double's 8; after an error R keeps its sentinel -12345. Read in every case. | 147 | ✓ | ✓ |

<!-- RULES END -->

## Differences from the reference

- **`CSNG("A"` (no `)`) and `CSNG("A",2)` are error 13 here, error 2 on the VG-8020** (rule R-CSNG-ORDER, KCV FX 33, 34) -- [D-ARGTYPEORDER](../../todo/open/D-ARGTYPEORDER.md). The reference requires the `)` before it refuses the string.
- **`CSNG` of a double that rounds past the largest exponent runs an enclosing `USR` routine before its `Overflow` here** ([D-CSNGOVERUSR](../../todo/open/D-CSNGOVERUSR.md)): `Q=USR(CSNG(9.999995D62))` is error 6 on both machines, but zerobas calls the routine first (with a double zero); the reference raises the error inside CSNG (rule R-CSNG-OVER, KCV CD CSNG 9.999995D62, -9.999995D62, 9.9999999999999D62, KCV FY 21). `R=CSNG(x)` is the same on both.
- **A POKEd zero single** ([D-CONVZERO](../../todo/open/D-CONVZERO.md)): `CSNG` of a single whose exponent byte is 0 or `&H80` with digit bytes left in it returns it unchanged on the reference and a clean zero here -- of type DOUBLE for 80 10 00 00 (rule R-CSNG-ODD, KCV FX 48, 49; a double such as that, KCV FY 6, 7). Only a POKE makes such a single.

The one rung not yet proven is **RAM usage**: `CSNG` uses the same amount of
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

- **The spec probe** (D-KWSPEC, 2026-11-24): a double is rounded half up on its 7th digit, by magnitude, and a carry can reach the exponent -- so `CSNG(9.999995D62)` is `Overflow` (error 6) on both machines. This page said before that `CSNG` had no range error and an error set {2, 13}; the probe refuted both. zerobas differs at that overflow inside `USR` (D-CSNGOVERUSR) and on a POKEd zero single (D-CONVZERO).
- **`CSNG` shipped on 2026-07-12** with the first slice of the math pack,
  reusing the rounding that storing into a single variable already does, so
  the two cannot disagree
  ([spec-basic-math-pack.md](../spec-basic-math-pack.md) §9).
- **`CSNG()` printed 0** (fixed 2026-07-13, D-F2-3); the reference says
  `Syntax error`
  ([spec-basic-empty-expr-syntax-error.md](../spec-basic-empty-expr-syntax-error.md)).
- **A malformed call ran on a leftover value** (fixed 2026-07-14, D-F2-4),
  for all fifteen math functions at once; the reference says `Syntax error`
  ([spec-basic-malformed-call-syntax-error.md](../spec-basic-malformed-call-syntax-error.md)).
  For `CSNG` the extra-argument form `CSNG(1,1)` is measured; the bare `CSNG` and the unclosed `CSNG(5` are measured by the spec probe too (error 2 on both, R-CSNG-SYNTAX).
- **The complete error set was measured** on 2026-09-27: {2, 13} on both machines -- it missed the Overflow of a double that rounds past the largest number (the spec probe found it, so the set is {2, 6, 13}) -- and `CSNG(1E38)` raises nothing on either
  ([`t6enum_b2.out`](../../scratchpad/t6enum_b2.out)).

See also [`CDBL`](CDBL.md) (to double precision) and [`CINT`](CINT.md) (to an
integer).

## Where it lives

`evmc_csng` in [basic/expr.asm](../../basic/expr.asm); the rounding is
`round_single_and_pack` in [basic/float-arith.asm](../../basic/float-arith.asm),
the same routine a store into a single variable uses.

## Related concepts

- [Numbers](../concepts/numbers.md) — integers, single and double precision

## Tests that cover it

- `make math-acceptance` — rounding of doubles, integer arguments, and the
  empty form `CSNG()`.
- `make kwsweep` — the everyday row (`CSNG(1.5)`) and the error rows for {2, 13} (the Overflow, error 6, is the spec probe's: R-CSNG-OVER).
- `make kwram` — the RAM-usage comparison.
