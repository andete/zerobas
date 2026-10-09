<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `NOT` — bitwise and logical "not"

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. No known divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`NOT a` flips every bit of a number taken as a 16-bit integer, so `NOT a` is
always `-a - 1`. Because true is −1 and false is 0, it also turns true into
false and back: `IF NOT (A>5) THEN …`. zerobas behaves exactly like the
Philips VG-8020 for every case we have measured, errors included.

The operand rules and the precedence order are shared by all the logical
operators and are described on the [`AND`](AND.md) page.

## Syntax

```
NOT <numeric expression>
```

`NOT` takes one operand, on its right.

## Details

- **Bitwise on 16 bits.** `NOT 0` is −1, `NOT -1` is 0, `NOT 5` is −6.
- **The operand is truncated toward zero to an integer** first: `NOT 2.5` is −3
  (that is, `NOT 2`), `NOT 1.5` is −2. The range is −32768 to 32767; `NOT 70000`
  is `Overflow` (error 6). See [`AND`](AND.md#details).
- **It can be repeated**: `NOT NOT 7` is 7.
- **Precedence:** `NOT` binds tighter than `AND`, `OR` and `IMP`:
  `NOT 1 AND 3` is `(NOT 1) AND 3`, which is 2, and `NOT 1 IMP 2` is
  `(NOT 1) IMP 2`, which is 3. Against `XOR` and `EQV` no order can be
  observed — both groupings always give the same result.
- **Use parentheses with a comparison.** Whether `NOT A>5` means
  `NOT (A>5)` or `(NOT A)>5` has not been measured on the reference;
  `NOT (A>5)` says what you mean either way.

| you write | you get |
|---|---|
| `NOT 0` | −1 |
| `NOT 2.5` | −3 |
| `NOT 70000` | error 6, `Overflow` |
| `NOT "A"` | error 13, `Type mismatch` |
| `PRINT NOT` | error 24, `Missing operand` |

The whole set of errors `NOT` can raise is {6, 13, 24}, the same on both
machines.

## Example

```
10 PRINT NOT 0;NOT -1;NOT 5
20 PRINT NOT 2.5;NOT NOT 7
30 A=3
40 IF NOT (A>5) THEN PRINT "small"
50 ON ERROR GOTO 80
60 PRINT NOT 70000
70 END
80 PRINT "Error";ERR:RESUME NEXT
RUN
-1  0 -6
-3  7
small
Error 6
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_not.out`](../../scratchpad/kwdoc_not.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

None known.

The one rung not yet proven is **RAM usage**: `NOT` uses the same amount of free
memory on both machines, but the VG-8020 writes some work-area cells that
zerobas does not.

## What we found, and how

- **Fractional operands** follow the VG-8020's truncate-or-`Overflow` rule
  since 2026-07-11 (`NOT 2.5` is −3, not −4):
  [spec-basic-float-core.md](../spec-basic-float-core.md) §10.3.
- **`NOT` against the other operators was measured with care** (2026-07-27).
  `NOT 1 EQV 2` gives 3 under both groupings, because `EQV` and `XOR` absorb a
  complement; so `NOT` against `EQV` and `XOR` cannot be ordered by any test,
  while against `IMP` (`NOT 1 IMP 2`) it can:
  [logicops-vg8020-characterization.md](../logicops-vg8020-characterization.md) §5.
- **Deeply nested expressions had no stack limit** (fixed 2026-09-27,
  D-STACKFLOOR). With arrays filling memory to the edge, a deep enough formula
  could overwrite them. A chain of `NOT`s is one of the two ways an expression
  nests (parentheses and functions are the other), so `NOT` got the same check:
  the evaluator now stops with `Out of memory` (error 7) instead, as the
  reference does.
- **The tests could not at first prove they would notice a broken `NOT`**
  (2026-09-14, D-KWOPCUT): its dispatch is a short jump that the
  deliberately-broken-build check did not recognise. It is now found by the
  routine it lives in, and a broken `NOT` fails the gates.

## Where it lives

`ev_not` / `ev_not_do` in [basic/expr.asm](../../basic/expr.asm), between the
logical layer and the comparisons; the integer conversion is
`fac_to_int_strict_reset` in
[basic/float-arith.asm](../../basic/float-arith.asm).

## Related concepts

- [Numbers](../concepts/numbers.md) — integers, single and double precision

## Tests that cover it

- `make logicops-acceptance` — results, precedence against the two-operand
  operators, and the integer range.
- `make float-acceptance` — fractional operands (`NOT 1.5`, `NOT 2.5`).
- `make kwsweep` — the everyday row (`NOT 0`), the error rows for {6, 13, 24},
  and the deliberately-broken-build check.
- `make kwram` — the RAM-usage comparison.
