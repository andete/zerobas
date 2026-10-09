<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `DEFDBL` — make variables double precision by their first letter

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. No known divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`DEFDBL D` makes every unsuffixed variable whose name starts with `D` a
double-precision number — as if you had written `D#`. Since double is already
MSX's default, `DEFDBL` is mostly used to take letters back after a wider
`DEFINT` or `DEFSNG`. zerobas behaves exactly like the Philips VG-8020 for
every case we have measured.

## Syntax

```
DEFDBL <letter>[-<letter>][,<letter>[-<letter>]...]
```

## Details

- **The rules are those of [`DEFINT`](DEFINT.md)**: first letter only, a
  suffix always wins, the last `DEF` for a letter wins, and the type is looked
  up at every use.
- **A double-precision value keeps fourteen digits**: after `DEFDBL A`, `A=1/3`
  prints `.33333333333333`.
- **`DEFINT A:DEFDBL A`** leaves `A` double — the later statement wins.
- **Errors:** every malformed `DEFDBL` (`DEFDBL 5`, `DEFDBL A-`, a reversed
  range) is `Syntax error` (error 2), the only error the VG-8020 raises for it.
  The full list is on the [`DEFINT`](DEFINT.md) page.

## Example

```
10 DEFINT A-Z
20 DEFDBL D
30 A=1/3:D=1/3
40 PRINT A;D
50 ON ERROR GOTO 80
60 DEFDBL A-
70 END
80 PRINT "Error";ERR:RESUME NEXT
RUN
 0  .33333333333333
Error 2
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_defdbl.out`](../../scratchpad/kwdoc_defdbl.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

Every letter is made integer first, so `A` holds 0; `DEFDBL D` gives `D` back
its full precision.

## Differences from the reference

None known.

The one rung not yet proven is **RAM usage**: `DEFDBL` uses the same amount of
free memory on both machines, but the two machines write different cells of
the documented work area while doing it.

## What we found, and how

- **`DEFDBL` arrived on 2026-07-12** with the other `DEF` statements.
- **`DEFDBL` had no keyword entry of its own** until 2026-08-19 (D-DEFTYPETOK);
  it was stored as `DEF` plus the letters `DBL`. It is now one token, as on
  the reference.
- **A malformed item could run its tail as a statement** (fixed 2026-08-31,
  D-DEFCORNER, for all four `DEF` statements — see [`DEFINT`](DEFINT.md)).
- **The range test needs a value only double precision can hold** (2026-09-14,
  D-KWBATCH6). `1.5` is exact in single precision too, so it could not show
  that a letter had really become double; `1/3`, with its fourteen digits, can.

## Where it lives

The same code as `DEFINT`: `ex_deftype` in [basic/usr.asm](../../basic/usr.asm)
and `deftype_tenant` in [sub/deftype.asm](../../sub/deftype.asm).

## Related concepts

- [Variables](../concepts/variables.md) — names, types, arrays, and where they live

## Tests that cover it

- `make float-acceptance` — `DEFDBL A:A=1/3` and the redeclaration row, among
  the shared type rules.
- `make kwsweep` — the single-letter and range rows, and the error rows
  `DEFDBL 5` and `DEFDBL A-` (2).
- `make kwram` — the RAM-usage comparison.
