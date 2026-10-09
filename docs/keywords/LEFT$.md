<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `LEFT$` — the first characters of a string

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. No known divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`LEFT$(a$,n)` returns the first `n` characters of `a$`. Its mirror is
[`RIGHT$`](RIGHT$.md), and [`MID$`](MID$.md) takes characters from the
middle. zerobas behaves exactly like the Philips VG-8020 for every case we
have measured, errors included.

## Syntax

```
LEFT$(<string expression>,<count>)
```

Both arguments are required.

## Details

- **A count larger than the string gives the whole string**; a count of 0
  gives `""`.
- **The count must be 0 to 255.** It is truncated toward zero, then checked
  in two steps, the same as [`CHR$`](CHR$.md):
  1. outside −32768 to 32767 → `Overflow` (error 6);
  2. inside that range but outside 0 to 255 → `Illegal function call`
     (error 5).
- **A number as the string, or a string as the count**, is `Type mismatch`
  (error 13). The type is checked before the count's range: `LEFT$(1,-1)` is
  error 13, not 5. If the wrong-typed argument fails to compute on its own,
  that error wins.
- **A missing or extra argument** (`LEFT$("AB")`, `LEFT$()`,
  `LEFT$("AB",1,1)`) is `Syntax error` (error 2).
- **Spaces are allowed** before the parenthesis and before the comma:
  `LEFT$ ("ABCDE" ,2)` is `"AB"`.
- **A short slice of a long string needs room only for the slice.** With
  little string space left, `LEFT$` of a 50-character string still works as
  on the reference.

| you write | you get |
|---|---|
| `LEFT$("ABCDE",2)` | `"AB"` |
| `LEFT$("ABC",9)`, `LEFT$("ABC",255)` | `"ABC"` |
| `LEFT$("ABC",0)` | `""` |
| `LEFT$("AB",-1)`, `LEFT$("AB",256)` | error 5, `Illegal function call` |
| `LEFT$("AB",70000)` | error 6, `Overflow` |
| `LEFT$(5,1)`, `LEFT$("AB","A")` | error 13, `Type mismatch` |
| `LEFT$("AB")`, `LEFT$()`, `LEFT$("AB",1,1)` | error 2, `Syntax error` |

The whole set of errors `LEFT$` can raise is {2, 5, 6, 13}, the same on both
machines.

## Example

```
10 A$="ABCDE"
20 PRINT LEFT$(A$,2)
30 PRINT LEFT$(A$,9);LEN(LEFT$(A$,0))
40 ON ERROR GOTO 80
50 PRINT LEFT$(A$,256)
60 PRINT LEFT$(A$,70000)
70 END
80 PRINT "Error";ERR:RESUME NEXT
RUN
AB
ABCDE 0
Error 5
Error 6
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_left_s.out`](../../scratchpad/kwdoc_left_s.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

None known.

The one rung not yet proven is **RAM usage**: `LEFT$` changes free memory by
the same amount on both machines, but the set of work-area cells written
differs ([`kwram_full.out`](../../scratchpad/kwram_full.out)). Nothing a
program can observe through `FRE` differs. No keyword has this rung yet.

## What we found, and how

- **Out-of-range counts were accepted silently** (fixed 2026-07-28,
  D-MISS-2). `LEFT$`, `RIGHT$`, `MID$` and `CHR$` computed an answer from a
  count the VG-8020 rejects. The two-step rule above, and its exact boundary
  (−32768 is error 5, not 6), come from that measurement:
  [spec-basic-str-domain.md](../spec-basic-str-domain.md).
- **`PRINT LEFT$(5,2)` said `Syntax error`** where both references say
  `Type mismatch` (fixed 2026-08-29, D-LEFTTM). The error was armed without
  looking at the argument; the reference evaluates the argument and reports
  what it raises, so `LEFT$(0*(1/0)+1)` is `Division by zero` (error 11):
  [spec-basic-lefttm.md](../spec-basic-lefttm.md).
- **A space before the parenthesis or the comma was a syntax error** (fixed
  2026-09-09, D-FNSPACE). Both reference machines accept
  `LEFT$ ("ABCDE",2)` and `LEFT$("ABCDE" ,2)`
  ([`fnspace_after2.out`](../../scratchpad/fnspace_after2.out)).
- **A slice of a big string ran out of string space** where the reference
  had room (fixed 2026-09-26, D-SLICEOOM). zerobas copied the whole source
  before slicing it, needing 53 bytes where the reference needs 3. Now only
  the result is allocated, for a plain variable and for an array element
  ([`sliceoom_run.out`](../../scratchpad/sliceoom_run.out)).

## Where it lives

`str_fn_left` in [basic/str-engine.asm](../../basic/str-engine.asm). It
shares its opening (`str_arg_open`) with `RIGHT$` and `MID$`, and its count
clamp (`str_lr_count`) with `RIGHT$`. The count is checked by the shared
`eval_byte_arg` in [basic/interp.asm](../../basic/interp.asm). The slice is
made by `she_snap_slice` and `she_slice_new` in
[sub/strheap.asm](../../sub/strheap.asm).

## Tests that cover it

- `make str-domain-acceptance` — the count's range, both error kinds, and
  the order of checks.
- `make string-acceptance` — `LEFT$` among the core string verbs, including
  `LEFT$` of a concatenation.
- `make kwsweep` — the everyday row and the error rows for {2, 5, 6, 13}.
- `make kwram` — the RAM-usage comparison.
