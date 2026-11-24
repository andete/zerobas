<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->
<!-- example: reference=CF-3300 disk=yes -->

# `CVD` — read a double-precision number back from an 8-byte string

> **Spec:** DRAFT 1 (2026-11-24) — 50 cases measured on the National CF-3300 (Disk BASIC, the reference) against zerobas's
> disk build, and on the Philips VG-8020 (no Disk BASIC) against its diskless one, by typed BASIC
> ([`kmkcv.py`](../../probes/basic/spec/kmkcv.py)); every rule is executable and every recorded output is read by one.
> Not yet reviewed ([the keyword plan](spec-plan.md)).
>
> **Status (2026-11-24):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✗ (an error code differ). 1 difference, found by the spec probe (below).
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`CVD(s$)` takes the first eight bytes of a string and returns the
double-precision number they hold. It is the reading half of
[`MKD$`](MKD$.md): `CVD(MKD$(x))` is `x`, all fourteen digits. It is a Disk
BASIC function, so the reference is the National CF-3300; zerobas gives the same values, and differs in an error code (below). It shares its
rules with [`CVI`](CVI.md) and [`CVS`](CVS.md).

## Syntax

```
CVD(<string expression>)
```

One argument, always.

## Details

- **The round trip keeps all fourteen digits**: `CVD(MKD$(1/3))` is
  .33333333333333 and `CVD(MKD$(.1))` is .1.
- **A string shorter than eight bytes** is `Illegal function call` (error 5) —
  including the four bytes of an `MKS$`: `CVD(MKS$(1.5))` is error 5, not a
  number read out of whatever follows.
- **A number instead of a string** (`CVD(5)`) is `Type mismatch` (error 13).
- **Without a disk system** (a diskless MSX such as the VG-8020) `CVD` is
  `Illegal function call` (error 5). A diskless zerobas does the same for the
  call measured there (`CVD("ABCDEFGH")`).

| you write | you get |
|---|---|
| `CVD(MKD$(.1))` | .1 |
| `CVD("ABCDEFG")`, `CVD("")`, `CVD(MKS$(1.5))` | error 5, `Illegal function call` |
| `CVD(5)` | error 13, `Type mismatch` |
| `CVD()`, `CVD("ABCDEFGH","ABCDEFGH")` | error 2, `Syntax error` |
| `CVD("ABCDEFGH")` on a machine without a disk ROM | error 5, `Illegal function call` |

The whole set of errors `CVD` can raise on the CF-3300 is {2, 5, 13}; zerobas
raises the same set.

## Example

```
10 ON ERROR GOTO 80
20 A$=MKD$(1/3)
30 PRINT LEN(A$)
40 PRINT CVD(A$)
50 PRINT CVD(MKD$(.1))
60 A#=CVD(MKS$(1.5))
70 END
80 PRINT "Error";ERR:RESUME NEXT
RUN
 8
 .33333333333333
 .1
Error 5
```

Run on the CF-3300 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_cvd.out`](../../scratchpad/kwdoc_cvd.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## The specification

Reference: the National CF-3300's Disk BASIC, against zerobas on the disk machine
(`C-BIOS_MSX1_EU_REPACK_DISK`); and, for the diskless rules, the Philips VG-8020's MSX BASIC against zerobas
on the diskless machine (`C-BIOS_MSX1_EU_REPACK_NODISK`).

**How to read the rules below.** Every rule is a sentence AND a check
([`probes/basic/spec/cvd_rules.py`](../../probes/basic/spec/cvd_rules.py), model in
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

**Controls** ([`kmkcv_controls.py`](../../probes/basic/spec/kmkcv_controls.py)): each is a rival rule run over the
reference's cases: “a short string padded with zero bytes” is FALSE on 14 of the 17 cases R-CVD-BYTES selects (e.g. KMC DCV 34); “exactly 8 bytes required” on 1 (KMC DCV 49); “without Disk BASIC the argument's type checked first (13) -- zerobas's” on 1 of R-CVD-NODISK's 21 (KMC FX 53).

<!-- RULES BEGIN -->
<!-- GENERATED by tools/spec_rules.py from probes/basic/spec/cvd_rules.py -- do not edit; `python3 tools/spec_rules.py probes/basic/spec/cvd_rules.py --write` -->

**6 rules; 6 hold on the reference. Of the 350 recorded outputs (each case's error from the statement and from its USR form, R's 8 bytes, S$'s length and first 8 bytes, the result's type as USR saw it and the result's own bytes): 350 read by a rule's check, 0 declared NOT evidence (below), 0 unread.**

#### 1. With Disk BASIC (the CF-3300)

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-CVD-BYTES** CVD(s) is the first 8 bytes of s, as they are -- a double, whatever they hold (a zero exponent byte with digits, a non-BCD nibble: unchanged); bytes beyond the 8th are ignored; a string shorter than 8 bytes is error 5 (Illegal function call), from `R=CVD(s)` and `USR(CVD(s))` alike. | 17 | ✓ | ✓ |
| **R-CVD-EXPR** The argument may be any string expression: CVD("A"+...+"H") is the bytes 41 42 ...; CVD(MID$(S$,3)) starts at S$'s third byte; and CVD(MKD$(x)) gives x back, byte for byte. | 2 | ✓ | ✓ |

#### 2. Forms and errors

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-CVD-TYPE** A number as the argument, or the result assigned to a string variable, is error 13 (Type mismatch). | 2 | ✓ | ✓ |
| **R-CVD-SYNTAX** No argument, a second argument, no closing parenthesis, or the name without a parenthesis is error 2 (Syntax error) -- with or without Disk BASIC. | 8 | ✓ | ✓ |

#### 3. Without Disk BASIC (the VG-8020)

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-CVD-NODISK** Without Disk BASIC every call of CVD whose argument computes is error 5 (Illegal function call) -- whatever the argument, a number included (5, not 13), and the result assigned to the wrong type too; nothing is assigned and USR is not reached. | 21 | ✓ | ✗ 1: KMC FX 53 |

#### 4. The result stored

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-CVD-ASSIGN** `R=CVD(s)` with R a double stores the result as a double: an integer by its value, a single's 4 bytes then four zero bytes -- an exponent-0 one too (CVS of 00 10 00 00 leaves R 00 10 00 00 00 00 00 00) --, a double's 8; after an error R keeps its sentinel -12345. Read in every case. | 50 | ✓ | ✓ |

<!-- RULES END -->

## Differences from the reference

- **Without Disk BASIC, `CVD(5)` is error 13 here, 5 on the VG-8020** ([D-DISKFNTYPE](../../todo/open/D-DISKFNTYPE.md); rule R-CVD-NODISK, KMC FX 53): the reference refuses every call with 5 before it looks at the argument's type.

The one rung not yet proven is **RAM usage**: `CVD` uses the same amount of
free memory on both machines, but the two write different sets of work-area
cells while doing it.

## On later generations (MSX2, MSX2+)

[A] Not measured yet: the probe has not run on the MSX2 / MSX2+ references (spec-method §4).

## Open (not measured)

- [A] Direct mode: every case ran inside a program.
- [A] Which work-area cells the call writes (the RAM-usage rung).
- [A] With a FIELD buffer, LSET / RSET and a random file (the disk region's).
- [A] Strings longer than 9 bytes; a string from a FIELD variable.

## What we found, and how

- **The spec probe** (D-KWSPEC, 2026-11-24): CVD takes the first 8 bytes of a string of at least 8, as they are; shorter is error 5. Without Disk BASIC every call whose argument computes is error 5, a wrong-type argument included. zerobas agrees on every value; its differences are error codes (below).
- **`CVD` was not a keyword at all** (fixed 2026-09-03, D-MKSD), like the
  rest of the floating-point family. It was added sharing `CVI`'s code, so it
  inherited `CVI`'s already corrected error order. Two deliberately broken
  builds showed what the tests must hold: with the length check weakened,
  `CVD(MKS$(1.5))` read eight bytes out of a four-byte string and answered
  a number; with the result typed as single, only `CVD(MKD$(1/3))` noticed,
  because 1.5 and 7 fit in six digits anyway
  ([spec-basic-mksd.md](../spec-basic-mksd.md) §5).
- **For a while `CVD` had a single scoring row** (counted 2026-09-13): no
  suite but the keyword sweep ever ran it. A round trip of .1, a fraction
  with no exact binary form, was added the same day (D-KWBREADTH).
- **A diskless zerobas answered `CVD`** where a diskless MSX refuses (fixed
  2026-09-03, D-MKHOOK), and the conversion moved into the disk ROM on
  2026-09-17 (D-CVMOVE)
  ([spec-basic-nodisk.md](../spec-basic-nodisk.md) §10).

## Where it lives

- Main ROM: `ev_ff_cvd` / `ev_ff_cv` in [basic/expr.asm](../../basic/expr.asm)
  parse the argument, check its length and type, and offer it to the disk ROM
  through the `CVD` hook; an unclaimed hook is error 5.
- Disk ROM: `hk_cv` in [disk/kernel.asm](../../disk/kernel.asm), shared with
  `CVI` and `CVS`.

## Tests that cover it

- `make kwsweep` — the round trips of 1 and .1, and the error rows for
  {2, 5, 13}, against the CF-3300.
- `make nodisk-acceptance` — error 5 on a diskless machine.
- `make kwram` — the RAM-usage comparison.
