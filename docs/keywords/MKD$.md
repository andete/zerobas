<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=CF-3300 disk=yes -->

# `MKD$` — pack a double-precision number into an 8-byte string

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. No known divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`MKD$(x)` returns the double-precision value of `x` as an eight-byte string —
exactly the eight bytes a double variable (`A#`) holds in memory. It is for
putting a number into a random-access file record; [`CVD`](CVD.md) turns the
bytes back into the number. It is a Disk BASIC function, so the reference is
the National CF-3300. zerobas gives the same bytes and the same errors in
every case we have measured. It works exactly like [`MKS$`](MKS$.md), with
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
- **There is no range error.**
- **Without a disk system** (a diskless MSX such as the VG-8020) `MKD$` is
  `Illegal function call` (error 5). A diskless zerobas does the same for the
  call measured there (`LEN(MKD$(1.5))`).

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

## Differences from the reference

None known.

The one rung not yet proven is **RAM usage**: `MKD$` uses the same amount of
free memory on both machines, but the two write different sets of work-area
cells while doing it.

## What we found, and how

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
  parse and widen the argument and offer it to the disk ROM through the
  `MKD$` hook; an unclaimed hook is error 5.
- Disk ROM: `hk_mkfloat` in [disk/kernel.asm](../../disk/kernel.asm), shared
  with `MKS$`.

## Related concepts

- [Numbers](../concepts/numbers.md) — integers, single and double precision

## Tests that cover it

- `make kwsweep` — the length row, the first-byte row for 1.5, the error
  rows for {2, 13}, and `CVD`'s round-trip rows, which build their argument
  with `MKD$`; all against the CF-3300.
- `make nodisk-acceptance` — error 5 on a diskless machine.
- `make kwram` — the RAM-usage comparison.
