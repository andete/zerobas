<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `ERASE` — remove an array

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. No known divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`ERASE A` removes the array `A` and frees its memory. Afterwards the name is
as if it had never been declared: a new [`DIM`](DIM.md) works without
`Redimensioned array`, and the new array starts out cleared. zerobas behaves
like the Philips VG-8020 in every case we have measured, errors included.

## Syntax

```
ERASE <array name>[,<array name>]...
```

Just the name, with its type suffix if it has one — no parentheses, no
subscripts.

## Details

- **The type suffix is part of the name**: `ERASE A` removes the default-type
  array `A` and leaves `A%` and `A$` alone.
- **Names are removed one by one, left to right.** In `ERASE P,Q` with no
  array `Q`, `P` is removed and then the statement fails on `Q`.
- **An array that does not exist is `Illegal function call`** (error 5) — never
  declared, already erased, or of another type.
- **Anything that is not a plain name is `Syntax error`** (error 2): a bare
  `ERASE`, `ERASE A(1)`, `ERASE A()`, `ERASE 5`, or a stray comma.

| you write | you get |
|---|---|
| `ERASE A` (`A` exists) | `A` is gone |
| `ERASE A` (no array `A`), `ERASE A` twice | 5 `Illegal function call` |
| `ERASE A%` when only `A` exists | 5 `Illegal function call` |
| `ERASE`, `ERASE A(1)`, `ERASE A,` | 2 `Syntax error` |

The whole set of errors `ERASE` can raise is {2, 5}, the same on both machines.

## Example

```
10 DIM A(5):A(1)=7
20 ERASE A
30 DIM A(5):PRINT A(1)
40 ON ERROR GOTO 70
50 ERASE A,Z
60 END
70 PRINT "Error";ERR:RESUME NEXT
RUN
 0
Error 5
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_erase.out`](../../scratchpad/kwdoc_erase.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

None known.

The one rung not yet proven is **RAM usage**.

## What we found, and how

- **`ERASE` arrived on 2026-07-15**, with its two kinds of error measured
  first. A review before it shipped caught `ERASE A$` removing the *numeric*
  array `A`: inside zerobas the `$` name had been given the same type code as a
  default-type number. The string type is now kept apart, and a test for it
  was added ([spec-basic-arrays-slice2-erase.md](../spec-basic-arrays-slice2-erase.md)).
- **Erasing stops where it fails, and that was checked against the reference**
  (2026-09-09, D-PARTSTATE). Some statements are all-or-nothing on the
  reference; `ERASE P,Q` is not — `P` is gone after the error on both
  references ([readings](../../scratchpad/partialstate_run.out)).
- **The keyword sweep's first `ERASE` row proved nothing** (2026-09-14,
  D-KWBATCH5): it printed a fixed marker, which an `ERASE` that did nothing
  prints just as well. The row that counts now reads the effect — after
  `ERASE`, a second `DIM` succeeds and the element reads 0, where without it
  the `DIM` is `Redimensioned array`.

## Where it lives

`ex_erase` in [basic/arrays.asm](../../basic/arrays.asm) reads the names; the
array engine's `aeng_erase` in [sub/arrays.asm](../../sub/arrays.asm) finds
the array and closes the gap it leaves.

## Related concepts

- [Variables](../concepts/variables.md) — names, types, arrays, and where they live

## Tests that cover it

- `make array-acceptance` — erasing, re-declaring, types and both kinds of
  error.
- `make kwsweep` — the effect row and the error rows for {2, 5}.
- `make kwram` — the RAM-usage comparison.
