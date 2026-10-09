<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `DEFSNG` — make variables single precision by their first letter

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. No known divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`DEFSNG S` makes every unsuffixed variable whose name starts with `S` a
single-precision number — as if you had written `S!`. On MSX this is a real
change: without it, a plain variable is *double* precision. zerobas behaves
exactly like the Philips VG-8020 for every case we have measured.

## Syntax

```
DEFSNG <letter>[-<letter>][,<letter>[-<letter>]...]
```

## Details

- **The rules are those of [`DEFINT`](DEFINT.md)**: first letter only, a
  suffix always wins, the last `DEF` for a letter wins, and the type is looked
  up at every use.
- **A single-precision value keeps six digits**, rounded: after `DEFSNG A`,
  `A=1/3` prints `.333333`, where a plain (double) `A` prints
  `.33333333333333`.
- **`DEFSNG` undoes an earlier `DEF`** for the same letters:
  `DEFINT A-C:DEFSNG A-C:C=1.5` keeps 1.5.
- **Errors:** every malformed `DEFSNG` (`DEFSNG 5`, `DEFSNG A-`, a reversed
  range) is `Syntax error` (error 2), the only error the VG-8020 raises for it.
  The full list is on the [`DEFINT`](DEFINT.md) page.

## Example

```
10 A=1/3
20 DEFSNG S
30 S=1/3
40 PRINT A
50 PRINT S
60 ON ERROR GOTO 90
70 DEFSNG 5
80 END
90 PRINT "Error";ERR:RESUME NEXT
RUN
 .33333333333333
 .333333
Error 2
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_defsng.out`](../../scratchpad/kwdoc_defsng.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

None known.

The one rung not yet proven is **RAM usage**: `DEFSNG` uses the same amount of
free memory on both machines, but the two machines write different cells of
the documented work area while doing it, and one cell ends on a different
value.

## What we found, and how

- **`DEFSNG` arrived on 2026-07-12** with the other `DEF` statements. Measuring
  typed variables at the time showed that MSX's default is double precision,
  correcting an earlier doubt that it was single.
- **`DEFSNG` had no keyword entry of its own** until 2026-08-19 (D-DEFTYPETOK);
  it was stored as `DEF` plus the letters `SNG`. It is now one token, as on
  the reference.
- **A malformed item could run its tail as a statement** (fixed 2026-08-31,
  D-DEFCORNER, for all four `DEF` statements — see [`DEFINT`](DEFINT.md)).
- **The range test sets the letters to integer first** (2026-09-14, D-KWBATCH6):
  it runs `DEFINT A-C` before `DEFSNG A-C`, so only a `DEFSNG` that really
  reached `C` prints 1.5 instead of 1.

## Where it lives

The same code as `DEFINT`: `ex_deftype` in [basic/usr.asm](../../basic/usr.asm)
and `deftype_tenant` in [sub/deftype.asm](../../sub/deftype.asm).

## Tests that cover it

- `make float-acceptance` — `DEFSNG A:A=1/3` against the reference, among the
  shared type rules.
- `make kwsweep` — the single-letter and range rows, and the error rows
  `DEFSNG 5` and `DEFSNG A-` (2).
- `make kwram` — the RAM-usage comparison.
