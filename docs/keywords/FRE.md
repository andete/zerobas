<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `FRE` — how much memory is free

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. No known divergence in
> how `FRE` counts; the amount of memory there is to count differs (below).
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`FRE` reports free memory, and there are two kinds. `FRE(0)` — any number in
the parentheses — is the space left for program lines, variables and arrays.
`FRE("")` — any string — is the space left in the string pool, whose size
`CLEAR` sets. zerobas keeps the two pools apart as the Philips VG-8020 does and
charges each the same amounts for the same work.

## Syntax

```
FRE(<numeric expression>)
FRE(<string expression>)
```

Only the *type* of the argument matters.

## Details

- **The numeric argument is ignored:** `FRE(0)`, `FRE(1)`, `FRE(-1)` and
  `FRE(255)` all give the same answer when asked at the same point.
- **The string argument's content is ignored too:** `FRE("")`, `FRE("ABCDE")`
  and `FRE(A$)` agree. `FRE("")` also tidies the string pool first, so space
  from strings no longer in use is counted as free.
- **The string pool is exactly what `CLEAR` asked for:** after `CLEAR 300`,
  `FRE("")` is 300; at start-up it is 200.
- **A string costs its characters to the string pool and only its variable
  entry to the other one.** `A$=STRING$(100,"A")` takes 100 from `FRE("")`.
- **What things cost, as `FRE(0)` sees it** (the same on both machines):
  a numeric variable 11 bytes; `DIM A(n)` 8 bytes per element plus 8.
- **Read both values at the same point.** `FRE(0)` counts down to the stack,
  so `FRE(0)-FRE(0)` is not 0 on the VG-8020: each extra level of expression
  nesting costs it a few bytes. To measure what something costs, create the
  variables you will store the readings in first, and read both readings
  with the same statement shape, as the example does.
- **Errors:** `FRE`, `FRE()`, `FRE(0,1)` and `FRE("","")` are `Syntax error`
  (error 2) — the only error either form raises, on both machines.

## Example

```
10 CLEAR 300
20 PRINT FRE("")
30 A$=STRING$(50,"X")
40 PRINT FRE("")
50 A=0:B=0:A=FRE(0):DIM Z(9):B=FRE(0)
60 PRINT A-B
70 ON ERROR GOTO 100
80 PRINT FRE()
90 END
100 PRINT "Error";ERR:RESUME NEXT
RUN
 300
 250
 88
Error 2
```

`DIM Z(9)` is ten 8-byte elements plus an 8-byte header: 88.

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_fre.out`](../../scratchpad/kwdoc_fre.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

None known in how `FRE` counts.

**The absolute `FRE(0)` figure is not the VG-8020's.** zerobas has its own
working storage in RAM (`$E000`–`$F37F`) and its own memory ceiling for BASIC,
so a freshly started zerobas reports a different amount of free memory. That
is the RAM-usage (TIER 4) question, and it is why no example on these pages
prints an absolute `FRE(0)`. How much `FRE(0)` shrinks per level of expression
nesting is a property of each machine's evaluator and is recorded, not
compared.

## What we found, and how

- **`FRE` did not exist** (added 2026-07-27). `FRE(0)` was read as an element
  of an array named `FRE` and answered 0; `FRE("")` was `Type mismatch`. The
  measurement that preceded it found the two pools, the dummy argument, and
  that a naive `FRE(0)=FRE(1)` test answers "false" for a reason that has
  nothing to do with the argument
  ([binfre-vg8020-characterization.md](../binfre-vg8020-characterization.md)).
- **There was only one pool** (fixed 2026-07-29, D-CLP). `CLEAR`'s
  string-space argument was accepted and thrown away; `FRE("")` reported all
  free memory and a string's characters were charged to `FRE(0)` as well.
  Since then `CLEAR n` sets the string pool to exactly n
  ([spec-basic-clearpool.md](../spec-basic-clearpool.md)).
- **8 KB of memory was reserved for nothing** (found and fixed 2026-09-01,
  D-FREGAP / D-RECLAIM). Asked what a start-up `Bytes free` line would say,
  the accounting showed an 8192-byte area kept free by convention, holding two
  bytes. Joost ruled *"BASIC and DOS never co-exist"*, which made that area
  free for BASIC; `FRE(0)` rose by 8192 at no ROM cost
  ([spec-fre-gap.md](../spec-fre-gap.md), [spec-reclaim.md](../spec-reclaim.md)).

## Where it lives

`ev_ff_fre` in [basic/expr.asm](../../basic/expr.asm) picks the form from the
argument's type (`ev_fre_num` for a number); the string-heap code in
[sub/strheap.asm](../../sub/strheap.asm) answers the two pools' sizes.

## Related concepts

- [The memory map](../concepts/memory-map.md) — where BASIC keeps things in RAM
- [Strings and string space](../concepts/strings-and-string-space.md) — where string values live
- [Variables](../concepts/variables.md) — names, types, arrays, and where they live

## Tests that cover it

- `make binfre-acceptance` — the two forms, the dummy argument, the allocation
  costs read at equal depth, and the errors.
- `make clearpool-acceptance` — `CLEAR`'s string pool and `FRE("")`.
- `make kwsweep` — the everyday row, a `DIM` cost row, a string cost row and
  the error rows for both forms.
- `make kwram` — the RAM-usage comparison.
