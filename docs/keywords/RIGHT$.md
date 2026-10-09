<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `RIGHT$` — the last characters of a string

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. No known divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`RIGHT$(a$,n)` returns the last `n` characters of `a$`. It is the mirror of
[`LEFT$`](LEFT$.md) and follows the same rules for its count; see that page
for the full story. zerobas behaves exactly like the Philips VG-8020 for every
case we have measured, errors included.

## Syntax

```
RIGHT$(<string expression>,<count>)
```

Both arguments are required.

## Details

- **A count larger than the string gives the whole string**; a count of 0
  gives `""`.
- **The count must be 0 to 255**: outside −32768 to 32767 it is `Overflow`
  (error 6), otherwise outside 0 to 255 it is `Illegal function call`
  (error 5). A fraction is truncated toward zero first.
- **A number as the string, or a string as the count**, is `Type mismatch`
  (error 13).
- **A missing or extra argument** is `Syntax error` (error 2).
- **Spaces are allowed** before the parenthesis and before the comma:
  `RIGHT$ ("ABCDE",2)` is `"DE"`.

| you write | you get |
|---|---|
| `RIGHT$("ABCDE",2)` | `"DE"` |
| `RIGHT$("ABC",9)` | `"ABC"` |
| `RIGHT$("ABC",0)` | `""` |
| `RIGHT$("AB",-1)`, `RIGHT$("AB",256)` | error 5, `Illegal function call` |
| `RIGHT$("AB",70000)` | error 6, `Overflow` |
| `RIGHT$(5,1)`, `RIGHT$("AB","A")` | error 13, `Type mismatch` |
| `RIGHT$("AB")`, `RIGHT$()`, `RIGHT$("AB",1,1)` | error 2, `Syntax error` |

The whole set of errors `RIGHT$` can raise is {2, 5, 6, 13}, the same on both
machines.

## Example

```
10 A$="ABCDE"
20 PRINT RIGHT$(A$,2)
30 PRINT RIGHT$(A$,9);LEN(RIGHT$(A$,0))
40 ON ERROR GOTO 80
50 PRINT RIGHT$(A$,-1)
60 PRINT RIGHT$(5,1)
70 END
80 PRINT "Error";ERR:RESUME NEXT
RUN
DE
ABCDE 0
Error 5
Error 13
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_right_s.out`](../../scratchpad/kwdoc_right_s.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

None known.

The one rung not yet proven is **RAM usage**: `RIGHT$` changes free memory
by the same amount on both machines, but the set of work-area cells written
differs ([`kwram_full.out`](../../scratchpad/kwram_full.out)). Nothing a
program can observe through `FRE` differs. No keyword has this rung yet.

## What we found, and how

`RIGHT$` shares its argument handling with `LEFT$`, and every finding there
applies here too; the [`LEFT$`](LEFT$.md) page has the details.

- **Out-of-range counts were accepted silently** (fixed 2026-07-28,
  D-MISS-2): [spec-basic-str-domain.md](../spec-basic-str-domain.md).
- **`PRINT RIGHT$(5,2)` said `Syntax error`** instead of `Type mismatch`
  (fixed 2026-08-29, D-LEFTTM): [spec-basic-lefttm.md](../spec-basic-lefttm.md).
- **`RIGHT$ ("ABCDE",2)` and `RIGHT$("ABCDE" ,2)` were syntax errors** (fixed
  2026-09-09, D-FNSPACE)
  ([`fnspace_after2.out`](../../scratchpad/fnspace_after2.out)).
- **A slice of a big string could run out of string space** where the
  reference had room (fixed 2026-09-26, D-SLICEOOM). The fix is in the code
  the three slicing functions share; the tight-memory rows were measured on
  `LEFT$` and `MID$`
  ([`sliceoom_run.out`](../../scratchpad/sliceoom_run.out)).

## Where it lives

`str_fn_right` in [basic/str-engine.asm](../../basic/str-engine.asm). It
shares `str_arg_open` with `LEFT$` and `MID$`, and `str_lr_count` with
`LEFT$`; the count is checked by `eval_byte_arg` in
[basic/interp.asm](../../basic/interp.asm).

## Tests that cover it

- `make str-domain-acceptance` — the count's range and both error kinds.
- `make string-acceptance` — `RIGHT$("HELLO",2)` among the core string verbs.
- `make kwsweep` — the everyday row and the error rows for {2, 5, 6, 13}.
- `make kwram` — the RAM-usage comparison.
