<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `INSTR` — find one string inside another

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. No known divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`INSTR(a$,b$)` returns the position, counting from 1, where `b$` first occurs
inside `a$`, or 0 if it does not occur. `INSTR(p,a$,b$)` starts looking at
position `p`. zerobas behaves exactly like the Philips VG-8020 for every case
we have measured, errors included.

## Syntax

```
INSTR([<start>,]<string to search>,<string to find>)
```

Two forms: with and without the start position. Which one you wrote is
decided by the type of the first argument — a number is the start, a string
is the text to search.

## Details

- **Positions count from 1.** `INSTR("HELLO","LL")` is 3.
- **Not found is 0**, not an error.
- **The start position skips earlier matches**: `INSTR(2,"ABA","A")` is 3,
  not 1.
- **A start past the end** finds nothing: `INSTR(10,"HELLO","L")` is 0.
- **An empty string to find** is found at once: `INSTR("HELLO","")` is 1.
- **The start must be 1 to 255.** 0, negative numbers and 256 or more are
  `Illegal function call` (error 5); outside −32768 to 32767 it is `Overflow`
  (error 6).
- **A number where a string belongs** is `Type mismatch` (error 13), in
  either string position. If that number itself fails to compute, its own
  error is reported instead.
- **A missing or extra argument** is `Syntax error` (error 2).
- **A space before the parenthesis is allowed**: `INSTR ("ABCDE","C")` is 3.

| you write | you get |
|---|---|
| `INSTR("HELLO","LL")` | 3 |
| `INSTR("HELLO","Z")` | 0 |
| `INSTR(3,"ABCABC","B")` | 5 |
| `INSTR(0,"AB","B")`, `INSTR(256,"AB","B")` | error 5, `Illegal function call` |
| `INSTR(70000,"AB","B")` | error 6, `Overflow` |
| `INSTR("AB",5)`, `INSTR(1,5,"B")` | error 13, `Type mismatch` |
| `INSTR("AB")`, `INSTR()`, `INSTR(1,"AB")` | error 2, `Syntax error` |
| `INSTR("AB","B","C")`, `INSTR(1,"AB","B","C")` | error 2, `Syntax error` |

Without a start, `INSTR` can raise {2, 13}; with one, {2, 5, 6, 13}. Both sets
are the same on both machines.

## Example

```
10 A$="HELLO WORLD"
20 PRINT INSTR(A$,"O");INSTR(6,A$,"O")
30 PRINT INSTR(A$,"Z");INSTR(A$,"")
40 PRINT INSTR(20,A$,"O")
50 ON ERROR GOTO 80
60 PRINT INSTR(0,A$,"O")
70 END
80 PRINT "Error";ERR:RESUME NEXT
RUN
 5  8
 0  1
 0
Error 5
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_instr.out`](../../scratchpad/kwdoc_instr.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

None known.

The one rung not yet proven is **RAM usage**: `INSTR` changes free memory by
the same amount on both machines, but the set of work-area cells written
differs ([`kwram_full.out`](../../scratchpad/kwram_full.out)). Nothing a
program can observe through `FRE` differs. No keyword has this rung yet.

## What we found, and how

- **`INSTR` arrived on 2026-07-10**, with its edge cases (not found, empty
  string to find, a start in the middle and past the end) captured on the
  VG-8020: [spec-basic-string-functions.md](../spec-basic-string-functions.md).
- **A start of 0 or less printed a silent `0`** where the reference raises
  error 5 (fixed 2026-07-17, in the follow-up to the string-heap work).
- **A start of 256 or more was still silently "not found"**, and one past
  32767 gave the wrong error (fixed 2026-07-28, D-MISS-2). `INSTR` had only
  half of the rule, hand-written, and was on nobody's list: it was found when
  a review question was answered by running the probe instead of by argument.
  The fix made the code smaller, because the hand-written half was replaced
  by the check `MID$` uses: [spec-basic-str-domain.md](../spec-basic-str-domain.md).
- **A number where a string belongs said `Syntax error`** where both
  references say `Type mismatch` (fixed 2026-08-29, D-INSTRTM). Two rows had
  been filed; measuring the whole surface first found five. The fix is in the
  order — evaluate the operand, then complain — so an operand that fails on
  its own still reports its own error:
  [spec-basic-instrtm.md](../spec-basic-instrtm.md).

## Where it lives

`ev_f_instr` in [basic/str-engine.asm](../../basic/str-engine.asm) reads the
arguments; the start position is checked by the shared `eval_pos_arg` in
[basic/interp.asm](../../basic/interp.asm), the same check `MID$` uses. The
search itself is `sh_instr_search` in [sub/strheap.asm](../../sub/strheap.asm),
in the sub-ROM.

## Tests that cover it

- `make string-acceptance` — found, not found, empty, start in the middle and
  past the end, against the reference.
- `make str-domain-acceptance` — the start position's range, both error kinds.
- `make kwsweep` — both forms (`INSTR(2,"ABA","A")` must read 3), and the error
  rows for both sets.
- `make kwram` — the RAM-usage comparison.
