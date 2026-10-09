<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `MOD` — the remainder of an integer division

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. No known divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`a MOD b` is what is left over when `a` is divided by `b` as whole numbers:
`7 MOD 3` is 1. It is the partner of integer division `\`: for any `a` and `b`,
`a = (a\b)*b + (a MOD b)`. zerobas behaves exactly like the Philips VG-8020
for every case we have measured, errors included.

## Syntax

```
<numeric expression> MOD <numeric expression>
```

## Details

- **The result takes the sign of the left operand** (the dividend), because
  `\` truncates toward zero:

  | `7 MOD 2` | `-7 MOD 2` | `7 MOD -2` | `-7 MOD -2` |
  |---|---|---|---|
  | 1 | −1 | 1 | −1 |

- **Both operands are converted to integers first, by truncating toward zero**
  — never by rounding: `7.5 MOD 4` is `7 MOD 4`, which is 3. This is the same
  rule the logical operators use ([`AND`](AND.md#details)).
- **The operand range is −32768 to 32767.** A value outside it is `Overflow`
  (error 6): `70000 MOD 2`, `40000 MOD 7`.
- **Dividing by zero** is `Division by zero` (error 11): `5 MOD 0`.
- **A string operand** is `Type mismatch` (error 13), on either side:
  `5 MOD "A"`, and also `PRINT "A" MOD 2`.
- **Nothing after the operator** (`PRINT 5 MOD`) is `Missing operand`
  (error 24).
- **Where it sits among the arithmetic operators:** zerobas evaluates `MOD`
  after `*`, `/` and `\` and before `+` and `-`, the documented MSX order. No
  test isolates that order against the reference yet; parentheses make it
  explicit.

| you write | you get |
|---|---|
| `7 MOD 3` | 1 |
| `-7 MOD 2` | −1 |
| `7.5 MOD 4` | 3 |
| `70000 MOD 2` | error 6, `Overflow` |
| `5 MOD 0` | error 11, `Division by zero` |
| `5 MOD "A"` | error 13, `Type mismatch` |
| `PRINT 5 MOD` | error 24, `Missing operand` |

The whole set of errors `MOD` can raise is {6, 11, 13, 24}, the same on both
machines.

## Example

```
10 PRINT 7 MOD 3;-7 MOD 2;7 MOD -2
20 PRINT 7.9 MOD 3;7.5 MOD 4
30 FOR I=1 TO 6:PRINT I MOD 3;:NEXT
40 PRINT
50 ON ERROR GOTO 80
60 PRINT 5 MOD 0
70 END
80 PRINT "Error";ERR:RESUME NEXT
RUN
 1 -1  1
 1  3
 1  2  0  1  2  0
Error 11
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_mod.out`](../../scratchpad/kwdoc_mod.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

None known.

The one rung not yet proven is **RAM usage**: `MOD` uses the same amount of free
memory on both machines, but the VG-8020 writes some work-area cells that
zerobas does not.

## What we found, and how

- **`MOD` used to be unsigned, and `MOD 0` gave 0** (fixed 2026-07-11). The
  first integer-only version divided without regard to sign and returned 0
  for a zero divisor; both were written down as known differences. Measuring the
  VG-8020 settled the sign rule, the truncation of fractional operands and the
  `Division by zero` error, and the float arithmetic brought all three in:
  [spec-basic-float-core.md](../spec-basic-float-core.md) §10.3–§10.4.
- **`PRINT "A" MOD 2` printed `A` and then `0`** instead of `Type mismatch`
  (fixed 2026-07-27). `PRINT` printed the string and then read `MOD` as the
  start of a second item; eleven operators had the same fault:
  [spec-basic-relational-chain.md](../spec-basic-relational-chain.md).
- **The tests could not at first prove they would notice a broken `MOD`**
  (2026-09-14, D-KWOPCUT). The deliberately-broken-build check looks for a
  compare followed by a jump to the keyword's code, and `MOD`'s compare is
  followed by a plain return instead. It is now found by the routine it lives
  in, and a broken `MOD` fails the gates.

## Where it lives

`ev_mod` / `ev_mod_lp` in [basic/expr.asm](../../basic/expr.asm); the
remainder is `signed_mod_de_bc` and the integer conversion
`fac_to_int_strict_reset`, both in
[basic/float-arith.asm](../../basic/float-arith.asm).

## Related concepts

- [Numbers](../concepts/numbers.md) — integers, single and double precision

## Tests that cover it

- `make float-acceptance` — the signs, division by zero, fractional and
  out-of-range operands (`7.9 MOD 3`, `40000 MOD 7`).
- `make logicops-acceptance` — the operator-after-a-string row (`"A" MOD 2`).
- `make kwsweep` — the everyday row (`7 MOD 3`), the error rows for
  {6, 11, 13, 24}, and the deliberately-broken-build check.
- `make kwram` — the RAM-usage comparison.
