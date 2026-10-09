<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `AND` — bitwise and logical "and"

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. No known divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`a AND b` combines two numbers bit by bit as 16-bit integers: a result bit is 1
only where both operands have a 1. Because a comparison gives −1 (all bits set)
for true and 0 for false, the same operator also works as the logical "and" in
`IF A>0 AND A<10 THEN …`. zerobas behaves exactly like the Philips VG-8020 for
every case we have measured, errors included.

This page also holds the rules shared by all six logical operators: `AND`,
[`OR`](OR.md), [`XOR`](XOR.md), [`EQV`](EQV.md), [`IMP`](IMP.md) and
[`NOT`](NOT.md).

## Syntax

```
<numeric expression> AND <numeric expression>
```

## Details

- **Bitwise on 16 bits.** `5 AND 3` is 1, `12 AND 10` is 8, `-1 AND 255` is
  255. The result is always a whole number from −32768 to 32767.
- **As a logical "and"** it relies on true being −1 and false 0:
  `(1<2) AND (3<4)` is −1, `(1<2) AND (3>4)` is 0.
- **Each operand is converted to an integer first, by truncating toward zero**
  — never by rounding. `2.7` becomes 2, `-2.7` becomes −2, and `2.5` and `3.5`
  become 2 and 3. So `2.7 AND 3` is 2.
- **The operand range is −32768 to 32767.** A value outside it is `Overflow`
  (error 6), on either side: `70000 AND 1` and `1 AND 70000` both fail. A
  fraction just inside the range is fine — `32767.6` truncates to 32767.
  (This is stricter than `POKE`'s address range, which accepts up to 65535.)
- **A string on either side** is `Type mismatch` (error 13): `1 AND "A"`,
  and also `PRINT "A" AND 1`.
- **Nothing after the operator** (`PRINT 1 AND`) is `Missing operand`
  (error 24).

### Precedence of the logical operators

Measured on the VG-8020 for every ordered pair, in both directions:

| tightest | | | | loosest |
|---|---|---|---|---|
| `NOT` | `AND` | `OR` | `XOR`, `EQV` | `IMP` |

- Arithmetic and comparisons bind tighter than the two-operand ones, so
  `A>0 AND A<10` means `(A>0) AND (A<10)`. (How `NOT` sits against a
  comparison has not been measured; see [`NOT`](NOT.md).)
- `XOR` and `EQV` cannot be ordered against each other by any measurement:
  every grouping of the two gives the same answer.
- All of them group left to right; this only shows with `IMP` (see its page).

### Errors

| you write | you get |
|---|---|
| `5 AND 3` | 1 |
| `2.7 AND 3` | 2 |
| `70000 AND 1`, `1 AND 70000` | error 6, `Overflow` |
| `1 AND "A"` | error 13, `Type mismatch` |
| `PRINT 1 AND` | error 24, `Missing operand` |

The whole set of errors `AND` can raise is {6, 13, 24}, the same on both
machines.

## Example

```
10 A=5
20 IF A>0 AND A<10 THEN PRINT "ok"
30 PRINT 5 AND 3;12 AND 10;-1 AND 255
40 PRINT 2.7 AND 3
50 ON ERROR GOTO 80
60 PRINT 70000 AND 1
70 END
80 PRINT "Error";ERR:RESUME NEXT
RUN
ok
 1  8  255
 2
Error 6
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_and.out`](../../scratchpad/kwdoc_and.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

None known.

The one rung not yet proven is **RAM usage**: `AND` uses the same amount of
free memory on both machines, but the VG-8020 writes some work-area cells that
zerobas does not. Nothing a program can observe through `FRE` differs.

## What we found, and how

- **Fractions were rounded, and out-of-range numbers silently became 0**, in
  an interim stage of the float work (fixed 2026-07-11, with the float
  arithmetic). Measuring the VG-8020 showed that the logical operators truncate
  toward zero and raise `Overflow` outside −32768 to 32767 — the same strict
  rule as `\` and `MOD`, and not the wider range `POKE` accepts:
  [spec-basic-float-core.md](../spec-basic-float-core.md) §10.3.
- **The precedence order was measured, not copied from the manual**
  (2026-07-27). Each pair was tested with three lines — the bare expression and
  both explicit groupings — so that a test whose two groupings happen to agree
  is reported as "cannot tell" rather than as a pass. That is how `XOR` and
  `EQV` turned out to be indistinguishable:
  [logicops-vg8020-characterization.md](../logicops-vg8020-characterization.md).
- **`PRINT "A" AND 1` printed two values** instead of `Type mismatch` (fixed
  2026-07-27). `PRINT` printed the string, then read the operator as the start
  of a second item. Eleven operators were affected, not the four first
  suspected: [spec-basic-relational-chain.md](../spec-basic-relational-chain.md).
- **One table now drives all five two-operand logical operators** (2026-07-27,
  when `EQV` and `IMP` were added). The first build of it passed every static
  check and crashed on any fractional operand (`2.7 AND 0`); the side-by-side
  test against the VG-8020 caught it before it shipped:
  [spec-basic-logicops-eqv-imp.md](../spec-basic-logicops-eqv-imp.md) §5.1.
- **The tests could not at first prove they would notice a broken `AND`**
  (2026-09-14, D-KWOPCUT). The deliberately-broken-build check finds a keyword
  by the compare that dispatches it, and the logical operators are found by
  walking a table instead. A cut for that table was added; a broken `AND` now
  fails the gates.

## Where it lives

`ev_logic` / `ev_lg` in [basic/expr.asm](../../basic/expr.asm) walk the
precedence table `logtab` in [basic/islands.asm](../../basic/islands.asm);
`lg_apply` and the one-instruction leaf `lg_and` do the work. The integer
conversion is `fac_to_int_strict_reset` in
[basic/float-arith.asm](../../basic/float-arith.asm), shared with `\` and
[`MOD`](MOD.md).

## Related concepts

- [Numbers](../concepts/numbers.md) — integers, single and double precision

## Tests that cover it

- `make logicops-acceptance` — results, every precedence pair, grouping, the
  integer range, and the operator-after-a-string rows.
- `make float-acceptance` — fractional and out-of-range operands
  (`1.5 AND 3`, `40000! AND 65535`).
- `make kwsweep` — the everyday row (`5 AND 3`), the error rows for
  {6, 13, 24}, and the deliberately-broken-build check.
- `make kwram` — the RAM-usage comparison.
