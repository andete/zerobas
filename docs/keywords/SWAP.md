<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `SWAP` — exchange the values of two variables

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. No known divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`SWAP A,B` exchanges the values of two variables of the same type: afterwards
`A` holds what `B` held and the other way round. It works for numbers, strings
and array elements. zerobas behaves exactly like the Philips VG-8020 for every
case we have measured, errors included.

## Syntax

```
SWAP <variable>,<variable>
```

Both operands must be variables or array elements — not numbers, expressions
or functions.

## Details

- **Every type exchanges**: integer, single, double and string variables, and
  array elements (`SWAP Q(0),Q(1)`, `SWAP A,Q(0)`, `SWAP Q$(0),Q$(1)`).
  `SWAP A,A` is allowed and changes nothing.
- **The types must be exactly equal.** A number with a string is
  `Type mismatch` (error 13), and so is any mix of numeric types: `A%` with
  `B!`, `A!` with `B#`, `A%` with a plain `B` (which is double). `DEFINT` and
  friends count: after `DEFINT C`, `C` and `D` are different types.
- **Strings are exchanged without copying their text.** Only the strings'
  descriptors move, so swapping a 2-character string with a 20-character one
  leaves both intact, also after later string allocations.
- **The second variable must already exist; the first need not.**
  `B=1:SWAP A,B` creates `A` (it ends up 1, `B` ends up 0), but `A=1:SWAP A,B`
  with no `B` yet is `Illegal function call` (error 5). An array that was
  never `DIM`med is no problem: `A=1:SWAP A,Q(0)` creates `Q` as `DIM` would
  and exchanges.
- **A wrong subscript** is `Subscript out of range` (error 9):
  `DIM Q(2):SWAP A,Q(9)`.
- **The shape errors** are `Syntax error` (error 2): `SWAP`, `SWAP A`,
  `SWAP A,1`, `SWAP 1,A`, `SWAP A,B+0`, `SWAP A,LEN("x")`, `SWAP (A),B`.
- **Anything after the second variable** is `Syntax error` too — but only
  *after* the exchange has happened: `A=1:B=2:SWAP A,B,C` leaves `A`=2 and
  `B`=1, then raises error 2. If `B` does not exist, the error is 5 instead.
- **Which error wins:** a type mismatch is reported before the missing second
  variable — `SWAP A,B$` with neither defined is error 13, not 5.

| you write | you get |
|---|---|
| `A=1:B=2:SWAP A,B` | A is 2, B is 1 |
| `A=1:B$="x":SWAP A,B$` | error 13, `Type mismatch` |
| `A%=1:B!=2.5:SWAP A%,B!` | error 13, `Type mismatch` |
| `A=1:SWAP A,B` (no `B`) | error 5, `Illegal function call` |
| `DIM Q(2):SWAP A,Q(9)` | error 9, `Subscript out of range` |
| `SWAP A`, `SWAP A,1` | error 2, `Syntax error` |

Every error above is the same on both machines.

## Example

```
10 A=1:B=2:SWAP A,B:PRINT A;B
20 A$="LEFT":B$="RIGHT"
30 SWAP A$,B$:PRINT A$;" ";B$
40 DIM Q(3):Q(0)=7:Q(1)=9
50 SWAP Q(0),Q(1):PRINT Q(0);Q(1)
60 ON ERROR GOTO 100
70 SWAP A,B$
80 SWAP A,Z
90 END
100 PRINT "Error";ERR:RESUME NEXT
RUN
 2  1
RIGHT LEFT
 9  7
Error 13
Error 5
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_swap.out`](../../scratchpad/kwdoc_swap.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

None known.

The one rung not yet proven is **RAM usage**: `SWAP` uses the same amount of
free memory on both machines, but the two machines write different work-area
cells along the way — the VG-8020 some that zerobas does not, and zerobas a few
the VG-8020 does not.

## What we found, and how

- **`SWAP` arrived on 2026-07-28**, after its behaviour on the VG-8020 was
  measured first (2026-07-27). Three things there are easy to guess wrong: the
  type rule is exact type equality, not just "number or string"; strings move
  by descriptor; and only the *second* variable has to exist:
  [missing-vg8020-characterization.md](../missing-vg8020-characterization.md) §4.
- **An extra operand gave the wrong error, at the wrong moment** (fixed
  2026-08-24, D-SWAP3). zerobas had its own check for a third operand that
  raised error 5 before exchanging anything; both reference machines exchange
  first and then raise error 2. The earlier measurement had agreed for the
  wrong reason — its `B` did not exist, so it was really measuring the
  second-operand rule. The check was deleted and the general end-of-statement
  check now handles it, which also saved ROM space:
  [spec-basic-swap3.md](../spec-basic-swap3.md).
- **Two undefined variables of different types gave the wrong error** (fixed
  2026-09-16, D-SWAPTYPE). `SWAP A,B$` with neither defined was
  `Illegal function call`; both references say `Type mismatch`
  ([kwt3_swapchk.out](../../scratchpad/kwt3_swapchk.out)). zerobas now checks
  the types, which it knows from the names, before complaining about the
  missing variable. The fix was ready on 2026-09-13 but had to wait three days
  for the ten bytes of ROM it needed.

## Where it lives

`ex_swap` in [basic/missing.asm](../../basic/missing.asm): `sw_operand`
resolves each operand (creating the first if needed), `sw_absent` raises the
missing-second-operand error, and `sw_types` checks the types and exchanges the
bytes.

## Tests that cover it

- `make missing-acceptance` — every type, array elements, string descriptors,
  the type-equality and existence rules, and the shape errors.
- `make kwsweep` — the everyday row (`SWAP A,B`), the error rows for 2 and 13,
  the `Type mismatch` row with undefined variables, and the
  deliberately-broken-build check.
- `make kwram` — the RAM-usage comparison.
