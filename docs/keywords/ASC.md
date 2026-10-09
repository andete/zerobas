<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `ASC` — the character code of a string's first character

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. No known divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`ASC(a$)` returns the character code, 0 to 255, of the first character of
`a$`. It is the inverse of [`CHR$`](CHR$.md): `ASC(CHR$(n)) = n`. zerobas
behaves exactly like the Philips VG-8020 for every case we have measured,
errors included.

## Syntax

```
ASC(<string expression>)
```

One argument, always.

## Details

- **Only the first character counts.** `ASC("abc")` is 97, the code of `a`;
  the rest of the string is ignored.
- **An empty string has no first character**, so `ASC("")` is
  `Illegal function call` (error 5).
- **A number instead of a string** (`ASC(5)`) is `Type mismatch` (error 13).
  When the number itself fails to compute, its own error wins: the argument is
  evaluated first, and only a clean number is a type mismatch.
- **No argument** (`ASC()`) is `Syntax error` (error 2).
- **A space before the parenthesis is allowed**: `ASC ("A")` is 65.

| you write | you get |
|---|---|
| `ASC("A")` | 65 |
| `ASC("abc")` | 97 |
| `ASC(CHR$(0))` | 0 |
| `ASC("")` | error 5, `Illegal function call` |
| `ASC(5)` | error 13, `Type mismatch` |
| `ASC()` | error 2, `Syntax error` |

The whole set of errors `ASC` can raise is {2, 5, 13}, the same on both
machines.

## Example

```
10 PRINT ASC("A");ASC("abc");ASC(" ")
20 PRINT ASC(CHR$(200))
30 ON ERROR GOTO 60
40 PRINT ASC("")
50 END
60 PRINT "Error";ERR:RESUME NEXT
RUN
 65  97  32
 200
Error 5
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_asc.out`](../../scratchpad/kwdoc_asc.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

None known.

The one rung not yet proven is **RAM usage**: `ASC` changes free memory by
the same amount on both machines, but the VG-8020 writes a few work-area cells
that zerobas does not
([`kwram_full.out`](../../scratchpad/kwram_full.out)). Nothing a program can
observe through `FRE` differs. No keyword has this rung yet.

## What we found, and how

- **`ASC("")` printed a silent `0`** where the VG-8020 raises error 5 (fixed
  2026-07-17, in the follow-up to the string-heap work). It now raises
  `Illegal function call` through the same deferred-error path the math
  functions use: [spec-basic-arrays-slice4a-string-heap.md](../spec-basic-arrays-slice4a-string-heap.md).
- **`ASC(5)` said `Syntax error`** where the reference says `Type mismatch`
  (fixed the same day, 2026-07-17). `LEN` and `VAL` share the code and were
  fixed with it.
- **A failing argument was reported as a type mismatch** (fixed 2026-08-29,
  D-STRTM). The type mismatch used to be armed before the argument was looked
  at, so a division by zero inside it was never reported. Now the argument is
  evaluated first. The measured row is on `LEN`, which shares this code:
  [spec-basic-strtm.md](../spec-basic-strtm.md).
- **Deep nesting crashed.** `LEN(CHR$(ASC(…)))` twelve levels deep crashed
  zerobas, while the references go 32 deep (fixed 2026-09-12, D-SPMERGE).
- **A space before the parenthesis** was checked when the string functions
  were found to reject it (D-NUMSPACE, 2026-09-09): `ASC ("A")` already worked
  on all three machines
  ([`numspace_run.out`](../../scratchpad/numspace_run.out)).

## Where it lives

`ev_ff_asc` in [basic/str-engine.asm](../../basic/str-engine.asm); the
string argument is read by `ev_str_arg` in the same file, which `LEN` and
`VAL` share. The empty-string error is `ev_f_ifc` in
[basic/expr.asm](../../basic/expr.asm).

## Related concepts

- [Strings and string space](../concepts/strings-and-string-space.md) — where string values live

## Tests that cover it

- `make kwsweep` — the everyday row (`ASC("A")`) and the error rows for
  {2, 5, 13}.
- `make string-acceptance` — `ASC("Z")` among the core string verbs.
- `make str-domain-acceptance` — `ASC("")` is its control row for an error
  raised deep inside an expression.
- `make parennest-acceptance` — `LEN(CHR$(ASC(…)))` nested 4 to 16 deep.
- `make kwram` — the RAM-usage comparison.
