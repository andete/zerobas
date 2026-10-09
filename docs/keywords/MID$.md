<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `MID$` — characters from the middle of a string, or overwrite them

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error not yet proven. One
> recorded difference: an extra argument gives the wrong error code (below).
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`MID$` is two things with one name. As a **function**, `MID$(a$,p,n)` returns
`n` characters of `a$` starting at position `p` (counting from 1), and
`MID$(a$,p)` returns everything from `p` to the end. As a **statement**,
`MID$(A$,p,n)=b$` overwrites characters of the variable `A$` in place, without
changing its length. zerobas behaves like the Philips VG-8020 in every case we
have measured except one error code.

## Syntax

```
MID$(<string expression>,<position>[,<count>])          function
MID$(<string variable>,<position>[,<count>])=<string>    statement
```

## Details

### The function

- **Positions count from 1.** `MID$("ABCDEF",2,3)` is `"BCD"`.
- **Without a count, it runs to the end**: `MID$("hello",3)` is `"llo"`.
- **Asking for more than is there is fine**: the result just stops at the end.
  A position past the end gives `""`.
- **The position must be 1 to 255** — the one argument in the string family
  that starts at 1, so `MID$(a$,0)` is an error while `MID$(a$,255)` is not.
- **The count must be 0 to 255.**
- Each number is truncated toward zero and then checked in two steps: outside
  −32768 to 32767 → `Overflow` (error 6); otherwise out of range →
  `Illegal function call` (error 5).
- **Arguments are checked left to right**, each completely before the next:
  `MID$(a$,99999,-1)` is error 6 (the position fails first), and
  `MID$(a$,0,99999)` is error 5.
- **Spaces are allowed** before the parenthesis and around the commas.

### The statement

- **The length of `A$` never changes.** The number of characters replaced is
  the smallest of: the count (if given), the length of `b$`, and the room left
  in `A$` from position `p`. Characters outside that span are untouched.
  `A$="HELLO":MID$(A$,4)="WXYZ"` makes `"HELWX"`.
- **`p` must be 1 to 255 and no more than `LEN(A$)`**; a position past the end
  of `A$` is error 5. The count must be 0 to 255.
- **The target can be an array element**: `MID$(A$(1),1,2)="XY"` works.
- **A string that came from `READ` is copied before it is changed**, so the
  `DATA` line in the program is left as it was.
- **A space before the `=`** is allowed.

### Errors

| situation | error |
|---|---|
| position 0, negative, or 256 and up; count negative or 256 and up | 5 `Illegal function call` |
| statement: position past the end of `A$` (`A$="AB":MID$(A$,3)="X"`) | 5 `Illegal function call` |
| a number outside −32768 to 32767 (`MID$("AB",70000,1)`) | 6 `Overflow` |
| a number where a string belongs, or a string where a number belongs | 13 `Type mismatch` |
| statement: the target is a numeric variable (`MID$(A,1,1)="X"`) | 13 `Type mismatch` |
| statement: a number on the right (`MID$(A$,1)=5`) | 13 `Type mismatch` |
| statement: nothing after `=` (`MID$(A$,2)=`) | 24 `Missing operand` |
| a missing argument (`MID$("AB")`, `MID$()`, `MID$(A$)="X"`), or no `=` | 2 `Syntax error` |
| an extra argument, or a non-variable target (see *Differences*) | 2 on the reference, 13 here |

## Example

```
10 A$="ABCDEF"
20 PRINT MID$(A$,2,3);" ";MID$(A$,4)
30 PRINT LEN(MID$(A$,9))
40 MID$(A$,2,3)="XYZ":PRINT A$
50 MID$(A$,5)="12345":PRINT A$
60 ON ERROR GOTO 90
70 PRINT MID$(A$,0)
75 MID$(A$,7)="X"
80 END
90 PRINT "Error";ERR:RESUME NEXT
RUN
BCD DEF
 0
AXYZEF
AXYZ12
Error 5
Error 5
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_mid_s.out`](../../scratchpad/kwdoc_mid_s.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

**An extra argument, or a target that is not a variable, is error 13 here
and error 2 on the VG-8020.** `PRINT MID$("AB",1,1,1)` and `MID$(5,1)="X"`
both read `Syntax error` on the reference and `Type mismatch` on zerobas
([`t6enum_b4.out`](../../scratchpad/t6enum_b4.out)). zerobas evaluates past
the point where the reference already demands `)` or a variable, and then
checks the type. It is filed as TIER 6 (D-MIDEXTRA in
[TODO.md](../../TODO.md)), likely one fix with the same shape in `MKI$`, and
it is why *every error* is not yet proven for `MID$`: the three-argument
function has no case where the reference's error 2 is matched.

The other rung not yet proven is **RAM usage**: `MID$` changes free memory by
the same amount on both machines, but the set of work-area cells written
differs ([`kwram_full.out`](../../scratchpad/kwram_full.out)).

## What we found, and how

- **The statement arrived on 2026-07-10**, as a handler of its own; the
  function is a different piece of code, so tests of one do not reach the
  other: [spec-basic-mid-statement.md](../spec-basic-mid-statement.md).
- **Out-of-range numbers were accepted silently**, in both forms (fixed
  2026-07-28, D-MISS-2). The statement was broken both ways:
  `MID$(A$,1,256)="X"` performed the assignment and `MID$(A$,1,99999)="X"`
  silently did nothing, where the reference raises; seven other cases gave
  `Syntax error` instead of 5 or 6. The function's position was also found to
  be the family's only 1-based argument:
  [spec-basic-str-domain.md](../spec-basic-str-domain.md).
- **An array element could not be the target** (fixed 2026-08-08, D-LVFIX):
  `MID$(A$(1),1,2)="XY"` was a syntax error on zerobas and works on both
  references: [lvsites-msx1-characterization.md](../lvsites-msx1-characterization.md).
- **The statement's right-hand side gave the wrong error** (fixed
  2026-08-26, D-MIDOP): nothing after `=` is 24 on the reference, a number is
  13, and zerobas said 2 for both:
  [spec-basic-midop.md](../spec-basic-midop.md).
- **Spaces** (fixed 2026-09-08, D-MIDSPACE, and 2026-09-09, D-FNSPACE):
  `MID$(A$,2) ="X"` raised error 2 and left `A$` unchanged, and
  `MID$ ("ABCDE",2,2)` was a syntax error
  ([`midspace_after.out`](../../scratchpad/midspace_after.out),
  [`fnspace_after2.out`](../../scratchpad/fnspace_after2.out)).
- **A slice of a big string ran out of string space** where the reference had
  room (fixed 2026-09-26, D-SLICEOOM): zerobas copied the whole source first
  ([`sliceoom_run.out`](../../scratchpad/sliceoom_run.out)).
- **`READ` strings began pointing at the program text** (2026-10-07,
  D-READREF), as on the references. `MID$` now copies such a string out before
  writing into it; on the VG-8020 a re-`READ` and `LIST` show the original.

## Where it lives

- The function: `str_fn_mid` in
  [basic/str-engine.asm](../../basic/str-engine.asm), sharing its opening
  (`str_arg_open`) with `LEFT$` and `RIGHT$`. The position is checked by
  `eval_pos_arg` and the count by `eval_byte_arg`, both in
  [basic/interp.asm](../../basic/interp.asm).
- The statement: `ex_mid_stmt` in the same file reads the target and the
  numbers; `mid_own` copies a `READ` string out first; the bytes are written
  by `sh_mid_store` in [sub/strheap.asm](../../sub/strheap.asm), in the
  sub-ROM.

## Related concepts

- [Strings and string space](../concepts/strings-and-string-space.md) — where string values live

## Tests that cover it

- `make str-domain-acceptance` — both forms' ranges, both error kinds, and the
  left-to-right order.
- `make string-acceptance` — the statement's overwrite rules (count longer
  than `b$`, `b$` longer than the room, empty `b$`, count 0) against the
  reference.
- `make readref-acceptance` — `MID$` into a `READ` string leaves the program
  alone.
- `make kwsweep` — all three forms (`MID$("hi",2,1)`, `MID$("hello",3)`, the
  statement) and the error rows.
- `make kwram` — the RAM-usage comparison.
