<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `DIM` — declare an array

> **Status (2026-10-10):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. One recorded
> difference: how close to the end of free memory an array may reach (below),
> now about 30 bytes where it was about 170.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`DIM A(10)` creates an array `A` with elements `A(0)` to `A(10)`;
`DIM B$(3,4)` creates a two-dimensional string array. The new elements are 0
(or empty strings). zerobas behaves like the Philips VG-8020 in every case we
have measured, errors included, except at the very edge of free memory.

## Syntax

```
DIM <name>(<bound>[,<bound>]...)[,<name>(<bound>[,<bound>]...)]...
```

Each bound is a numeric expression. The name may carry a type suffix (`%`,
`!`, `#`, `$`); without one it has the default type, which is double precision
unless a `DEFINT`/`DEFSNG`/`DEFSTR` says otherwise.

## Details

- **Subscripts start at 0**: `DIM A(3)` has four elements.
- **There is no limit on the number of dimensions** that a program line can
  reach; the reference was measured storing and reading an element through 32
  subscripts.
- **An array used without `DIM` is created with bound 10 in every dimension**
  on first use, so `A(11)` on an undeclared `A` is `Subscript out of range`.
- **The size check is on bytes, before anything is allocated.** If the
  elements need more than 65535 bytes (2 per integer, 4 per single, 8 per
  double, 3 per string), the answer is `Subscript out of range`; if they fit
  that limit but not in free memory, it is `Out of memory`. So `DIM Q%(200,200)`
  is `Subscript out of range` although neither bound is large.
- **Several arrays in one `DIM` are created one by one.** In
  `DIM P(3),Q(-1)`, `P` is created and then `Q` fails; `P` stays.
- **`DIM` an existing array again is `Redimensioned array`** — whatever the new
  bounds. Use [`ERASE`](ERASE.md) first.
- **A name with no bounds is accepted and does nothing**: `DIM A` and
  `DIM A,B(2)` run without error, and `A` is not created.

| you write | you get |
|---|---|
| `DIM A(-1)` | 5 `Illegal function call` |
| `DIM A(70000)` | 6 `Overflow` |
| `DIM A(10000)` (80008 bytes of doubles) | 9 `Subscript out of range` |
| `A(9)=1` after `DIM A(3)` | 9 `Subscript out of range` |
| `DIM A(2):DIM A(2)` | 10 `Redimensioned array` |
| `DIM A("X")` | 13 `Type mismatch` |
| `DIM 5`, bare `DIM`, `DIM A,` | 2 `Syntax error` |
| more elements than free memory | 7 `Out of memory` |

The measured set of errors for `DIM` is {2, 5, 6, 9, 10, 13} for one dimension
and {5, 9, 10, 13} for several, the same on both machines.

## Example

```
10 DIM A(3),B$(2,1)
20 FOR I=0 TO 3:A(I)=I*I:NEXT
30 B$(2,1)="HI"
40 PRINT A(3);B$(2,1)
50 ON ERROR GOTO 80
60 A(4)=1
70 DIM A(5):END
80 PRINT "Error";ERR:RESUME NEXT
RUN
 9 HI
Error 9
Error 10
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_dim.out`](../../scratchpad/kwdoc_dim.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

**An array that leaves very little memory free fits on the VG-8020 and is
`Out of memory` here** (D-DIMRESERVE, open, a TIER 4 item). Size it with
`X=INT((FRE(0)-K)/8):DIM A(X)`: the VG-8020 accepts the `DIM` down to `K` = 110,
and zerobas down to `K` = 140 ([gate](../../probes/basic/basic_probe_dimedge.py)).
Until 2026-10-10 zerobas refused below `K` = 280, because it kept a fixed
256-byte reserve for its own stack ([readings](../../scratchpad/dimedge_run.out)).
Joost ruled on 2026-10-09: *"yes, we need to match reference there"*. Three
steps on 2026-10-10 did most of it. The expression evaluator was reworked, so a
simple statement needs 101 bytes of stack instead of 147 (the VG-8020: 79,
[after](../../scratchpad/stackhwref_after_s2.out)). Then the reserve was cut to
116 bytes, the deepest stack zerobas reaches without its expression check (92
bytes, in the line editor), plus room to spare
([statements](../../scratchpad/lowpoint_disk2.out),
[editor](../../scratchpad/lowpoint_dm.out)). The last 30 bytes are that
deeper stack.

Both machines behave alike just past the edge: the `DIM` fits, and the next
statement may itself be `Out of memory`, because a formula needs a little stack
too. The VG-8020 runs a simple `PRINT` again from about `K` = 126, zerobas from
about 192: zerobas's formula check keeps more in hand
([VG-8020](../../scratchpad/dimedge_ref_fine.out),
[zerobas](../../scratchpad/edgesafe_run.out)). That check was also tested at
this edge: no statement wrote into the array.

More generally, zerobas has less free memory than the VG-8020, so an array that
only just fits there can be `Out of memory` here. That is part of the **RAM
usage** rung, which is not yet proven.

## What we found, and how

- **Arrays arrived between 2026-07-15 and 2026-07-17**: numeric arrays with
  the auto-dimension to 10 first, then string arrays.
- **A huge `DIM` gave the wrong error** (fixed 2026-07-29, D-ARR-B):
  `DIM Q(20000)` was `Out of memory` here and `Subscript out of range` on the
  reference. Measuring the edge for each type showed the limit is 65535 bytes
  of elements, so it moves with the element size, and that it also applies to
  an array created without `DIM`
  ([arrdim-vg8020-characterization.md](../arrdim-vg8020-characterization.md)).
- **Arrays were limited to four dimensions** (fixed 2026-07-29, D-ARR-C). That
  limit had been written down as matching the reference and never measured;
  the reference has none ([arrdim-c-vg8020-characterization.md](../arrdim-c-vg8020-characterization.md)).
- **`DIM A` was a `Syntax error`** (fixed 2026-08-28, D-DIMBARE). The comment
  next to the code said a bound list was required; both references accept the
  bare name and ignore it ([spec-basic-dimbare.md](../spec-basic-dimbare.md)).
- **A deep formula could overwrite an array that filled memory** (fixed
  2026-09-27, D-STACKFLOOR). Looking into the reserve above showed nothing
  stopped a nested expression's stack from growing down into the arrays;
  the reference raises `Out of memory` instead. The evaluator now checks its
  stack as it goes.
- **The reserve at the end of memory was cut from 256 bytes to 116**
  (2026-10-10, D-DIMRESERVE). Two probes on zerobas's own stack measured how deep
  each kind of statement goes and how close it gets to the arrays
  ([`lowpoint_probe.py`](../../scratchpad/lowpoint_probe.py),
  [`edgesafe_probe.py`](../../scratchpad/edgesafe_probe.py)). With the reserve cut
  to 16 bytes, the second probe saw the stack write into the array, so it can
  tell ([knife](../../scratchpad/edgesafe_knife.out)).

## Where it lives

- `ex_dim` in [basic/arrays.asm](../../basic/arrays.asm) reads the names and
  bounds; the array engine itself runs from the sub ROM —
  `aeng_dim` and `ary_alloc` in [sub/arrays.asm](../../sub/arrays.asm), which
  makes the size check before allocating.
- The evaluator's stack check is `stk_guard` in
  [basic/expr.asm](../../basic/expr.asm).
- The design notes are in [spec-basic-arrays.md](../spec-basic-arrays.md).

## Related concepts

- [The memory map](../concepts/memory-map.md) — where BASIC keeps things in RAM
- [Variables](../concepts/variables.md) — names, types, arrays, and where they live

## Tests that cover it

- `make array-acceptance` — creating, using, re-declaring and erasing arrays.
- `make arrdim-acceptance` — the size limit per type, the number of
  dimensions, and what a failed `DIM` leaves behind.
- `make ctllim-acceptance` — a deep formula next to an array that fills memory.
- `make kwsweep` — one- and multi-dimensional rows (the second reads the cell
  with its subscripts swapped) and the error rows.
- `make kwram` — the RAM-usage comparison.
