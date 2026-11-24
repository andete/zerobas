<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->
<!-- example: reference=CF-3300 disk=yes -->

# `MKI$` — pack an integer into a 2-byte string

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

`MKI$(n)` returns the integer `n` as a two-byte string holding its raw
16-bit value, low byte first. It is how a program puts a number into a
random-access file record (with `FIELD` and `LSET`); [`CVI`](CVI.md) turns the
two bytes back into the number. It is a Disk BASIC function, so the reference
is the National CF-3300. zerobas gives the same bytes; it differs in an
error code or two (below).

## Syntax

```
MKI$(<numeric expression>)
```

One argument, always.

## Details

- **Low byte first.** `MKI$(258)` (258 is `&H0102`) is `CHR$(2)+CHR$(1)`.
  Negative numbers survive the round trip: `CVI(MKI$(-1))` is −1.
- **A fraction is dropped toward zero**: `MKI$(1.5)` packs 1, `MKI$(-1.5)`
  packs −1, `MKI$(-32768.4)` packs −32768. This is the same truncation as
  [`CINT`](CINT.md).
- **The value must fit an integer**, −32768 to 32767, after truncating;
  `MKI$(32768)` and `MKI$(-32769)` are `Overflow` (error 6).
- **Without a disk system** (a diskless MSX such as the VG-8020) `MKI$` is
  `Illegal function call` (error 5): the keyword is known, but the function
  belongs to the disk ROM. On the VG-8020 even `MKI$("A")` is error 5; only a
  syntax fault such as `MKI$(1,1)` is reported first, as error 2. A diskless
  zerobas answers error 5 too, except to a string argument: 13 (below).

| you write | you get |
|---|---|
| `MKI$(258)` | `CHR$(2)+CHR$(1)` |
| `MKI$(1.5)`, `MKI$(-1.5)` | the bytes of 1, of −1 |
| `MKI$(32768)`, `MKI$(-32769)` | error 6, `Overflow` |
| `MKI$("A")` | error 13, `Type mismatch` |
| `MKI$()`, `MKI$(1,1)` | error 2, `Syntax error` |
| `MKI$(258)` on a machine without a disk ROM | error 5, `Illegal function call` |

The whole set of errors `MKI$` can raise on the CF-3300 is {2, 6, 13}; zerobas
raises the same set.

## Example

```
10 ON ERROR GOTO 90
20 A$=MKI$(258)
30 B$=RIGHT$(A$,1)
40 PRINT LEN(A$);ASC(A$);ASC(B$)
50 PRINT CVI(MKI$(1.5));CVI(MKI$(-1.5))
60 A$=MKI$(32768)
70 PRINT CVI(MKI$(-32768.4))
80 END
90 PRINT "Error";ERR:RESUME NEXT
RUN
 2  2  1
 1 -1
Error 6
-32768
```

Run on the CF-3300 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_mki_s.out`](../../scratchpad/kwdoc_mki_s.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## The specification

Reference: the National CF-3300's Disk BASIC, against zerobas on the disk machine
(`C-BIOS_MSX1_EU_REPACK_DISK`); and, for the diskless rules, the Philips VG-8020's MSX BASIC against zerobas
on the diskless machine (`C-BIOS_MSX1_EU_REPACK_NODISK`).

**How to read the rules below.** Every rule is a sentence AND a check
([`probes/basic/spec/mki_s_rules.py`](../../probes/basic/spec/mki_s_rules.py), model in
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
reference's cases: “the number rounded half away from zero” is FALSE on 11 of the 35 cases R-MKI-BYTES selects (e.g. KMC DMK 11); “without Disk BASIC the argument's type checked first (13) -- zerobas's” on 1 of R-MKI-NODISK's 43 (KMC FX 0).

<!-- RULES BEGIN -->
<!-- GENERATED by tools/spec_rules.py from probes/basic/spec/mki_s_rules.py -- do not edit; `python3 tools/spec_rules.py probes/basic/spec/mki_s_rules.py --write` -->

**7 rules; 7 hold on the reference. Of the 672 recorded outputs (each case's error from the statement and from its USR form, R's 8 bytes, S$'s length and first 8 bytes, the result's type as USR saw it and the result's own bytes): 672 read by a rule's check, 0 declared NOT evidence (below), 0 unread.**

#### 1. With Disk BASIC (the CF-3300)

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-MKI-BYTES** MKI$(x) is a string of 2 bytes: x converted as CINT(x) does ([CINT](CINT.md): toward zero, 2.5 -> 2, -2.5 -> -2), then that number's own bytes, as VARPTR shows them (an integer low byte first). Where CINT raises Overflow, so does MKI$ (32768, 1E10, 1D20): error 6, S$ left as it was. | 35 | ✓ | ✓ |

#### 2. Forms and errors

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-MKI-FORMS** A space before the parenthesis is allowed, and a literal's own type is the argument's (7 and &H8000 integers, 2.5 and 40000 singles, 1/3 a double -- kmath's measured literal types); each gives what R-MKI-BYTES says for it. | 6 | ✓ | ✓ |
| **R-MKI-OWNERR** An argument that fails to compute raises its own error (1/0: error 11) -- with or without Disk BASIC: the argument is evaluated first. | 2 | ✓ | ✓ |
| **R-MKI-TYPE** A string as the argument, or the result assigned to a number variable, is error 13 (Type mismatch). | 2 | ✓ | ✓ |
| **R-MKI-SYNTAX** No argument, a second argument, no closing parenthesis, or the name without a parenthesis is error 2 (Syntax error) -- with or without Disk BASIC. | 8 | ✓ | ✗ 2: KMC FX 5, KMC DFX 5 |

#### 3. Without Disk BASIC (the VG-8020)

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-MKI-NODISK** Without Disk BASIC every call of MKI$ whose argument computes is error 5 (Illegal function call) -- whatever the argument, a string included (5, not 13), and the result assigned to the wrong type too; nothing is assigned and USR is not reached. | 43 | ✓ | ✗ 1: KMC FX 0 |

#### 4. The result stored

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-MKI-ASSIGN** `S$=MKI$(x)` assigns only S$: R keeps its sentinel -12345 in every case. | 96 | ✓ | ✓ |

<!-- RULES END -->

## Differences from the reference

- **`S$=MKI$` (no parenthesis) is error 24 (Missing operand) here, error 2 on the CF-3300 and the VG-8020** ([D-MKNOPAREN](../../todo/open/D-MKNOPAREN.md); rule R-MKI-SYNTAX, KMC FX 5, DFX 5), on the disk and the diskless build alike.
- **Without Disk BASIC, `MKI$("A")` is error 13 here, 5 on the VG-8020** ([D-DISKFNTYPE](../../todo/open/D-DISKFNTYPE.md); rule R-MKI-NODISK, KMC FX 0): the reference refuses every call with 5 before it looks at the argument's type.

The one rung not yet proven is **RAM usage**: `MKI$` uses the same amount of
free memory on both machines, but the two write different sets of work-area
cells while doing it.

## On later generations (MSX2, MSX2+)

[A] Not measured yet: the probe has not run on the MSX2 / MSX2+ references (spec-method §4).

## Open (not measured)

- [A] Direct mode: every case ran inside a program.
- [A] Which work-area cells the call writes (the RAM-usage rung).
- [A] With a FIELD buffer, LSET / RSET and a random file (the disk region's).

## What we found, and how

- **The spec probe** (D-KWSPEC, 2026-11-24): MKI$ is CINT and then the integer's two bytes, low byte first: truncation toward zero, Overflow past the range (32768, 1E10). Without Disk BASIC every call whose argument computes is error 5, a wrong-type argument included. zerobas agrees on every value; its differences are error codes (below).
- **A diskless zerobas answered `MKI$`**, where a diskless MSX refuses with
  error 5 (fixed 2026-09-03, D-MKHOOK). On a real MSX the main ROM knows the
  keyword and the disk ROM supplies the function through a documented hook;
  zerobas had the function built into the main ROM. `MKI$` was the first verb
  routed through its hook, and the other disk functions followed the same day
  ([spec-basic-nodisk.md](../spec-basic-nodisk.md) §9–10).
- **The work moved into the disk ROM** (2026-09-17, D-MKINT), under Joost's
  ruling of that day: *"all disk commands need to be in the disk rom"*. The
  behaviour did not change.
- **Out-of-range numbers came back as a string** (fixed 2026-09-29,
  D-MKIRANGE). `MKI$(32768)` packed −32768 and `MKI$(-32769)` packed 32767,
  where the CF-3300 says `Overflow`; worse, `MKI$(-32768.4)` packed 32767
  instead of −32768 — a wrong value, not just a missing error. Found by the
  2026-09-27 run that enumerates every error the reference raises
  ([`t6enum_b3.out`](../../scratchpad/t6enum_b3.out)); before and after:
  [`mkirange_run.out`](../../scratchpad/mkirange_run.out),
  [`mkirange_after.out`](../../scratchpad/mkirange_after.out).
- **`MKI$(1,1)` was `Type mismatch`** (fixed 2026-09-29, D-MKEXTRA); the
  CF-3300 says `Syntax error`. The same fix covered `MKS$` and `MKD$`.
- **The early tests could not see the bytes.** The first row checked only
  `LEN(MKI$(1))=2`, which a function returning two zero bytes would pass.
  A row reading the first byte of 258 was added on 2026-09-13 (D-KWBREADTH)
  and one reading both bytes and their order on 2026-09-14 (D-KWBATCH5).

## Where it lives

- Main ROM: `str_mki` / `str_mkf` in [basic/strvar.asm](../../basic/strvar.asm)
  parse the argument and offer it to the disk ROM through the `MKI$` hook; an
  unclaimed hook is error 5.
- Disk ROM: `hk_mki` in [disk/kernel.asm](../../disk/kernel.asm) truncates a
  fractional argument and checks the range.
- The design of the family is in [spec-basic-mksd.md](../spec-basic-mksd.md).
  One housekeeping item is open (D-MKIREUSE, filed 2026-09-29): `hk_mki`
  carries its own float-to-integer conversion where main has one; replacing
  it changes no behaviour, and it waits on a ruling by Joost.

## Tests that cover it

- `make kwsweep` — the everyday rows (length, both bytes and their order, the
  first byte of 258), the error rows for {2, 6, 13}, and the −32768.4 value,
  all against the CF-3300.
- `make nodisk-acceptance` — error 5 on a diskless machine.
- `make kwram` — the RAM-usage comparison.
