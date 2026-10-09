<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `DEFINT` — make variables integers by their first letter

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. No known divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`DEFINT A-C` makes every variable whose name starts with `A`, `B` or `C`, and
has no type suffix, an integer — as if you had written `A%`, `B%`, `C%`.
Its siblings do the same for the other types: [`DEFSNG`](DEFSNG.md) (single
precision), [`DEFDBL`](DEFDBL.md) (double precision) and
[`DEFSTR`](DEFSTR.md) (string). This page holds the rules all four share.
zerobas behaves exactly like the Philips VG-8020 for every case we have
measured.

## Syntax

```
DEFINT <letter>[-<letter>][,<letter>[-<letter>]...]
```

A single letter (`DEFINT I`), a range (`DEFINT A-C`), or a list of either
(`DEFINT A-C,I,N`).

## Details

Rules shared by all four `DEF` type statements:

- **Without any `DEF`, an unsuffixed variable is double precision.** `A=1/3`
  prints `.33333333333333`, fourteen digits, the same as `A#`.
- **Only the first letter counts**, and only for names without a suffix. A
  suffix always wins: after `DEFINT A`, `A#` is still double.
- **The type is looked up every time a name is used**, not when the variable
  was created. So `A=7:DEFINT A:PRINT A` prints 0: the `A` that holds 7 is the
  double one, and the `A` you now name is a new integer.
- **The last `DEF` for a letter wins**: `DEFINT A:DEFDBL A` leaves `A` double.
- **What ends an item is `,`, `:` or the end of the line**, nothing else.

For `DEFINT` itself:

- **A value stored in an integer variable loses its fraction**: after
  `DEFINT A`, `A=1.7` stores 1.
- **Loop and `READ` variables follow the rule too**: `DEFINT I:FOR I=1 TO 3:NEXT`
  leaves `I` at 4.

### Errors

Every malformed `DEF` statement is `Syntax error` (error 2) — the only error
the VG-8020 raises for any of the four, in either form:

| you write | why |
|---|---|
| `DEFINT 5`, `DEFINT 1` | not a letter |
| `DEFINT A-`, `DEFINT A-1` | the range has no end letter |
| `DEFINT Z-A` | a reversed range |
| `DEFINT` | nothing to declare |
| `DEFINT AB`, `DEFINT AC=7` | something glued to the item |

## Example

```
10 DEFINT A-C,N
20 A=1.7:N=7/2:D=1.7:B#=1.5
30 PRINT A;N;D;B#
40 ON ERROR GOTO 70
50 DEFINT Z-A
60 END
70 PRINT "Error";ERR:RESUME NEXT
RUN
 1  3  1.7  1.5
Error 2
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_defint.out`](../../scratchpad/kwdoc_defint.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

`A` and `N` are integers, `D` is outside the declared letters and stays double,
and `B#` keeps its own suffix.

## Differences from the reference

None known.

The one rung not yet proven is **RAM usage**: `DEFINT` uses the same amount of
free memory on both machines, but the two machines write different cells of
the documented work area while doing it, and one cell ends on a different
value.

## What we found, and how

- **The four `DEF` statements arrived on 2026-07-12**, together with typed
  variables. A review the same day found that a `DEFINT` loop or `READ`
  variable was stored as one type and read back as another, so it read 0; that
  was fixed the same day.
- **`DEFINT` was stored differently from the reference** (fixed 2026-08-18 and
  2026-08-19, D-DEFINTTOK and D-DEFTYPETOK). zerobas stored it as `DEF` plus
  the letters `INT`, and had no entry at all for the other three; the reference
  stores each as a single token of its own. For `DEFSTR` the missing entry also
  changed how the argument after it was read. All four now store the
  reference's bytes, argument included.
- **`DEFINT AC=7` ran `C=7`** (fixed 2026-08-31, D-DEFCORNER). After an item,
  zerobas accepted anything as its end and ran the rest as a new statement.
  `DEFINT AB` had agreed with the reference all along — both said
  `Syntax error` — but for a different reason, which a row designed to tell the
  two apart exposed: [spec-basic-defcorner.md](../spec-basic-defcorner.md).
- **The test checks the effect, not the parse** (2026-09-12, D-KWDRAIN): it
  expects 1, not 1.7, so a `DEFINT` that parsed and did nothing fails. The
  range row (2026-09-14) checks a letter only the range covers.

## Where it lives

`ex_deftype` in [basic/usr.asm](../../basic/usr.asm) serves all four
statements; it hands the line to the sub-ROM routine `deftype_tenant` in
[sub/deftype.asm](../../sub/deftype.asm), which reads which statement it was
from the token, checks the letters and fills the 26-entry type table. Each
variable reference consults that table (`deftbl_lookup` in
[basic/vars.asm](../../basic/vars.asm)).

## Related concepts

- [Variables](../concepts/variables.md) — names, types, arrays, and where they live

## Tests that cover it

- `make float-acceptance` — the type rules: default double, ranges, lists,
  suffix wins, redeclaration, and the loop/`READ` regression rows.
- `make kwsweep` — the single-letter and range rows, and the error rows
  `DEFINT 5` and `DEFINT A-` (2).
- `make kwram` — the RAM-usage comparison.
