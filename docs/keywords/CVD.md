<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=CF-3300 disk=yes -->

# `CVD` — read a double-precision number back from an 8-byte string

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. No known divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`CVD(s$)` takes the first eight bytes of a string and returns the
double-precision number they hold. It is the reading half of
[`MKD$`](MKD$.md): `CVD(MKD$(x))` is `x`, all fourteen digits. It is a Disk
BASIC function, so the reference is the National CF-3300; zerobas gives the
same values and the same errors in every case we have measured. It shares its
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

## Differences from the reference

None known.

The one rung not yet proven is **RAM usage**: `CVD` uses the same amount of
free memory on both machines, but the two write different sets of work-area
cells while doing it.

## What we found, and how

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
