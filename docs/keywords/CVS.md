<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->
<!-- example: reference=CF-3300 disk=yes -->

# `CVS` — read a single-precision number back from a 4-byte string

> **Spec:** DRAFT 1 (2026-11-24) — 50 cases measured on the National CF-3300 (Disk BASIC, the reference) against zerobas's
> disk build, and on the Philips VG-8020 (no Disk BASIC) against its diskless one, by typed BASIC
> ([`kmkcv.py`](../../probes/basic/spec/kmkcv.py)); every rule is executable and every recorded output is read by one.
> Goldfish pass 1 (2026-11-24) acted on ([the keyword plan](spec-plan.md)).
>
> **Status (2026-11-24):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✗ (an error code differ). 2 differences, found by the spec probe (below).
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`CVS(s$)` takes the first four bytes of a string and returns the
single-precision number they hold. It is the reading half of
[`MKS$`](MKS$.md): `CVS(MKS$(x))` is `x` rounded to six digits. It is a Disk
BASIC function, so the reference is the National CF-3300; zerobas gives the same values, and differs in an error code and in one stored zero (below). It shares its
rules with [`CVI`](CVI.md) (two bytes) and [`CVD`](CVD.md) (eight).

## Syntax

```
CVS(<string expression>)
```

One argument, always.

## Details

- **The round trip keeps six digits**: `CVS(MKS$(1.5))` is 1.5, and
  `CVS(MKS$(1.23456789#))` is 1.23457.
- **Only the first four bytes count**; the rest of a longer string is
  ignored. `CVS("ABCDEFGH")` is 4.24344 — whatever number the bytes of "ABCD"
  happen to spell.
- **A string shorter than four bytes** (`CVS("ABC")`, `CVS("AB")`,
  `CVS("")`) is `Illegal function call` (error 5).
- **A number instead of a string** (`CVS(5)`) is `Type mismatch` (error 13).
- **Without a disk system** (a diskless MSX such as the VG-8020) `CVS` is
  `Illegal function call` (error 5). A diskless zerobas gives error 5 too, except for a wrong-type argument: `CVS(5)` is 13 there (below).

| you write | you get |
|---|---|
| `CVS(MKS$(1.5))` | 1.5 |
| `CVS(MKS$(1E30))` | 1E+30 |
| `CVS("ABCDEFGH")` | 4.24344 |
| `CVS("ABC")`, `CVS("")` | error 5, `Illegal function call` |
| `CVS(5)` | error 13, `Type mismatch` |
| `CVS()`, `CVS("ABCD","ABCD")` | error 2, `Syntax error` |
| `CVS(MKS$(1.5))` on a machine without a disk ROM | error 5, `Illegal function call` |

The whole set of errors `CVS` can raise on the CF-3300 is {2, 5, 13}; zerobas
raises the same set.

## Example

```
10 ON ERROR GOTO 80
20 A$=MKS$(1.5)
30 PRINT CVS(A$);CVS(MKS$(-1.5))
40 PRINT CVS(MKS$(1.23456789#))
50 PRINT CVS("ABCDEFGH")
60 A=CVS("ABC")
70 END
80 PRINT "Error";ERR:RESUME NEXT
RUN
 1.5 -1.5
 1.23457
 4.24344
Error 5
```

Run on the CF-3300 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_cvs.out`](../../scratchpad/kwdoc_cvs.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## The specification

Reference: the National CF-3300's Disk BASIC, against zerobas on the disk machine
(`C-BIOS_MSX1_EU_REPACK_DISK`); and, for the diskless rules, the Philips VG-8020's MSX BASIC against zerobas
on the diskless machine (`C-BIOS_MSX1_EU_REPACK_NODISK`).

**How to read the rules below.** Every rule is a sentence AND a check
([`probes/basic/spec/cvs_rules.py`](../../probes/basic/spec/cvs_rules.py), model in
[`kmkcv_model.py`](../../probes/basic/spec/kmkcv_model.py), run by
[`tools/spec_rules.py`](../../tools/spec_rules.py); [docs/spec-method.md](../spec-method.md) §3a,
[the keyword plan](spec-plan.md)) over the measured cases it names.
- **reference:** ✓ means the check holds on EVERY case it selects of the reference's run (the CF-3300's for the
  KMC D* cases, the VG-8020's for the others).
- **zerobas:** the cases where zerobas fails it, which are its differences.

The tables are generated from the checks, so a sentence here cannot say more than the data does.

**Evidence.** One probe, [`probes/basic/spec/kmkcv.py`](../../probes/basic/spec/kmkcv.py) (the conversion region's
second, on the shared RAM-record harness [`ramrec.py`](../../probes/basic/spec/ramrec.py) and the USR type readout of
[`kmath.py`](../../probes/basic/spec/kmath.py)), typed on both machines of each pair -- the disk pair each booted
with a copy of `disk/test720.dsk` in drive A; run file [`scratchpad/KMC_run1.out`](../../scratchpad/KMC_run1.out)
(2026-11-24; zerobas's side on that day's builds). Before every case `S$` is `""`, `R` -12345 and the USR type cell
255, so an error, which assigns nothing, cannot read as a result; the record holds the error, R's 8 bytes, `S$`'s
length and first 8 bytes, and (for the `USR` forms) the result's type and own bytes.
- **[KMC DMK *i*]** / **[KMC MK *i*]**: `S$=MKI$(N)`-style calls of MKI$, MKS$ and MKD$ over the numbers
  I:0, I:1, I:-1, I:255, I:256, I:12345, I:32767, I:-32768, S:0, S:1, S:-1, S:.5, S:2.5, S:-2.5, S:1.5, S:-1.5, S:32767.9, S:-32768.9, S:32768, S:1E10, S:1.23456, S:1E-64, D:0, D:1, D:-1, D:2.5, D:-2.5, D:1.2345678901234, D:-1.2345678901234, D:1.2345650000001, D:32767.5, D:-32768.5, D:1D20, D:9.999995D62, D:1.2345678D-10 (I integer, S single, D double; each READ into
  `N%` / `N!` / `N#` and its own bytes recorded first) -- with and without Disk BASIC.
- **[KMC DCV *i*]** / **[KMC CV *i*]**: `R=CVx(S$)` and `Q=USR(CVx(S$))` of CVI, CVS and CVD over 17 strings built
  with `CHR$` from DATA bytes: lengths 0 to 9, canonical integers, singles and doubles, a zero exponent byte with
  digits, `&H80` with digits, a non-BCD nibble -- with and without Disk BASIC.
- **[KMC DFX *i*]** / **[KMC FX *i*]**: fixed statements (`FX` in the probe): a wrong-type argument, the result
  assigned to the wrong type, `1/0`, no argument, an extra one, no `)`, no parenthesis; the forms `F (5)`, `7`,
  `2.5`, `1/3`, `&H8000`, `40000`; an 8-byte string expression, `MID$`, and each round trip `CVx(MKx$(...))`.
- **[KMC DFY *i*]** / **[KMC FY *i*]** (goldfish pass 1, 2026-11-24): `MKI$(-32769)`, `MKI$(-1E10)`, `MKI$(-32768.9999#)`; `MKS$` of the exact ties `1.234565#` / `-1.234565#` and of `9.9999949999999D62`; `MID$` into CVS and CVD; `CVx(CHR$(1/0))`; `S$` holding "XY" before a failing `S$=...`; `CVI(MKI$(-12346))`; CVD of three non-canonical doubles.

**Controls** ([`kmkcv_controls.py`](../../probes/basic/spec/kmkcv_controls.py)): each is a rival rule run over the
reference's cases: “a short string padded with zero bytes (no error)” is FALSE on 7 of the 17 cases R-CVS-BYTES selects (e.g. KMC DCV 17); “an exponent-0 single made a clean zero” is FALSE on 2 of the 17 cases R-CVS-BYTES selects (e.g. KMC DCV 26); “exactly 4 bytes required” is FALSE on 5 of the 17 cases R-CVS-BYTES selects (e.g. KMC DCV 29); “an exponent-0 single stored in R as 8 zero bytes -- D-ZEROLET” is FALSE on 2 of the 54 cases R-CVS-ASSIGN selects (e.g. KMC DCV 26).

<!-- RULES BEGIN -->
<!-- GENERATED by tools/spec_rules.py from probes/basic/spec/cvs_rules.py -- do not edit; `python3 tools/spec_rules.py probes/basic/spec/cvs_rules.py --write` -->

**7 rules; 7 hold on the reference. Of the 378 recorded outputs (each case's error from the statement and from its USR form, R's 8 bytes, S$'s length and first 8 bytes, the result's type as USR saw it and the result's own bytes): 378 read by a rule's check, 0 declared NOT evidence (below), 0 unread.**

#### 1. With Disk BASIC (the CF-3300)

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-CVS-BYTES** CVS(s) is the first 4 bytes of s, as they are -- a single, whatever they hold (a zero exponent byte with digits, a non-BCD nibble: unchanged); bytes beyond the 4th are ignored; a string shorter than 4 bytes is error 5 (Illegal function call), from `R=CVS(s)` and `USR(CVS(s))` alike. | 17 | ✓ | ✓ |
| **R-CVS-EXPR** The argument may be any string expression: CVS("A"+...+"H") is the bytes 41 42 ...; CVS(MID$(S$,3)) starts at S$'s third byte; and CVS(MKS$(x)) gives x back, byte for byte. | 3 | ✓ | ✓ |

#### 2. Forms and errors

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-CVS-OWNERR** An argument that fails to compute raises its own error (CVS(CHR$(1/0)): error 11) -- with or without Disk BASIC: the argument is evaluated first. | 2 | ✓ | ✓ |
| **R-CVS-TYPE** A number as the argument, or the result assigned to a string variable, is error 13 (Type mismatch). | 2 | ✓ | ✓ |
| **R-CVS-SYNTAX** No argument, a second argument, no closing parenthesis, or the name without a parenthesis is error 2 (Syntax error) -- with or without Disk BASIC. | 8 | ✓ | ✓ |

#### 3. Without Disk BASIC (the VG-8020)

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-CVS-NODISK** Without Disk BASIC every call of CVS whose argument computes is error 5 (Illegal function call) -- whatever the argument, a number included (5, not 13), and the result assigned to the wrong type too; nothing is assigned and USR is not reached. | 22 | ✓ | ✗ 1: KMC FX 46 |

#### 4. The result stored

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-CVS-ASSIGN** `R=CVS(s)` with R a double stores the result: a single's 4 bytes then four zero bytes -- an exponent-0 one too (CVS of 00 10 00 00 leaves R 00 10 00 00 00 00 00 00); after an error R keeps its sentinel -12345. Read in every case. | 54 | ✓ | ✗ 2: KMC DCV 26, KMC DCV 27 |

<!-- RULES END -->

## Differences from the reference

- **Without Disk BASIC, `CVS(5)` is error 13 here, 5 on the VG-8020** ([D-DISKFNTYPE](../../todo/open/D-DISKFNTYPE.md); rule R-CVS-NODISK, KMC FX 46): the reference refuses every call with 5 before it looks at the argument's type.
- **A single whose exponent byte is 0 or &H80 but whose digit bytes are not, stored in a double, is zero bytes here** ([D-ZEROLET](../../todo/open/D-ZEROLET.md); rule R-CVS-ASSIGN, KMC DCV 26, 27): `R=CVS(CHR$(0)+CHR$(16)+CHR$(0)+CHR$(0))` leaves R 00 10 00 00 00 00 00 00 on the CF-3300, eight zero bytes here. `CVS`'s own result agrees; it is the assignment's.

The one rung not yet proven is **RAM usage**: `CVS` uses the same amount of
free memory on both machines, but the two write different sets of work-area
cells while doing it.

## On later generations (MSX2, MSX2+)

[A] Not measured yet: the probe has not run on the MSX2 / MSX2+ references (spec-method §4).

## Open (not measured)

- [A] Direct mode: every case ran inside a program.
- [A] Which work-area cells the call writes (the RAM-usage rung).
- [A] With a FIELD buffer, LSET / RSET and a random file (the disk region's).
- [A] Strings longer than 9 bytes; a string from a FIELD variable.
- [A] The error set's closure: an Out of string space (14) with string space full before `S$=MK*$(x)` is not tried.
- [A] A CV result stored in an integer or single variable (`R%=CVS(...)`).

## What we found, and how

- **The spec probe** (D-KWSPEC, 2026-11-24): CVS takes the first 4 bytes of a string of at least 4, as they are -- a zero exponent byte with digits and a non-BCD nibble unchanged; shorter is error 5. Without Disk BASIC every call whose argument computes is error 5, a wrong-type argument included. zerobas agrees on every value; its differences are an error code and one stored zero (below).
- **`CVS` was not a keyword at all** (fixed 2026-09-03, D-MKSD), like the
  rest of the floating-point family: `CVS` was missing from the keyword
  table. It was added sharing `CVI`'s code, so it inherited `CVI`'s already
  corrected error order (see [`CVI`](CVI.md)) instead of re-deriving it. A
  deliberately weakened length check made `CVS("AB")` answer a plausible
  4.22229 out of whatever followed the string; the slice's probe
  ([`mksd_probe.py`](../../scratchpad/mksd_probe.py)) has the rows that catch
  it ([spec-basic-mksd.md](../spec-basic-mksd.md) §5).
- **A diskless zerobas answered `CVS`** where a diskless MSX refuses (fixed
  2026-09-03, D-MKHOOK), and the conversion moved into the disk ROM on
  2026-09-17 (D-CVMOVE)
  ([spec-basic-nodisk.md](../spec-basic-nodisk.md) §10).

## Where it lives

- Main ROM: `ev_ff_cvs` / `ev_ff_cv` in [basic/expr.asm](../../basic/expr.asm)
  parse the argument, check its length and type, and offer it to the disk ROM
  through the `CVS` hook; an unclaimed hook is error 5.
- Disk ROM: `hk_cv` in [disk/kernel.asm](../../disk/kernel.asm), shared with
  `CVI` and `CVD`.

## Tests that cover it

- `make kwsweep` — the round trips of 1 and 1.5, and the error rows for
  {2, 5, 13}, against the CF-3300.
- `make nodisk-acceptance` — error 5 on a diskless machine.
- `make kwram` — the RAM-usage comparison.
