<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `POS` — the column the cursor is in

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. One recorded
> difference: a string as the dummy argument (below).
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`POS(0)` is the text cursor's column, counted from 0 at the left edge of the
text area. The argument is a dummy: it must be there, and its value is
ignored. [`CSRLIN`](CSRLIN.md) gives the row; [`LPOS`](LPOS.md) is the same
thing for the printer. zerobas behaves like the Philips VG-8020 in every case
we have measured except one: a string as the dummy argument.

## Syntax

```
POS(<dummy>)
```

The parentheses and one argument are required.

## Details

- **0-based.** At the start of a line `POS(0)` is 0; after `PRINT "ABC";` it
  is 3.
- **The argument is ignored.** `POS(1)`, `POS(99)`, `POS(-1)` and `POS(1+1)`
  all give the same answer as `POS(0)`. There is no range check, so a
  negative or large value is not an error.
- **Inside a `PRINT` it is read when it is reached.** In
  `PRINT "AB";"[";POS(0)` it is 3, because `AB[` has already been printed by
  then.
- **It follows `LOCATE`.** After `LOCATE 9,3` it is 9.
- **Errors**, the same on both machines:

| you write | you get |
|---|---|
| `POS` without parentheses | error 2, `Syntax error` |
| `POS()`, `POS(1,2)` | error 2, `Syntax error` |
| `POS("A")` | **VG-8020: accepted.** zerobas: error 13 — see *Differences* |

## Example

```
10 PRINT "ABC";:P=POS(0):PRINT
20 PRINT "Column after ABC:";P
30 PRINT TAB(10);:PRINT POS(0)
40 PRINT POS(-1);POS(99)
50 ON ERROR GOTO 80
60 PRINT POS()
70 END
80 PRINT "Error";ERR:RESUME NEXT
RUN
ABC
Column after ABC: 3
           10
 0  3
Error 2
```

In line 30 the number is printed from column 10, so it shows as ` 10` after
ten blanks. In line 40 the dummy arguments make no difference: the first
`POS` is read at column 0, the second after the first number (` 0 `) has been
printed, at column 3.
Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_pos.out`](../../scratchpad/kwdoc_pos.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

**`POS("A")` is `Type mismatch` here and accepted on the VG-8020**, which
prints the column as usual (D-POSDUMMY, found 2026-09-27, filed in
[TODO.md](../../TODO.md) as a TIER 6 item). On the reference the argument
really is a dummy, and its type is not checked either. `LPOS("A")` has the
same difference. The reference raises nothing there, so it does not hold
back the "every error" rung, whose set is {2}.

The other rung not yet proven is **RAM usage**: `POS` moves free memory the
same way on both machines, but the set of documented work-area cells each one
writes is not the same.

## What we found, and how

- **`POS` used to be silently wrong** (fixed 2026-07-27, the cursor slice
  [spec-basic-cursor-cluster.md](../spec-basic-cursor-cluster.md)). Without its
  own keyword, `POS(0)` was read as element 0 of an array called `POS`, which
  is 0, with no error. The rules above were measured on the VG-8020 first
  ([cursor-vg8020-characterization.md](../cursor-vg8020-characterization.md)),
  including the four argument values that showed the argument is ignored
  rather than a selector.
- **The test does not use `POS` to check its neighbours.** The cursor
  measurements find where a marker landed on the screen grid instead of asking
  `POS`, so a wrong `TAB(` and a wrong `POS` cannot cancel out and look right.
- **A string dummy argument is checked here and not there** (found
  2026-09-27, D-POSDUMMY, still open).

## Where it lives

`ev_ff_pos` in [basic/expr.asm](../../basic/expr.asm). It reads the BIOS
cursor column and subtracts 1, because the BIOS counts from 1. `POS` is in the
one-argument function table in [basic/islands.asm](../../basic/islands.asm)
and deliberately left out of the range-check chain.

## Tests that cover it

- `make cursor-acceptance` — the column at line start, after text, with the
  four dummy values, and without parentheses.
- `make kwsweep` — the everyday row (text first, so the answer is a known
  column other than 0) and the error rows for {2}.
- `make kwram` — the RAM-usage comparison.
