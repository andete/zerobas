<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `IMP` — bitwise implication

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. No known divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`a IMP b` combines two numbers bit by bit as 16-bit integers and is exactly
`(NOT a) OR b`: a result bit is 0 only where `a` has a 1 and `b` has a 0. On
truth values (−1 and 0) it reads "if a then b": it is false only when `a` is
true and `b` is false. It is the loosest of the logical operators. zerobas
behaves exactly like the Philips VG-8020 for every case we have measured,
errors included.

The operand rules and the precedence order are shared by all the logical
operators and are described on the [`AND`](AND.md) page.

## Syntax

```
<numeric expression> IMP <numeric expression>
```

## Details

- **Measured results:**

  | expression | result | expression | result |
  |---|---|---|---|
  | `0 IMP 0` | −1 | `-1 IMP -1` | −1 |
  | `0 IMP -1` | −1 | `-1 IMP 0` | 0 |
  | `5 IMP 3` | −5 | `12 IMP 10` | −5 |
  | `1 IMP 0` | −2 | `&HF0F0 IMP &H0FF0` | 4095 |

- **Order matters.** Unlike the other logical operators, `IMP` is not
  commutative: `0 IMP -1` is −1 but `-1 IMP 0` is 0.
- **A chain groups left to right**, and `IMP` is the one operator where you
  can see it: `0 IMP 0 IMP 0` is `(0 IMP 0) IMP 0`, which is 0 (grouping
  from the right would give −1).
- **Lowest precedence.** Everything else binds tighter: arithmetic
  (`1 IMP 2 + 3` is `1 IMP 5`), comparisons (`1 = 1 IMP 1 = 0` is
  `(1=1) IMP (1=0)`, which is 0), and `NOT`, `AND`, `OR`, `XOR`, `EQV`.
- **Operands are truncated toward zero to an integer** first; the range is
  −32768 to 32767. `32767 IMP 0` is −32768, `32768 IMP 0` is `Overflow`
  (error 6). See [`AND`](AND.md#details).

| you write | you get |
|---|---|
| `5 IMP 3` | −5 |
| `70000 IMP 1`, `1 IMP 70000` | error 6, `Overflow` |
| `1 IMP "A"` | error 13, `Type mismatch` |
| `PRINT 1 IMP` | error 24, `Missing operand` |

The whole set of errors `IMP` can raise is {6, 13, 24}, the same on both
machines.

## Example

```
10 PRINT 5 IMP 3;1 IMP 0
20 PRINT 0 IMP -1;-1 IMP 0
30 PRINT 0 IMP 0 IMP 0
40 PRINT &HF0F0 IMP &H0FF0
50 ON ERROR GOTO 80
60 PRINT 32768 IMP 0
70 END
80 PRINT "Error";ERR:RESUME NEXT
RUN
-5 -2
-1  0
 0
 4095
Error 6
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_imp.out`](../../scratchpad/kwdoc_imp.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

None known.

The one rung not yet proven is **RAM usage**: `IMP` uses the same amount of free
memory on both machines, but the VG-8020 writes some work-area cells that
zerobas does not.

## What we found, and how

- **`IMP` was missing, and silently wrong** (added 2026-07-27). zerobas read
  `IMP` as a variable name, so `PRINT 5 IMP 3` printed three separate values
  with no error. Its meaning, `(NOT a) OR b`, and the fact that it is not
  commutative were measured on the VG-8020 before it was written:
  [logicops-vg8020-characterization.md](../logicops-vg8020-characterization.md),
  [spec-basic-logicops-eqv-imp.md](../spec-basic-logicops-eqv-imp.md).
- **Its place in the order needed both directions measured.** `x IMP y OR z`
  gives the same answer under either grouping, so it says nothing; only
  `x OR y IMP z` shows that `OR` binds tighter. Testing one direction per pair
  would have left that hole unnoticed.
- **Several "obvious" test rows measured nothing.** `IMP n -1` is always −1,
  and `NOT 0 IMP 0` gives the same value under both groupings; such rows were
  replaced by ones whose groupings disagree, so a pass means something.
- **`PRINT "A" IMP 1` printed `A` and then `-1`** instead of `Type mismatch`
  (fixed 2026-07-27): [spec-basic-relational-chain.md](../spec-basic-relational-chain.md).

## Where it lives

`ev_logic` / `ev_lg` in [basic/expr.asm](../../basic/expr.asm) walk the table
`logtab` in [basic/islands.asm](../../basic/islands.asm), where `IMP` is the
first (loosest) entry; the leaf `lg_imp` (complement, then `or`) does the work.

## Related concepts

- [Numbers](../concepts/numbers.md) — integers, single and double precision

## Tests that cover it

- `make logicops-acceptance` — the truth table, every precedence pair, the
  left-to-right grouping, the integer range.
- `make kwsweep` — the everyday row (`5 IMP 3`), the error rows for
  {6, 13, 24}, and the deliberately-broken-build check.
- `make kwram` — the RAM-usage comparison.
