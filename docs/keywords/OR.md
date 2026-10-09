<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `OR` — bitwise and logical "or"

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. No known divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`a OR b` combines two numbers bit by bit as 16-bit integers: a result bit is 1
where either operand has a 1. With comparisons, which give −1 for true and 0
for false, it is the logical "or": `IF K=1 OR K=2 THEN …`. zerobas behaves
exactly like the Philips VG-8020 for every case we have measured, errors
included.

The operand rules and the precedence order are shared by all the logical
operators and are described on the [`AND`](AND.md) page.

## Syntax

```
<numeric expression> OR <numeric expression>
```

## Details

- **Bitwise on 16 bits.** `5 OR 3` is 7, `12 OR 10` is 14, `0 OR 0` is 0 and
  `-1 OR 0` is −1. A common use is setting bits: `K=K OR 4`.
- **Operands are truncated toward zero to an integer** first; outside −32768 to
  32767 is `Overflow` (error 6). See [`AND`](AND.md#details).
- **Precedence:** `OR` binds looser than `AND` and tighter than `XOR`, `EQV`
  and `IMP`; arithmetic and comparisons bind tighter still. So
  `A OR B AND C` is `A OR (B AND C)`.

| you write | you get |
|---|---|
| `5 OR 3` | 7 |
| `70000 OR 1`, `1 OR 70000` | error 6, `Overflow` |
| `1 OR "A"` | error 13, `Type mismatch` |
| `PRINT 1 OR` | error 24, `Missing operand` |

The whole set of errors `OR` can raise is {6, 13, 24}, the same on both
machines.

## Example

```
10 PRINT 5 OR 3;12 OR 10
20 PRINT 0 OR 0;-1 OR 0
30 K=0:K=K OR 4:K=K OR 1:PRINT K
40 ON ERROR GOTO 70
50 PRINT 1 OR "A"
60 END
70 PRINT "Error";ERR:RESUME NEXT
RUN
 7  14
 0 -1
 5
Error 13
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_or.out`](../../scratchpad/kwdoc_or.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

None known.

The one rung not yet proven is **RAM usage**: `OR` uses the same amount of free
memory on both machines, but the VG-8020 writes some work-area cells that
zerobas does not.

## What we found, and how

`OR` shares its history with the other logical operators; the details are on
the [`AND`](AND.md#what-we-found-and-how) page. In short:

- **Fractional and out-of-range operands** follow the VG-8020's
  truncate-or-`Overflow` rule since 2026-07-11.
- **`PRINT "A" OR 1` printed `A` and then `1`** instead of `Type mismatch`
  (fixed 2026-07-27): [spec-basic-relational-chain.md](../spec-basic-relational-chain.md).
- **The order `AND` > `OR` > `XOR`** was measured on the VG-8020 pair by pair
  (2026-07-27): [logicops-vg8020-characterization.md](../logicops-vg8020-characterization.md).

## Where it lives

`ev_logic` / `ev_lg` in [basic/expr.asm](../../basic/expr.asm) walk the table
`logtab` in [basic/islands.asm](../../basic/islands.asm); the leaf `lg_or` does
the work.

## Related concepts

- [Numbers](../concepts/numbers.md) — integers, single and double precision

## Tests that cover it

- `make logicops-acceptance` — results, precedence and the integer range.
- `make float-acceptance` — fractional operands (`1.5 OR 4`).
- `make kwsweep` — the everyday row (`5 OR 3`), the error rows for
  {6, 13, 24}, and the deliberately-broken-build check.
- `make kwram` — the RAM-usage comparison.
