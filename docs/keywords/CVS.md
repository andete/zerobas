<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=CF-3300 disk=yes -->

# `CVS` — read a single-precision number back from a 4-byte string

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. No known divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`CVS(s$)` takes the first four bytes of a string and returns the
single-precision number they hold. It is the reading half of
[`MKS$`](MKS$.md): `CVS(MKS$(x))` is `x` rounded to six digits. It is a Disk
BASIC function, so the reference is the National CF-3300; zerobas gives the
same values and the same errors in every case we have measured. It shares its
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
  `Illegal function call` (error 5). A diskless zerobas does the same for the
  call measured there (`CVS(MKS$(1.5))`).

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

## Differences from the reference

None known.

The one rung not yet proven is **RAM usage**: `CVS` uses the same amount of
free memory on both machines, but the two write different sets of work-area
cells while doing it.

## What we found, and how

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
