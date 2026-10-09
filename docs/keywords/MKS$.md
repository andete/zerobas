<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=CF-3300 disk=yes -->

# `MKS$` — pack a single-precision number into a 4-byte string

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. No known divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`MKS$(x)` returns the single-precision value of `x` as a four-byte string —
exactly the four bytes a single variable (`A!`) holds in memory. It is for
putting a number into a random-access file record; [`CVS`](CVS.md) turns the
bytes back into the number. It is a Disk BASIC function, so the reference is
the National CF-3300. zerobas gives the same bytes and the same errors in
every case we have measured. [`MKI$`](MKI$.md) and [`MKD$`](MKD$.md) are its
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
- **There is no range error.** `CVS(MKS$(1E30))` is 1E+30 and
  `CVS(MKS$(1E-30))` is 1E-30.
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

The whole set of errors `MKS$` can raise on the CF-3300 is {2, 13}; zerobas
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

## Differences from the reference

None known.

The one rung not yet proven is **RAM usage**: `MKS$` uses the same amount of
free memory on both machines, but the two write different sets of work-area
cells while doing it.

## What we found, and how

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
  parse and widen the argument and offer it to the disk ROM through the
  `MKS$` hook; an unclaimed hook is error 5.
- Disk ROM: `hk_mkfloat` in [disk/kernel.asm](../../disk/kernel.asm) rounds
  and packs the value, shared with `MKD$`.

## Related concepts

- [Numbers](../concepts/numbers.md) — integers, single and double precision

## Tests that cover it

- `make kwsweep` — the length row, the first-byte row for 1.5, and the error
  rows for {2, 13}, against the CF-3300.
- `make nodisk-acceptance` — error 5 on a diskless machine.
- `make kwram` — the RAM-usage comparison.
