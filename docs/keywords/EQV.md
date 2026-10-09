<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `EQV` — bitwise equivalence

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. No known divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`a EQV b` combines two numbers bit by bit as 16-bit integers: a result bit is 1
where the two operands have the *same* bit. It is exactly `NOT (a XOR b)`. On
truth values (−1 and 0) it answers "are both true, or both false?". zerobas
behaves exactly like the Philips VG-8020 for every case we have measured,
errors included.

The operand rules and the precedence order are shared by all the logical
operators and are described on the [`AND`](AND.md) page.

## Syntax

```
<numeric expression> EQV <numeric expression>
```

## Details

- **Measured results:**

  | expression | result | expression | result |
  |---|---|---|---|
  | `0 EQV 0` | −1 | `-1 EQV -1` | −1 |
  | `0 EQV -1` | 0 | `-1 EQV 0` | 0 |
  | `5 EQV 3` | −7 | `12 EQV 10` | −7 |
  | `1 EQV 0` | −2 | | |

  It is commutative: `a EQV b` equals `b EQV a`.
- **Operands are truncated toward zero to an integer** first: `2.7 EQV 0` is −3
  (operand 2) and `-2.7 EQV 0` is 1 (operand −2). The range is −32768 to 32767:
  `-32768 EQV 0` is 32767, `-32769 EQV 0` and `1E10 EQV 1` are `Overflow`
  (error 6). See [`AND`](AND.md#details).
- **Precedence:** looser than `AND` and `OR`, tighter than `IMP`. Against
  [`XOR`](XOR.md) no order can be observed. Arithmetic binds tighter:
  `1 EQV 2 + 3` is `1 EQV 5`, which is −5.

| you write | you get |
|---|---|
| `5 EQV 3` | −7 |
| `70000 EQV 1`, `1 EQV 70000` | error 6, `Overflow` |
| `1 EQV "A"`, `"A" EQV 1` | error 13, `Type mismatch` |
| `PRINT 1 EQV` | error 24, `Missing operand` |

The whole set of errors `EQV` can raise is {6, 13, 24}, the same on both
machines.

## Example

```
10 PRINT 5 EQV 3;1 EQV 0
20 PRINT 0 EQV 0;0 EQV -1
30 PRINT NOT (5 XOR 3)
40 PRINT (1>2) EQV (3>4)
50 ON ERROR GOTO 80
60 PRINT 1 EQV "A"
70 END
80 PRINT "Error";ERR:RESUME NEXT
RUN
-7 -2
-1  0
-7
-1
Error 13
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_eqv.out`](../../scratchpad/kwdoc_eqv.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

None known.

The one rung not yet proven is **RAM usage**: `EQV` uses the same amount of free
memory on both machines, but the VG-8020 writes some work-area cells that
zerobas does not.

## What we found, and how

- **`EQV` was missing, and silently wrong** (added 2026-07-27). Before, zerobas
  read `EQV` as a variable name, so `PRINT 5 EQV 3` printed three separate
  values with no error. Its meaning was measured before it was written:
  `NOT (a XOR b)` was treated as a guess to search for test values with, and
  the VG-8020's own answers decided. The token number (`$F9`) was read from
  the VG-8020's own tokenised lines:
  [logicops-vg8020-characterization.md](../logicops-vg8020-characterization.md),
  [spec-basic-logicops-eqv-imp.md](../spec-basic-logicops-eqv-imp.md).
- **The integer conversion was read through `EQV` itself.** `EQV n 0` equals
  `NOT n`, so its printed result names the converted operand exactly; that is
  how truncation (not rounding) was established for all the logical operators.
- **`EQV` and `XOR` have no observable order**, so where `EQV` sits relative to
  `XOR` is a free choice; it was decided on 2026-07-27 to keep them on separate
  levels, in the manual's order.
- **Adding it made the parser smaller.** `EQV` and `IMP` came in with one
  table-driven layer replacing three hand-written ones, which took less ROM
  space than before.

## Where it lives

`ev_logic` / `ev_lg` in [basic/expr.asm](../../basic/expr.asm) walk the table
`logtab` in [basic/islands.asm](../../basic/islands.asm); the leaf `lg_eqv`
(`xor`, then complement) does the work.

## Tests that cover it

- `make logicops-acceptance` — the truth table, every precedence pair, the
  integer range; a build with the complement deleted fails it.
- `make kwsweep` — the everyday row (`5 EQV 3`), the error rows for
  {6, 13, 24}, and the deliberately-broken-build check.
- `make kwram` — the RAM-usage comparison.
