<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `STRING$` — a character repeated a number of times

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. One recorded
> difference: an empty fill string gives the wrong error code (below).
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`STRING$(n,c)` returns `n` copies of one character. The character is given
either as a code (`STRING$(3,65)` is `"AAA"`) or as a string, whose first
character is used (`STRING$(3,"*")` is `"***"`). [`SPACE$`](SPACE$.md) is the
special case for spaces. zerobas behaves like the Philips VG-8020 in every case
we have measured except one error code.

## Syntax

```
STRING$(<count>,<character code>)
STRING$(<count>,<string expression>)
```

Which form you wrote is decided by the type of the second argument.

## Details

- **Only the first character of a string is used**: `STRING$(3,"xyz")` is
  `"xxx"`.
- **The count must be 0 to 255**, and so must a character code. Outside
  −32768 to 32767 either one is `Overflow` (error 6); otherwise out of range
  it is `Illegal function call` (error 5). There is no silent clamp.
- **A long result needs string space.** In the string space a program starts
  with, `STRING$(255,"A")` is `Out of string space` (error 14) on both
  machines; after `CLEAR 600` it is 255 characters.
- **A string as the count** (`STRING$("A","A")`) is `Type mismatch`
  (error 13).
- **A missing or extra argument** (`STRING$(2)`, `STRING$()`,
  `STRING$(2,"A","A")`) is `Syntax error` (error 2).
- **Spaces are allowed** before the parenthesis and before the comma:
  `STRING$ (2,65)` is `"AA"`.

| you write | you get |
|---|---|
| `STRING$(3,65)` | `"AAA"` |
| `STRING$(3,"*")` | `"***"` |
| `STRING$(-1,"A")`, `STRING$(256,"A")` | error 5, `Illegal function call` |
| `STRING$(2,-1)`, `STRING$(2,256)` | error 5, `Illegal function call` |
| `STRING$(99999,65)`, `STRING$(5,99999)` | error 6, `Overflow` |
| `STRING$("A","A")` | error 13, `Type mismatch` |
| `STRING$(2)`, `STRING$()`, `STRING$(2,"A","A")` | error 2, `Syntax error` |
| `STRING$(2,"")` | error 5 on the reference, **error 2 here** (see *Differences*) |

The set of errors the T6 enumeration measured for `STRING$` is {2, 5, 13},
and each has a matching case; the `Overflow` above comes from the separate
range measurements and agrees too.

## Example

```
10 PRINT STRING$(5,"*")
20 PRINT STRING$(3,65);STRING$(3,"xyz")
30 PRINT LEN(STRING$(0,"A"))
40 ON ERROR GOTO 70
50 PRINT STRING$(256,"A")
60 END
70 PRINT "Error";ERR:RESUME NEXT
RUN
*****
AAAxxx
 0
Error 5
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_string_s.out`](../../scratchpad/kwdoc_string_s.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

**An empty fill string is error 2 here and error 5 on the VG-8020.**
`PRINT STRING$(2,"")` reads `Illegal function call` on the reference — an
empty string has no first character, which the reference treats as a bad
value, like `ASC("")` — and `Syntax error` on zerobas
([`t6enum_b2.out`](../../scratchpad/t6enum_b2.out)). Every other `STRING$`
error case agreed. It is filed as TIER 6 (D-STRINGEMPTY in
[TODO.md](../../TODO.md)). The rung *every error* is still ticked, because
error 5 is matched by other cases (`STRING$(-1,"A")`); this case reports the
wrong one.

The other rung not yet proven is **RAM usage**: `STRING$` changes free memory
by the same amount on both machines, but the set of work-area cells written
differs ([`kwram_full.out`](../../scratchpad/kwram_full.out)).

## What we found, and how

- **`STRING$` arrived on 2026-07-10.** Its first run against the VG-8020
  caught `PRINT STRING$(…)` answering `Type mismatch`, because the `PRINT`
  item reader had no case for it; a review the same day caught a negative
  count being clamped instead of refused:
  [spec-basic-string-functions.md](../spec-basic-string-functions.md).
- **A malformed `STRING$` call could hang the machine** (fixed 2026-07-17),
  filling the screen with ` 0`; it is now a `Syntax error`.
- **Out-of-range counts and codes went through without the reference's
  error** (fixed 2026-07-19, D-F2-2). Both numbers are now checked as bytes,
  0 to 255: [spec-basic-df2-2-intarg-coercion.md](../spec-basic-df2-2-intarg-coercion.md).
- **The documents still described a clamp** on 2026-08-29; measuring it again
  (D-SPCLAMP) showed zerobas already agreed with both references at every
  point. The run also showed that at the starting string space the
  255-character case fails on space, not on the limit, on all three machines —
  so the limit itself is tested after `CLEAR 600`:
  [spec-basic-spclamp.md](../spec-basic-spclamp.md).
- **`STRING$ (2,65)` and `STRING$(2 ,65)` were syntax errors** (fixed
  2026-09-09, D-FNSPACE)
  ([`fnspace_after2.out`](../../scratchpad/fnspace_after2.out)).

## Where it lives

`str_fn_string` in [basic/str-engine.asm](../../basic/str-engine.asm) reads
the count, then tries the second argument as a string and, failing that, as a
number. Both numbers are checked by the shared `get_byte_arg` in
[basic/interp.asm](../../basic/interp.asm). The characters are written by
`sh_fill` in [sub/strheap.asm](../../sub/strheap.asm), in the sub-ROM.

## Related concepts

- [Strings and string space](../concepts/strings-and-string-space.md) — where string values live

## Tests that cover it

- `make str-domain-acceptance` — the count's and the code's ranges, both error
  kinds, and the int16 boundary.
- `make string-acceptance` — the code and string forms and a 100-character
  result, against the reference.
- `make kwsweep` — the everyday row (`STRING$(3,"x")`) and the error rows for
  {2, 5, 13}.
- `make kwram` — the RAM-usage comparison.
