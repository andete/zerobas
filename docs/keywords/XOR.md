<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `XOR` — bitwise exclusive "or"

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. No known divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`a XOR b` combines two numbers bit by bit as 16-bit integers: a result bit is 1
where exactly one of the operands has a 1. Applying the same `XOR` twice gives
the original number back, and `XOR -1` flips every bit. zerobas behaves exactly
like the Philips VG-8020 for every case we have measured, errors included.

The operand rules and the precedence order are shared by all the logical
operators and are described on the [`AND`](AND.md) page.

## Syntax

```
<numeric expression> XOR <numeric expression>
```

## Details

- **Bitwise on 16 bits.** `5 XOR 3` is 6, `12 XOR 9` is 5, `5 XOR -1` is −6
  (the same as `NOT 5`).
- **On truth values** (−1 and 0) it is "one or the other but not both".
- **Operands are truncated toward zero to an integer** first; outside −32768 to
  32767 is `Overflow` (error 6). See [`AND`](AND.md#details).
- **Precedence:** looser than `AND` and `OR`, tighter than `IMP`. `XOR` and
  [`EQV`](EQV.md) cannot be ordered against each other by any measurement —
  every grouping of the two gives the same result.

| you write | you get |
|---|---|
| `5 XOR 3` | 6 |
| `70000 XOR 1`, `1 XOR 70000` | error 6, `Overflow` |
| `1 XOR "A"` | error 13, `Type mismatch` |
| `PRINT 1 XOR` | error 24, `Missing operand` |

The whole set of errors `XOR` can raise is {6, 13, 24}, the same on both
machines.

## Example

```
10 PRINT 5 XOR 3;12 XOR 9
20 PRINT 5 XOR -1
30 A=1234:K=99:B=A XOR K
40 PRINT B;B XOR K
50 ON ERROR GOTO 80
60 PRINT 1 XOR 70000
70 END
80 PRINT "Error";ERR:RESUME NEXT
RUN
 6  5
-6
 1201  1234
Error 6
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_xor.out`](../../scratchpad/kwdoc_xor.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

None known.

The one rung not yet proven is **RAM usage**: `XOR` uses the same amount of free
memory on both machines, but the VG-8020 writes some work-area cells that
zerobas does not.

## What we found, and how

`XOR` shares its history with the other logical operators; the details are on
the [`AND`](AND.md#what-we-found-and-how) page. Two points are its own:

- **`XOR` and `EQV` have no observable order** (measured 2026-07-27). Both
  reduce to the same three-way bit operation, so `(x XOR y) EQV z` and
  `x XOR (y EQV z)` are equal for every x, y and z. zerobas places `EQV` one
  level looser only so the table reads in the manual's order; that choice
  cannot change any result:
  [logicops-vg8020-characterization.md](../logicops-vg8020-characterization.md) §3.
- **`PRINT "A" XOR 1` printed `A` and then `1`** instead of `Type mismatch`
  (fixed 2026-07-27): [spec-basic-relational-chain.md](../spec-basic-relational-chain.md).

## Where it lives

`ev_logic` / `ev_lg` in [basic/expr.asm](../../basic/expr.asm) walk the table
`logtab` in [basic/islands.asm](../../basic/islands.asm); the leaf `lg_xor` does
the work.

## Tests that cover it

- `make logicops-acceptance` — results, precedence and the integer range.
- `make kwsweep` — the everyday row (`5 XOR 3`), the error rows for
  {6, 13, 24}, and the deliberately-broken-build check.
- `make kwram` — the RAM-usage comparison.
