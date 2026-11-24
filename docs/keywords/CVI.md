<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->
<!-- example: reference=CF-3300 disk=yes -->

# `CVI` — read an integer back from a 2-byte string

> **Spec:** DRAFT 1 (2026-11-24) — 52 cases measured on the National CF-3300 (Disk BASIC, the reference) against zerobas's
> disk build, and on the Philips VG-8020 (no Disk BASIC) against its diskless one, by typed BASIC
> ([`kmkcv.py`](../../probes/basic/spec/kmkcv.py)); every rule is executable and every recorded output is read by one.
> Not yet reviewed ([the keyword plan](spec-plan.md)).
>
> **Status (2026-11-24):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✗ (an error code differ). 1 difference, found by the spec probe (below).
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`CVI(s$)` takes the first two bytes of a string and returns the integer they
hold, low byte first. It is the reading half of [`MKI$`](MKI$.md):
`CVI(MKI$(n))` is `n`. Programs use it on fields read from a random-access
file. It is a Disk BASIC function, so the reference is the National CF-3300; zerobas gives the same values, and differs in an error code (below).

## Syntax

```
CVI(<string expression>)
```

One argument, always.

## Details

- **Low byte first**: `CVI("AB")` is 16961, which is 66*256+65 ("B" is 66,
  "A" is 65).
- **The full integer range comes back**, sign included:
  `CVI(MKI$(-1))` is −1 and `CVI(MKI$(32767))` is 32767.
- **Only the first two bytes count.** A longer string is fine and the rest is
  ignored: `CVI(MKS$(1.5))`, given four bytes, is 5441.
- **A string shorter than two bytes** (`CVI("A")`, `CVI("")`) is
  `Illegal function call` (error 5). zerobas once read past the end of the
  string here; it no longer does.
- **A number instead of a string** (`CVI(5)`) is `Type mismatch` (error 13).
  But when the argument itself goes wrong first, its own error wins:
  `CVI(LEFT$("AB"))` is `Syntax error` and `CVI(0*(1/0)+1)` is
  `Division by zero`, on the CF-3300 and here.
- **Without a disk system** (a diskless MSX such as the VG-8020) `CVI` is
  `Illegal function call` (error 5): the keyword is known, but the function
  belongs to the disk ROM. A diskless zerobas does the same for the calls
  measured there (`CVI("AB")`, `CVI(MKI$(258))`).

| you write | you get |
|---|---|
| `CVI("AB")` | 16961 |
| `CVI(MKI$(-1))` | −1 |
| `CVI(MKS$(1.5))` | 5441 (first two of four bytes) |
| `CVI("A")`, `CVI("")` | error 5, `Illegal function call` |
| `CVI(5)` | error 13, `Type mismatch` |
| `CVI()`, `CVI("AB","AB")` | error 2, `Syntax error` |
| `CVI("AB")` on a machine without a disk ROM | error 5, `Illegal function call` |

The whole set of errors `CVI` can raise on the CF-3300 is {2, 5, 13}; zerobas
raises the same set.

## Example

```
10 ON ERROR GOTO 80
20 PRINT CVI(MKI$(258));CVI(MKI$(-1))
30 PRINT CVI("AB")
40 PRINT CVI(MKS$(1.5))
50 A=CVI("A")
60 A=CVI(5)
70 END
80 PRINT "Error";ERR:RESUME NEXT
RUN
 258 -1
 16961
 5441
Error 5
Error 13
```

Run on the CF-3300 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_cvi.out`](../../scratchpad/kwdoc_cvi.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## The specification

Reference: the National CF-3300's Disk BASIC, against zerobas on the disk machine
(`C-BIOS_MSX1_EU_REPACK_DISK`); and, for the diskless rules, the Philips VG-8020's MSX BASIC against zerobas
on the diskless machine (`C-BIOS_MSX1_EU_REPACK_NODISK`).

**How to read the rules below.** Every rule is a sentence AND a check
([`probes/basic/spec/cvi_rules.py`](../../probes/basic/spec/cvi_rules.py), model in
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
reference's cases: “a short string padded with zero bytes” is FALSE on 2 of the 17 cases R-CVI-BYTES selects (e.g. KMC DCV 0); “the last 2 bytes, not the first” on 11 (KMC DCV 3); “exactly 2 bytes required” on 11 (KMC DCV 3); “without Disk BASIC the argument's type checked first (13) -- zerobas's” on 1 of R-CVI-NODISK's 22 (KMC FX 39).

<!-- RULES BEGIN -->
<!-- GENERATED by tools/spec_rules.py from probes/basic/spec/cvi_rules.py -- do not edit; `python3 tools/spec_rules.py probes/basic/spec/cvi_rules.py --write` -->

**6 rules; 6 hold on the reference. Of the 364 recorded outputs (each case's error from the statement and from its USR form, R's 8 bytes, S$'s length and first 8 bytes, the result's type as USR saw it and the result's own bytes): 364 read by a rule's check, 0 declared NOT evidence (below), 0 unread.**

#### 1. With Disk BASIC (the CF-3300)

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-CVI-BYTES** CVI(s) is the first 2 bytes of s, as they are -- an integer, low byte first, whatever they hold (a zero exponent byte with digits, a non-BCD nibble: unchanged); bytes beyond the 2th are ignored; a string shorter than 2 bytes is error 5 (Illegal function call), from `R=CVI(s)` and `USR(CVI(s))` alike. | 17 | ✓ | ✓ |
| **R-CVI-EXPR** The argument may be any string expression: CVI("A"+...+"H") is the bytes 41 42 ...; CVI(MID$(S$,3)) starts at S$'s third byte; and CVI(MKI$(x)) gives x back, byte for byte. | 3 | ✓ | ✓ |

#### 2. Forms and errors

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-CVI-TYPE** A number as the argument, or the result assigned to a string variable, is error 13 (Type mismatch). | 2 | ✓ | ✓ |
| **R-CVI-SYNTAX** No argument, a second argument, no closing parenthesis, or the name without a parenthesis is error 2 (Syntax error) -- with or without Disk BASIC. | 8 | ✓ | ✓ |

#### 3. Without Disk BASIC (the VG-8020)

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-CVI-NODISK** Without Disk BASIC every call of CVI whose argument computes is error 5 (Illegal function call) -- whatever the argument, a number included (5, not 13), and the result assigned to the wrong type too; nothing is assigned and USR is not reached. | 22 | ✓ | ✗ 1: KMC FX 39 |

#### 4. The result stored

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-CVI-ASSIGN** `R=CVI(s)` with R a double stores the result as a double: an integer by its value, a single's 4 bytes then four zero bytes -- an exponent-0 one too (CVS of 00 10 00 00 leaves R 00 10 00 00 00 00 00 00) --, a double's 8; after an error R keeps its sentinel -12345. Read in every case. | 52 | ✓ | ✓ |

<!-- RULES END -->

## Differences from the reference

- **Without Disk BASIC, `CVI(5)` is error 13 here, 5 on the VG-8020** ([D-DISKFNTYPE](../../todo/open/D-DISKFNTYPE.md); rule R-CVI-NODISK, KMC FX 39): the reference refuses every call with 5 before it looks at the argument's type.

The one rung not yet proven is **RAM usage**: `CVI` uses the same amount of
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

- **The spec probe** (D-KWSPEC, 2026-11-24): CVI takes the first 2 bytes of a string of at least 2, as they are; shorter is error 5. Without Disk BASIC every call whose argument computes is error 5, a wrong-type argument included. zerobas agrees on every value; its differences are error codes (below).
- **Three wrong answers in one function** (fixed 2026-08-31, D-CVITM).
  `CVI(5)` was `Syntax error` instead of `Type mismatch`; `CVI("A")` read one
  byte of the string and one byte of whatever followed it, and answered a
  plausible 8769 instead of error 5; and the first fix briefly turned `CVI()`
  into `Type mismatch`, because an empty argument has to be judged before the
  type question is asked
  ([spec-basic-cvitm.md](../spec-basic-cvitm.md)).
- **That fix had a hole** (fixed the same day, D-CVISTRTM): `CVI(0*(1/0)+1)`
  answered `Type mismatch` where the CF-3300 says `Division by zero`. The
  argument is now evaluated first, so its own error wins
  ([spec-basic-cvistrtm.md](../spec-basic-cvistrtm.md)).
- **Which machine is the reference was settled by measurement** (2026-09-02).
  The VG-8020 answers error 5 to every `CVI`. The National CF-3000, a
  cassette machine whose main ROM is byte-identical to the CF-3300's, also
  answers 5 — so the difference is the disk ROM, and the CF-3300 is the
  machine that can judge `CVI`. The same argument had settled it for `LSET`
  the same day ([spec-basic-lsetref.md](../spec-basic-lsetref.md)).
- **A diskless zerobas answered `CVI`** where a diskless MSX refuses (fixed
  2026-09-03, D-MKHOOK): it now goes through its documented hook, and with no
  disk ROM nobody answers
  ([spec-basic-nodisk.md](../spec-basic-nodisk.md) §10).
- **The conversion moved into the disk ROM** (2026-09-17, D-CVMOVE), and that
  was a compatibility fix: main had redone the conversion after the hook
  returned, so a different disk ROM's answer would have been overwritten. The
  first version of the move broke `CVI(MKI$(258))` — the two functions shared
  a scratch buffer, and a round trip made it overwrite its own input. Caught
  by the test rows before it shipped.

## Where it lives

- Main ROM: `ev_ff_cvi` / `ev_ff_cv` in [basic/expr.asm](../../basic/expr.asm)
  parse the argument, check its length and type, and offer it to the disk ROM
  through the `CVI` hook; an unclaimed hook is error 5.
- Disk ROM: `hk_cv` in [disk/kernel.asm](../../disk/kernel.asm) does the
  conversion. [`CVS`](CVS.md) and [`CVD`](CVD.md) share both routines, with a
  width of 4 and 8 bytes.

## Tests that cover it

- `make kwsweep` — the everyday row (`CVI(MKI$(7))`), the sign and range row
  (−1 and 32767), the short-string row, and the error rows for {2, 5, 13},
  all against the CF-3300.
- `make nodisk-acceptance` — error 5 on a diskless machine.
- `make kwram` — the RAM-usage comparison.
