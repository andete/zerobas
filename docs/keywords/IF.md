<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `IF` — run part of a line only when a condition holds

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. One recorded
> difference: `IF 1 GOTO` with no line number (below).
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`IF A>3 THEN PRINT "big" ELSE PRINT "small"` evaluates the condition and runs
the `THEN` part when it is true (not zero), the `ELSE` part when it is false.
Either part can be statements or just a line number to jump to. `THEN` and
`ELSE` are covered here: they only ever appear inside an `IF`, and have no
pages of their own. zerobas behaves like the Philips VG-8020 in every case we
have measured but one.

## Syntax

```
IF <condition> THEN <statements> | <line number> [ELSE <statements> | <line number>]
IF <condition> GOTO <line number> [ELSE <statements> | <line number>]
```

## Details

- **True means not zero**, fractions included: `IF .5 THEN` and
  `IF -.5 THEN` take the `THEN` part.
- **A string is not a condition**: `IF A$ THEN`, `IF "X" THEN` are
  `Type mismatch` (error 13).
- **`THEN 100` and `ELSE 100` are jumps**: a bare line number after either
  means `GOTO` that line.
- **The parts run to the end of the line.** When the condition is false and
  there is no `ELSE`, everything after `THEN` on that line is skipped,
  including statements after a `:`. When the `THEN` part runs, the `ELSE`
  part is skipped.
- **An `ELSE` belongs to the nearest `IF` that does not have one yet.** In
  `IF 0 THEN IF 1 THEN B=1 ELSE B=2`, the `ELSE` is the inner `IF`'s, so a
  false outer condition runs neither; add a second `ELSE` and that one is the
  outer `IF`'s. Each nested `IF` claims one `ELSE`.
- **An empty part is allowed**: `IF 1 THEN` and `IF 0 THEN 30 ELSE` do
  nothing, on both machines.

### Errors

| you write | you get |
|---|---|
| `IF THEN 30` (no condition), `IF 1 GOTO "A"` | 2 `Syntax error` |
| `IF 1 THEN 99`, `IF 0 THEN 30 ELSE 99`, `IF 1 GOTO 99`, no line 99 | 8 `Undefined line number` |
| `IF "A" THEN 30`, `IF "A" GOTO 30` | 13 `Type mismatch` |
| `IF 1 GOTO` (no line number) | accepted on the VG-8020, 2 here — see *Differences* |

The whole set of errors `IF` raises is {2, 8, 13} for `THEN` and `GOTO` and
{8, 13} for `ELSE`, the same on both machines.

## Example

```
10 A=5:IF A>3 THEN PRINT "Big"
20 IF A>9 THEN PRINT "Huge" ELSE 40
30 PRINT "skipped"
40 IF .5 THEN PRINT "Half is true"
50 B=9
60 IF 0 THEN IF 1 THEN B=1 ELSE B=2
70 IF 2>1 GOTO 90
80 B=0
90 PRINT "B=";B
100 ON ERROR GOTO 130
110 IF "A" THEN 120
120 END
130 PRINT "Error";ERR:RESUME NEXT
RUN
Big
Half is true
B= 9
Error 13
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_if.out`](../../scratchpad/kwdoc_if.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

**`IF 1 GOTO` with no line number** is accepted by the VG-8020, which carries
on without jumping, and is `Syntax error` here (D-IFGOTOBARE, found
2026-09-27 by the every-error enumeration;
[t6enum_b6.out](../../scratchpad/t6enum_b6.out)). `IF 1 GOTO 99` and
`IF 1 GOTO "A"` agree. It is filed as a TIER 6 item in
[TODO.md](../../TODO.md).

The one rung not yet proven is **RAM usage**.

## What we found, and how

- **A false `IF` ran a nested `IF`'s `ELSE`** (fixed 2026-09-02, D-IFSEM).
  zerobas looked for the first `ELSE` on the line, so
  `B=9:IF 0 THEN IF 1 THEN B=1 ELSE B=2` left `B` at 2 where both references
  leave 9. Two rules fit that row — "a false `IF` ends the line" and "each
  nested `IF` claims one `ELSE`" — and only a row with a second `ELSE`
  (both references: 3) separates them; the first rule would have been the
  wrong fix. `IF` had been reviewed because, although nearly every test uses
  it, almost nothing measured it ([spec-basic-ifsem.md](../spec-basic-ifsem.md)).
- **`IF 0 THEN 20 ELSE 30` was `Syntax error`** (fixed 2026-08-01, D-LNREF):
  the line number after `ELSE` was not stored as a line-number reference, so
  the jump code that was already written never ran.
- **A fractional condition was judged on its whole-number part**, so
  `IF .5 THEN` took the false branch; found and fixed in a review on
  2026-07-11. The reference treats any non-zero number as true.
- **The `ELSE` and `GOTO` forms had no rows in the keyword sweep** until
  D-KWIF2: the only row took the `THEN` branch, so an `ELSE` that was read and
  then ignored would have passed.

## Where it lives

`ex_if` and `if_skip_to_else` (the nesting-aware search for the matching
`ELSE`) in [basic/interp.asm](../../basic/interp.asm). A line number after
`THEN` or `ELSE` goes to `GOTO`'s own `ex_goto_at`.

## Tests that cover it

- `make ifsem-acceptance` — nested `IF`s and their `ELSE`s, fractional
  conditions, string conditions.
- `make kwsweep` — the `THEN`, `ELSE` and `GOTO` rows, and the error rows for
  {2, 8, 13}.
- `make kwram` — the RAM-usage comparison.
