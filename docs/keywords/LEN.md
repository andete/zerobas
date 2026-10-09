<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `LEN` — the length of a string

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. No known divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`LEN(a$)` returns the number of characters in `a$`, from 0 for an empty
string to 255, the longest string BASIC can hold. zerobas behaves exactly like
the Philips VG-8020 for every case we have measured, errors included.

## Syntax

```
LEN(<string expression>)
```

One argument, always.

## Details

- **Every character counts**, spaces and control characters included:
  `LEN(CHR$(0))` is 1 and `LEN(STR$(12))` is 3, because `STR$` keeps the
  leading space.
- **The argument can be any string expression** — a variable, a literal, a
  concatenation or another function's result.
- **A number instead of a string** (`LEN(5)`) is `Type mismatch` (error 13).
  If the number itself fails to compute, its own error is reported instead:
  `LEN(0*(1/0)+1)` is `Division by zero` (error 11).
- **No argument** (`LEN()`) is `Syntax error` (error 2).
- **A space before the parenthesis is allowed**: `LEN ("ABCDEFG")` is 7.

| you write | you get |
|---|---|
| `LEN("ABCDE")` | 5 |
| `LEN("")` | 0 |
| `LEN(5)` | error 13, `Type mismatch` |
| `LEN(0*(1/0)+1)` | error 11, `Division by zero` |
| `LEN()` | error 2, `Syntax error` |

The whole set of errors `LEN` can raise is {2, 13}, the same on both machines.
(An error inside the argument, like the division by zero above, belongs to
the expression, not to `LEN`.)

## Example

```
10 A$="HELLO"
20 PRINT LEN(A$);LEN("");LEN(A$+A$)
30 PRINT LEN(STR$(12))
40 ON ERROR GOTO 70
50 PRINT LEN(5)
60 END
70 PRINT "Error";ERR:RESUME NEXT
RUN
 5  0  10
 3
Error 13
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_len.out`](../../scratchpad/kwdoc_len.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

None known.

The one rung not yet proven is **RAM usage**: `LEN` changes free memory by
the same amount on both machines, but the VG-8020 writes a few work-area cells
that zerobas does not
([`kwram_full.out`](../../scratchpad/kwram_full.out)). Nothing a program can
observe through `FRE` differs. No keyword has this rung yet.

## What we found, and how

- **`LEN(5)` said `Syntax error`** where the reference says `Type mismatch`
  (fixed 2026-07-17, with `ASC(5)` and `VAL(5)`, which share the code).
- **The type mismatch hid the argument's own error** (fixed 2026-08-29,
  D-STRTM). It was armed before the argument was evaluated, so
  `LEN(0*(1/0)+1)` said 13 where both references say 11. The fix was the
  order — evaluate first, then complain:
  [spec-basic-strtm.md](../spec-basic-strtm.md).
- **Deep nesting crashed.** `LEN(CHR$(ASC(…)))` twelve levels deep crashed
  zerobas and sixteen gave a nonsense error, while both references go 32 deep.
  The expression evaluator ran out of stack; it now shares one region with the
  control frames, as the references do (fixed 2026-09-12, D-SPMERGE):
  [spec-basic-spmerge.md](../spec-basic-spmerge.md).
- **A space before the parenthesis** was checked when other string functions
  were found to reject it (D-NUMSPACE, 2026-09-09): `LEN ("ABCDEFG")` already
  worked on all three machines
  ([`numspace_run.out`](../../scratchpad/numspace_run.out)).

## Where it lives

`ev_ff_len` in [basic/str-engine.asm](../../basic/str-engine.asm); the
string argument is read by `ev_str_arg` in the same file, shared with `ASC`
and `VAL`. The deferred type mismatch is `ev_f_tmm` in
[basic/expr.asm](../../basic/expr.asm).

## Related concepts

- [Strings and string space](../concepts/strings-and-string-space.md) — where string values live

## Tests that cover it

- `make kwsweep` — the everyday row (`LEN("ab")`) and the error rows for
  {2, 13}.
- `make string-acceptance` — `LEN("ABCDE")` among the core string verbs.
- `make str-domain-acceptance` — `LEN` is the readout of most of its rows,
  and its control row.
- `make parennest-acceptance` — `LEN(CHR$(ASC(…)))` nested 4 to 16 deep.
- `make kwram` — the RAM-usage comparison.
