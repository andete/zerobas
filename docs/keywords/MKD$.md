<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->
<!-- example: reference=CF-3300 disk=yes -->

# `MKD$` — pack a double-precision number into an 8-byte string

> **Spec:** DRAFT 1 (2026-11-24) — 96 cases measured on the National CF-3300 (Disk BASIC, the reference) against zerobas's
> disk build, and on the Philips VG-8020 (no Disk BASIC) against its diskless one, by typed BASIC
> ([`kmkcv.py`](../../probes/basic/spec/kmkcv.py)); every rule is executable and every recorded output is read by one.
> Goldfish pass 1 (2026-11-24) acted on ([the keyword plan](spec-plan.md)).
>
> **Status (2026-11-24):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✗ (two error codes differ). 2 differences, found by the spec probe (below).
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`MKD$(x)` returns the double-precision value of `x` as an eight-byte string —
exactly the eight bytes a double variable (`A#`) holds in memory. It is for
putting a number into a random-access file record; [`CVD`](CVD.md) turns the
bytes back into the number. It is a Disk BASIC function, so the reference is
the National CF-3300. zerobas gives the same bytes; it differs in an
error code or two (below). It works exactly like [`MKS$`](MKS$.md), with
eight bytes instead of four; read that page for the shared detail.

## Syntax

```
MKD$(<numeric expression>)
```

One argument, always.

## Details

- **The bytes are the variable's own**: one byte of sign and exponent, then
  seven bytes holding fourteen decimal digits, two per byte. `MKD$(1.5)` is
  65, 21, 0, 0, 0, 0, 0, 0, and `MKD$(1/3)` is 64 followed by seven 51s
  (51 is `&H33`, the digits "33").
- **All fourteen digits are kept**: `CVD(MKD$(1/3))` gives back
  .33333333333333, and `CVD(MKD$(.1))` gives back .1.
- **An integer or single argument is widened** to double first.
- **There is no range error**: every number has a double.
- **Without a disk system** (a diskless MSX such as the VG-8020) `MKD$` is
  `Illegal function call` (error 5). A diskless zerobas gives error 5 too, except for a wrong-type argument: `MKD$("A")` is 13 there (below).

| you write | you get |
|---|---|
| `MKD$(1.5)` | bytes 65 21 0 0 0 0 0 0 |
| `LEN(MKD$(1))` | 8 |
| `MKD$("A")` | error 13, `Type mismatch` |
| `MKD$()`, `MKD$(1,1)` | error 2, `Syntax error` |
| `MKD$(1.5)` on a machine without a disk ROM | error 5, `Illegal function call` |

The whole set of errors `MKD$` can raise on the CF-3300 is {2, 13}; zerobas
raises the same set.

## Example

```
10 ON ERROR GOTO 90
20 A$=MKD$(1.5):GOSUB 70
30 A$=MKD$(1/3):GOSUB 70
40 PRINT CVD(A$)
50 A$=MKD$(1,1)
60 END
70 FOR I=1 TO 8:B=ASC(MID$(A$,I,1))
80 PRINT B;:NEXT:PRINT:RETURN
90 PRINT "Error";ERR:RESUME NEXT
RUN
 65  21  0  0  0  0  0  0
 64  51  51  51  51  51  51  51
 .33333333333333
Error 2
```

Run on the CF-3300 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_mkd_s.out`](../../scratchpad/kwdoc_mkd_s.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## The specification

Reference: the National CF-3300's Disk BASIC, against zerobas on the disk machine
(`C-BIOS_MSX1_EU_REPACK_DISK`); and, for the diskless rules, the Philips VG-8020's MSX BASIC against zerobas
on the diskless machine (`C-BIOS_MSX1_EU_REPACK_NODISK`).

**How to read the rules below.** Every rule is a sentence AND a check
([`probes/basic/spec/mkd_s_rules.py`](../../probes/basic/spec/mkd_s_rules.py), model in
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
- **[KMC DMK *i*]** / **[KMC MK *i*]**: `S$=MKD$(N)`-style calls of MKI$, MKS$ and MKD$ over the numbers
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
reference's cases: “every number's bytes as a double's -- an integer's two bytes widened, not converted” is FALSE on 7 of the 35 cases R-MKD-BYTES selects (e.g. KMC DMK 71); “without Disk BASIC the argument's type checked first (13) -- zerobas's” is FALSE on 1 of the 43 cases R-MKD-NODISK selects (e.g. KMC FX 26).

<!-- RULES BEGIN -->
<!-- GENERATED by tools/spec_rules.py from probes/basic/spec/mkd_s_rules.py -- do not edit; `python3 tools/spec_rules.py probes/basic/spec/mkd_s_rules.py --write` -->

**7 rules; 7 hold on the reference. Of the 672 recorded outputs (each case's error from the statement and from its USR form, R's 8 bytes, S$'s length and first 8 bytes, the result's type as USR saw it and the result's own bytes): 672 read by a rule's check, 0 declared NOT evidence (below), 0 unread.**

#### 1. With Disk BASIC (the CF-3300)

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-MKD-BYTES** MKD$(x) is a string of 8 bytes: x converted as CDBL(x) does ([CDBL](CDBL.md): a single's 6 digits and 8 zeros), then that number's own bytes, as VARPTR shows them (an integer low byte first). Where CDBL raises Overflow, so does MKD$ -- never: every number has a double. | 35 | ✓ | ✓ |

#### 2. Forms and errors

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-MKD-FORMS** A space before the parenthesis is allowed, and a literal's own type is the argument's (7 and &H8000 integers, 2.5 and 40000 singles, 1/3 a double -- kmath's measured literal types); each gives what R-MKD-BYTES says for it. | 6 | ✓ | ✓ |
| **R-MKD-OWNERR** An argument that fails to compute raises its own error (1/0: error 11) -- with or without Disk BASIC: the argument is evaluated first. | 2 | ✓ | ✓ |
| **R-MKD-TYPE** A string as the argument, or the result assigned to a number variable, is error 13 (Type mismatch). | 2 | ✓ | ✓ |
| **R-MKD-SYNTAX** No argument, a second argument, no closing parenthesis, or the name without a parenthesis is error 2 (Syntax error) -- with or without Disk BASIC. | 8 | ✓ | ✗ 2: KMC FX 31, KMC DFX 31 |

#### 3. Without Disk BASIC (the VG-8020)

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-MKD-NODISK** Without Disk BASIC every call of MKD$ whose argument computes is error 5 (Illegal function call) -- whatever the argument, a string included (5, not 13), and the result assigned to the wrong type too; nothing is assigned and USR is not reached. | 43 | ✓ | ✗ 1: KMC FX 26 |

#### 4. The result stored

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-MKD-ASSIGN** `S$=MKD$(x)` assigns only S$: R keeps its sentinel -12345 in every case. | 96 | ✓ | ✓ |

<!-- RULES END -->

## Differences from the reference

- **`S$=MKD$` (no parenthesis) is error 24 (Missing operand) here, error 2 on the CF-3300 and the VG-8020** ([D-MKNOPAREN](../../todo/open/D-MKNOPAREN.md); rule R-MKD-SYNTAX, KMC FX 31, DFX 31), on the disk and the diskless build alike.
- **Without Disk BASIC, `MKD$("A")` is error 13 here, 5 on the VG-8020** ([D-DISKFNTYPE](../../todo/open/D-DISKFNTYPE.md); rule R-MKD-NODISK, KMC FX 26): the reference refuses every call with 5 before it looks at the argument's type.

The one rung not yet proven is **RAM usage**: `MKD$` uses the same amount of
free memory on both machines, but the two write different sets of work-area
cells while doing it.

## On later generations (MSX2, MSX2+)

[A] Not measured yet: the probe has not run on the MSX2 / MSX2+ references (spec-method §4).

## Open (not measured)

- [A] Direct mode: every case ran inside a program.
- [A] Which work-area cells the call writes (the RAM-usage rung).
- [A] With a FIELD buffer, LSET / RSET and a random file (the disk region's).
- [A] The error set's closure: an Out of string space (14) with string space full before `S$=MK*$(x)` is not tried.
- [A] A CV result stored in an integer or single variable (`R%=CVS(...)`).

## What we found, and how

- **The spec probe** (D-KWSPEC, 2026-11-24): MKD$ is CDBL and then the double's eight bytes: an integer is converted (MKD$(1) is 41 10 00 ..., not 01 00 padded); a single's 4 bytes and four zero bytes are what CDBL gives. Without Disk BASIC every call whose argument computes is error 5, a wrong-type argument included. zerobas agrees on every value; its differences are error codes (below).
- **`MKD$` was not a keyword at all** (fixed 2026-09-03, D-MKSD), like
  `MKS$`, `CVS` and `CVD`: `MKD$(1.5)` was read as an element of a string
  array and gave the empty string
  ([spec-basic-mksd.md](../spec-basic-mksd.md)). Values such as 1.5 fit in
  six digits and survive almost any packing mistake, so the slice's probe
  ([`mksd_probe.py`](../../scratchpad/mksd_probe.py)) also carries
  `CVD(MKD$(1/3))`, which needs all fourteen.
- **A diskless zerobas answered `MKD$`** where a diskless MSX refuses (fixed
  2026-09-03, D-MKHOOK); the packing now runs in the disk ROM
  ([spec-basic-nodisk.md](../spec-basic-nodisk.md) §10, §13).
- **`MKD$(1,1)` was `Type mismatch`** (fixed 2026-09-29, D-MKEXTRA); the
  CF-3300 says `Syntax error`
  ([`t6enum_b3.out`](../../scratchpad/t6enum_b3.out)).

## Where it lives

- Main ROM: `str_mkd` / `str_mkf` in [basic/strvar.asm](../../basic/strvar.asm)
  parse the argument and offer it to the disk ROM through the `MKD$` hook; an
  unclaimed hook is error 5.
- Disk ROM: `hk_mkfloat` in [disk/kernel.asm](../../disk/kernel.asm) widens the
  argument (since 2026-10-20) and packs it, shared with `MKS$`.

## Related concepts

- [Numbers](../concepts/numbers.md) — integers, single and double precision

## Tests that cover it

- `make kwsweep` — the length row, the first-byte row for 1.5, the error
  rows for {2, 13}, and `CVD`'s round-trip rows, which build their argument
  with `MKD$`; all against the CF-3300.
- `make nodisk-acceptance` — error 5 on a diskless machine.
- `make kwram` — the RAM-usage comparison.
