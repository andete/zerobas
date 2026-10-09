<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# Numbers — integers, single and double precision

> **Status (2026-10-09):** number types, literals, arithmetic, conversions and
> printed output agree with the VG-8020 in every measured case, apart from
> deliberate last-digit differences where zerobas is the more accurate side
> (long divisors, `SQR` and the other maths functions). Open: an `&B` number in
> a program is `Syntax error` here (D-AMPB, TIER 1), `RESUME NEXT` after an
> `Overflow` (D-RESNEXTOVF, TIER 3, below) and `TAN(1E38)` (TIER 6).
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

MSX BASIC has three kinds of number: **integers** (`A%`, −32768 to 32767),
**single precision** (`A!`, 6 significant digits) and **double precision**
(`A#`, 14 significant digits). Single and double are decimal floating point:
the digits are stored in BCD, so `0.1` is exactly 0.1 and there is no binary
rounding noise. A variable without a suffix is **double precision**, and every
calculation with a fraction in it is done in double precision. Integers
truncate, single precision rounds: `A%=1.7` stores 1, `A!=1234567` stores
1234570.

zerobas follows the Philips VG-8020 in all of this. Where it does not, it is
because zerobas computes the correctly rounded last digit and the reference
does not; those differences are listed below.

## How it works

### The three types

| type | suffix | holds | bytes | example |
|---|---|---|---|---|
| integer | `%` | −32768 to 32767, whole numbers | 2 | `A%=-5` |
| single precision | `!` | 6 significant digits | 4 | `A!=1.5` |
| double precision | `#`, or none | 14 significant digits | 8 | `A=1/3` |

Both float types reach from 1E-64 up to just below 1E+63. They share one
published layout — the bytes a variable holds (`PEEK(VARPTR(A!))` onward), a
literal in a stored line, and [`MKS$`](../keywords/MKS$.md) /
[`MKD$`](../keywords/MKD$.md):

- **byte 0**: bit 7 is the sign, bits 0–6 the decimal exponent plus 64; a
  byte 0 of 0 means zero, whatever follows;
- **bytes 1–3 (single) or 1–7 (double)**: the mantissa, two decimal digits per
  byte (packed BCD), normalised to lie between .1 and 1.

So 1.5, which is .15 times 10, is 65, `&H15`, 0, 0. An integer is two bytes, low byte
first, two's complement.

### How a literal is typed

The type is decided when the line is typed, by counting digits (leading zeros
excluded, trailing zeros included):

| you type | type | why |
|---|---|---|
| `5`, `32767` | integer | no point, no exponent, at most 5 digits and ≤ 32767 |
| `40000`, `999999` | single | too big for an integer, at most 6 digits |
| `1000000` | double | 7 or more digits |
| `3.14159`, `1E6` | single | a point or an `E` exponent, at most 6 digits |
| `3.141592` | double | 7 or more digits |
| `1D6`, `1#` / `1!` / `5%` | double / single / integer | a `D` exponent or a suffix decides |
| `&HFF`, `&O17` | integer | hexadecimal and octal, 16 bits |

- **Rounding to the type is half-up**: `1234567!` is stored as 1234570. A carry
  through all six digits of a single is not renormalised, so `9999995!` becomes
  1000000, not 10000000 — on the VG-8020 too, and zerobas reproduces it.
- **`&H` and `&O` are 16-bit patterns**: `&HFF` is 255; `&H8000` and above read
  as negative (`&HD000` is −12288).
- **`&B` is not a token on MSX1**: `&B101` in a program line is stored as the
  typed characters on both machines — but the VG-8020 reads it when the line
  runs (`PRINT &B101` is 5, `&B1111111111111111` is −1) and zerobas says
  `Syntax error` (D-AMPB, open, TIER 1;
  [`ampb_run.out`](../../scratchpad/ampb_run.out)). `VAL("&B101")` is 5 on
  both, and so is `&B101` read from `DATA`.
- **Out of range**: `1E63` and `65535%` are `Overflow` (error 6) before
  anything on the typed line runs; `1E-65` silently becomes 0. A suffix after
  an exponent (`1E10#`) derails the line on both machines.

### Arithmetic

- **Integer `+`, `-` and `*` stay integer**, and a result that leaves the
  integer range is promoted, exactly: `32767*32767` is 1073676289.
- **Everything else is double precision**: with one single or double operand,
  both are widened and the result is a double. `2!/3!` prints
  `.66666666666667`, and `/` is always real division (`7/2` is 3.5).
- **`\` and `MOD` are integer operations**: operands are truncated toward zero
  and must lie between −32768 and 32767, else `Overflow`. `-7\2` is −3, and
  `MOD` takes the dividend's sign (`-7 MOD 2` is −1). `AND`, `OR`, `XOR`,
  `NOT`, `EQV` and `IMP` convert their operands the same way.
- **`^`** gives a double and binds tighter than a leading minus (`-2^2` is −4).
  **Comparisons** give −1 or 0, floats compared as floats; `IF .5 THEN` is taken.
- **Rounding** is half-up on the 15th digit, except that a subtraction exactly
  halfway rounds toward zero (`2-5E-14` is 1.9999999999999) — the reference's
  behaviour, reproduced on purpose.
- **Overflow** (error 6) is decided from the operands' exponents before
  normalising: `2E62*4` is `Overflow` although 8E62 would fit. A result too
  small to hold becomes 0 without an error.
- **Division by zero** (error 11) for `/`, `\` and `MOD` at every precision,
  and for `0^-1`. A numeric error stops the statement: `PRINT "[";1/0;"]"`
  prints the `[`, then the error.

### Conversions: truncation and rounding

| conversion | rule | example |
|---|---|---|
| store into `%`, `CINT`, `FIX` | truncate toward zero | `A%=-1.7` → −1 |
| `INT` | round down | `INT(-1.7)` → −2 |
| store into `!`, `CSNG` | round half-up to 6 digits | `A!=2/3` → .666667 |
| store into `#`, `CDBL` | exact; widening adds no digits | `CDBL` of a single 1/3 → .333333 |
| statement arguments that are addresses (`POKE`, `PEEK`, `HEX$`) | −32768 to 65535, then truncate | `POKE 40000.5,1` writes address 40001 |

An integer store outside −32768 to 32767 is `Overflow`, as is `CINT(32768)`;
a string into a numeric variable, or the reverse, is `Type mismatch` (error 13).
In the address range a value of 32768 or more is wrapped negative before it is
truncated, so a fraction there rounds up: `HEX$(40000.1)` is `9C41` on both
machines.

### How numbers print

`PRINT` (and [`STR$`](../keywords/STR$.md), without the trailing space) writes:

- **a leading space or `-`**, the digits, **one trailing space**: `PRINT 1;-2`
  shows ` 1 -2 `;
- **no leading zero, no trailing zeros, no point for whole numbers**: `.5`,
  `1` (typed as `1.0`); up to 6 significant digits for a single, 14 for a
  double;
- **plain form from .01 up to below 1E14** (`.01`, `10000000000000`), **`E`
  notation outside it** with a signed two-digit exponent: `.001` prints
  `1E-03`, `6.023E23` prints `6.023E+23`. `D` is never printed.

A number that would not fit at the end of the line moves whole to the next
line; [`PRINT USING`](../keywords/PRINT.md) formats through a template.

## Example

```
10 PRINT 1/3;7/2;7\2
20 A!=1/3:A%=-1.7:PRINT A!;A%;INT(-1.7)
30 PRINT 32767*32767;&HFF;&O17
40 PRINT .01;.001;1E13;1E14
50 B!=1.5:V=VARPTR(B!)
60 FOR I=0 TO 3:PRINT PEEK(V+I);:NEXT
70 PRINT:ON ERROR GOTO 100
80 PRINT 1/0
90 PRINT 1E62*9
95 END
100 PRINT "Error";ERR:RESUME NEXT
RUN
 .33333333333333  3.5  3
 .333333 -1 -2
 1073676289  255  15
 .01  1E-03  10000000000000  1E+14
 65  21  0  0
Error 11
Error 6
```

Line 60 reads the four bytes of the single 1.5; line 90 is `Overflow` because
the exponents of 1E62 and 9 add up to more than 63.
Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_numbers.out`](../../scratchpad/kwdoc_numbers.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

- **`RESUME NEXT` after an `Overflow` skips the rest of the line** (D-RESNEXTOVF,
  found 2026-10-09, open, TIER 3). After a trapped `Overflow` in the first
  statement of `PRINT 1E62*9:PRINT "A"`, the VG-8020 resumes at `PRINT "A"`;
  zerobas goes on at the next line. Division by zero, `SQR(-1)` and a direct
  `ERROR 6` resume correctly on both
  ([`resnext_run.out`](../../scratchpad/resnext_run.out)). This is why the
  example keeps its `END` on a line of its own.
- **Division by a long divisor: the last digit.** zerobas rounds correctly;
  the VG-8020 is a few units low in the 14th digit once the divisor has more
  than 10 significant digits (`2/1.4142135623731`: …731 here, …729 there).
  Copying it was tried on 2026-07-13 and stopped at about 80 %: the deciding
  digit lies below the 14 the machine prints. Joost decided the same day to
  keep correct rounding and record the difference
  ([spec-basic-math-pack.md](../spec-basic-math-pack.md) §10.3.1).
- **The maths functions' last digits**, deliberate and described on each page:
  [`SQR`](../keywords/SQR.md) is correctly rounded, [`EXP`](../keywords/EXP.md)
  and [`LOG`](../keywords/LOG.md) stay within two units of the true value
  (the VG-8020 is 330 units off at `EXP(-50)`), [`SIN`](../keywords/SIN.md),
  [`COS`](../keywords/COS.md) and [`TAN`](../keywords/TAN.md) reduce the angle
  with more digits, and [`ATN`](../keywords/ATN.md) differs by one unit either
  way. `EXP` of a large negative argument is 0 here where the VG-8020 says
  `Overflow` (between about −149.7 and −297, and `EXP(-1E30)`).
- **`READ` of a number** (fixed 2026-10-09, D-READFLT): `DATA 1.5`, `2E3` and
  `-.25` were `Syntax error` here and `DATA 40000` read back as −25536, because
  `READ` parsed integers only. It now uses the same number reader as
  [`INPUT`](../keywords/INPUT.md) and `VAL`
  ([`readflt_after.out`](../../scratchpad/readflt_after.out)).
- **Open, `TAN(1E38)`**: `Overflow` on the VG-8020, a number here (D-TANBIG, TIER 6).
- **RAM usage** is not proven: same free memory used, different work-area
  cells written.

## What we found, and how

- **The default type is double, and single is only a storage format**
  (2026-07-11/12): `A=1/3` and even `2!/3!` print fourteen digits on the
  VG-8020 ([spec-basic-float-core.md](../spec-basic-float-core.md) §10.1, §11.1).
- **`CINT` truncates; our own design said it rounds** (corrected 2026-07-12).
- **A halfway subtraction rounds toward zero** (fixed 2026-07-13): the
  reference decides by the signs of the operands, not by the `+` or `-` typed
  ([spec-float-subtract-tie-compat.md](../spec-float-subtract-tie-compat.md)).
- **−32768 has no positive partner** (fixed 2026-08-11, D-NEG8K):
  `-CINT(-32768)` must promote to 32768 while `0-CINT(-32768)` wraps to −32768
  ([fixpoint8000-msx1-sweep.md](../fixpoint8000-msx1-sweep.md)).
- **"Differs in the last digit only" was the reference being wrong**
  (2026-09-01, D-MATHACC): scored against a 60-digit oracle, the VG-8020's
  `EXP` is up to 330 units off and zerobas's within half a unit
  ([spec-basic-mathacc.md](../spec-basic-mathacc.md)).

## How zerobas does it

A literal is converted once, when the line is typed: `tk_float` in
[sub/tkfloat.asm](../../sub/tkfloat.asm) applies the digit-count rules and
emits token `$1D` + 4 value bytes or `$1F` + 8; `&H`/`&O` become `$0C`/`$0B` +
16 bits ([basic/tokenise.inc](../../basic/tokenise.inc)). At run time integers
stay on a 16-bit path; floats use the accumulator, which is the published `DAC`
at `&HF7F6`, where `USR` machine code finds its argument.
[basic/float-arith.asm](../../basic/float-arith.asm) holds `fp_add`, `fp_sub`,
`fp_mul` and `fp_div` (unpacked 14-digit mantissas plus a guard digit),
`round_and_finalize`, the subtraction tie rule `fpa_sub_finalize`, the
exponent-sum check `check_preexp_bounds`, and the two integer conversions
`fac_to_int_strict` / `fac_to_int_addr`; `round_single_and_pack` serves both
`CSNG` and a store into a single variable, so they cannot disagree. The
formatter is `flt_fmt` in [basic/float.asm](../../basic/float.asm), writing
into the published `FBUFFR`. The maths functions and `^` run in the sub-ROM
(`sub/fp_*.asm`) with the project's own constants, never the reference's.
The design record is [spec-basic-float-core.md](../spec-basic-float-core.md),
[spec-basic-math-pack.md](../spec-basic-math-pack.md) and
[spec-basic-mathpack-slice2.md](../spec-basic-mathpack-slice2.md); where an
early section there disagrees with this page, this page is current.

## Related pages

- Keywords: [`CINT`](../keywords/CINT.md), [`CSNG`](../keywords/CSNG.md),
  [`CDBL`](../keywords/CDBL.md), [`INT`](../keywords/INT.md),
  [`FIX`](../keywords/FIX.md), [`MOD`](../keywords/MOD.md),
  [`VAL`](../keywords/VAL.md), [`STR$`](../keywords/STR$.md),
  [`PRINT`](../keywords/PRINT.md), [`READ`](../keywords/READ.md).
- Concepts: [variables.md](variables.md), [program-text.md](program-text.md),
  [errors.md](errors.md).
- More keywords: [`AND`](../keywords/AND.md), [`EQV`](../keywords/EQV.md), [`IMP`](../keywords/IMP.md), [`NOT`](../keywords/NOT.md), [`OR`](../keywords/OR.md), [`XOR`](../keywords/XOR.md), [`ATN`](../keywords/ATN.md), [`COS`](../keywords/COS.md), [`EXP`](../keywords/EXP.md), [`LOG`](../keywords/LOG.md), [`SIN`](../keywords/SIN.md), [`SQR`](../keywords/SQR.md), [`TAN`](../keywords/TAN.md), [`MKD$`](../keywords/MKD$.md), [`MKS$`](../keywords/MKS$.md), [`HEX$`](../keywords/HEX$.md).

## Tests that cover it

- `make float-acceptance` — literals and their bytes, the output format,
  arithmetic, rounding, overflow, division by zero, conversions, typed variables.
- `make math-acceptance` — the conversion and maths functions, scored against
  the true value where zerobas deliberately differs.
- `make prnumwrap-acceptance` — a number at the end of a line.
- `make kwsweep` — an everyday row and the error rows per numeric keyword.
