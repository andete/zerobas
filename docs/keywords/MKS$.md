<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->
<!-- example: reference=CF-3300 disk=yes -->

# `MKS$` — pack a single-precision number into a 4-byte string

> **Spec:** DRAFT 1 (2026-11-24) — 96 cases measured on the National CF-3300 (Disk BASIC, the reference) against zerobas's
> disk build, and on the Philips VG-8020 (no Disk BASIC) against its diskless one, by typed BASIC
> ([`kmkcv.py`](../../probes/basic/spec/kmkcv.py)); every rule is executable and every recorded output is read by one.
> Not yet reviewed ([the keyword plan](spec-plan.md)).
>
> **Status (2026-11-24):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✗ (two error codes differ). 2 differences, found by the spec probe (below).
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`MKS$(x)` returns the single-precision value of `x` as a four-byte string —
exactly the four bytes a single variable (`A!`) holds in memory. It is for
putting a number into a random-access file record; [`CVS`](CVS.md) turns the
bytes back into the number. It is a Disk BASIC function, so the reference is
the National CF-3300. zerobas gives the same bytes; it differs in an
error code or two (below). [`MKI$`](MKI$.md) and [`MKD$`](MKD$.md) are its
siblings for integers and doubles.

## Syntax

```
MKS$(<numeric expression>)
```

One argument, always.

## Details

- **The bytes are the variable's own.** `MKS$(1.5)` is the same four bytes as
  `PEEK(VARPTR(A!))` onward for `A!=1.5`: 65, 21, 0, 0. The first byte is the
  sign and exponent, the other three hold six decimal digits, two per byte.
- **Zero is four zero bytes**: `MKS$(0)` is 0, 0, 0, 0.
- **An integer argument is widened**: `MKS$(1)` is 65, 16, 0, 0.
- **A double argument is rounded to six digits**, as storing it into `A!`
  would: `CVS(MKS$(1.23456789#))` is 1.23457.
- **A double that rounds past the largest number is `Overflow`** (error 6):
  `MKS$(9.999995D62)`. `CVS(MKS$(1E30))` is 1E+30 and `CVS(MKS$(1E-30))` is 1E-30.
- **Without a disk system** (a diskless MSX such as the VG-8020) `MKS$` is
  `Illegal function call` (error 5): the keyword is known, but the function
  belongs to the disk ROM. A diskless zerobas does the same for the calls
  measured there (`LEN(MKS$(1.5))`, `CVS(MKS$(1.5))`).

| you write | you get (byte values) |
|---|---|
| `MKS$(1.5)` | 65 21 0 0 |
| `MKS$(-1.5)` | 193 21 0 0 |
| `MKS$(1)` | 65 16 0 0 |
| `MKS$(0)` | 0 0 0 0 |
| `MKS$("A")` | error 13, `Type mismatch` |
| `MKS$()`, `MKS$(1,1)` | error 2, `Syntax error` |
| `MKS$(1.5)` on a machine without a disk ROM | error 5, `Illegal function call` |

The whole set of errors `MKS$` can raise on the CF-3300 is {2, 6, 13}; zerobas
raises the same set.

## Example

```
10 ON ERROR GOTO 90
20 A$=MKS$(1.5):GOSUB 70
30 A$=MKS$(-1.5):GOSUB 70
40 A$=MKS$(0):GOSUB 70
50 A$=MKS$("A")
60 END
70 FOR I=1 TO 4:B=ASC(MID$(A$,I,1))
80 PRINT B;:NEXT:PRINT:RETURN
90 PRINT "Error";ERR:RESUME NEXT
RUN
 65  21  0  0
 193  21  0  0
 0  0  0  0
Error 13
```

Run on the CF-3300 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_mks_s.out`](../../scratchpad/kwdoc_mks_s.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## The specification

Reference: the National CF-3300's Disk BASIC, against zerobas on the disk machine
(`C-BIOS_MSX1_EU_REPACK_DISK`); and, for the diskless rules, the Philips VG-8020's MSX BASIC against zerobas
on the diskless machine (`C-BIOS_MSX1_EU_REPACK_NODISK`).

**How to read the rules below.** Every rule is a sentence AND a check
([`probes/basic/spec/mks_s_rules.py`](../../probes/basic/spec/mks_s_rules.py), model in
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
- **[KMC DMK *i*]** / **[KMC MK *i*]**: `S$=MKS$(N)`-style calls of MKI$, MKS$ and MKD$ over the numbers
  I:0, I:1, I:-1, I:255, I:256, I:12345, I:32767, I:-32768, S:0, S:1, S:-1, S:.5, S:2.5, S:-2.5, S:1.5, S:-1.5, S:32767.9, S:-32768.9, S:32768, S:1E10, S:1.23456, S:1E-64, D:0, D:1, D:-1, D:2.5, D:-2.5, D:1.2345678901234, D:-1.2345678901234, D:1.2345650000001, D:32767.5, D:-32768.5, D:1D20, D:9.999995D62, D:1.2345678D-10 (I integer, S single, D double; each READ into
  `N%` / `N!` / `N#` and its own bytes recorded first) -- with and without Disk BASIC.
- **[KMC DCV *i*]** / **[KMC CV *i*]**: `R=CVx(S$)` and `Q=USR(CVx(S$))` of CVI, CVS and CVD over 17 strings built
  with `CHR$` from DATA bytes: lengths 0 to 9, canonical integers, singles and doubles, a zero exponent byte with
  digits, `&H80` with digits, a non-BCD nibble -- with and without Disk BASIC.
- **[KMC DFX *i*]** / **[KMC FX *i*]**: fixed statements (`FX` in the probe): a wrong-type argument, the result
  assigned to the wrong type, `1/0`, no argument, an extra one, no `)`, no parenthesis; the forms `F (5)`, `7`,
  `2.5`, `1/3`, `&H8000`, `40000`; an 8-byte string expression, `MID$`, and each round trip `CVx(MKx$(...))`.

**Controls** ([`kmkcv_controls.py`](../../probes/basic/spec/kmkcv_controls.py)): each is a rival rule run over the
reference's cases: “a double's digits beyond the 6th dropped” is FALSE on 5 of the 35 cases R-MKS-BYTES selects (e.g. KMC DMK 62); “without Disk BASIC the argument's type checked first (13) -- zerobas's” on 1 of R-MKS-NODISK's 43 (KMC FX 13).

<!-- RULES BEGIN -->
<!-- GENERATED by tools/spec_rules.py from probes/basic/spec/mks_s_rules.py -- do not edit; `python3 tools/spec_rules.py probes/basic/spec/mks_s_rules.py --write` -->

**7 rules; 7 hold on the reference. Of the 672 recorded outputs (each case's error from the statement and from its USR form, R's 8 bytes, S$'s length and first 8 bytes, the result's type as USR saw it and the result's own bytes): 672 read by a rule's check, 0 declared NOT evidence (below), 0 unread.**

#### 1. With Disk BASIC (the CF-3300)

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-MKS-BYTES** MKS$(x) is a string of 4 bytes: x converted as CSNG(x) does ([CSNG](CSNG.md): a double rounded half up on its 7th digit), then that number's own bytes, as VARPTR shows them (an integer low byte first). Where CSNG raises Overflow, so does MKS$ (9.999995D62): error 6. | 35 | ✓ | ✓ |

#### 2. Forms and errors

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-MKS-FORMS** A space before the parenthesis is allowed, and a literal's own type is the argument's (7 and &H8000 integers, 2.5 and 40000 singles, 1/3 a double -- kmath's measured literal types); each gives what R-MKS-BYTES says for it. | 6 | ✓ | ✓ |
| **R-MKS-OWNERR** An argument that fails to compute raises its own error (1/0: error 11) -- with or without Disk BASIC: the argument is evaluated first. | 2 | ✓ | ✓ |
| **R-MKS-TYPE** A string as the argument, or the result assigned to a number variable, is error 13 (Type mismatch). | 2 | ✓ | ✓ |
| **R-MKS-SYNTAX** No argument, a second argument, no closing parenthesis, or the name without a parenthesis is error 2 (Syntax error) -- with or without Disk BASIC. | 8 | ✓ | ✗ 2: KMC FX 18, KMC DFX 18 |

#### 3. Without Disk BASIC (the VG-8020)

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-MKS-NODISK** Without Disk BASIC every call of MKS$ whose argument computes is error 5 (Illegal function call) -- whatever the argument, a string included (5, not 13), and the result assigned to the wrong type too; nothing is assigned and USR is not reached. | 43 | ✓ | ✗ 1: KMC FX 13 |

#### 4. The result stored

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-MKS-ASSIGN** `S$=MKS$(x)` assigns only S$: R keeps its sentinel -12345 in every case. | 96 | ✓ | ✓ |

<!-- RULES END -->

## Differences from the reference

- **`S$=MKS$` (no parenthesis) is error 24 (Missing operand) here, error 2 on the CF-3300 and the VG-8020** ([D-MKNOPAREN](../../todo/open/D-MKNOPAREN.md); rule R-MKS-SYNTAX, KMC FX 18, DFX 18), on the disk and the diskless build alike.
- **Without Disk BASIC, `MKS$("A")` is error 13 here, 5 on the VG-8020** ([D-DISKFNTYPE](../../todo/open/D-DISKFNTYPE.md); rule R-MKS-NODISK, KMC FX 13): the reference refuses every call with 5 before it looks at the argument's type.

The one rung not yet proven is **RAM usage**: `MKS$` uses the same amount of
free memory on both machines, but the two write different sets of work-area
cells while doing it.

## On later generations (MSX2, MSX2+)

[A] Not measured yet: the probe has not run on the MSX2 / MSX2+ references (spec-method §4).

## Open (not measured)

- [A] Direct mode: every case ran inside a program.
- [A] Which work-area cells the call writes (the RAM-usage rung).
- [A] With a FIELD buffer, LSET / RSET and a random file (the disk region's).

## What we found, and how

- **The spec probe** (D-KWSPEC, 2026-11-24): MKS$ is CSNG and then the single's four bytes -- so a double that rounds past the largest exponent is `Overflow`: `MKS$(9.999995D62)` is error 6 (this page said before there was no range error). Without Disk BASIC every call whose argument computes is error 5, a wrong-type argument included. zerobas agrees on every value; its differences are error codes (below).
- **`MKS$` was not a keyword at all** (fixed 2026-09-03, D-MKSD). It was
  missing from zerobas's keyword table, so `MKS$(1.5)` was read as an element
  of a string array named `MKS$` and quietly gave the empty string — a silent
  wrong answer. The keyword sweep could not see it either, because its second
  reference machine was not booting in time; that was fixed the same day
  ([spec-basic-mksd.md](../spec-basic-mksd.md)).
- **Zero would have been packed wrongly** (fixed 2026-09-03, D-FACZERO).
  Measuring the byte layout before writing `MKS$` showed that zerobas stored
  zero with the previous value's digits left behind: `MKS$(0)` would have
  given 0, 255, 255, 255. It never showed in `PRINT`, which stops at the
  first byte ([spec-basic-faczero.md](../spec-basic-faczero.md)).
- **A diskless zerobas answered `MKS$`** where a diskless MSX refuses (fixed
  2026-09-03, D-MKHOOK). It now goes through its documented hook, and the
  rounding itself runs in the disk ROM (D-DISKABI, the same day)
  ([spec-basic-nodisk.md](../spec-basic-nodisk.md) §10, §13).
- **`MKS$(1,1)` was `Type mismatch`** (fixed 2026-09-29, D-MKEXTRA); the
  CF-3300 says `Syntax error`. Found by the 2026-09-27 run that enumerates
  every error the reference raises
  ([`t6enum_b3.out`](../../scratchpad/t6enum_b3.out)).

## Where it lives

- Main ROM: `str_mks` / `str_mkf` in [basic/strvar.asm](../../basic/strvar.asm)
  parse the argument and offer it to the disk ROM through the `MKS$` hook; an
  unclaimed hook is error 5.
- Disk ROM: `hk_mkfloat` in [disk/kernel.asm](../../disk/kernel.asm) widens an
  integer argument (since 2026-10-20), then rounds and packs the value, shared
  with `MKD$`.

## Related concepts

- [Numbers](../concepts/numbers.md) — integers, single and double precision

## Tests that cover it

- `make kwsweep` — the length row, the first-byte row for 1.5, and the error
  rows for {2, 13}, against the CF-3300.
- `make nodisk-acceptance` — error 5 on a diskless machine.
- `make kwram` — the RAM-usage comparison.
